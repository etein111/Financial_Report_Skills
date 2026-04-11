"""
submit_report.py — Neolyst 报告提交接口。

流程：
1. 调用 submit_report RPC
2. 返回 {report_id, version_no, status}

业务逻辑（当前版本定位、状态流转、日志写入）全部在 Supabase RPC 侧，本模块只做调用串联。
"""

from supabase import Client


def submit_report(client: Client, report_id: str) -> dict:
    """
    提交 draft/rejected 报告当前版本为 submitted 状态。

    Args:
        client: 已认证的 Supabase client
        report_id: 报告 UUID 字符串

    Returns:
        dict: {"report_id": str, "version_no": int, "status": "submitted"}

    Raises:
        ValueError: RPC 调用失败
    """
    try:
        resp = client.rpc("submit_report", {
            "p_report_id": report_id,
        }).execute()
    except Exception as e:
        raise ValueError(str(e)) from e

    row = resp.data[0]
    return {
        "report_id": str(row["report_id"]),
        "version_no": row["version_no"],
        "status": row["status"],
    }
