"""
test_reject_report.py — reject_report 集成测试。
"""
import uuid
import pytest

from .conftest import _base_report_payload, _create_submitted_report


@pytest.fixture(scope="module")
def reject_coverage_id(neolyst_client, test_sector_id, test_analyst_email):
    from skills.neolyst.scripts import coverage as cov

    _suffix = uuid.uuid4().hex[:6].upper()
    cov_id = cov.create_coverage(
        neolyst_client,
        ticker=f"REJ{_suffix}",
        english_name=f"Reject Test Co {_suffix}",
        sector_id=test_sector_id,
        isin=f"HK{_suffix}{'0' * (10 - len(_suffix))}",
        country_of_domicile="Hong Kong",
        analysts=[{"analyst_email": test_analyst_email, "author_order": 1}],
    )
    yield cov_id
    neolyst_client.table("coverage").delete().eq("id", cov_id).execute()


class TestRejectReport:
    def test_reject_submitted_report(self, neolyst_client, reject_coverage_id, test_analyst_email, tmp_path):
        from skills.neolyst.scripts.report import reject_report as rr

        submitted = _create_submitted_report(
            neolyst_client, reject_coverage_id, tmp_path / "reject_happy",
            "Reject Test", test_analyst_email,
        )
        report_id = submitted["report_id"]

        try:
            result = rr(neolyst_client, report_id, "数据不完整")

            assert result["status"] == "rejected"
            uuid.UUID(result["report_id"])

            resp = (
                neolyst_client.table("report")
                .select("status, rejection_reason")
                .eq("id", report_id)
                .execute()
            )
            assert resp.data[0]["status"] == "rejected"
            assert resp.data[0]["rejection_reason"] == "数据不完整"

            log_resp = (
                neolyst_client.table("report_status_log")
                .select("*")
                .eq("report_id", report_id)
                .eq("to_status", "rejected")
                .execute()
            )
            assert log_resp.data
            log = log_resp.data[0]
            assert log["from_status"] == "submitted"
            assert log["to_status"] == "rejected"
            assert log["reason"] == "数据不完整"
        finally:
            neolyst_client.table("report").delete().eq("id", report_id).execute()


class TestRejectEdgeCases:
    def test_reject_draft_raises(self, neolyst_client, reject_coverage_id, test_analyst_email, tmp_path):
        from skills.neolyst.scripts.report import save_report
        from skills.neolyst.scripts.report import reject_report as rr

        saved = save_report(neolyst_client, _base_report_payload(
            test_analyst_email,
            title="Reject Draft Test",
            ticker="REJDRAFT",
            investment_thesis="Test investment thesis",
            coverage_id=reject_coverage_id,
            rating="OUTPERFORM",
            target_price=100.0,
        ))
        try:
            with pytest.raises(ValueError, match="无法退回"):
                rr(neolyst_client, saved["report_id"], "不应退回 draft")
        finally:
            neolyst_client.table("report").delete().eq("id", saved["report_id"]).execute()

    def test_reject_without_reason_raises(self, neolyst_client, reject_coverage_id, test_analyst_email, tmp_path):
        from skills.neolyst.scripts.report import reject_report as rr

        submitted = _create_submitted_report(
            neolyst_client, reject_coverage_id, tmp_path / "no_reason",
            "No Reason Test", test_analyst_email,
        )
        report_id = submitted["report_id"]

        try:
            with pytest.raises(ValueError, match="退回原因不能为空"):
                rr(neolyst_client, report_id, "")
        finally:
            neolyst_client.table("report").delete().eq("id", report_id).execute()

    def test_reject_nonexistent_report_raises(self, neolyst_client):
        from skills.neolyst.scripts.report import reject_report as rr

        with pytest.raises(ValueError, match="报告不存在"):
            rr(neolyst_client, str(uuid.uuid4()), "some reason")
