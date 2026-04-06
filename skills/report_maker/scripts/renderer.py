"""renderer.py - 模板渲染模块。

负责 Word 模板渲染、fragment 插入和 PDF 转换。
"""

from typing import Dict, Any, List, Tuple, Optional
from pathlib import Path
from copy import deepcopy
import sys
import subprocess
import shutil

SCRIPTS_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPTS_DIR))

# 尝试导入依赖
try:
    from docx import Document
    from docx.shared import Inches, Pt, Cm
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docxtpl import DocxTemplate
    DOCX_AVAILABLE = True
except ImportError as e:
    print(f"Warning: {e}")
    Document = None
    Inches = None
    Pt = None
    Cm = None
    OxmlElement = None
    qn = None
    DocxTemplate = None
    DOCX_AVAILABLE = False

import common

# 占位符标记（用于避免 docxtpl 破坏文档结构）
ABSTRACT_MARKER = '###ABSTRACT_MARKER###'
BODY_MARKER = '###BODY_MARKER###'
ENGLISH_SUMMARY_MARKER = '###ENGLISH_SUMMARY_MARKER###'


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


def find_libreoffice() -> str:
    """查找 LibreOffice 可执行文件。

    支持跨平台检测：
    - Windows: 检查常见安装路径
    - Linux/Mac: 使用 which 命令查找

    Returns:
        LibreOffice 可执行文件路径，如果找不到返回 None
    """
    import platform

    system = platform.system()
    libreoffice_cmd = None

    if system == "Windows":
        # Windows 特定路径
        possible_paths = [
            r"C:\Program Files\LibreOffice\program\soffice.exe",
            r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
            r"C:\Program Files\LibreOffice 7\program\soffice.exe",
            r"C:\Program Files\LibreOffice 6\program\soffice.exe",
        ]

        for path in possible_paths:
            if Path(path).exists():
                libreoffice_cmd = path
                break

        # 如果没有找到，尝试通过 PATH 查找
        if not libreoffice_cmd:
            for cmd in ['soffice', 'libreoffice']:
                found = shutil.which(cmd)
                if found:
                    libreoffice_cmd = found
                    break
    else:
        # Linux/Mac: 使用 which 查找
        possible_commands = ['libreoffice', 'libreoffice7.5', 'libreoffice7.6', 'soffice']

        for cmd in possible_commands:
            found = shutil.which(cmd)
            if found:
                libreoffice_cmd = found
                break

    return libreoffice_cmd


def verify_pdf_output(pdf_path: str, min_size: int = 1024) -> bool:
    """验证 PDF 输出文件。

    Args:
        pdf_path: PDF 文件路径
        min_size: 最小文件大小（字节），默认 1KB

    Returns:
        是否验证通过
    """
    if not Path(pdf_path).exists():
        return False

    # 检查文件大小
    try:
        size = Path(pdf_path).stat().st_size
        if size < min_size:
            print(f"PDF 文件太小: {size} 字节")
            return False

        # 可选：验证 PDF 文件头
        with open(pdf_path, 'rb') as f:
            header = f.read(4)
            if header != b'%PDF':
                print("PDF 文件头无效")
                return False

        return True
    except Exception as e:
        print(f"PDF 验证失败: {e}")
        return False


def convert_to_pdf_with_retry(
    docx_path: str,
    pdf_path: str,
    max_retries: int = 2,
    timeout: int = 120
) -> bool:
    """带重试机制的 PDF 转换。

    Args:
        docx_path: Word 文档路径
        pdf_path: 输出 PDF 路径
        max_retries: 最大重试次数（默认 2）
        timeout: 超时时间（秒，默认 120）

    Returns:
        是否转换成功
    """
    import time

    libreoffice_cmd = find_libreoffice()

    if not libreoffice_cmd:
        print("LibreOffice 未找到，跳过 PDF 转换")
        print("提示: 请安装 LibreOffice 以启用 PDF 转换功能")
        return False

    output_dir = Path(pdf_path).parent

    # 如果 PDF 已存在，先删除
    if Path(pdf_path).exists():
        Path(pdf_path).unlink()

    for attempt in range(max_retries):
        try:
            print(f"PDF 转换尝试 {attempt + 1}/{max_retries}...")

            result = subprocess.run(
                [
                    libreoffice_cmd,
                    '--headless',
                    '--convert-to', 'pdf',
                    '--outdir', str(output_dir),
                    str(docx_path)
                ],
                capture_output=True,
                text=True,
                timeout=timeout
            )

            # 检查返回码
            if result.returncode != 0:
                print(f"LibreOffice 返回错误: {result.stderr}")
                if attempt < max_retries - 1:
                    print(f"等待 2 秒后重试...")
                    time.sleep(2)
                    continue
                else:
                    return False

            # 验证输出文件
            if not verify_pdf_output(pdf_path):
                print("PDF 输出验证失败")
                if attempt < max_retries - 1:
                    print(f"等待 2 秒后重试...")
                    time.sleep(2)
                    continue
                else:
                    return False

            print(f"PDF 转换成功: {pdf_path}")
            return True

        except subprocess.TimeoutExpired:
            print(f"PDF 转换超时（超过 {timeout} 秒）")
            if attempt < max_retries - 1:
                print(f"等待 2 秒后重试...")
                time.sleep(2)
                continue
            else:
                return False

        except Exception as e:
            print(f"PDF 转换异常: {e}")
            if attempt < max_retries - 1:
                print(f"等待 2 秒后重试...")
                time.sleep(2)
                continue
            else:
                return False

    return False


def convert_to_pdf(docx_path: str, pdf_path: str) -> bool:
    """转换 Word 文档为 PDF（简化接口）。

    Args:
        docx_path: Word 文档路径
        pdf_path: 输出 PDF 路径

    Returns:
        是否转换成功
    """
    return convert_to_pdf_with_retry(docx_path, pdf_path, max_retries=2)



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


def prepare_context_with_analysts(elements: Dict[str, Any]) -> Dict[str, Any]:
    """准备渲染上下文，展平分析师字段。

    将 a1_cn, a1_en, a1_sfc, a1_email 等展平为：
    analyst_chinese_name, analyst_english_name, analyst_sfc_code, analyst_email

    对于没有值的分析师字段（a2-a8），将占位符替换为空字符串。
    对于值为"未找到"的字段，替换为空字符串。

    Args:
        elements: 原始要素字典

    Returns:
        处理后的上下文字典
    """
    context = {}

    # 定义表示"未找到"的值（这些值应该被替换为空字符串）
    not_found_values = ['未找到', '未提供', 'N/A', 'n/a', 'NA', 'na', 'None', 'none', '无', '-']

    def clean_value(v):
        """清理值，将"未找到"等替换为空字符串"""
        if v is None:
            return ''
        if isinstance(v, str) and v.strip() in not_found_values:
            return ''
        return v

    # 跳过分析师原始字段和 fragment 字段
    skip_prefixes = ['a1_', 'a2_', 'a3_', 'a4_', 'a5_', 'a6_', 'a7_', 'a8_']
    for k, v in elements.items():
        if k in ['abstract', 'body', 'english_summary']:
            continue
        if any(k.startswith(p) for p in skip_prefixes):
            continue
        context[k] = clean_value(v)

    # 展平第一个分析师字段（用于模板渲染）
    context['analyst_chinese_name'] = clean_value(elements.get('a1_cn', ''))
    context['analyst_english_name'] = clean_value(elements.get('a1_en', ''))
    context['analyst_sfc_code'] = clean_value(elements.get('a1_sfc', ''))
    context['analyst_email'] = clean_value(elements.get('a1_email', ''))

    # 确保所有分析师字段都有值（空字符串），避免模板中的占位符未被替换
    # 分析师字段：a1_cn, a1_en, a1_sfc, a1_email ... a8_cn, a8_en, a8_sfc, a8_email
    analyst_suffixes = ['cn', 'en', 'sfc', 'email']
    for i in range(1, 9):
        for suffix in analyst_suffixes:
            field_name = f'a{i}_{suffix}'
            # 如果 elements 中没有该字段或值为 None 或"未找到"，设置为空字符串
            context[field_name] = clean_value(elements.get(field_name, ''))

    # 记录哪些分析师有数据（用于后续清理空分析师单元格）
    context['_analysts_with_data'] = set()
    for i in range(1, 9):
        cn = clean_value(elements.get(f'a{i}_cn', ''))
        en = clean_value(elements.get(f'a{i}_en', ''))
        if cn or en:  # 如果有中文名或英文名，认为该分析师有数据
            context['_analysts_with_data'].add(i)

    # 收集所有分析师（用于循环渲染，如果模板支持）
    analysts = []
    for i in range(1, 9):
        cn = clean_value(elements.get(f'a{i}_cn', ''))
        if cn:
            analysts.append({
                'chinese_name': cn,
                'english_name': clean_value(elements.get(f'a{i}_en', '')),
                'sfc_code': clean_value(elements.get(f'a{i}_sfc', '')),
                'email': clean_value(elements.get(f'a{i}_email', ''))
            })
    context['analysts'] = analysts

    return context


def insert_abstract_to_cell(doc: Document, abstract_doc: Document, marker: str) -> bool:
    """在表格单元格中插入 abstract 内容，完整保留格式。

    使用 lxml 递归搜索所有表格（包括嵌套表格）。

    Args:
        doc: 目标文档
        abstract_doc: abstract 文档
        marker: 占位符标记

    Returns:
        是否成功插入
    """
    # 使用 lxml 递归搜索所有表格单元格（包括嵌套表格）
    W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
    body = doc.element.body

    def find_marker_in_cells(parent):
        """递归搜索所有单元格中的 marker"""
        for tc in parent.iter(f'{W}tc'):
            cell_text = ''.join(t.text or '' for t in tc.iter(f'{W}t'))
            if marker in cell_text:
                return tc
        return None

    # 搜索所有表格（包括嵌套）
    tc = find_marker_in_cells(body)

    if tc is not None:
        # 删除所有段落元素
        for p in list(tc.findall(f'{W}p')):
            tc.remove(p)

        # 插入 abstract 内容（使用 deepcopy 完整保留格式）
        for src_para in abstract_doc.element.body.iter(f'{W}p'):
            para_text = ''.join(t.text or '' for t in src_para.iter(f'{W}t'))
            if para_text.strip():
                tc.append(deepcopy(src_para))

        return True

    return False


def _insert_abstract_at_paragraph(doc: Document, abstract_doc: Document, marker: str) -> bool:
    """在段落中的 marker 位置插入 abstract 内容。

    当 abstract 不在表格单元格中时使用此方法。

    Args:
        doc: 目标文档
        abstract_doc: abstract 文档
        marker: 占位符标记

    Returns:
        是否成功插入
    """
    body_elem = doc.element.body
    all_elements = list(body_elem)
    W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'

    for i, elem in enumerate(all_elements):
        if elem.tag.endswith('}p'):
            text = ''.join(t.text for t in elem.iter() if t.text)
            if marker in text:
                # 找到 marker 段落，检查其中是否有 sectPr
                # 如果有 sectPr（分节符），需要删除它避免产生多余分页
                pPr = elem.find(f'{W}pPr')
                if pPr is not None:
                    sectPr = pPr.find(f'{W}sectPr')
                    if sectPr is not None:
                        pPr.remove(sectPr)
                        print(f"  已删除 marker 段落中的 sectPr 分节符")

                # 在该位置插入 abstract 内容（倒序插入以保持顺序）
                insert_idx = i
                abstract_elements = list(abstract_doc.element.body)
                for j, abs_elem in enumerate(reversed(abstract_elements)):
                    tag = abs_elem.tag.split('}')[-1]
                    if tag in ['p', 'tbl', 'sdt']:
                        # 检查是否是空段落
                        if tag == 'p':
                            para_text = ''.join(t.text for t in abs_elem.iter() if t.text)
                            if not para_text.strip():
                                continue  # 跳过空段落
                        body_elem.insert(insert_idx, deepcopy(abs_elem))

                # 删除 marker 段落（现在段落中已经没有 sectPr 了）
                body_elem.remove(elem)

                return True

    return False


def _get_document_sectpr_margins(doc_path: str) -> Dict[str, str]:
    """读取文档的 sectPr 页边距信息。

    Args:
        doc_path: 文档路径

    Returns:
        页边距字典 {'top': '...', 'bottom': '...', 'left': '...', 'right': '...', ...}
    """
    import zipfile
    from lxml import etree

    W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
    margins = {}

    try:
        with zipfile.ZipFile(doc_path, 'r') as z:
            with z.open('word/document.xml') as f:
                tree = etree.parse(f)

        # 查找文档末尾的 sectPr
        body = tree.getroot().find(f'.//{W}body')
        if body is not None:
            sectPr = body.find(f'{W}sectPr')
            if sectPr is not None:
                pgMar = sectPr.find(f'{W}pgMar')
                if pgMar is not None:
                    for attr in ['top', 'bottom', 'left', 'right', 'header', 'footer', 'gutter']:
                        val = pgMar.get(f'{W}{attr}')
                        if val:
                            margins[attr] = val

    except Exception as e:
        print(f"  读取文档页边距失败: {e}")

    return margins


def _apply_margins_to_sectpr(docx_path: str, margins: Dict[str, str], target_sectpr_index: int = -1) -> bool:
    """将页边距应用到文档中的 sectPr。

    Args:
        docx_path: 文档路径
        margins: 页边距字典
        target_sectpr_index: 目标 sectPr 索引（-1 表示最后一个 body/sectPr，-2 表示倒数第二个段落内的 sectPr）

    Returns:
        是否成功
    """
    if not margins:
        return False

    import zipfile
    from lxml import etree

    W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'

    try:
        # 读取文档
        with zipfile.ZipFile(docx_path, 'r') as z:
            files = {name: z.read(name) for name in z.namelist()}

        if 'word/document.xml' not in files:
            return False

        doc_tree = etree.fromstring(files['word/document.xml'])
        body = doc_tree.find(f'{W}body')
        if body is None:
            return False

        # 收集所有 sectPr（包括段落内的和 body 末尾的）
        all_sectPrs = []

        # 段落内的 sectPr（连续分节符）
        for p in body.findall(f'.//{W}p'):
            pPr = p.find(f'{W}pPr')
            if pPr is not None:
                sectPr = pPr.find(f'{W}sectPr')
                if sectPr is not None:
                    all_sectPrs.append(('pPr', sectPr))

        # body 末尾的 sectPr
        body_sectPr = body.find(f'{W}sectPr')
        if body_sectPr is not None:
            all_sectPrs.append(('body', body_sectPr))

        if not all_sectPrs:
            return False

        # 选择目标 sectPr
        if target_sectpr_index < 0:
            target_sectpr_index = len(all_sectPrs) + target_sectpr_index

        if target_sectpr_index < 0 or target_sectpr_index >= len(all_sectPrs):
            return False

        _, target_sectPr = all_sectPrs[target_sectpr_index]

        # 应用页边距
        pgMar = target_sectPr.find(f'{W}pgMar')
        if pgMar is None:
            pgMar = etree.SubElement(target_sectPr, f'{W}pgMar')

        for attr, val in margins.items():
            pgMar.set(f'{W}{attr}', val)

        # 保存
        files['word/document.xml'] = etree.tostring(
            doc_tree, xml_declaration=True, encoding='UTF-8', standalone=True
        )

        import os
        os.remove(docx_path)
        with zipfile.ZipFile(docx_path, 'w', zipfile.ZIP_DEFLATED) as z:
            for name, content in files.items():
                z.writestr(name, content)

        return True

    except Exception as e:
        print(f"  应用页边距失败: {e}")
        return False


def insert_body_at_marker_compose(doc_path: str, body_path: str, marker: str, output_path: str) -> bool:
    """使用 docxcompose 三段式合并：在 marker 位置插入 body。

    将原文档拆分为 marker 之前和之后两部分，
    然后用 docxcompose 合并：part1 + body + sectPr + part3。
    这样可以正确处理所有图片和资源引用。

    Args:
        doc_path: 渲染后的模板路径
        body_path: body 文档路径
        marker: 占位符标记
        output_path: 输出路径

    Returns:
        是否成功插入
    """
    try:
        from docxcompose.composer import Composer
        import shutil
        from copy import deepcopy
        from lxml import etree

        W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'

        # 0. 保存 body.docx 的页边距信息（合并后需要恢复）
        body_margins = _get_document_sectpr_margins(body_path)
        if body_margins:
            print(f"  body.docx 页边距: top={body_margins.get('top')}, bottom={body_margins.get('bottom')}")

        # 1. 找到 marker 位置和其中的 sectPr
        doc = Document(doc_path)
        body_elem = doc.element.body
        all_elements = list(body_elem)

        marker_idx = None
        marker_sectPr = None  # 保留 marker 段落中的 sectPr（分节符）
        for i, elem in enumerate(all_elements):
            text = ''.join(t.text or '' for t in elem.iter() if t.text)
            if marker in text:
                marker_idx = i
                # 检查 marker 段落中是否有 sectPr（分节符）
                if elem.tag.endswith('}p'):
                    pPr = elem.find(f'{W}pPr')
                    if pPr is not None:
                        sectPr = pPr.find(f'{W}sectPr')
                        if sectPr is not None:
                            # 提取 sectPr（深拷贝避免被删除）
                            marker_sectPr = deepcopy(sectPr)
                            print(f"  保留 marker 段落中的 sectPr 分节符")
                break

        if marker_idx is None:
            return False

        # 2. 创建 part1（marker 之前的内容）
        part1_path = Path(output_path).parent / "temp_part1.docx"
        shutil.copy(doc_path, str(part1_path))

        part1_doc = Document(str(part1_path))
        part1_body = part1_doc.element.body
        part1_elements = list(part1_body)

        # 删除 marker 及之后的所有元素
        for elem in part1_elements[marker_idx:]:
            tag = elem.tag.split('}')[-1]
            if tag != 'sectPr':  # 保留 sectPr（页面设置）
                part1_body.remove(elem)

        part1_doc.save(str(part1_path))

        # 3. 创建 part3（marker 之后的内容）
        part3_path = Path(output_path).parent / "temp_part3.docx"
        shutil.copy(doc_path, str(part3_path))

        part3_doc = Document(str(part3_path))
        part3_body = part3_doc.element.body
        part3_elements = list(part3_body)

        # 删除 marker 及之前的所有元素
        has_part3_content = False
        for elem in part3_elements[:marker_idx + 1]:
            tag = elem.tag.split('}')[-1]
            if tag != 'sectPr':
                part3_body.remove(elem)

        # 检查 part3 是否有实际内容
        for elem in part3_body:
            tag = elem.tag.split('}')[-1]
            if tag in ['p', 'tbl', 'sdt']:
                text = ''.join(t.text or '' for t in elem.iter() if t.text)
                if text.strip():
                    has_part3_content = True
                    break

        if has_part3_content:
            part3_doc.save(str(part3_path))

        # 4. 使用 docxcompose 合并：part1 + body + sectPr(分页符) + part3
        master = Document(str(part1_path))
        composer = Composer(master)

        # 追加 body
        body_doc = Document(body_path)

        # 如果有 marker_sectPr，在 body 末尾添加一个带有 sectPr 的段落
        # 这样 body 和 part3（APPENDIX 1 Summary）之间就有分页符了
        if marker_sectPr is not None and has_part3_content:
            # 创建分页段落
            page_break_para = body_doc.element.body.makeelement(
                f'{W}p',
                {}
            )
            pPr = etree.SubElement(page_break_para, f'{W}pPr')
            pPr.append(deepcopy(marker_sectPr))
            body_doc.element.body.append(page_break_para)
            print(f"  在 body 末尾添加分页符段落")

        composer.append(body_doc)

        # 追加 part3（如果有内容）
        if has_part3_content:
            part3_for_merge = Document(str(part3_path))
            composer.append(part3_for_merge)

        # 保存最终文档
        composer.save(output_path)

        # 5. 恢复 body 的页边距（修复 docxcompose 覆盖页边距的问题）
        if body_margins:
            # docxcompose 会在 part1 和 body 之间插入一个 sectPr（分节符）
            # 这个 sectPr 应该使用 body 的页边距
            # 找到并修复这个 sectPr
            _fix_docxcompose_sectpr_margins(output_path, body_margins, has_part3_content)

        # 6. 清理临时文件
        part1_path.unlink(missing_ok=True)
        if has_part3_content:
            part3_path.unlink(missing_ok=True)

        return True

    except Exception as e:
        print(f"  docxcompose 三段式合并失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def _fix_docxcompose_sectpr_margins(docx_path: str, body_margins: Dict[str, str], has_part3: bool) -> int:
    """修复 docxcompose 合并时插入的 sectPr 页边距。

    docxcompose 在 append() 时会在合并点插入分节符（pPr/sectPr），
    这些分节符通常使用默认页边距（1英寸 = 1440 twips）。

    本函数将这些分节符的页边距修改为 body.docx 的原始页边距。

    Args:
        docx_path: docx 文件路径
        body_margins: body.docx 的页边距
        has_part3: 是否有 part3（附录）

    Returns:
        修复的 sectPr 数量
    """
    import zipfile
    from lxml import etree

    W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
    fixed_count = 0

    try:
        # 读取文档
        with zipfile.ZipFile(docx_path, 'r') as z:
            files = {name: z.read(name) for name in z.namelist()}

        if 'word/document.xml' not in files:
            return 0

        doc_tree = etree.fromstring(files['word/document.xml'])
        body = doc_tree.find(f'{W}body')
        if body is None:
            return 0

        # 收集所有段落内的 sectPr（docxcompose 插入的分节符）
        ppr_sectprs = []
        for p in body.findall(f'.//{W}p'):
            pPr = p.find(f'{W}pPr')
            if pPr is not None:
                sectPr = pPr.find(f'{W}sectPr')
                if sectPr is not None:
                    ppr_sectprs.append(sectPr)

        # 修复这些 sectPr 的页边距
        # 第一个 sectPr（part1 和 body 之间）：应用 body 的页边距
        # 因为这个 sectPr 定义的是它之前内容（part1/首页）的格式
        # 所以我们可能不应该修改它...
        #
        # 实际上，Word 的 sectPr 定义的是它之前内容的格式：
        # - 段落内的 sectPr（连续分节符）定义它之前段落的格式
        # - body 末尾的 sectPr 定义整个文档最后一节的格式
        #
        # docxcompose 在合并时：
        # 1. 在 part1 末尾插入一个 sectPr（定义 part1 的格式）
        # 2. 追加 body 的内容
        # 3. 在 body 末尾插入一个 sectPr（定义 body 的格式）
        # 4. 追加 part3 的内容
        #
        # 问题是：docxcompose 插入的 sectPr 使用默认页边距，而不是 body 的页边距
        #
        # 解决方案：
        # - 第一个 pPr/sectPr（part1 末尾）：保持原样（定义首页格式）
        # - 第二个 pPr/sectPr（body 末尾）：使用 body 的页边距
        # - body/sectPr（文档末尾）：保持原样（定义附录格式）

        if len(ppr_sectprs) >= 1 and body_margins:
            # 修复第一个 sectPr（如果它使用默认页边距）
            # 这个 sectPr 定义的是它之前内容（首页模板）的格式，不应该修改
            pass

        if len(ppr_sectprs) >= 2 and body_margins:
            # 修复第二个 sectPr（body 末尾）
            # 这个 sectPr 定义的是 body 的格式，应该使用 body 的页边距
            sectPr = ppr_sectprs[1]
            pgMar = sectPr.find(f'{W}pgMar')
            if pgMar is not None:
                # 比较当前 pgMar 和 body_margins，如果不同则替换
                needs_fix = False
                for attr, val in body_margins.items():
                    current_val = pgMar.get(f'{W}{attr}', '')
                    if current_val != val:
                        needs_fix = True
                        break

                if needs_fix:
                    for attr, val in body_margins.items():
                        pgMar.set(f'{W}{attr}', val)
                    fixed_count += 1
                    print(f"  已修复 body 分节符页边距: top={body_margins.get('top')}, bottom={body_margins.get('bottom')}, left={body_margins.get('left')}, right={body_margins.get('right')}")

        # 如果只有一个 pPr/sectPr，它就是 body 的分节符
        if len(ppr_sectprs) == 1 and body_margins:
            sectPr = ppr_sectprs[0]
            pgMar = sectPr.find(f'{W}pgMar')
            if pgMar is not None:
                # 比较当前 pgMar 和 body_margins，如果不同则替换
                needs_fix = False
                for attr, val in body_margins.items():
                    current_val = pgMar.get(f'{W}{attr}', '')
                    if current_val != val:
                        needs_fix = True
                        break

                if needs_fix:
                    for attr, val in body_margins.items():
                        pgMar.set(f'{W}{attr}', val)
                    fixed_count += 1
                    print(f"  已修复 body 分节符页边距: top={body_margins.get('top')}, bottom={body_margins.get('bottom')}, left={body_margins.get('left')}, right={body_margins.get('right')}")

        if fixed_count > 0:
            # 保存修改后的文档
            files['word/document.xml'] = etree.tostring(
                doc_tree, xml_declaration=True, encoding='UTF-8', standalone=True
            )

            import os
            os.remove(docx_path)
            with zipfile.ZipFile(docx_path, 'w', zipfile.ZIP_DEFLATED) as z:
                for name, content in files.items():
                    z.writestr(name, content)

    except Exception as e:
        print(f"  修复 docxcompose sectPr 页边距时出错: {e}")

    return fixed_count


def _apply_english_summary_margins(docx_path: str, es_margins: Dict[str, str]) -> bool:
    """在 english_summary 内容末尾（法律附录之前）插入分节符，应用 english_summary 的页边距。

    english_summary 和 body 使用不同的页边距。
    为了让 english_summary 有正确的页边距，我们需要在其内容末尾
    （在法律附录 "附录APPENDIX" 之前）插入一个分节符。

    Word 的 sectPr 定义的是它之前内容的格式。
    所以我们在法律附录之前插入 sectPr，定义 english_summary 的格式。

    Args:
        docx_path: 文档路径
        es_margins: english_summary.docx 的页边距

    Returns:
        是否成功
    """
    import zipfile
    from lxml import etree

    W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'

    try:
        # 读取文档
        with zipfile.ZipFile(docx_path, 'r') as z:
            files = {name: z.read(name) for name in z.namelist()}

        if 'word/document.xml' not in files:
            return False

        doc_tree = etree.fromstring(files['word/document.xml'])
        body = doc_tree.find(f'{W}body')
        if body is None:
            return False

        # 找到法律附录的开始位置
        # 标记：包含 "附录APPENDIX" 的元素（可能是段落或表格）
        # 注意：不要匹配 "APPENDIX 1"（这是 english_summary 的一部分）
        appendix_idx = None

        all_elements = list(body)
        for idx, elem in enumerate(all_elements):
            # 获取元素中的所有文本
            text = ''.join(t.text or '' for t in elem.iter(f'{W}t'))

            # 只匹配 "附录APPENDIX"，不匹配 "APPENDIX 1"
            if '附录APPENDIX' in text:
                appendix_idx = idx
                print(f"  找到法律附录 '附录APPENDIX' 在 body 子元素 {idx}")
                break
            # 也检查 "重要信息披露" 或 "IMPORTANT DISCLOSURES"
            if '重要信息披露' in text or 'IMPORTANT DISCLOSURES' in text.upper():
                appendix_idx = idx
                print(f"  找到法律附录 '重要信息披露' 在 body 子元素 {idx}")
                break

        if appendix_idx is None or appendix_idx == 0:
            print(f"  english_summary: 未找到法律附录位置，无法插入分节符")
            return False

        # 在法律附录之前找到最后一个段落
        prev_para = None
        prev_para_idx = None
        for i in range(appendix_idx - 1, -1, -1):
            elem = all_elements[i]
            if elem.tag == f'{W}p':
                # 跳过空段落
                text = ''.join(t.text or '' for t in elem.iter(f'{W}t')).strip()
                if text:
                    prev_para = elem
                    prev_para_idx = i
                    print(f"  在 body 子元素 {i} 添加 sectPr: {text[:50]}")
                    break

        if prev_para is None:
            # 如果没有找到非空段落，使用最后一个段落
            for i in range(appendix_idx - 1, -1, -1):
                elem = all_elements[i]
                if elem.tag == f'{W}p':
                    prev_para = elem
                    prev_para_idx = i
                    print(f"  在空段落 body 子元素 {i} 添加 sectPr")
                    break

        if prev_para is None:
            print(f"  english_summary: 法律附录前没有段落，无法插入分节符")
            return False

        # 检查这个段落是否已经有 sectPr
        pPr = prev_para.find(f'{W}pPr')
        if pPr is None:
            pPr = etree.SubElement(prev_para, f'{W}pPr')
            # 将 pPr 移到段落开头
            prev_para.insert(0, pPr)

        existing_sectPr = pPr.find(f'{W}sectPr')
        if existing_sectPr is not None:
            # 已有 sectPr，更新其页边距
            pgMar = existing_sectPr.find(f'{W}pgMar')
            if pgMar is None:
                pgMar = etree.SubElement(existing_sectPr, f'{W}pgMar')
            for attr, val in es_margins.items():
                pgMar.set(f'{W}{attr}', val)
            print(f"  english_summary: 已更新分节符页边距: top={es_margins.get('top')}, bottom={es_margins.get('bottom')}, left={es_margins.get('left')}")
        else:
            # 创建新的 sectPr（连续分节符）
            sectPr = etree.SubElement(pPr, f'{W}sectPr')

            # 设置分节类型为连续（continuous）
            sectType = etree.SubElement(sectPr, f'{W}type')
            sectType.set(f'{W}val', 'continuous')

            # 设置页边距
            pgMar = etree.SubElement(sectPr, f'{W}pgMar')
            for attr, val in es_margins.items():
                pgMar.set(f'{W}{attr}', val)

            # 从文档末尾的 sectPr 复制页面大小设置
            body_sectPr = body.find(f'{W}sectPr')
            if body_sectPr is not None:
                pgSz = body_sectPr.find(f'{W}pgSz')
                if pgSz is not None:
                    new_pgSz = etree.SubElement(sectPr, f'{W}pgSz')
                    for attr in pgSz.attrib:
                        new_pgSz.set(attr, pgSz.get(attr))

            print(f"  english_summary: 已在法律附录前插入分节符，页边距: top={es_margins.get('top')}, bottom={es_margins.get('bottom')}, left={es_margins.get('left')}")

        # 保存
        files['word/document.xml'] = etree.tostring(
            doc_tree, xml_declaration=True, encoding='UTF-8', standalone=True
        )

        import os
        os.remove(docx_path)
        with zipfile.ZipFile(docx_path, 'w', zipfile.ZIP_DEFLATED) as z:
            for name, content in files.items():
                z.writestr(name, content)

        return True

    except Exception as e:
        print(f"  应用 english_summary 页边距失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def insert_body_at_marker(doc: Document, body_doc: Document, marker: str) -> bool:
    """在标记位置插入 body 内容，保留完整格式（包括图片、表格、目录）。

    使用 deepcopy 复制 XML 元素。图片保持原有引用（依赖后续的资源复制）。

    Args:
        doc: 目标文档
        body_doc: body 文档
        marker: 占位符标记

    Returns:
        是否成功插入
    """
    body_element = doc.element.body

    for i, elem in enumerate(body_element):
        if elem.tag.endswith('}p'):
            # 获取段落文本
            text = ''.join(t.text for t in elem.iter() if t.text)
            if marker in text:
                # 在此位置插入 body 内容
                insert_idx = i

                # 从 body_doc 复制所有元素（使用 deepcopy 保留格式）
                # 包括段落(p)、表格(tbl)、目录控件(sdt)等
                for body_elem in body_doc.element.body:
                    tag = body_elem.tag.split('}')[-1]
                    # 复制段落、表格和目录控件，跳过 section 属性
                    if tag in ['p', 'tbl', 'sdt']:
                        new_elem = deepcopy(body_elem)
                        body_element.insert(insert_idx, new_elem)
                        insert_idx += 1

                # 删除原占位符段落
                body_element.remove(elem)
                return True

    return False


def _fix_split_placeholders_in_docx(docx_path: str, output_path: str = None) -> str:
    """修复 Word 文档中被拆分的 Jinja2 占位符。

    Word 在保存时会将 {{ a1_email }} 拆分成多个 <w:t> 元素，
    如 {{ a1_ + email + }}，导致 docxtpl 无法识别。

    此函数在 XML 级别合并这些被拆分的占位符。

    Args:
        docx_path: 输入 docx 文件路径
        output_path: 输出 docx 文件路径（默认覆盖原文件）

    Returns:
        修复后的文件路径
    """
    import zipfile
    import re
    import os
    from lxml import etree

    if output_path is None:
        output_path = docx_path

    W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'

    try:
        # 读取 docx
        docx_dir = os.path.dirname(docx_path)
        temp_dir = os.path.join(docx_dir, '_temp_fix_placeholders')

        with zipfile.ZipFile(docx_path, 'r') as z:
            z.extractall(temp_dir)

        # 读取 document.xml
        doc_xml_path = os.path.join(temp_dir, 'word', 'document.xml')
        tree = etree.parse(doc_xml_path)
        root = tree.getroot()

        # 检测是否有 Jinja2 占位符模式的正则
        jinja_pattern = re.compile(r'(\{\{[^}]*\}\}|\{%[^%]*%\})')

        def fix_runs_in_parent(parent):
            """修复一个父元素中的 run，合并被拆分的占位符"""
            # 查找所有直接子 run（不递归查找孙元素）
            runs = []
            for child in parent:
                if isinstance(child, etree._Element) and child.tag == f'{W}r':
                    runs.append(child)

            if not runs:
                return

            # 收集所有 run 的文本
            run_texts = []
            for r in runs:
                t_elem = r.find(f'{W}t')
                text = t_elem.text if t_elem is not None and t_elem.text else ''
                run_texts.append((r, t_elem, text))

            # 合并所有文本来检测占位符
            full_text = ''.join([rt[2] for rt in run_texts])

            if not jinja_pattern.search(full_text):
                return  # 没有 Jinja2 语法

            # 重建文本：将所有文本合并到第一个 run 中
            if run_texts:
                first_run, first_t, _ = run_texts[0]

                if first_t is None:
                    first_t = etree.SubElement(first_run, f'{W}t')

                first_t.text = full_text
                first_t.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')

                # 清空其他 run 的文本
                for r, t, _ in run_texts[1:]:
                    if t is not None:
                        t.text = ''

        def fix_element(elem):
            """递归处理元素及其子元素"""
            # 处理段落
            if elem.tag == f'{W}p':
                fix_runs_in_parent(elem)
            elif elem.tag == f'{W}tc':
                # 处理单元格内的段落
                for child in elem:
                    if child.tag == f'{W}p':
                        fix_runs_in_parent(child)
                    elif child.tag == f'{W}tbl':
                        # 处理嵌套表格
                        fix_element(child)
                # 也处理直接子段落（有些结构可能不同）
                for p in elem.findall(f'{W}p'):
                    fix_runs_in_parent(p)
            elif elem.tag == f'{W}tbl':
                # 处理表格行
                for tr in elem.findall(f'{W}tr'):
                    for tc in tr.findall(f'{W}tc'):
                        fix_element(tc)

            # 递归处理所有子元素
            for child in list(elem):
                fix_element(child)

        # 从 body 开始处理
        body = root.find(f'{W}body')
        if body is not None:
            fix_element(body)

        # 写回 document.xml
        tree.write(doc_xml_path, xml_declaration=True, encoding='UTF-8', standalone=True)

        # 重新打包
        if os.path.exists(output_path) and output_path != docx_path:
            os.remove(output_path)
        elif output_path == docx_path:
            os.remove(docx_path)

        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as z:
            for root_dir, dirs, files in os.walk(temp_dir):
                for file in files:
                    file_path = os.path.join(root_dir, file)
                    arcname = os.path.relpath(file_path, temp_dir)
                    z.write(file_path, arcname)

        # 清理临时目录
        import shutil
        shutil.rmtree(temp_dir)

        return output_path

    except Exception as e:
        print(f"  修复占位符时出错: {e}")
        import traceback
        traceback.print_exc()
        # 如果出错，复制原文件
        if output_path != docx_path:
            import shutil
            shutil.copy2(docx_path, output_path)
        return output_path


def replace_analyst_placeholders_in_xml(docx_path: str, elements: Dict[str, Any]) -> str:
    """在 XML 级别替换嵌套表格中的分析师占位符。

    docxtpl 不能正确处理嵌套表格，会导致嵌套表格结构丢失。
    这个函数在 docxtpl 渲染后直接操作 XML，正确替换占位符。

    Args:
        docx_path: docx 文件路径
        elements: 包含分析师数据的字典

    Returns:
        修改后的文件路径（可能与输入相同）
    """
    import zipfile
    import re
    import os

    # 准备替换映射
    # 格式: {{ a1_cn }} -> "杨斌"
    replacements = {}
    analyst_suffixes = ['cn', 'en', 'sfc', 'email']

    for i in range(1, 9):
        for suffix in analyst_suffixes:
            key = f'a{i}_{suffix}'
            value = elements.get(key, '') or ''
            placeholder = f'{{{{ {key} }}}}'
            replacements[placeholder] = value

    # 也处理没有花括号的格式（docxtpl 可能简化了）
    for i in range(1, 9):
        for suffix in analyst_suffixes:
            key = f'a{i}_{suffix}'
            value = elements.get(key, '') or ''
            placeholder = f'{{{{{key}}}}}'
            replacements[placeholder] = value

    # 读取 docx（zip 格式）
    docx_dir = os.path.dirname(docx_path)
    docx_name = os.path.basename(docx_path)
    temp_dir = os.path.join(docx_dir, '_temp_docx')

    try:
        # 解压
        with zipfile.ZipFile(docx_path, 'r') as z:
            z.extractall(temp_dir)

        # 读取 document.xml
        doc_xml_path = os.path.join(temp_dir, 'word', 'document.xml')
        with open(doc_xml_path, 'r', encoding='utf-8') as f:
            xml_content = f.read()

        # 执行替换
        for placeholder, value in replacements.items():
            if placeholder in xml_content:
                xml_content = xml_content.replace(placeholder, str(value))

        # 写回 document.xml
        with open(doc_xml_path, 'w', encoding='utf-8') as f:
            f.write(xml_content)

        # 重新打包为 docx
        # 删除原文件
        os.remove(docx_path)

        # 创建新的 docx（zip）
        with zipfile.ZipFile(docx_path, 'w', zipfile.ZIP_DEFLATED) as z:
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, temp_dir)
                    z.write(file_path, arcname)

    finally:
        # 清理临时目录
        import shutil
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

    return docx_path


def replace_all_placeholders_in_xml(
    docx_path: str,
    context: Dict[str, Any],
    elements: Dict[str, Any]
) -> str:
    """通过 XML 级别替换所有占位符。

    docxtpl 会破坏嵌套表格结构，所以使用直接的 XML 替换来代替。
    这确保嵌套表格（分析师表格）不会被破坏。

    Args:
        docx_path: docx 文件路径
        context: 渲染上下文（来自 prepare_context_with_analysts）
        elements: 原始要素字典

    Returns:
        修改后的文件路径
    """
    import zipfile
    import os

    # 收集所有要替换的占位符
    replacements = {}

    # 1. 添加分析师占位符（a1_cn, a1_en, a1_sfc, a1_email, ... a8_cn, ...）
    analyst_suffixes = ['cn', 'en', 'sfc', 'email']
    for i in range(1, 9):
        for suffix in analyst_suffixes:
            key = f'a{i}_{suffix}'
            value = context.get(key, '') or ''
            # 替换格式 {{ a1_cn }} 和 {{a1_cn}}
            replacements[f'{{{{ {key} }}}}'] = value
            replacements[f'{{{{{key}}}}}'] = value

    # 2. 添加所有普通字段占位符（从 context 中获取）
    # 跳过特殊字段和分析师字段（已在上面处理）
    skip_fields = {'abstract', 'body', 'analysts', '_analysts_with_data', '_abstract_file', '_body_file'}
    analyst_prefixes = tuple(f'a{i}_' for i in range(1, 9))

    for field, value in context.items():
        # 跳过特殊字段
        if field in skip_fields:
            continue
        # 跳过分析师字段（已在上面处理）
        if field.startswith(analyst_prefixes):
            continue
        # 跳过内部字段（以 _ 开头）
        if field.startswith('_'):
            continue

        # 替换格式 {{ field }} 和 {{field}}
        str_value = str(value) if value else ''
        replacements[f'{{{{ {field} }}}}'] = str_value
        replacements[f'{{{{{field}}}}}'] = str_value

    # 3. 添加抽象占位符 {{ abstract }} 和 {{ body }}
    # 替换为标记，以便后续插入 abstract 和 body 内容
    replacements['{{ abstract }}'] = ABSTRACT_MARKER
    replacements['{{abstract}}'] = ABSTRACT_MARKER
    replacements['{{ body }}'] = BODY_MARKER
    replacements['{{body}}'] = BODY_MARKER

    # 读取并修改 docx
    docx_dir = os.path.dirname(docx_path)
    temp_dir = os.path.join(docx_dir, '_temp_docx_replace')

    try:
        # 解压
        with zipfile.ZipFile(docx_path, 'r') as z:
            z.extractall(temp_dir)

        # 读取 document.xml
        doc_xml_path = os.path.join(temp_dir, 'word', 'document.xml')
        with open(doc_xml_path, 'r', encoding='utf-8') as f:
            xml_content = f.read()

        # 执行替换（按长度降序排列，避免部分匹配问题）
        sorted_placeholders = sorted(replacements.keys(), key=len, reverse=True)
        for placeholder in sorted_placeholders:
            value = replacements[placeholder]
            if placeholder in xml_content:
                xml_content = xml_content.replace(placeholder, value)

        # 写回 document.xml
        with open(doc_xml_path, 'w', encoding='utf-8') as f:
            f.write(xml_content)

        # 重新打包为 docx
        os.remove(docx_path)
        with zipfile.ZipFile(docx_path, 'w', zipfile.ZIP_DEFLATED) as z:
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, temp_dir)
                    z.write(file_path, arcname)

    finally:
        import shutil
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

    return docx_path


def _escape_jinja_in_charts(docx_path: str) -> Dict[str, str]:
    """转义图表 XML 中的 Jinja2 语法，防止 docxtpl 解析错误。

    Word 图表的数据存储在 word/charts/*.xml 文件中，
    如果图表数据包含 {{ }} 语法，Jinja2 会尝试解析导致错误。

    Args:
        docx_path: docx 文件路径

    Returns:
        被转义的文件内容字典 {文件名: 原始内容}，用于后续恢复
    """
    import zipfile
    import os
    import re

    escaped_files = {}

    try:
        docx_dir = os.path.dirname(docx_path)
        temp_dir = os.path.join(docx_dir, '_temp_escape_charts')

        with zipfile.ZipFile(docx_path, 'r') as z:
            z.extractall(temp_dir)

        # 查找并转义 charts 目录下的所有 XML 文件
        charts_dir = os.path.join(temp_dir, 'word', 'charts')
        if os.path.exists(charts_dir):
            for filename in os.listdir(charts_dir):
                if filename.endswith('.xml'):
                    filepath = os.path.join(charts_dir, filename)
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # 检查是否包含 Jinja2 语法
                    if '{{' in content or '{%' in content:
                        # 保存原始内容
                        escaped_files[f'word/charts/{filename}'] = content

                        # 转义 {{ 和 {% 为 HTML 实体风格
                        escaped_content = content.replace('{{', '&#123;&#123;')
                        escaped_content = escaped_content.replace('}}', '&#125;&#125;')
                        escaped_content = escaped_content.replace('{%', '&#123;%')
                        escaped_content = escaped_content.replace('%}', '%&#125;')

                        with open(filepath, 'w', encoding='utf-8') as f:
                            f.write(escaped_content)

        # 重新打包
        os.remove(docx_path)
        with zipfile.ZipFile(docx_path, 'w', zipfile.ZIP_DEFLATED) as z:
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, temp_dir)
                    z.write(file_path, arcname)

        # 清理临时目录
        import shutil
        shutil.rmtree(temp_dir)

    except Exception as e:
        print(f"  转义图表 Jinja2 语法时出错: {e}")

    return escaped_files


def _restore_jinja_in_charts(docx_path: str, escaped_files: Dict[str, str]) -> None:
    """恢复图表 XML 中被转义的 Jinja2 语法。

    Args:
        docx_path: docx 文件路径
        escaped_files: 被转义的文件内容字典 {文件名: 原始内容}
    """
    import zipfile
    import os

    if not escaped_files:
        return

    try:
        docx_dir = os.path.dirname(docx_path)
        temp_dir = os.path.join(docx_dir, '_temp_restore_charts')

        with zipfile.ZipFile(docx_path, 'r') as z:
            z.extractall(temp_dir)

        # 恢复原始内容
        for arcname, original_content in escaped_files.items():
            filepath = os.path.join(temp_dir, arcname)
            if os.path.exists(filepath):
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(original_content)

        # 重新打包
        os.remove(docx_path)
        with zipfile.ZipFile(docx_path, 'w', zipfile.ZIP_DEFLATED) as z:
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, temp_dir)
                    z.write(file_path, arcname)

        # 清理临时目录
        import shutil
        shutil.rmtree(temp_dir)

    except Exception as e:
        print(f"  恢复图表 Jinja2 语法时出错: {e}")


def render_report(
    template_path: str,
    elements: Dict[str, Any],
    abstract_path: str,
    body_path: str,
    output_path: str,
    english_summary_path: str = None
) -> bool:
    """渲染报告，正确处理分析师字段、abstract、body 和 english_summary。

    法律附录识别规则：
    - 前面有分页符（单独一页）
    - 开头必定是："附录APPENDIX"
    - 结尾是整个文档的结尾

    Args:
        template_path: 模板文件路径
        elements: 要素字典
        abstract_path: 摘要文件路径
        body_path: 正文文件路径
        output_path: 输出文件路径
        english_summary_path: 英文摘要文件路径（可选）

    Returns:
        是否成功
    """
    if not DOCX_AVAILABLE:
        print("Error: python-docx or docxtpl not installed")
        return False

    try:
        from docxcompose.composer import Composer

        # 1. 准备渲染上下文
        context = prepare_context_with_analysts(elements)

        # 2. 添加 abstract、body 和 english_summary 的 MARKER 到上下文
        # docxtpl 会将 {{ abstract }}、{{ body }}、{{ english_summary }} 替换为 MARKER
        # 后续再在 MARKER 位置插入实际内容
        context['abstract'] = ABSTRACT_MARKER
        context['body'] = BODY_MARKER
        context['english_summary'] = ENGLISH_SUMMARY_MARKER

        # 3. 修复模板中被拆分的占位符（Word 会把 {{ a1_email }} 拆成多个 run）
        temp_path = Path(output_path).parent / "temp_rendered.docx"
        fixed_template_path = Path(output_path).parent / "temp_fixed_template.docx"
        _fix_split_placeholders_in_docx(template_path, str(fixed_template_path))

        # 3.1 转义图表 XML 中的 Jinja2 语法（防止 docxtpl 解析错误）
        escaped_chart_files = _escape_jinja_in_charts(str(fixed_template_path))
        if escaped_chart_files:
            print(f"  已转义 {len(escaped_chart_files)} 个图表文件中的 Jinja2 语法")

        # 3.5 扩展分析师认证声明（为多个分析师复制声明段落）
        expanded_analysts = expand_analyst_certification(str(fixed_template_path), elements)
        if expanded_analysts > 0:
            print(f"  已扩展分析师认证声明（新增 {expanded_analysts} 个分析师）")

        # 4. 使用 docxtpl 渲染修复后的模板（支持 {% if %} 语法）
        template = DocxTemplate(str(fixed_template_path))
        template.render(context)
        template.save(str(temp_path))

        # 清理修复后的临时模板
        fixed_template_path.unlink(missing_ok=True)

        # 5. 处理 ABSTRACT_MARKER - 在表格单元格中插入 abstract 内容
        doc = Document(str(temp_path))

        if Path(abstract_path).exists() and Path(abstract_path).stat().st_size > 0:
            abstract_doc = Document(abstract_path)
            abstract_inserted = insert_abstract_to_cell(doc, abstract_doc, ABSTRACT_MARKER)
            if abstract_inserted:
                print(f"  已在 ABSTRACT_MARKER 位置插入 abstract")
            else:
                # 如果没有在表格中找到，尝试在段落中查找并替换
                abstract_inserted = _insert_abstract_at_paragraph(doc, abstract_doc, ABSTRACT_MARKER)
                if abstract_inserted:
                    print(f"  已在段落中插入 abstract")
                else:
                    print(f"  ⚠️ 未找到 ABSTRACT_MARKER，abstract 未插入")

        # 保存处理 abstract 后的文档
        doc.save(str(temp_path))

        # 6. 处理 BODY_MARKER - 使用 docxcompose 三段式合并
        if Path(body_path).exists() and Path(body_path).stat().st_size > 0:
            # 使用三段式合并：part1 + body + part3
            body_inserted = insert_body_at_marker_compose(
                str(temp_path), body_path, BODY_MARKER, output_path
            )

            if body_inserted:
                print(f"  已使用 docxcompose 三段式合并插入 body（保留图表和格式）")
                # 补救：确保 body 中的图片被正确复制（docxcompose 可能丢失部分图片关系）
                copied_count = _copy_media_between_docx(body_path, output_path)
                if copied_count > 0:
                    print(f"  已补充复制 {copied_count} 张图片（修复 docxcompose 图片丢失）")
            else:
                # 如果没找到 marker，使用 docxcompose 追加到末尾
                print(f"  ⚠️ 未找到 BODY_MARKER，使用 docxcompose 追加 body")
                # 保存 body 的页边距
                body_margins = _get_document_sectpr_margins(body_path)

                doc = Document(str(temp_path))
                composer = Composer(doc)
                composer.append(Document(body_path))
                composer.save(output_path)

                # 修复 docxcompose 插入的分节符页边距
                if body_margins:
                    _fix_docxcompose_sectpr_margins(output_path, body_margins, False)

                # 补救：确保 body 中的图片被正确复制
                copied_count = _copy_media_between_docx(body_path, output_path)
                if copied_count > 0:
                    print(f"  已补充复制 {copied_count} 张图片（修复 docxcompose 图片丢失）")

        else:
            # 没有 body 文件，删除 BODY_MARKER 段落并保存
            doc = Document(str(temp_path))
            body_elem = doc.element.body
            for elem in list(body_elem):
                text = ''.join(t.text or '' for t in elem.iter() if t.text)
                if BODY_MARKER in text:
                    body_elem.remove(elem)
                    print(f"  已删除 BODY_MARKER（无 body 文件）")
                    break
            doc.save(output_path)

        # 6.5 处理 ENGLISH_SUMMARY_MARKER - 在标记位置插入 english_summary 内容
        if english_summary_path and Path(english_summary_path).exists() and Path(english_summary_path).stat().st_size > 0:
            # 保存 english_summary 的页边距
            es_margins = _get_document_sectpr_margins(english_summary_path)
            if es_margins:
                print(f"  english_summary.docx 页边距: top={es_margins.get('top')}, bottom={es_margins.get('bottom')}")

            doc = Document(output_path)
            english_summary_doc = Document(english_summary_path)

            # 尝试在表格单元格中插入
            es_inserted = insert_abstract_to_cell(doc, english_summary_doc, ENGLISH_SUMMARY_MARKER)
            if es_inserted:
                print(f"  已在 ENGLISH_SUMMARY_MARKER 位置插入 english_summary（表格单元格）")
            else:
                # 如果没有在表格中找到，尝试在段落中查找并替换
                es_inserted = _insert_abstract_at_paragraph(doc, english_summary_doc, ENGLISH_SUMMARY_MARKER)
                if es_inserted:
                    print(f"  已在段落中插入 english_summary")
                else:
                    print(f"  ⚠️ 未找到 ENGLISH_SUMMARY_MARKER，english_summary 未插入")

            doc.save(output_path)

            # 如果 english_summary 有自己的页边距，应用到它之前的分节符
            # 注意：_insert_abstract_at_paragraph 会在插入内容的末尾位置
            # 我们需要找到 english_summary 内容的位置，并在其前面添加分节符
            if es_margins and es_inserted:
                _apply_english_summary_margins(output_path, es_margins)
        else:
            # 没有 english_summary 文件，删除 ENGLISH_SUMMARY_MARKER
            doc = Document(output_path)
            body_elem = doc.element.body
            marker_removed = False
            for elem in list(body_elem):
                text = ''.join(t.text or '' for t in elem.iter() if t.text)
                if ENGLISH_SUMMARY_MARKER in text:
                    body_elem.remove(elem)
                    marker_removed = True
                    print(f"  已删除 ENGLISH_SUMMARY_MARKER（无 english_summary 文件）")
                    break
            if marker_removed:
                doc.save(output_path)

        # 7. 恢复图表 XML 中被转义的 Jinja2 语法
        if escaped_chart_files:
            _restore_jinja_in_charts(output_path, escaped_chart_files)
            print(f"  已恢复 {len(escaped_chart_files)} 个图表文件的原始内容")

        # 8. 清理临时文件
        temp_path.unlink(missing_ok=True)

        # 9. 验证输出
        final_doc = Document(output_path)
        image_count = sum(1 for rel in final_doc.part.rels.values() if 'image' in rel.reltype)

        # 验证附录是否完整保留（使用 lxml 检测，避免 python-docx 漏读）
        appendix_result = _verify_appendix_with_lxml(output_path)
        appendix_found = appendix_result.get('found', False)

        print(f"  输出: 段落={len(final_doc.paragraphs)}, 表格={len(final_doc.tables)}, 图片={image_count}")
        if appendix_found:
            print(f"  ✅ 法律附录已完整保留 ({appendix_result.get('location', '')})")
        else:
            print(f"  ⚠️ 法律附录未找到")

        return True

    except Exception as e:
        print(f"渲染失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def _verify_appendix_with_lxml(doc_path: str) -> Dict[str, Any]:
    """使用 lxml 验证文档中是否存在法律附录。

    python-docx 的 doc.paragraphs 会漏读嵌套在复杂结构中的段落，
    所以需要直接用 lxml 解析 XML 来检测。

    Args:
        doc_path: 文档路径

    Returns:
        {"found": bool, "location": str, "text": str}
    """
    import zipfile
    from lxml import etree

    W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
    appendix_keywords = ['附录APPENDIX', 'IMPORTANT DISCLOSURE']

    try:
        with zipfile.ZipFile(doc_path, 'r') as z:
            with z.open('word/document.xml') as f:
                tree = etree.parse(f)

        # 搜索段落中的附录标记
        for idx, p in enumerate(tree.iter(f'{W}p')):
            text = ''.join(t.text or '' for t in p.iter(f'{W}t'))
            text_upper = text.upper()
            for kw in appendix_keywords:
                if kw.upper() in text_upper:
                    return {
                        "found": True,
                        "location": f"段落 {idx}",
                        "text": text[:50]
                    }

        # 搜索表格中的附录标记
        for tbl_idx, tbl in enumerate(tree.iter(f'{W}tbl')):
            for row_idx, tr in enumerate(tbl.findall(f'{W}tr')):
                for col_idx, tc in enumerate(tr.findall(f'{W}tc')):
                    cell_text = ''.join(t.text or '' for t in tc.iter(f'{W}t'))
                    text_upper = cell_text.upper()
                    for kw in appendix_keywords:
                        if kw.upper() in text_upper:
                            return {
                                "found": True,
                                "location": f"表格 {tbl_idx} [{row_idx},{col_idx}]",
                                "text": cell_text[:50]
                            }

        return {"found": False}

    except Exception as e:
        print(f"  验证附录时出错: {e}")
        return {"found": False, "error": str(e)}


def _remove_docxcompose_extra_sectPr(docx_path: str) -> int:
    """删除 docxcompose 合并时插入的多余 sectPr。

    docxcompose 在 append() 时会自动插入分节符，这些分节符通常使用
    Word 默认页边距 (top=1440, bottom=1440, 即 1 英寸 = 1440 twips)。
    这会导致法律附录等部分的页边距被破坏。

    本函数检测并删除这些多余的 sectPr（段落内的 pPr/sectPr），
    保留文档末尾的独立 sectPr。

    Args:
        docx_path: docx 文件路径

    Returns:
        删除的 sectPr 数量
    """
    import zipfile
    from lxml import etree

    W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
    removed_count = 0

    try:
        # 读取文档
        with zipfile.ZipFile(docx_path, 'r') as z:
            files = {name: z.read(name) for name in z.namelist()}

        if 'word/document.xml' not in files:
            return 0

        doc_tree = etree.fromstring(files['word/document.xml'])
        body = doc_tree.find(f'{W}body')
        if body is None:
            return 0

        # 查找段落内的 sectPr (pPr/sectPr) - 这些是 docxcompose 插入的分节符
        # 特征：页边距为默认值 (top=1440, bottom=1440)
        for p in body.findall(f'.//{W}p'):
            pPr = p.find(f'{W}pPr')
            if pPr is not None:
                sectPr = pPr.find(f'{W}sectPr')
                if sectPr is not None:
                    # 检查是否是 docxcompose 插入的默认页边距 sectPr
                    pgMar = sectPr.find(f'{W}pgMar')
                    if pgMar is not None:
                        top = pgMar.get(f'{W}top', '')
                        bottom = pgMar.get(f'{W}bottom', '')
                        # 默认页边距：top=1440, bottom=1440 (1 inch = 1440 twips)
                        if top == '1440' and bottom == '1440':
                            pPr.remove(sectPr)
                            removed_count += 1
                            continue

                    # 如果没有 pgMar（使用继承的页边距），也可能是 docxcompose 插入的
                    # 但为了安全，只删除有明确默认页边距的

        if removed_count > 0:
            # 保存修改后的文档
            files['word/document.xml'] = etree.tostring(
                doc_tree, xml_declaration=True, encoding='UTF-8', standalone=True
            )

            import os
            os.remove(docx_path)
            with zipfile.ZipFile(docx_path, 'w', zipfile.ZIP_DEFLATED) as z:
                for name, content in files.items():
                    z.writestr(name, content)

    except Exception as e:
        print(f"  清理 docxcompose sectPr 时出错: {e}")

    return removed_count


def _clean_body_empty_paragraphs(body_doc: Document) -> None:
    """只清理 body 文档开头的空段落，保留 sectPr（页边距信息）。

    Args:
        body_doc: body 文档
    """
    ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
    body_body = body_doc.element.body

    # 只删除开头的空段落（保留目录控件 sdt 和 sectPr）
    body_elements = list(body_body)
    for elem in body_elements:
        tag = elem.tag.split('}')[-1]
        if tag == 'p':
            texts = elem.findall('.//w:t', ns)
            text = ''.join([t.text or '' for t in texts]).strip()
            if not text:
                body_body.remove(elem)
            else:
                break
        elif tag not in ['sdt', 'sectPr']:
            break


def _copy_media_between_docx(source_path: str, target_path: str) -> int:
    """从源 docx 复制所有媒体资源到目标 docx。

    使用 zipfile 直接操作，确保图片文件被正确复制。
    当 body_doc 的 XML 被 deepcopy 到 master_doc 后，图片引用（rId）会被保留，
    但目标文档的 rels 文件中没有对应的关系。本函数补充这些缺失的关系。

    Args:
        source_path: 源 docx 文件路径（如 body.docx）
        target_path: 目标 docx 文件路径（如 output.docx）

    Returns:
        复制的媒体文件数量
    """
    import zipfile
    import os
    import hashlib
    from lxml import etree

    copied_count = 0

    try:
        # 读取源文档的所有媒体文件和关系
        source_rid_to_media = {}  # {rId: (media_name, media_bytes, media_hash)}

        with zipfile.ZipFile(source_path, 'r') as z:
            for name in z.namelist():
                if name.startswith('word/media/'):
                    media_bytes = z.read(name)
                    media_hash = hashlib.md5(media_bytes).hexdigest()
                    # 记录所有媒体（不管是否有 rels 引用）
                    source_rid_to_media[f'_h_{media_hash}'] = (name[5:], media_bytes, media_hash)

            # 读取源文档的关系文件
            if 'word/_rels/document.xml.rels' in z.namelist():
                rels_xml = z.read('word/_rels/document.xml.rels')
                rels_tree = etree.fromstring(rels_xml)
                ns = {'r': 'http://schemas.openxmlformats.org/package/2006/relationships'}
                for rel in rels_tree.findall('r:Relationship', ns):
                    rel_id = rel.get('Id')
                    target = rel.get('Target')
                    rel_type = rel.get('Type')
                    if target and target.startswith('media/') and 'image' in rel_type:
                        media_name = target
                        if f'word/{media_name}' in z.namelist():
                            media_bytes = z.read(f'word/{media_name}')
                            media_hash = hashlib.md5(media_bytes).hexdigest()
                            source_rid_to_media[rel_id] = (media_name, media_bytes, media_hash)

        if not source_rid_to_media:
            return 0

        # 读取目标文档
        target_media_by_hash = {}  # {hash: media_name}
        target_rid_to_hash = {}     # {rId: hash} - 目标文档中已有的图片关系
        target_files = {}

        with zipfile.ZipFile(target_path, 'r') as z:
            for name in z.namelist():
                if name.startswith('word/media/'):
                    media_bytes = z.read(name)
                    media_hash = hashlib.md5(media_bytes).hexdigest()
                    target_media_by_hash[media_hash] = name[5:]
                target_files[name] = z.read(name)

            # 读取目标文档的 relations
            if 'word/_rels/document.xml.rels' in z.namelist():
                rels_xml = z.read('word/_rels/document.xml.rels')
                rels_tree = etree.fromstring(rels_xml)
                ns = {'r': 'http://schemas.openxmlformats.org/package/2006/relationships'}
                for rel in rels_tree.findall('r:Relationship', ns):
                    rel_id = rel.get('Id')
                    target = rel.get('Target')
                    rel_type = rel.get('Type')
                    if target and target.startswith('media/') and 'image' in rel_type:
                        if f'word/{target}' in z.namelist():
                            media_bytes = z.read(f'word/{target}')
                            media_hash = hashlib.md5(media_bytes).hexdigest()
                            target_rid_to_hash[rel_id] = media_hash

        # 找出目标文档中已有的最大 image 编号
        max_image_num = 0
        for media_name in target_files.keys():
            if 'word/media/image' in media_name:
                try:
                    num_str = media_name.split('image')[1].split('.')[0]
                    num = int(num_str)
                    if num > max_image_num:
                        max_image_num = num
                except (ValueError, IndexError):
                    pass

        # 找出目标文档中已有的 rId
        existing_rids = set(target_rid_to_hash.keys())

        # 更新目标文档的 rels 文件
        target_rels_tree = None
        if 'word/_rels/document.xml.rels' in target_files:
            target_rels_tree = etree.fromstring(target_files['word/_rels/document.xml.rels'])

        # rid_mapping: {源rId: (新rId, 新media_name)}
        rid_mapping = {}

        # 为源文档中的每个图片关系在目标文档中创建对应关系
        for rel_id, (media_name, media_bytes, media_hash) in source_rid_to_media.items():
            if rel_id.startswith('_h_'):  # 跳过无关系的媒体
                continue

            if media_hash in target_media_by_hash:
                # 目标文档中已有相同内容的图片
                existing_rid = None
                for rid, h in target_rid_to_hash.items():
                    if h == media_hash:
                        existing_rid = rid
                        break

                if existing_rid:
                    # 使用已有的 rId
                    rid_mapping[rel_id] = (existing_rid, target_media_by_hash[media_hash])
                    continue
                else:
                    # 这是不可能的情况，因为 target_media_by_hash 是按 hash 索引的
                    pass

            # 需要复制图片到目标文档
            max_image_num += 1
            ext = media_name.rsplit('.', 1)[-1] if '.' in media_name else 'png'
            new_media_name = f'media/image{max_image_num}.{ext}'

            # 生成新的唯一 rId
            new_rid = rel_id
            counter = 1
            while new_rid in existing_rids:
                new_rid = f'{rel_id}_{counter}'
                counter += 1

            rid_mapping[rel_id] = (new_rid, new_media_name)
            existing_rids.add(new_rid)

            # 添加图片文件
            target_files[f'word/{new_media_name}'] = media_bytes
            copied_count += 1

            # 在 rels 中添加新关系
            if target_rels_tree is not None:
                new_rel = etree.SubElement(target_rels_tree, 'Relationship')
                new_rel.set('Id', new_rid)
                new_rel.set('Type', 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/image')
                new_rel.set('Target', new_media_name)

        # 更新 document.xml 中的图片引用（将源 rId 替换为新 rId）
        if rid_mapping:
            doc_xml = target_files.get('word/document.xml')
            if doc_xml:
                doc_tree = etree.fromstring(doc_xml)
                W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
                R = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'

                # 遍历所有元素，查找包含 rId 引用的属性
                for elem in doc_tree.iter():
                    # 检查 r:embed 属性（图片引用）
                    embed_attr = f'{R}embed'
                    if embed_attr in elem.attrib:
                        old_rid = elem.attrib[embed_attr]
                        if old_rid in rid_mapping:
                            new_rid, new_media_name = rid_mapping[old_rid]
                            elem.attrib[embed_attr] = new_rid

                    # 检查 r:id 属性（关系引用）
                    id_attr = f'{R}id'
                    if id_attr in elem.attrib:
                        old_rid = elem.attrib[id_attr]
                        if old_rid in rid_mapping:
                            new_rid, new_media_name = rid_mapping[old_rid]
                            elem.attrib[id_attr] = new_rid

                target_files['word/document.xml'] = etree.tostring(
                    doc_tree, xml_declaration=True, encoding='UTF-8', standalone=True
                )

        # 更新 rels 文件
        if target_rels_tree is not None and copied_count > 0:
            target_files['word/_rels/document.xml.rels'] = etree.tostring(
                target_rels_tree, xml_declaration=True, encoding='UTF-8', standalone=True
            )

        # 更新 [Content_Types].xml
        if '[Content_Types].xml' in target_files and copied_count > 0:
            ct_tree = etree.fromstring(target_files['[Content_Types].xml'])

            existing_exts = set()
            for default in ct_tree.findall('.//{http://schemas.openxmlformats.org/package/2006/content-types}Default'):
                existing_exts.add(default.get('Extension', '').lower())

            ext_content_types = {
                'png': 'image/png',
                'jpeg': 'image/jpeg',
                'jpg': 'image/jpeg',
                'gif': 'image/gif',
                'bmp': 'image/bmp',
                'tiff': 'image/tiff',
                'emf': 'image/x-emf',
                'wmf': 'image/x-wmf',
            }

            for _, new_media_name, _ in [(k, v[1], None) for k, v in rid_mapping.items() if not k.startswith('_h_')]:
                ext = new_media_name.rsplit('.', 1)[-1].lower() if '.' in new_media_name else ''
                if ext and ext not in existing_exts and ext in ext_content_types:
                    new_default = etree.SubElement(ct_tree, '{http://schemas.openxmlformats.org/package/2006/content-types}Default')
                    new_default.set('Extension', ext)
                    new_default.set('ContentType', ext_content_types[ext])
                    existing_exts.add(ext)

            target_files['[Content_Types].xml'] = etree.tostring(
                ct_tree, xml_declaration=True, encoding='UTF-8', standalone=True
            )

        # 重新写入目标文档
        if copied_count > 0:
            os.remove(target_path)
            with zipfile.ZipFile(target_path, 'w', zipfile.ZIP_DEFLATED) as z:
                for name, content in target_files.items():
                    z.writestr(name, content)

    except Exception as e:
        print(f"  复制媒体资源时出错: {e}")
        import traceback
        traceback.print_exc()

    return copied_count


def _ensure_final_sectPr(body_element, final_sectPr) -> None:
    """确保文档末尾有正确的 sectPr。

    Args:
        body_element: 文档 body 元素
        final_sectPr: 要添加的 sectPr（来自模板末尾）
    """
    # 删除现有的末尾 sectPr
    while True:
        elements = list(body_element)
        if elements and elements[-1].tag.split('}')[-1] == 'sectPr':
            body_element.remove(elements[-1])
        else:
            break

    # 添加模板的 sectPr
    if final_sectPr is not None:
        body_element.append(final_sectPr)


def expand_analyst_certification(docx_path: str, elements: Dict[str, Any]) -> int:
    """扩展分析师认证声明，为每个分析师生成独立的声明段落。

    在模板中，分析师声明只有一个版本（使用 a1_cn, a1_en）。
    如果有多个分析师（a2, a3...），需要复制整段声明并替换对应的占位符。

    分析师认证声明模板格式：
    我， {{ a1_cn }}，在此保证...I, {{ a1_en }}, certify that...

    Args:
        docx_path: docx 文件路径
        elements: 包含分析师数据的字典（a1_cn, a1_en, a2_cn, a2_en, ...）

    Returns:
        扩展的分析师数量（不包括第一个）
    """
    import zipfile
    import os
    import re
    from lxml import etree

    # 1. 统计有多少个分析师有数据
    analysts = []
    for i in range(1, 9):
        cn = elements.get(f'a{i}_cn', '')
        en = elements.get(f'a{i}_en', '')
        if cn or en:
            analysts.append({
                'index': i,
                'cn': cn or '',
                'en': en or ''
            })

    if len(analysts) <= 1:
        # 只有一个或没有分析师，不需要扩展
        return 0

    W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'

    try:
        # 2. 解压 docx
        docx_dir = os.path.dirname(docx_path)
        temp_dir = os.path.join(docx_dir, '_temp_analyst_expand')

        with zipfile.ZipFile(docx_path, 'r') as z:
            z.extractall(temp_dir)

        # 3. 读取 document.xml
        doc_xml_path = os.path.join(temp_dir, 'word', 'document.xml')
        tree = etree.parse(doc_xml_path)
        root = tree.getroot()

        # 4. 找到分析师声明所在的表格单元格
        # 搜索包含 "在此保证" 和 "a1_cn" 的单元格
        # 优先选择较小的单元格（独立的分析师声明表格），而不是大的法律附录
        certification_cell = None
        certification_row = None
        certification_table = None
        best_cell_length = float('inf')

        for tbl in root.iter(f'{W}tbl'):
            for tr in tbl.findall(f'{W}tr'):
                for tc in tr.findall(f'{W}tc'):
                    cell_text = ''.join(t.text or '' for t in tc.iter(f'{W}t'))
                    if '在此保证' in cell_text and ('a1_cn' in cell_text or '{{ a1_cn }}' in cell_text):
                        # 选择文本长度较短的单元格（独立声明 vs 大附录）
                        if len(cell_text) < best_cell_length:
                            best_cell_length = len(cell_text)
                            certification_cell = tc
                            certification_row = tr
                            certification_table = tbl

        if certification_cell is None:
            print("  ⚠️ 未找到分析师认证声明单元格")
            # 清理临时目录
            import shutil
            shutil.rmtree(temp_dir)
            return 0

        # 5. 获取声明段落模板
        # 单元格中可能有多个段落，找到包含声明的那个
        certification_paragraphs = []
        for p in certification_cell.findall(f'{W}p'):
            p_text = ''.join(t.text or '' for t in p.iter(f'{W}t'))
            if '在此保证' in p_text:
                certification_paragraphs.append(p)

        if not certification_paragraphs:
            print("  ⚠️ 未找到分析师认证声明段落")
            import shutil
            shutil.rmtree(temp_dir)
            return 0

        # 获取第一个声明段落作为模板
        template_para = certification_paragraphs[0]
        template_para_xml = etree.tostring(template_para, encoding='unicode')

        # 6. 为额外的分析师创建声明段落
        # 在第一个声明段落后插入
        insert_position = list(certification_cell).index(template_para) + 1

        expanded_count = 0
        for analyst in analysts[1:]:  # 跳过第一个分析师
            # 复制模板段落
            new_para_xml = template_para_xml

            # 替换占位符：a1_cn -> 实际值, a1_en -> 实际值
            # 支持多种格式：{{ a1_cn }}、{{a1_cn}}、{ a1_cn }
            new_para_xml = re.sub(
                r'\{\{\s*a1_cn\s*\}\}|\{%?\s*a1_cn\s*%?\}',
                analyst['cn'],
                new_para_xml
            )
            new_para_xml = re.sub(
                r'\{\{\s*a1_en\s*\}\}|\{%?\s*a1_en\s*%?\}',
                analyst['en'],
                new_para_xml
            )

            # 解析新段落
            new_para = etree.fromstring(new_para_xml)

            # 插入到单元格中
            certification_cell.insert(insert_position, new_para)
            insert_position += 1
            expanded_count += 1

        # 7. 写回 document.xml
        tree.write(doc_xml_path, xml_declaration=True, encoding='UTF-8', standalone=True)

        # 8. 重新打包为 docx
        os.remove(docx_path)
        with zipfile.ZipFile(docx_path, 'w', zipfile.ZIP_DEFLATED) as z:
            for root_dir, dirs, files in os.walk(temp_dir):
                for file in files:
                    file_path = os.path.join(root_dir, file)
                    arcname = os.path.relpath(file_path, temp_dir)
                    z.write(file_path, arcname)

        # 9. 清理临时目录
        import shutil
        shutil.rmtree(temp_dir)

        return expanded_count

    except Exception as e:
        print(f"  扩展分析师声明时出错: {e}")
        import traceback
        traceback.print_exc()
        # 清理临时目录
        import shutil
        temp_dir = os.path.join(os.path.dirname(docx_path), '_temp_analyst_expand')
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        return 0
