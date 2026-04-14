"""
test_publish_report.py — publish_report 集成测试。
"""
import uuid
import pytest


@pytest.fixture(scope="module")
def publish_coverage_id(neolyst_client, test_sector_id, test_analyst_email):
    from skills.neolyst.scripts import coverage as cov

    _suffix = uuid.uuid4().hex[:6].upper()
    cov_id = cov.create_coverage(
        neolyst_client,
        ticker=f"PUB{_suffix}",
        english_name=f"Publish Test Co {_suffix}",
        sector_id=test_sector_id,
        isin=f"HK{_suffix}{'0' * (10 - len(_suffix))}",
        country_of_domicile="Hong Kong",
        analysts=[{"analyst_email": test_analyst_email, "author_order": 1}],
    )
    yield cov_id
    neolyst_client.table("coverage").delete().eq("id", cov_id).execute()


class TestPublishReport:
    def test_publish_submitted_report(self, neolyst_client, publish_coverage_id, test_analyst_email, tmp_path):
        from skills.neolyst.scripts.report import publish_report as pr

        submitted = _create_submitted_report(
            neolyst_client, publish_coverage_id, tmp_path / "publish_happy",
            "Publish Test", test_analyst_email,
        )
        report_id = submitted["report_id"]

        try:
            result = pr(neolyst_client, report_id)

            assert result["status"] == "published"
            uuid.UUID(result["report_id"])

            resp = (
                neolyst_client.table("report")
                .select("status, published_by, published_at")
                .eq("id", report_id)
                .execute()
            )
            assert resp.data[0]["status"] == "published"
            assert resp.data[0]["published_by"] is not None
            assert resp.data[0]["published_at"] is not None

            log_resp = (
                neolyst_client.table("report_status_log")
                .select("*")
                .eq("report_id", report_id)
                .eq("to_status", "published")
                .execute()
            )
            assert log_resp.data
            log = log_resp.data[0]
            assert log["from_status"] == "submitted"
            assert log["to_status"] == "published"
        finally:
            neolyst_client.table("report").delete().eq("id", report_id).execute()


class TestPublishEdgeCases:
    def test_publish_draft_raises(self, neolyst_client, publish_coverage_id, test_analyst_email, tmp_path):
        from skills.neolyst.scripts.report import save_report
        from skills.neolyst.scripts.report import publish_report as pr

        saved = save_report(neolyst_client, _base_report_payload(
            test_analyst_email,
            title="Publish Draft Test",
            ticker="PUBDRAFT",
            investment_thesis="Test investment thesis",
            coverage_id=publish_coverage_id,
            rating="OUTPERFORM",
            target_price=100.0,
        ))
        try:
            with pytest.raises(ValueError, match="无法发布"):
                pr(neolyst_client, saved["report_id"])
        finally:
            neolyst_client.table("report").delete().eq("id", saved["report_id"]).execute()

    def test_publish_nonexistent_report_raises(self, neolyst_client):
        from skills.neolyst.scripts.report import publish_report as pr

        with pytest.raises(ValueError, match="报告不存在"):
            pr(neolyst_client, str(uuid.uuid4()))
