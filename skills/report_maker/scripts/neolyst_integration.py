"""
neolyst_integration.py — report_maker 对 neolyst 的统一接口封装。

职责：
1. 模板解析：从 neolyst 获取模板路径（替代本地 router.yaml）
2. 草稿保存：字段映射 + 调用 save_report
3. Coverage 解析：resolve_coverage
4. 分析师解析：resolve_analyst_by_email
5. 草稿校验：调用 validate_report
6. 报告提交：调用 submit_report
7. 文件上传：upload_report_files / upload_model_file
"""

import sys
from pathlib import Path
from typing import Dict, Any, Optional, List
from supabase import Client

# 将项目根目录（neoskills）加入 sys.path，以便能导入 skills.neolyst 等模块
_NEOSKILLS_ROOT = str(Path(__file__).resolve().parents[3])
if _NEOSKILLS_ROOT not in sys.path:
    sys.path.insert(0, _NEOSKILLS_ROOT)

from skills.neolyst.scripts.connection import get_client
from skills.neolyst.scripts.template import resolve_template
from skills.neolyst.scripts.report import save_report, validate_report, submit_report
from skills.neolyst.scripts.coverage import resolve_coverage
from skills.neolyst.scripts.analyst import resolve_analyst_by_email
from skills.neolyst.scripts.upload_files import upload_report_files, upload_model_file
from .common import COMPANY_REPORT_TYPES, SECTOR_REPORT_TYPES


# ==================== 模板解析 ====================

def resolve_template_for_report(
    report_type: str,
    report_language: str,
    dest_dir: str = ".",
    client: Client = None,
) -> Dict[str, str]:
    """
    从 neolyst 解析模板，返回本地路径。

    Args:
        report_type: 报告类型（如 "company", "macro"）
        report_language: 报告语言（如 "en", "zh"）
        dest_dir: 下载根目录，默认 "."，文件落在 {dest_dir}/templates/{report_type}/{report_language}/
        client: Supabase client，默认从环境变量创建

    Returns:
        {"template_local_path": str, "schema_local_path": str | None}

    Raises:
        ValueError: 模板不存在或未发布
    """
    if client is None:
        client = get_client()
    return resolve_template(client, report_type, report_language, dest_dir)


# ==================== 分析师解析 ====================

def resolve_analysts_from_elements(
    elements: Dict[str, Any],
    client: Client = None,
) -> List[Dict[str, Any]]:
    """
    从 elements.yaml 的 a1~a8 作者槽位解析分析师列表。

    用 resolve_analyst_by_email 校验并标准化，每位分析师返回：
    {"analyst_email": str, "author_order": int, "analyst_id": str}

    Args:
        elements: elements.yaml 内容，需含 a1~a8 槽位
        client: Supabase client

    Returns:
        分析师列表（按 author_order 升序，最多 8 人）

    Raises:
        ValueError: 分析师未找到或已停用
    """
    if client is None:
        client = get_client()

    analysts = []
    for i in range(1, 9):
        email = elements.get(f"a{i}")
        if email:
            record = resolve_analyst_by_email(client, email)
            analysts.append({
                "analyst_email": record["email"],
                "author_order": i,
                "analyst_id": str(record["id"]),
            })

    return analysts


def get_contact_person_options(analysts: List[Dict[str, Any]]) -> List[str]:
    """从分析师列表提取可选的 contact_person 邮箱列表。"""
    return [a["analyst_email"] for a in analysts]


# ==================== Coverage 解析 ====================

def resolve_coverage_for_report(
    ticker: str,
    first_analyst_email: str,
    client: Client = None,
) -> str:
    """
    根据 ticker 和 1作分析师邮箱查询 coverage_id。

    Args:
        ticker: 股票代码
        first_analyst_email: 1作分析师邮箱
        client: Supabase client

    Returns:
        coverage_id 字符串

    Raises:
        ValueError: coverage 未命中、命中多条或数据异常
    """
    if client is None:
        client = get_client()
    return resolve_coverage(client, ticker, first_analyst_email)


# ==================== 字段映射与补齐 ====================

def detect_language_from_title(title: str) -> str:
    """
    从标题判断报告语言。

    规则：标题中任意字符 ord > 127 则判定为 "zh"，否则为 "en"。

    Args:
        title: 报告标题

    Returns:
        "zh" 或 "en"
    """
    for char in title:
        if ord(char) > 127:
            return "zh"
    return "en"


def compress_investment_thesis(abstract: str, max_length: int = 150) -> str:
    """
    将报告摘要压缩为投资要点概述。

    规则：直接截取前 max_length 字符，句尾不截断单词。

    Args:
        abstract: 原始摘要文本
        max_length: 最大长度，默认 150

    Returns:
        压缩后的概述
    """
    if not abstract:
        return ""
    if len(abstract) <= max_length:
        return abstract

    # 找最后一个完整句子结束符
    truncated = abstract[:max_length]
    last_punct = max(
        truncated.rfind('。'),
        truncated.rfind('.'),
        truncated.rfind('！'),
        truncated.rfind('!'),
    )
    if last_punct > max_length * 0.5:
        return truncated[:last_punct + 1]
    return truncated.rstrip()


def map_elements_to_draft(
    elements: Dict[str, Any],
    report_type: str,
    report_file: str,
    pdf_file: str,
    contact_person: str,
    analysts: List[Dict[str, Any]],
    coverage_id: Optional[str] = None,
    investment_thesis: Optional[str] = None,
    model_file: Optional[str] = None,
) -> Dict[str, Any]:
    """
    将 report_maker 的 elements 映射为 neolyst save_report 的 draft 输入。

    最小字段：title、report_type、report_language、analysts、report_file、pdf_file

    提交前补齐字段：contact_person、investment_thesis、coverage_id、ticker、rating、target_price、region_code、sector_id、model_file

    Args:
        elements: elements.yaml 内容
        report_type: 报告类型
        report_file: 最终 Word 文件路径
        pdf_file: 最终 PDF 文件路径
        contact_person: 联系人邮箱（必须属于 analysts）
        analysts: resolve_analysts_from_elements 返回的分析师列表
        coverage_id: coverage UUID（公司类报告）
        investment_thesis: 投资要点概述，默认从 abstract 压缩
        model_file: Excel 模型文件路径（公司类报告）
        region_code: 区域代码（行业类报告）
        sector_id: 行业 UUID（行业类报告）

    Returns:
        neolyst save_report 所需的 draft 字典
    """
    title = elements.get("title", "")
    report_language = detect_language_from_title(title)

    draft = {
        "title": title,
        "report_type": report_type,
        "report_language": report_language,
        "analysts": analysts,
        "report_file": report_file,
        "pdf_file": pdf_file,
        "contact_person": contact_person,
    }

    # investment_thesis：从 abstract 压缩或直接使用传入值
    if investment_thesis is None:
        abstract = elements.get("abstract", "")
        draft["investment_thesis"] = compress_investment_thesis(abstract)
    else:
        draft["investment_thesis"] = investment_thesis

    # 公司类报告字段
    if report_type in COMPANY_REPORT_TYPES:
        if coverage_id:
            draft["coverage_id"] = coverage_id
        ticker = elements.get("ticker")
        if ticker:
            draft["ticker"] = ticker
        rating = elements.get("rating")
        if rating:
            draft["rating"] = rating
        target_price = elements.get("target_price")
        if target_price:
            draft["target_price"] = target_price
        if model_file:
            draft["model_file"] = model_file

    # 行业类报告字段
    elif report_type in SECTOR_REPORT_TYPES:
        region_code = elements.get("region_code")
        if region_code:
            draft["region_code"] = region_code
        sector_id = elements.get("sector_id")
        if sector_id:
            draft["sector_id"] = sector_id

    return draft


# ==================== 草稿操作 ====================

def save_draft(
    draft: Dict[str, Any],
    client: Client = None,
) -> Dict[str, Any]:
    """
    调用 neolyst save_report 保存草稿。

    Args:
        draft: map_elements_to_draft 返回的草稿字典
        client: Supabase client

    Returns:
        {"report_id": str}
    """
    if client is None:
        client = get_client()
    return save_report(client, draft)


def validate_draft(
    report_id: str,
    client: Client = None,
) -> None:
    """
    调用 neolyst validate_report 校验草稿。

    校验失败时抛出 ValueError。

    Args:
        report_id: 报告 UUID
        client: Supabase client

    Raises:
        ValueError: 校验失败
    """
    if client is None:
        client = get_client()
    validate_report(client, report_id)


def submit_draft(
    report_id: str,
    client: Client = None,
) -> Dict[str, Any]:
    """
    调用 neolyst submit_report 提交报告。

    Args:
        report_id: 报告 UUID
        client: Supabase client

    Returns:
        {"report_id": str, "status": "submitted"}
    """
    if client is None:
        client = get_client()
    return submit_report(client, report_id)


# ==================== 文件上传 ====================

def upload_draft_files(
    report_id: str,
    report_file: str,
    pdf_file: str,
    client: Client = None,
) -> Dict[str, str]:
    """
    上传报告 Word + PDF 文件到 neolyst Storage。

    Args:
        report_id: 报告 UUID
        report_file: Word 文件本地路径
        pdf_file: PDF 文件本地路径
        client: Supabase client

    Returns:
        {"report_id": str, "word_path": str, "pdf_path": str}
    """
    if client is None:
        client = get_client()
    return upload_report_files(client, report_id, report_file, pdf_file)


def upload_model(
    report_id: str,
    model_file: str,
    client: Client = None,
) -> Dict[str, str]:
    """
    上传 Excel 模型文件到 neolyst Storage。

    Args:
        report_id: 报告 UUID
        model_file: Excel 文件本地路径
        client: Supabase client

    Returns:
        {"report_id": str, "model_path": str}
    """
    if client is None:
        client = get_client()
    return upload_model_file(client, report_id, model_file)