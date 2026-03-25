"""splitter.py - 摘要/正文拆分模块。

使用 python-docx 从草稿中拆分摘要和正文片段。
"""

from typing import Dict, Any, List, Tuple
from pathlib import Path
import sys

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

import common


def extract_abstract(draft_path: str, scope: str) -> Path:
    """提取摘要片段。

    根据位置描述从草稿中提取摘要区域。

    Args:
        draft_path: 草稿文件路径
        scope: 位置描述（如"首页右侧"）

    Returns:
        abstract.docx 文件路径
    """
    if Document is None:
        return Path(common.FILE_ABSTRACT)
    
    try:
        doc = Document(draft_path)
        
        # 简化实现：提取首页的某些表格或段落
        # 实际应该根据 scope 解析位置，这里先做简单版本
        
        abstract_doc = Document()
        
        # 策略：提取首页的特定表格
        # 根据观察，摘要通常在首页的某个表格中
        if len(doc.tables) > 0:
            # 假设第一个表格包含摘要信息
            table = doc.tables[0]
            
            # 复制表格到新文档
            for row in table.rows:
                # 添加空段落
                abstract_doc.add_paragraph()
                
                # 复制行内容
                for cell in row.cells:
                    if cell.text:
                        abstract_doc.add_paragraph(cell.text)
        
        return Path(common.FILE_ABSTRACT)
    except Exception as e:
        print(f"提取摘要失败: {e}")
        return Path(common.FILE_ABSTRACT)


def extract_body(draft_path: str, scope: str) -> Path:
    """提取正文片段。

    从草稿中提取正文区域（排除首页和摘要）。

    Args:
        draft_path: 草稿文件路径
        scope: 位置描述（如"从第三页开始"）

    Returns:
        body.docx 文件路径
    """
    if Document is None:
        return Path(common.FILE_BODY)
    
    try:
        doc = Document(draft_path)
        
        # 简化实现：从第二页开始提取所有内容
        # 实际应该根据 scope 解析页面位置
        
        body_doc = Document()
        
        # 跳过首页，复制剩余内容
        # 这里简化处理：复制所有段落和表格
        
        # 复制段落（跳过首页部分）
        start_index = 20  # 跳过首页的大约段落数
        
        for i, para in enumerate(doc.paragraphs[start_index:], start=start_index):
            if para.text.strip():
                new_para = body_doc.add_paragraph(para.text)
                # 复制样式
                if para.style:
                    new_para.style = para.style
        
        # 复制表格（跳过首页的表格）
        start_table = 2  # 跳过首页的前 2 个表格
        
        for table in doc.tables[start_table:]:
            # 复制表格结构
            # 注意：完整复制表格比较复杂，这里做简化处理
            
            # 添加表格标题
            body_doc.add_paragraph(f"[表格: {len(table.rows)} 行 x {len(table.columns)} 列]")
            
            # 复制表格内容
            for row_idx, row in enumerate(table.rows):
                row_data = []
                for cell in row.cells:
                    row_data.append(cell.text)
                body_doc.add_paragraph(" | ".join(row_data))
        
        return Path(common.FILE_BODY)
    except Exception as e:
        print(f"提取正文失败: {e}")
        return Path(common.FILE_BODY)


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
    """复制段落到目标文档。

    Args:
        target_doc: 目标文档
        source_para: 源段落
    """
    new_para = target_doc.add_paragraph(source_para.text)

    # 复制样式
    if source_para.style:
        try:
            new_para.style = source_para.style
        except Exception:
            pass

    # 复制段落格式（粗体、斜体等）
    for run in source_para.runs:
        if run.text:
            new_run = new_para.add_run(run.text)
            if run.bold:
                new_run.bold = True
            if run.italic:
                new_run.italic = True
            if run.underline:
                new_run.underline = True


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

    return '\n'.join(instructions)
