"""
test_submit_report.py — submit_report 集成测试。
"""
import uuid
import pytest


@pytest.fixture(scope="module")
def submit_coverage_id(neolyst_client, test_sector_id, test_analyst_email):
    from skills.neolyst.scripts import coverage as cov

    _suffix = uuid.uuid4().hex[:6].upper()
    cov_id = cov.create_coverage(
        neolyst_client,
        ticker=f"SUB{_suffix}",
        english_name=f"Submit Test Co {_suffix}",
        sector_id=test_sector_id,
        isin=f"HK{_suffix}{'0' * (10 - len(_suffix))}",
        country_of_domicile="Hong Kong",
        analysts=[{"analyst_email": test_analyst_email, "author_order": 1}],
    )
    yield cov_id
    neolyst_client.table("coverage").delete().eq("id", cov_id).execute()


@pytest.fixture(scope="module")
def submitted_report(neolyst_client, submit_coverage_id, test_analyst_email, tmp_path_factory):
    from skills.neolyst.scripts.report import submit_report as sr

    d = tmp_path_factory.mktemp("submit_test")
    result = _create_submitted_report(
        neolyst_client, submit_coverage_id, d,
        "Submit Test Report", test_analyst_email,
    )
    yield result
    neolyst_client.table("report").delete().eq("id", result["report_id"]).execute()


class TestSubmitReport:
    def test_returns_report_id_uuid(self, submitted_report):
        uuid.UUID(submitted_report["report_id"])
        assert submitted_report["status"] == "submitted"

    def test_report_status_updated_in_db(self, neolyst_client, submitted_report):
        resp = (
            neolyst_client.table("report")
            .select("status")
            .eq("id", submitted_report["report_id"])
            .execute()
        )
        assert resp.data[0]["status"] == "submitted"

    def test_status_log_created(self, neolyst_client, submitted_report):
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
        assert log["metadata"]["title"] == "Submit Test Report"
        assert log["metadata"]["word_path"]
        assert log["metadata"]["pdf_path"]

    def test_submit_already_submitted_raises(self, neolyst_client, submitted_report):
        from skills.neolyst.scripts.report import submit_report as sr

        with pytest.raises(ValueError):
            sr(
                neolyst_client,
                submitted_report["report_id"],
            )

    def test_submit_without_word_path_raises(self, neolyst_client, submit_coverage_id, test_analyst_email, tmp_path):
        from skills.neolyst.scripts.report import save_report
        from skills.neolyst.scripts import upload_files
        from skills.neolyst.scripts.report import submit_report as sr

        word_path, pdf_path = _make_files(tmp_path)
        saved = save_report(neolyst_client, _base_report_payload(
            test_analyst_email,
            title="Submit Missing Word",
            ticker="SUBWORD",
            investment_thesis="Test investment thesis",
            coverage_id=submit_coverage_id,
        ))
        try:
            upload_files.upload_report_files(neolyst_client, saved["report_id"], word_path, pdf_path)
            neolyst_client.table("report").update({"word_path": None}).eq("id", saved["report_id"]).execute()
            with pytest.raises(ValueError, match="Word"):
                sr(neolyst_client, saved["report_id"])
        finally:
            neolyst_client.table("report").delete().eq("id", saved["report_id"]).execute()

    def test_submit_without_pdf_path_raises(self, neolyst_client, submit_coverage_id, test_analyst_email, tmp_path):
        from skills.neolyst.scripts.report import save_report
        from skills.neolyst.scripts import upload_files
        from skills.neolyst.scripts.report import submit_report as sr

        word_path, pdf_path = _make_files(tmp_path)
        saved = save_report(neolyst_client, _base_report_payload(
            test_analyst_email,
            title="Submit Missing PDF",
            ticker="SUBPDF",
            investment_thesis="Test investment thesis",
            coverage_id=submit_coverage_id,
        ))
        try:
            upload_files.upload_report_files(neolyst_client, saved["report_id"], word_path, pdf_path)
            neolyst_client.table("report").update({"pdf_path": None}).eq("id", saved["report_id"]).execute()
            with pytest.raises(ValueError, match="PDF"):
                sr(neolyst_client, saved["report_id"])
        finally:
            neolyst_client.table("report").delete().eq("id", saved["report_id"]).execute()

    def test_submit_missing_investment_thesis_raises(
        self, neolyst_client, submit_coverage_id, test_analyst_email, tmp_path
    ):
        from skills.neolyst.scripts.report import save_report
        from skills.neolyst.scripts import upload_files
        from skills.neolyst.scripts.report import submit_report as sr

        word_path, pdf_path = _make_files(tmp_path)
        saved = save_report(neolyst_client, _base_report_payload(
            test_analyst_email,
            title="Validate Gate Test",
            ticker="VGATE",
            investment_thesis="initial thesis",
            coverage_id=submit_coverage_id,
        ))
        try:
            upload_files.upload_report_files(neolyst_client, saved["report_id"], word_path, pdf_path)
            neolyst_client.table("report").update(
                {"investment_thesis": None}
            ).eq("id", saved["report_id"]).execute()
            with pytest.raises(ValueError, match="投资论点"):
                sr(neolyst_client, saved["report_id"])
        finally:
            neolyst_client.table("report").delete().eq(
                "id", saved["report_id"]
            ).execute()

    def test_submit_company_without_coverage_raises(
        self, neolyst_client, submit_coverage_id, test_analyst_email, tmp_path
    ):
        from skills.neolyst.scripts.report import save_report
        from skills.neolyst.scripts import upload_files
        from skills.neolyst.scripts.report import submit_report as sr

        word_path, pdf_path = _make_files(tmp_path)
        saved = save_report(neolyst_client, _base_report_payload(
            test_analyst_email,
            title="Coverage Gate Test",
            ticker="CGATE",
            investment_thesis="test thesis",
            coverage_id=submit_coverage_id,
        ))
        try:
            upload_files.upload_report_files(neolyst_client, saved["report_id"], word_path, pdf_path)
            neolyst_client.table("report").update(
                {"coverage_id": None}
            ).eq("id", saved["report_id"]).execute()
            with pytest.raises(ValueError, match="coverage_id"):
                sr(neolyst_client, saved["report_id"])
        finally:
            neolyst_client.table("report").delete().eq(
                "id", saved["report_id"]
            ).execute()
