"""
test_save_report.py — save_report 集成测试。
"""
import uuid
import pytest

from .conftest import _base_report_payload


class TestSaveReport:
    def test_returns_report_id_uuid(self, neolyst_client, test_analyst_email):
        from skills.neolyst.scripts.report import save_report

        result = save_report(neolyst_client, _base_report_payload(
            test_analyst_email,
            title="Test Save Report",
            ticker="TSAVE01",
            report_file="/tmp/ignored.docx",
            pdf_file="/tmp/ignored.pdf",
            model_file="/tmp/ignored.xlsx",
        ))
        try:
            assert result["report_id"]
            uuid.UUID(result["report_id"])
        finally:
            neolyst_client.table("report").delete().eq("id", result["report_id"]).execute()

    def test_new_report_has_null_paths(self, neolyst_client, test_analyst_email):
        from skills.neolyst.scripts.report import save_report

        result = save_report(neolyst_client, _base_report_payload(
            test_analyst_email,
            title="Null Paths Test",
            ticker="TSAVE02",
            report_file="/tmp/ignored.docx",
            pdf_file="/tmp/ignored.pdf",
            model_file="/tmp/ignored.xlsx",
        ))
        try:
            resp = (
                neolyst_client.table("report")
                .select("status, word_path, pdf_path, model_path")
                .eq("id", result["report_id"])
                .execute()
            )
            row = resp.data[0]
            assert row["status"] == "draft"
            assert row["word_path"] is None
            assert row["pdf_path"] is None
            assert row["model_path"] is None
        finally:
            neolyst_client.table("report").delete().eq("id", result["report_id"]).execute()

    def test_update_metadata_keeps_existing_paths(self, neolyst_client, test_analyst_email, tmp_path):
        from skills.neolyst.scripts.report import save_report
        from skills.neolyst.scripts import upload_files

        word = tmp_path / "report.docx"
        pdf = tmp_path / "report.pdf"
        model = tmp_path / "model.xlsx"
        word.write_bytes(b"fake docx")
        pdf.write_bytes(b"fake pdf")
        model.write_bytes(b"fake xlsx")

        first = save_report(neolyst_client, _base_report_payload(
            test_analyst_email,
            title="Initial Title",
            ticker="TSAVE03",
        ))
        report_id = first["report_id"]
        try:
            uploaded = upload_files.upload_report_files(neolyst_client, report_id, str(word), str(pdf))
            model_uploaded = upload_files.upload_model_file(neolyst_client, report_id, str(model))

            save_report(neolyst_client, _base_report_payload(
                test_analyst_email,
                report_id=report_id,
                title="Updated Title",
                ticker="TSAVE03",
                rating="OUTPERFORM",
                investment_thesis="Updated thesis",
            ))

            resp = (
                neolyst_client.table("report")
                .select("title, rating, word_path, pdf_path, model_path")
                .eq("id", report_id)
                .execute()
            )
            row = resp.data[0]
            assert row["title"] == "Updated Title"
            assert row["rating"] == "OUTPERFORM"
            assert row["word_path"] == uploaded["word_path"]
            assert row["pdf_path"] == uploaded["pdf_path"]
            assert row["model_path"] == model_uploaded["model_path"]
        finally:
            neolyst_client.table("report").delete().eq("id", report_id).execute()


class TestSaveReportErrors:
    def test_missing_title_raises(self, neolyst_client, test_analyst_email):
        from skills.neolyst.scripts.report import save_report

        with pytest.raises(ValueError):
            save_report(neolyst_client, _base_report_payload(
                test_analyst_email, title=None,
            ))

    def test_empty_analysts_raises(self, neolyst_client, test_analyst_email):
        from skills.neolyst.scripts.report import save_report

        with pytest.raises(ValueError, match="analysts 不能为空"):
            save_report(neolyst_client, _base_report_payload(
                test_analyst_email, analysts=[],
            ))
