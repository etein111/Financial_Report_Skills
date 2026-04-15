#!/usr/bin/env python3
"""generate_nested_table_fixture.py - 生成包含嵌套表格的 Word 文档 fixture。

用于测试 field_extractor.py 中的嵌套表格解析功能。

生成的文档结构：
- 首页主表格（1行2列）：
  - 左单元格：公司信息 + 日期
  - 右单元格：嵌套的财务数据表格
- 嵌套表格包含：
  - 评级、目标价、当前价等字段
  - 分析师信息
"""

import sys
from pathlib import Path

# 添加 scripts 目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

try:
    from docx import Document
    from docx.shared import Pt, Cm
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
except ImportError:
    print("python-docx not installed. Run: uv pip install python-docx")
    sys.exit(1)


def create_nested_table_cell_with_table(parent_cell, nested_data):
    """在单元格内创建嵌套表格。

    Args:
        parent_cell: 父单元格
        nested_data: 嵌套表格数据 [[cell1, cell2], [cell3, cell4], ...]
    """
    # 添加一个段落作为分隔（如果需要）
    # 然后创建嵌套表格
    nested_table = parent_cell.add_table(rows=len(nested_data), cols=len(nested_data[0]) if nested_data else 2)
    nested_table.style = 'Table Grid'

    for row_idx, row_data in enumerate(nested_data):
        row = nested_table.rows[row_idx]
        for col_idx, cell_text in enumerate(row_data):
            cell = row.cells[col_idx]
            cell.text = cell_text
            # 设置字体大小
            for para in cell.paragraphs:
                for run in para.runs:
                    run.font.size = Pt(10)

    return nested_table


def create_nested_table_document(output_path: str):
    """创建包含嵌套表格的 Word 文档。

    文档结构模拟真实的研报首页：
    - 公司信息和日期在主表格
    - 财务数据（评级、目标价、分析师等）在嵌套表格中
    """
    doc = Document()

    # 添加标题
    title = doc.add_paragraph()
    title_run = title.add_run("西锐飞机 (2507.HK) - 首次覆盖：深度研究报告")
    title_run.bold = True
    title_run.font.size = Pt(14)

    # 添加日期段落
    date_para = doc.add_paragraph()
    date_para.add_run("21 Oct 2025")

    # 创建主表格（1行2列）
    main_table = doc.add_table(rows=1, cols=2)
    main_table.style = 'Table Grid'
    main_table.autofit = True

    # 设置列宽
    for cell in main_table.rows[0].cells:
        cell.width = Cm(8)

    # 左单元格：公司基本信息
    left_cell = main_table.rows[0].cells[0]
    left_cell.text = "公司信息\n"
    left_cell.add_paragraph("公司：西锐飞机")
    left_cell.add_paragraph("股票代码：2507.HK")
    left_cell.add_paragraph("报告日期：21 Oct 2025")
    left_cell.add_paragraph("评级：买入")

    # 在左单元格中添加另一个嵌套表格（分析师信息）
    analyst_table = left_cell.add_table(rows=3, cols=2)
    analyst_table.style = 'Table Grid'
    analyst_table.rows[0].cells[0].text = "分析师"
    analyst_table.rows[0].cells[1].text = "杨斌"
    analyst_table.rows[1].cells[0].text = "Email"
    analyst_table.rows[1].cells[1].text = "yangbin@example.com"
    analyst_table.rows[2].cells[0].text = "认证"
    analyst_table.rows[2].cells[1].text = "SFC:BSQ313"

    # 右单元格：嵌套的财务数据表格
    right_cell = main_table.rows[0].cells[1]
    right_cell.text = "财务数据"

    # 在右单元格中创建嵌套表格
    financial_data = [
        ["当前价格", "12.50"],
        ["目标价格", "15.60"],
        ["潜在涨幅", "24.8%"],
        ["市值（亿元）", "22.11bn"],
        ["52周最高", "14.50"],
        ["52周最低", "8.30"],
    ]
    nested_financial = right_cell.add_table(rows=len(financial_data), cols=2)
    nested_financial.style = 'Table Grid'
    for row_idx, (label, value) in enumerate(financial_data):
        nested_financial.rows[row_idx].cells[0].text = label
        nested_financial.rows[row_idx].cells[1].text = value

    # 添加第二个主表格（更复杂的嵌套结构）
    doc.add_paragraph()  # 空行

    section_title = doc.add_paragraph()
    section_title.add_run("投资摘要").bold = True

    # 创建包含多层嵌套的表格
    outer_table = doc.add_table(rows=2, cols=1)
    outer_table.style = 'Table Grid'

    # 外层表格的第一行：包含嵌套的详细财务数据
    detail_cell = outer_table.rows[0].cells[0]
    detail_cell.text = "详细财务数据"

    # 在 detail_cell 中创建多层嵌套
    detail_nested = detail_cell.add_table(rows=4, cols=4)
    detail_nested.style = 'Table Grid'

    # 表头
    headers = ["指标", "2023A", "2024E", "2025E"]
    for col_idx, header in enumerate(headers):
        cell = detail_nested.rows[0].cells[col_idx]
        cell.text = header
        for para in cell.paragraphs:
            for run in para.runs:
                run.bold = True

    # 数据行
    financial_rows = [
        ["营收（亿元）", "15.2", "18.5", "22.1"],
        ["净利润（亿元）", "2.1", "2.8", "3.5"],
        ["EPS（元）", "0.85", "1.12", "1.40"],
    ]
    for row_idx, row_data in enumerate(financial_rows, start=1):
        for col_idx, cell_text in enumerate(row_data):
            detail_nested.rows[row_idx].cells[col_idx].text = cell_text

    # 外层表格的第二行：包含注释和特殊字段
    note_cell = outer_table.rows[1].cells[0]
    note_cell.text = "备注"

    note_nested = note_cell.add_table(rows=2, cols=1)
    note_nested.style = 'Table Grid'
    note_nested.rows[0].cells[0].text = "注：数据来源为公司财报和估算"
    note_nested.rows[1].cells[0].text = "current_price_date: 21 Oct 2025"

    # 保存文档
    doc.save(output_path)
    print(f"已生成嵌套表格 fixture: {output_path}")


def create_simple_nested_fixture(output_path: str):
    """创建简单的嵌套表格 fixture（用于基本测试）。"""
    doc = Document()

    # 标题
    title = doc.add_paragraph()
    title.add_run("西锐飞机 (2507.HK)").bold = True
    doc.add_paragraph("21 Oct 2025")

    # 主表格
    table = doc.add_table(rows=4, cols=2)
    table.style = 'Table Grid'

    # 第一行：评级
    table.rows[0].cells[0].text = "评级"
    table.rows[0].cells[1].text = "买入"

    # 第二行：目标价
    table.rows[1].cells[0].text = "目标价"
    table.rows[1].cells[1].text = "15.60"

    # 第三行：当前价（在嵌套表格中）
    table.rows[2].cells[0].text = "当前价"
    # 在这个单元格中创建嵌套表格
    price_cell = table.rows[2].cells[1]
    price_cell.text = "包含嵌套"
    nested_price = price_cell.add_table(rows=2, cols=1)
    nested_price.rows[0].cells[0].text = "价格"
    nested_price.rows[1].cells[0].text = "12.50"

    # 第四行：市值
    table.rows[3].cells[0].text = "市值"
    table.rows[3].cells[1].text = "22.11bn"

    doc.save(output_path)
    print(f"已生成简单嵌套表格 fixture: {output_path}")


if __name__ == "__main__":
    # 获取 fixtures 目录
    fixtures_dir = Path(__file__).parent
    fixtures_dir.mkdir(exist_ok=True)

    # 生成两个 fixture
    create_nested_table_document(str(fixtures_dir / "nested_table_financial.docx"))
    create_simple_nested_fixture(str(fixtures_dir / "nested_table_simple.docx"))

    print("\n生成完成！文件位置：")
    print(f"  - {fixtures_dir / 'nested_table_financial.docx'}")
    print(f"  - {fixtures_dir / 'nested_table_simple.docx'}")
