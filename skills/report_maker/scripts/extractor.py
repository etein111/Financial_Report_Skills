"""extractor.py - LLM 要素提取模块（增强版）。

结合自动化提取和 LLM 智能提取，提供最佳效果。

遵循函数式编程原则：纯函数、无副作用、I/O 分离。
"""

from typing import Dict, Any, Optional, List, Tuple, Callable
from pathlib import Path
import sys
import yaml

SCRIPTS_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPTS_DIR))

import common
import field_extractor

import zipfile
from lxml import etree

W = common.W_NS


def _read_full_text_lxml(docx_path: str) -> str:
    """使用 lxml 读取文档完整文本（包括嵌套表格内容）。

    解决 python-docx 漏读嵌套表格的问题，确保 LLM 能看到完整内容。

    Args:
        docx_path: docx 文件路径

    Returns:
        文档所有文本组成的字符串
    """
    texts = []
    with zipfile.ZipFile(docx_path, 'r') as z:
        with z.open('word/document.xml') as f:
            tree = etree.parse(f).getroot()

    # 遍历所有 w:t 元素获取所有文本
    for t in tree.iter(f'{W}t'):
        if t.text:
            texts.append(t.text)

    return '\n'.join(texts)


# ==================== LLM 调用接口 ====================

def call_llm_extraction(
    draft_path: str,
    schema: Dict[str, Any],
    missing_fields: List[str],
    llm_provider: Optional[Callable] = None
) -> Dict[str, Any]:
    """调用 LLM 提取缺失字段。

    Args:
        draft_path: 草稿文件路径
        schema: schema.yaml 内容
        missing_fields: 缺失字段列表
        llm_provider: 可选的 LLM 调用函数（默认使用内置实现）

    Returns:
        LLM 提取的字段字典
    """
    if llm_provider is not None:
        return llm_provider(draft_path, schema, missing_fields)

    # 内置 LLM 调用实现（需要配置 LLM API）
    try:
        # 使用 lxml 读取完整文档文本（包括嵌套表格）
        full_text = _read_full_text_lxml(draft_path)

        # 构建缺失字段的提取 prompt
        prompt = _build_llm_extraction_prompt(schema, missing_fields, full_text)

        # 调用 LLM（这里需要接入实际的 LLM API）
        # 示例：使用 anthropic 或 openai API
        llm_result = _call_llm_api(prompt)

        return llm_result
    except Exception as e:
        print(f"警告: LLM fallback 失败: {e}")
        return {}


def _build_llm_extraction_prompt(
    schema: Dict[str, Any],
    missing_fields: List[str],
    document_text: str
) -> str:
    """构建 LLM 提取提示词。

    Args:
        schema: schema.yaml 内容
        missing_fields: 缺失字段列表
        document_text: 文档文本内容

    Returns:
        提示词字符串
    """
    prompt = f"""请从以下研究报告中提取这些缺失的字段：

缺失字段：{', '.join(missing_fields)}

文档内容：
{'-' * 50}
{document_text[:8000]}  # 限制文本长度
{'-' * 50}

请以 YAML 格式返回提取的字段，只返回你找到的字段，不要返回空值。

格式：
field_name: "提取的值"
another_field: "提取的值"
"""
    return prompt


def _call_llm_api(prompt: str) -> Dict[str, Any]:
    """调用 LLM API。

    Args:
        prompt: 提示词

    Returns:
        LLM 返回的字段字典
    """
    raise NotImplementedError("LLM API 调用未实现")


# ==================== 主要提取函数 ====================

def extract_elements(
    draft_path: str,
    schema: Dict[str, Any],
    context: str = "",
    use_auto_extraction: bool = True,
    use_llm_fallback: bool = True
) -> Dict[str, Any]:
    """从草稿中提取要素。

    优先使用函数提取，缺失字段自动调用 LLM fallback。

    Args:
        draft_path: 草稿文件路径
        schema: schema.yaml 内容
        context: 额外上下文
        use_auto_extraction: 是否使用自动化提取（默认 True）
        use_llm_fallback: 是否使用 LLM 补充缺失字段（默认 True）

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

    # 第一步：自动化提取
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
            # 自动化提取失败，打印警告
            print(f"自动化提取失败: {e}")

    # 第二步：LLM fallback（补充缺失字段）
    if use_llm_fallback:
        # 找出缺失的字段（空值且不是 abstract/body）
        missing_fields = [
            k for k, v in elements.items()
            if not v and k not in ['abstract', 'body']
        ]

        if missing_fields:
            print(f"检测到 {len(missing_fields)} 个缺失字段，尝试 LLM fallback...")
            print(f"缺失字段: {', '.join(missing_fields)}")

            # 调用 LLM 提取
            llm_results = call_llm_extraction(draft_path, schema, missing_fields)

            if llm_results:
                # 合并 LLM 结果
                elements = merge_llm_results(elements, llm_results, schema)
                print(f"LLM 成功补充 {len(llm_results)} 个字段")

                # 再次检查缺失字段
                remaining = [k for k, v in elements.items() if not v and k not in ['abstract', 'body']]
                if remaining:
                    print(f"警告: 仍有 {len(remaining)} 个字段无法提取: {', '.join(remaining)}")
            else:
                print("LLM fallback 未返回结果，缺失字段将留空")

    return elements


def extract_elements_with_missing(
    draft_path: str,
    schema: Dict[str, Any],
    context: str = "",
    use_auto_extraction: bool = True,
    use_llm_fallback: bool = True
) -> Tuple[Dict[str, Any], List[str]]:
    """从草稿中提取要素，返回缺失字段列表。

    Args:
        draft_path: 草稿文件路径
        schema: schema.yaml 内容
        context: 额外上下文
        use_auto_extraction: 是否使用自动化提取
        use_llm_fallback: 是否使用 LLM 补充缺失字段

    Returns:
        (elements, missing_fields) 元组
    """
    elements = extract_elements(
        draft_path,
        schema,
        context,
        use_auto_extraction,
        use_llm_fallback
    )

    # 收集仍为空的字段
    missing_fields = [
        k for k, v in elements.items()
        if not v and k not in ['abstract', 'body']
    ]

    return elements, missing_fields


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
