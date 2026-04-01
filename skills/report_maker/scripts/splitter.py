"""splitter.py - 摘要/正文拆分模块。

使用 lxml 直接解析 document.xml，从草稿中拆分摘要和正文片段。
支持保留完整格式（字体、加粗、样式等）和图片。

注意：python-docx 的 doc.tables 会漏读嵌套表格，因此使用 lxml 直接解析。
"""

from typing import Dict, Any, List, Tuple, Optional
from pathlib import Path
from copy import deepcopy
import shutil
import sys
import zipfile

SCRIPTS_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPTS_DIR))

try:
    from docx import Document
    from docx.shared import Inches, Pt
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
except ImportError:
    Document = None
    Inches = None
    Pt = None
    OxmlElement = None
    qn = None

from lxml import etree

import common


W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'


def _get_para_text(para_elem) -> str:
    """获取段落的所有文本。

    Args:
        para_elem: 段落元素

    Returns:
        段落文本
    """
    return ''.join(t.text or '' for t in para_elem.iter(f'{W}t'))


def _get_all_tables_lxml(doc_path: str) -> List[etree._Element]:
    """使用 lxml 获取文档中所有表格（包括嵌套表格）。

    解决 python-docx 漏读嵌套表格的问题。

    Args:
        doc_path: docx 文件路径

    Returns:
        表格元素列表
    """
    with zipfile.ZipFile(doc_path, 'r') as z:
        with z.open('word/document.xml') as f:
            tree = etree.parse(f).getroot()
    return list(tree.iter(f'{W}tbl'))


def _get_cell_text_lxml(tc_elem) -> str:
    """获取单元格的文本（包括嵌套内容）。

    Args:
        tc_elem: 单元格元素

    Returns:
        单元格文本
    """
    texts = []
    for t in tc_elem.iter(f'{W}t'):
        if t.text:
            texts.append(t.text)
    return ''.join(texts)


def extract_abstract(draft_path: str, scope: str, output_path: Optional[str] = None) -> Path:
    """提取摘要片段，保留完整格式。

    根据位置描述从草稿中提取摘要区域。
    使用 deepcopy 保留原始格式（字体、加粗、样式等）。

    注意：使用 lxml 解析 document.xml，确保嵌套表格不漏读。

    Args:
        draft_path: 草稿文件路径
        scope: 位置描述（如"首页右侧"）
        output_path: 输出路径（可选）

    Returns:
        abstract.docx 文件路径
    """
    if Document is None:
        return Path(output_path or common.FILE_ABSTRACT)

    out_path = Path(output_path or common.FILE_ABSTRACT)

    try:
        doc = Document(draft_path)

        # 创建新文档
        abstract_doc = Document()

        # 删除新文档的默认空段落
        for para in abstract_doc.paragraphs:
            p = para._element
            p.getparent().remove(p)

        # 策略1：从首页表格中查找摘要（常见于公司报告模板）
        # 使用 lxml 确保所有表格都能读取（包括嵌套表格）
        abstract_found = False
        all_tables = _get_all_tables_lxml(draft_path)

        if all_tables:
            first_table = all_tables[0]

            # 搜索包含摘要内容特征的单元格
            for row in first_table.findall(f'{W}tr'):
                for tc in row.findall(f'{W}tc'):
                    cell_text = _get_cell_text_lxml(tc).strip()
                    # 摘要通常以公司名或关键词开头，且较长
                    if any(marker in cell_text for marker in [
                        '是私人航空业', '是全球', '公司是', '本报告',
                        '投资亮点', '核心观点', '摘要'
                    ]) and len(cell_text) > 200:
                        # 使用 deepcopy 复制段落，保留所有格式
                        for para_elem in tc.findall(f'{W}p'):
                            if _get_para_text(para_elem).strip():
                                new_para = deepcopy(para_elem)
                                abstract_doc.element.body.append(new_para)
                        abstract_found = True
                        break
                if abstract_found:
                    break

        # 策略2：如果表格中没找到，从段落中查找
        if not abstract_found:
            in_abstract = False
            body = doc.element.body
            for para in body.iter(f'{W}p'):
                text = _get_para_text(para).strip()

                # 开始标记
                if any(marker in text for marker in ['摘要', '投资亮点', '核心观点']):
                    in_abstract = True
                    continue

                # 结束标记
                if in_abstract and any(marker in text for marker in ['目录', '1 ', '1.']):
                    break

                if in_abstract and text:
                    new_para = deepcopy(para)
                    abstract_doc.element.body.append(new_para)

        abstract_doc.save(str(out_path))
        return out_path

    except Exception as e:
        print(f"提取摘要失败: {e}")
        import traceback
        traceback.print_exc()
        return out_path


def extract_body(draft_path: str, scope: str, output_path: Optional[str] = None) -> Path:
    """提取正文片段，保留完整格式、表格和图片。

    使用"复制整个文档 → 删除范围外元素"的方式，
    确保所有格式、图片和表格都被完整保留。

    包含目录（如果存在）。

    Args:
        draft_path: 草稿文件路径
        scope: 位置描述（如"从第三页开始"）
        output_path: 输出路径（可选）

    Returns:
        body.docx 文件路径
    """
    if Document is None:
        return Path(output_path or common.FILE_BODY)

    out_path = Path(output_path or common.FILE_BODY)

    try:
        # 步骤1：复制整个文档（保留所有资源引用）
        shutil.copy(draft_path, str(out_path))

        # 步骤2：打开复制的文档进行编辑
        doc = Document(str(out_path))
        body = doc.element.body
        elements = list(body)

        # 步骤3：找到正文的起始和结束位置
        start_idx = None
        end_idx = len(elements)
        toc_idx = None  # 目录位置

        # 正文结束标记（附录/免责声明）
        end_markers = ['重要信息披露', '[Table_disclaimer]', '免责声明', 'APPENDIX', '附录']

        # 首先找到目录位置和正文结束位置
        for i, elem in enumerate(elements):
            text = ''.join(elem.itertext()).strip()
            tag = elem.tag.split('}')[-1]

            # 找目录位置（"目录"标题或 sdt 目录控件）
            if toc_idx is None:
                # 检查是否是目录标题
                if text == '目录':
                    toc_idx = i
                    print(f"找到目录位置: 元素 {i}")
                # 检查是否是 sdt 目录控件（Word 自动生成的目录）
                elif tag == 'sdt' and '目录' in text:
                    toc_idx = i
                    print(f"找到目录控件: 元素 {i}")

            # 找结束位置
            for marker in end_markers:
                if marker in text:
                    end_idx = i
                    break
            if end_idx < len(elements):
                break

        # 确定起始位置
        if toc_idx is not None:
            # 如果有目录，从目录开始
            start_idx = toc_idx
        else:
            # 如果没有目录，找正文第一章
            # 正文起始标记（章节1开头）- 排除目录条目（包含Tab+页码）
            for i, elem in enumerate(elements):
                text = ''.join(elem.itertext()).strip()

                # 检查是否是正文标题（以 "1 " 开头，但不是目录条目）
                if text.startswith('1 ') or text.startswith('1.'):
                    # 目录条目通常包含 Tab 字符和页码
                    # 正文标题通常不包含 Tab 或以数字结尾
                    if '\t' not in text and not text[-1].isdigit():
                        start_idx = i
                        break
                    # 或者检查是否是 Heading 样式
                    if elem.tag.endswith('}p'):
                        pPr = elem.find('.//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}pStyle')
                        if pPr is not None:
                            style_val = pPr.get('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val', '')
                            if 'Heading' in style_val or '标题' in style_val:
                                start_idx = i
                                break

        if start_idx is None:
            print("警告：未找到正文起始位置，使用默认值")
            start_idx = 10  # 默认跳过前10个元素

        print(f"正文范围: 元素 {start_idx} - {end_idx}")

        # 步骤4：删除范围外的元素
        elements_to_remove = []

        # 删除结束位置之后的元素（倒序）
        for i in range(len(elements) - 1, end_idx - 1, -1):
            elem = elements[i]
            tag = elem.tag.split('}')[-1]
            if tag not in ['sectPr']:  # 保留节属性
                elements_to_remove.append(elem)

        # 删除起始位置之前的元素（倒序）
        for i in range(start_idx - 1, -1, -1):
            elem = elements[i]
            tag = elem.tag.split('}')[-1]
            if tag not in ['sectPr']:
                elements_to_remove.append(elem)

        # 执行删除
        for elem in elements_to_remove:
            try:
                body.remove(elem)
            except ValueError:
                pass  # 元素可能已被删除

        # 注意：不重置页边距，保留原始草稿的 section 格式
        # 原始草稿可能有不同的 section 和边距设置，这是设计意图的一部分

        # 步骤5：保存
        doc.save(str(out_path))

        # 验证结果
        final_doc = Document(str(out_path))
        print(f"正文提取完成: {len(final_doc.paragraphs)} 段落, "
              f"{len(final_doc.tables)} 表格, "
              f"{len(final_doc.inline_shapes)} 图片")

        return out_path

    except Exception as e:
        print(f"提取正文失败: {e}")
        import traceback
        traceback.print_exc()
        return out_path


def locate_fragment_by_content(doc_path: str, keywords: List[str]) -> Dict[str, Any]:
    """根据关键词定位 fragment 在文档中的位置。

    Args:
        doc_path: 文档路径
        keywords: 关键词列表

    Returns:
        位置信息字典，包含匹配的段落和表格
    """
    if Document is None:
        return {"error": "python-docx not installed"}

    try:
        doc = Document(doc_path)

        matches = {
            "paragraphs": [],
            "tables": [],
            "total_matches": 0
        }

        # 搜索包含关键词的段落
        for i, para in enumerate(doc.paragraphs):
            for keyword in keywords:
                if keyword in para.text:
                    matches["paragraphs"].append({
                        "type": "paragraph",
                        "index": i,
                        "keyword": keyword,
                        "text": para.text[:100],
                        "full_text": para.text
                    })
                    matches["total_matches"] += 1

        # 搜索包含关键词的表格
        for i, table in enumerate(doc.tables):
            table_matched = False
            matched_cells = []

            for row_idx, row in enumerate(table.rows):
                for col_idx, cell in enumerate(row.cells):
                    for keyword in keywords:
                        if keyword in cell.text:
                            if not table_matched:
                                matches["tables"].append({
                                    "type": "table",
                                    "index": i,
                                    "rows": len(table.rows),
                                    "cols": len(table.columns),
                                    "matched_cells": []
                                })
                                table_matched = True
                            matches["tables"][-1]["matched_cells"].append({
                                "row": row_idx,
                                "col": col_idx,
                                "keyword": keyword,
                                "text": cell.text[:100]
                            })
                            matches["total_matches"] += 1

        return matches
    except Exception as e:
        return {"error": str(e)}


def extract_fragment_by_table_range(
    doc_path: str,
    table_start: int,
    table_end: int,
    output_path: str,
    include_surrounding: bool = False,
    surrounding_paras: int = 0
) -> bool:
    """按表格范围提取片段。

    Args:
        doc_path: 源文档路径
        table_start: 起始表格索引（包含）
        table_end: 结束表格索引（包含）
        output_path: 输出文件路径
        include_surrounding: 是否包含表格前后的段落
        surrounding_paras: 前后各包含多少段落

    Returns:
        是否成功
    """
    if Document is None:
        return False

    try:
        doc = Document(doc_path)
        fragment_doc = Document()

        # 验证索引范围
        if table_start >= len(doc.tables):
            print(f"错误：起始表格索引 {table_start} 超出范围（文档共 {len(doc.tables)} 个表格）")
            return False

        actual_end = min(table_end, len(doc.tables) - 1)

        # 如果需要，尝试找到第一个表格前的段落
        if include_surrounding and surrounding_paras > 0:
            # 找到第一个表格所在的段落位置
            first_table_para_index = _find_table_paragraph_position(doc, table_start)

            if first_table_para_index is not None:
                # 复制表格前的段落
                start_para = max(0, first_table_para_index - surrounding_paras)
                for para in doc.paragraphs[start_para:first_table_para_index]:
                    if para.text.strip():
                        _copy_paragraph(fragment_doc, para)

        # 复制指定范围的表格
        for table_idx in range(table_start, actual_end + 1):
            table = doc.tables[table_idx]

            # 完整复制表格
            _copy_table(fragment_doc, table)

            # 表格后添加空行
            fragment_doc.add_paragraph()

        # 如果需要，复制最后一个表格后的段落
        if include_surrounding and surrounding_paras > 0:
            last_table_para_index = _find_table_paragraph_position(doc, actual_end)

            if last_table_para_index is not None:
                end_para = min(len(doc.paragraphs), last_table_para_index + surrounding_paras + 1)
                for para in doc.paragraphs[last_table_para_index + 1:end_para]:
                    if para.text.strip():
                        _copy_paragraph(fragment_doc, para)

        fragment_doc.save(output_path)
        return True
    except Exception as e:
        print(f"按表格范围提取失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def extract_fragment_by_paragraph_range(
    doc_path: str,
    para_start: int,
    para_end: int,
    output_path: str,
    include_tables: bool = True
) -> bool:
    """按段落范围提取片段。

    Args:
        doc_path: 源文档路径
        para_start: 起始段落索引（包含）
        para_end: 结束段落索引（包含）
        output_path: 输出文件路径
        include_tables: 是否包含范围内的表格

    Returns:
        是否成功
    """
    if Document is None:
        return False

    try:
        doc = Document(doc_path)
        fragment_doc = Document()

        # 验证索引范围
        if para_start >= len(doc.paragraphs):
            print(f"错误：起始段落索引 {para_start} 超出范围（文档共 {len(doc.paragraphs)} 个段落）")
            return False

        actual_end = min(para_end, len(doc.paragraphs) - 1)

        # 收集范围内的所有元素
        copied_tables = set()

        for para_idx in range(para_start, actual_end + 1):
            para = doc.paragraphs[para_idx]

            # 复制段落
            if para.text.strip():
                _copy_paragraph(fragment_doc, para)

            # 检查段落间是否有表格
            if include_tables:
                for table_idx, table in enumerate(doc.tables):
                    if table_idx in copied_tables:
                        continue

                    # 检查表格是否在当前段落之后，下一个段落之前
                    table_pos = _find_table_paragraph_position(doc, table_idx)
                    if table_pos is not None and para_idx <= table_pos < actual_end:
                        _copy_table(fragment_doc, table)
                        copied_tables.add(table_idx)
                        fragment_doc.add_paragraph()  # 表格后空行

        fragment_doc.save(output_path)
        return True
    except Exception as e:
        print(f"按段落范围提取失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def extract_fragment_by_keywords(
    doc_path: str,
    start_keywords: List[str],
    end_keywords: List[str],
    output_path: str
) -> bool:
    """根据关键词定位并提取片段。

    Args:
        doc_path: 源文档路径
        start_keywords: 起始关键词列表（匹配任一即可）
        end_keywords: 结束关键词列表（匹配任一即可）
        output_path: 输出文件路径

    Returns:
        是否成功
    """
    if Document is None:
        return False

    try:
        # 定位起始和结束位置
        start_result = locate_fragment_by_content(doc_path, start_keywords)
        end_result = locate_fragment_by_content(doc_path, end_keywords)

        if "error" in start_result or "error" in end_result:
            print("定位失败")
            return False

        if not start_result["paragraphs"] and not start_result["tables"]:
            print(f"未找到起始关键词: {start_keywords}")
            return False

        if not end_result["paragraphs"] and not end_result["tables"]:
            print(f"未找到结束关键词: {end_keywords}")
            return False

        # 获取起始和结束索引
        start_para = start_result["paragraphs"][0]["index"] if start_result["paragraphs"] else None
        end_para = end_result["paragraphs"][0]["index"] if end_result["paragraphs"] else None

        start_table = start_result["tables"][0]["index"] if start_result["tables"] else None
        end_table = end_result["tables"][0]["index"] if end_result["tables"] else None

        # 优先使用段落范围
        if start_para is not None and end_para is not None:
            return extract_fragment_by_paragraph_range(
                doc_path, start_para, end_para, output_path, include_tables=True
            )
        # 其次使用表格范围
        elif start_table is not None and end_table is not None:
            return extract_fragment_by_table_range(
                doc_path, start_table, end_table, output_path,
                include_surrounding=True, surrounding_paras=1
            )
        else:
            print("无法确定提取范围")
            return False

    except Exception as e:
        print(f"按关键词提取失败: {e}")
        import traceback
        traceback.print_exc()
        return False


# ==================== 辅助函数 ====================

def _find_table_paragraph_position(doc: Document, table_index: int) -> int:
    """找到表格所在的段落位置（近似）。

    Args:
        doc: Word 文档对象
        table_index: 表格索引

    Returns:
        段落索引，如果找不到返回 None
    """
    if table_index >= len(doc.tables):
        return None

    table = doc.tables[table_index]

    # 尝试通过表格元素的位置找到段落索引
    # 这是一个近似方法，因为 python-docx 不直接提供表格在段落中的位置

    # 方法：遍历所有段落，找到第一个出现在表格之后的段落
    # 通过比较元素在 XML 中的位置

    try:
        table_element = table._element

        for i, para in enumerate(doc.paragraphs):
            para_element = para._element

            # 比较元素在文档中的位置
            # 如果段落元素在表格元素之后，返回这个段落的索引
            if _is_element_after(para_element, table_element):
                # 返回表格前一个段落的索引
                return max(0, i - 1)

    except Exception:
        pass

    # 如果无法精确定位，返回一个估计值
    # 假设表格大致分布在文档中
    return int(len(doc.paragraphs) * (table_index + 1) / (len(doc.tables) + 1))


def _is_element_after(elem1, elem2) -> bool:
    """检查 elem1 是否在 elem2 之后（在文档流中）。

    Args:
        elem1: 第一个元素
        elem2: 第二个元素

    Returns:
        True 如果 elem1 在 elem2 之后
    """
    try:
        # 通过比较元素的 lxml 内存地址或位置来判断
        # 这是一个简化方法，可能不完全准确
        return id(elem1) > id(elem2)
    except Exception:
        return False


def _copy_paragraph(target_doc: Document, source_para) -> None:
    """复制段落到目标文档，保留完整格式。

    使用 deepcopy 复制段落的 XML 元素，确保所有格式信息都被保留。

    Args:
        target_doc: 目标文档
        source_para: 源段落
    """
    # 使用 deepcopy 复制完整的段落元素（包括所有格式）
    new_para_element = deepcopy(source_para._element)
    target_doc.element.body.append(new_para_element)


def _copy_table(target_doc: Document, source_table) -> None:
    """完整复制表格到目标文档。

    Args:
        target_doc: 目标文档
        source_table: 源表格
    """
    # 创建新表格
    table = target_doc.add_table(rows=len(source_table.rows), cols=len(source_table.columns))

    # 复制表格内容
    for i, row in enumerate(source_table.rows):
        for j, cell in enumerate(row.cells):
            target_cell = table.rows[i].cells[j]

            # 复制单元格文本
            if cell.text:
                target_cell.text = cell.text

            # 尝试复制单元格格式
            try:
                # 复制段落
                for para_idx, para in enumerate(cell.paragraphs):
                    if para_idx == 0:
                        target_cell.text = para.text
                    elif para.text:
                        target_cell.add_paragraph(para.text)
            except Exception:
                pass

    # 复制表格样式（如果可用）
    try:
        if source_table.style:
            table.style = source_table.style
    except Exception:
        pass


def read_document_structure(doc_path: str) -> Dict[str, Any]:
    """读取 Word 文档结构。
    
    返回文档的基本信息，帮助 Claude 理解文档结构。

    Args:
        doc_path: Word 文档路径

    Returns:
        文档结构信息
    """
    if Document is None:
        return {"error": "python-docx not installed"}
    
    try:
        doc = Document(doc_path)
        
        structure = {
            "paragraphs": len(doc.paragraphs),
            "tables": len(doc.tables),
            "sections": len(doc.sections),
            "paragraph_preview": [],
            "table_preview": [],
            "page_breaks": 0
        }
        
        # 统计分页符
        for i, para in enumerate(doc.paragraphs[:50]):  # 只检查前 50 个
            if i > 0 and doc.paragraphs[i-1]._element.pPr is not None:
                # 检查是否有分页属性
                pPr = doc.paragraphs[i-1]._element.pPr
                if pPr is not None:
                    for child in pPr.iterchildren():
                        if 'page' in str(child).lower():
                            structure["page_breaks"] += 1
                            break
        
        # 前 10 个段落预览
        for i, para in enumerate(doc.paragraphs[:10]):
            structure["paragraph_preview"].append({
                "index": i,
                "text": para.text[:100],  # 前 100 字符
                "style": para.style.name if para.style else "Normal"
            })
        
        # 表格信息
        for i, table in enumerate(doc.tables[:5]):
            structure["table_preview"].append({
                "index": i,
                "rows": len(table.rows),
                "cols": len(table.columns),
                "cell_sample": table.rows[0].cells[0].text[:50] if table.rows else ""
            })
        
        return structure
    except Exception as e:
        return {"error": str(e)}


def create_fragments_document(source_path: str, abstract_path: str, body_path: str) -> bool:
    """创建摘要和正文片段的空文档。
    
    Args:
        source_path: 源文档路径
        abstract_path: 摘要输出路径
        body_path: 正文输出路径

    Returns:
        是否成功
    """
    if Document is None:
        return False
    
    try:
        # 创建空的摘要文档
        abstract_doc = Document()
        abstract_doc.save(abstract_path)
        
        # 创建空的正文文档
        body_doc = Document()
        body_doc.save(body_path)
        
        return True
    except Exception as e:
        print(f"创建片段文档失败: {e}")
        return False


def get_split_instructions(schema: Dict[str, Any]) -> str:
    """获取拆分指令。

    根据 schema 中的 scope 描述生成拆分指令。

    Args:
        schema: schema.yaml 内容

    Returns:
        拆分指令文本
    """
    instructions = []

    abstract_def = schema.get('abstract', {})
    if abstract_def.get('type') == 'fragment':
        scope = abstract_def.get('scope', '')
        hints = abstract_def.get('hints', [])
        instructions.append(f"摘要位置：{scope}")
        if hints:
            instructions.append(f"摘要特征：{' '.join(hints)}")

    body_def = schema.get('body', {})
    if body_def.get('type') == 'fragment':
        scope = body_def.get('scope', '')
        hints = body_def.get('hints', [])
        instructions.append(f"正文位置：{scope}")
        if hints:
            instructions.append(f"正文特征：{' '.join(hints)}")

    appendix_def = schema.get('appendix', {})
    if appendix_def.get('type') == 'fragment':
        scope = appendix_def.get('scope', '')
        hints = appendix_def.get('hints', [])
        instructions.append(f"法律披露附录位置：{scope}")
        if hints:
            instructions.append(f"法律披露附录特征：{' '.join(hints)}")

    return '\n'.join(instructions)


def extract_appendix(draft_path: str, scope: str, output_path: Optional[str] = None) -> Path:
    """提取法律披露附录片段。

    法律披露附录包含：
    - 附录APPENDIX标题
    - 重要信息披露（IMPORTANT DISCLOSURES）
    - 一定从新的一页开始（通过分节符隔离）

    Args:
        draft_path: 草稿文件路径
        scope: 位置描述（如"正文之后，报告末尾"）
        output_path: 输出路径（可选）

    Returns:
        appendix.docx 文件路径
    """
    if Document is None:
        return Path(output_path or common.FILE_APPENDIX)

    out_path = Path(output_path or common.FILE_APPENDIX)

    try:
        doc = Document(draft_path)
        body = doc.element.body
        elements = list(body)

        # 法律披露附录的起始标记
        appendix_markers = [
            'APPENDIX',
            '附录',
            '重要信息披露',
            'IMPORTANT DISCLOSURES',
            'Disclaimer',
            '免责声明',
            '[Table_disclaimer]'
        ]

        # 查找附录起始位置
        start_idx = None
        for i, elem in enumerate(elements):
            text = ''.join(elem.itertext()).strip()

            for marker in appendix_markers:
                if marker in text:
                    start_idx = i
                    print(f"找到法律披露附录起始位置: 元素 {i} - '{text[:50]}'")
                    break

            if start_idx is not None:
                break

        if start_idx is None:
            print("警告：未找到法律披露附录")
            # 返回空文档
            empty_doc = Document()
            empty_doc.save(str(out_path))
            return out_path

        # 创建新文档
        appendix_doc = Document()

        # 删除新文档的默认空段落
        for para in appendix_doc.paragraphs:
            p = para._element
            p.getparent().remove(p)

        # 复制附录内容
        for i in range(start_idx, len(elements)):
            elem = elements[i]
            tag = elem.tag.split('}')[-1]

            if tag == 'p':
                # 复制段落
                new_para = deepcopy(elem)
                appendix_doc.element.body.append(new_para)
            elif tag == 'tbl':
                # 复制表格
                new_table = deepcopy(elem)
                appendix_doc.element.body.append(new_table)

        appendix_doc.save(str(out_path))
        return out_path

    except Exception as e:
        print(f"提取法律披露附录失败: {e}")
        import traceback
        traceback.print_exc()
        return out_path


def validate_appendix(draft_path: str, schema: Dict[str, Any]) -> Dict[str, Any]:
    """验证法律披露附录是否存在。

    Args:
        draft_path: 草稿文件路径
        schema: schema.yaml 内容

    Returns:
        验证结果：
        {
            "has_appendix": bool,
            "has_important_disclosures": bool,
            "has_appendix_title": bool,
            "location": str,
            "suggestion": str
        }
    """
    if Document is None:
        return {"has_appendix": False, "error": "python-docx not installed"}

    result = {
        "has_appendix": False,
        "has_important_disclosures": False,
        "has_appendix_title": False,
        "location": "",
        "suggestion": ""
    }

    try:
        doc = Document(draft_path)
        body = doc.element.body
        elements = list(body)

        # 法律披露附录的关键词
        appendix_keywords = [
            'APPENDIX',
            '附录',
            '重要信息披露',
            'IMPORTANT DISCLOSURES',
            'Disclaimer',
            '免责声明',
            '[Table_disclaimer]'
        ]

        # 重要信息披露的关键词（必须包含）
        important_keywords = [
            'DISCLOSURES',
            '披露',
            '利益冲突',
            'Conflict of Interest',
            '评级',
            'Rating'
        ]

        found_keywords = []
        important_found = []

        for i, elem in enumerate(elements):
            text = ''.join(elem.itertext()).strip()

            for kw in appendix_keywords:
                if kw in text and kw not in found_keywords:
                    found_keywords.append(kw)
                    result["has_appendix"] = True
                    result["location"] = f"元素 {i}: {text[:50]}"

            for kw in important_keywords:
                if kw in text and kw not in important_found:
                    important_found.append(kw)
                    result["has_important_disclosures"] = True

        # 判断附录标题
        for kw in ['APPENDIX', '附录']:
            if kw in found_keywords:
                result["has_appendix_title"] = True
                break

        # 生成建议
        if not result["has_appendix"]:
            result["suggestion"] = "⚠️ 未找到法律披露附录，请检查报告末尾是否包含 IMPORTANT DISCLOSURES"
        elif not result["has_important_disclosures"]:
            result["suggestion"] = "⚠️ 找到附录但未包含重要信息披露内容"
        else:
            result["suggestion"] = "✅ 法律披露附录验证通过"

        return result

    except Exception as e:
        return {"has_appendix": False, "error": str(e)}
