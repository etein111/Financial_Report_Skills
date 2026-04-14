"""
save_report.py — Neolyst 报告元数据保存接口。

执行流程：
1. 若 report_id 为 None，用 uuid.uuid4() 生成
2. 调用 upsert_report RPC 创建或更新 report 元数据
3. 返回 {"report_id": str}

业务逻辑全部在 Supabase RPC 侧，本模块只做 I/O 和参数整理。
"""

import uuid

from supabase import Client

from . import rpc


FILE_KEYS = ("report_file", "pdf_file", "model_file")


def save_report(client: Client, draft: dict) -> dict:
    """
    创建或更新 report 元数据。

    Args:
        client: 已认证的 Supabase client
        draft: 报告元数据字典；允许带 report_id，文件字段会被剥离

    Returns:
        dict: {"report_id": str}
    """
    report_id = draft.get("report_id") or str(uuid.uuid4())

    payload = {
        key: value
        for key, value in draft.items()
        if key not in FILE_KEYS
    }
    payload["report_id"] = report_id

    row = rpc.single_row(
        rpc.call_rpc(client, "upsert_report", {"p_draft": payload}),
        "upsert_report RPC returned empty data",
    )
    return {"report_id": str(row["report_id"])}
