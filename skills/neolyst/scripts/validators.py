"""
validators.py — Neolyst 报告提交前校验。

校验逻辑的单一事实源在 DB 侧（validate_report RPC）。
Python 层只封装 RPC 调用，返回标准化结果。
"""

from supabase import Client

from . import rpc


def validate_report(client: Client, report_id: str) -> dict:
    """
    调用 validate_report RPC，校验报告当前版本是否满足提交条件。
    校验逻辑在 DB 侧，此函数只封装调用。

    Args:
        client: 已认证的 Supabase client
        report_id: 报告 UUID 字符串

    Returns:
        dict: {"report_id": report_id, "version_no": int}（校验通过时）

    Raises:
        ValueError: 校验失败，消息列出所有失败项，以"；"分隔
    """
    resp = (
        client.table("report")
        .select("current_version_no")
        .eq("id", report_id)
        .execute()
    )
    if not resp.data:
        raise ValueError(f"报告不存在: {report_id}")
    version_no = resp.data[0]["current_version_no"] or 0

    rpc.call_rpc(client, "validate_report", {"p_report_id": report_id})
    return {"report_id": report_id, "version_no": version_no}
