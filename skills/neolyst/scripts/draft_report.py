"""
draft_report.py — Neolyst draft 报告保存接口。

执行流程（支持 analyst 权限）：
1. 若 report_id 为 None，用 uuid.uuid4() 生成
2. 调用 init_draft_report RPC → 建/更新 report + 替换 report_analyst → 返回 next_version_no
3. 上传本地文件到 reports/{report_id}/v{version_no}/{原始文件名}
   （此时 report 已在 DB，analyst 的 Storage 权限不受阻）
4. 调用 commit_draft_version RPC → 插入 report_version + 更新 current_version_no
5. 返回 {report_id, version_no, status}

业务逻辑全部在 Supabase RPC 侧，本模块只做 I/O 和参数整理。
"""

import uuid
from pathlib import Path

from supabase import Client

from . import storage


def save_draft_report(client: Client, draft: dict) -> dict:
    """
    保存 draft 报告（新建或追加版本）。

    若 report_id 为 None，则生成新 UUID。调用 init_draft_report RPC 创建或更新报告元数据，
    然后上传相关本地文件到 Storage，最后调用 commit_draft_version RPC 提交版本。

    Args:
        client: 已认证的 Supabase client
        draft: 报告草稿数据，包含以下字段：
            - report_id (str | None): 既有报告 UUID，或 None（新建）
            - title (str): 报告标题
            - report_type (str): 报告类型
            - report_language (str | None): 报告语言
            - analysts (list[dict]): 分析师列表，每项含 analyst_email, author_order
            - report_file (str | None): 本地 Word 文件路径
            - pdf_file (str | None): 本地 PDF 文件路径
            - model_file (str | None): 本地模型文件路径
            - coverage_id (str | None): coverage UUID
            - ticker (str | None): 股票代码
            - rating (str | None): 评级
            - target_price (float | None): 目标价
            - region_code (str | None): 地区代码
            - sector_id (str | None): 行业 UUID
            - contact_person (str | None): 联系人
            - investment_thesis (str | None): 投资论文

    Returns:
        dict: 保存结果，包含：
            - report_id (str): 报告 UUID
            - version_no (int): 版本号
            - status (str): 报告状态（通常为 'draft'）

    Raises:
        FileNotFoundError: 本地文件不存在（由 storage.upload 抛出）
        ValueError: RPC 调用失败或其他业务逻辑错误
    """
    # 第 1 步：确定 report_id
    report_id = draft.get("report_id")
    if report_id is None:
        report_id = str(uuid.uuid4())

    # 第 2 步：构建 p_draft（排除文件字段）
    p_draft = {
        k: v for k, v in draft.items()
        if k not in ("report_file", "pdf_file", "model_file")
    }
    p_draft["report_id"] = report_id

    # 第 3 步：调用 init_draft_report RPC
    try:
        init_resp = client.rpc("init_draft_report", {"p_draft": p_draft}).execute()
    except Exception as e:
        raise ValueError(str(e)) from e

    if not init_resp.data:
        raise ValueError("init_draft_report RPC returned empty data")

    version_no = init_resp.data[0]["next_version_no"]

    # 第 4 步：上传文件
    def _upload(local_path: str | None) -> str | None:
        if not local_path:
            return None
        filename = Path(local_path).name
        storage_path = f"reports/{report_id}/v{version_no}/{filename}"
        storage.upload(client, storage_path, local_path)
        return storage_path

    word_file_path = _upload(draft.get("report_file"))
    pdf_file_path = _upload(draft.get("pdf_file"))
    model_file_path = _upload(draft.get("model_file"))

    # 第 5 步：构建 snapshot（p_draft 已排除本地路径，加入 storage 路径）
    snapshot = dict(p_draft)
    if word_file_path:
        snapshot["word_file_path"] = word_file_path
    if pdf_file_path:
        snapshot["pdf_file_path"] = pdf_file_path
    if model_file_path:
        snapshot["model_file_path"] = model_file_path

    # 第 6 步：调用 commit_draft_version RPC
    try:
        commit_resp = client.rpc("commit_draft_version", {
            "p_report_id": report_id,
            "p_version_no": version_no,
            "p_word_path": word_file_path,
            "p_pdf_path": pdf_file_path,
            "p_model_path": model_file_path,
            "p_snapshot": snapshot,
        }).execute()
    except Exception as e:
        raise ValueError(str(e)) from e

    if not commit_resp.data:
        raise ValueError("commit_draft_version RPC returned empty data")

    row = commit_resp.data[0]

    # 第 7 步：返回结果
    return {
        "report_id": str(row["report_id"]),
        "version_no": row["version_no"],
        "status": row["status"],
    }
