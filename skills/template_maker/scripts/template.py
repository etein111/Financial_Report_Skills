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

def replace_field_value_in_doc(doc: Document, field_name: str, field_value: str) -> Document:
    """在文档中替换单个字段值为占位符（返回新文档）。

    Args:
        doc: Document 对象
        field_name: 字段名（如 "company"）
        field_value: 字段值（如 "西锐飞机"）

    Returns:
        修改后的 Document 对象
    """
    placeholder = common.format_placeholder(field_name)
    value_str = str(field_value)

    # 在段落中替换
    for para in doc.paragraphs:
        if value_str in para.text:
            _replace_text_in_para(para, value_str, placeholder)

    # 在表格中替换（包括嵌套表格）
    for table in doc.tables:
        _replace_in_table(table, value_str, placeholder)

    # 在页眉页脚中替换
    for section in doc.sections:
        for para in section.header.paragraphs:
            if value_str in para.text:
                _replace_text_in_para(para, value_str, placeholder)
        for para in section.footer.paragraphs:
            if value_str in para.text:
                _replace_text_in_para(para, value_str, placeholder)

    return doc


def _replace_in_table(table, old_text: str, new_text: str):
    """在表格中递归替换文本（包括嵌套表格）。

    Args:
        table: python-docx 表格对象
        old_text: 要替换的文本
        new_text: 新文本
    """
    for row in table.rows:
        for cell in row.cells:
            # 先处理嵌套表格
            for nested_table in cell.tables:
                _replace_in_table(nested_table, old_text, new_text)

            # 再处理单元格段落
            for para in cell.paragraphs:
                if old_text in para.text:
                    _replace_text_in_para(para, old_text, new_text)


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
    from docx.oxml.ns import qn

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

    # 保存第一个元素的引用，用于插入占位符
    first_element = all_elements[start_element_idx]

    # 删除正文范围内的所有元素（从后往前删除，避免索引混乱）
    for i in range(end_idx - 1, start_element_idx - 1, -1):
        elem = all_elements[i]
        parent = elem.getparent()
        if parent is not None:
            parent.remove(elem)

    # 在第一个元素原来的位置插入占位符段落
    # 创建新的段落元素
    from docx.oxml import OxmlElement

    new_para = OxmlElement('w:p')
    new_run = OxmlElement('w:r')
    new_text = OxmlElement('w:t')
    new_text.text = common.format_body_placeholder()
    new_run.append(new_text)
    new_para.append(new_run)

    # 找到正确的插入位置
    # 如果有剩余元素，插入到它们之前
    if end_idx < len(all_elements):
        next_element = all_elements[end_idx]
        body.insert(list(body).index(next_element), new_para)
    else:
        # 附加到末尾
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
