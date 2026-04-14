"""
test_retract_report.py — retract_report 集成测试。
"""
import json
import uuid
from pathlib import Path

import pytest

TEST_ANALYST = json.loads((Path(__file__).parent / "test_config.json").read_text())["email"]


def _make_files(directory: Path) -> tuple[str, str]:
    directory.mkdir(parents=True, exist_ok=True)
    word = directory / "report.docx"
    pdf = directory / "report.pdf"
    word.write_bytes(b"fake docx")
    pdf.write_bytes(b"fake pdf")
    return str(word), str(pdf)


def _create_submitted_report(client, coverage_id, tmp_dir, title="Retract Test"):
    from skills.neolyst.scripts import save_report, upload_files
    from skills.neolyst.scripts import submit_report as sr

    word_path, pdf_path = _make_files(tmp_dir)
    saved = save_report.save_report(client, {
        "report_id": None,
        "title": title,
        "report_type": "company",
        "report_language": "en",
        "investment_thesis": "Test investment thesis",
        "contact_person": TEST_ANALYST,
        "analysts": [{"analyst_email": TEST_ANALYST, "author_order": 1}],
        "ticker": title[:8].upper().replace(" ", ""),
        "coverage_id": coverage_id,
        "rating": "OUTPERFORM",
        "target_price": 100.0,
    })
    upload_files.upload_report_files(client, saved["report_id"], word_path, pdf_path)
    return sr.submit_report(client, saved["report_id"])


@pytest.fixture(scope="module")
def retract_coverage_id(neolyst_client):
    from skills.neolyst.scripts import coverage as cov

    _suffix = uuid.uuid4().hex[:6].upper()
    sector_resp = neolyst_client.table("sector").select("id").eq("is_active", True).limit(1).execute()
    sector_id = sector_resp.data[0]["id"]

    cov_id = cov.create_coverage(
        neolyst_client,
        ticker=f"RET{_suffix}",
        english_name=f"Retract Test Co {_suffix}",
        sector_id=sector_id,
        isin=f"HK{_suffix}{'0' * (10 - len(_suffix))}",
        country_of_domicile="Hong Kong",
        analysts=[{"analyst_email": TEST_ANALYST, "author_order": 1}],
    )
    yield cov_id
    neolyst_client.table("coverage").delete().eq("id", cov_id).execute()


class TestRetractSubmittedReport:
    def test_retract_submitted_report(self, neolyst_client, retract_coverage_id, tmp_path):
        from skills.neolyst.scripts import retract_report as rr

        submitted = _create_submitted_report(
            neolyst_client, retract_coverage_id, tmp_path / "retract_happy",
        )
        report_id = submitted["report_id"]

        try:
            result = rr.retract_report(neolyst_client, report_id)

            assert result["status"] == "draft"
            uuid.UUID(result["report_id"])

            resp = (
                neolyst_client.table("report")
                .select("status")
                .eq("id", report_id)
                .execute()
            )
            assert resp.data[0]["status"] == "draft"

            log_resp = (
                neolyst_client.table("report_status_log")
                .select("*")
                .eq("report_id", report_id)
                .eq("to_status", "draft")
                .execute()
            )
            assert log_resp.data
            log = log_resp.data[0]
            assert log["from_status"] == "submitted"
            assert log["to_status"] == "draft"
            assert "@" in (log["action_by_name"] or "")
            assert log["metadata"]
        finally:
            neolyst_client.table("report").delete().eq("id", report_id).execute()


class TestRetractEdgeCases:
    def test_retract_draft_raises(self, neolyst_client, retract_coverage_id, tmp_path):
        from skills.neolyst.scripts import save_report
        from skills.neolyst.scripts import retract_report as rr

        saved = save_report.save_report(neolyst_client, {
            "report_id": None,
            "title": "Retract Draft Test",
            "report_type": "company",
            "report_language": "en",
            "investment_thesis": "Test investment thesis",
            "contact_person": TEST_ANALYST,
            "analysts": [{"analyst_email": TEST_ANALYST, "author_order": 1}],
            "ticker": "RETDRAFT",
            "coverage_id": retract_coverage_id,
            "rating": "OUTPERFORM",
            "target_price": 100.0,
        })
        try:
            with pytest.raises(ValueError, match="无法撤回"):
                rr.retract_report(neolyst_client, saved["report_id"])
        finally:
            neolyst_client.table("report").delete().eq("id", saved["report_id"]).execute()

    def test_retract_already_retracted_raises(self, neolyst_client, retract_coverage_id, tmp_path):
        from skills.neolyst.scripts import retract_report as rr

        submitted = _create_submitted_report(
            neolyst_client, retract_coverage_id, tmp_path / "double_retract",
        )
        report_id = submitted["report_id"]

        try:
            rr.retract_report(neolyst_client, report_id)
            with pytest.raises(ValueError, match="无法撤回"):
                rr.retract_report(neolyst_client, report_id)
        finally:
            neolyst_client.table("report").delete().eq("id", report_id).execute()

    def test_retract_nonexistent_report_raises(self, neolyst_client):
        from skills.neolyst.scripts import retract_report as rr

        with pytest.raises(ValueError, match="报告不存在"):
            rr.retract_report(neolyst_client, str(uuid.uuid4()))
