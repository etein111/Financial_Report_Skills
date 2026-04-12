"""
validators.py — Neolyst draft 报告提交前校验。

校验规则（全量收集，一次性抛出所有错误）：
1. report 存在且 status in ('draft', 'rejected')
2. report.current_version_no > 0，且当前版本存在
3. word_file_path / pdf_file_path 非空
4. 必填字段：title / report_type / report_language / investment_thesis / contact_person
5. 至少一个分析师；contact_person 在分析师列表中（大小写不敏感）
6. 每个分析师在 analyst 表中存在且 is_active
7. company / company_flash 类型：coverage_id 必填且存在
8. sector_id / region_code：有值时验证存在性

业务逻辑全部在 Python 侧实现，仅做 SELECT 查询，不调用 RPC。
"""

from supabase import Client


def _record_exists(client: Client, table: str, field: str, value: str) -> bool:
    """查询表中是否存在指定字段值的记录。"""
    resp = client.table(table).select(field).eq(field, value).execute()
    return bool(resp.data)


def validate_draft(client: Client, report_id: str) -> dict:
    """
    校验 draft 报告当前版本是否满足提交条件。
    纯校验，不修改数据库、不补字段、不重试、不保存 draft。

    Args:
        client: 已认证的 Supabase client
        report_id: 报告 UUID 字符串

    Returns:
        dict: {"report_id": report_id, "version_no": current_version_no}（校验通过时）

    Raises:
        ValueError: 校验失败，消息列出所有失败项，以"；"分隔
    """
    errors: list[str] = []

    report_resp = (
        client.table("report")
        .select(
            "id, status, current_version_no, title, report_type, report_language, "
            "investment_thesis, contact_person, coverage_id, sector_id, region_code"
        )
        .eq("id", report_id)
        .execute()
    )
    if not report_resp.data:
        raise ValueError(f"报告不存在: {report_id}")
    report = report_resp.data[0]
    report_type = report.get("report_type")
    current_version_no = report.get("current_version_no") or 0

    if report["status"] not in ("draft", "rejected"):
        errors.append(f"报告状态为 {report['status']}，仅 draft/rejected 可提交")

    version = None
    if current_version_no <= 0:
        errors.append("报告当前没有可校验版本")
    else:
        version_resp = (
            client.table("report_version")
            .select("word_file_path, pdf_file_path")
            .eq("report_id", report_id)
            .eq("version_no", current_version_no)
            .execute()
        )
        if not version_resp.data:
            errors.append(f"当前版本 v{current_version_no} 不存在")
        else:
            version = version_resp.data[0]

    if version:
        if not version.get("word_file_path"):
            errors.append("缺少 Word 文件路径（word_file_path）")
        if not version.get("pdf_file_path"):
            errors.append("缺少 PDF 文件路径（pdf_file_path）")

    required_fields = {
        "title": "标题（title）",
        "report_type": "报告类型（report_type）",
        "report_language": "报告语言（report_language）",
        "investment_thesis": "投资论点（investment_thesis）",
        "contact_person": "联系人（contact_person）",
    }
    for field, label in required_fields.items():
        if not report.get(field):
            errors.append(f"缺少必填字段：{label}")

    analysts_resp = (
        client.table("report_analyst")
        .select("analyst_email")
        .eq("report_id", report_id)
        .execute()
    )
    analyst_emails = [a["analyst_email"] for a in analysts_resp.data]
    if not analyst_emails:
        errors.append("报告没有分析师（report_analyst 为空）")

    # contact_person 必须在分析师列表中（大小写不敏感）
    contact = report.get("contact_person")
    if contact and analyst_emails and contact.lower() not in [e.lower() for e in analyst_emails]:
        errors.append(f"contact_person（{contact}）不在本报告分析师列表中")

    # 批量查询分析师存在性，避免 N+1
    if analyst_emails:
        a_resp = (
            client.table("analyst")
            .select("email, is_active")
            .in_("email", analyst_emails)
            .execute()
        )
        found = {row["email"]: row["is_active"] for row in a_resp.data}
        for email in analyst_emails:
            if email not in found:
                errors.append(f"分析师不存在：{email}")
            elif not found[email]:
                errors.append(f"分析师已停用：{email}")

    if report_type in ("company", "company_flash"):
        coverage_id = report.get("coverage_id")
        if not coverage_id:
            errors.append(f"公司类报告（{report_type}）必须关联 coverage_id")
        elif not _record_exists(client, "coverage", "id", coverage_id):
            errors.append(f"coverage 不存在：{coverage_id}")

    sector_id = report.get("sector_id")
    if sector_id and not _record_exists(client, "sector", "id", sector_id):
        errors.append(f"sector 不存在：{sector_id}")

    region_code = report.get("region_code")
    if region_code and not _record_exists(client, "region", "code", region_code):
        errors.append(f"region 不存在：{region_code}")

    if errors:
        raise ValueError("校验失败：" + "；".join(errors))

    return {"report_id": report_id, "version_no": current_version_no}
