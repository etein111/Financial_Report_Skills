"""
submit_report.py — Neolyst 报告提交接口。

流程：
1. 调用 validate_draft 校验（失败则直接抛出 ValueError）
2. 调用 submit_report RPC → 原子更新 report.status + 写入 report_status_log
3. 返回 {report_id, version_no, status}

业务逻辑（状态流转、日志写入）全部在 Supabase RPC 侧，本模块只做调用串联。
"""

from supabase import Client

from skills.neolyst.scripts.validators import validate_draft


def submit_report(client: Client, report_id: str, version_no: int) -> dict:
    """
    提交 draft/rejected 报告为 submitted 状态。

    Args:
        client: 已认证的 Supabase client
        report_id: 报告 UUID 字符串
        version_no: 要提交的版本号

    Returns:
        dict: {"report_id": str, "version_no": int, "status": "submitted"}

    Raises:
        ValueError: 校验未通过（含具体失败原因）或 RPC 调用失败
    """
    # 1. 校验（失败直接抛出）
    validate_draft(client, report_id, version_no)

    # 2. 调用 submit_report RPC
    try:
        resp = client.rpc("submit_report", {
            "p_report_id": report_id,
            "p_version_no": version_no,
        }).execute()
    except Exception as e:
        raise ValueError(str(e)) from e

    row = resp.data[0]
    return {
        "report_id": str(row["report_id"]),
        "version_no": row["version_no"],
        "status": row["status"],
    }
