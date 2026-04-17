"""composer.py - 文档合并模块

提供使用 docxcompose 进行文档合并的功能。
"""

from pathlib import Path
from typing import Dict, Any, Optional
from copy import deepcopy

try:
    from docx import Document
    from docxcompose.composer import Composer
    DOCXCOMPOSE_AVAILABLE = True
except ImportError:
    DOCXCOMPOSE_AVAILABLE = False
    Document = None
    Composer = None

import sys
SCRIPTS_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPTS_DIR))

import common
from sectpr_manager import (
    _save_all_template_sectPrs,
    _restore_all_sectPrs,
    _restore_final_sectPr,
)
from image_handler import _copy_media_between_docx


def insert_body_at_marker_compose(
    doc_path: str,
    body_path: str,
    marker: str,
    output_path: str,
    template_path: str = None,
) -> bool:
    """在 marker 位置插入 body：直接 XML 操作 + 资源合并。

    流程：
    1. 打开渲染后的模板，找到 BODY_MARKER 位置
    2. 将 marker 段落替换为 body 文档的所有内容元素
    3. 合并 body 的图片等资源到输出文档
    4. 恢复模板 sectPr

    Args:
        doc_path: 渲染后的模板路径
        body_path: body 文档路径
        marker: 占位符标记
        output_path: 输出路径
        template_path: 原始模板路径（用于恢复文档末尾 sectPr）

    Returns:
        是否成功插入
    """
    try:
        W = common.W_NS
        doc = Document(doc_path)
        body_doc = Document(body_path)
        doc_body = doc.element.body
        elements = list(doc_body)

        marker_idx = None
        for i, elem in enumerate(elements):
            text = common.get_element_text(elem)
            if marker in text:
                marker_idx = i
                break

        if marker_idx is None:
            return False

        marker_elem = elements[marker_idx]
        parent = marker_elem.getparent()

        body_elements = list(body_doc.element.body)
        body_content = [deepcopy(e) for e in body_elements if common.local_tag(e) != 'sectPr']

        parent.remove(marker_elem)
        for j, new_elem in enumerate(body_content):
            parent.insert(marker_idx + j, new_elem)

        print(f"  已在 BODY_MARKER 位置插入 body（{len(body_content)} 个元素）")

        template_sectPrs = None
        if template_path:
            template_sectPrs = _save_all_template_sectPrs(template_path)

        doc.save(output_path)

        if template_sectPrs is not None:
            _restore_all_sectPrs(output_path, template_sectPrs)
        else:
            template_final_sectPr = _save_template_final_sectPr(template_path)
            if template_final_sectPr is not None:
                _restore_final_sectPr(output_path, template_final_sectPr)

        copied_count = _copy_media_between_docx(body_path, output_path)
        if copied_count > 0:
            print(f"  已补充复制 {copied_count} 张图片")

        return True

    except Exception as e:
        print(f"  body 插入失败: {e}")
        import traceback
        traceback.print_exc()
        return False
