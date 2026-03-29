"""extractor.py - LLM 要素提取模块（增强版）。

结合自动化提取和 LLM 智能提取，提供最佳效果。

遵循函数式编程原则：纯函数、无副作用、I/O 分离。
"""

from typing import Dict, Any, Optional
from pathlib import Path
import sys

SCRIPTS_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPTS_DIR))

import common
from . import field_extractor


def extract_elements(
    draft_path: str,
    schema: Dict[str, Any],
    context: str = "",
    use_auto_extraction: bool = True
) -> Dict[str, Any]:
    """从草稿中提取要素。

    Args:
        draft_path: 草稿文件路径
        schema: schema.yaml 内容
        context: 额外上下文
        use_auto_extraction: 是否使用自动化提取（默认 True）

    Returns:
        提取的字段字典
    """
    # 初始化结果
    elements = {}
    for field_name in schema.keys():
        if field_name not in ['abstract', 'body']:
            elements[field_name] = ""

    if 'abstract' in schema:
        elements['abstract'] = common.FILE_ABSTRACT
    if 'body' in schema:
        elements['body'] = common.FILE_BODY

    # 自动化提取（如果有实现）
    if use_auto_extraction:
        try:
            auto_extracted = field_extractor.extract_fields_from_docx(
                draft_path,
                schema,
                context
            )
            # 合并自动化提取的结果
            elements.update(auto_extracted)
        except Exception as e:
            # 自动化提取失败，返回空值（稍后由 LLM 处理）
            print(f"自动化提取失败: {e}")

    return elements


def format_extraction_prompt(schema: Dict[str, Any], report_type: str) -> str:
    """格式化提取提示词。

    Args:
        schema: schema.yaml 内容
        report_type: 报告类型

    Returns:
        格式化的提示词
    """
    prompt = f"请从这份 {report_type} 报告草稿中提取以下字段：\n\n"

    for field_name, field_def in schema.items():
        if field_name in ['abstract', 'body']:
            continue

        description = field_def.get('description', field_name)
        format_example = field_def.get('format', '')

        prompt += f"- {field_name}: {description}"
        if format_example:
            prompt += f" (示例: {format_example})"
        prompt += "\n"

    prompt += "\n注意：\n"
    prompt += "1. 如果某个字段在草稿中找不到，留空即可\n"
    prompt += "2. 请严格按照字段名返回结果\n"
    prompt += "3. 注意检查嵌套表格中的数据\n"

    return prompt


def merge_llm_results(
    elements: Dict[str, Any],
    llm_results: Dict[str, Any],
    schema: Dict[str, Any]
) -> Dict[str, Any]:
    """合并 LLM 提取结果到 elements。

    优先使用已提取的值，只补充空字段。

    Args:
        elements: 当前 elements 字典
        llm_results: LLM 提取结果
        schema: schema.yaml 内容

    Returns:
        合并后的 elements 字典
    """
    result = elements.copy()

    for field_name in schema.keys():
        if field_name in ['abstract', 'body']:
            continue

        # 如果当前值为空，使用 LLM 结果
        if not result.get(field_name) and field_name in llm_results:
            value = llm_results[field_name]
            if value is None:
                value = ""
            result[field_name] = str(value) if value else ""

    return result


def validate_elements(elements: Dict[str, Any], schema: Dict[str, Any]) -> Dict[str, Any]:
    """验证并补全 elements。

    确保所有字段都存在，空字段使用空字符串。

    Args:
        elements: elements 字典
        schema: schema.yaml 内容

    Returns:
        验证后的 elements 字典
    """
    return common.ensure_all_fields(elements, schema)


def format_elements_for_confirmation(elements: Dict[str, Any]) -> str:
    """格式化 elements 用于用户确认。

    生成 Markdown 表格。

    Args:
        elements: elements 字典

    Returns:
        Markdown 表格字符串
    """
    lines = []
    lines.append("| 字段 | 提取值 |")
    lines.append("|------|--------|")

    for field_name, value in elements.items():
        if field_name in ['abstract', 'body']:
            continue

        value_str = str(value) if value else ""
        # 截断过长的值
        if len(value_str) > 50:
            value_str = value_str[:47] + "..."

        # 添加状态标记
        status = "✅" if value_str else "⚠️"
        lines.append(f"| **{field_name}** | `{value_str}` {status} |")

    return "\n".join(lines)
