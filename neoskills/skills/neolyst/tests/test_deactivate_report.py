"""
test_deactivate_report.py — deactivate_report 集成测试。
"""
import uuid
import pytest

from .conftest import _base_report_payload


@pytest.fixture(scope="module")
def deactivate_coverage_id(neolyst_client, test_sector_id, test_analyst_email):
    from skills.neolyst.scripts import coverage as cov

    _suffix = uuid.uuid4().hex[:6].upper()
    cov_id = cov.create_coverage(
        neolyst_client,
        ticker=f"DEACT{_suffix}",
        english_name=f"Deactivate Test Co {_suffix}",
        sector_id=test_sector_id,
        isin=f"HK{_suffix}{'0' * (10 - len(_suffix))}",
        country_of_domicile="Hong Kong",
        analysts=[{"analyst_email": test_analyst_email, "author_order": 1}],
    )
    yield cov_id
    neolyst_client.table("coverage").delete().eq("id", cov_id).execute()


class TestDeactivateReport:
    def test_deactivate_draft_report(self, neolyst_client, deactivate_coverage_id, test_analyst_email):
        from skills.neolyst.scripts.report import save_report
        from skills.neolyst.scripts.report import deactivate_report

        saved = save_report(neolyst_client, _base_report_payload(
            test_analyst_email,
            title="Deactivate Draft Test",
            ticker="DEACT01",
            investment_thesis="Test thesis",
            coverage_id=deactivate_coverage_id,
            rating="OUTPERFORM",
            target_price=100.0,
        ))
        report_id = saved["report_id"]

        try:
            result = deactivate_report(neolyst_client, report_id)

            assert result["report_id"] == report_id
            assert result["is_active"] is False

            resp = (
                neolyst_client.table("report")
                .select("is_active")
                .eq("id", report_id)
                .execute()
            )
            assert resp.data[0]["is_active"] is False
        finally:
            neolyst_client.table("report").delete().eq("id", report_id).execute()

    def test_deactivate_nonexistent_raises(self, neolyst_client):
        from skills.neolyst.scripts.report import deactivate_report

        with pytest.raises(ValueError, match="报告不存在"):
            deactivate_report(neolyst_client, str(uuid.uuid4()))

    def test_deactivate_already_inactive_raises(self, neolyst_client, deactivate_coverage_id, test_analyst_email):
        from skills.neolyst.scripts.report import save_report
        from skills.neolyst.scripts.report import deactivate_report

        saved = save_report(neolyst_client, _base_report_payload(
            test_analyst_email,
            title="Deactivate Twice Test",
            ticker="DEACT02",
            investment_thesis="Test thesis",
            coverage_id=deactivate_coverage_id,
            rating="OUTPERFORM",
            target_price=100.0,
        ))
        report_id = saved["report_id"]

        try:
            deactivate_report(neolyst_client, report_id)
            with pytest.raises(ValueError, match="报告已废弃"):
                deactivate_report(neolyst_client, report_id)
        finally:
            neolyst_client.table("report").delete().eq("id", report_id).execute()
