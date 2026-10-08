"""
template.py — Neolyst 模板管理接口。

路径规则在 Supabase 函数中定义，本模块不拼路径字符串。
"""

from pathlib import Path
from supabase import Client

from . import rpc, storage


def upsert_template(
    client: Client,
    report_type: str,
    language: str,
    template_local_path: str,
    schema_local_path: str | None = None,
) -> None:
    """
    上传本地模板文件到 Storage，并 upsert report_template 记录。

    流程：
    1. 调用 RPC get_template_storage_paths 获取目标路径
    2. 上传文件到返回的路径
    3. 调用 RPC upsert_template_record 让服务端写库

    Returns:
        None。幂等操作，多次调用安全。
    """
    paths = rpc.single_row(
        rpc.call_rpc(client, "get_template_storage_paths", {
            "p_report_type": report_type,
            "p_language": language,
        }),
        f"get_template_storage_paths 未返回数据: {report_type}/{language}",
    )
    tmpl_storage_path = paths["template_file_path"]
    schema_storage_path = paths["schema_file_path"]

    storage.upload(client, tmpl_storage_path, template_local_path)

    if schema_local_path:
        storage.upload(client, schema_storage_path, schema_local_path)

    rpc.call_rpc(client, "upsert_template_record", {
        "p_report_type": report_type,
        "p_language": language,
    })


def reuse_template(
    client: Client,
    report_type: str,
    language: str,
    same_as_report_type: str,
) -> None:
    """
    让 report_type 的模板记录复用 same_as_report_type 的文件路径（静态复制）。
    主模板重新上传后需重新执行才能同步。

    Raises:
        ValueError: 源模板不存在、源模板未发布、report_type 与 same_as_report_type 相同
    """
    rpc.call_rpc(client, "reuse_template", {
        "p_report_type": report_type,
        "p_language": language,
        "p_same_as_report_type": same_as_report_type,
    })


def resolve_template(
    client: Client,
    report_type: str,
    language: str,
    dest_dir: str = ".",
) -> dict:
    """
    查询模板记录，下载文件到本地，返回本地路径。

    Args:
        dest_dir: 下载根目录，文件落在 {dest_dir}/templates/{report_type}/{language}/

    Returns:
        {"template_local_path": "...", "schema_local_path": "..." or None}

    Raises:
        ValueError: 模板记录不存在或 template_file_path 为空（未发布）
    """
    resp = (
        client.table("report_template")
        .select("template_file_path, schema_file_path")
        .eq("report_type", report_type)
        .eq("language", language)
        .execute()
    )

    if not resp.data:
        raise ValueError(f"模板不存在: report_type={report_type!r}, language={language!r}")

    record = resp.data[0]
    if not record.get("template_file_path"):
        raise ValueError(f"模板未发布（路径为空）: report_type={report_type!r}, language={language!r}")

    local_dir = Path(dest_dir) / "templates" / report_type / language
    template_local = str(local_dir / "template.docx")

    storage.download(
        client,
        record["template_file_path"],
        template_local,
    )

    schema_local = None
    if record.get("schema_file_path"):
        try:
            schema_local = str(local_dir / "schema.yaml")
            storage.download(client, record["schema_file_path"], schema_local)
        except (FileNotFoundError, ValueError):
            schema_local = None

    return {
        "template_local_path": template_local,
        "schema_local_path": schema_local,
    }
