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
            # 替换格式 {{ a1_cn }} -> "杨斌"
            replacements[f'{{{{ {key} }}}}'] = value
            # 也处理无空格格式 {{{key}}}
            replacements[f'{{{{{key}}}}}]'] = value.rstrip(']') if value else ''

    # 2. 添加简单字段占位符（company, ticker, rating, 等）
    simple_fields = [
        'report_date', 'company', 'ticker', 'title', 'rating',
        'current_price', 'target_price', 'market_cap', 'shares_in_issue',
        'one_year_high', 'one_year_low', 'current_price_date',
        'analyst_chinese_name', 'analyst_english_name', 'analyst_sfc_code', 'analyst_email',
        'a1_cn', 'a1_en', 'a1_sfc', 'a1_email'
    ]
    for field in simple_fields:
        if field in context:
            value = context[field]
            if field in ['abstract', 'body']:
                # 这些用标记替代
                replacements[f'{{{{{field}}}}}]'] = ''
            else:
                replacements[f'{{{{{field}}}}}]'] = str(value) if value else ''

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

    使用 docxcompose 正确合并 body 文档，保留图片和格式。

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

        # 1. 准备渲染上下文（展平分析师字段）
        context = prepare_context_with_analysts(elements)

        # 2. 复制模板并通过 XML 替换所有占位符
        # 注意：docxtpl 会破坏嵌套表格，所以不能使用它进行渲染
        temp_path = Path(output_path).parent / "temp_rendered.docx"
        _copy_docx(template_path, str(temp_path))

        # 2.5 通过 XML 级别替换所有占位符
        replace_all_placeholders_in_xml(str(temp_path), context, elements)

        # 3. 继续后续处理（插入 abstract、body 等）

        # 3.5 加载渲染后的文档
        doc = Document(str(temp_path))
        template_section_count = len(doc.sections)

        # 3.5 清理空分析师单元格（移除只有标签没有数据的单元格内容）
        # 注意：此时占位符已经被替换为实际值，空单元格只包含标签如 "], SFC:"
        analysts_with_data = context.get('_analysts_with_data', set())
        cleaned_cells = clean_empty_analyst_cells(doc, analysts_with_data)
        if cleaned_cells > 0:
            print(f"  已清理 {cleaned_cells} 个空分析师单元格")

        # 4. 加载并处理 abstract
        abstract_inserted = False
        if Path(abstract_path).exists() and Path(abstract_path).stat().st_size > 0:
            abstract_doc = Document(abstract_path)
            abstract_inserted = insert_abstract_to_cell(doc, abstract_doc, ABSTRACT_MARKER)
            if abstract_inserted:
                print(f"  已插入 abstract")
            else:
                print(f"  警告: 未找到 abstract 占位符")

        # 5. 找到 BODY_MARKER 位置，准备用 docxcompose 插入 body
        body_element = doc.element.body
        marker_idx = None
        marker_elem = None

        for i, elem in enumerate(body_element):
            if elem.tag.endswith('}p'):
                text = ''.join(t.text for t in elem.iter() if t.text)
                if BODY_MARKER in text:
                    marker_idx = i
                    marker_elem = elem
                    break

        if marker_idx is None:
            print(f"  警告: 未找到 body 占位符")
            doc.save(output_path)
            temp_path.unlink(missing_ok=True)
            return True

        # 6. 提取 marker 之后的元素（法律附录等）
        # 注意：要同时提取末尾的 sectPr，因为它定义了文档的 section 属性
        elements_after_marker = []
        final_sectPr = None
        all_elements = list(body_element)

        for elem in all_elements[marker_idx + 1:]:
            tag = elem.tag.split('}')[-1]
            if tag == 'sectPr':
                # 保存文档末尾的 sectPr
                final_sectPr = deepcopy(elem)
                body_element.remove(elem)
            else:
                elements_after_marker.append(deepcopy(elem))
                body_element.remove(elem)

        # 7. 删除 marker 段落
        body_element.remove(marker_elem)

        # 8. 保存临时文档（只有模板前半部分）
        temp_before_path = Path(output_path).parent / "temp_before.docx"
        doc.save(str(temp_before_path))

        # 9. 使用 docxcompose 合并 body
        master = Document(str(temp_before_path))
        composer = Composer(master)

        body_doc = None
        if Path(body_path).exists() and Path(body_path).stat().st_size > 0:
            body_doc = Document(body_path)

            # 9.5 在追加之前清理 body_doc 中的所有 sectPr（防止空白页）
            # 这些 sectPr 会导致强制换页
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
            for elem in body_elements[:-1]:  # 排除最后一个元素
                if elem.tag.split('}')[-1] == 'sectPr':
                    body_body.remove(elem)

            # 删除 body_doc 开头的空段落（保留目录控件 sdt）
            body_elements = list(body_body)
            for elem in body_elements:
                tag = elem.tag.split('}')[-1]
                if tag == 'p':
                    texts = elem.findall('.//w:t', ns)
                    text = ''.join([t.text or '' for t in texts]).strip()
                    if not text:
                        body_body.remove(elem)
                    else:
                        break  # 遇到有内容的段落就停止
                elif tag != 'sdt':  # sdt (目录) 保留
                    break

            composer.append(body_doc)
            print(f"  已使用 docxcompose 插入 body（已预清理 sectPr）")

        # 10. 在附录前添加分节符，隔离正文和附录
        # 这样附录可以使用独立的页边距设置（保持 template 原始值）
        master_body = master.element.body
        ns_local = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}

        # 创建一个分节符段落（sectPr in pPr）
        # 这会让附录之后的内容属于新的 section
        if elements_after_marker:
            # 创建空段落
            from docx.oxml import OxmlElement
            from docx.oxml.ns import qn

            # 创建 p 元素
            p_elem = OxmlElement('w:p')
            pPr = OxmlElement('w:pPr')

            # 创建 sectPr（分节符）
            sectPr = OxmlElement('w:sectPr')
            # 使用 nextPage 类型（新页面开始）
            sect_type = OxmlElement('w:type')
            sect_type.set(qn('w:val'), 'nextPage')
            sectPr.append(sect_type)

            # 设置页面尺寸（A4: 21.01cm x 29.70cm）
            pgSz = OxmlElement('w:pgSz')
            pgSz.set(qn('w:w'), '11910')  # A4 宽度 in twips
            pgSz.set(qn('w:h'), '16840')  # A4 高度 in twips
            sectPr.append(pgSz)

            # 设置页边距为 body.docx 的值（6.35cm）
            # 这个 sectPr 定义的是前面 section（正文）的属性
            pgMar = OxmlElement('w:pgMar')
            pgMar.set(qn('w:left'), '3600')  # 6.35cm in twips
            pgMar.set(qn('w:right'), '567')  # 1.00cm in twips
            pgMar.set(qn('w:top'), '567')    # 1.00cm in twips
            pgMar.set(qn('w:bottom'), '1021')  # 1.80cm in twips
            pgMar.set(qn('w:header'), '567')  # 页眉距离 1.00cm
            pgMar.set(qn('w:footer'), '919')  # 页脚距离 1.62cm
            pgMar.set(qn('w:gutter'), '0')
            sectPr.append(pgMar)

            # 设置列
            cols = OxmlElement('w:cols')
            cols.set(qn('w:space'), '425')
            cols.set(qn('w:num'), '1')
            sectPr.append(cols)

            # 设置文档网格
            docGrid = OxmlElement('w:docGrid')
            docGrid.set(qn('w:linePitch'), '299')
            docGrid.set(qn('w:charSpace'), '0')
            sectPr.append(docGrid)

            pPr.append(sectPr)
            p_elem.append(pPr)

            # 添加分节符段落
            master_body.append(p_elem)

        # 10.5 把法律附录等内容添加回去
        for elem in elements_after_marker:
            master_body.append(elem)

        # 10.6 确保文档末尾有正确的 sectPr
        # 先删除 body.docx 带来的所有末尾 sectPr
        master_body = master.element.body
        while True:
            last_elem = list(master_body)[-1] if list(master_body) else None
            if last_elem is not None and last_elem.tag.split('}')[-1] == 'sectPr':
                master_body.remove(last_elem)
            else:
                break

        # 添加原来 template 的 sectPr
        if final_sectPr is not None:
            master_body.append(final_sectPr)

        # 11. 保存最终文档
        composer.save(output_path)

        # 12. 复制 body 的页眉页脚和页边距到 output
        # 注意：必须在保存后重新加载文档才能正确复制
        if body_doc:
            # 确保文件已完全写入
            import time
            time.sleep(0.1)

            # 重新加载文档
            final_doc = Document(output_path)
            body_doc_fresh = Document(body_path)

            # Body Section 结构：
            # - 可能只有 1 个 section，或者有多个 section
            # - 第一个 section 通常包含正文的页边距设置（如 6.35cm）
            #
            # Output Section 结构：
            # - Section 0: 封面（保持原样）
            # - Section 1 到倒数第二个: 正文（复制 body 的页边距和页眉）
            # - 最后一个 Section: 附录（保持 template 原样，不修改）
            if len(body_doc_fresh.sections) >= 1 and len(final_doc.sections) >= 2:
                # 使用 body 的第一个 section 作为页边距来源
                margin_source = body_doc_fresh.sections[0]  # 页边距（如 6.35cm）
                footer_source = body_doc_fresh.sections[0]  # 页脚

                # 如果 body 有多个 section，使用 Section 1 的 header（通常是蓝色）
                # 否则使用 Section 0 的 header
                if len(body_doc_fresh.sections) > 1:
                    header_source = body_doc_fresh.sections[1]
                else:
                    header_source = body_doc_fresh.sections[0]

                # 确定要更新的 section 范围
                # 如果有 3+ sections：Section 0=封面，Section 1~n-2=正文，Section n-1=附录
                # 如果只有 2 sections：Section 0=封面，Section 1=正文（也是最后一个）
                if len(final_doc.sections) > 2:
                    # 有附录，排除最后一个 section
                    sections_to_update = len(final_doc.sections) - 1
                else:
                    # 没有附录，更新所有非封面 section
                    sections_to_update = len(final_doc.sections)
                for target_idx in range(1, sections_to_update):
                    target_section = final_doc.sections[target_idx]

                    # 复制页边距（关键：保留 body.docx 的页边距）
                    target_section.left_margin = margin_source.left_margin
                    target_section.right_margin = margin_source.right_margin
                    target_section.top_margin = margin_source.top_margin
                    target_section.bottom_margin = margin_source.bottom_margin

                    # 复制设置
                    target_section.different_first_page_header_footer = header_source.different_first_page_header_footer

                    # 复制默认页眉
                    target_section.header.is_linked_to_previous = False
                    for child in list(target_section.header._element):
                        target_section.header._element.remove(child)
                    for child in header_source.header._element:
                        target_section.header._element.append(deepcopy(child))

                    # 复制默认页脚
                    target_section.footer.is_linked_to_previous = False
                    for child in list(target_section.footer._element):
                        target_section.footer._element.remove(child)
                    for child in footer_source.footer._element:
                        target_section.footer._element.append(deepcopy(child))

                    # 复制首页页眉
                    try:
                        target_section.first_page_header.is_linked_to_previous = False
                        for child in list(target_section.first_page_header._element):
                            target_section.first_page_header._element.remove(child)
                        for child in header_source.header._element:
                            target_section.first_page_header._element.append(deepcopy(child))
                    except Exception:
                        pass

                    # 复制首页页脚
                    try:
                        target_section.first_page_footer.is_linked_to_previous = False
                        for child in list(target_section.first_page_footer._element):
                            target_section.first_page_footer._element.remove(child)
                        for child in footer_source.footer._element:
                            target_section.first_page_footer._element.append(deepcopy(child))
                    except Exception:
                        pass

                final_doc.save(output_path)
                print(f"  已复制 body 页边距（左={margin_source.left_margin.cm:.2f}cm）和页眉页脚到 {sections_to_update - 1} 个正文 sections")

        # 12.5 清理 body 带来的 section breaks 和多余空段落（防止空白页）
        final_doc = Document(output_path)
        body_element = final_doc.element.body
        ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}

        elements = list(body_element)

        # 找到法律附录表格的位置（附录是 template 的内容，不应被修改）
        appendix_idx = len(elements)
        for i, elem in enumerate(elements):
            tag = elem.tag.split('}')[-1]
            if tag == 'tbl':
                texts = elem.findall('.//w:t', ns)
                text = ''.join([t.text or '' for t in texts])
                if '[Table_disclaimer]' in text or 'APPENDIX' in text or '附录' in text:
                    appendix_idx = i
                    break

        # 找到封面结束位置（第一个 sectPr 之后）
        cover_end_idx = 0
        for i, elem in enumerate(elements):
            tag = elem.tag.split('}')[-1]
            if tag == 'p':
                pPr = elem.find('w:pPr', ns)
                if pPr is not None and pPr.find('w:sectPr', ns) is not None:
                    cover_end_idx = i + 1
                    break

        # 只清理封面之后、附录之前的 body 区域的 sectPr
        # 不要删除附录之后的任何元素（包括文档末尾的 sectPr）
        # 保留附录前一个元素的 sectPr（用于隔离正文和附录）
        elements_to_remove = []
        sectPrs_removed = 0

        for i, elem in enumerate(elements):
            # 只处理封面之后、附录之前的元素
            # 排除 appendix_idx - 1（附录前一个元素，用于隔离）
            if i <= cover_end_idx or i >= appendix_idx - 1:
                continue

            tag = elem.tag.split('}')[-1]

            # 删除独立的 sectPr 元素（在 body 区域内）
            if tag == 'sectPr':
                elements_to_remove.append(elem)
                sectPrs_removed += 1

            # 移除段落内的 sectPr
            elif tag == 'p':
                pPr = elem.find('w:pPr', ns)
                if pPr is not None:
                    sectPr = pPr.find('w:sectPr', ns)
                    if sectPr is not None:
                        pPr.remove(sectPr)
                        sectPrs_removed += 1

        # 删除独立的 sectPr 元素
        for elem in elements_to_remove:
            body_element.remove(elem)

        # 重新获取元素列表（因为删除了一些元素）
        elements = list(body_element)

        # 重新找到附录位置
        appendix_idx = len(elements)
        for i, elem in enumerate(elements):
            tag = elem.tag.split('}')[-1]
            if tag == 'tbl':
                texts = elem.findall('.//w:t', ns)
                text = ''.join([t.text or '' for t in texts])
                if '[Table_disclaimer]' in text or 'APPENDIX' in text or '附录' in text:
                    appendix_idx = i
                    break

        # 清理附录前的多余空段落（保留最多 1 个）
        paragraphs_to_remove = []
        consecutive_empty = 0

        for i in range(cover_end_idx, appendix_idx):
            elem = elements[i]
            tag = elem.tag.split('}')[-1]
            if tag == 'p':
                texts = elem.findall('.//w:t', ns)
                text_content = ''.join([t.text or '' for t in texts]).strip()
                if not text_content:
                    consecutive_empty += 1
                    # 只保留 1 个连续空段落
                    if consecutive_empty > 1:
                        paragraphs_to_remove.append(elem)
                else:
                    consecutive_empty = 0
            else:
                consecutive_empty = 0

        # 删除多余的空段落
        for elem in paragraphs_to_remove:
            body_element.remove(elem)

        changes_made = len(paragraphs_to_remove) > 0 or sectPrs_removed > 0 or len(elements_to_remove) > 0
        if changes_made:
            final_doc.save(output_path)
            if paragraphs_to_remove:
                print(f"  已清理 {len(paragraphs_to_remove)} 个多余空段落")
            if sectPrs_removed > 0:
                print(f"  已移除 {sectPrs_removed} 个 body 带来的 section breaks")

        # 12.6 重新设置正文 sections 的页边距（因为步骤 12.5 可能修改了 section 结构）
        if body_doc:
            final_doc = Document(output_path)
            body_doc_fresh = Document(body_path)

            if len(body_doc_fresh.sections) >= 1 and len(final_doc.sections) >= 2:
                margin_source = body_doc_fresh.sections[0]

                # 确定正文 sections 的范围
                if len(final_doc.sections) > 2:
                    sections_to_update = len(final_doc.sections) - 1
                else:
                    sections_to_update = len(final_doc.sections)

                margins_updated = 0
                for target_idx in range(1, sections_to_update):
                    target_section = final_doc.sections[target_idx]
                    target_section.left_margin = margin_source.left_margin
                    target_section.right_margin = margin_source.right_margin
                    target_section.top_margin = margin_source.top_margin
                    target_section.bottom_margin = margin_source.bottom_margin
                    margins_updated += 1

                if margins_updated > 0:
                    final_doc.save(output_path)
                    print(f"  已重新设置 {margins_updated} 个正文 sections 的页边距（左={margin_source.left_margin.cm:.2f}cm）")

        # 13. 清理临时文件
        temp_path.unlink(missing_ok=True)
        temp_before_path.unlink(missing_ok=True)

        # 14. 验证输出
        final_doc = Document(output_path)
        image_count = sum(1 for rel in final_doc.part.rels.values() if 'image' in rel.reltype)
        print(f"  输出: 段落={len(final_doc.paragraphs)}, 表格={len(final_doc.tables)}, 图片={image_count}")

        return True

    except Exception as e:
        print(f"渲染失败: {e}")
        import traceback
        traceback.print_exc()
        return False
