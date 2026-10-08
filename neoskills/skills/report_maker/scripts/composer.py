"""composer.py - 文档合并模块

提供使用 docxcompose 进行文档合并的功能。
"""

from pathlib import Path
from typing import Dict, Any, Optional

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


def _replace_body_sectPr_with_page_break(doc: Document) -> None:
    """将 body 中的所有 sectPr 替换为分页符。

    分节符会影响页眉页脚的继承，因此替换为分页符。
    分页符是一个包含 <w:br w:type="page"/> 的段落。

    sectPr 可能在两种位置：
    1. 段落内的 pPr > sectPr
    2. body 的直接子元素（body-level sectPr）

    Args:
        doc: python-docx Document 对象
    """
    W = common.W_NS
    body = doc.element.body

    # 创建分页符 XML
    page_break_p = W  # noqa

    def _make_page_break_para():
        """创建一个包含分页符的段落"""
        from lxml import etree
        # <w:p>
        p = etree.Element(f'{W}p')
        # <w:r>
        r = etree.SubElement(p, f'{W}r')
        # <w:br w:type="page"/>
        br = etree.SubElement(r, f'{W}br')
        br.set(f'{W}type', 'page')
        return p

    sectPrs_to_remove = []

    # 先收集所有 body-level sectPr 的位置
    elements = list(body)
    body_level_sectPrs = []
    for i, elem in enumerate(elements):
        if elem.tag == f'{W}sectPr':
            body_level_sectPrs.append((i, elem))

    # 最后一个 body-level sectPr 需要保留
    last_body_level_idx = body_level_sectPrs[-1][0] if body_level_sectPrs else None

    # 收集所有需要替换的 sectPr（跳过最后一个 body-level sectPr）
    for i, elem in enumerate(elements):
        if elem.tag == f'{W}p':
            pPr = elem.find(f'{W}pPr')
            if pPr is not None:
                sectPr = pPr.find(f'{W}sectPr')
                if sectPr is not None:
                    sectPrs_to_remove.append((i, elem, pPr, sectPr))
        elif elem.tag == f'{W}sectPr':
            # 跳过最后一个 body-level sectPr
            if i != last_body_level_idx:
                sectPrs_to_remove.append((i, elem, None, elem))

    # 反向遍历（从后往前）处理，避免索引变化问题
    for item in reversed(sectPrs_to_remove):
        idx, elem, pPr, sectPr = item

        # 在 sectPr 之前插入分页符
        page_break_para = _make_page_break_para()
        body.insert(idx, page_break_para)

        # 删除 sectPr
        if pPr is not None:
            pPr.remove(sectPr)
        else:
            body.remove(elem)

    if sectPrs_to_remove:
        print(f"  已将 body 中的 {len(sectPrs_to_remove)} 个分节符替换为分页符")


def insert_body_at_marker_compose(
    doc_path: str,
    body_path: str,
    marker: str,
    output_path: str,
    template_path: str = None,
) -> bool:
    """使用 docxcompose 三段式合并：在 marker 位置插入 body。

    模板已分为 4 个 section（封面/body/英文摘要/法律披露），
    每个 section 自带 sectPr（含 header/footer 引用）。
    body 内容插入 body section 后自动继承该 section 的 header/footer，
    无需额外处理页眉页脚。

    Args:
        doc_path: 渲染后的模板路径
        body_path: body 文档路径
        marker: 占位符标记
        output_path: 输出路径
        template_path: 原始模板路径（用于恢复文档末尾 sectPr）

    Returns:
        是否成功插入
    """
    if not DOCXCOMPOSE_AVAILABLE:
        print("  ⚠️ docxcompose 不可用，无法使用三段式合并")
        return False

    try:
        # docxcompose 会损坏 sectPrs，需要预先保存
        template_sectPrs = None
        if template_path:
            template_sectPrs = _save_all_template_sectPrs(template_path)

        part1_doc = Document(doc_path)
        part1_body = part1_doc.element.body
        part1_elements = list(part1_body)

        marker_idx = None
        for i, elem in enumerate(part1_elements):
            text = common.get_element_text(elem)
            if marker in text:
                marker_idx = i
                break

        if marker_idx is None:
            return False

        part1_path = Path(output_path).parent / "temp_part1.docx"
        for elem in part1_elements[marker_idx:]:
            if common.local_tag(elem) != 'sectPr':
                part1_body.remove(elem)
        part1_doc.save(str(part1_path))

        # 创建 part3（marker 之后的内容 = 英文摘要 + 法律披露 sections）
        part3_path = Path(output_path).parent / "temp_part3.docx"
        part3_doc = Document(doc_path)
        part3_body = part3_doc.element.body
        part3_elements = list(part3_body)

        has_part3_content = False
        for elem in part3_elements[:marker_idx + 1]:
            tag = common.local_tag(elem)
            if tag != 'sectPr':
                part3_body.remove(elem)

        for elem in part3_body:
            tag = common.local_tag(elem)
            if tag in ['p', 'tbl', 'sdt']:
                text = common.get_element_text(elem)
                if text.strip():
                    has_part3_content = True
                    break

        if has_part3_content:
            part3_doc.save(str(part3_path))

        # 合并：part1(封面) + body + part3(英文摘要+法律披露)
        master = Document(str(part1_path))
        composer = Composer(master)

        body_doc = Document(body_path)
        _replace_body_sectPr_with_page_break(body_doc)
        composer.append(body_doc, remove_property_fields=False)

        if has_part3_content:
            part3_for_merge = Document(str(part3_path))
            composer.append(part3_for_merge, remove_property_fields=False)

        composer.save(output_path)

        # 恢复所有 sectPrs（docxcompose 会损坏 header/footer rId 引用）
        if template_sectPrs is not None:
            _restore_all_sectPrs(output_path, template_sectPrs)

        # 复制 body 中的图片资源（修复 docxcompose 图片丢失）
        copied_count = _copy_media_between_docx(body_path, output_path)
        if copied_count > 0:
            print(f"  已补充复制 {copied_count} 张图片（修复 docxcompose 图片丢失）")

        # 清理临时文件
        part1_path.unlink(missing_ok=True)
        if has_part3_content:
            part3_path.unlink(missing_ok=True)

        return True

    except Exception as e:
        print(f"  docxcompose 三段式合并失败: {e}")
        import traceback
        traceback.print_exc()
        return False
