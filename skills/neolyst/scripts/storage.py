"""
storage.py — Neolyst Supabase Storage 封装。

只负责文件上传/下载，路径由调用方传入（来自 Supabase RPC）。
bucket 名称是实现细节，调用方只需调用语义化函数。
"""

from pathlib import Path
from supabase import Client

_TEMPLATE_BUCKET = "templates"
_REPORT_BUCKET = "reports"


def upload_template(client: Client, storage_path: str, local_path: str) -> None:
    """上传文件到模板 bucket，已存在时覆盖。"""
    _upload(client, _TEMPLATE_BUCKET, storage_path, local_path)


def download_template(client: Client, storage_path: str, local_path: str) -> None:
    """从模板 bucket 下载文件到本地路径。"""
    _download(client, _TEMPLATE_BUCKET, storage_path, local_path)


def upload_report(client: Client, storage_path: str, local_path: str) -> None:
    """上传文件到报告 bucket，已存在时覆盖。"""
    _upload(client, _REPORT_BUCKET, storage_path, local_path)


def download_report(client: Client, storage_path: str, local_path: str) -> None:
    """从报告 bucket 下载文件到本地路径。"""
    _download(client, _REPORT_BUCKET, storage_path, local_path)


def _upload(client: Client, bucket: str, storage_path: str, local_path: str) -> None:
    local = Path(local_path)
    if not local.exists():
        raise FileNotFoundError(f"Local file not found: {local_path}")
    data = local.read_bytes()
    try:
        client.storage.from_(bucket).upload(storage_path, data)
    except Exception:
        client.storage.from_(bucket).update(storage_path, data)


def _download(client: Client, bucket: str, storage_path: str, local_path: str) -> None:
    local = Path(local_path)
    local.parent.mkdir(parents=True, exist_ok=True)
    data = client.storage.from_(bucket).download(storage_path)
    local.write_bytes(data)
