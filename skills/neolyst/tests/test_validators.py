"""
test_validators.py — validate_draft 集成测试（11 个）。
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


def _save_draft(client, directory, overrides=None):
    from skills.neolyst.scripts import draft_report

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
        "report_file": word_path,
        "pdf_file": pdf_path,
        "model_file": None,
    }
    if overrides:
        base.update(overrides)
    return draft_report.save_draft_report(client, base)


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
    """完整合法的 company draft（含 coverage_id）。模块结束后清理。"""
    d = tmp_path_factory.mktemp("validators_valid")
    result = _save_draft(neolyst_client, d, {"coverage_id": test_coverage_id})
    yield result
    _cleanup(neolyst_client, result["report_id"])


# ── happy path ────────────────────────────────────────────────────────

class TestValidateDraftHappyPath:
    def test_valid_report_passes(self, neolyst_client, valid_report):
        """完整合法 draft 通过校验，返回 {report_id, version_no}。"""
        from skills.neolyst.scripts.validators import validate_draft

        result = validate_draft(
            neolyst_client,
            valid_report["report_id"],
        )
        assert result["report_id"] == valid_report["report_id"]
        assert result["version_no"] == valid_report["version_no"]


# ── non-company types ────────────────────────────────────────────────

class TestValidateDraftNonCompanyTypes:
    def test_sector_type_passes_without_coverage_id(self, neolyst_client, tmp_path):
        """sector 类型不要求 coverage_id，校验通过。"""
        from skills.neolyst.scripts.validators import validate_draft

        result = _save_draft(neolyst_client, tmp_path, {
            "report_type": "sector",
            "coverage_id": None,
        })
        try:
            v = validate_draft(neolyst_client, result["report_id"])
            assert v["report_id"] == result["report_id"]
        finally:
            _cleanup(neolyst_client, result["report_id"])

    def test_macro_type_passes_without_coverage_id(self, neolyst_client, tmp_path):
        """macro 类型不要求 coverage_id，校验通过。"""
        from skills.neolyst.scripts.validators import validate_draft

        result = _save_draft(neolyst_client, tmp_path, {
            "report_type": "macro",
            "coverage_id": None,
        })
        try:
            v = validate_draft(neolyst_client, result["report_id"])
            assert v["report_id"] == result["report_id"]
        finally:
            _cleanup(neolyst_client, result["report_id"])


# ── field errors ─────────────────────────────────────────────────────

class TestValidateDraftFieldErrors:
    def test_missing_investment_thesis_fails(self, neolyst_client, test_coverage_id, tmp_path):
        """investment_thesis 为 None 时校验失败，错误含"投资论点"。"""
        from skills.neolyst.scripts.validators import validate_draft

        result = _save_draft(neolyst_client, tmp_path, {
            "investment_thesis": None,
            "coverage_id": test_coverage_id,
        })
        try:
            with pytest.raises(ValueError, match="投资论点"):
                validate_draft(neolyst_client, result["report_id"])
        finally:
            _cleanup(neolyst_client, result["report_id"])

    def test_missing_contact_person_fails(self, neolyst_client, test_coverage_id, tmp_path):
        """contact_person 为 None 时校验失败，错误含"联系人"。"""
        from skills.neolyst.scripts.validators import validate_draft

        result = _save_draft(neolyst_client, tmp_path, {
            "contact_person": None,
            "coverage_id": test_coverage_id,
        })
        try:
            with pytest.raises(ValueError, match="联系人"):
                validate_draft(neolyst_client, result["report_id"])
        finally:
            _cleanup(neolyst_client, result["report_id"])

    def test_missing_report_language_fails(self, neolyst_client, test_coverage_id, tmp_path):
        """report_language 为 None 时校验失败，错误含"报告语言"。"""
        from skills.neolyst.scripts.validators import validate_draft

        result = _save_draft(neolyst_client, tmp_path, {
            "report_language": None,
            "coverage_id": test_coverage_id,
        })
        try:
            with pytest.raises(ValueError, match="报告语言"):
                validate_draft(neolyst_client, result["report_id"])
        finally:
            _cleanup(neolyst_client, result["report_id"])


# ── analyst errors ────────────────────────────────────────────────────

class TestValidateDraftAnalystErrors:
    def test_contact_person_not_in_analysts_fails(self, neolyst_client, test_coverage_id, tmp_path):
        """contact_person 不在 analysts 列表中时校验失败。"""
        from skills.neolyst.scripts.validators import validate_draft

        result = _save_draft(neolyst_client, tmp_path, {
            "contact_person": "nobody@example.com",
            "coverage_id": test_coverage_id,
        })
        try:
            with pytest.raises(ValueError, match="contact_person"):
                validate_draft(neolyst_client, result["report_id"])
        finally:
            _cleanup(neolyst_client, result["report_id"])


# ── coverage errors ───────────────────────────────────────────────────

class TestValidateDraftCoverageErrors:
    def test_company_without_coverage_id_fails(self, neolyst_client, tmp_path):
        """company 类型不填 coverage_id 时校验失败，错误含"coverage_id"。"""
        from skills.neolyst.scripts.validators import validate_draft

        result = _save_draft(neolyst_client, tmp_path, {"coverage_id": None})
        try:
            with pytest.raises(ValueError, match="coverage_id"):
                validate_draft(neolyst_client, result["report_id"])
        finally:
            _cleanup(neolyst_client, result["report_id"])


# ── version / file errors ─────────────────────────────────────────────

class TestValidateDraftVersionErrors:
    def test_current_version_zero_fails(self, neolyst_client, test_coverage_id, tmp_path):
        """current_version_no=0 时校验失败，错误含"当前没有可校验版本"。"""
        from skills.neolyst.scripts.validators import validate_draft

        result = _save_draft(neolyst_client, tmp_path, {"coverage_id": test_coverage_id})
        try:
            (
                neolyst_client.table("report")
                .update({"current_version_no": 0})
                .eq("id", result["report_id"])
                .execute()
            )
            with pytest.raises(ValueError, match="当前没有可校验版本"):
                validate_draft(neolyst_client, result["report_id"])
        finally:
            _cleanup(neolyst_client, result["report_id"])

    def test_current_version_missing_row_fails(self, neolyst_client, test_coverage_id, tmp_path):
        """current_version_no 指向不存在的 report_version 时校验失败。"""
        from skills.neolyst.scripts.validators import validate_draft

        result = _save_draft(neolyst_client, tmp_path, {"coverage_id": test_coverage_id})
        try:
            (
                neolyst_client.table("report")
                .update({"current_version_no": 999})
                .eq("id", result["report_id"])
                .execute()
            )
            with pytest.raises(ValueError, match=r"当前版本 v999 不存在"):
                validate_draft(neolyst_client, result["report_id"])
        finally:
            _cleanup(neolyst_client, result["report_id"])

    def test_missing_pdf_file_fails(self, neolyst_client, test_coverage_id, tmp_path):
        """pdf_file 未上传（pdf_file_path 为 None）时校验失败，错误含"PDF"。"""
        from skills.neolyst.scripts import draft_report
        from skills.neolyst.scripts.validators import validate_draft

        word = tmp_path / "report.docx"
        word.write_bytes(b"fake docx")
        result = draft_report.save_draft_report(neolyst_client, {
            "report_id": None,
            "title": "PDF Missing Test",
            "report_type": "company",
            "report_language": "zh",
            "investment_thesis": "test",
            "contact_person": TEST_ANALYST,
            "analysts": [{"analyst_email": TEST_ANALYST, "author_order": 1}],
            "coverage_id": test_coverage_id,
            "ticker": None,
            "sector_id": None,
            "region_code": None,
            "rating": None,
            "target_price": None,
            "report_file": str(word),
            "pdf_file": None,
            "model_file": None,
        })
        try:
            with pytest.raises(ValueError, match="PDF"):
                validate_draft(neolyst_client, result["report_id"])
        finally:
            _cleanup(neolyst_client, result["report_id"])


# ── status / existence errors ─────────────────────────────────────────

class TestValidateDraftStatusErrors:
    def test_nonexistent_report_raises(self, neolyst_client):
        """不存在的 report_id 直接抛出 ValueError（含"报告不存在"）。"""
        from skills.neolyst.scripts.validators import validate_draft

        with pytest.raises(ValueError, match="报告不存在"):
            validate_draft(neolyst_client, str(uuid.uuid4()))
