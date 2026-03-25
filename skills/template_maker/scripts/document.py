"""文档分析函数。

用于分析 Word 文档结构、定位内容、获取段落和表格信息。
"""

from pathlib import Path
from typing import Dict, List, Any, Union, Optional
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
            "type": str,             # "table", "nested_table" 或 "paragraph"
            "table": int,
            "row": int,
            "col": int,
            "index": int,
            "context": str,
            "nested": bool,          # 是否在嵌套表格中
            "nested_table": int,     # 嵌套表格索引
            "nested_row": int,       # 嵌套表格行索引
            "nested_col": int,       # 嵌套表格列索引
        }
    """
    doc = Document(doc_path)

    # 在表格中搜索（包括嵌套表格）
    for table_idx, table in enumerate(doc.tables):
        for row_idx, row in enumerate(table.rows):
            for col_idx, cell in enumerate(row.cells):
                # 先搜索嵌套表格
                for nested_idx, nested_table in enumerate(cell.tables):
                    for n_row_idx, n_row in enumerate(nested_table.rows):
                        for n_col_idx, n_cell in enumerate(n_row.cells):
                            if search_text in n_cell.text:
                                return {
                                    "found": True,
                                    "type": "nested_table",
                                    "table": table_idx,
                                    "row": row_idx,
                                    "col": col_idx,
                                    "nested": True,
                                    "nested_table": nested_idx,
                                    "nested_row": n_row_idx,
                                    "nested_col": n_col_idx,
                                    "context": f"在表格 {table_idx} 第 {row_idx} 行第 {col_idx} 列的嵌套表格中"
                                }

                # 再搜索单元格本身
                if search_text in cell.text:
                    return {
                        "found": True,
                        "type": "table",
                        "table": table_idx,
                        "row": row_idx,
                        "col": col_idx,
                        "nested": False,
                        "context": f"在表格 {table_idx} 的第 {row_idx} 行第 {col_idx} 列"
                    }

    # 在段落中搜索
    for para_idx, para in enumerate(doc.paragraphs):
        if search_text in para.text:
            return {
                "found": True,
                "type": "paragraph",
                "index": para_idx,
                "nested": False,
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
    1. 先找到字段值所在的表格
    2. 在该表格中查找长文本（摘要）
    3. 收集同一列中所有后续的摘要段落

    Args:
        doc_path: Word 文档路径
        elements: elements.yaml 的内容

    Returns:
        摘要位置信息，包含起止行范围
    """
    doc = Document(doc_path)

    # 取第一个字段值作为定位点
    if not elements:
        return {"found": False, "reason": "elements 为空"}

    first_field_value = list(elements.values())[0]
    if not first_field_value:
        return {"found": False, "reason": "字段值为空"}

    # 找到字段值所在位置
    location = find_content_location(doc_path, str(first_field_value))
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

                # 查找摘要的结束行（同一列中连续有内容的行）
                row_end = row_idx
                for r in range(row_idx + 1, len(table.rows)):
                    # 检查该行是否有足够的列（处理合并单元格）
                    if col_idx >= len(table.rows[r].cells):
                        break
                    next_cell = table.rows[r].cells[col_idx]
                    next_text = next_cell.text.strip()
                    # 如果下一行同列有内容且不是表头类短文本，认为是摘要的延续
                    if next_text and len(next_text) > 20:
                        row_end = r
                    elif not next_text:
                        # 空行，继续检查
                        continue
                    else:
                        # 短文本，可能是其他区域，停止
                        break

                # 收集所有摘要内容的预览
                all_text = []
                for r in range(row_idx, row_end + 1):
                    # 检查该行是否有足够的列
                    if col_idx >= len(table.rows[r].cells):
                        continue
                    cell_text = table.rows[r].cells[col_idx].text.strip()
                    if cell_text:
                        all_text.append(cell_text[:50])

                return {
                    "found": True,
                    "table": table_idx,
                    "row_start": row_idx,
                    "row_end": row_end,
                    "row": row_idx,  # 保持向后兼容
                    "col_start": col_idx,
                    "col_end": col_end,
                    "preview": " | ".join(all_text)[:200],
                    "context": f"在表格 {table_idx} 第 {row_idx}-{row_end} 行，列 {col_idx}-{col_end}"
                }

    return {"found": False, "reason": "表格中未找到长文本"}


def find_body_range_by_sections(doc_path: str) -> Dict[str, Any]:
    """根据分节结构定位正文范围。

    策略：
    - 分节 0: 封面/标题
    - 分节 1: 首页（包含摘要）
    - 分节 2: 正文内容
    - 分节 3: 附录

    Args:
        doc_path: Word 文档路径

    Returns:
        正文范围信息
    """
    doc = Document(doc_path)
    section_paragraphs = _get_section_paragraphs(doc)

    if len(section_paragraphs) < 3:
        return {
            "found": False,
            "reason": f"分节数量不足（{len(section_paragraphs)} 个），需要至少 3 个分节"
        }

    # 正文从第三分节（索引 2）开始
    if 2 not in section_paragraphs or not section_paragraphs[2]:
        return {"found": False, "reason": "未找到分节 2"}

    start_idx = section_paragraphs[2][0]

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


def find_body_elements(doc_path: str) -> Dict[str, Any]:
    """根据分节结构定位正文范围内的所有元素（段落和表格）。

    正文不只是文字，还包括目录、所有的图表和表格。
    附录不属于正文，保留不替换。

    策略：
    - 分节 0: 封面/标题（保留）
    - 分节 1: 目录 + 首页摘要区域（目录属于正文，摘要单独处理）
    - 分节 2: 正文内容（包括段落、表格、图表）
    - 分节 3: 附录（保留）

    正文范围定义：
    - 起始：跳过首页表格，从目录（SDT）或第一个非首页表格的元素开始
    - 结束：到分节2的最后一个段落（分节边界）结束
    - 分节边界之后的所有元素（表格、段落等）属于附录，保留不替换

    Args:
        doc_path: Word 文档路径

    Returns:
        {
            "found": bool,
            "start_element_idx": int,  # body 中的起始元素索引
            "end_element_idx": int,    # body 中的结束元素索引（不包含）
            "elements_count": int,      # 正文元素数量
            "context": str,
        }
    """
    from docx.oxml.ns import qn

    doc = Document(doc_path)
    body = doc._body._body

    # 获取所有块级元素（段落和表格）
    all_elements = _get_body_elements(body)

    # 获取分节边界
    section_boundaries = _detect_section_boundaries(doc)

    if len(section_boundaries) < 2:
        return {
            "found": False,
            "reason": f"分节数量不足（{len(section_boundaries)} 个边界），需要至少 2 个分节边界"
        }

    # 正文起始：跳过首页表格，从目录（SDT）或第一个非表格元素开始
    # 首页表格通常是元素0，目录通常是元素1或2（可能是SDT）
    start_element_idx = None
    for i, elem in enumerate(all_elements):
        # 跳过首页表格（通常是第一个表格）
        if i == 0 and elem.tag == qn('w:tbl'):
            continue
        # 跳过首页表格后的空段落
        if elem.tag == qn('w:p'):
            texts = []
            for t in elem.iter(qn('w:t')):
                if t.text:
                    texts.append(t.text)
            text = ''.join(texts).strip()
            if not text:
                continue
        # 找到第一个有内容的元素（目录SDT或有内容的段落）
        start_element_idx = i
        break

    if start_element_idx is None:
        # 如果没找到，默认从元素1开始（跳过首页表格）
        start_element_idx = 1 if len(all_elements) > 1 else 0

    # 正文结束位置：分节2的最后一个段落（含分节边界标记）
    # 分节边界列表中第三个边界（索引2）就是正文的结束段落
    if len(section_boundaries) >= 3:
        body_end_para_idx = section_boundaries[2]  # 分节边界所在的段落（包含在正文中）
    else:
        # 没有分节3（附录），正文到文档结尾
        body_end_para_idx = len(doc.paragraphs) - 1

    # 将段落索引转换为 body 元素索引
    end_element_idx = _find_element_index_by_paragraph(doc, all_elements, body_end_para_idx)
    if end_element_idx is not None:
        end_element_idx += 1  # 不包含结束索引，所以 +1

    if end_element_idx is None:
        # 如果结束索引找不到，使用所有元素的末尾
        end_element_idx = len(all_elements)

    return {
        "found": True,
        "start_element_idx": start_element_idx,
        "end_element_idx": end_element_idx,
        "elements_count": end_element_idx - start_element_idx,
        "context": f"body 元素 {start_element_idx} 到 {end_element_idx}，共 {end_element_idx - start_element_idx} 个元素（含目录）"
    }


def _get_body_elements(body) -> List[Any]:
    """获取 body 中所有块级元素（段落和表格）。

    Args:
        body: document body 的 lxml 元素

    Returns:
        元素列表
    """
    from docx.oxml.ns import qn

    elements = []
    for child in body:
        tag = child.tag
        # 段落: w:p
        if tag == qn('w:p'):
            elements.append(child)
        # 表格: w:tbl
        elif tag == qn('w:tbl'):
            elements.append(child)
        # sdt (structured document tag) 也可能包含内容
        elif tag == qn('w:sdt'):
            elements.append(child)
    return elements


def _find_element_index_by_paragraph(doc: Document, elements: List[Any], para_idx: int) -> Optional[int]:
    """根据段落索引找到对应的 body 元素索引。

    Args:
        doc: Document 对象
        elements: body 元素列表
        para_idx: 段落索引

    Returns:
        元素索引，未找到返回 None
    """
    from docx.oxml.ns import qn

    if para_idx >= len(doc.paragraphs):
        return None

    # 获取目标段落的 XML 元素
    target_para_element = doc.paragraphs[para_idx]._element

    # 在 elements 中查找
    for i, elem in enumerate(elements):
        if elem is target_para_element:
            return i
        # 如果元素是段落，检查是否匹配
        if elem.tag == qn('w:p') and elem is target_para_element:
            return i

    return None


def find_elements_yaml(word_path: Union[Path, str]) -> Optional[Path]:
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
