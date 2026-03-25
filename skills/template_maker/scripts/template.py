"""模板操作函数。

用于替换字段值、替换摘要/正文、调整位置、添加/删除字段等操作。
"""

from pathlib import Path
from typing import Dict, Any
from docx import Document


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
    placeholder = "{{" + f" {field_name} " + "}}"
    value_str = str(field_value)

    # 在段落中替换
    for para in doc.paragraphs:
        if value_str in para.text:
            _replace_text_in_para(para, value_str, placeholder)

    # 在表格中替换（包括嵌套表格）
    for table in doc.tables:
        _replace_in_table_recursive(table, value_str, placeholder)

    # 在页眉页脚中替换
    for section in doc.sections:
        for para in section.header.paragraphs:
            if value_str in para.text:
                _replace_text_in_para(para, value_str, placeholder)
        for para in section.footer.paragraphs:
            if value_str in para.text:
                _replace_text_in_para(para, value_str, placeholder)

    return doc


def _replace_in_table_recursive(table, old_text: str, new_text: str):
    """递归地在表格中替换文本（包括所有嵌套层级的表格）。

    Args:
        table: python-docx 表格对象
        old_text: 要替换的文本
        new_text: 新文本
    """
    for row in table.rows:
        for cell in row.cells:
            # 1. 替换单元格段落中的文本
            replaced = False
            for para in cell.paragraphs:
                if old_text in para.text:
                    _replace_text_in_para(para, old_text, new_text)
                    replaced = True

            # 2. 如果段落级别没找到，检查嵌套表格
            if not replaced and len(cell.tables) > 0:
                for nested_table in cell.tables:
                    for nested_row in nested_table.rows:
                        for nested_cell in nested_row.cells:
                            for para in nested_cell.paragraphs:
                                if old_text in para.text:
                                    _replace_text_in_para(para, old_text, new_text)
                                    replaced = True

            # 3. 递归处理所有嵌套表格（无论是否已找到）
            for nested_table in cell.tables:
                _replace_in_table_recursive(nested_table, old_text, new_text)


def _replace_in_cell_runs(cell, old_text: str, new_text: str):
    """在单元格的所有 runs 中递归搜索并替换文本。

    有些表格单元格的文本可能被分散在多个嵌套结构中，
    这个函数会深度搜索所有可能的文本位置。

    Args:
        cell: python-docx 单元格对象
        old_text: 要替换的文本
        new_text: 新文本
    """
    # 方法1: 检查是否有嵌套表格
    if len(cell.tables) > 0:
        # 在嵌套表格中查找并替换
        for nested_table in cell.tables:
            for row in nested_table.rows:
                for nested_cell in row.cells:
                    for para in nested_cell.paragraphs:
                        if old_text in para.text:
                            _replace_text_in_para(para, old_text, new_text)
                            return  # 找到并替换后返回

    # 方法2: 尝试直接搜索单元格的 XML 内容
    cell_xml = cell._element.xml
    if old_text in cell_xml:
        # 在 XML 中找到了，尝试在段落级别替换
        for para in cell.paragraphs:
            _deep_replace_in_paragraph(para, old_text, new_text)


def _deep_replace_in_paragraph(para, old_text: str, new_text: str):
    """深度搜索段落中的所有文本节点并替换。

    Args:
        para: python-docx 段落对象
        old_text: 要替换的文本
        new_text: 新文本
    """
    # 方法1: 先尝试使用段落文本
    full_text = para.text
    if old_text in full_text:
        import re
        pattern = re.escape(old_text)

        # 清除现有 runs 并重新创建
        for run in para.runs:
            run.text = ""

        # 添加替换后的文本到第一个 run
        if para.runs:
            para.runs[0].text = re.sub(pattern, new_text, full_text)
        else:
            para.add_run(re.sub(pattern, new_text, full_text))
        return

    # 方法2: 如果段落文本为空，直接操作 XML
    para_xml = para._element.xml
    if old_text in para_xml:
        _replace_text_in_xml(para._element, old_text, new_text)


def _replace_text_in_xml(element, old_text: str, new_text: str):
    """直接在 XML 元素中替换文本。

    Args:
        element: lxml 元素对象
        old_text: 要替换的文本
        new_text: 新文本
    """
    # 查找所有 w:t 文本节点
    ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
    text_nodes = element.findall('.//w:t', ns)

    for text_node in text_nodes:
        if text_node.text and old_text in text_node.text:
            text_node.text = text_node.text.replace(old_text, new_text)


def replace_abstract_in_doc(doc: Document, table: int, row: int,
                           col_start: int, col_end: int) -> Document:
    """在文档中替换摘要区域为 {{ abstract }} 占位符（返回新文档）。

    Args:
        doc: Document 对象
        table: 表格索引
        row: 行索引
        col_start: 起始列索引
        col_end: 结束列索引

    Returns:
        修改后的 Document 对象
    """
    if table >= len(doc.tables):
        raise ValueError(f"表格索引 {table} 超出范围")

    tbl = doc.tables[table]
    if row >= len(tbl.rows):
        raise ValueError(f"行索引 {row} 超出范围")

    tbl_row = tbl.rows[row]

    # 替换指定范围的单元格
    for col_idx in range(col_start, min(col_end + 1, len(tbl_row.cells))):
        cell = tbl_row.cells[col_idx]
        # 清空所有段落
        for paragraph in cell.paragraphs:
            for run in paragraph.runs:
                run.text = ""
        # 添加摘要占位符
        if cell.paragraphs:
            cell.paragraphs[0].runs[0].text = "{{ abstract }}"
        else:
            cell.add_paragraph("{{ abstract }}")

    return doc


def replace_body_in_doc(doc: Document, start_paragraph: int,
                       end_paragraph: int) -> Document:
    """在文档中替换正文区域为 {{ body }} 占位符（返回新文档）。

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
        para.runs[0].text = "{{ body }}"
    else:
        para.add_run("{{ body }}")

    # 删除正文区域的其他段落（从后往前删除）
    for i in range(end_idx - 1, start_paragraph, -1):
        if i < len(doc.paragraphs):
            para = doc.paragraphs[i]
            para._element.getparent().remove(para._element)

    return doc


# ==================== 位置调整 ====================

def adjust_abstract_position_in_doc(doc: Document, table: int, row: int,
                                   col_start: int, col_end: int) -> Document:
    """调整摘要位置（返回新文档）。

    Args:
        doc: Document 对象
        table: 表格索引
        row: 行索引
        col_start: 起始列索引
        col_end: 结束列索引

    Returns:
        修改后的 Document 对象
    """
    return replace_abstract_in_doc(doc, table, row, col_start, col_end)


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
    """
    placeholder = "{{" + f" {field_name} " + "}}"

    # 解析位置提示
    if position_hint.startswith("after:"):
        # 在指定字段之后插入
        existing_field = position_hint[6:]
        # 这里需要调用 document.py 的 find_content_location
        # 暂时跳过实现
        pass

    elif position_hint.startswith("table:"):
        # 直接指定表格位置
        parts = position_hint.split(",")
        table_idx = int(parts[0].split(":")[1])

        table = doc.tables[table_idx]
        # 在指定位置插入占位符
        # ... (具体实现)
        pass

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

    return doc


def remove_field_from_doc(doc: Document, field_name: str) -> Document:
    """从文档中删除字段（返回新文档）。

    Args:
        doc: Document 对象
        field_name: 字段名

    Returns:
        修改后的 Document 对象
    """
    placeholder = "{{" + f" {field_name} " + "}}"

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

    # 先保存原始文本（在清除 runs 之前）
    original_text = paragraph.text

    # 清除现有 runs
    for run in paragraph.runs:
        run.text = ""

    # 添加新 run
    new_text_value = original_text.replace(old_text, new_text)
    if paragraph.runs:
        paragraph.runs[0].text = new_text_value
    else:
        paragraph.add_run(new_text_value)
