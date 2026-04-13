"""
test_submit_report.py — submit_report 集成测试（5 个）。
"""
import json
import uuid
from pathlib import Path

import pytest

TEST_ANALYST = json.loads((Path(__file__).parent / "test_config.json").read_text())["email"]


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
    result = sr.submit_report(neolyst_client, draft["report_id"])
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
            )

    def test_submit_without_current_version_raises(self, neolyst_client, submit_coverage_id, tmp_path):
        """current_version_no=0 时 submit_report 抛出 ValueError。"""
        from skills.neolyst.scripts import draft_report
        from skills.neolyst.scripts import submit_report as sr

        word_path, pdf_path = _make_files(tmp_path)
        draft = draft_report.save_draft_report(neolyst_client, {
            "report_id": None,
            "title": "Submit No Version",
            "report_type": "company",
            "report_language": "en",
            "investment_thesis": "Test investment thesis",
            "contact_person": TEST_ANALYST,
            "analysts": [{"analyst_email": TEST_ANALYST, "author_order": 1}],
            "ticker": "SUBZERO",
            "coverage_id": submit_coverage_id,
            "sector_id": None,
            "region_code": None,
            "rating": "OUTPERFORM",
            "target_price": 100.0,
            "report_file": word_path,
            "pdf_file": pdf_path,
            "model_file": None,
        })
        try:
            (
                neolyst_client.table("report")
                .update({"current_version_no": 0})
                .eq("id", draft["report_id"])
                .execute()
            )
            with pytest.raises(ValueError, match="当前没有可提交版本"):
                sr.submit_report(neolyst_client, draft["report_id"])
        finally:
            neolyst_client.table("report").delete().eq("id", draft["report_id"]).execute()

    def test_submit_with_missing_current_version_row_raises(self, neolyst_client, submit_coverage_id, tmp_path):
        """current_version_no 指向不存在版本时 submit_report 抛出 ValueError。"""
        from skills.neolyst.scripts import draft_report
        from skills.neolyst.scripts import submit_report as sr

        word_path, pdf_path = _make_files(tmp_path)
        draft = draft_report.save_draft_report(neolyst_client, {
            "report_id": None,
            "title": "Submit Missing Version",
            "report_type": "company",
            "report_language": "en",
            "investment_thesis": "Test investment thesis",
            "contact_person": TEST_ANALYST,
            "analysts": [{"analyst_email": TEST_ANALYST, "author_order": 1}],
            "ticker": "SUBMISS",
            "coverage_id": submit_coverage_id,
            "sector_id": None,
            "region_code": None,
            "rating": "OUTPERFORM",
            "target_price": 100.0,
            "report_file": word_path,
            "pdf_file": pdf_path,
            "model_file": None,
        })
        try:
            (
                neolyst_client.table("report")
                .update({"current_version_no": 999})
                .eq("id", draft["report_id"])
                .execute()
            )
            with pytest.raises(ValueError, match=r"当前版本 v999 不存在"):
                sr.submit_report(neolyst_client, draft["report_id"])
        finally:
            neolyst_client.table("report").delete().eq("id", draft["report_id"]).execute()

    def test_submit_missing_investment_thesis_raises(
        self, neolyst_client, submit_coverage_id, tmp_path
    ):
        """investment_thesis 置 NULL 后直接 submit_report 被 RPC 守门员拦截。"""
        from skills.neolyst.scripts import draft_report
        from skills.neolyst.scripts import submit_report as sr

        word_path, pdf_path = _make_files(tmp_path)
        draft = draft_report.save_draft_report(neolyst_client, {
            "report_id": None,
            "title": "Validate Gate Test",
            "report_type": "company",
            "report_language": "en",
            "investment_thesis": "initial thesis",
            "contact_person": TEST_ANALYST,
            "analysts": [{"analyst_email": TEST_ANALYST, "author_order": 1}],
            "ticker": "VGATE",
            "coverage_id": submit_coverage_id,
            "sector_id": None,
            "region_code": None,
            "rating": None,
            "target_price": None,
            "report_file": word_path,
            "pdf_file": pdf_path,
            "model_file": None,
        })
        try:
            neolyst_client.table("report").update(
                {"investment_thesis": None}
            ).eq("id", draft["report_id"]).execute()
            with pytest.raises(ValueError, match="投资论点"):
                sr.submit_report(neolyst_client, draft["report_id"])
        finally:
            neolyst_client.table("report").delete().eq(
                "id", draft["report_id"]
            ).execute()

    def test_submit_company_without_coverage_raises(
        self, neolyst_client, submit_coverage_id, tmp_path
    ):
        """company 报告 coverage_id 置 NULL 后直接 submit_report 被 RPC 守门员拦截。"""
        from skills.neolyst.scripts import draft_report
        from skills.neolyst.scripts import submit_report as sr

        word_path, pdf_path = _make_files(tmp_path)
        draft = draft_report.save_draft_report(neolyst_client, {
            "report_id": None,
            "title": "Coverage Gate Test",
            "report_type": "company",
            "report_language": "en",
            "investment_thesis": "test thesis",
            "contact_person": TEST_ANALYST,
            "analysts": [{"analyst_email": TEST_ANALYST, "author_order": 1}],
            "ticker": "CGATE",
            "coverage_id": submit_coverage_id,
            "sector_id": None,
            "region_code": None,
            "rating": None,
            "target_price": None,
            "report_file": word_path,
            "pdf_file": pdf_path,
            "model_file": None,
        })
        try:
            neolyst_client.table("report").update(
                {"coverage_id": None}
            ).eq("id", draft["report_id"]).execute()
            with pytest.raises(ValueError, match="coverage_id"):
                sr.submit_report(neolyst_client, draft["report_id"])
        finally:
            neolyst_client.table("report").delete().eq(
                "id", draft["report_id"]
            ).execute()
