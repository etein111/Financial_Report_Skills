"""文档分析函数。

用于查找摘要位置、正文范围、附录标记等。

使用 lxml 直接解析 document.xml，确保嵌套表格也能完整读取。
"""

import re
import zipfile
from typing import Dict, Any, List, Optional, Tuple
from lxml import etree


W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'


def _parse_docx_xml(doc_path: str) -> etree._Element:
    """直接解析 document.xml，完整读取所有内容（包括嵌套表格）。

    Args:
        doc_path: docx 文件路径

    Returns:
        document.xml 的根元素
    """
    with zipfile.ZipFile(doc_path, 'r') as z:
        with z.open('word/document.xml') as f:
            return etree.parse(f).getroot()


def _get_paragraphs_and_tables(tree: etree._Element) -> Tuple[List[etree._Element], List[etree._Element]]:
    """获取所有段落和表格元素。

    直接从 XML 结构中提取，避免 python-docx 漏读问题。

    Args:
        tree: document.xml 根元素

    Returns:
        (paragraphs, tables) 元组
    """
    paragraphs = list(tree.iter(f'{W}p'))
    tables = list(tree.iter(f'{W}tbl'))
    return paragraphs, tables


def _get_para_text(para: etree._Element) -> str:
    """获取段落的所有文本。

    Args:
        para: 段落元素

    Returns:
        段落文本
    """
    return ''.join(t.text or '' for t in para.iter(f'{W}t'))


def _get_cell_text(tc: etree._Element) -> str:
    """获取单元格的所有文本（包括嵌套表格）。

    Args:
        tc: 单元格元素

    Returns:
        单元格文本
    """
    texts = []
    for t in tc.iter(f'{W}t'):
        if t.text:
            texts.append(t.text)
    return ''.join(texts)


def _get_table_cells(table: etree._Element) -> List[List[str]]:
    """获取表格所有单元格的文本。

    Args:
        table: 表格元素

    Returns:
        二维列表，每行是单元格文本列表
    """
    rows = []
    for tr in table.findall(f'{W}tr'):
        cells = []
        for tc in tr.findall(f'{W}tc'):
            cells.append(_get_cell_text(tc))
        rows.append(cells)
    return rows


# ==================== 摘要查找 ====================

def find_abstract_by_elements(doc_path: str, elements: dict) -> Dict[str, Any]:
    """根据 elements.yaml 中定义的字段，智能查找摘要位置。

    摘要判断逻辑：
    1. 摘要是一段连贯的文本，包含投资观点、核心分析结论
    2. 摘要不包含评级(RATING)、目标价(TARGET PRICE)等单独字段
    3. 摘要通常是自然段落，不是表格中的键值对
    4. 跳过标题字段（title, title_ch, title_en），避免将标题误判为摘要

    使用 lxml 直接解析，确保嵌套表格不漏读。

    Args:
        doc_path: 文档路径
        elements: elements.yaml 内容

    Returns:
        {
            "found": bool,
            "table": int,       # 表格索引（如果有的话）
            "row": int,         # 行索引
            "col_start": int,   # 起始列
            "col_end": int,     # 结束列
            "context": str      # 上下文描述
        }
    """
    tree = _parse_docx_xml(doc_path)
    paragraphs, tables = _get_paragraphs_and_tables(tree)

    # 收集所有字段值用于匹配
    field_values = []
    for field_name, field_value in elements.items():
        if field_value and isinstance(field_value, str) and len(field_value) > 5:
            field_values.append((field_name, field_value.strip()))

    # 按长度降序排列（优先匹配更长的文本）
    field_values.sort(key=lambda x: len(x[1]), reverse=True)

    # 在文档中搜索字段值对应的位置
    for field_name, field_value in field_values:
        # 跳过分析师相关字段（不适合作为摘要内容）
        if field_name.startswith('a') and any(s in field_name for s in ['_cn', '_en', '_sfc', '_email']):
            continue

        # 跳过标题相关字段（标题不是摘要）
        if field_name in ('title', 'title_ch', 'title_en'):
            continue

        # 在段落中搜索
        for para_idx, para in enumerate(paragraphs):
            para_text = _get_para_text(para)
            if field_value in para_text:
                # 检查这个段落是否像摘要（长文本，没有明显的键值对格式）
                if _is_likely_abstract_paragraph(para_text, field_value):
                    return {
                        "found": True,
                        "table": None,
                        "row": None,
                        "col_start": None,
                        "col_end": None,
                        "start_paragraph": para_idx,
                        "context": f"段落 {para_idx}: {para_text[:50]}..."
                    }

        # 在表格中搜索（使用 lxml，嵌套表格不漏读）
        for tbl_idx, table in enumerate(tables):
            for row_idx, row in enumerate(table.findall(f'{W}tr')):
                for col_idx, tc in enumerate(row.findall(f'{W}tc')):
                    cell_text = _get_cell_text(tc)
                    if field_value in cell_text:
                        # 检查这个单元格是否像摘要
                        if _is_likely_abstract_cell_text(cell_text, field_value, tc):
                            return {
                                "found": True,
                                "table": tbl_idx,
                                "row": row_idx,
                                "col_start": col_idx,
                                "col_end": col_idx,
                                "context": f"表格 {tbl_idx} 行 {row_idx} 列 {col_idx}: {cell_text[:50]}..."
                            }

    return {"found": False, "reason": "未找到匹配的摘要内容"}


def _is_likely_abstract_paragraph(text: str, field_value: str) -> bool:
    """判断段落是否像摘要。

    Args:
        text: 段落完整文本
        field_value: 字段值

    Returns:
        True 如果像摘要
    """
    # 检查是否有键值对格式的标记（如冒号后是短文本）
    lines = text.split('\n')
    for line in lines:
        if ':' in line:
            parts = line.split(':', 1)
            if len(parts) == 2 and len(parts[1].strip()) < 50:
                # 这更像是键值对，不是摘要
                return False

    # 摘要通常是较长的文本
    if len(field_value) < 100:
        return False

    return True


def _is_likely_abstract_cell_text(cell_text: str, field_value: str, tc: etree._Element = None) -> bool:
    """判断单元格是否像摘要。

    Args:
        cell_text: 单元格文本
        field_value: 字段值
        tc: 单元格元素（可选，用于检查段落数量）

    Returns:
        True 如果像摘要
    """
    # 如果单元格文本较短，可能不是摘要
    if len(cell_text) < 100:
        return False

    # 如果提供了元素，检查段落数量
    if tc is not None:
        # 计算单元格中的段落数量
        para_count = len(list(tc.iter(f'{W}p')))
        if para_count == 1:
            return True

    return True


# ==================== 正文范围查找 ====================

def find_body_range_by_sections(doc_path: str) -> Dict[str, Any]:
    """根据分节符位置确定正文范围。

    使用 lxml 直接解析 document.xml，确保完整读取。

    Args:
        doc_path: 文档路径

    Returns:
        {
            "found": bool,
            "start_paragraph": int,
            "end_paragraph": int,
            "context": str
        }
    """
    tree = _parse_docx_xml(doc_path)
    paragraphs = list(tree.iter(f'{W}p'))
    sect_pr_indices = []  # [paragraph_index, ...]

    for para_idx, para in enumerate(paragraphs):
        # 检查段落是否有分节符
        pPr = para.find(f'{W}pPr')
        if pPr is not None:
            sect_pr = pPr.find(f'{W}sectPr')
            if sect_pr is not None:
                sect_pr_indices.append(para_idx)

    # 如果有分节符，以最后一个分节符之后作为正文结束
    if sect_pr_indices:
        last_sect_idx = sect_pr_indices[-1]
        return {
            "found": True,
            "start_paragraph": 0,  # 正文从第一段开始
            "end_paragraph": last_sect_idx + 1,
            "context": f"正文范围: 段落 0 到 {last_sect_idx}（分节符之前）"
        }

    # 如果没有分节符，返回整个文档
    return {
        "found": True,
        "start_paragraph": 0,
        "end_paragraph": len(paragraphs),
        "context": f"正文范围: 段落 0 到 {len(paragraphs) - 1}（整个文档）"
    }


# ==================== 附录查找 ====================

def find_appendix_by_markers(doc_path: str) -> Dict[str, Any]:
    """根据标记词查找附录（法律披露）位置。

    支持的附录标记：
    1. 中文标记："附录APPENDIX"、"附录 APPENDIX"
    2. 英文标记：APPENDIX 开头的大写标题
    3. 重要披露："IMPORTANT DISCLOSURES"、"重要信息披露"

    使用 lxml 直接解析 document.xml，确保嵌套表格不漏读。

    Args:
        doc_path: 文档路径

    Returns:
        {
            "found": bool,
            "start_paragraph": int,
            "preview": list[str],
            "has_page_break_before": bool,
            "context": str
        }
    """
    tree = _parse_docx_xml(doc_path)

    # 附录关键词（用于搜索 w:t 元素）
    appendix_keywords = ['附录APPENDIX', 'IMPORTANT DISCLOSURE']

    # 先搜索段落中的附录标记
    for idx, p in enumerate(tree.iter(f'{W}p')):
        text = _get_para_text(p)
        for kw in appendix_keywords:
            if kw in text.upper():
                # 检查前面是否有分页符
                has_page_break = False
                pPr = p.find(f'{W}pPr')
                if pPr is not None:
                    last_pPr = list(pPr.iter())[-1] if len(list(pPr)) > 0 else None
                    if last_pPr is not None and etree.QName(last_pPr.tag).localname == 'lastRenderedPageBreak':
                        has_page_break = True

                return {
                    "found": True,
                    "start_paragraph": idx,
                    "preview": [text[:100] if text else ''],
                    "has_page_break_before": has_page_break,
                    "context": f"段落 {idx}: {text[:50]}"
                }

    # 搜索表格中的附录标记
    for tbl in tree.iter(f'{W}tbl'):
        # 获取表格标题
        caption = tbl.find(f'{W}tblPr/{W}tblCaption')
        caption_val = caption.get(f'{W}val') if caption is not None else ''

        # 遍历表格所有单元格
        for row_idx, tr in enumerate(tbl.findall(f'{W}tr')):
            for col_idx, tc in enumerate(tr.findall(f'{W}tc')):
                cell_text = _get_cell_text(tc)
                for kw in appendix_keywords:
                    if kw in cell_text.upper():
                        return {
                            "found": True,
                            "start_paragraph": None,
                            "table_caption": caption_val,
                            "row": row_idx,
                            "col": col_idx,
                            "preview": [cell_text[:100] if cell_text else ''],
                            "has_page_break_before": False,
                            "context": f"表格 {caption_val} 行 {row_idx} 列 {col_idx}: {cell_text[:50]}"
                        }

    return {"found": False, "reason": "未找到附录标记"}


def find_first_appendix_position(doc_path: str) -> Dict[str, Any]:
    """找到文档中第一个 APPENDIX 标题的位置。

    这个函数用于确定正文的结束位置。正文应该在第一个 APPENDIX 标题之前结束，
    无论这个 APPENDIX 是内容附录（如 "APPENDIX 1 Summary"）还是法律附录
    （如 "附录APPENDIX 重要信息披露"）。

    使用 lxml 直接解析 document.xml，确保嵌套表格不漏读。

    Args:
        doc_path: 文档路径

    Returns:
        {
            "found": bool,
            "start_paragraph": int,
            "text": str,
            "context": str
        }
    """
    tree = _parse_docx_xml(doc_path)
    paragraphs = list(tree.iter(f'{W}p'))

    for i, para in enumerate(paragraphs):
        text = _get_para_text(para).strip()
        text_upper = text.upper()

        if not text:
            continue

        is_appendix_title = False

        # 1. 中英混合格式（如 "附录APPENDIX 重要信息披露"）
        if '附录' in text and 'APPENDIX' in text_upper:
            is_appendix_title = True
        # 2. 纯英文 APPENDIX 开头（如 "APPENDIX 1 Summary"）
        elif text_upper.startswith('APPENDIX'):
            is_appendix_title = True
        # 3. IMPORTANT DISCLOSURES
        elif 'IMPORTANT DISCLOSURE' in text_upper:
            is_appendix_title = True
        # 4. 独立的中文"附录"（后面没有其他内容）
        elif text.startswith('附录') and len(text) < 50:
            is_appendix_title = True

        if is_appendix_title:
            return {
                "found": True,
                "start_paragraph": i,
                "text": text[:100],
                "context": f"段落 {i}: {text[:50]}"
            }

    return {"found": False, "reason": "未找到 APPENDIX 相关标题"}


# ==================== 辅助函数 ====================

def find_content_location(doc_path: str, field_name: str, field_value: str) -> Dict[str, Any]:
    """查找特定字段内容在文档中的位置。

    使用 lxml 直接解析 document.xml，确保嵌套表格不漏读。

    Args:
        doc_path: 文档路径
        field_name: 字段名
        field_value: 字段值

    Returns:
        {
            "found": bool,
            "type": "paragraph" | "table" | "header" | "footer",
            "index": int,  # 段落索引或表格索引
            "row": int,    # 如果是表格，则为行索引
            "col": int,    # 如果是表格，则为列索引
            "context": str
        }
    """
    tree = _parse_docx_xml(doc_path)

    # 在段落中搜索
    paragraphs = list(tree.iter(f'{W}p'))
    for idx, para in enumerate(paragraphs):
        para_text = _get_para_text(para)
        if field_value in para_text:
            return {
                "found": True,
                "type": "paragraph",
                "index": idx,
                "context": f"段落 {idx}: {para_text[:50]}..."
            }

    # 在表格中搜索（包括嵌套表格）
    for tbl_idx, table in enumerate(tree.iter(f'{W}tbl')):
        for row_idx, tr in enumerate(table.findall(f'{W}tr')):
            for col_idx, tc in enumerate(tr.findall(f'{W}tc')):
                cell_text = _get_cell_text(tc)
                if field_value in cell_text:
                    return {
                        "found": True,
                        "type": "table",
                        "index": tbl_idx,
                        "row": row_idx,
                        "col": col_idx,
                        "context": f"表格 {tbl_idx} 行 {row_idx} 列 {col_idx}: {cell_text[:50]}..."
                    }

    # 在页眉页脚中搜索（需要从 docx 中读取 header/footer）
    try:
        import zipfile
        for section_idx, section in enumerate(_iter_sections(doc_path)):
            for part_name in ['header', 'footer']:
                part = _get_section_part(section, part_name)
                if part is None:
                    continue
                for para in part.iter(f'{W}p'):
                    para_text = _get_para_text(para)
                    if field_value in para_text:
                        return {
                            "found": True,
                            "type": part_name,
                            "index": section_idx,
                            "context": f"节 {section_idx} {part_name}: {para_text[:50]}..."
                        }
    except Exception:
        # 如果读取页眉页脚失败，跳过这个来源
        pass

    return {"found": False, "reason": f"未找到字段 {field_name} 的内容"}


def _iter_sections(doc_path: str):
    """迭代文档中的所有 section 元素。

    Args:
        doc_path: docx 文件路径

    Yields:
        section 元素
    """
    with zipfile.ZipFile(doc_path, 'r') as z:
        # 获取 section 数量
        doc_xml = z.read('word/document.xml')
        tree = etree.fromstring(doc_xml)
        body = tree.find(f'{W}body')
        if body is not None:
            for sectPr in body.iter(f'{W}sectPr'):
                yield sectPr


def _get_section_part(section: etree._Element, part_name: str) -> Optional[etree._Element]:
    """获取 section 的页眉或页脚部分。

    Args:
        section: sectPr 元素
        part_name: 'header' 或 'footer'

    Returns:
        header/footer 元素，如果不存在返回 None
    """
    # 查找 headerReference 或 footerReference
    ref_name = f'{W}{part_name}Reference'
    ref = section.find(ref_name)
    if ref is None:
        return None

    # 获取 ID
    id_attr = f'{W}id'
    rid = ref.get(id_attr)
    if rid is None:
        return None

    # 从 relationships 中查找实际文件
    # 这需要读取 .rels 文件，但 lxml 不能直接处理
    # 回退：返回 None
    return None
