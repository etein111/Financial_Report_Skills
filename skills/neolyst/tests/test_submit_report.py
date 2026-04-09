"""
test_submit_report.py — submit_report 集成测试（5 个）。
"""
import uuid
from pathlib import Path

import pytest

TEST_ANALYST = "yangxue@opendelp.com"


def _make_files(directory: Path) -> tuple[str, str]:
    word = directory / "report.docx"
    pdf = directory / "report.pdf"
    word.write_bytes(b"fake docx")
    pdf.write_bytes(b"fake pdf")
    return str(word), str(pdf)


@pytest.fixture(scope="module")
def submit_coverage_id(neolyst_client):
    from skills.neolyst.scripts import coverage as cov

    _suffix = uuid.uuid4().hex[:6].upper()
    sector_resp = neolyst_client.table("sector").select("id").eq("is_active", True).limit(1).execute()
    sector_id = sector_resp.data[0]["id"]

    cov_id = cov.create_coverage(
        neolyst_client,
        ticker=f"SUB{_suffix}",
        english_name=f"Submit Test Co {_suffix}",
        sector_id=sector_id,
        isin=f"HK{_suffix}{'0' * (10 - len(_suffix))}",
        country_of_domicile="Hong Kong",
        analysts=[{"analyst_email": TEST_ANALYST, "author_order": 1}],
    )
    yield cov_id
    neolyst_client.table("coverage").delete().eq("id", cov_id).execute()


@pytest.fixture(scope="module")
def submitted_report(neolyst_client, submit_coverage_id, tmp_path_factory):
    """首次提交合法报告，模块结束后清理。"""
    from skills.neolyst.scripts import draft_report
    from skills.neolyst.scripts import submit_report as sr

    d = tmp_path_factory.mktemp("submit_test")
    word_path, pdf_path = _make_files(d)
    draft = draft_report.save_draft_report(neolyst_client, {
        "report_id": None,
        "title": "Submit Test Report",
        "report_type": "company",
        "report_language": "en",
        "investment_thesis": "Test investment thesis",
        "contact_person": TEST_ANALYST,
        "analysts": [{"analyst_email": TEST_ANALYST, "author_order": 1}],
        "ticker": "SUBTEST",
        "coverage_id": submit_coverage_id,
        "sector_id": None,
        "region_code": None,
        "rating": "OUTPERFORM",
        "target_price": 100.0,
        "report_file": word_path,
        "pdf_file": pdf_path,
        "model_file": None,
    })
    result = sr.submit_report(neolyst_client, draft["report_id"], draft["version_no"])
    yield result
    neolyst_client.table("report").delete().eq("id", result["report_id"]).execute()


class TestSubmitReport:
    def test_returns_submitted_status(self, submitted_report):
        """submit_report 返回 status == 'submitted'。"""
        assert submitted_report["status"] == "submitted"

    def test_returns_report_id_and_version(self, submitted_report):
        """返回合法 UUID report_id 和 version_no == 1。"""
        uuid.UUID(submitted_report["report_id"])
        assert submitted_report["version_no"] == 1

    def test_report_status_updated_in_db(self, neolyst_client, submitted_report):
        """report 表中 status 更新为 submitted。"""
        resp = (
            neolyst_client.table("report")
            .select("status")
            .eq("id", submitted_report["report_id"])
            .execute()
        )
        assert resp.data[0]["status"] == "submitted"

    def test_status_log_created(self, neolyst_client, submitted_report):
        """report_status_log 有 draft→submitted 记录，action_by_name 为邮箱。"""
        resp = (
            neolyst_client.table("report_status_log")
            .select("*")
            .eq("report_id", submitted_report["report_id"])
            .execute()
        )
        assert resp.data
        log = resp.data[0]
        assert log["from_status"] == "draft"
        assert log["to_status"] == "submitted"
        assert log["version_no"] == 1
        assert "@" in (log["action_by_name"] or "")

    def test_submit_already_submitted_raises(self, neolyst_client, submitted_report):
        """对已 submitted 的报告再次调用 submit_report 抛出 ValueError。"""
        from skills.neolyst.scripts import submit_report as sr

        with pytest.raises(ValueError):
            sr.submit_report(
                neolyst_client,
                submitted_report["report_id"],
                submitted_report["version_no"],
            )
