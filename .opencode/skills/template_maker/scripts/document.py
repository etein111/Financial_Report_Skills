"""文档分析函数。

用于查找摘要位置、正文范围、附录标记等。
"""

import re
from typing import Dict, Any
from docx import Document


# ==================== 摘要查找 ====================

def find_abstract_by_elements(doc_path: str, elements: dict) -> Dict[str, Any]:
    """根据 elements.yaml 中定义的字段，智能查找摘要位置。

    摘要判断逻辑：
    1. 摘要是一段连贯的文本，包含投资观点、核心分析结论
    2. 摘要不包含评级(RATING)、目标价(TARGET PRICE)等单独字段
    3. 摘要通常是自然段落，不是表格中的键值对
    4. 跳过标题字段（title, title_ch, title_en），避免将标题误判为摘要

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
    doc = Document(doc_path)

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
        for para_idx, para in enumerate(doc.paragraphs):
            if field_value in para.text:
                # 检查这个段落是否像摘要（长文本，没有明显的键值对格式）
                if _is_likely_abstract_paragraph(para.text, field_value):
                    return {
                        "found": True,
                        "table": None,
                        "row": None,
                        "col_start": None,
                        "col_end": None,
                        "start_paragraph": para_idx,
                        "context": f"段落 {para_idx}: {para.text[:50]}..."
                    }

        # 在表格中搜索
        for tbl_idx, table in enumerate(doc.tables):
            for row_idx, row in enumerate(table.rows):
                for col_idx, cell in enumerate(row.cells):
                    if field_value in cell.text:
                        # 检查这个单元格是否像摘要
                        if _is_likely_abstract_cell(cell, field_value):
                            return {
                                "found": True,
                                "table": tbl_idx,
                                "row": row_idx,
                                "col_start": col_idx,
                                "col_end": col_idx,
                                "context": f"表格 {tbl_idx} 行 {row_idx} 列 {col_idx}: {cell.text[:50]}..."
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


def _is_likely_abstract_cell(cell, field_value: str) -> bool:
    """判断单元格是否像摘要。

    Args:
        cell: 单元格对象
        field_value: 字段值

    Returns:
        True 如果像摘要
    """
    cell_text = cell.text

    # 如果单元格只有一个段落，且包含字段值，可能是摘要
    if len(cell.paragraphs) == 1:
        return True

    # 如果单元格文本较短，可能不是摘要
    if len(cell_text) < 100:
        return False

    return True


# ==================== 正文范围查找 ====================

def find_body_range_by_sections(doc_path: str) -> Dict[str, Any]:
    """根据分节符位置确定正文范围。

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
    from lxml import etree

    doc = Document(doc_path)
    body = doc._body._body

    # 收集所有段落的 pPr（段落属性）及其索引
    paragraphs = list(doc.paragraphs)
    sect_pr_indices = []  # [(paragraph_index, sect_pr_element), ...]

    for para_idx, para in enumerate(paragraphs):
        # 检查段落是否有分节符
        pPr = para._element.find('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}pPr')
        if pPr is not None:
            sect_pr = pPr.find('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}sectPr')
            if sect_pr is not None:
                sect_pr_indices.append((para_idx, sect_pr))

    # 如果有分节符，以最后一个分节符之后作为正文结束
    if sect_pr_indices:
        last_sect_idx = sect_pr_indices[-1][0]
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
        "end_paragraph": len(doc.paragraphs),
        "context": f"正文范围: 段落 0 到 {len(doc.paragraphs) - 1}（整个文档）"
    }


# ==================== 附录查找 ====================

def find_appendix_by_markers(doc_path: str) -> Dict[str, Any]:
    """根据标记词查找附录（法律披露）位置。

    支持的附录标记：
    1. 中文标记："附录APPENDIX"、"附录 APPENDIX"
    2. 英文标记：APPENDIX 开头的大写标题
    3. 重要披露："IMPORTANT DISCLOSURES"、"重要信息披露"

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
    import zipfile
    from lxml import etree

    W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'

    # 直接解析 document.xml 以获取所有内容（包括 python-docx 漏读的表格）
    with zipfile.ZipFile(doc_path, 'r') as z:
        with z.open('word/document.xml') as f:
            tree = etree.parse(f)

    # 附录关键词（用于搜索 w:t 元素）
    appendix_keywords = ['附录APPENDIX', 'IMPORTANT DISCLOSURE']

    # 先搜索段落中的附录标记
    for idx, p in enumerate(tree.iter(f'{W}p')):
        text = ''.join(t.text or '' for t in p.iter(f'{W}t'))
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

    # 搜索表格中的附录标记（使用 lxml 直接解析，避免 python-docx 漏读问题）
    for tbl in tree.iter(f'{W}tbl'):
        # 获取表格标题
        caption = tbl.find(f'{W}tblPr/{W}tblCaption')
        caption_val = caption.get(f'{W}val') if caption is not None else ''

        # 遍历表格所有单元格
        for row_idx, tr in enumerate(tbl.findall(f'{W}tr')):
            for col_idx, tc in enumerate(tr.findall(f'{W}tc')):
                cell_text = ''.join(t.text or '' for t in tc.iter(f'{W}t'))
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
    doc = Document(doc_path)

    for i, para in enumerate(doc.paragraphs):
        text = para.text.strip()
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
    doc = Document(doc_path)

    # 在段落中搜索
    for idx, para in enumerate(doc.paragraphs):
        if field_value in para.text:
            return {
                "found": True,
                "type": "paragraph",
                "index": idx,
                "context": f"段落 {idx}: {para.text[:50]}..."
            }

    # 在表格中搜索
    for tbl_idx, table in enumerate(doc.tables):
        for row_idx, row in enumerate(table.rows):
            for col_idx, cell in enumerate(row.cells):
                if field_value in cell.text:
                    return {
                        "found": True,
                        "type": "table",
                        "index": tbl_idx,
                        "row": row_idx,
                        "col": col_idx,
                        "context": f"表格 {tbl_idx} 行 {row_idx} 列 {col_idx}: {cell.text[:50]}..."
                    }

    # 在页眉页脚中搜索
    for section_idx, section in enumerate(doc.sections):
        for para_idx, para in enumerate(section.header.paragraphs):
            if field_value in para.text:
                return {
                    "found": True,
                    "type": "header",
                    "index": section_idx,
                    "context": f"节 {section_idx} 页眉: {para.text[:50]}..."
                }
        for para_idx, para in enumerate(section.footer.paragraphs):
            if field_value in para.text:
                return {
                    "found": True,
                    "type": "footer",
                    "index": section_idx,
                    "context": f"节 {section_idx} 页脚: {para.text[:50]}..."
                }

    return {"found": False, "reason": f"未找到字段 {field_name} 的内容"}
