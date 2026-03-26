"""extractor.py - LLM 要素提取模块。"""

from typing import Dict, Any
from pathlib import Path
import sys

SCRIPTS_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPTS_DIR))

import common


def extract_elements(draft_path: str, schema: Dict[str, Any], context: str = "") -> Dict[str, Any]:
    """从草稿中提取要素。"""
    elements = {}
    for field_name in schema.keys():
        if field_name not in ['abstract', 'body']:
            elements[field_name] = ""

    if 'abstract' in schema:
        elements['abstract'] = common.FILE_ABSTRACT
    if 'body' in schema:
        elements['body'] = common.FILE_BODY

    return elements


def format_extraction_prompt(schema: Dict[str, Any], report_type: str) -> str:
    """格式化提取提示词。"""
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

    prompt += "\n注意：\n1. 如果某个字段在草稿中找不到，留空即可\n2. 请严格按照字段名返回结果\n"

    return prompt


def merge_llm_results(elements: Dict[str, Any], llm_results: Dict[str, Any], schema: Dict[str, Any]) -> Dict[str, Any]:
    """合并 LLM 提取结果到 elements。"""
    result = elements.copy()

    for field_name in schema.keys():
        if field_name in ['abstract', 'body']:
            continue

        if field_name in llm_results:
            value = llm_results[field_name]
            if value is None:
                value = ""
            result[field_name] = str(value) if value else ""

    return result
