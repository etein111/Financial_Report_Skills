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

def save_document_with_cleanup(doc: Document, output_path: str) -> None:
    """保存 Word 文档并清理孤立的嵌入对象（图表、Excel 等）。

    当删除正文区域后，原有的图表和嵌入对象可能不再被引用，
    此函数会自动清理这些孤立文件，减小文档大小。

    Args:
        doc: Document 对象
        output_path: 输出路径
    """
    import zipfile
    import io
    from lxml import etree

    # 先保存到内存
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    doc_bytes = buffer.read()

    used_files = set()
    try:
        with zipfile.ZipFile(io.BytesIO(doc_bytes), 'r') as z:
            rId_to_target = {}
            try:
                with z.open('word/_rels/document.xml.rels') as f:
                    tree = etree.parse(f)
                    for rel in tree.iter('{http://schemas.openxmlformats.org/package/2006/relationships}Relationship'):
                        rid = rel.get('Id')
                        target = rel.get('Target')
                        if rid and target:
                            rId_to_target[rid] = target
            except KeyError:
                pass

            chart_ole_refs = set()
            for name in z.namelist():
                if name.startswith('word/charts/_rels/') and name.endswith('.xml.rels'):
                    try:
                        with z.open(name) as f:
                            chart_tree = etree.parse(f)
                            for rel in chart_tree.iter('{http://schemas.openxmlformats.org/package/2006/relationships}Relationship'):
                                target = rel.get('Target')
                                rel_type = rel.get('Type')
                                if target and ('oleObject' in rel_type or 'package' in rel_type or 'Workbook' in target):
                                    if 'embeddings/' in target:
                                        fname = target.split('embeddings/')[-1]
                                        chart_ole_refs.add(f'embeddings/{fname}')
                                    elif target.startswith('embeddings/'):
                                        chart_ole_refs.add(target)
                    except Exception:
                        pass

            for rid, target in rId_to_target.items():
                if 'embeddings/' in target:
                    used_files.add(target)
                elif target.startswith('../embeddings/'):
                    used_files.add(target.replace('../', ''))
            for ref in chart_ole_refs:
                if 'embeddings/' in ref:
                    used_files.add(ref)

            essential_files = {'word/document.xml', 'word/styles.xml', 'word/settings.xml',
                             'word/numbering.xml', 'Content_Types.xml', '[Content_Types].xml'}

            referenced_charts = set()
            for rid, target in rId_to_target.items():
                if 'charts/chart' in target:
                    if target.startswith('charts/'):
                        referenced_charts.add(f'word/{target}')
                    elif target.startswith('word/charts/'):
                        referenced_charts.add(target)

            referenced_embeddings = set()
            for rid, target in rId_to_target.items():
                if 'embeddings/' in target:
                    referenced_embeddings.add(f'word/{target}')
                elif target.startswith('../embeddings/'):
                    referenced_embeddings.add(f'word/{target.replace("../", "")}')
            for ref in chart_ole_refs:
                if ref.startswith('embeddings/'):
                    referenced_embeddings.add(f'word/{ref}')

            # 收集所有被引用的 media 文件
            # 需要检查 rId 是否真的在文档内容中被使用
            referenced_media = set()
            rId_to_media = {}
            for rid, target in rId_to_target.items():
                if 'media/' in target:
                    rId_to_media[rid] = f'word/{target}'

            # 检查 document.xml 中实际使用的 rId 引用
            doc_content = z.read('word/document.xml').decode('utf-8', errors='ignore')
            import re
            used_rids = set(re.findall(r'r:embed="(rId\d+)"', doc_content))

            # 也检查 header 和 footer 文件
            for name in z.namelist():
                if name.startswith('word/header') and name.endswith('.xml'):
                    try:
                        content = z.read(name).decode('utf-8', errors='ignore')
                        used_rids.update(re.findall(r'r:embed="(rId\d+)"', content))
                    except:
                        pass
                elif name.startswith('word/footer') and name.endswith('.xml'):
                    try:
                        content = z.read(name).decode('utf-8', errors='ignore')
                        used_rids.update(re.findall(r'r:embed="(rId\d+)"', content))
                    except:
                        pass

            # 只添加实际被使用的 media 文件
            for rid in used_rids:
                if rid in rId_to_media:
                    referenced_media.add(rId_to_media[rid])

            # 也检查 chart 中的内嵌媒体引用
            for name in z.namelist():
                if name.startswith('word/charts/') and name.endswith('.xml'):
                    try:
                        chart_content = z.read(name).decode('utf-8', errors='ignore')
                        for match in chart_content.split('media/'):
                            if '/' in match or '\\' in match:
                                parts = (match.split('/')[0] if '/' in match else match.split('\\')[0]).split('"')[0].split('>')[0]
                                if parts and not parts.startswith('..'):
                                    referenced_media.add(f'word/media/{parts}')
                    except:
                        pass

            all_files = set(z.namelist())
            files_to_delete = set()
            for f in all_files:
                if f in essential_files or f.startswith('word/_rels/'):
                    continue
                if '/_rels/' in f or f.endswith('.rels'):
                    continue
                if f.startswith('word/charts/chart'):
                    if f.endswith('.xml.rels'):
                        continue
                    if f not in referenced_charts:
                        files_to_delete.add(f)
                        files_to_delete.add(f + '.rels')
                elif f.startswith('word/embeddings/'):
                    if f not in referenced_embeddings:
                        files_to_delete.add(f)
                elif f.startswith('word/media/'):
                    if f not in referenced_media:
                        files_to_delete.add(f)

            if not files_to_delete:
                with open(output_path, 'wb') as dst:
                    dst.write(doc_bytes)
                return

            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as new_z:
                for item in z.namelist():
                    if item not in files_to_delete:
                        new_z.writestr(item, z.read(item))
            print(f'  已清理 {len(files_to_delete)} 个孤立文件')
    except Exception as e:
        with open(output_path, 'wb') as dst:
            dst.write(doc_bytes)
        print(f'  清理失败，使用原始保存: {e}')


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

    # 替换有值的分析师信息（使用 Jinja2 if-block 格式）
    for i, data in analysts.items():
        # 姓名+SFC 占位符（带Jinja2 if条件）
        # 格式: {% if a1_cn %} {{ a1_cn }} {{ a1_en }}], SFC:{{ a1_sfc }}
        info_placeholder = '{% if a' + str(i) + '_cn %} {{ a' + str(i) + '_cn }} {{ a' + str(i) + '_en }}], SFC:{{ a' + str(i) + '_sfc }}'
        email_placeholder = '{{ a' + str(i) + '_email }} {% endif %}'

        if data['cn'] and data['en'] and data['sfc']:
            # 构造可能的组合格式（文档中的格式可能有变化）
            info_patterns = [
                f"{data['cn']}·{data['en']}，SFC:{data['sfc']}",
                f"{data['cn']} {data['en']}], SFC:{data['sfc']}",  # 逗号后有空格
                f"{data['cn']} {data['en']}],SFC:{data['sfc']}",   # 逗号后无空格
                f"{data['cn']}·{data['en']}, SFC:{data['sfc']}",
                f"{data['cn']} {data['en']}, SFC:{data['sfc']}",
                f"{data['cn']}{data['en']}, SFC:{data['sfc']}",   # 无空格（常见格式）
            ]

            # 在文档中查找并替换
            for pattern in info_patterns:
                _replace_text_in_nested_tables(doc, pattern, info_placeholder)

        if data['email']:
            _replace_text_in_nested_tables(doc, data['email'], email_placeholder)

    # 为分析师表格中的所有位置创建占位符（动态计算位置）
    # 算法：
    # 1. 数据行数 = rows - 1（减去标记行）
    # 2. 如果数据行是偶数：从第1行开始
    # 3. 如果数据行是奇数：跳过第1行（作为表头），从第2行开始
    # 4. 每2行一组，横向填充

    if author_tables:
        # 只处理第一个表格（其他都是合并单元格的视图）
        author_table = author_tables[0]

        # 根据表格列数计算能容纳的分析师数量，而不是根据实际有值的数量
        # 用户说 "2x5" 意思是 2行 x 5列，即5列横向排列
        # 用户说 "2x3，就是三个分析师一行"
        rows = len(author_table.rows)
        cols = len(author_table.columns)
        data_rows = rows - 1  # 减去标记行

        # 计算起始行
        if data_rows % 2 == 0:
            # 偶数数据行：从第1行开始
            start_row = 1
        else:
            # 奇数数据行：跳过第1行（作为表头），从第2行开始
            start_row = 2

        # 计算能填充的分析师数量（按列数填充，空值也填占位符）
        cols_available = cols  # 每列一个分析师
        groups = (rows - start_row) // 2  # 每2行一组（信息行+邮箱行）
        analyst_count = cols_available * groups

        # 动态计算填充位置
        analyst_positions = _calculate_analyst_positions(author_table, analyst_count)

        # 直接在 XML 级别操作，避免 python-docx 处理合并单元格的问题
        from lxml import etree
        W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'

        def _get_cell_text(tc):
            """获取单元格直接子元素的文本（不包括嵌套 tc 的文本）。"""
            parts = []
            for elem in tc:
                if elem.tag == W + 'p':
                    for r in elem:
                        if r.tag == W + 'r':
                            t = r.find(W + 't')
                            if t is not None and t.text:
                                parts.append(t.text)
            return ''.join(parts)

        # 获取 author_table 的底层 XML 元素
        author_tbl = author_table._tbl

        for info_row, col, email_row, _, analyst_idx in analyst_positions:
            i = analyst_idx

            # 构建 Jinja2 格式的占位符
            info_placeholder = '{% if a' + str(i) + '_cn %} {{ a' + str(i) + '_cn }} {{ a' + str(i) + '_en }}], SFC:{{ a' + str(i) + '_sfc }}'
            email_placeholder = '{{ a' + str(i) + '_email }} {% endif %}'

            # 直接在 author_tbl 中查找对应的单元格
            trs = author_tbl.findall(W + 'tr')
            if info_row >= len(trs):
                continue

            tr = trs[info_row]
            tcs = tr.findall(W + 'tc')

            # 处理信息单元格（姓名+SFC）
            if col < len(tcs):
                tc = tcs[col]
                tc_text = _get_cell_text(tc)
                if '{% if a' + str(i) + '_cn %}' not in tc_text:
                    # 清理所有段落，只保留第一个 paragraph 的第一个 run
                    paras = tc.findall(W + 'p')
                    for p in paras[1:]:
                        tc.remove(p)
                    # 设置新文本
                    paras = tc.findall(W + 'p')
                    if paras:
                        first_para = paras[0]
                        runs = first_para.findall(W + 'r')
                        if runs:
                            t = runs[0].find(W + 't')
                            if t is not None:
                                t.text = info_placeholder

            # 处理邮箱单元格
            if email_row < len(trs):
                tr_email = trs[email_row]
                tcs_email = tr_email.findall(W + 'tc')
                if col < len(tcs_email):
                    tc = tcs_email[col]
                    tc_text = _get_cell_text(tc)
                    if '{% endif %}' not in tc_text:
                        paras = tc.findall(W + 'p')
                        for p in paras[1:]:
                            tc.remove(p)
                        paras = tc.findall(W + 'p')
                        if paras:
                            first_para = paras[0]
                            runs = first_para.findall(W + 'r')
                            if runs:
                                t = runs[0].find(W + 't')
                                if t is not None:
                                    t.text = email_placeholder

    return doc


def _count_analysts_with_data(elements: dict) -> int:
    """计算 elements 中实际有值的分析师数量。

    Args:
        elements: 包含分析师字段的字典

    Returns:
        有数据的分析师数量
    """
    count = 0
    for i in range(1, 9):
        if elements.get(f'a{i}_cn') or elements.get(f'a{i}_en'):
            count += 1
    return count


def _calculate_analyst_positions(author_table, analyst_count: int) -> list:
    """根据表格维数和分析师数量计算填充位置。

    算法：
    1. 数据行数 = rows - 1（减去标记行）
    2. 如果数据行是偶数：从第1行开始
    3. 如果数据行是奇数：跳过第1行（作为表头），从第2行开始
    4. 每2行一组，横向填充

    Args:
        author_table: 分析师表格对象
        analyst_count: 实际有值的分析师数量

    Returns:
        list of (info_row, col, email_row, col, analyst_idx)
    """
    rows = len(author_table.rows)
    cols = len(author_table.columns)
    data_rows = rows - 1  # 减去标记行

    positions = []

    # 计算起始行
    if data_rows % 2 == 0:
        # 偶数数据行：从第1行开始
        start_row = 1
    else:
        # 奇数数据行：跳过第1行（表头），从第2行开始
        start_row = 2

    # 计算能填充的分析师数量（取表格能容纳的数量和实际分析师数量的较小值）
    cols_available = cols  # 每组横向填满
    groups = (rows - start_row) // 2  # 能放几组
    max_analysts = cols_available * groups
    actual_count = min(analyst_count, max_analysts)

    # 生成位置
    analyst_idx = 1
    for group in range(groups):
        for col in range(cols_available):
            if analyst_idx > actual_count:
                break
            info_row = start_row + group * 2
            email_row = info_row + 1
            positions.append((info_row, col, email_row, col, analyst_idx))
            analyst_idx += 1
        if analyst_idx > actual_count:
            break

    return positions


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
    """设置单元格文本（清空现有内容后设置）。

    处理合并单元格时可能存在的重复内容问题。
    """
    from lxml import etree
    W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'

    # 获取单元格底层 XML 元素
    tc = cell._tc

    # 删除所有现有段落
    for p in tc.findall(W + 'p'):
        tc.remove(p)

    # 创建新段落（使用 rPr 保持格式兼容）
    new_p = etree.SubElement(tc, W + 'p')
    new_r = etree.SubElement(new_p, W + 'r')
    new_t = etree.SubElement(new_r, W + 't')
    new_t.text = text


def _set_cell_text_jinja(cell, placeholder: str):
    """设置单元格文本，处理可能重复的内容。

    有些模板（OpenCode生成）的单元格内容会重复，
    这个函数会清理重复内容后设置新文本。
    """
    from lxml import etree
    import re
    W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'

    # 获取单元格底层 XML 元素
    tc = cell._tc

    # 获取当前所有段落的文本，检测是否有重复
    all_text = ''.join(tc.itertext())

    # 如果文本看起来有重复（比如 {{ a1_cn }} 出现多次），清理一下
    # 通过检查段落的 run 数量来判断
    paragraphs = tc.findall(W + 'p')
    runs_data = []
    for p in paragraphs:
        runs = p.findall(W + 'r')
        for r in runs:
            t = r.find(W + 't')
            if t is not None and t.text:
                runs_data.append(t.text)

    # 检查是否有连续重复的内容片段
    if len(runs_data) > 1:
        combined_text = ''.join(runs_data)
        # 尝试检测是否是重复模式：把文本对半拆分后比较
        half_len = len(combined_text) // 2
        if half_len > 10 and combined_text[:half_len] == combined_text[half_len:]:
            # 内容确实重复了，使用前半部分作为唯一内容
            unique_text = combined_text[:half_len]
            # 从 unique_text 中提取占位符
            # 格式如：{{ a1_cn }} {{ a1_en }}], SFC:{{ a1_sfc }}
            match = re.search(r'\{\{[^}]+\}\}', unique_text)
            if match:
                # 只保留占位符部分
                placeholder = match.group(0)
                # 如果有多行，只取第一行
                if '\\n' in placeholder:
                    placeholder = placeholder.split('\\n')[0]

    # 删除所有现有段落
    for p in tc.findall(W + 'p'):
        tc.remove(p)

    # 创建新段落
    new_p = etree.SubElement(tc, W + 'p')
    new_r = etree.SubElement(new_p, W + 'r')
    new_t = etree.SubElement(new_r, W + 't')
    new_t.text = placeholder


def replace_abstract_in_doc(doc: Document, table: int, row: int,
                           col_start: int, col_end: int) -> Document:
    """在文档中替换摘要区域为 {{ abstract }} 占位符（返回新文档）。

    只在第一个单元格设置占位符，其他单元格清空内容。
    清空时会删除所有内容，包括图表、图片等。

    Args:
        doc: Document 对象
        table: 表格索引
        row: 行索引
        col_start: 起始列索引
        col_end: 结束列索引

    Returns:
        修改后的 Document 对象
    """
    from lxml import etree

    if table >= len(doc.tables):
        raise ValueError(f"表格索引 {table} 超出范围")

    tbl = doc.tables[table]
    if row >= len(tbl.rows):
        raise ValueError(f"行索引 {row} 超出范围")

    tbl_row = tbl.rows[row]

    # 替换指定范围的单元格
    first_cell = True
    for col_idx in range(col_start, min(col_end + 1, len(tbl_row.cells))):
        cell = tbl_row.cells[col_idx]
        tc = cell._tc  # 获取底层 XML 元素

        if first_cell:
            # 第一个单元格：清空所有内容，只保留一个段落设置占位符
            # 删除单元格内除第一个段落外的所有子元素（段落、表格等）
            W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
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
            W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
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


def replace_summary_in_doc(doc: Document, start_paragraph: int,
                          end_paragraph: int) -> Document:
    """在文档中替换 Summary 区域为 {{ summary }} 占位符（返回新文档）。

    删除 Summary 区域内的所有段落和表格，只保留一个占位符。
    使用段落索引来确定范围，确保正确处理所有内容。

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

    # 创建段落索引到 body_children 索引的映射
    para_to_body_idx = {}

    for body_idx, child in enumerate(body_children):
        tag = etree.QName(child.tag).localname
        if tag == 'p':
            # body直接子元素就是段落元素
            # 找到这个段落在 doc.paragraphs 中的位置
            for para_idx, para in enumerate(doc.paragraphs):
                if para._element is child:
                    para_to_body_idx[para_idx] = body_idx
                    break
        elif tag == 'tbl':
            # 表格元素：检查表格内的每个段落在 doc.paragraphs 中的位置
            for p_elem in child.iter(f'{W}p'):
                for para_idx, para in enumerate(doc.paragraphs):
                    if para._element is p_elem:
                        para_to_body_idx[para_idx] = body_idx
                        break
        elif tag == 'sdt':
            # SDT 元素：检查 SDT 内的每个段落
            for p_elem in child.iter(f'{W}p'):
                for para_idx, para in enumerate(doc.paragraphs):
                    if para._element is p_elem:
                        para_to_body_idx[para_idx] = body_idx
                        break

    # 找到起始和结束位置对应的 body_children 索引
    start_body_idx = para_to_body_idx.get(start_paragraph, 0)
    end_body_idx = para_to_body_idx.get(end_paragraph - 1, len(body_children) - 1)

    # 确保 start_body_idx < end_body_idx
    if start_body_idx > end_body_idx:
        start_body_idx, end_body_idx = end_body_idx, start_body_idx

    # 收集要删除的元素（Summary 区域内的所有 body_children 元素）
    elements_to_remove = []
    first_body_element = None

    for body_idx in range(start_body_idx, end_body_idx + 1):
        child = body_children[body_idx]
        tag = etree.QName(child.tag).localname

        if first_body_element is None:
            first_body_element = child

        elements_to_remove.append(child)

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
            t.text = "{{ summary }}"
        else:
            # 如果第一个不是段落，需要替换为段落
            idx = list(body).index(first_body_element)
            body.remove(first_body_element)

            # 创建新段落
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
    # 对于 doc.paragraphs[n]，找到它在 body_children 中的直接父元素
    body_children = list(body)

    # 创建段落索引到 body_children 索引的映射
    # doc.paragraphs[n]._element 对应的 body_children 元素
    para_to_body_idx = {}

    for body_idx, child in enumerate(body_children):
        tag = etree.QName(child.tag).localname
        if tag == 'p':
            # body直接子元素就是段落元素
            # 找到这个段落在 doc.paragraphs 中的位置
            for para_idx, para in enumerate(doc.paragraphs):
                if para._element is child:
                    para_to_body_idx[para_idx] = body_idx
                    break
        elif tag == 'tbl':
            # 表格元素：检查表格内的每个段落在 doc.paragraphs 中的位置
            for p_elem in child.iter(f'{W}p'):
                for para_idx, para in enumerate(doc.paragraphs):
                    if para._element is p_elem:
                        para_to_body_idx[para_idx] = body_idx
                        break
        elif tag == 'sdt':
            # SDT 元素：检查 SDT 内的每个段落
            for p_elem in child.iter(f'{W}p'):
                for para_idx, para in enumerate(doc.paragraphs):
                    if para._element is p_elem:
                        para_to_body_idx[para_idx] = body_idx
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
            # 删除所有子元素（除了 pPr）
            for child in list(first_body_element):
                child_tag = etree.QName(child.tag).localname
                if child_tag not in ('pPr',):
                    first_body_element.remove(child)

            # 添加新的 run 包含占位符
            r = etree.SubElement(first_body_element, f'{W}r')
            t = etree.SubElement(r, f'{W}t')
            t.text = "{{ body }}"
        else:
            # 如果第一个不是段落（如表格），需要替换为段落
            idx = list(body).index(first_body_element)
            body.remove(first_body_element)

            # 创建新段落
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
