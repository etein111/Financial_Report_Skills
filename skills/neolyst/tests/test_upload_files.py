"""
test_upload_files.py — upload_report_files / upload_model_file 集成测试。
"""
import json
import re
import time
from pathlib import Path

TEST_ANALYST = json.loads((Path(__file__).parent / "test_config.json").read_text())["email"]


def _make_files(directory: Path, prefix: str = "report") -> tuple[str, str, str]:
    directory.mkdir(parents=True, exist_ok=True)
    word = directory / f"{prefix}.docx"
    pdf = directory / f"{prefix}.pdf"
    model = directory / f"{prefix}.xlsx"
    word.write_bytes(b"fake docx")
    pdf.write_bytes(b"fake pdf")
    model.write_bytes(b"fake xlsx")
    return str(word), str(pdf), str(model)


def _create_report(client):
    from skills.neolyst.scripts import save_report

    return save_report.save_report(client, {
        "report_id": None,
        "title": "Upload Files Test",
        "report_type": "company",
        "report_language": "en",
        "analysts": [{"analyst_email": TEST_ANALYST, "author_order": 1}],
        "ticker": "UPLD001",
        "coverage_id": None,
        "rating": None,
        "target_price": None,
        "region_code": None,
        "sector_id": None,
        "contact_person": TEST_ANALYST,
        "investment_thesis": "upload test thesis",
    })["report_id"]


def _strip_bucket(storage_path: str) -> str:
    return storage_path.split("/", 1)[1]


def test_upload_report_files_updates_report_and_storage(neolyst_client, tmp_path):
    from skills.neolyst.scripts import upload_files

    report_id = _create_report(neolyst_client)
    word, pdf, _ = _make_files(tmp_path / "docs")
    try:
        result = upload_files.upload_report_files(neolyst_client, report_id, word, pdf)
        assert re.match(rf"^reports/{report_id}/report/\d{{8}}_\d{{6}}/report\.docx$", result["word_path"])
        assert re.match(rf"^reports/{report_id}/report/\d{{8}}_\d{{6}}/report\.pdf$", result["pdf_path"])
        assert result["word_path"].rsplit("/", 1)[0] == result["pdf_path"].rsplit("/", 1)[0]

        row = (
            neolyst_client.table("report")
            .select("word_path, pdf_path")
            .eq("id", report_id)
            .execute()
            .data[0]
        )
        assert row["word_path"] == result["word_path"]
        assert row["pdf_path"] == result["pdf_path"]

        prefix = _strip_bucket(result["word_path"]).rsplit("/", 1)[0]
        names = [item["name"] for item in neolyst_client.storage.from_("reports").list(prefix)]
        assert "report.docx" in names
        assert "report.pdf" in names
    finally:
        neolyst_client.table("report").delete().eq("id", report_id).execute()


def test_upload_model_file_updates_only_model_path(neolyst_client, tmp_path):
    from skills.neolyst.scripts import upload_files

    report_id = _create_report(neolyst_client)
    word, pdf, model = _make_files(tmp_path / "model")
    try:
        docs = upload_files.upload_report_files(neolyst_client, report_id, word, pdf)
        uploaded_model = upload_files.upload_model_file(neolyst_client, report_id, model)

        row = (
            neolyst_client.table("report")
            .select("word_path, pdf_path, model_path")
            .eq("id", report_id)
            .execute()
            .data[0]
        )
        assert row["word_path"] == docs["word_path"]
        assert row["pdf_path"] == docs["pdf_path"]
        assert row["model_path"] == uploaded_model["model_path"]
        assert re.match(rf"^reports/{report_id}/model/\d{{8}}_\d{{6}}/report\.xlsx$", uploaded_model["model_path"])
    finally:
        neolyst_client.table("report").delete().eq("id", report_id).execute()


def test_reupload_keeps_old_storage_objects(neolyst_client, tmp_path):
    from skills.neolyst.scripts import upload_files

    report_id = _create_report(neolyst_client)
    first_word, first_pdf, _ = _make_files(tmp_path / "first", "first_report")
    second_word, second_pdf, _ = _make_files(tmp_path / "second", "second_report")
    try:
        first = upload_files.upload_report_files(neolyst_client, report_id, first_word, first_pdf)
        time.sleep(1.1)
        second = upload_files.upload_report_files(neolyst_client, report_id, second_word, second_pdf)

        assert first["word_path"] != second["word_path"]
        assert first["pdf_path"] != second["pdf_path"]

        first_prefix = _strip_bucket(first["word_path"]).rsplit("/", 1)[0]
        second_prefix = _strip_bucket(second["word_path"]).rsplit("/", 1)[0]
        first_names = [item["name"] for item in neolyst_client.storage.from_("reports").list(first_prefix)]
        second_names = [item["name"] for item in neolyst_client.storage.from_("reports").list(second_prefix)]
        assert "first_report.docx" in first_names
        assert "second_report.docx" in second_names
    finally:
        neolyst_client.table("report").delete().eq("id", report_id).execute()
