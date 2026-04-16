"""
report.py — Neolyst 报告生命周期操作。

包含报告元数据保存、提交前校验、提交、撤回、发布和退回。
文件上传逻辑在 upload_files 模块中。
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
        "upsert_report RPC 未返回数据",
    )
    return {"report_id": str(row["report_id"])}


def validate_report(client: Client, report_id: str) -> None:
    """
    调用 validate_report RPC，校验报告是否满足提交条件。

    校验不通过时 RPC 抛出 ValueError；通过时无返回值。
    """
    rpc.call_rpc(client, "validate_report", {"p_report_id": report_id})


def submit_report(client: Client, report_id: str) -> dict:
    """提交报告，返回 {"report_id": str, "status": "submitted"}。"""
    row = rpc.single_row(rpc.call_rpc(client, "submit_report", {
        "p_report_id": report_id,
    }))
    return {
        "report_id": str(row["report_id"]),
        "status": row["status"],
    }


def retract_report(client: Client, report_id: str) -> dict:
    """撤回报告，返回 {"report_id": str, "status": "draft"}。"""
    row = rpc.single_row(rpc.call_rpc(client, "retract_report", {
        "p_report_id": report_id,
    }))
    return {
        "report_id": str(row["report_id"]),
        "status": row["status"],
    }


def publish_report(client: Client, report_id: str) -> dict:
    """发布报告，返回 {"report_id": str, "status": "published"}。"""
    row = rpc.single_row(rpc.call_rpc(client, "publish_report", {
        "p_report_id": report_id,
    }))
    return {
        "report_id": str(row["report_id"]),
        "status": row["status"],
    }


def reject_report(client: Client, report_id: str, reason: str) -> dict:
    """退回报告，返回 {"report_id": str, "status": "rejected"}。"""
    row = rpc.single_row(rpc.call_rpc(client, "reject_report", {
        "p_report_id": report_id,
        "p_rejection_reason": reason,
    }))
    return {
        "report_id": str(row["report_id"]),
        "status": row["status"],
    }


def deactivate_report(client: Client, report_id: str) -> dict:
    """废弃报告，设 is_active=False。返回 {"report_id": str, "is_active": False}。"""
    resp = (
        client.table("report")
        .update({"is_active": False})
        .eq("id", report_id)
        .eq("is_active", True)
        .execute()
    )
    if not resp.data:
        exists = (
            client.table("report")
            .select("id,is_active")
            .eq("id", report_id)
            .execute()
        )
        if not exists.data:
            raise ValueError(f"报告不存在：{report_id}")
        raise ValueError(f"报告已废弃：{report_id}")
    return {"report_id": report_id, "is_active": False}
