"""文档分析函数。

用于分析 Word 文档结构、定位内容、获取段落和表格信息。
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Any
from docx import Document


def find_content_location(doc_path: str, search_text: str) -> Dict[str, Any]:
    """在文档中查找指定文本的位置。

    Args:
        doc_path: Word 文档路径
        search_text: 要搜索的文本

    Returns:
        位置信息：
        {
            "found": bool,
            "type": str,             # "table" 或 "paragraph"
            "table": int,
            "row": int,
            "col": int,
            "index": int,
            "context": str
        }
    """
    doc = Document(doc_path)

    # 在表格中搜索
    for table_idx, table in enumerate(doc.tables):
        for row_idx, row in enumerate(table.rows):
            for col_idx, cell in enumerate(row.cells):
                if search_text in cell.text:
                    return {
                        "found": True,
                        "type": "table",
                        "table": table_idx,
                        "row": row_idx,
                        "col": col_idx,
                        "context": f"在表格 {table_idx} 的第 {row_idx} 行第 {col_idx} 列"
                    }

    # 在段落中搜索
    for para_idx, para in enumerate(doc.paragraphs):
        if search_text in para.text:
            return {
                "found": True,
                "type": "paragraph",
                "index": para_idx,
                "context": f"在段落 {para_idx}"
            }

    return {"found": False, "context": "未找到"}


def get_document_structure(doc_path: str) -> Dict[str, Any]:
    """获取文档结构信息。

    Args:
        doc_path: Word 文档路径

    Returns:
        文档结构：
        {
            "paragraphs_count": int,
            "tables_count": int,
            "sections": List[int],
            "tables": List[Dict],
        }
    """
    doc = Document(doc_path)

    # 检测分节边界
    section_boundaries = _detect_section_boundaries(doc)

    # 获取表格信息
    tables_info = []
    for table_idx, table in enumerate(doc.tables):
        tables_info.append({
            "index": table_idx,
            "rows": len(table.rows),
            "cols": len(table.columns)
        })

    return {
        "paragraphs_count": len(doc.paragraphs),
        "tables_count": len(doc.tables),
        "sections": section_boundaries,
        "tables": tables_info
    }


def get_table_content(doc_path: str, table_idx: int, max_rows: int = 5) -> Dict[str, Any]:
    """获取指定表格的内容。

    Args:
        doc_path: Word 文档路径
        table_idx: 表格索引
        max_rows: 最多返回几行内容

    Returns:
        表格内容：
        {
            "index": int,
            "rows": int,
            "cols": int,
            "content": List[List[str]]
        }
    """
    doc = Document(doc_path)
    table = doc.tables[table_idx]

    content = []
    for row_idx, row in enumerate(table.rows[:max_rows]):
        row_content = []
        for cell in row.cells:
            row_content.append(cell.text.strip()[:50])
        content.append(row_content)

    return {
        "index": table_idx,
        "rows": len(table.rows),
        "cols": len(table.columns),
        "content": content
    }


def get_paragraphs_content(doc_path: str, start: int, end: int) -> List[str]:
    """获取指定段落范围的内容。

    Args:
        doc_path: Word 文档路径
        start: 起始段落索引
        end: 结束段落索引（不包含）

    Returns:
        段落文本列表
    """
    doc = Document(doc_path)
    contents = []

    for i in range(start, min(end, len(doc.paragraphs))):
        text = doc.paragraphs[i].text.strip()
        contents.append(f"段落 {i}: {text[:100]}")

    return contents


def find_abstract_by_elements(doc_path: str, elements: Dict[str, Any]) -> Dict[str, Any]:
    """根据 elements.yaml 的字段值定位摘要位置。

    策略：
    1. 优先使用 company 字段定位
    2. 找到字段值所在的表格
    3. 在该表格中查找长文本（摘要）

    Args:
        doc_path: Word 文档路径
        elements: elements.yaml 的内容

    Returns:
        摘要位置信息
    """
    doc = Document(doc_path)

    # 优先使用 company 字段，其次 title，最后用第一个非分析师字段
    search_value = None
    for field_name in ['company', 'title', 'ticker']:
        if field_name in elements and elements[field_name]:
            search_value = str(elements[field_name])
            break

    if not search_value:
        # 回退到第一个非 analysts 字段
        for k, v in elements.items():
            if v and not k.startswith('a') and not k.startswith('analyst'):
                search_value = str(v)
                break

    if not search_value:
        return {"found": False, "reason": "未找到可用的定位字段"}

    # 找到字段值所在位置
    location = find_content_location(doc_path, search_value)
    if not location["found"]:
        return {"found": False, "reason": "未找到字段值"}

    if location["type"] != "table":
        return {"found": False, "reason": "字段值不在表格中"}

    # 在该表格中查找长文本（摘要）
    table_idx = location["table"]
    table = doc.tables[table_idx]

    for row_idx, row in enumerate(table.rows):
        for col_idx, cell in enumerate(row.cells):
            text = cell.text.strip()
            # 摘要通常是长文本（> 50 字符）
            if len(text) > 50:
                col_end = col_idx
                for c in range(col_idx + 1, len(row.cells)):
                    if row.cells[c].text.strip():
                        col_end = c
                    else:
                        break

                return {
                    "found": True,
                    "table": table_idx,
                    "row": row_idx,
                    "col_start": col_idx,
                    "col_end": col_end,
                    "preview": text[:100],
                    "context": f"在表格 {table_idx} 第 {row_idx} 行，列 {col_idx}-{col_end}"
                }

    return {"found": False, "reason": "表格中未找到长文本"}


def find_body_range_by_sections(doc_path: str) -> Dict[str, Any]:
    """根据分节结构定位正文范围（包含目录）。

    策略：
    - 分节 0: 封面/标题
    - 分节 1: 目录页（包含在 body 中）
    - 分节 2: 正文内容
    - 分节 3: 附录

    Body 从分节 1 开始（首页之后），包含目录和正文内容。

    Args:
        doc_path: Word 文档路径

    Returns:
        正文范围信息
    """
    doc = Document(doc_path)
    section_paragraphs = _get_section_paragraphs(doc)

    if len(section_paragraphs) < 2:
        return {
            "found": False,
            "reason": f"分节数量不足（{len(section_paragraphs)} 个），需要至少 2 个分节"
        }

    # Body 从分节 1 开始（包含目录）
    if 1 not in section_paragraphs or not section_paragraphs[1]:
        return {"found": False, "reason": "未找到分节 1"}

    start_idx = section_paragraphs[1][0]

    # 正文结束位置
    end_idx = len(doc.paragraphs)

    # 如果有分节 3，正文在分节 3 开始之前结束
    if 3 in section_paragraphs and section_paragraphs[3]:
        end_idx = section_paragraphs[3][0]

    return {
        "found": True,
        "start_paragraph": start_idx,
        "end_paragraph": end_idx,
        "paragraphs_count": end_idx - start_idx,
        "context": f"段落 {start_idx} 到 {end_idx}，共 {end_idx - start_idx} 个段落"
    }


def find_appendix_by_markers(doc_path: str) -> Dict[str, Any]:
    """根据标记词定位法律披露附录。

    法律附录识别规则：
    - 前面有分页符（单独一页）
    - 开头必定是："附录APPENDIX"
    - 结尾是整个文档的结尾

    策略：
    1. 使用 lxml 直接解析 document.xml 搜索"附录APPENDIX"
    2. 可能在段落或表格单元格中
    3. 检查该位置是否前面有分页符（sectPr type=nextPage）
    4. 返回附录的起始位置和内容预览

    Args:
        doc_path: Word 文档路径

    Returns:
        附录位置信息
    """
    import zipfile
    from lxml import etree

    ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}

    # 直接解析 document.xml 搜索
    with zipfile.ZipFile(doc_path, 'r') as z:
        with z.open('word/document.xml') as f:
            tree = etree.parse(f)

    # 搜索包含"附录APPENDIX"的段落或单元格
    target_text = '附录APPENDIX'
    appendix_elem = None
    appendix_location_type = None  # "paragraph" 或 "table_cell"

    # 先搜索段落
    for i, para in enumerate(tree.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p')):
        text = ''.join(para.itertext())
        if target_text in text or ('附录' in text.upper() and 'APPENDIX' in text.upper()):
            appendix_elem = para
            appendix_location_type = "paragraph"
            break

    # 如果段落里没找到，搜索表格单元格
    if appendix_elem is None:
        for tc in tree.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tc'):
            text = ''.join(tc.itertext())
            if target_text in text or ('附录' in text.upper() and 'APPENDIX' in text.upper()):
                appendix_elem = tc
                appendix_location_type = "table_cell"
                break

    if appendix_elem is None:
        return {
            "found": False,
            "reason": "未找到包含'附录APPENDIX'的段落或单元格"
        }

    # 找到 appendix_elem 在 body 中的位置索引
    body = tree.getroot()
    all_paragraphs = list(body.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p'))
    all_tables = list(body.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tbl'))

    if appendix_location_type == "paragraph":
        try:
            appendix_idx = all_paragraphs.index(appendix_elem)
        except ValueError:
            appendix_idx = -1
    else:
        # 表格单元格：在所有表格中找位置
        appendix_idx = -1
        for t_idx, tbl in enumerate(all_tables):
            for r_idx, tr in enumerate(tbl.findall('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tr')):
                for c_idx, tc in enumerate(tr.findall('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tc')):
                    if tc is appendix_elem:
                        appendix_idx = t_idx * 1000 + r_idx * 100 + c_idx  # 用编码表示位置

    # 检查前面是否有分页符
    has_page_break_before = False
    prev_sectPr = None

    if appendix_location_type == "paragraph":
        # 找前一个段落的 sectPr
        if appendix_idx > 0:
            prev_para = all_paragraphs[appendix_idx - 1]
            pPr = prev_para.find('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}pPr')
            if pPr is not None:
                sectPr = pPr.find('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}sectPr')
                if sectPr is not None:
                    sect_type = sectPr.find('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}type')
                    if sect_type is not None and sect_type.get('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val') == 'nextPage':
                        has_page_break_before = True
    else:
        # 表格单元格：找前一个段落
        tbl = appendix_elem.getparent().getparent()  # tc -> tr -> tbl
        tbl_idx = list(body.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tbl')).index(tbl)

        # 如果表格前面有段落，检查是否有分页符
        if tbl_idx > 0:
            prev_para = all_paragraphs[tbl_idx - 1] if tbl_idx <= len(all_paragraphs) else None
            if prev_para is not None:
                pPr = prev_para.find('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}pPr')
                if pPr is not None:
                    sectPr = pPr.find('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}sectPr')
                    if sectPr is not None:
                        sect_type = sectPr.find('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}type')
                        if sect_type is not None and sect_type.get('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val') == 'nextPage':
                            has_page_break_before = True

    # 获取附录文本内容
    appendix_text = ''.join(appendix_elem.itertext())
    if len(appendix_text) > 100:
        appendix_text_preview = appendix_text[:100]
    else:
        appendix_text_preview = appendix_text

    # 构建预览（从附录元素后的内容）
    preview = []
    if appendix_location_type == "paragraph":
        # 从当前段落开始，收集后续段落的文本
        for i in range(appendix_idx, min(appendix_idx + 3, len(all_paragraphs))):
            text = ''.join(all_paragraphs[i].itertext()).strip()
            if text:
                preview.append(text[:80])
    else:
        # 表格单元格，收集单元格内容
        full_text = ''.join(appendix_elem.itertext())
        preview.append(full_text[:80])

    return {
        "found": True,
        "location_type": appendix_location_type,
        "element_index": appendix_idx,
        "has_page_break_before": has_page_break_before,
        "text": appendix_text_preview,
        "preview": preview,
        "context": f"{appendix_location_type} 中找到'附录APPENDIX'"
    }


def find_elements_yaml(word_path: Path | str) -> Path | None:
    """查找与 Word 文件配对的 elements.yaml。

    Args:
        word_path: Word 文件路径（Path 或 str）

    Returns:
        找到的 elements.yaml 路径，未找到返回 None
    """
    word_path = Path(word_path) if isinstance(word_path, str) else word_path
    word_dir = word_path.parent
    word_name = word_path.stem

    candidates = [
        word_dir / f"{word_name} elements.yaml",
        word_dir / f"{word_name}_elements.yaml",
        word_dir / "elements.yaml",
    ]

    for candidate in candidates:
        if candidate.exists():
            return candidate

    return None


# 辅助函数

def _detect_section_boundaries(doc: Document) -> List[int]:
    """检测所有分节边界的段落索引。

    分节边界是段落属性中包含 sectPr 的段落。
    """
    section_boundaries = []

    for i, paragraph in enumerate(doc.paragraphs):
        pPr = paragraph._element.pPr
        if pPr is not None:
            sectPr = pPr.find('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}sectPr')
            if sectPr is not None:
                section_boundaries.append(i)

    return section_boundaries


def _get_section_paragraphs(doc: Document) -> Dict[int, List[int]]:
    """获取每个分节包含的段落索引范围。

    Returns:
        字典，键为分节索引，值为段落索引列表
    """
    section_boundaries = _detect_section_boundaries(doc)

    section_paragraphs = {}
    current_section = 0

    for i in range(len(doc.paragraphs)):
        if i in section_boundaries:
            if current_section not in section_paragraphs:
                section_paragraphs[current_section] = []
            section_paragraphs[current_section].append(i)
            current_section += 1
        else:
            if current_section not in section_paragraphs:
                section_paragraphs[current_section] = []
            section_paragraphs[current_section].append(i)

    return section_paragraphs
