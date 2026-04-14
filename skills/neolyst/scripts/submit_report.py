"""
submit_report.py — Neolyst 报告提交接口。

流程：
1. 调用 submit_report RPC
2. 返回 {"report_id": str, "status": "submitted"}
"""

from supabase import Client

from . import rpc


def submit_report(client: Client, report_id: str) -> dict:
    row = rpc.single_row(rpc.call_rpc(client, "submit_report", {
        "p_report_id": report_id,
    }))
    return {
        "report_id": str(row["report_id"]),
        "status": row["status"],
    }
