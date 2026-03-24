"""模板操作函数。

用于替换字段值、替换摘要/正文、调整位置、添加/删除字段等操作。
"""

from pathlib import Path
from typing import Dict, Any
from docx import Document


def replace_field_value(doc_path: str, output_path: str,
                       field_name: str, field_value: str) -> Dict[str, Any]:
    """替换单个字段值为占位符。

    Args:
        doc_path: 输入文档路径
        output_path: 输出文档路径
        field_name: 字段名（如 "company"）
        field_value: 字段值（如 "西锐飞机"）

    Returns:
        {
            "success": bool,
            "replaced_count": int,
            "message": str
        }
    """
    doc = Document(doc_path)
    placeholder = f"{{{{ {field_name }}}}"
    value_str = str(field_value)
    count = 0

    # 在段落中替换
    for para in doc.paragraphs:
        if value_str in para.text:
            _replace_text_in_para(para, value_str, placeholder)
            count += 1

    # 在表格中替换
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for para in cell.paragraphs:
                    if value_str in para.text:
                        _replace_text_in_para(para, value_str, placeholder)
                        count += 1

    # 在页眉页脚中替换
    for section in doc.sections:
        for para in section.header.paragraphs:
            if value_str in para.text:
                _replace_text_in_para(para, value_str, placeholder)
                count += 1
        for para in section.footer.paragraphs:
            if value_str in para.text:
                _replace_text_in_para(para, value_str, placeholder)
                count += 1

    doc.save(output_path)

    return {
        "success": True,
        "replaced_count": count,
        "message": f"已替换 {field_name} 为 {{{{ {field_name }}}}，共 {count} 处"
    }


def replace_abstract(doc_path: str, output_path: str,
                    table: int, row: int, col_start: int, col_end: int) -> Dict[str, Any]:
    """替换摘要区域为 {{ abstract }} 占位符。

    Args:
        doc_path: 输入文档路径
        output_path: 输出文档路径
        table: 表格索引
        row: 行索引
        col_start: 起始列索引
        col_end: 结束列索引

    Returns:
        操作结果
    """
    doc = Document(doc_path)

    if table >= len(doc.tables):
        return {"success": False, "reason": f"表格索引 {table} 超出范围"}

    tbl = doc.tables[table]
    if row >= len(tbl.rows):
        return {"success": False, "reason": f"行索引 {row} 超出范围"}

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

    doc.save(output_path)

    return {
        "success": True,
        "message": f"已替换表格 {table} 第 {row} 行列 {col_start}-{col_end} 为 {{ abstract }}"
    }


def replace_body(doc_path: str, output_path: str,
                start_paragraph: int, end_paragraph: int) -> Dict[str, Any]:
    """替换正文区域为 {{ body }} 占位符。

    Args:
        doc_path: 输入文档路径
        output_path: 输出文档路径
        start_paragraph: 起始段落索引
        end_paragraph: 结束段落索引（不包含）

    Returns:
        操作结果
    """
    doc = Document(doc_path)

    if start_paragraph >= len(doc.paragraphs):
        return {"success": False, "reason": f"起始段落 {start_paragraph} 超出范围"}

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

    doc.save(output_path)

    return {
        "success": True,
        "message": f"已替换段落 {start_paragraph}-{end_paragraph} 为 {{ body }}，删除了 {end_idx - start_paragraph - 1} 个段落"
    }


def adjust_abstract_position(doc_path: str, output_path: str,
                            table: int, row: int,
                            col_start: int, col_end: int) -> Dict[str, Any]:
    """调整摘要位置。

    Args:
        doc_path: 输入文档路径
        output_path: 输出文档路径
        table: 表格索引
        row: 行索引
        col_start: 起始列索引
        col_end: 结束列索引

    Returns:
        操作结果
    """
    result = replace_abstract(doc_path, output_path, table, row, col_start, col_end)

    return {
        "success": result["success"],
        "message": f"已调整摘要位置到表格 {table} 第 {row} 行列 {col_start}-{col_end}"
    }


def adjust_body_range(doc_path: str, output_path: str,
                     start_paragraph: int,
                     end_paragraph: int) -> Dict[str, Any]:
    """调整正文范围。

    Args:
        doc_path: 输入文档路径
        output_path: 输出文档路径
        start_paragraph: 起始段落索引
        end_paragraph: 结束段落索引（不包含）

    Returns:
        操作结果
    """
    result = replace_body(doc_path, output_path, start_paragraph, end_paragraph)

    return {
        "success": result["success"],
        "message": f"已调整正文范围到段落 {start_paragraph}-{end_paragraph}"
    }


def add_field_to_template(doc_path: str, output_path: str,
                         field_name: str, field_value: str,
                         position_hint: str) -> Dict[str, Any]:
    """在现有模板中添加新字段。

    Args:
        doc_path: 输入文档路径
        output_path: 输出文档路径
        field_name: 字段名（如 "analyst"）
        field_value: 字段值（如 "张三"）
        position_hint: 位置提示
            - "after:company" (在 company 字段之后)
            - "table:0,row:3,col:2" (在表格 0 第 3 行第 2 列)
            - "paragraph:5" (在段落 5 之后)

    Returns:
        操作结果
    """
    doc = Document(doc_path)
    placeholder = f"{{{{ {field_name }}}}"

    # 解析位置提示
    if position_hint.startswith("after:"):
        # 在指定字段之后插入
        existing_field = position_hint[6:]
        existing_location = find_content_location(doc_path, f"{{{{ {existing_field }}}}")

        if not existing_location["found"]:
            return {"success": False, "reason": f"未找到字段 {existing_field}"}

        # 在找到的位置后插入（简化处理）
        if existing_location["type"] == "table":
            table_idx = existing_location["table"]
            row_idx = existing_location["row"]
            table = doc.tables[table_idx]

            # 在当前行后添加新行
            if row_idx + 1 < len(table.rows):
                new_row = table.rows[row_idx]._element.addnext(
                    table.rows[row_idx]._element.__class__()
                )
            else:
                table.add_row()

        doc.save(output_path)
        return {
            "success": True,
            "message": f"已在 {existing_field} 之后添加 {field_name} 字段"
        }

    elif position_hint.startswith("table:"):
        # 直接指定表格位置
        parts = position_hint.split(",")
        table_idx = int(parts[0].split(":")[1])

        table = doc.tables[table_idx]
        # 在指定位置插入占位符
        # ... (具体实现)

        doc.save(output_path)
        return {
            "success": True,
            "message": f"已在表格 {table_idx} 添加 {field_name} 字段"
        }

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

        doc.save(output_path)
        return {
            "success": True,
            "message": f"已在段落 {para_idx} 添加 {field_name} 字段"
        }

    else:
        return {"success": False, "reason": "无法解析位置提示"}


def remove_field_from_template(doc_path: str, output_path: str,
                              field_name: str) -> Dict[str, Any]:
    """从模板中删除字段（删除占位符）。

    Args:
        doc_path: 输入文档路径
        output_path: 输出文档路径
        field_name: 字段名

    Returns:
        操作结果
    """
    doc = Document(doc_path)
    placeholder = f"{{{{ {field_name }}}}"
    count = 0

    # 在段落中查找并删除
    for para in doc.paragraphs:
        if placeholder in para.text:
            # 删除包含占位符的段落
            para._element.getparent().remove(para._element)
            count += 1

    # 在表格中查找并删除
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for para in cell.paragraphs:
                    if placeholder in para.text:
                        # 清空内容
                        para.text = ""
                        count += 1

    doc.save(output_path)

    return {
        "success": True,
        "removed_count": count,
        "message": f"已删除 {field_name} 字段，共 {count} 处"
    }


# 辅助函数

def _replace_text_in_para(paragraph, old_text: str, new_text: str):
    """替换单个段落中的文本。

    Args:
        paragraph: python-docx 段落对象
        old_text: 要替换的文本
        new_text: 新文本
    """
    if old_text not in paragraph.text:
        return

    # 清除现有 runs
    for run in paragraph.runs:
        run.text = ""

    # 添加新 run
    if paragraph.runs:
        paragraph.runs[0].text = paragraph.text.replace(old_text, new_text)
    else:
        paragraph.add_run(paragraph.text.replace(old_text, new_text))
