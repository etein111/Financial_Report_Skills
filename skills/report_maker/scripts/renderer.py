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


def _cleanup_merged_cells(doc: Document) -> Document:
    """清理嵌套的重复单元格和异常结构。

    OpenCode 生成的模板会在 tc 中嵌套 tbl，导致内容重复。
    本函数清理这些异常结构。

    Args:
        doc: Document 对象

    Returns:
        清理后的 Document 对象
    """
    from lxml import etree
    W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'

    def get_direct_text(elem):
        """获取元素直接子元素的文本，不包括嵌套元素。"""
        parts = []
        for child in elem:
            if child.tag == W + 'p':
                for r in child:
                    if r.tag == W + 'r':
                        t = r.find(W + 't')
                        if t is not None and t.text:
                            parts.append(t.text)
        return ''.join(parts)

    def merge_nested_tbl_to_tc(tc):
        """将 tc 中嵌套的 tbl 内容合并到 tc 本身。

        OpenCode 生成的模板结构是：tc > tbl > tr > tc
        需要提取内层 tc 的文本，替换到外层 tc 中。
        """
        nested_tbls = tc.findall(W + 'tbl')
        if not nested_tbls:
            return

        # 获取外层 tc 自己的文本（通常是标记如 [Table_Author]）
        outer_text = get_direct_text(tc)

        # 收集所有嵌套 tc 的文本
        all_nested_texts = []
        for nested_tbl in nested_tbls:
            for nested_tr in nested_tbl.findall(W + 'tr'):
                row_texts = []
                for nested_tc in nested_tr.findall(W + 'tc'):
                    text = get_direct_text(nested_tc)
                    row_texts.append(text)
                all_nested_texts.append(row_texts)

        # 清理嵌套 tbl（删除所有）
        for nested_tbl in nested_tbls:
            tc.remove(nested_tbl)

        # 如果外层文本是标记（如 [Table_Author]），保留标记但添加内容
        if outer_text and '[' in outer_text:
            # 保留外层标记，添加内层内容
            paras = tc.findall(W + 'p')
            if paras:
                first_para = paras[0]
                runs = first_para.findall(W + 'r')
                if runs:
                    t = runs[0].find(W + 't')
                    if t is not None:
                        # 收集所有内层文本
                        content = []
                        for row in all_nested_texts:
                            for text in row:
                                if text and not text.startswith('{{'):
                                    content.append(text)
                        if content:
                            t.text = content[0]

    # 遍历文档中的所有顶层表格
    for tbl in doc.element.body.findall(W + 'tbl'):
        for tr in tbl.findall(W + 'tr'):
            for tc in tr.findall(W + 'tc'):
                merge_nested_tbl_to_tc(tc)

    return doc


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

        # 4. 清理嵌套的重复单元格
        final_doc = _cleanup_merged_cells(final_doc)

        # 5. 直接保存
        final_doc.save(output_path)

        # 6. 清理临时文件
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

    Args:
        elements: 原始要素字典

    Returns:
        处理后的上下文字典
    """
    context = {}

    # 跳过分析师原始字段和 fragment 字段
    skip_prefixes = ['a1_', 'a2_', 'a3_', 'a4_', 'a5_', 'a6_', 'a7_', 'a8_']
    for k, v in elements.items():
        if k in ['abstract', 'body']:
            continue
        if any(k.startswith(p) for p in skip_prefixes):
            continue
        context[k] = v

    # 展平第一个分析师字段（用于模板渲染）
    context['analyst_chinese_name'] = elements.get('a1_cn', '')
    context['analyst_english_name'] = elements.get('a1_en', '')
    context['analyst_sfc_code'] = elements.get('a1_sfc', '')
    context['analyst_email'] = elements.get('a1_email', '')

    # 确保所有分析师字段都有值（空字符串），避免模板中的占位符未被替换
    # 分析师字段：a1_cn, a1_en, a1_sfc, a1_email ... a8_cn, a8_en, a8_sfc, a8_email
    analyst_suffixes = ['cn', 'en', 'sfc', 'email']
    for i in range(1, 9):
        for suffix in analyst_suffixes:
            field_name = f'a{i}_{suffix}'
            # 如果 elements 中没有该字段或值为 None，设置为空字符串
            context[field_name] = elements.get(field_name) or ''

    # 记录哪些分析师有数据（用于后续清理空分析师单元格）
    context['_analysts_with_data'] = set()
    for i in range(1, 9):
        cn = elements.get(f'a{i}_cn', '')
        en = elements.get(f'a{i}_en', '')
        if cn or en:  # 如果有中文名或英文名，认为该分析师有数据
            context['_analysts_with_data'].add(i)

    # 收集所有分析师（用于循环渲染，如果模板支持）
    analysts = []
    for i in range(1, 9):
        cn = elements.get(f'a{i}_cn', '')
        if cn:
            analysts.append({
                'chinese_name': cn,
                'english_name': elements.get(f'a{i}_en', ''),
                'sfc_code': elements.get(f'a{i}_sfc', ''),
                'email': elements.get(f'a{i}_email', '')
            })
    context['analysts'] = analysts

    return context


def clean_empty_analyst_cells(doc: Document, analysts_with_data: set) -> int:
    """清理没有数据的分析师单元格。

    当分析师没有数据时，清空整个单元格（包括固定标签如 SFC:、Email: 等）。
    支持嵌套表格。

    Args:
        doc: Word 文档对象
        analysts_with_data: 有数据的分析师编号集合（如 {1, 2}）

    Returns:
        清理的单元格数量
    """
    cleaned_count = 0

    def clean_table(table):
        """递归清理表格（包括嵌套表格）"""
        nonlocal cleaned_count

        for row in table.rows:
            for cell in row.cells:
                # 先处理嵌套表格
                for nested_table in cell.tables:
                    clean_table(nested_table)

                cell_text = cell.text.strip()

                # 跳过空单元格
                if not cell_text:
                    continue

                # 检查是否是空分析师单元格的特征：
                # 模板格式: "{{ a1_cn }} {{ a1_en }}], SFC:{{ a1_sfc }}"
                # 空分析师渲染后: " ], SFC:" 或 "], SFC:"

                # 检测模式：包含 "], SFC:" 但没有实际名字
                if '], SFC:' in cell_text or '],SFC:' in cell_text:
                    # 移除已知的标签和标点
                    text_check = cell_text
                    for pattern in ['], SFC:', '],SFC:', 'SFC:', ', SFC:', '@']:
                        text_check = text_check.replace(pattern, '')

                    # 移除空白字符
                    text_check = text_check.strip()

                    # 如果移除标签后没有实际内容（或只有很短的残留），清空单元格
                    if len(text_check) < 3:
                        cell.text = ''
                        cleaned_count += 1

    # 处理所有顶级表格
    for table in doc.tables:
        clean_table(table)

    return cleaned_count


def insert_abstract_to_cell(doc: Document, abstract_doc: Document, marker: str) -> bool:
    """在表格单元格中插入 abstract 内容，完整保留格式。

    Args:
        doc: 目标文档
        abstract_doc: abstract 文档
        marker: 占位符标记

    Returns:
        是否成功插入
    """
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                if marker in cell.text:
                    # 完全清空单元格（删除所有段落，只保留一个空段落）
                    tc = cell._tc
                    # 删除所有段落元素
                    for p in tc.findall('.//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p'):
                        tc.remove(p)

                    # 插入 abstract 内容（使用 deepcopy 完整保留格式）
                    for src_para in abstract_doc.paragraphs:
                        if src_para.text.strip():
                            # 直接复制整个段落元素
                            tc.append(deepcopy(src_para._element))

                    return True
    return False


def insert_body_at_marker_compose(doc_path: str, body_path: str, marker: str, output_path: str) -> bool:
    """使用 docxcompose 在标记位置插入 body 内容。

    将模板分成 marker 之前和之后两部分，然后用 docxcompose 合并。

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

        # 加载文档
        doc = Document(doc_path)
        body_doc = Document(body_path)

        # 找到 marker 位置
        body_element = doc.element.body
        marker_idx = None

        for i, elem in enumerate(body_element):
            if elem.tag.endswith('}p'):
                text = ''.join(t.text for t in elem.iter() if t.text)
                if marker in text:
                    marker_idx = i
                    break

        if marker_idx is None:
            print(f"  未找到 marker: {marker}")
            return False

        # 创建两个临时文档：marker 之前和之后
        # 方法：删除 marker 段落，然后用 docxcompose 插入 body

        # 删除 marker 段落
        marker_elem = list(body_element)[marker_idx]
        body_element.remove(marker_elem)

        # 保存临时文档（没有 marker）
        temp_path = Path(output_path).parent / "temp_no_marker.docx"
        doc.save(str(temp_path))

        # 使用 docxcompose 合并
        # 策略：将 body 内容插入到正确位置
        # docxcompose 默认是追加到末尾，我们需要更复杂的处理

        # 另一种方法：直接操作 XML，但用 body_doc 的原始内容
        doc = Document(str(temp_path))
        body_element = doc.element.body
        elements = list(body_element)

        # 计算插入位置（marker 原来的位置）
        insert_idx = marker_idx

        # 从 body_doc 复制所有元素
        for body_elem in body_doc.element.body:
            tag = body_elem.tag.split('}')[-1]
            if tag in ['p', 'tbl', 'sdt']:
                new_elem = deepcopy(body_elem)
                body_element.insert(insert_idx, new_elem)
                insert_idx += 1

        doc.save(output_path)

        # 清理临时文件
        Path(temp_path).unlink(missing_ok=True)

        # 使用 docxcompose 修复图片引用
        # 重新打开并用 composer 合并空文档来触发资源整理
        master = Document(output_path)
        composer = Composer(master)
        # 不实际追加任何文档，只是用 composer 保存
        composer.save(output_path)

        return True

    except Exception as e:
        print(f"  docxcompose 插入失败: {e}")
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


def fix_body_margins(body_doc: Document, left_margin_cm: float = 1.0, right_margin_cm: float = 1.0) -> None:
    """修复 body 文档的页边距。

    body 从 draft 提取时可能带有首页的特殊页边距（如 6.35cm），
    需要重置为标准值。

    Args:
        body_doc: body 文档
        left_margin_cm: 左边距（厘米）
        right_margin_cm: 右边距（厘米）
    """
    if Cm is None:
        return

    for section in body_doc.sections:
        section.left_margin = Cm(left_margin_cm)
        section.right_margin = Cm(right_margin_cm)


def copy_headers_footers(source_doc: Document, target_doc: Document, target_section_start: int = 1) -> None:
    """复制源文档的页眉页脚到目标文档。

    复制所有类型的页眉页脚：默认、首页、奇偶页。

    Args:
        source_doc: 源文档（body.docx）
        target_doc: 目标文档（output.docx）
        target_section_start: 目标文档中开始复制的 section 索引
    """
    source_sections = list(source_doc.sections)
    target_sections = list(target_doc.sections)

    def copy_element(source, target):
        """复制 XML 元素内容"""
        if source is None or target is None:
            return
        source_elem = source._element
        target_elem = target._element
        for child in list(target_elem):
            target_elem.remove(child)
        for child in source_elem:
            target_elem.append(deepcopy(child))

    # 复制页眉页脚到目标 section
    for i, source_section in enumerate(source_sections):
        target_idx = target_section_start + i
        if target_idx >= len(target_sections):
            break

        target_section = target_sections[target_idx]

        # 复制 section 的页眉页脚设置
        target_section.different_first_page_header_footer = source_section.different_first_page_header_footer

        # 断开所有链接
        try:
            target_section.header.is_linked_to_previous = False
        except:
            pass
        try:
            target_section.footer.is_linked_to_previous = False
        except:
            pass
        try:
            target_section.first_page_header.is_linked_to_previous = False
        except:
            pass
        try:
            target_section.first_page_footer.is_linked_to_previous = False
        except:
            pass
        try:
            target_section.even_page_header.is_linked_to_previous = False
        except:
            pass
        try:
            target_section.even_page_footer.is_linked_to_previous = False
        except:
            pass

        # 复制页眉
        try:
            copy_element(source_section.header, target_section.header)
        except:
            pass
        try:
            copy_element(source_section.first_page_header, target_section.first_page_header)
        except:
            pass
        try:
            copy_element(source_section.even_page_header, target_section.even_page_header)
        except:
            pass

        # 复制页脚
        try:
            copy_element(source_section.footer, target_section.footer)
        except:
            pass
        try:
            copy_element(source_section.first_page_footer, target_section.first_page_footer)
        except:
            pass
        try:
            copy_element(source_section.even_page_footer, target_section.even_page_footer)
        except:
            pass


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


def _copy_docx(src: str, dst: str) -> None:
    """复制 docx 文件。

    Args:
        src: 源文件路径
        dst: 目标文件路径
    """
    import shutil
    shutil.copy2(src, dst)


def _escape_xml_text(text: str) -> str:
    """转义 XML 特殊字符。

    Args:
        text: 原始文本

    Returns:
        转义后的文本，用于插入 XML
    """
    if not text:
        return ''
    # 替换 XML 特殊字符
    text = text.replace('&', '&amp;')  # 必须最先处理
    text = text.replace('<', '&lt;')
    text = text.replace('>', '&gt;')
    text = text.replace('"', '&quot;')
    text = text.replace("'", '&apos;')
    return text


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
            value = _escape_xml_text(context.get(key, '') or '')
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
        str_value = _escape_xml_text(str(value) if value else '')
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


def render_report(
    template_path: str,
    elements: Dict[str, Any],
    abstract_path: str,
    body_path: str,
    output_path: str
) -> bool:
    """渲染报告，正确处理分析师字段、abstract 和 body。

    支持 Jinja2 模板语法，包括 {% if %}, {% for %} 等控制结构。
    模板中的分析师字段可以使用 if block 条件渲染：
        {% if a1_cn %}
        {{ a1_cn }} {{ a1_en }}], SFC:{{ a1_sfc }}
        {% if a2_cn %}
        {{ a2_cn }} {{ a2_en }}], SFC:{{ a2_sfc }}
        {% endif %}
        {% endif %}

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

    Returns:
        是否成功
    """
    if not DOCX_AVAILABLE:
        print("Error: python-docx or docxtpl not installed")
        return False

    try:
        from docxcompose.composer import Composer

        # 1. 准备渲染上下文（支持 Jinja2 if block）
        context = prepare_context_with_analysts(elements)

        # 2. 使用 docxtpl 渲染模板（支持 Jinja2 语法）
        # docxtpl 支持 {% if %}, {% for %} 等控制结构
        template = DocxTemplate(template_path)

        # 将 abstract 和 body 路径转换为绝对路径
        abstract_abs = str(Path(abstract_path).resolve()) if abstract_path else ''
        body_abs = str(Path(body_path).resolve()) if body_path else ''

        # 添加到上下文供后续插入使用
        context['_abstract_abs'] = abstract_abs
        context['_body_abs'] = body_abs

        template.render(context)

        # 3. 保存 docxtpl 渲染结果
        temp_path = Path(output_path).parent / "temp_rendered.docx"
        template.save(str(temp_path))

        # 4. 加载渲染后的文档
        doc = Document(str(temp_path))

        # 4. 插入 abstract
        if abstract_path and Path(abstract_path).is_file() and Path(abstract_path).stat().st_size > 0:
            abstract_doc = Document(abstract_path)
            if insert_abstract_to_cell(doc, abstract_doc, ABSTRACT_MARKER):
                print(f"  已插入 abstract")
            else:
                print(f"  警告: 未找到 abstract 占位符")

        # 5. 找到 BODY_MARKER 位置
        body_element = doc.element.body
        all_elements = list(body_element)
        ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}

        marker_idx = None
        marker_elem = None

        for i, elem in enumerate(all_elements):
            if elem.tag.endswith('}p'):
                text = ''.join(t.text for t in elem.iter() if t.text)
                if BODY_MARKER in text:
                    marker_idx = i
                    marker_elem = elem
                    print(f"  找到 body 占位符位置: 第 {i} 个元素")
                    break

        # 6. 在 BODY_MARKER 位置插入 body 内容
        if marker_elem is not None and body_path and Path(body_path).is_file() and Path(body_path).stat().st_size > 0:
            body_doc = Document(body_path)

            # 收集 body 末尾的 sectPr（body 自己的页边距设置）
            body_sectPr = None
            body_elements = list(body_doc.element.body)
            for elem in reversed(body_elements):
                tag = elem.tag.split('}')[-1]
                if tag == 'sectPr':
                    body_sectPr = deepcopy(elem)
                    break

            # 只清理 body 开头的空段落，保留 sectPr（页边距信息）
            _clean_body_empty_paragraphs(body_doc)

            # 在 marker 位置插入 body 的所有元素
            insert_idx = marker_idx
            for body_elem in body_doc.element.body:
                tag = body_elem.tag.split('}')[-1]
                # 复制段落、表格和目录控件，跳过 sectPr（稍后单独处理）
                if tag in ['p', 'tbl', 'sdt']:
                    new_elem = deepcopy(body_elem)
                    body_element.insert(insert_idx, new_elem)
                    insert_idx += 1

            # 删除 marker 段落（现在位置变了，需要重新找）
            all_elements = list(body_element)
            for elem in all_elements:
                if elem.tag.endswith('}p'):
                    text = ''.join(t.text for t in elem.iter() if t.text)
                    if BODY_MARKER in text:
                        body_element.remove(elem)
                        break

            # 在 body 内容末尾添加 body 的 sectPr（保留 body 的页边距）
            if body_sectPr is not None:
                body_element.append(body_sectPr)

            print(f"  已在占位符位置插入 body（保留 body 的页边距）")

        elif marker_elem is None:
            print(f"  警告: 未找到 body 占位符 (BODY_MARKER)")

        # 7. 保存最终文档
        doc.save(output_path)

        # 8. 清理临时文件
        temp_path.unlink(missing_ok=True)

        # 11. 验证输出
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


def _clean_body_sectPr(body_doc: Document) -> None:
    """清理 body 文档中的 sectPr，防止空白页。

    Args:
        body_doc: body 文档
    """
    ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
    body_body = body_doc.element.body

    # 删除段落内的 sectPr
    for p_elem in body_body.findall('.//w:p', ns):
        pPr = p_elem.find('w:pPr', ns)
        if pPr is not None:
            sectPr = pPr.find('w:sectPr', ns)
            if sectPr is not None:
                pPr.remove(sectPr)

    # 删除独立的 sectPr（除了文档末尾的）
    body_elements = list(body_body)
    for elem in body_elements[:-1]:
        if elem.tag.split('}')[-1] == 'sectPr':
            body_body.remove(elem)

    # 删除开头的空段落（保留目录控件 sdt）
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
        elif tag != 'sdt':
            break


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


def _copy_images_from_body(master_doc: Document, body_doc: Document) -> int:
    """从 body 文档复制图片资源到主文档。

    Args:
        master_doc: 主文档
        body_doc: body 文档

    Returns:
        复制的图片数量
    """
    copied_count = 0

    try:
        # 获取 body 文档中的所有图片关系
        for rel_id, rel in body_doc.part.rels.items():
            if 'image' in rel.reltype:
                # 获取图片数据
                image_part = rel.target_part
                image_blob = image_part.blob
                content_type = image_part.content_type

                # 添加到主文档
                # 注意：这里的 rel_id 可能会改变，需要更新引用
                # 但由于我们用 deepcopy 复制了 XML，引用已经存在
                # 只需要确保图片资源存在即可

                # 检查主文档是否已有该图片
                image_exists = False
                for master_rel in master_doc.part.rels.values():
                    if 'image' in master_rel.reltype:
                        if master_rel.target_part.blob == image_blob:
                            image_exists = True
                            break

                if not image_exists:
                    # 添加新图片到主文档
                    # 使用相同的 rel_id 以保持引用一致
                    from docx.opc.constants import RELATIONSHIP_TYPE as RT
                    master_doc.part.relate_to(image_part, RT.IMAGE, rel_id)
                    copied_count += 1

    except Exception as e:
        print(f"  复制图片时出错: {e}")

    if copied_count > 0:
        print(f"  已复制 {copied_count} 张图片")

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
