"""
workflow.py — report_maker 完整报告提交流程。

职责：
1. prepare_and_save_draft：加载 elements、解析分析师、尝试解析 coverage、保存草稿
2. submit_report_workflow：校验草稿、上传文件、提交报告

报告类型分类：
- 公司类报告：("company", "company_flash") - 使用 coverage_id, model_file
- 行业类报告：("sector", "macro", "strategy", "quantitative", "bond") - 不需要 coverage_id
"""

from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path

from .neolyst_integration import (
    resolve_analysts_from_elements,
    resolve_coverage_for_report,
    map_elements_to_draft,
    save_draft,
    validate_draft,
    submit_draft,
    upload_draft_files,
    upload_model,
    get_contact_person_options,
)
from .common import load_yaml, COMPANY_REPORT_TYPES, SECTOR_REPORT_TYPES


# ==================== 核心工作流函数 ====================

def prepare_and_save_draft(
    elements_path: str,
    report_type: str,
    report_file: str,
    pdf_file: str,
    dest_dir: str = ".",
    client=None,
) -> Dict[str, Any]:
    """
    准备并保存报告草稿。

    流程：
    1. 加载 elements.yaml
    2. 解析分析师列表
    3. 若是公司类报告，尝试解析 coverage_id
    4. 映射字段并保存草稿

    Args:
        elements_path: elements.yaml 文件路径
        report_type: 报告类型（如 "company", "sector"）
        report_file: 最终 Word 文件路径
        pdf_file: 最终 PDF 文件路径
        dest_dir: 下载根目录（用于 resolve_template），默认 "."
        client: Supabase client，默认从环境变量创建

    Returns:
        {
            report_id: str,           # 草稿报告 UUID
            analysts: List[Dict],     # 分析师列表
            contact_person_options: List[str],  # 可选的联系人邮箱列表
            coverage_id: str | None,  # coverage UUID（公司类报告）
            draft: Dict,             # 映射后的草稿字典
        }

    Raises:
        ValueError: 分析师未找到、coverage 解析失败或草稿保存失败
    """
    # 1. 加载 elements.yaml
    elements = load_yaml(elements_path)
    if not elements:
        raise ValueError(f"elements.yaml 为空或不存在: {elements_path}")

    # 2. 解析分析师列表
    analysts = resolve_analysts_from_elements(elements, client=client)
    if not analysts:
        raise ValueError("未找到有效的分析师，请检查 elements.yaml 中的 a1~a8 槽位")

    # 3. 获取可选联系人列表
    contact_person_options = get_contact_person_options(analysts)

    # 4. 公司类报告：尝试解析 coverage_id
    coverage_id: Optional[str] = None
    if report_type in COMPANY_REPORT_TYPES:
        ticker = elements.get("ticker")
        first_analyst_email = analysts[0]["analyst_email"] if analysts else None
        if ticker and first_analyst_email:
            try:
                coverage_id = resolve_coverage_for_report(ticker, first_analyst_email, client=client)
            except ValueError as e:
                # coverage 解析失败不阻止流程，记录警告
                # 后续 map_elements_to_draft 会处理 coverage_id 为 None 的情况
                pass

    # 5. 映射字段并保存草稿
    # contact_person 默认为第一作者
    contact_person = contact_person_options[0] if contact_person_options else None
    if not contact_person:
        raise ValueError("没有可用的联系人（分析师列表为空）")

    draft = map_elements_to_draft(
        elements=elements,
        report_type=report_type,
        report_file=report_file,
        pdf_file=pdf_file,
        contact_person=contact_person,
        analysts=analysts,
        coverage_id=coverage_id,
    )

    # 保存草稿
    result = save_draft(draft, client=client)
    report_id = result.get("report_id")
    if not report_id:
        raise ValueError(f"草稿保存失败，未返回 report_id: {result}")

    return {
        "report_id": report_id,
        "analysts": analysts,
        "contact_person_options": contact_person_options,
        "coverage_id": coverage_id,
        "draft": draft,
    }


def submit_report_workflow(
    report_id: str,
    report_file: str,
    pdf_file: str,
    contact_person: str,
    analysts: List[Dict[str, Any]],
    coverage_id: Optional[str] = None,
    model_file: Optional[str] = None,
    client=None,
) -> Dict[str, Any]:
    """
    提交流稿工作流。

    流程：
    1. 校验草稿
    2. 上传报告文件（Word + PDF）
    3. 若是公司类报告且有 model_file，上传模型文件
    4. 提交报告

    Args:
        report_id: 报告 UUID
        report_file: Word 文件本地路径
        pdf_file: PDF 文件本地路径
        contact_person: 联系人邮箱（必须属于 analysts）
        analysts: 分析师列表
        coverage_id: coverage UUID（公司类报告）
        model_file: Excel 模型文件路径（公司类报告）
        client: Supabase client

    Returns:
        {"report_id": str, "status": str}

    Raises:
        ValueError: 校验失败或提交失败
    """
    # 0. 校验 contact_person 属于 analysts
    analyst_emails = {a["analyst_email"] for a in analysts}
    if contact_person not in analyst_emails:
        raise ValueError(
            f"contact_person '{contact_person}' 不在分析师列表中。"
            f"可选值: {analyst_emails}"
        )

    # 1. 校验草稿
    validate_draft(report_id, client=client)

    # 2. 上传报告文件
    upload_result = upload_draft_files(report_id, report_file, pdf_file, client=client)
    if upload_result.get("report_id") != report_id:
        raise ValueError(f"文件上传失败: {upload_result}")

    # 3. 公司类报告：上传模型文件（若提供）
    if model_file and coverage_id:
        upload_model_result = upload_model(report_id, model_file, client=client)
        if upload_model_result.get("report_id") != report_id:
            raise ValueError(f"模型文件上传失败: {upload_model_result}")

    # 4. 提交报告
    submit_result = submit_draft(report_id, client=client)
    if submit_result.get("report_id") != report_id:
        raise ValueError(f"报告提交失败: {submit_result}")

    return {
        "report_id": report_id,
        "status": submit_result.get("status", "submitted"),
    }


# ==================== 辅助函数 ====================

def is_company_report(report_type: str) -> bool:
    """判断是否为公司类报告。"""
    return report_type in COMPANY_REPORT_TYPES


def is_sector_report(report_type: str) -> bool:
    """判断是否为行业类报告。"""
    return report_type in SECTOR_REPORT_TYPES


def classify_report_type(report_type: str) -> str:
    """分类报告类型。

    Args:
        report_type: 报告类型

    Returns:
        "company" 或 "sector"

    Raises:
        ValueError: 未知报告类型
    """
    if is_company_report(report_type):
        return "company"
    elif is_sector_report(report_type):
        return "sector"
    else:
        raise ValueError(
            f"未知的报告类型: {report_type}。"
            f"公司类: {COMPANY_REPORT_TYPES}，行业类: {SECTOR_REPORT_TYPES}"
        )
