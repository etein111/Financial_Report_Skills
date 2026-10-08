"""
test_retract_report.py — retract_report 集成测试。
"""
import uuid
import pytest

from .conftest import _base_report_payload, _create_submitted_report


@pytest.fixture(scope="module")
def retract_coverage_id(neolyst_client, test_sector_id, test_analyst_email):
    from skills.neolyst.scripts import coverage as cov

    _suffix = uuid.uuid4().hex[:6].upper()
    cov_id = cov.create_coverage(
        neolyst_client,
        ticker=f"RET{_suffix}",
        english_name=f"Retract Test Co {_suffix}",
        sector_id=test_sector_id,
        isin=f"HK{_suffix}{'0' * (10 - len(_suffix))}",
        country_of_domicile="Hong Kong",
        analysts=[{"analyst_email": test_analyst_email, "author_order": 1}],
    )
    yield cov_id
    neolyst_client.table("coverage").delete().eq("id", cov_id).execute()


class TestRetractSubmittedReport:
    def test_retract_submitted_report(self, neolyst_client, retract_coverage_id, test_analyst_email, tmp_path):
        from skills.neolyst.scripts.report import retract_report as rr

        submitted = _create_submitted_report(
            neolyst_client, retract_coverage_id, tmp_path / "retract_happy",
            "Retract Test", test_analyst_email,
        )
        report_id = submitted["report_id"]

        try:
            result = rr(neolyst_client, report_id)

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
    def test_retract_draft_raises(self, neolyst_client, retract_coverage_id, test_analyst_email, tmp_path):
        from skills.neolyst.scripts.report import save_report
        from skills.neolyst.scripts.report import retract_report as rr

        saved = save_report(neolyst_client, _base_report_payload(
            test_analyst_email,
            title="Retract Draft Test",
            ticker="RETDRAFT",
            investment_thesis="Test investment thesis",
            coverage_id=retract_coverage_id,
            rating="OUTPERFORM",
            target_price=100.0,
        ))
        try:
            with pytest.raises(ValueError, match="无法撤回"):
                rr(neolyst_client, saved["report_id"])
        finally:
            neolyst_client.table("report").delete().eq("id", saved["report_id"]).execute()

    def test_retract_already_retracted_raises(self, neolyst_client, retract_coverage_id, test_analyst_email, tmp_path):
        from skills.neolyst.scripts.report import retract_report as rr

        submitted = _create_submitted_report(
            neolyst_client, retract_coverage_id, tmp_path / "double_retract",
            "Double Retract Test", test_analyst_email,
        )
        report_id = submitted["report_id"]

        try:
            rr(neolyst_client, report_id)
            with pytest.raises(ValueError, match="无法撤回"):
                rr(neolyst_client, report_id)
        finally:
            neolyst_client.table("report").delete().eq("id", report_id).execute()

    def test_retract_nonexistent_report_raises(self, neolyst_client):
        from skills.neolyst.scripts.report import retract_report as rr

        with pytest.raises(ValueError, match="报告不存在"):
            rr(neolyst_client, str(uuid.uuid4()))
