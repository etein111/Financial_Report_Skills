"""
test_draft_report.py — save_draft_report 集成测试。
"""
import json
import uuid
from pathlib import Path

import pytest

TEST_ANALYST = json.loads((Path(__file__).parent / "test_config.json").read_text())["email"]


# ── module-level fixtures ────────────────────────────────────────────

@pytest.fixture(scope="module")
def tmp_module_dir(tmp_path_factory):
    return tmp_path_factory.mktemp("draft_report")


def _make_files(directory: Path) -> tuple[str, str]:
    word = directory / "report.docx"
    pdf = directory / "report.pdf"
    word.write_bytes(b"fake docx content for test")
    pdf.write_bytes(b"fake pdf content for test")
    return str(word), str(pdf)


@pytest.fixture(scope="module")
def first_save_result(neolyst_client, tmp_module_dir):
    """首次保存（report_id=None），模块结束后清理 report 及 storage 文件。"""
    from skills.neolyst.scripts import draft_report

    word_path, pdf_path = _make_files(tmp_module_dir)
    result = draft_report.save_draft_report(neolyst_client, {
        "report_id": None,
        "title": "Test Draft Report Iter4",
        "report_type": "company",
        "report_language": "en",
        "analysts": [{"analyst_email": TEST_ANALYST, "author_order": 1}],
        "ticker": "TSTDR01",
        "coverage_id": None,
        "rating": None,
        "target_price": None,
        "region_code": None,
        "sector_id": None,
        "contact_person": None,
        "investment_thesis": None,
        "report_file": word_path,
        "pdf_file": pdf_path,
        "model_file": None,
    })
    yield result
    # Teardown: 删除 report（级联删除 report_version/report_analyst）
    neolyst_client.table("report").delete().eq("id", result["report_id"]).execute()
    # 清理 storage（v1/ v2/ 目录）
    report_id = result["report_id"]
    try:
        neolyst_client.storage.from_("reports").remove([
            f"{report_id}/v1/report.docx",
            f"{report_id}/v1/report.pdf",
            f"{report_id}/v2/report.docx",
            f"{report_id}/v2/report.pdf",
        ])
    except Exception:
        pass


@pytest.fixture(scope="module")
def second_save_result(neolyst_client, first_save_result, tmp_module_dir):
    """基于同一 report_id 的第二次保存（更新 title/rating）。"""
    from skills.neolyst.scripts import draft_report

    word_path, pdf_path = _make_files(tmp_module_dir)
    return draft_report.save_draft_report(neolyst_client, {
        "report_id": first_save_result["report_id"],
        "title": "Test Draft Report Iter4 v2",
        "report_type": "company",
        "report_language": "en",
        "analysts": [{"analyst_email": TEST_ANALYST, "author_order": 1}],
        "ticker": "TSTDR01",
        "coverage_id": None,
        "rating": "OUTPERFORM",
        "target_price": 100.0,
        "region_code": None,
        "sector_id": None,
        "contact_person": TEST_ANALYST,
        "investment_thesis": "Updated thesis",
        "report_file": word_path,
        "pdf_file": pdf_path,
        "model_file": None,
    })


# ── happy path ───────────────────────────────────────────────────────

class TestSaveDraftNewReport:
    def test_returns_report_id_uuid(self, first_save_result):
        """首次保存返回合法 UUID 字符串的 report_id。"""
        assert first_save_result["report_id"]
        uuid.UUID(first_save_result["report_id"])

    def test_returns_version_no_1(self, first_save_result):
        """首次保存 version_no == 1。"""
        assert first_save_result["version_no"] == 1

    def test_returns_status_draft(self, first_save_result):
        """首次保存 status == 'draft'。"""
        assert first_save_result["status"] == "draft"

    def test_report_record_exists(self, neolyst_client, first_save_result):
        """report 表有对应记录，核心字段正确。"""
        resp = (
            neolyst_client.table("report")
            .select("*")
            .eq("id", first_save_result["report_id"])
            .execute()
        )
        assert resp.data
        record = resp.data[0]
        assert record["title"] == "Test Draft Report Iter4"
        assert record["report_type"] == "company"
        assert record["status"] == "draft"
        assert record["current_version_no"] == 1

    def test_report_version_record_exists(self, neolyst_client, first_save_result):
        """report_version 表有 version_no=1，file_path 含 v1/，snapshot 含 analysts 不含本地路径。"""
        resp = (
            neolyst_client.table("report_version")
            .select("*")
            .eq("report_id", first_save_result["report_id"])
            .eq("version_no", 1)
            .execute()
        )
        assert resp.data
        record = resp.data[0]
        assert "/v1/" in record["word_file_path"]
        assert "/v1/" in record["pdf_file_path"]
        snapshot = record["snapshot_json"]
        assert "analysts" in snapshot
        assert "report_file" not in snapshot
        assert "pdf_file" not in snapshot
        assert "model_file" not in snapshot

    def test_report_analyst_records_exist(self, neolyst_client, first_save_result):
        """report_analyst 表有 author_order=1 的分析师记录。"""
        resp = (
            neolyst_client.table("report_analyst")
            .select("*")
            .eq("report_id", first_save_result["report_id"])
            .execute()
        )
        assert len(resp.data) == 1
        assert resp.data[0]["analyst_email"] == TEST_ANALYST
        assert resp.data[0]["author_order"] == 1

    def test_storage_files_uploaded(self, neolyst_client, first_save_result):
        """Storage reports/{report_id}/v1/ 中有 report.docx 和 report.pdf。"""
        report_id = first_save_result["report_id"]
        files = neolyst_client.storage.from_("reports").list(f"{report_id}/v1")
        names = [f["name"] for f in files]
        assert "report.docx" in names
        assert "report.pdf" in names


class TestSaveDraftSecondVersion:
    def test_same_report_id(self, first_save_result, second_save_result):
        """第二次保存沿用同一 report_id。"""
        assert second_save_result["report_id"] == first_save_result["report_id"]

    def test_version_no_incremented(self, second_save_result):
        """第二次保存 version_no == 2。"""
        assert second_save_result["version_no"] == 2

    def test_report_current_version_updated(self, neolyst_client, second_save_result):
        """report.current_version_no 更新为 2，title 和 rating 为新值。"""
        resp = (
            neolyst_client.table("report")
            .select("current_version_no, title, rating")
            .eq("id", second_save_result["report_id"])
            .execute()
        )
        record = resp.data[0]
        assert record["current_version_no"] == 2
        assert record["title"] == "Test Draft Report Iter4 v2"
        assert record["rating"] == "OUTPERFORM"

    def test_v2_files_in_separate_dir(self, neolyst_client, second_save_result):
        """v2 文件存储在 v2/ 目录，不覆盖 v1/ 文件。"""
        report_id = second_save_result["report_id"]
        files_v2 = neolyst_client.storage.from_("reports").list(f"{report_id}/v2")
        names = [f["name"] for f in files_v2]
        assert "report.docx" in names
        assert "report.pdf" in names


# ── error cases ──────────────────────────────────────────────────────

class TestSaveDraftErrors:
    def test_missing_title_raises(self, neolyst_client, tmp_path):
        """title 为 None 时 NOT NULL 违规，包装为 ValueError。"""
        from skills.neolyst.scripts import draft_report

        word = tmp_path / "r.docx"
        word.write_bytes(b"x")
        pdf = tmp_path / "r.pdf"
        pdf.write_bytes(b"x")

        with pytest.raises(ValueError):
            draft_report.save_draft_report(neolyst_client, {
                "report_id": None,
                "title": None,
                "report_type": "company",
                "report_language": "en",
                "analysts": [{"analyst_email": TEST_ANALYST, "author_order": 1}],
                "report_file": str(word),
                "pdf_file": str(pdf),
            })

    def test_empty_analysts_raises(self, neolyst_client, tmp_path):
        """analysts 为空列表时 RPC 抛出"analysts 不能为空"。"""
        from skills.neolyst.scripts import draft_report

        word = tmp_path / "r.docx"
        word.write_bytes(b"x")
        pdf = tmp_path / "r.pdf"
        pdf.write_bytes(b"x")

        with pytest.raises(ValueError, match="analysts 不能为空"):
            draft_report.save_draft_report(neolyst_client, {
                "report_id": None,
                "title": "Error Test",
                "report_type": "company",
                "report_language": "en",
                "analysts": [],
                "report_file": str(word),
                "pdf_file": str(pdf),
            })
