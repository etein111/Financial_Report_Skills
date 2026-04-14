"""
test_save_report.py — save_report 集成测试。
"""
import json
import uuid
from pathlib import Path

import pytest

TEST_ANALYST = json.loads((Path(__file__).parent / "test_config.json").read_text())["email"]


@pytest.fixture(scope="module")
def tmp_module_dir(tmp_path_factory):
    return tmp_path_factory.mktemp("save_report")


def _base_payload(**overrides):
    payload = {
        "report_id": None,
        "title": "Test Save Report",
        "report_type": "company",
        "report_language": "en",
        "analysts": [{"analyst_email": TEST_ANALYST, "author_order": 1}],
        "ticker": "TSAVE01",
        "coverage_id": None,
        "rating": None,
        "target_price": None,
        "region_code": None,
        "sector_id": None,
        "contact_person": None,
        "investment_thesis": None,
        "report_file": "/tmp/ignored.docx",
        "pdf_file": "/tmp/ignored.pdf",
        "model_file": "/tmp/ignored.xlsx",
    }
    payload.update(overrides)
    return payload


class TestSaveReport:
    def test_returns_report_id_uuid(self, neolyst_client):
        from skills.neolyst.scripts import save_report

        result = save_report.save_report(neolyst_client, _base_payload())
        try:
            assert result["report_id"]
            uuid.UUID(result["report_id"])
        finally:
            neolyst_client.table("report").delete().eq("id", result["report_id"]).execute()

    def test_new_report_has_null_paths(self, neolyst_client):
        from skills.neolyst.scripts import save_report

        result = save_report.save_report(neolyst_client, _base_payload(title="Null Paths Test"))
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

    def test_update_metadata_keeps_existing_paths(self, neolyst_client, tmp_path):
        from skills.neolyst.scripts import save_report, upload_files

        word = tmp_path / "report.docx"
        pdf = tmp_path / "report.pdf"
        model = tmp_path / "model.xlsx"
        word.write_bytes(b"fake docx")
        pdf.write_bytes(b"fake pdf")
        model.write_bytes(b"fake xlsx")

        first = save_report.save_report(neolyst_client, _base_payload(title="Initial Title"))
        report_id = first["report_id"]
        try:
            uploaded = upload_files.upload_report_files(neolyst_client, report_id, str(word), str(pdf))
            model_uploaded = upload_files.upload_model_file(neolyst_client, report_id, str(model))

            save_report.save_report(neolyst_client, _base_payload(
                report_id=report_id,
                title="Updated Title",
                rating="OUTPERFORM",
                contact_person=TEST_ANALYST,
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
    def test_missing_title_raises(self, neolyst_client):
        from skills.neolyst.scripts import save_report

        with pytest.raises(ValueError):
            save_report.save_report(neolyst_client, _base_payload(title=None))

    def test_empty_analysts_raises(self, neolyst_client):
        from skills.neolyst.scripts import save_report

        with pytest.raises(ValueError, match="analysts 不能为空"):
            save_report.save_report(neolyst_client, _base_payload(analysts=[]))
