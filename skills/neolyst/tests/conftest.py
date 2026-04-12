"""Pytest 配置文件 - neolyst skill 测试。

从 tests/test_config.json 读取连接配置（不提交到版本库）。
首次使用：cp test_config.example.json test_config.json，按需修改。
"""
import json
import sys
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
