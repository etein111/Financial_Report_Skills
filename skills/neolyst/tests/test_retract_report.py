"""
test_retract_report.py — retract_report 集成测试（4 个）。
"""
import json
import uuid
from pathlib import Path

import pytest

TEST_ANALYST = json.loads((Path(__file__).parent / "test_config.json").read_text())["email"]


def _make_files(directory: Path) -> tuple[str, str]:
    directory.mkdir(parents=True, exist_ok=True)
    word = directory / "report.docx"
    pdf = directory / "report.pdf"
    word.write_bytes(b"fake docx")
    pdf.write_bytes(b"fake pdf")
    return str(word), str(pdf)


def _create_submitted_report(client, coverage_id, tmp_dir, title="Retract Test"):
    """辅助函数：创建 draft → 提交为 submitted → 返回提交结果。"""
    from skills.neolyst.scripts import draft_report
    from skills.neolyst.scripts import submit_report as sr

    word_path, pdf_path = _make_files(tmp_dir)
    draft = draft_report.save_draft_report(client, {
        "report_id": None,
        "title": title,
        "report_type": "company",
        "report_language": "en",
        "investment_thesis": "Test investment thesis",
        "contact_person": TEST_ANALYST,
        "analysts": [{"analyst_email": TEST_ANALYST, "author_order": 1}],
        "ticker": title[:8].upper().replace(" ", ""),
        "coverage_id": coverage_id,
        "sector_id": None,
        "region_code": None,
        "rating": "OUTPERFORM",
        "target_price": 100.0,
        "report_file": word_path,
        "pdf_file": pdf_path,
        "model_file": None,
    })
    return sr.submit_report(client, draft["report_id"])


@pytest.fixture(scope="module")
def retract_coverage_id(neolyst_client):
    from skills.neolyst.scripts import coverage as cov

    _suffix = uuid.uuid4().hex[:6].upper()
    sector_resp = neolyst_client.table("sector").select("id").eq("is_active", True).limit(1).execute()
    sector_id = sector_resp.data[0]["id"]

    cov_id = cov.create_coverage(
        neolyst_client,
        ticker=f"RET{_suffix}",
        english_name=f"Retract Test Co {_suffix}",
        sector_id=sector_id,
        isin=f"HK{_suffix}{'0' * (10 - len(_suffix))}",
        country_of_domicile="Hong Kong",
        analysts=[{"analyst_email": TEST_ANALYST, "author_order": 1}],
    )
    yield cov_id
    neolyst_client.table("coverage").delete().eq("id", cov_id).execute()


class TestRetractSubmittedReport:
    """测试 submitted → draft 撤回完整流程（单测试覆盖返回值 + DB + 日志）。"""

    def test_retract_submitted_report(self, neolyst_client, retract_coverage_id, tmp_path):
        """创建 submitted 报告 → 撤回 → 验证返回值、DB 状态、状态日志。"""
        from skills.neolyst.scripts import retract_report as rr

        submitted = _create_submitted_report(
            neolyst_client, retract_coverage_id, tmp_path / "retract_happy",
        )
        report_id = submitted["report_id"]

        try:
            result = rr.retract_report(neolyst_client, report_id)

            # 1. 返回值：status == draft
            assert result["status"] == "draft"
            uuid.UUID(result["report_id"])
            assert result["version_no"] == submitted["version_no"]

            # 2. DB 状态：report.status == draft
            resp = (
                neolyst_client.table("report")
                .select("status")
                .eq("id", report_id)
                .execute()
            )
            assert resp.data[0]["status"] == "draft"

            # 3. 状态日志：submitted → draft，含 metadata 快照
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
            assert log["version_no"] == submitted["version_no"]
            assert "@" in (log["action_by_name"] or "")
            assert log["metadata"]
        finally:
            neolyst_client.table("report").delete().eq("id", report_id).execute()


class TestRetractEdgeCases:
    """测试撤回边界条件。"""

    def test_retract_draft_raises(self, neolyst_client, retract_coverage_id, tmp_path):
        """对 draft 报告调用 retract_report 抛出 ValueError。"""
        from skills.neolyst.scripts import draft_report
        from skills.neolyst.scripts import retract_report as rr

        word_path, pdf_path = _make_files(tmp_path / "draft_edge")
        draft = draft_report.save_draft_report(neolyst_client, {
            "report_id": None,
            "title": "Retract Draft Test",
            "report_type": "company",
            "report_language": "en",
            "investment_thesis": "Test investment thesis",
            "contact_person": TEST_ANALYST,
            "analysts": [{"analyst_email": TEST_ANALYST, "author_order": 1}],
            "ticker": "RETDRAFT",
            "coverage_id": retract_coverage_id,
            "sector_id": None,
            "region_code": None,
            "rating": "OUTPERFORM",
            "target_price": 100.0,
            "report_file": word_path,
            "pdf_file": pdf_path,
            "model_file": None,
        })
        try:
            with pytest.raises(ValueError, match="无法撤回"):
                rr.retract_report(neolyst_client, draft["report_id"])
        finally:
            neolyst_client.table("report").delete().eq("id", draft["report_id"]).execute()

    def test_retract_already_retracted_raises(self, neolyst_client, retract_coverage_id, tmp_path):
        """对已撤回为 draft 的报告再次撤回，抛出 ValueError。"""
        from skills.neolyst.scripts import retract_report as rr

        submitted = _create_submitted_report(
            neolyst_client, retract_coverage_id, tmp_path / "double_retract",
        )
        report_id = submitted["report_id"]

        try:
            rr.retract_report(neolyst_client, report_id)  # 第一次撤回成功
            with pytest.raises(ValueError, match="无法撤回"):
                rr.retract_report(neolyst_client, report_id)  # 第二次应失败
        finally:
            neolyst_client.table("report").delete().eq("id", report_id).execute()

    def test_retract_nonexistent_report_raises(self, neolyst_client):
        """对不存在的报告调用 retract_report 抛出 ValueError。"""
        from skills.neolyst.scripts import retract_report as rr

        with pytest.raises(ValueError, match="报告不存在"):
            rr.retract_report(neolyst_client, str(uuid.uuid4()))
