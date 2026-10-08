"""
storage.py — Neolyst Supabase Storage 封装。

只负责文件上传/下载。路径由调用方传入（来自 Supabase RPC），本模块不拼路径字符串。

路径规范：数据库中存储的所有 Storage 路径必须包含 bucket 前缀，格式为 {bucket}/{path}。
"""

from pathlib import Path
from supabase import Client


def upload(client: Client, storage_path: str, local_path: str) -> None:
    """上传本地文件到 Storage，已存在时覆盖。storage_path 格式：{bucket}/{path}。"""
    bucket, path = _split(storage_path)
    try:
        data = Path(local_path).read_bytes()
    except FileNotFoundError:
        raise FileNotFoundError(f"本地文件不存在: {local_path}")
    try:
        client.storage.from_(bucket).upload(path, data)
    except Exception as e:
        if "already exists" not in str(e).lower():
            raise
        client.storage.from_(bucket).update(path, data)


def download(client: Client, storage_path: str, local_path: str) -> None:
    """从 Storage 下载文件到本地路径。storage_path 格式：{bucket}/{path}。"""
    bucket, path = _split(storage_path)
    local = Path(local_path)
    local.parent.mkdir(parents=True, exist_ok=True)
    data = client.storage.from_(bucket).download(path)
    local.write_bytes(data)


def _split(storage_path: str) -> tuple[str, str]:
    """将 'bucket/path/to/file' 拆分为 ('bucket', 'path/to/file')。"""
    bucket, _, path = storage_path.partition("/")
    if not bucket or not path:
        raise ValueError(f"无效的 storage_path（格式应为 'bucket/path'）: {storage_path!r}")
    return bucket, path
