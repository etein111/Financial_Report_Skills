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

    将分析师表格规范化为 4x4 表格，格式如下：
    Row 1: {% if a1_cn %} {{ a1_cn }} {{ a1_en }}], SFC:{{ a1_sfc }} {% endif %} | ... | {% if a4_cn %} {{ a4_cn }} {{ a4_en }}], SFC:{{ a4_sfc }} {% endif %}
    Row 2: {{ a1_email }} | {{ a2_email }} | {{ a3_email }} | {{ a4_email }}
    Row 3: {% if a5_cn %} {{ a5_cn }} {{ a5_en }}], SFC:{{ a5_sfc }} {% endif %} | ... | {% if a8_cn %} {{ a8_cn }} {{ a8_en }}], SFC:{{ a8_sfc }} {% endif %}
    Row 4: {{ a5_email }} | {{ a6_email }} | {{ a7_email }} | {{ a8_email }}

    使用 lxml 直接解析 document.xml 以正确处理合并单元格。

    Args:
        doc: Document 对象
        elements: 包含分析师字段的字典

    Returns:
        修改后的 Document 对象
    """
    from lxml import etree

    W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'

    # 收集分析师数据
    analysts = {}
    for i in range(1, 9):
        cn = elements.get(f'a{i}_cn', '')
        en = elements.get(f'a{i}_en', '')
        sfc = elements.get(f'a{i}_sfc', '')
        email = elements.get(f'a{i}_email', '')
        analysts[i] = {'cn': cn, 'en': en, 'sfc': sfc, 'email': email}

    # 获取文档的 body 元素
    body = doc._body._body

    # 使用 lxml 找到所有 Table_Author 表格
    author_tbl_element = None
    for tbl in body.findall(f'.//{W}tbl'):
        # 检查第一个单元格是否包含 [Table_Author]
        first_tc = tbl.find(f'.//{W}tr/{W}tc')
        if first_tc is not None:
            tc_text = ''.join(t.text or '' for t in first_tc.iter(f'{W}t'))
            if '[Table_Author]' in tc_text:
                author_tbl_element = tbl
                break

    if author_tbl_element is None:
        # 如果没找到 Table_Author，尝试其他方法
        for tbl in body.findall(f'.//{W}tbl'):
            tbl_text = ''.join(t.text or '' for t in tbl.iter(f'{W}t'))
            if '[Table_Author]' in tbl_text:
                author_tbl_element = tbl
                break

    # 如果找到了分析师表格，将其规范化为 4x4 表格
    if author_tbl_element is not None:
        author_tbl = author_tbl_element

        # 获取表格的行和列
        trs = author_tbl.findall(W + 'tr')
        rows = len(trs)
        first_tr = trs[0] if trs else None
        first_tr_tcs = first_tr.findall(W + 'tc') if first_tr else []
        cols = len(first_tr_tcs)

        # 判断是否需要重建表格
        # 4x4 表格意味着：4 行数据行（不含标记行），4 列
        # 格式：Row1(信息) | Row2(邮箱) | Row3(信息) | Row4(邮箱)

        # 先找到 [Table_Author] 标记单元格并清空其内容
        marker_tc = None
        for tbl in body.findall(f'.//{W}tbl'):
            for row in tbl.findall(W + 'tr'):
                for tc in row.findall(W + 'tc'):
                    tc_text = ''.join(t.text or '' for t in tc.iter(f'{W}t'))
                    if '[Table_Author]' in tc_text:
                        marker_tc = tc
                        break
                if marker_tc:
                    break
            if marker_tc:
                break

        # 清空标记单元格内容
        if marker_tc is not None:
            # 保留段落属性，删除内容
            for child in list(marker_tc):
                if etree.QName(child.tag).localname != 'pPr':
                    marker_tc.remove(child)
            # 在第一个段落添加空文本
            first_p = marker_tc.find(W + 'p')
            if first_p is not None:
                for child in list(first_p):
                    if etree.QName(child.tag).localname != 'pPr':
                        first_p.remove(child)
                r = etree.SubElement(first_p, W + 'r')
                t = etree.SubElement(r, W + 't')
                t.text = ''

        # 构建 4x4 表格内容
        # Row 1: a1-a4 分析师信息
        row1_cells = []
        for i in [1, 2, 3, 4]:
            placeholder = (
                '{% if a' + str(i) + '_cn %} {{ a' + str(i) + '_cn }} {{ a' + str(i) + '_en }}], '
                'SFC:{{ a' + str(i) + '_sfc }} {% endif %}'
            )
            row1_cells.append(placeholder)

        # Row 2: a1-a4 邮箱
        row2_cells = ['{{ a1_email }}', '{{ a2_email }}', '{{ a3_email }}', '{{ a4_email }}']

        # Row 3: a5-a8 分析师信息
        row3_cells = []
        for i in [5, 6, 7, 8]:
            placeholder = (
                '{% if a' + str(i) + '_cn %} {{ a' + str(i) + '_cn }} {{ a' + str(i) + '_en }}], '
                'SFC:{{ a' + str(i) + '_sfc }} {% endif %}'
            )
            row3_cells.append(placeholder)

        # Row 4: a5-a8 邮箱
        row4_cells = ['{{ a5_email }}', '{{ a6_email }}', '{{ a7_email }}', '{{ a8_email }}']

        # 找到 marker_tc 所在的行，以它为基准重建表格
        # 我们需要在 author_tbl 中找到 marker_tc 所在的行位置
        marker_row_idx = None
        marker_col_idx = None
        for row_idx, row in enumerate(trs):
            for col_idx, tc in enumerate(row.findall(W + 'tc')):
                if tc is marker_tc:
                    marker_row_idx = row_idx
                    marker_col_idx = col_idx
                    break
            if marker_row_idx is not None:
                break

        if marker_row_idx is not None and marker_col_idx is not None:
            # 找到包含 marker 的行的位置
            # 我们需要获取该行的属性（如宽度等）来创建新的单元格
            ref_row = trs[marker_row_idx]
            ref_tc = ref_row.findall(W + 'tc')[marker_col_idx] if marker_col_idx < len(ref_row.findall(W + 'tc')) else None

            def create_cell_text(text: str, ref_tc: etree._Element = None) -> etree._Element:
                """创建包含文本的单元格"""
                if ref_tc is not None:
                    # 复制单元格属性
                    new_tc = etree.fromstring(etree.tostring(ref_tc))
                    # 清空内容
                    for child in list(new_tc):
                        tag = etree.QName(child.tag).localname
                        if tag != 'pPr':  # 保留段落属性
                            new_tc.remove(child)
                    # 添加文本段落
                    p = new_tc.find(W + 'p')
                    if p is None:
                        p = etree.SubElement(new_tc, W + 'p')
                    # 清空段落内容
                    for child in list(p):
                        tag = etree.QName(child.tag).localname
                        if tag != 'pPr':
                            p.remove(child)
                    # 添加文本
                    r = etree.SubElement(p, W + 'r')
                    t = etree.SubElement(r, W + 't')
                    t.text = text
                    return new_tc
                else:
                    # 创建新单元格
                    new_tc = etree.Element(W + 'tc')
                    p = etree.SubElement(new_tc, W + 'p')
                    r = etree.SubElement(p, W + 'r')
                    t = etree.SubElement(r, W + 't')
                    t.text = text
                    return new_tc

            def create_empty_cell() -> etree._Element:
                """创建空单元格"""
                new_tc = etree.Element(W + 'tc')
                p = etree.SubElement(new_tc, W + 'p')
                r = etree.SubElement(p, W + 'r')
                t = etree.SubElement(r, W + 't')
                t.text = ''
                return new_tc

            # 替换 marker 单元格为新的 4x4 表格
            # 找到 marker_tc 在 author_tbl 中的位置
            all_tcs_in_tbl = list(author_tbl.iter(W + 'tc'))
            if marker_tc in all_tcs_in_tbl:
                tc_idx_in_tbl = all_tcs_in_tbl.index(marker_tc)

                # 计算 marker_tc 在第几行第几列
                cum_cols = 0
                target_row_idx = 0
                target_col_idx = 0
                for ri, row in enumerate(trs):
                    tcs_in_row = row.findall(W + 'tc')
                    if tc_idx_in_tbl >= cum_cols and tc_idx_in_tbl < cum_cols + len(tcs_in_row):
                        target_row_idx = ri
                        target_col_idx = tc_idx_in_tbl - cum_cols
                        break
                    cum_cols += len(tcs_in_row)

                # 获取该行用于复制属性
                ref_row_elem = trs[target_row_idx] if target_row_idx < len(trs) else None
                ref_tc_elem = None
                if ref_row_elem is not None:
                    ref_tcs_in_row = ref_row_elem.findall(W + 'tc')
                    if target_col_idx < len(ref_tcs_in_row):
                        ref_tc_elem = ref_tcs_in_row[target_col_idx]

                # 创建新行
                new_row1 = etree.SubElement(author_tbl, W + 'tr')
                new_row2 = etree.SubElement(author_tbl, W + 'tr')
                new_row3 = etree.SubElement(author_tbl, W + 'tr')
                new_row4 = etree.SubElement(author_tbl, W + 'tr')

                # 为每行添加4个单元格
                for cell_text in row1_cells:
                    new_tc = create_cell_text(cell_text, ref_tc_elem)
                    new_row1.append(new_tc)
                for cell_text in row2_cells:
                    new_tc = create_cell_text(cell_text, ref_tc_elem)
                    new_row2.append(new_tc)
                for cell_text in row3_cells:
                    new_tc = create_cell_text(cell_text, ref_tc_elem)
                    new_row3.append(new_tc)
                for cell_text in row4_cells:
                    new_tc = create_cell_text(cell_text, ref_tc_elem)
                    new_row4.append(new_tc)

    return doc


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


def replace_abstract_in_doc(doc: Document, table: int, row: int,
                           col_start: int, col_end: int) -> Document:
    """在文档中替换摘要区域为 {{ abstract }} 占位符（返回新文档）。

    只在第一个单元格设置占位符，其他单元格清空内容。
    清空时会删除所有内容，包括图表、图片等。

    使用 lxml 直接解析以正确处理合并单元格。

    Args:
        doc: Document 对象
        table: 表格索引（基于 lxml 的表格索引）
        row: 行索引
        col_start: 起始列索引
        col_end: 结束列索引

    Returns:
        修改后的 Document 对象
    """
    from lxml import etree

    W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'

    # 获取文档的 body 元素
    body = doc._body._body

    # 使用 lxml 找到所有表格（与 find_abstract_by_elements 一致的索引方式）
    all_tables = list(body.findall(f'.//{W}tbl'))

    if table >= len(all_tables):
        raise ValueError(f"表格索引 {table} 超出范围 (lxml找到{len(all_tables)}个表格)")

    tbl_element = all_tables[table]

    # 获取表格的行
    trs = tbl_element.findall(W + 'tr')
    if row >= len(trs):
        raise ValueError(f"行索引 {row} 超出范围")

    tbl_row = trs[row]

    # 替换指定范围的单元格
    first_cell = True
    for col_idx in range(col_start, min(col_end + 1, len(tbl_row.findall(W + 'tc')))):
        tc = tbl_row.findall(W + 'tc')[col_idx]

        if first_cell:
            # 第一个单元格：清空所有内容，只保留一个段落设置占位符
            # 删除单元格内除第一个段落外的所有子元素（段落、表格等）
            children_to_remove = []
            first_p = None
            for child in tc:
                tag = etree.QName(child.tag).localname
                if tag == 'p':
                    if first_p is None:
                        first_p = child
                    else:
                        children_to_remove.append(child)
                elif tag == 'tbl':
                    children_to_remove.append(child)

            # 删除多余元素
            for child in children_to_remove:
                tc.remove(child)

            # 清空第一个段落的所有内容（包括图表 w:drawing）
            if first_p is not None:
                # 删除所有 run 和其他内容元素
                for child in list(first_p):
                    tag = etree.QName(child.tag).localname
                    if tag not in ('pPr',):  # 保留段落属性
                        first_p.remove(child)

                # 添加新的 run 包含占位符
                r = etree.SubElement(first_p, f'{W}r')
                t = etree.SubElement(r, f'{W}t')
                t.text = "{{ abstract }}"

            first_cell = False
        else:
            # 其他单元格：完全清空内容
            children_to_remove = []
            first_p = None
            for child in tc:
                tag = etree.QName(child.tag).localname
                if tag == 'p':
                    if first_p is None:
                        first_p = child
                    else:
                        children_to_remove.append(child)
                elif tag == 'tbl':
                    children_to_remove.append(child)

            # 删除多余元素
            for child in children_to_remove:
                tc.remove(child)

            # 清空第一个段落
            if first_p is not None:
                for child in list(first_p):
                    tag = etree.QName(child.tag).localname
                    if tag not in ('pPr',):
                        first_p.remove(child)

    return doc


def replace_abstract_in_doc_by_paragraph(doc: Document, start_paragraph: int,
                                        end_paragraph: int) -> Document:
    """在文档中替换摘要区域为 {{ abstract }} 占位符（返回新文档）。

    使用段落索引来确定范围，删除范围内的所有内容，只保留一个占位符。
    关键修复：正确处理段落位于表格/SDT 嵌套内的情况，只删除目标段落本身，
    而不影响文档中的其他内容。

    Args:
        doc: Document 对象
        start_paragraph: 起始段落索引（python-docx paragraphs索引）
        end_paragraph: 结束段落索引（不包含）

    Returns:
        修改后的 Document 对象
    """
    from lxml import etree

    W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'

    if start_paragraph >= len(doc.paragraphs):
        raise ValueError(f"起始段落 {start_paragraph} 超出范围")

    # 获取 body 元素
    body = doc._body._body

    # 建立 doc.paragraphs 索引到 body 直接子元素的映射
    body_children = list(body)

    # 创建更精确的映射：段落索引 -> (body_children索引, 元素, 是否是body直接子元素)
    para_info = {}

    for body_idx, child in enumerate(body_children):
        tag = etree.QName(child.tag).localname
        if tag == 'p':
            # body直接子元素就是段落元素
            for para_idx, para in enumerate(doc.paragraphs):
                if para._element is child:
                    para_info[para_idx] = (body_idx, child, True)
                    break
        elif tag == 'tbl':
            # 表格元素：表格内段落不建立直接映射，避免删除整个表格
            # 只记录表格在 body_children 中的位置
            pass
        elif tag == 'sdt':
            # SDT 元素：同上
            pass

    # 找到起始和结束段落对应的 body_children 元素
    start_para_elem = doc.paragraphs[start_paragraph]._element
    end_para_elem = doc.paragraphs[end_paragraph - 1]._element if end_paragraph > 0 else None

    # 收集要处理的段落元素（从起始到结束的所有段落）
    paragraphs_to_process = []
    for para_idx in range(start_paragraph, end_paragraph):
        if para_idx in para_info:
            _, elem, is_direct = para_info[para_idx]
            if is_direct:
                paragraphs_to_process.append((para_idx, elem))

    # 如果没有找到直接的段落元素，尝试通过 body_children 遍历
    if not paragraphs_to_process:
        # 找到起始和结束段落所在的 body_children 范围
        start_body_idx = 0
        end_body_idx = len(body_children) - 1

        # 遍历 body_children 找到包含起始和结束段落的元素
        for body_idx, child in enumerate(body_children):
            if start_para_elem in child.iter():
                start_body_idx = body_idx
            if end_para_elem and end_para_elem in child.iter():
                end_body_idx = body_idx
                break

        # 收集范围内的所有 body_children 元素
        elements_to_remove = []
        first_body_element = None

        for body_idx in range(start_body_idx, end_body_idx + 1):
            child = body_children[body_idx]
            tag = etree.QName(child.tag).localname

            if first_body_element is None:
                first_body_element = child

            # 只收集段落元素，不收集表格（避免删除整个表格）
            if tag == 'p':
                elements_to_remove.append(child)
            elif tag == 'tbl' or tag == 'sdt':
                # 检查表格/SDT 是否包含在范围内
                if start_para_elem in child.iter() or (end_para_elem and end_para_elem in child.iter()):
                    # 表格/SDT 被部分包含，收集它但后续会特殊处理
                    elements_to_remove.append(child)

    else:
        # 使用精确的段落信息
        elements_to_remove = [elem for _, elem in paragraphs_to_process]
        first_body_element = elements_to_remove[0] if elements_to_remove else None

    # 删除收集的元素（从后往前删除，保留第一个用于放置占位符）
    for element in reversed(elements_to_remove[1:]):
        body.remove(element)

    # 在第一个元素位置设置占位符
    if first_body_element is not None and elements_to_remove:
        tag = etree.QName(first_body_element.tag).localname

        if tag == 'p':
            # 如果第一个是段落，清空内容设置占位符
            for child in list(first_body_element):
                child_tag = etree.QName(child.tag).localname
                if child_tag not in ('pPr',):
                    first_body_element.remove(child)

            # 添加新的 run 包含占位符
            r = etree.SubElement(first_body_element, f'{W}r')
            t = etree.SubElement(r, f'{W}t')
            t.text = "{{ abstract }}"
        else:
            # 如果第一个不是段落，需要替换为段落
            idx = list(body).index(first_body_element)
            body.remove(first_body_element)

            # 创建新段落
            new_p = etree.Element(f'{W}p')
            r = etree.SubElement(new_p, f'{W}r')
            t = etree.SubElement(r, f'{W}t')
            t.text = "{{ abstract }}"

            body.insert(idx, new_p)
            first_body_element = new_p

    return doc


def replace_summary_in_doc(doc: Document, start_paragraph: int,
                          end_paragraph: int) -> Document:
    """在文档中替换 Summary 区域为 {{ summary }} 占位符（返回新文档）。

    删除 Summary 区域内的所有段落和表格，只保留一个占位符。
    使用段落索引来确定范围，确保正确处理所有内容。
    关键修复：正确处理段落位于表格/SDT 嵌套内的情况。

    Args:
        doc: Document 对象
        start_paragraph: 起始段落索引（python-docx paragraphs索引）
        end_paragraph: 结束段落索引（不包含）

    Returns:
        修改后的 Document 对象
    """
    from lxml import etree

    W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'

    if start_paragraph >= len(doc.paragraphs):
        raise ValueError(f"起始段落 {start_paragraph} 超出范围")

    # 获取 body 元素
    body = doc._body._body

    # 建立 doc.paragraphs 索引到 body 直接子元素的映射
    body_children = list(body)

    # 创建更精确的映射：段落索引 -> (body_children索引, 元素, 是否是body直接子元素)
    para_info = {}

    for body_idx, child in enumerate(body_children):
        tag = etree.QName(child.tag).localname
        if tag == 'p':
            for para_idx, para in enumerate(doc.paragraphs):
                if para._element is child:
                    para_info[para_idx] = (body_idx, child, True)
                    break
        elif tag == 'tbl':
            # 表格元素：不建立映射，避免删除整个表格
            pass
        elif tag == 'sdt':
            # SDT 元素：不建立映射，避免删除整个 SDT
            pass

    # 找到起始和结束段落对应的 body_children 元素
    start_para_elem = doc.paragraphs[start_paragraph]._element
    end_para_elem = doc.paragraphs[end_paragraph - 1]._element if end_paragraph > 0 else None

    # 收集要处理的段落元素
    paragraphs_to_process = []
    for para_idx in range(start_paragraph, end_paragraph):
        if para_idx in para_info:
            _, elem, is_direct = para_info[para_idx]
            if is_direct:
                paragraphs_to_process.append((para_idx, elem))

    # 如果没有找到直接的段落元素，通过 body_children 遍历
    if not paragraphs_to_process:
        start_body_idx = 0
        end_body_idx = len(body_children) - 1

        for body_idx, child in enumerate(body_children):
            if start_para_elem in child.iter():
                start_body_idx = body_idx
            if end_para_elem and end_para_elem in child.iter():
                end_body_idx = body_idx
                break

        elements_to_remove = []
        first_body_element = None

        for body_idx in range(start_body_idx, end_body_idx + 1):
            child = body_children[body_idx]
            tag = etree.QName(child.tag).localname

            if first_body_element is None:
                first_body_element = child

            if tag == 'p':
                elements_to_remove.append(child)
            elif tag == 'tbl' or tag == 'sdt':
                if start_para_elem in child.iter() or (end_para_elem and end_para_elem in child.iter()):
                    elements_to_remove.append(child)
    else:
        elements_to_remove = [elem for _, elem in paragraphs_to_process]
        first_body_element = elements_to_remove[0] if elements_to_remove else None

    # 删除收集的元素（从后往前删除，保留第一个用于放置占位符）
    for element in reversed(elements_to_remove[1:]):
        body.remove(element)

    # 在第一个元素位置设置占位符
    if first_body_element is not None and elements_to_remove:
        tag = etree.QName(first_body_element.tag).localname

        if tag == 'p':
            for child in list(first_body_element):
                child_tag = etree.QName(child.tag).localname
                if child_tag not in ('pPr',):
                    first_body_element.remove(child)

            r = etree.SubElement(first_body_element, f'{W}r')
            t = etree.SubElement(r, f'{W}t')
            t.text = "{{ summary }}"
        else:
            idx = list(body).index(first_body_element)
            body.remove(first_body_element)

            new_p = etree.Element(f'{W}p')
            r = etree.SubElement(new_p, f'{W}r')
            t = etree.SubElement(r, f'{W}t')
            t.text = "{{ summary }}"

            body.insert(idx, new_p)
            first_body_element = new_p

    return doc


def replace_body_in_doc(doc: Document, start_paragraph: int,
                       end_paragraph: int) -> Document:
    """在文档中替换正文区域为 {{ body }} 占位符（返回新文档）。

    删除正文区域内的所有元素（段落、表格、图表、目录等），只保留一个占位符。
    目录（SDT）也会被删除，因为目录内容会根据正文自动生成。
    保留正文结束处的分节符。

    使用段落索引来确定范围，确保正确处理所有内容。

    Args:
        doc: Document 对象
        start_paragraph: 起始段落索引（python-docx paragraphs索引）
        end_paragraph: 结束段落索引（不包含）

    Returns:
        修改后的 Document 对象
    """
    from lxml import etree
    from copy import deepcopy

    W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'

    if start_paragraph >= len(doc.paragraphs):
        raise ValueError(f"起始段落 {start_paragraph} 超出范围")

    # 获取 body 元素
    body = doc._body._body

    # 建立 doc.paragraphs 索引到 body 直接子元素的映射
    body_children = list(body)

    # 创建段落索引到 body_children 索引的映射
    # 关键修复：对于表格/SDT 内的段落，映射到表格/SDT 元素本身，而不是表格内的段落
    para_to_body_idx = {}

    for body_idx, child in enumerate(body_children):
        tag = etree.QName(child.tag).localname
        if tag == 'p':
            # body直接子元素就是段落元素
            for para_idx, para in enumerate(doc.paragraphs):
                if para._element is child:
                    para_to_body_idx[para_idx] = body_idx
                    break
        elif tag == 'tbl':
            # 表格元素：映射到表格本身，避免删除整个表格后重新计算索引
            # 找到这个表格的第一个段落在 doc.paragraphs 中的位置
            first_para_in_table = None
            for p_elem in child.iter(f'{W}p'):
                for para_idx, para in enumerate(doc.paragraphs):
                    if para._element is p_elem:
                        para_to_body_idx[para_idx] = body_idx
                        if first_para_in_table is None:
                            first_para_in_table = para_idx
                        break
                if first_para_in_table is not None:
                    break
        elif tag == 'sdt':
            # SDT 元素：同上
            first_para_in_sdt = None
            for p_elem in child.iter(f'{W}p'):
                for para_idx, para in enumerate(doc.paragraphs):
                    if para._element is p_elem:
                        para_to_body_idx[para_idx] = body_idx
                        if first_para_in_sdt is None:
                            first_para_in_sdt = para_idx
                        break
                if first_para_in_sdt is not None:
                    break

    # 找到起始和结束位置对应的 body_children 索引
    start_body_idx = para_to_body_idx.get(start_paragraph, 0)
    end_body_idx = para_to_body_idx.get(end_paragraph - 1, len(body_children) - 1)

    # 确保 start_body_idx < end_body_idx
    if start_body_idx > end_body_idx:
        start_body_idx, end_body_idx = end_body_idx, start_body_idx

    # 收集要删除的元素（正文区域内的所有 body_children 元素）
    elements_to_remove = []
    first_body_element = None
    last_sect_pr = None

    for body_idx in range(start_body_idx, end_body_idx + 1):
        child = body_children[body_idx]
        tag = etree.QName(child.tag).localname

        if first_body_element is None:
            first_body_element = child

        elements_to_remove.append(child)

        # 检查段落是否有分节符
        if tag == 'p':
            sect_pr = child.find(f'.//{W}sectPr')
            if sect_pr is not None:
                last_sect_pr = deepcopy(sect_pr)

    # 删除收集的元素（从后往前删除，保留第一个用于放置占位符）
    for element in reversed(elements_to_remove[1:]):
        body.remove(element)

    # 在第一个元素位置设置占位符
    if first_body_element is not None and elements_to_remove:
        tag = etree.QName(first_body_element.tag).localname

        if tag == 'p':
            # 如果第一个是段落，清空内容设置占位符
            for child in list(first_body_element):
                child_tag = etree.QName(child.tag).localname
                if child_tag not in ('pPr',):
                    first_body_element.remove(child)

            r = etree.SubElement(first_body_element, f'{W}r')
            t = etree.SubElement(r, f'{W}t')
            t.text = "{{ body }}"
        else:
            # 如果第一个不是段落（如表格），需要替换为段落
            idx = list(body).index(first_body_element)
            body.remove(first_body_element)

            new_p = etree.Element(f'{W}p')
            r = etree.SubElement(new_p, f'{W}r')
            t = etree.SubElement(r, f'{W}t')
            t.text = "{{ body }}"

            body.insert(idx, new_p)
            first_body_element = new_p

        # 如果有分节符，添加到 body 占位符段落
        if last_sect_pr is not None:
            pPr = first_body_element.find(f'{W}pPr')
            if pPr is None:
                pPr = etree.Element(f'{W}pPr')
                first_body_element.insert(0, pPr)
            pPr.append(last_sect_pr)

    # 清理图表关系：删除 document.xml.rels 中的图表引用
    # 这样 save_document_with_cleanup 会将图表视为孤立文件并删除
    try:
        # 获取文档的内部 zip 结构
        from docx.opc.constants import RELATIONSHIP_TYPE as RT
        import zipfile
        import io

        # 保存到内存
        buffer = io.BytesIO()
        doc.save(buffer)
        buffer.seek(0)

        # 读取并修改 relationships
        with zipfile.ZipFile(buffer, 'r') as zin:
            rels_content = zin.read('word/_rels/document.xml.rels')

        # 解析 XML
        rels_tree = etree.fromstring(rels_content)
        nsmap = {'r': 'http://schemas.openxmlformats.org/package/2006/relationships'}

        # 找到并删除所有 chart 引用
        chart_rels_to_remove = []
        for rel in rels_tree.findall('r:Relationship', nsmap):
            rel_type = rel.get('Type', '')
            target = rel.get('Target', '')
            if 'chart' in rel_type.lower() or (target.startswith('charts/') and target.endswith('.xml')):
                chart_rels_to_remove.append(rel)

        for rel in chart_rels_to_remove:
            rels_tree.remove(rel)

        # 重新序列化为 XML
        new_rels_content = etree.tostring(rels_tree, xml_declaration=True, encoding='UTF-8', standalone=True)

        # 更新 buffer 中的文件
        buffer.seek(0)
        output_buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'r') as zin:
            with zipfile.ZipFile(output_buffer, 'w', zipfile.ZIP_DEFLATED) as zout:
                for item in zin.namelist():
                    if item == 'word/_rels/document.xml.rels':
                        zout.writestr(item, new_rels_content)
                    else:
                        zout.writestr(item, zin.read(item))

        # 重新加载文档
        output_buffer.seek(0)
        from docx import Document
        doc = Document(output_buffer)

    except Exception as e:
        # 如果清理失败，继续使用原始文档（图表会被保留）
        import traceback
        traceback.print_exc()
        print(f'  警告: 清理图表关系失败: {e}')

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
