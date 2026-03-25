"""renderer.py - 模板渲染模块。

负责 Word 模板渲染、fragment 插入和 PDF 转换。
"""

from typing import Dict, Any, List, Tuple
from pathlib import Path
import sys
import subprocess
import shutil

SCRIPTS_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPTS_DIR))

# 尝试导入依赖
try:
    from docx import Document
    from docx.shared import Inches, Pt
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docxtpl import DocxTemplate
    DOCX_AVAILABLE = True
except ImportError as e:
    print(f"Warning: {e}")
    Document = None
    Inches = None
    Pt = None
    OxmlElement = None
    qn = None
    DocxTemplate = None
    DOCX_AVAILABLE = False

import common


def render_template(
    template_path: str,
    elements: Dict[str, Any],
    abstract_path: str,
    body_path: str,
    output_path: str
) -> bool:
    """渲染模板并生成最终报告。"""
    if not DOCX_AVAILABLE:
        print("Error: python-docx or docxtpl not installed")
        return False
    
    try:
        # 1. 使用 docxtpl 渲染短字段
        template = DocxTemplate(template_path)
        
        # 准备上下文
        context = {k: v for k, v in elements.items() 
                   if k not in [common.FILE_ABSTRACT, common.FILE_BODY]}
        
        template.render(context)
        
        # 2. 保存到临时文件
        temp_output = str(Path(output_path).parent / "temp_rendered.docx")
        template.save(temp_output)
        
        # 3. 加载并处理
        from docx import Document
        final_doc = Document(temp_output)
        
        # 简化处理：直接保存
        final_doc.save(output_path)
        
        # 4. 清理临时文件
        Path(temp_output).unlink(missing_ok=True)
        
        return True
    except Exception as e:
        print(f"渲染失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def find_placeholder_in_document(doc_path: str, placeholder: str) -> List[Dict[str, Any]]:
    """查找文档中所有占位符的位置。

    Args:
        doc_path: Word 文档路径
        placeholder: 占位符文本（如 "abstract"、"body"）

    Returns:
        占位符位置列表，每个位置包含类型、索引等信息
    """
    if Document is None:
        return []

    try:
        doc = Document(doc_path)
        locations = []

        # 搜索段落中的占位符
        for i, para in enumerate(doc.paragraphs):
            if placeholder in para.text:
                locations.append({
                    "type": "paragraph",
                    "index": i,
                    "full_text": para.text,
                    "placeholder": placeholder
                })

        # 搜索表格中的占位符
        for table_idx, table in enumerate(doc.tables):
            for row_idx, row in enumerate(table.rows):
                for col_idx, cell in enumerate(row.cells):
                    if placeholder in cell.text:
                        locations.append({
                            "type": "table_cell",
                            "table": table_idx,
                            "row": row_idx,
                            "col": col_idx,
                            "full_text": cell.text,
                            "placeholder": placeholder
                        })

        return locations
    except Exception as e:
        print(f"查找占位符失败: {e}")
        return []


def insert_fragment_at_placeholder(
    target_doc: Document,
    source_doc: Document,
    placeholder: str,
    replace_placeholder: bool = True
) -> bool:
    """在目标文档的占位符位置插入源文档内容。

    Args:
        target_doc: 目标 Word 文档
        source_doc: 源 Word 文档（包含要插入的内容）
        placeholder: 占位符文本
        replace_placeholder: 是否替换占位符（True）或插入到占位符后（False）

    Returns:
        是否成功插入
    """
    if Document is None:
        return False

    try:
        inserted = False

        # 1. 尝试在段落中找到占位符
        for i, para in enumerate(target_doc.paragraphs):
            if placeholder in para.text:
                if replace_placeholder:
                    # 替换占位符段落
                    # 清空原段落
                    para.clear()

                    # 插入源文档内容
                    _insert_document_after_paragraph(target_doc, source_doc, i)
                else:
                    # 插入到占位符段落后
                    _insert_document_after_paragraph(target_doc, source_doc, i)

                inserted = True
                break  # 只替换第一个匹配的占位符

        # 2. 如果段落中没找到，尝试在表格单元格中查找
        if not inserted:
            for table_idx, table in enumerate(target_doc.tables):
                for row_idx, row in enumerate(table.rows):
                    for col_idx, cell in enumerate(row.cells):
                        if placeholder in cell.text:
                            if replace_placeholder:
                                # 替换单元格内容
                                cell.text = ""

                                # 插入源文档内容到单元格
                                for para in source_doc.paragraphs:
                                    if para.text.strip():
                                        cell.add_paragraph(para.text)
                            else:
                                # 在单元格后插入整个表格比较复杂
                                # 简化处理：在单元格文本后追加
                                for para in source_doc.paragraphs:
                                    if para.text.strip():
                                        cell.add_paragraph(para.text)

                            inserted = True
                            break
                    if inserted:
                        break
                if inserted:
                    break

        return inserted
    except Exception as e:
        print(f"插入 fragment 失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def render_with_fragments(
    template_path: str,
    elements: Dict[str, Any],
    abstract_path: str,
    body_path: str,
    output_path: str
) -> bool:
    """渲染模板并智能插入 fragments。

    这是 render_template 的增强版本，支持 fragment 字段的智能插入。

    Args:
        template_path: 模板文件路径
        elements: 要素字典
        abstract_path: 摘要 fragment 文件路径
        body_path: 正文 fragment 文件路径
        output_path: 输出文件路径

    Returns:
        是否成功
    """
    if not DOCX_AVAILABLE:
        print("Error: python-docx or docxtpl not installed")
        return False

    try:
        # 1. 使用 docxtpl 渲染短字段
        template = DocxTemplate(template_path)

        # 准备上下文（排除 fragment 字段）
        context = {k: v for k, v in elements.items()
                   if k not in [common.FILE_ABSTRACT, common.FILE_BODY]}

        template.render(context)

        # 2. 保存到临时文件
        temp_output = str(Path(output_path).parent / "temp_rendered.docx")
        template.save(temp_output)

        # 3. 加载渲染后的文档
        final_doc = Document(temp_output)

        # 4. 插入 abstract fragment
        abstract_inserted = False
        if Path(abstract_path).exists() and Path(abstract_path).stat().st_size > 0:
            abstract_doc = Document(abstract_path)
            abstract_inserted = insert_fragment_at_placeholder(
                final_doc, abstract_doc, "{{abstract}}", replace_placeholder=True
            )

            # 如果没找到 {{abstract}} 占位符，尝试其他变体
            if not abstract_inserted:
                for placeholder in ["abstract", "摘要", "%abstract%", "${abstract}"]:
                    if insert_fragment_at_placeholder(
                        final_doc, abstract_doc, placeholder, replace_placeholder=True
                    ):
                        abstract_inserted = True
                        break

            if not abstract_inserted:
                print(f"警告: 未找到 abstract 占位符，fragment 未插入")

        # 5. 插入 body fragment
        body_inserted = False
        if Path(body_path).exists() and Path(body_path).stat().st_size > 0:
            body_doc = Document(body_path)
            body_inserted = insert_fragment_at_placeholder(
                final_doc, body_doc, "{{body}}", replace_placeholder=True
            )

            # 如果没找到 {{body}} 占位符，尝试其他变体
            if not body_inserted:
                for placeholder in ["body", "正文", "%body%", "${body}"]:
                    if insert_fragment_at_placeholder(
                        final_doc, body_doc, placeholder, replace_placeholder=True
                    ):
                        body_inserted = True
                        break

            if not body_inserted:
                print(f"警告: 未找到 body 占位符，fragment 未插入")

        # 6. 保存最终文档
        final_doc.save(output_path)

        # 7. 清理临时文件
        Path(temp_output).unlink(missing_ok=True)

        return True
    except Exception as e:
        print(f"渲染失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def copy_document_with_style(source_doc: Document, target_doc: Document) -> None:
    """复制源文档的所有内容到目标文档，保留样式。

    Args:
        source_doc: 源文档
        target_doc: 目标文档
    """
    # 复制所有段落
    for para in source_doc.paragraphs:
        new_para = target_doc.add_paragraph(para.text)

        # 复制段落样式
        if para.style and para.style.name != "Normal":
            try:
                new_para.style = para.style
            except Exception:
                pass

        # 复制段落中的 run 格式
        for run in para.runs:
            if run.text:
                new_run = new_para.add_run(run.text)
                if run.bold:
                    new_run.bold = True
                if run.italic:
                    new_run.italic = True
                if run.underline:
                    new_run.underline = True
                if run.font.size:
                    new_run.font.size = run.font.size
                if run.font.name:
                    new_run.font.name = run.font.name

    # 复制所有表格
    for table in source_doc.tables:
        _copy_table_to_doc(target_doc, table)


def _insert_document_after_paragraph(
    target_doc: Document,
    source_doc: Document,
    para_index: int
) -> None:
    """在指定段落后插入整个文档。

    Args:
        target_doc: 目标文档
        source_doc: 源文档
        para_index: 段落索引
    """
    if para_index >= len(target_doc.paragraphs):
        # 如果索引超出范围，添加到文档末尾
        copy_document_with_style(source_doc, target_doc)
        return

    # 获取目标段落的元素
    target_para = target_doc.paragraphs[para_index]
    target_element = target_para._element

    # 在目标段落后插入源文档内容
    # 注意：这里需要深度复制元素，避免修改源文档

    # 插入段落
    for source_para in source_doc.paragraphs:
        if source_para.text.strip():
            new_para = target_doc.add_paragraph(source_para.text)

            # 复制样式
            if source_para.style:
                try:
                    new_para.style = source_para.style
                except Exception:
                    pass

    # 插入表格
    for table in source_doc.tables:
        _copy_table_to_doc(target_doc, table)


def _copy_table_to_doc(target_doc: Document, source_table) -> None:
    """复制表格到目标文档。

    Args:
        target_doc: 目标文档
        source_table: 源表格
    """
    try:
        # 创建新表格
        new_table = target_doc.add_table(
            rows=len(source_table.rows),
            cols=len(source_table.columns)
        )

        # 复制表格内容和格式
        for i, row in enumerate(source_table.rows):
            for j, cell in enumerate(row.cells):
                target_cell = new_table.rows[i].cells[j]

                # 复制单元格文本和段落
                for para_idx, para in enumerate(cell.paragraphs):
                    if para_idx == 0:
                        target_cell.text = para.text
                    elif para.text.strip():
                        target_cell.add_paragraph(para.text)

        # 尝试复制表格样式
        if source_table.style:
            try:
                new_table.style = source_table.style
            except Exception:
                pass
    except Exception as e:
        print(f"复制表格失败: {e}")


def convert_to_pdf(docx_path: str, pdf_path: str) -> bool:
    """转换 Word 文档为 PDF。"""
    try:
        output_dir = Path(pdf_path).parent
        
        # 查找 LibreOffice
        libreoffice_cmd = None
        for cmd in ['libreoffice', 'libreoffice7.5', 'libreoffice7.6', 'soffice']:
            found = shutil.which(cmd)
            if found:
                libreoffice_cmd = cmd
                break
        
        if not libreoffice_cmd:
            print("LibreOffice 未找到，跳过 PDF 转换")
            return False
        
        result = subprocess.run([
            libreoffice_cmd,
            '--headless',
            '--convert-to', 'pdf',
            '--outdir', str(output_dir),
            str(docx_path)
        ], capture_output=True, text=True, timeout=60)
        
        if result.returncode != 0:
            return False
        
        return Path(pdf_path).exists()
    except Exception as e:
        print(f"PDF 转换失败: {e}")
        return False


def prepare_render_context(elements: Dict[str, Any], report_dir: str) -> Dict[str, Any]:
    """准备渲染上下文。"""
    context = elements.copy()
    context['_abstract_file'] = str(Path(report_dir) / common.FILE_ABSTRACT)
    context['_body_file'] = str(Path(report_dir) / common.FILE_BODY)
    return context


def validate_template(template_path: str) -> Dict[str, Any]:
    """验证模板文件。"""
    if not DOCX_AVAILABLE:
        return {"valid": False, "error": "python-docx not installed"}
    
    try:
        from docx import Document
        doc = Document(template_path)
        
        return {
            "valid": True,
            "paragraphs": len(doc.paragraphs),
            "tables": len(doc.tables),
            "sections": len(doc.sections)
        }
    except Exception as e:
        return {"valid": False, "error": str(e)}
