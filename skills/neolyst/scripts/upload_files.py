"""
upload_files.py — Neolyst 报告文件上传接口。

业务逻辑全部在 Supabase RPC 侧，本模块只负责：
1. 向 generate_upload_path 申请路径前缀
2. 上传本地文件到 Storage
3. 调用 update_report_doc_paths / update_model_path 回写 report 当前路径
"""

from pathlib import Path

from supabase import Client

from . import rpc, storage


def _join_prefix(prefix: str, local_path: str) -> str:
    if not prefix.endswith("/"):
        raise ValueError(f"Invalid upload prefix: {prefix!r}")
    return f"{prefix}{Path(local_path).name}"


def _generate_prefix(client: Client, report_id: str, category: str) -> str:
    resp = rpc.call_rpc(client, "generate_upload_path", {
        "p_report_id": report_id,
        "p_file_category": category,
    })
    if not resp.data:
        raise ValueError("generate_upload_path RPC returned empty data")

    # scalar RETURNS text: resp.data is the string directly
    if isinstance(resp.data, str):
        return resp.data

    first = resp.data[0]
    if isinstance(first, dict):
        return str(first.get("generate_upload_path") or next(iter(first.values())))
    return str(first)


def upload_report_files(
    client: Client,
    report_id: str,
    report_file: str,
    pdf_file: str,
) -> dict:
    """
    上传 Word + PDF，并回写 report.word_path/report.pdf_path。
    """
    prefix = _generate_prefix(client, report_id, "report")
    word_path = _join_prefix(prefix, report_file)
    pdf_path = _join_prefix(prefix, pdf_file)

    storage.upload(client, word_path, report_file)
    storage.upload(client, pdf_path, pdf_file)

    rpc.call_rpc(client, "update_report_doc_paths", {
        "p_report_id": report_id,
        "p_word_path": word_path,
        "p_pdf_path": pdf_path,
    })

    return {
        "report_id": report_id,
        "word_path": word_path,
        "pdf_path": pdf_path,
    }


def upload_model_file(client: Client, report_id: str, model_file: str) -> dict:
    """
    上传 Model 文件，并回写 report.model_path。
    """
    prefix = _generate_prefix(client, report_id, "model")
    model_path = _join_prefix(prefix, model_file)

    storage.upload(client, model_path, model_file)
    rpc.call_rpc(client, "update_model_path", {
        "p_report_id": report_id,
        "p_model_path": model_path,
    })

    return {
        "report_id": report_id,
        "model_path": model_path,
    }
