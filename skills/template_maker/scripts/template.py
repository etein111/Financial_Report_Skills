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

    支持两种匹配模式：
    1. 完整匹配：在单个段落/单元格中查找完整的字段值
    2. 首行匹配：对于长文本，如果完整匹配失败，尝试匹配文本的第一行/前100个字符

    Args:
        doc: Document 对象
        field_name: 字段名（如 "company"）
        field_value: 字段值（如 "西锐飞机"）

    Returns:
        修改后的 Document 对象
    """
    placeholder = "{{" + f" {field_name} " + "}}"
    value_str = str(field_value).strip()

    # 对于长文本，准备首行匹配模式
    # 取第一行或前 100 个字符作为匹配目标
    first_line = value_str.split('\n')[0].strip()[:100] if '\n' in value_str else value_str[:100]
    use_partial_match = len(value_str) > 100

    matched = False

    # 在段落中替换
    for para in doc.paragraphs:
        para_text = para.text
        if value_str in para_text:
            _replace_text_in_para(para, value_str, placeholder)
            matched = True
        elif use_partial_match and first_line in para_text and len(first_line) >= 50:
            # 长文本首行匹配：如果找到首行，替换整个段落内容为占位符
            _replace_text_in_para(para, para_text, placeholder)
            matched = True

    # 在表格中替换（包括嵌套表格），跟踪已处理的单元格避免重复
    processed_cells = set()
    for table in doc.tables:
        if _replace_in_table(table, value_str, placeholder, processed_cells, first_line if use_partial_match else None):
            matched = True

    # 在页眉页脚中替换
    for section in doc.sections:
        for para in section.header.paragraphs:
            if value_str in para.text:
                _replace_text_in_para(para, value_str, placeholder)
                matched = True
        for para in section.footer.paragraphs:
            if value_str in para.text:
                _replace_text_in_para(para, value_str, placeholder)
                matched = True

    return doc


def _replace_in_table(table, value_str: str, placeholder: str, processed_cells: set, first_line: str = None) -> bool:
    """递归替换表格中的文本（包括嵌套表格）。

    Returns:
        是否找到并替换了匹配项
    """
    matched = False
    for row in table.rows:
        for cell in row.cells:
            # 使用单元格的 XML 元素本身作为 key（而不是 id()，因为 id 可能被重用）
            cell_tc = cell._tc
            if cell_tc in processed_cells:
                continue
            processed_cells.add(cell_tc)

            # 替换单元格中的段落
            for para in cell.paragraphs:
                para_text = para.text
                if value_str in para_text:
                    _replace_text_in_para(para, value_str, placeholder)
                    matched = True
                elif first_line and first_line in para_text and len(first_line) >= 50:
                    # 长文本首行匹配
                    _replace_text_in_para(para, para_text, placeholder)
                    matched = True

            # 递归处理嵌套表格
            for nested_table in cell.tables:
                if _replace_in_table(nested_table, value_str, placeholder, set(), first_line):
                    matched = True

    return matched


def replace_analyst_fields_in_doc(doc: Document, elements: dict) -> Document:
    """替换分析师字段为占位符。

    处理逻辑：
    1. 对于有值的分析师，找到组合字符串并替换为组合占位符
    2. 定位分析师表格（[Table_Author]），为所有位置创建占位符

    Args:
        doc: Document 对象
        elements: 包含分析师字段的字典

    Returns:
        修改后的 Document 对象
    """
    # 收集分析师数据
    analysts = {}
    for i in range(1, 9):
        cn = elements.get(f'a{i}_cn', '')
        en = elements.get(f'a{i}_en', '')
        sfc = elements.get(f'a{i}_sfc', '')
        email = elements.get(f'a{i}_email', '')
        analysts[i] = {'cn': cn, 'en': en, 'sfc': sfc, 'email': email}

    # 找到所有分析师表格（[Table_Author]）
    author_tables = []
    for table in doc.tables:
        _find_author_tables(table, author_tables)

    # 替换有值的分析师信息
    for i, data in analysts.items():
        if data['cn'] and data['en'] and data['sfc']:
            # 构造可能的组合格式（文档中的格式可能有变化）
            info_patterns = [
                f"{data['cn']}·{data['en']}，SFC:{data['sfc']}",
                f"{data['cn']} {data['en']}], SFC:{data['sfc']}",  # 逗号后有空格
                f"{data['cn']} {data['en']}],SFC:{data['sfc']}",   # 逗号后无空格
                f"{data['cn']}·{data['en']}, SFC:{data['sfc']}",
                f"{data['cn']} {data['en']}, SFC:{data['sfc']}",
            ]
            info_placeholder = f"{{{{ a{i}_cn }}}} {{{{ a{i}_en }}}}], SFC:{{{{ a{i}_sfc }}}}"

            # 在文档中查找并替换
            for pattern in info_patterns:
                _replace_text_in_nested_tables(doc, pattern, info_placeholder)

        if data['email']:
            email_placeholder = f"{{{{ a{i}_email }}}}"
            _replace_text_in_nested_tables(doc, data['email'], email_placeholder)

    # 为分析师表格中的所有 8 个位置创建占位符
    # 分析师表格布局（5行 x 4列）：
    # 行0: [Table_Author] 标记
    # 行1 列0-3: 分析师 1-4 的姓名+SFC
    # 行2 列0-3: 分析师 1-4 的邮箱
    # 行3 列0-3: 分析师 5-8 的姓名+SFC
    # 行4 列0-3: 分析师 5-8 的邮箱

    if author_tables:
        # 只处理第一个表格（其他都是合并单元格的视图）
        author_table = author_tables[0]

        # 分析师位置映射：(行, 列) -> 分析师编号
        analyst_positions = [
            # 分析师 1-4：行1(姓名)、行2(邮箱)
            (1, 0, 1), (1, 1, 2), (1, 2, 3), (1, 3, 4),  # 行1列0-3 -> a1-a4
            # 分析师 5-8：行3(姓名)、行4(邮箱)
            (3, 0, 5), (3, 1, 6), (3, 2, 7), (3, 3, 8),  # 行3列0-3 -> a5-a8
        ]

        for info_row, col, analyst_idx in analyst_positions:
            email_row = info_row + 1

            # 检查行和列是否在范围内
            if info_row >= len(author_table.rows) or col >= len(author_table.columns):
                continue

            info_cell = author_table.rows[info_row].cells[col]
            email_cell = author_table.rows[email_row].cells[col] if email_row < len(author_table.rows) else None

            # 姓名+SFC 占位符
            cell_text = info_cell.text.strip()
            if '{{' not in cell_text:
                # 不管原来有没有值，都替换为占位符
                info_placeholder = f"{{{{ a{analyst_idx}_cn }}}} {{{{ a{analyst_idx}_en }}}}], SFC:{{{{ a{analyst_idx}_sfc }}}}"
                _set_cell_text(info_cell, info_placeholder)

            # 邮箱占位符
            if email_cell:
                cell_text = email_cell.text.strip()
                if '{{' not in cell_text:
                    email_placeholder = f"{{{{ a{analyst_idx}_email }}}}"
                    _set_cell_text(email_cell, email_placeholder)

    return doc


def _find_author_tables(table, result_list):
    """递归查找所有 [Table_Author] 表格。

    查找规则：如果表格的第一行第一个单元格包含 [Table_Author]，则该表格是分析师表格。
    """
    # 检查当前表格是否是分析师表格
    if table.rows and table.rows[0].cells:
        first_cell_text = table.rows[0].cells[0].text.strip()
        if '[Table_Author]' in first_cell_text:
            result_list.append(table)
            return  # 找到后不再递归搜索子表格

    # 递归搜索嵌套表格
    for row in table.rows:
        for cell in row.cells:
            for nested in cell.tables:
                _find_author_tables(nested, result_list)


def _replace_text_in_nested_tables(doc: Document, old_text: str, new_text: str):
    """在文档的所有表格（包括嵌套表格）中替换文本。"""
    for table in doc.tables:
        _replace_in_all_cells(table, old_text, new_text)


def _replace_in_all_cells(table, old_text: str, new_text: str):
    """递归替换表格中所有单元格的文本。"""
    for row in table.rows:
        for cell in row.cells:
            # 替换单元格中的段落
            for para in cell.paragraphs:
                if old_text in para.text:
                    _replace_text_in_para(para, old_text, new_text)

            # 递归处理嵌套表格
            for nested_table in cell.tables:
                _replace_in_all_cells(nested_table, old_text, new_text)


def _set_cell_text(cell, text: str):
    """设置单元格文本（清空现有内容后设置）。"""
    # 清空所有段落
    for para in cell.paragraphs:
        for run in para.runs:
            run.text = ""
    # 设置新文本
    if cell.paragraphs and cell.paragraphs[0].runs:
        cell.paragraphs[0].runs[0].text = text
    elif cell.paragraphs:
        cell.paragraphs[0].add_run(text)
    else:
        cell.add_paragraph(text)


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

    删除正文区域内的所有元素（段落、表格、目录等），只保留一个占位符。
    目录（SDT）也会被删除，因为目录内容会根据正文自动生成。
    保留正文结束处的分节符。

    Args:
        doc: Document 对象
        start_paragraph: 起始段落索引
        end_paragraph: 结束段落索引（不包含）

    Returns:
        修改后的 Document 对象
    """
    from lxml import etree
    from copy import deepcopy

    if start_paragraph >= len(doc.paragraphs):
        raise ValueError(f"起始段落 {start_paragraph} 超出范围")

    # 获取 body 元素
    body = doc._body._body

    # 找到起始段落和结束段落对应的 XML 元素
    start_para_element = doc.paragraphs[start_paragraph]._element
    end_idx = min(end_paragraph, len(doc.paragraphs))
    end_para_element = doc.paragraphs[end_idx - 1]._element if end_idx > start_paragraph else start_para_element

    # 先删除所有 SDT（目录）元素
    sdt_elements = [child for child in body if etree.QName(child.tag).localname == 'sdt']
    for sdt in sdt_elements:
        body.remove(sdt)

    # 收集要删除的元素（正文区域内的所有段落和表格）
    elements_to_remove = []
    in_body_range = False
    first_body_element = None
    last_sect_pr = None  # 保存最后一个分节符

    for child in list(body):
        tag = etree.QName(child.tag).localname

        # 检查是否进入正文区域
        if child == start_para_element:
            in_body_range = True
            first_body_element = child

        # 如果在正文区域内，收集要删除的元素
        if in_body_range:
            if tag in ('p', 'tbl'):
                elements_to_remove.append(child)
                # 检查段落是否有分节符
                if tag == 'p':
                    sect_pr = child.find('.//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}sectPr')
                    if sect_pr is not None:
                        last_sect_pr = deepcopy(sect_pr)

        # 检查是否离开正文区域
        if child == end_para_element:
            in_body_range = False
            break

    # 删除收集的元素（从后往前删除，保留第一个段落用于放置占位符）
    for element in reversed(elements_to_remove[1:]):
        body.remove(element)

    # 在第一个元素位置设置占位符
    if first_body_element is not None and elements_to_remove:
        # 使用 python-docx 的 Paragraph 包装器操作第一个段落
        from docx.text.paragraph import Paragraph
        para = Paragraph(first_body_element, doc._body)

        # 清空所有 runs
        for run in para.runs:
            run.text = ""

        # 设置占位符
        if para.runs:
            para.runs[0].text = "{{ body }}"
        else:
            para.add_run("{{ body }}")

        # 如果有分节符，添加到 body 占位符段落
        if last_sect_pr is not None:
            # 获取段落的 pPr（段落属性）元素，如果没有则创建
            pPr = first_body_element.find('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}pPr')
            if pPr is None:
                pPr = etree.SubElement(
                    first_body_element,
                    '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}pPr'
                )
                # pPr 应该在段落的最前面
                first_body_element.insert(0, pPr)
            # 添加分节符到 pPr
            pPr.append(last_sect_pr)

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

    # 先保存原始文本
    original_text = paragraph.text

    # 清除现有 runs
    for run in paragraph.runs:
        run.text = ""

    # 使用保存的原始文本进行替换
    new_content = original_text.replace(old_text, new_text)

    # 添加新 run
    if paragraph.runs:
        paragraph.runs[0].text = new_content
    else:
        paragraph.add_run(new_content)
