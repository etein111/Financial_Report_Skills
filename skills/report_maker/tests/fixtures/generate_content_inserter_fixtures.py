#!/usr/bin/env python3
"""generate_content_inserter_fixtures.py - 生成 content_inserter 测试用的 Word 文档 fixture。

用于测试 content_inserter.py 中的：
- insert_abstract_to_cell: 在表格单元格中插入内容
- _insert_abstract_at_paragraph: 在段落中插入内容
- _apply_english_summary_margins: 应用页边距

生成的文档结构：
- doc_with_abstract_marker.docx: 包含 {{ABSTRACT}} 标记的文档
- doc_with_paragraph_marker.docx: 段落中包含 {{ABSTRACT}} 标记
- doc_with_appendix_marker.docx: 包含 APPENDIX 1 标记
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

try:
    from docx import Document
except ImportError:
    print("python-docx not installed. Run: uv pip install python-docx")
    sys.exit(1)


def create_doc_with_cell_marker(output_path: str):
    """创建带单元格 marker 的文档。"""
    doc = Document()

    # 添加标题
    doc.add_heading("研究报告", 0)

    # 添加内容段落
    doc.add_paragraph("以下是报告摘要：")

    # 创建带 marker 的表格
    table = doc.add_table(rows=2, cols=2)
    table.style = 'Table Grid'

    # 表格结构：
    # | 公司信息 | {{ABSTRACT}} |
    # | 评级 | 买入 |
    table.rows[0].cells[0].text = "公司信息"
    table.rows[0].cells[1].text = "{{ABSTRACT}}"
    table.rows[1].cells[0].text = "评级"
    table.rows[1].cells[1].text = "买入"

    doc.save(output_path)
    print(f"已生成: {output_path}")


def create_doc_with_paragraph_marker(output_path: str):
    """创建带段落 marker 的文档。"""
    doc = Document()

    # 添加标题
    doc.add_heading("研究报告", 0)

    # 添加内容段落
    doc.add_paragraph("公司：威胜控股")
    doc.add_paragraph("股票代码：3393.HK")

    # 添加带 marker 的段落
    abstract_para = doc.add_paragraph()
    abstract_para.add_run("以下是报告摘要：")
    abstract_para.add_run("{{ABSTRACT}}")

    doc.add_paragraph("评级：买入")
    doc.add_paragraph("目标价：15.60")

    doc.save(output_path)
    print(f"已生成: {output_path}")


def create_doc_with_appendix_marker(output_path: str):
    """创建带 APPENDIX 1 标记的文档（用于测试页边距）。"""
    doc = Document()

    # 添加正文
    doc.add_heading("研究报告", 0)
    doc.add_paragraph("这是报告正文内容...")

    # 添加分节符前的段落（会被设置页边距）
    doc.add_paragraph("第一节内容")
    doc.add_paragraph("第二节内容")

    # 添加 APPENDIX 1 标记（英文摘要开始）
    appendix_para = doc.add_paragraph()
    appendix_run = appendix_para.add_run("APPENDIX 1")
    appendix_run.bold = True

    # 添加英文摘要内容
    doc.add_paragraph("English Summary Content Here")
    doc.add_paragraph("更多英文摘要内容...")

    # 添加法律披露
    doc.add_paragraph("IMPORTANT DISCLOSURE")
    doc.add_paragraph("法律披露内容...")

    doc.save(output_path)
    print(f"已生成: {output_path}")


def create_abstract_content_doc(output_path: str):
    """创建包含 abstract 内容的文档。"""
    doc = Document()

    doc.add_heading("报告摘要", 1)
    doc.add_paragraph("威胜控股是国内领先的能源计量设备制造商。")
    doc.add_paragraph("公司在智能电表市场占据重要地位。")

    doc.save(output_path)
    print(f"已生成: {output_path}")


if __name__ == "__main__":
    fixtures_dir = Path(__file__).parent
    fixtures_dir.mkdir(exist_ok=True)

    # 生成 content_inserter 测试用的 fixture
    create_doc_with_cell_marker(str(fixtures_dir / "doc_with_cell_marker.docx"))
    create_doc_with_paragraph_marker(str(fixtures_dir / "doc_with_paragraph_marker.docx"))
    create_doc_with_appendix_marker(str(fixtures_dir / "doc_with_appendix_marker.docx"))
    create_abstract_content_doc(str(fixtures_dir / "abstract_content.docx"))

    print("\n生成完成！")
