"""
test_validators.py — validate_report 集成测试。
"""
import json
import uuid
from pathlib import Path

import pytest

TEST_ANALYST = json.loads((Path(__file__).parent / "test_config.json").read_text())["email"]


# ── helpers ──────────────────────────────────────────────────────────

def _make_files(directory: Path) -> tuple[str, str]:
    word = directory / "report.docx"
    pdf = directory / "report.pdf"
    word.write_bytes(b"fake docx")
    pdf.write_bytes(b"fake pdf")
    return str(word), str(pdf)


def _save_report_with_files(client, directory, overrides=None):
    from skills.neolyst.scripts import save_report, upload_files

    word_path, pdf_path = _make_files(directory)
    base = {
        "report_id": None,
        "title": "Validator Test Report",
        "report_type": "company",
        "report_language": "zh",
        "investment_thesis": "test thesis",
        "contact_person": TEST_ANALYST,
        "analysts": [{"analyst_email": TEST_ANALYST, "author_order": 1}],
        "ticker": "VTEST01",
        "coverage_id": None,
        "sector_id": None,
        "region_code": None,
        "rating": None,
        "target_price": None,
    }
    if overrides:
        base.update(overrides)

    saved = save_report.save_report(client, base)
    upload_files.upload_report_files(client, saved["report_id"], word_path, pdf_path)
    return saved


def _cleanup(client, report_id):
    client.table("report").delete().eq("id", report_id).execute()


# ── module fixtures ───────────────────────────────────────────────────

@pytest.fixture(scope="module")
def test_coverage_id(neolyst_client):
    from skills.neolyst.scripts import coverage as cov

    _suffix = uuid.uuid4().hex[:6].upper()
    sector_resp = neolyst_client.table("sector").select("id").eq("is_active", True).limit(1).execute()
    sector_id = sector_resp.data[0]["id"]

    cov_id = cov.create_coverage(
        neolyst_client,
        ticker=f"VLD{_suffix}",
        english_name=f"Validator Test Co {_suffix}",
        sector_id=sector_id,
        isin=f"US{_suffix}{'0' * (10 - len(_suffix))}",
        country_of_domicile="China",
        analysts=[{"analyst_email": TEST_ANALYST, "author_order": 1}],
    )
    yield cov_id
    neolyst_client.table("coverage").delete().eq("id", cov_id).execute()


@pytest.fixture(scope="module")
def valid_report(neolyst_client, test_coverage_id, tmp_path_factory):
    d = tmp_path_factory.mktemp("validators_valid")
    result = _save_report_with_files(neolyst_client, d, {"coverage_id": test_coverage_id})
    yield result
    _cleanup(neolyst_client, result["report_id"])


# ── happy path ────────────────────────────────────────────────────────

class TestValidateDraftHappyPath:
    def test_valid_report_passes(self, neolyst_client, valid_report):
        from skills.neolyst.scripts.validators import validate_report

        result = validate_report(
            neolyst_client,
            valid_report["report_id"],
        )
        assert result["report_id"] == valid_report["report_id"]


# ── non-company types ────────────────────────────────────────────────

class TestValidateDraftNonCompanyTypes:
    def test_sector_type_passes_without_coverage_id(self, neolyst_client, tmp_path):
        from skills.neolyst.scripts.validators import validate_report

        result = _save_report_with_files(neolyst_client, tmp_path, {
            "report_type": "sector",
            "coverage_id": None,
        })
        try:
            v = validate_report(neolyst_client, result["report_id"])
            assert v["report_id"] == result["report_id"]
        finally:
            _cleanup(neolyst_client, result["report_id"])

    def test_macro_type_passes_without_coverage_id(self, neolyst_client, tmp_path):
        from skills.neolyst.scripts.validators import validate_report

        result = _save_report_with_files(neolyst_client, tmp_path, {
            "report_type": "macro",
            "coverage_id": None,
        })
        try:
            v = validate_report(neolyst_client, result["report_id"])
            assert v["report_id"] == result["report_id"]
        finally:
            _cleanup(neolyst_client, result["report_id"])


# ── field errors ─────────────────────────────────────────────────────

class TestValidateDraftFieldErrors:
    def test_missing_investment_thesis_fails(self, neolyst_client, test_coverage_id, tmp_path):
        from skills.neolyst.scripts.validators import validate_report

        result = _save_report_with_files(neolyst_client, tmp_path, {
            "investment_thesis": None,
            "coverage_id": test_coverage_id,
        })
        try:
            with pytest.raises(ValueError, match="投资论点"):
                validate_report(neolyst_client, result["report_id"])
        finally:
            _cleanup(neolyst_client, result["report_id"])

    def test_missing_contact_person_fails(self, neolyst_client, test_coverage_id, tmp_path):
        from skills.neolyst.scripts.validators import validate_report

        result = _save_report_with_files(neolyst_client, tmp_path, {
            "contact_person": None,
            "coverage_id": test_coverage_id,
        })
        try:
            with pytest.raises(ValueError, match="联系人"):
                validate_report(neolyst_client, result["report_id"])
        finally:
            _cleanup(neolyst_client, result["report_id"])

    def test_missing_report_language_fails(self, neolyst_client, test_coverage_id, tmp_path):
        from skills.neolyst.scripts.validators import validate_report

        result = _save_report_with_files(neolyst_client, tmp_path, {
            "report_language": None,
            "coverage_id": test_coverage_id,
        })
        try:
            with pytest.raises(ValueError, match="报告语言"):
                validate_report(neolyst_client, result["report_id"])
        finally:
            _cleanup(neolyst_client, result["report_id"])


# ── analyst errors ────────────────────────────────────────────────────

class TestValidateDraftAnalystErrors:
    def test_contact_person_not_in_analysts_fails(self, neolyst_client, test_coverage_id, tmp_path):
        from skills.neolyst.scripts.validators import validate_report

        result = _save_report_with_files(neolyst_client, tmp_path, {
            "contact_person": "nobody@example.com",
            "coverage_id": test_coverage_id,
        })
        try:
            with pytest.raises(ValueError, match="contact_person"):
                validate_report(neolyst_client, result["report_id"])
        finally:
            _cleanup(neolyst_client, result["report_id"])


# ── coverage errors ───────────────────────────────────────────────────

class TestValidateDraftCoverageErrors:
    def test_company_without_coverage_id_fails(self, neolyst_client, tmp_path):
        from skills.neolyst.scripts.validators import validate_report

        result = _save_report_with_files(neolyst_client, tmp_path, {"coverage_id": None})
        try:
            with pytest.raises(ValueError, match="coverage_id"):
                validate_report(neolyst_client, result["report_id"])
        finally:
            _cleanup(neolyst_client, result["report_id"])


# ── path errors ───────────────────────────────────────────────────────

class TestValidateDraftPathErrors:
    def test_missing_word_path_fails(self, neolyst_client, test_coverage_id, tmp_path):
        from skills.neolyst.scripts.validators import validate_report

        result = _save_report_with_files(neolyst_client, tmp_path, {"coverage_id": test_coverage_id})
        try:
            neolyst_client.table("report").update({"word_path": None}).eq("id", result["report_id"]).execute()
            with pytest.raises(ValueError, match="Word"):
                validate_report(neolyst_client, result["report_id"])
        finally:
            _cleanup(neolyst_client, result["report_id"])

    def test_missing_pdf_path_fails(self, neolyst_client, test_coverage_id, tmp_path):
        from skills.neolyst.scripts.validators import validate_report

        result = _save_report_with_files(neolyst_client, tmp_path, {"coverage_id": test_coverage_id})
        try:
            neolyst_client.table("report").update({"pdf_path": None}).eq("id", result["report_id"]).execute()
            with pytest.raises(ValueError, match="PDF"):
                validate_report(neolyst_client, result["report_id"])
        finally:
            _cleanup(neolyst_client, result["report_id"])


# ── status / existence errors ─────────────────────────────────────────

class TestValidateDraftStatusErrors:
    def test_nonexistent_report_raises(self, neolyst_client):
        from skills.neolyst.scripts.validators import validate_report

        with pytest.raises(ValueError, match="报告不存在"):
            validate_report(neolyst_client, str(uuid.uuid4()))
