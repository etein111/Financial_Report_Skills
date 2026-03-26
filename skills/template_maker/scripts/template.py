"""模板操作函数。

用于替换字段值、替换摘要/正文、调整位置、添加/删除字段等操作。
"""

from pathlib import Path
from typing import Dict, Any
from docx import Document

from . import common


# ==================== 文档操作 ====================

def load_document(doc_path: str) -> Document:
    """加载 Word 文档。

    Args:
        doc_path: 文档路径

    Returns:
        Document 对象
    """
    return Document(doc_path)


def save_document(doc: Document, output_path: str) -> None:
    """保存 Word 文档。

    Args:
        doc: Document 对象
        output_path: 输出路径
    """
    doc.save(output_path)


# ==================== 字段替换 ====================

# 长文本阈值：超过此长度的字段值使用前缀匹配
LONG_TEXT_THRESHOLD = 100
# 前缀匹配长度：用于匹配长文本的前缀字符数
PREFIX_MATCH_LENGTH = 50


def replace_field_value_in_doc(doc: Document, field_name: str, field_value: str) -> Document:
    """在文档中替换单个字段值为占位符（返回新文档）。

    对于长文本（超过 100 字符），使用前缀匹配策略：
    如果段落以字段值的前 50 个字符开头，则将整个段落替换为占位符。

    Args:
        doc: Document 对象
        field_name: 字段名（如 "company"）
        field_value: 字段值（如 "西锐飞机"）

    Returns:
        修改后的 Document 对象
    """
    placeholder = common.format_placeholder(field_name)
    value_str = str(field_value)

    # 判断是否为长文本
    is_long_text = len(value_str) > LONG_TEXT_THRESHOLD
    prefix = value_str[:PREFIX_MATCH_LENGTH] if is_long_text else None

    # 在段落中替换
    for para in doc.paragraphs:
        if is_long_text:
            # 长文本：前缀匹配，替换整个段落
            if para.text.strip().startswith(prefix):
                _replace_entire_para(para, placeholder)
        else:
            # 短文本：完整匹配
            if value_str in para.text:
                _replace_text_in_para(para, value_str, placeholder)

    # 在表格中替换（包括嵌套表格）
    for table in doc.tables:
        _replace_in_table(table, value_str, placeholder, is_long_text, prefix)

    # 在页眉页脚中替换
    for section in doc.sections:
        for para in section.header.paragraphs:
            if value_str in para.text:
                _replace_text_in_para(para, value_str, placeholder)
        for para in section.footer.paragraphs:
            if value_str in para.text:
                _replace_text_in_para(para, value_str, placeholder)

    return doc


def _replace_in_table(table, old_text: str, new_text: str,
                      is_long_text: bool = False, prefix: str = None):
    """在表格中递归替换文本（包括嵌套表格）。

    Args:
        table: python-docx 表格对象
        old_text: 要替换的文本
        new_text: 新文本
        is_long_text: 是否为长文本
        prefix: 长文本的前缀（用于前缀匹配）
    """
    for row in table.rows:
        for cell in row.cells:
            # 先处理嵌套表格
            for nested_table in cell.tables:
                _replace_in_table(nested_table, old_text, new_text, is_long_text, prefix)

            # 再处理单元格段落
            if is_long_text:
                # 长文本：查找以前缀开头的段落，替换该段落及其后续段落（直到遇到标题）
                _replace_long_text_in_cell(cell, prefix, new_text)
            else:
                for para in cell.paragraphs:
                    if old_text in para.text:
                        _replace_text_in_para(para, old_text, new_text)


def _replace_long_text_in_cell(cell, prefix: str, placeholder: str):
    """在单元格中替换长文本内容。

    查找以 prefix 开头的段落，将该段落替换为占位符，
    并删除后续的内容段落（直到遇到下一个标题或单元格结束）。

    Args:
        cell: python-docx 单元格对象
        prefix: 长文本的前缀
        placeholder: 占位符文本
    """
    paragraphs = cell.paragraphs
    start_idx = None

    # 查找以 prefix 开头的段落
    for i, para in enumerate(paragraphs):
        if para.text.strip().startswith(prefix):
            start_idx = i
            break

    if start_idx is None:
        return

    # 找到内容结束位置（下一个标题段落或单元格结束）
    # 标题通常是短文本（<50 字符）且独占一行
    end_idx = start_idx + 1
    for i in range(start_idx + 1, len(paragraphs)):
        text = paragraphs[i].text.strip()
        # 如果是空段落，继续
        if not text:
            end_idx = i + 1
            continue
        # 如果是短文本标题（如"投资建议"、"风险"等），停止
        if len(text) < 50 and not text.startswith(prefix[:20]):
            break
        end_idx = i + 1

    # 替换第一个段落为占位符
    _replace_entire_para(paragraphs[start_idx], placeholder)

    # 删除后续的内容段落（从后往前删除）
    for i in range(end_idx - 1, start_idx, -1):
        para = paragraphs[i]
        para._element.getparent().remove(para._element)


def replace_abstract_in_doc(doc: Document, table: int, row: int,
                           col_start: int, col_end: int,
                           row_end: int = None) -> Document:
    """在文档中替换摘要区域为 {{ abstract }} 占位符（返回新文档）。

    Args:
        doc: Document 对象
        table: 表格索引
        row: 行索引（起始行）
        col_start: 起始列索引
        col_end: 结束列索引
        row_end: 结束行索引（可选，默认与 row 相同）

    Returns:
        修改后的 Document 对象
    """
    if table >= len(doc.tables):
        raise ValueError(f"表格索引 {table} 超出范围")

    tbl = doc.tables[table]
    if row >= len(tbl.rows):
        raise ValueError(f"行索引 {row} 超出范围")

    # 如果没有指定结束行，则只处理起始行
    if row_end is None:
        row_end = row

    # 清空所有涉及的行的内容
    for row_idx in range(row, min(row_end + 1, len(tbl.rows))):
        tbl_row = tbl.rows[row_idx]
        for col_idx in range(col_start, min(col_end + 1, len(tbl_row.cells))):
            cell = tbl_row.cells[col_idx]
            # 清空所有段落
            for paragraph in cell.paragraphs:
                for run in paragraph.runs:
                    run.text = ""

    # 只在第一行第一列添加摘要占位符
    first_cell = tbl.rows[row].cells[col_start]
    if first_cell.paragraphs and first_cell.paragraphs[0].runs:
        first_cell.paragraphs[0].runs[0].text = common.format_abstract_placeholder()
    elif first_cell.paragraphs:
        first_cell.paragraphs[0].add_run(common.format_abstract_placeholder())
    else:
        first_cell.add_paragraph(common.format_abstract_placeholder())

    return doc


def replace_body_in_doc(doc: Document, start_paragraph: int,
                       end_paragraph: int) -> Document:
    """在文档中替换正文区域为 {{ body }} 占位符（返回新文档）。

    注意：此函数只处理段落，不处理表格。
    如需处理包含表格的正文，请使用 replace_body_elements_in_doc。

    Args:
        doc: Document 对象
        start_paragraph: 起始段落索引
        end_paragraph: 结束段落索引（不包含）

    Returns:
        修改后的 Document 对象
    """
    if start_paragraph >= len(doc.paragraphs):
        raise ValueError(f"起始段落 {start_paragraph} 超出范围")

    end_idx = min(end_paragraph, len(doc.paragraphs))

    # 清空正文区域的第一个段落，用于放置 {{ body }}
    para = doc.paragraphs[start_paragraph]
    for run in para.runs:
        run.text = ""
    if para.runs:
        para.runs[0].text = common.format_body_placeholder()
    else:
        para.add_run(common.format_body_placeholder())

    # 删除正文区域的其他段落（从后往前删除）
    for i in range(end_idx - 1, start_paragraph, -1):
        if i < len(doc.paragraphs):
            para = doc.paragraphs[i]
            para._element.getparent().remove(para._element)

    return doc


def replace_body_elements_in_doc(doc: Document,
                                 start_element_idx: int,
                                 end_element_idx: int) -> Document:
    """在文档中替换正文区域为 {{ body }} 占位符（包括所有元素）。

    正文包括段落、表格、图表等所有块级元素。
    附录部分保留不变。

    Args:
        doc: Document 对象
        start_element_idx: body 中起始元素索引
        end_element_idx: body 中结束元素索引（不包含）

    Returns:
        修改后的 Document 对象
    """
    return _replace_elements_region(doc, start_element_idx, end_element_idx,
                                    common.format_body_placeholder())


def replace_appendix_in_doc(doc: Document,
                            start_element_idx: int,
                            end_element_idx: int) -> Document:
    """在文档中替换 APPENDIX 区域为 {{ appendix }} 占位符。

    Args:
        doc: Document 对象
        start_element_idx: APPENDIX 起始元素索引
        end_element_idx: APPENDIX 结束元素索引（不包含）

    Returns:
        修改后的 Document 对象
    """
    return _replace_elements_region(doc, start_element_idx, end_element_idx,
                                    common.format_placeholder("appendix"))


def _replace_elements_region(doc: Document,
                             start_element_idx: int,
                             end_element_idx: int,
                             placeholder: str) -> Document:
    """通用的元素区域替换函数。

    删除指定范围的元素，并在原位置插入占位符。
    保留原始段落的格式（字体、大小等）。
    保留区域末尾的分页符和分节符。

    Args:
        doc: Document 对象
        start_element_idx: 起始元素索引
        end_element_idx: 结束元素索引（不包含）
        placeholder: 要插入的占位符文本

    Returns:
        修改后的 Document 对象
    """
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement
    from copy import deepcopy

    body = doc._body._body

    # 获取所有块级元素
    all_elements = []
    for child in body:
        tag = child.tag
        if tag in (qn('w:p'), qn('w:tbl'), qn('w:sdt')):
            all_elements.append(child)

    if start_element_idx >= len(all_elements):
        raise ValueError(f"起始元素索引 {start_element_idx} 超出范围 {len(all_elements)}")

    end_idx = min(end_element_idx, len(all_elements))

    # 保存第一个段落的格式属性（在删除之前）
    first_elem = all_elements[start_element_idx]
    saved_pPr = None
    saved_rPr = None
    if first_elem.tag == qn('w:p'):
        # 保存段落属性
        pPr = first_elem.find(qn('w:pPr'))
        if pPr is not None:
            saved_pPr = deepcopy(pPr)
        # 保存第一个 run 的属性
        first_run = first_elem.find(qn('w:r'))
        if first_run is not None:
            rPr = first_run.find(qn('w:rPr'))
            if rPr is not None:
                saved_rPr = deepcopy(rPr)

    # 检查并保存区域末尾的分页符/分节符段落
    trailing_break_elements = []
    for i in range(end_idx - 1, start_element_idx - 1, -1):
        elem = all_elements[i]
        if elem.tag == qn('w:p'):
            # 检查是否是分节符段落
            pPr = elem.find(qn('w:pPr'))
            has_sectPr = pPr is not None and pPr.find(qn('w:sectPr')) is not None

            # 检查是否是分页符段落
            has_page_break = any(
                br.get(qn('w:type')) == 'page'
                for br in elem.iter(qn('w:br'))
            )

            # 检查是否是空段落（只有分页符或分节符）
            texts = [t.text for t in elem.iter(qn('w:t')) if t.text]
            is_empty = not ''.join(texts).strip()

            if is_empty and (has_sectPr or has_page_break):
                trailing_break_elements.insert(0, deepcopy(elem))
                end_idx = i  # 不删除这个分页符元素
            else:
                break
        else:
            break

    # 删除范围内的所有元素（从后往前删除，避免索引混乱）
    for i in range(end_idx - 1, start_element_idx - 1, -1):
        elem = all_elements[i]
        parent = elem.getparent()
        if parent is not None:
            parent.remove(elem)

    # 创建新的占位符段落（保留原始格式）
    new_para = OxmlElement('w:p')
    if saved_pPr is not None:
        # 移除分节符（如果有），只保留格式
        new_pPr = deepcopy(saved_pPr)
        sectPr = new_pPr.find(qn('w:sectPr'))
        if sectPr is not None:
            new_pPr.remove(sectPr)
        new_para.append(new_pPr)

    new_run = OxmlElement('w:r')
    if saved_rPr is not None:
        new_run.append(saved_rPr)

    new_text = OxmlElement('w:t')
    new_text.text = placeholder
    new_run.append(new_text)
    new_para.append(new_run)

    # 在正确的位置插入占位符
    if end_idx < len(all_elements):
        next_element = all_elements[end_idx]
        insert_pos = list(body).index(next_element)
        body.insert(insert_pos, new_para)
    else:
        body.append(new_para)

    return doc


# ==================== 位置调整 ====================

def adjust_abstract_position_in_doc(doc: Document, table: int, row: int,
                                   col_start: int, col_end: int,
                                   row_end: int = None) -> Document:
    """调整摘要位置（返回新文档）。

    Args:
        doc: Document 对象
        table: 表格索引
        row: 行索引（起始行）
        col_start: 起始列索引
        col_end: 结束列索引
        row_end: 结束行索引（可选）

    Returns:
        修改后的 Document 对象
    """
    return replace_abstract_in_doc(doc, table, row, col_start, col_end, row_end)


def adjust_body_range_in_doc(doc: Document, start_paragraph: int,
                            end_paragraph: int) -> Document:
    """调整正文范围（返回新文档）。

    Args:
        doc: Document 对象
        start_paragraph: 起始段落索引
        end_paragraph: 结束段落索引（不包含）

    Returns:
        修改后的 Document 对象
    """
    return replace_body_in_doc(doc, start_paragraph, end_paragraph)


# ==================== 字段管理 ====================

def add_field_to_doc(doc: Document, field_name: str, field_value: str,
                    position_hint: str) -> Document:
    """在文档中添加新字段（返回新文档）。

    Args:
        doc: Document 对象
        field_name: 字段名（如 "analyst"）
        field_value: 字段值（如 "张三"）
        position_hint: 位置提示
            - "after:company" (在 company 字段之后)
            - "table:0,row:3,col:2" (在表格 0 第 3 行第 2 列)
            - "paragraph:5" (在段落 5 之后)

    Returns:
        修改后的 Document 对象

    Raises:
        NotImplementedError: 当位置提示类型未实现时
    """
    placeholder = common.format_placeholder(field_name)

    # 解析位置提示
    if position_hint.startswith("after:"):
        raise NotImplementedError(
            f"位置提示 'after:{position_hint[6:]}' 尚未实现。"
            "需要集成 document.py 的 find_content_location 函数。"
        )

    elif position_hint.startswith("table:"):
        raise NotImplementedError(
            f"位置提示 '{position_hint}' 尚未实现。"
        )

    elif position_hint.startswith("paragraph:"):
        # 在指定段落之后插入
        para_idx = int(position_hint.split(":")[1])

        # 在指定段落前插入新段落
        if para_idx < len(doc.paragraphs):
            new_para = doc.paragraphs[para_idx]._element.addprevious(
                doc.paragraphs[para_idx]._element.__class__()
            )
            # 设置文本
            from docx.oxml.text.paragraph import CT_P
            from docx.text.paragraph import Paragraph
            new_para_obj = Paragraph(new_para, doc)
            new_para_obj.text = placeholder
    else:
        raise ValueError(f"未知的位置提示格式: {position_hint}")

    return doc


def remove_field_from_doc(doc: Document, field_name: str) -> Document:
    """从文档中删除字段（返回新文档）。

    Args:
        doc: Document 对象
        field_name: 字段名

    Returns:
        修改后的 Document 对象
    """
    placeholder = common.format_placeholder(field_name)

    # 在段落中查找并删除
    for para in doc.paragraphs:
        if placeholder in para.text:
            # 删除包含占位符的段落
            para._element.getparent().remove(para._element)

    # 在表格中查找并删除
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for para in cell.paragraphs:
                    if placeholder in para.text:
                        # 清空内容
                        para.text = ""

    return doc


# ==================== 辅助函数 ====================

def _replace_text_in_para(paragraph, old_text: str, new_text: str):
    """替换单个段落中的文本。

    Args:
        paragraph: python-docx 段落对象
        old_text: 要替换的文本
        new_text: 新文本
    """
    if old_text not in paragraph.text:
        return

    # 先保存原始文本（在清空 runs 之前）
    original_text = paragraph.text
    replaced_text = original_text.replace(old_text, new_text)

    # 清除现有 runs
    for run in paragraph.runs:
        run.text = ""

    # 设置替换后的文本
    if paragraph.runs:
        paragraph.runs[0].text = replaced_text
    else:
        paragraph.add_run(replaced_text)


def _replace_entire_para(paragraph, new_text: str):
    """将整个段落替换为新文本。

    用于长文本的前缀匹配替换。

    Args:
        paragraph: python-docx 段落对象
        new_text: 新文本（占位符）
    """
    # 清除现有 runs
    for run in paragraph.runs:
        run.text = ""

    # 设置新文本
    if paragraph.runs:
        paragraph.runs[0].text = new_text
    else:
        paragraph.add_run(new_text)
