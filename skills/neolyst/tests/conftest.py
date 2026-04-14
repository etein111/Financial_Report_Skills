"""Pytest 配置文件 - neolyst skill 测试。

从 tests/test_config.json 读取连接配置（不提交到版本库）。
首次使用：cp test_config.example.json test_config.json，按需修改。
"""
import json
import sys
import uuid
import pytest
from pathlib import Path

# 将项目根目录加入 Python 路径，支持 `from skills.neolyst.scripts import ...`
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

TEST_DIR = Path(__file__).parent
CONFIG_FILE = TEST_DIR / "test_config.json"


def _load_test_config() -> dict:
    if not CONFIG_FILE.exists():
        pytest.exit(
            f"测试配置文件不存在: {CONFIG_FILE}\n"
            f"请复制模板并修改: cp {TEST_DIR / 'test_config.example.json'} {CONFIG_FILE}"
        )
    return json.loads(CONFIG_FILE.read_text())


_config = _load_test_config()

# 注入环境变量供 connection.py 读取
import os
os.environ["NEOLYST_URL"] = _config["supabase_url"]
os.environ["NEOLYST_ANON_KEY"] = _config["anon_key"]

TEST_EMAIL = _config["email"]
TEST_PASSWORD = _config["password"]


@pytest.fixture(scope="session")
def neolyst_client():
    """返回已认证的 Supabase client（session 级，整个测试会话复用）。"""
    from skills.neolyst.scripts import connection

    test_dir = Path.home() / "tmp" / "neolyst_test"
    test_dir.mkdir(parents=True, exist_ok=True)

    return connection.get_client(
        neolyst_dir=str(test_dir),
        email=TEST_EMAIL,
        password=TEST_PASSWORD,
    )


@pytest.fixture(scope="session")
def test_analyst_email():
    """测试使用的分析师邮箱（来自 test_config.json）。"""
    return TEST_EMAIL


@pytest.fixture(scope="session", autouse=True)
def ensure_buckets(neolyst_client):
    """确保 templates 和 reports bucket 存在（幂等）。"""
    for bucket in ("templates", "reports"):
        try:
            neolyst_client.storage.create_bucket(bucket, options={"public": False})
        except Exception:
            pass  # 已存在则忽略


@pytest.fixture(scope="session")
def test_sector_id(neolyst_client):
    """第一个可用的 sector id。"""
    resp = neolyst_client.table("sector").select("id").eq("is_active", True).limit(1).execute()
    assert resp.data, "需要至少一条 sector 记录，请先运行 supabase db reset"
    return resp.data[0]["id"]


# ── shared test helpers ────────────────────────────────────────────────


def _make_files(directory: Path, prefix: str = "report") -> tuple[str, str]:
    """创建最小化 docx 和 pdf 测试文件。"""
    directory.mkdir(parents=True, exist_ok=True)
    word = directory / f"{prefix}.docx"
    pdf = directory / f"{prefix}.pdf"
    word.write_bytes(b"fake docx")
    pdf.write_bytes(b"fake pdf")
    return str(word), str(pdf)


def _base_report_payload(analyst_email: str, **overrides) -> dict:
    """构造 save_report 所需的标准 payload 字典。"""
    payload = {
        "report_id": None,
        "title": "Test Report",
        "report_type": "company",
        "report_language": "en",
        "analysts": [{"analyst_email": analyst_email, "author_order": 1}],
        "ticker": "TEST001",
        "coverage_id": None,
        "rating": None,
        "target_price": None,
        "region_code": None,
        "sector_id": None,
        "contact_person": analyst_email,
        "investment_thesis": None,
    }
    payload.update(overrides)
    return payload


def _create_submitted_report(client, coverage_id, tmp_dir, title, analyst_email, **payload_overrides):
    """创建并提交一份报告，返回 submit_report 的返回值。"""
    from skills.neolyst.scripts import save_report, upload_files, submit_report as sr

    word_path, pdf_path = _make_files(tmp_dir)
    saved = save_report.save_report(client, _base_report_payload(
        analyst_email,
        title=title,
        coverage_id=coverage_id,
        investment_thesis=f"{title} thesis",
        rating="OUTPERFORM",
        target_price=100.0,
        **payload_overrides,
    ))
    upload_files.upload_report_files(client, saved["report_id"], word_path, pdf_path)
    return sr.submit_report(client, saved["report_id"])
