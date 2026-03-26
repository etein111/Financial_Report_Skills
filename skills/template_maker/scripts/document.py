"""文档分析函数。

用于分析 Word 文档结构、定位内容、获取段落和表格信息。
"""

from pathlib import Path
from typing import Dict, List, Any, Union, Optional
from docx import Document

from . import common


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
            # 摘要通常是长文本
            if len(text) > common.MIN_ABSTRACT_LENGTH:
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
                    if next_text and len(next_text) > common.MIN_CONTINUATION_LENGTH:
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
    """根据分节结构和关键字定位正文范围内的所有元素（段落和表格）。

    正文不只是文字，还包括目录、所有的图表和表格。
    附录不属于正文，保留不替换。

    策略：
    - 正文开始：第一个分节边界之后的第一个元素
    - 正文结束：遇到 "APPENDIX" 或 "附录" 关键字之前
    - 如果没有找到附录标记，使用最后一个分节边界作为结束

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

    if len(section_boundaries) < 1:
        return {
            "found": False,
            "reason": "未找到分节边界"
        }

    # 正文起始：第一个分节边界之后
    first_boundary_para_idx = section_boundaries[0]
    start_element_idx = _find_element_index_by_paragraph(doc, all_elements, first_boundary_para_idx)
    if start_element_idx is not None:
        start_element_idx += 1  # 分节边界之后的下一个元素
    else:
        start_element_idx = 1  # 默认从元素1开始（跳过首页表格）

    # 正文结束：查找 APPENDIX 或 附录 关键字
    end_element_idx = None
    appendix_keywords = ["APPENDIX", "附录"]

    for i, elem in enumerate(all_elements):
        if i <= start_element_idx:
            continue

        # 只检查段落元素
        if elem.tag == qn('w:p'):
            texts = []
            for t in elem.iter(qn('w:t')):
                if t.text:
                    texts.append(t.text)
            text = ''.join(texts).strip()

            # 检查是否是附录标题（以 APPENDIX 或 附录 开头）
            for keyword in appendix_keywords:
                if text.startswith(keyword):
                    end_element_idx = i
                    break

            if end_element_idx is not None:
                break

    # 如果没找到附录标记，使用最后一个分节边界
    if end_element_idx is None:
        if len(section_boundaries) >= 2:
            last_boundary_para_idx = section_boundaries[-1]
            end_element_idx = _find_element_index_by_paragraph(doc, all_elements, last_boundary_para_idx)
            if end_element_idx is not None:
                end_element_idx += 1  # 包含分节边界段落
        else:
            # 只有一个分节，正文到文档结尾（但保留最后10个元素作为可能的附录）
            end_element_idx = max(start_element_idx + 1, len(all_elements) - 10)

    if end_element_idx is None:
        end_element_idx = len(all_elements)

    return {
        "found": True,
        "start_element_idx": start_element_idx,
        "end_element_idx": end_element_idx,
        "elements_count": end_element_idx - start_element_idx,
        "context": f"body 元素 {start_element_idx} 到 {end_element_idx}，共 {end_element_idx - start_element_idx} 个元素"
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


def find_appendix_elements(doc_path: str) -> Dict[str, Any]:
    """定位 APPENDIX 区域（英文摘要）的元素范围。

    策略：
    - 起始：以 "APPENDIX" 开头的段落
    - 结束：下一个分节边界，或 "附录" 开头的段落，或文档末尾

    Args:
        doc_path: Word 文档路径

    Returns:
        {
            "found": bool,
            "start_element_idx": int,
            "end_element_idx": int,
            "elements_count": int,
            "context": str,
        }
    """
    from docx.oxml.ns import qn

    doc = Document(doc_path)
    body = doc._body._body

    all_elements = _get_body_elements(body)

    # 查找 APPENDIX 开始位置
    start_element_idx = None
    for i, elem in enumerate(all_elements):
        if elem.tag == qn('w:p'):
            texts = [t.text for t in elem.iter(qn('w:t')) if t.text]
            text = ''.join(texts).strip()
            if text.startswith("APPENDIX"):
                start_element_idx = i
                break

    if start_element_idx is None:
        return {"found": False, "reason": "未找到 APPENDIX 区域"}

    # 查找结束位置：下一个分节边界或 "附录" 开头
    end_element_idx = None
    section_boundaries = _detect_section_boundaries(doc)

    for i, elem in enumerate(all_elements):
        if i <= start_element_idx:
            continue

        if elem.tag == qn('w:p'):
            texts = [t.text for t in elem.iter(qn('w:t')) if t.text]
            text = ''.join(texts).strip()

            # 检查是否是附录（中文法律免责声明）
            if text.startswith("附录"):
                end_element_idx = i
                break

            # 检查是否是分节边界
            sectPr = elem.find('.//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}sectPr')
            if sectPr is not None:
                end_element_idx = i + 1  # 包含分节边界
                break

    if end_element_idx is None:
        # 没有找到结束标记，使用文档末尾（但保留最后的表格/段落作为可能的免责声明）
        for i in range(len(all_elements) - 1, start_element_idx, -1):
            elem = all_elements[i]
            if elem.tag == qn('w:tbl'):
                end_element_idx = i
                break
        if end_element_idx is None:
            end_element_idx = len(all_elements)

    return {
        "found": True,
        "start_element_idx": start_element_idx,
        "end_element_idx": end_element_idx,
        "elements_count": end_element_idx - start_element_idx,
        "context": f"APPENDIX 元素 {start_element_idx} 到 {end_element_idx}，共 {end_element_idx - start_element_idx} 个元素"
    }


def find_section_by_title(doc_path: str, start_title: str, end_titles: List[str]) -> Dict[str, Any]:
    """根据标题定位文档中的一个区域（不包含标题本身）。

    策略：
    - 起始：以 start_title 开头的段落的**下一个元素**（保留标题）
    - 结束：以 end_titles 中任意一个开头的段落之前

    Args:
        doc_path: Word 文档路径
        start_title: 起始标题（如 "核心观点"）
        end_titles: 结束标题列表（如 ["投资建议", "风险提示"]）

    Returns:
        {
            "found": bool,
            "start_element_idx": int,
            "end_element_idx": int,
            "elements_count": int,
            "context": str,
        }
    """
    from docx.oxml.ns import qn

    doc = Document(doc_path)
    body = doc._body._body

    all_elements = _get_body_elements(body)

    # 查找起始位置（标题的下一个元素）
    start_element_idx = None
    for i, elem in enumerate(all_elements):
        if elem.tag == qn('w:p'):
            texts = [t.text for t in elem.iter(qn('w:t')) if t.text]
            text = ''.join(texts).strip()
            if text.startswith(start_title):
                # 找到标题，起始位置是下一个元素
                start_element_idx = i + 1
                break

    if start_element_idx is None:
        return {"found": False, "reason": f"未找到以 '{start_title}' 开头的段落"}

    if start_element_idx >= len(all_elements):
        return {"found": False, "reason": f"'{start_title}' 标题后没有内容"}

    # 查找结束位置：同时考虑结束标题和分节边界，取更靠前的位置
    end_by_title = None
    end_by_section = None

    # 1. 查找结束标题
    for i, elem in enumerate(all_elements):
        if i <= start_element_idx:
            continue

        if elem.tag == qn('w:p'):
            texts = [t.text for t in elem.iter(qn('w:t')) if t.text]
            text = ''.join(texts).strip()

            for end_title in end_titles:
                if text.startswith(end_title):
                    end_by_title = i
                    break

            if end_by_title is not None:
                break

    # 2. 查找分节边界（在起始位置及之后的第一个）
    section_boundaries = _detect_section_boundaries(doc)
    for boundary_para_idx in section_boundaries:
        elem_idx = _find_element_index_by_paragraph(doc, all_elements, boundary_para_idx)
        if elem_idx is not None and elem_idx >= start_element_idx:
            # 分节边界段落本身属于当前区域，结束位置是它的下一个元素
            end_by_section = elem_idx + 1
            break

    # 3. 取两者中更靠前的位置（优先使用分节边界，因为它定义了页面结构）
    if end_by_title is not None and end_by_section is not None:
        end_element_idx = min(end_by_title, end_by_section)
    elif end_by_section is not None:
        end_element_idx = end_by_section
    elif end_by_title is not None:
        end_element_idx = end_by_title
    else:
        end_element_idx = None

    if end_element_idx is None:
        return {"found": False, "reason": f"未找到结束标题 {end_titles}"}

    return {
        "found": True,
        "start_element_idx": start_element_idx,
        "end_element_idx": end_element_idx,
        "elements_count": end_element_idx - start_element_idx,
        "context": f"区域 '{start_title}' 内容：元素 {start_element_idx} 到 {end_element_idx}"
    }
