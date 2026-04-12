"""
retract_report.py — Neolyst 报告撤回接口。

流程：
1. 调用 retract_report RPC
2. 返回 {report_id, version_no, status}

业务逻辑（状态校验、流转日志写入）全部在 Supabase RPC 侧，本模块只做调用串联。
"""

from supabase import Client

from . import rpc


def retract_report(client: Client, report_id: str) -> dict:
    """
    将 submitted/rejected 报告撤回为 draft 状态。

    Args:
        client: 已认证的 Supabase client
        report_id: 报告 UUID 字符串

    Returns:
        dict: {"report_id": str, "version_no": int, "status": "draft"}

    Raises:
        ValueError: RPC 调用失败（报告不存在、状态不允许撤回等）
    """
    row = rpc.single_row(rpc.call_rpc(client, "retract_report", {
        "p_report_id": report_id,
    }))
    return {
        "report_id": str(row["report_id"]),
        "version_no": row["version_no"],
        "status": row["status"],
    }
