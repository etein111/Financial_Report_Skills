"""文档分析函数。

用于分析 Word 文档结构、定位内容、获取段落和表格信息。
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Any
from docx import Document
import re


def find_content_location(doc_path: str, search_text: str) -> Dict[str, Any]:
    """在文档中查找指定文本的位置。

    由于合并单元格问题，直接从 XML 中搜索。

    Args:
        doc_path: Word 文档路径
        search_text: 要搜索的文本

    Returns:
        位置信息：
        {
            "found": bool,
            "type": str,             # "table" 或 "paragraph"
            "table": int,
            "row": int,
            "col": int,
            "index": int,
            "context": str
        }
    """
    doc = Document(doc_path)
    body_xml = doc.element.body.xml

    # 从 XML 中搜索
    if search_text in body_xml:
        # 判断在表格还是段落中
        # 找到该文本最近的上下文
        text_pos = body_xml.find(search_text)

        # 找到前一个 <w:tc> 或 <w:p> 标签
        tc_pos = body_xml.rfind('<w:tc>', 0, text_pos)
        p_pos = body_xml.rfind('<w:p ', 0, text_pos)

        if tc_pos > p_pos:
            # 在表格中
            # 找到所属表格
            tbl_start = body_xml.rfind('<w:tbl>', 0, tc_pos)
            tbl_end = body_xml.find('</w:tbl>', tc_pos)

            # 计算表格索引
            tbl_count = body_xml[:tbl_start].count('<w:tbl>')

            # 计算行号和列号
            tbl_xml = body_xml[tbl_start:tbl_end]
            relative_pos = tc_pos - tbl_start

            row_idx = tbl_xml[:relative_pos].count('<w:tr ')
            row_start = tbl_xml.rfind('<w:tr ', 0, relative_pos)
            row_end = tbl_xml.find('</w:tr>', relative_pos)
            row_xml = tbl_xml[row_start:row_end]
            col_idx = row_xml[:relative_pos - row_start].count('<w:tc>')

            return {
                "found": True,
                "type": "table",
                "table": tbl_count,
                "row": row_idx,
                "col": col_idx,
                "context": f"在表格 {tbl_count} 的第 {row_idx} 行第 {col_idx} 列"
            }
        else:
            # 在段落中
            para_count = body_xml[:p_pos].count('<w:p ')
            return {
                "found": True,
                "type": "paragraph",
                "index": para_count,
                "context": f"在段落 {para_count}"
            }

    return {"found": False, "context": "未找到"}


def find_long_text_in_table_from_xml(body_xml: str, table_start: int, table_end: int, min_length: int = 50) -> Dict[str, Any]:
    """从 XML 中查找表格内的长文本（摘要）。

    策略：找到所有超过 min_length 的文本，返回最长的那个（通常是摘要）。

    Args:
        body_xml: 文档 XML
        table_start: 表格开始位置
        table_end: 表格结束位置
        min_length: 最小文本长度

    Returns:
        位置信息
    """
    tbl_xml = body_xml[table_start:table_end]

    # 解析每一行每一列（包括嵌套表格）
    row_pattern = r'<w:tr [^>]*>(.*?)</w:tr>'
    rows = list(re.finditer(row_pattern, tbl_xml, re.DOTALL))

    # 收集所有长文本候选
    candidates = []

    for row_idx, row_match in enumerate(rows):
        row_xml = row_match.group(0)
        cell_pattern = r'<w:tc>(.*?)</w:tc>'
        cells = list(re.finditer(cell_pattern, row_xml, re.DOTALL))

        for col_idx, cell_match in enumerate(cells):
            cell_xml = cell_match.group(0)

            # 提取直接文本（不包含嵌套表格）
            texts = re.findall(r'<w:t[^>]*>([^<]*)</w:t>', cell_xml)
            full_text = ''.join(texts).strip()

            # 也检查嵌套表格中的文本
            nested_texts = []
            nested_pattern = r'<w:t[^>]*>([^<]*)</w:t>'
            # 查找嵌套表格
            nested_tables = re.findall(r'<w:tbl>(.*?)</w:tbl>', cell_xml, re.DOTALL)
            for nested_tbl in nested_tables:
                nested_texts.extend(re.findall(nested_pattern, nested_tbl))
            nested_full_text = ''.join(nested_texts).strip()

            # 合并文本
            combined_text = full_text + nested_full_text

            if len(combined_text) > min_length:
                candidates.append({
                    "row": row_idx,
                    "col_start": col_idx,
                    "col_end": col_idx,
                    "text": combined_text,
                    "length": len(combined_text)
                })

    if not candidates:
        return {"found": False}

    # 选择最长的文本（通常是摘要）
    best = max(candidates, key=lambda x: x["length"])
    return {
        "found": True,
        "row": best["row"],
        "col_start": best["col_start"],
        "col_end": best["col_end"],
        "preview": best["text"][:100],
        "text": best["text"]
    }


def find_abstract_on_first_page(doc: Document, abstract_scope: str) -> Dict[str, Any]:
    """根据 abstract_scope 在首页查找摘要位置。

    策略：
    1. 找到第一个表格之后的段落
    2. 提取从表格后到分节符之前的所有段落作为摘要
    3. 如果没有分节符，提取到文档末尾或附录之前

    Args:
        doc: Document 对象
        abstract_scope: 摘要位置描述（如"首页"、"首页右侧"等）

    Returns:
        摘要位置信息
    """
    paragraphs = doc.paragraphs
    body = doc.element.body
    body_elements = list(body)

    # 找到第一个表格的位置
    first_table = doc.tables[0] if doc.tables else None
    if not first_table:
        return {"found": False, "reason": "未找到表格"}

    tbl_element = first_table._element
    tbl_index = body_elements.index(tbl_element)

    # 找到表格后的第一个段落索引
    start_para_idx = -1
    for i, p in enumerate(paragraphs):
        # 检查段落是否在表格之后
        try:
            p_index = body_elements.index(p._element)
            if p_index > tbl_index:
                start_para_idx = i
                print(f"[DEBUG] 表格后第一个段落: 索引={i}, 内容前50字='{p.text[:50] if p.text else '(空)'}'")
                break
        except ValueError:
            continue

    if start_para_idx < 0:
        return {"found": False, "reason": "表格后未找到段落"}

    # 查找分节符位置（摘要结束标志）
    end_para_idx = len(paragraphs)
    for i in range(start_para_idx, len(paragraphs)):
        p = paragraphs[i]
        # 检查是否有分节符
        pPr = p._element.pPr
        if pPr is not None:
            sectPr = pPr.find('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}sectPr')
            if sectPr is not None:
                end_para_idx = i + 1  # 包含分节符所在段落
                print(f"[DEBUG] 找到分节符: 段落索引={i}")
                break
        # 检查是否是附录标志
        text = p.text.strip()
        if '信息披露' in text or 'Disclosure' in text or '免责声明' in text:
            end_para_idx = i
            print(f"[DEBUG] 找到附录标志: 段落索引={i}, 内容='{text[:30]}'")
            break

    print(f"[DEBUG] 摘要段落范围: {start_para_idx} 到 {end_para_idx}")

    # 提取摘要文本
    abstract_paragraphs = []
    for i in range(start_para_idx, end_para_idx):
        text = paragraphs[i].text.strip()
        if text:  # 跳过空段落
            abstract_paragraphs.append(text)

    abstract_text = '\n'.join(abstract_paragraphs)

    if not abstract_text:
        return {"found": False, "reason": "未找到摘要内容"}

    return {
        "found": True,
        "type": "paragraphs",
        "start_paragraph": start_para_idx,
        "end_paragraph": end_para_idx,
        "table": -1,
        "row": start_para_idx,
        "col_start": end_para_idx - 1,
        "col_end": -1,
        "preview": abstract_text[:100],
        "text": abstract_text,
        "context": f"表格后段落（段落 {start_para_idx} 到 {end_para_idx - 1}，共 {end_para_idx - start_para_idx} 段）"
    }


def find_abstract_by_elements(doc_path: str, elements: Dict[str, Any]) -> Dict[str, Any]:
    """根据 elements.yaml 的字段值定位摘要位置。

    策略：
    1. 使用 title_ch/title_en/theme_ch/theme_en 等常见标题字段定位
    2. 在该表格中查找长文本（摘要）

    由于合并单元格问题，直接从 XML 中搜索。

    Args:
        doc_path: Word 文档路径
        elements: elements.yaml 的内容

    Returns:
        摘要位置信息
    """
    doc = Document(doc_path)

    # 优先使用 title_ch/title_en 等字段
    search_value = None
    for field_name in ['title_ch', 'title_en', 'theme_ch', 'theme_en', 'company', 'title', 'ticker']:
        if field_name in elements and elements[field_name]:
            search_value = str(elements[field_name])
            break

    if not search_value:
        # 回退到第一个非分析师字段
        for k, v in elements.items():
            if v and not k.startswith('a') and not k.startswith('analyst') and k not in ['sections', 'appendix', 'analysts']:
                search_value = str(v)
                break

    if not search_value:
        return {"found": False, "reason": "未找到可用的定位字段"}

    # 从 XML 中搜索
    body_xml = doc.element.body.xml
    if search_value not in body_xml:
        return {"found": False, "reason": "未找到字段值"}

    # 找到该文本所在的位置
    text_pos = body_xml.find(search_value)
    tc_pos = body_xml.rfind('<w:tc>', 0, text_pos)
    tbl_start = body_xml.rfind('<w:tbl>', 0, tc_pos)
    tbl_end = body_xml.find('</w:tbl>', tc_pos) + 8

    # 计算表格索引
    tbl_count = body_xml[:tbl_start].count('<w:tbl>')

    # 在该表格中查找长文本
    long_text_info = find_long_text_in_table_from_xml(body_xml, tbl_start, tbl_end)

    if long_text_info.get("found"):
        return {
            "found": True,
            "table": tbl_count,
            "row": long_text_info["row"],
            "col_start": long_text_info["col_start"],
            "col_end": long_text_info["col_end"],
            "preview": long_text_info["preview"],
            "text": long_text_info.get("text", ""),
            "context": f"在表格 {tbl_count} 第 {long_text_info['row']} 行，列 {long_text_info['col_start']}-{long_text_info['col_end']}"
        }

    return {"found": False, "reason": "表格中未找到长文本"}


def get_document_structure(doc_path: str) -> Dict[str, Any]:
    """获取文档结构信息。

    Args:
        doc_path: Word 文档路径

    Returns:
        文档结构：
        {
            "paragraphs_count": int,
            "tables_count": int,
            "sections": List[int],
            "tables": List[Dict],
        }
    """
    doc = Document(doc_path)

    # 检测分节边界
    section_boundaries = _detect_section_boundaries(doc)

    # 获取表格信息
    tables_info = []
    for table_idx, table in enumerate(doc.tables):
        tables_info.append({
            "index": table_idx,
            "rows": len(table.rows),
            "cols": len(table.columns)
        })

    return {
        "paragraphs_count": len(doc.paragraphs),
        "tables_count": len(doc.tables),
        "sections": section_boundaries,
        "tables": tables_info
    }


def get_table_content(doc_path: str, table_idx: int, max_rows: int = 5) -> Dict[str, Any]:
    """获取指定表格的内容。

    Args:
        doc_path: Word 文档路径
        table_idx: 表格索引
        max_rows: 最多返回几行内容

    Returns:
        表格内容：
        {
            "index": int,
            "rows": int,
            "cols": int,
            "content": List[List[str]]
        }
    """
    doc = Document(doc_path)
    table = doc.tables[table_idx]

    content = []
    for row_idx, row in enumerate(table.rows[:max_rows]):
        row_content = []
        for cell in row.cells:
            row_content.append(cell.text.strip()[:50])
        content.append(row_content)

    return {
        "index": table_idx,
        "rows": len(table.rows),
        "cols": len(table.columns),
        "content": content
    }


def get_paragraphs_content(doc_path: str, start: int, end: int) -> List[str]:
    """获取指定段落范围的内容。

    Args:
        doc_path: Word 文档路径
        start: 起始段落索引
        end: 结束段落索引（不包含）

    Returns:
        段落文本列表
    """
    doc = Document(doc_path)
    contents = []

    for i in range(start, min(end, len(doc.paragraphs))):
        text = doc.paragraphs[i].text.strip()
        contents.append(f"段落 {i}: {text[:100]}")

    return contents




def find_body_range_by_sections(doc_path: str, body_scope: str = None) -> Dict[str, Any]:
    """根据分节结构定位正文范围（包含目录）。

    策略：
    - 如果 body_scope 包含"第二页"，则从分节 1 开始
    - 否则使用默认逻辑：分节 0=首页，分节 1=正文

    Args:
        doc_path: Word 文档路径
        body_scope: 正文位置描述（如"从第二页开始"）

    Returns:
        正文范围信息
    """
    doc = Document(doc_path)
    section_paragraphs = _get_section_paragraphs(doc)

    # 如果有多个分节
    if len(section_paragraphs) >= 2:
        # 检查 body_scope
        if body_scope and "第二页" in body_scope:
            # 正文从分节 1 开始
            if 1 in section_paragraphs and section_paragraphs[1]:
                start_idx = section_paragraphs[1][0]
            else:
                start_idx = 0
        else:
            # 默认：分节 0=首页，分节 1=正文
            if 1 in section_paragraphs and section_paragraphs[1]:
                start_idx = section_paragraphs[1][0]
            elif 0 in section_paragraphs and section_paragraphs[0]:
                start_idx = section_paragraphs[0][0]
            else:
                start_idx = 0
    elif len(section_paragraphs) == 1:
        # 只有一个分节，正文从首页之后开始
        if section_paragraphs.get(0):
            start_idx = section_paragraphs[0][0]
        else:
            start_idx = 0
    else:
        return {
            "found": False,
            "reason": f"分节数量不足（{len(section_paragraphs)} 个）"
        }

    # 正文结束位置
    end_idx = len(doc.paragraphs)

    # 如果有分节 3（附录），正文在分节 3 开始之前结束
    if 3 in section_paragraphs and section_paragraphs[3]:
        end_idx = section_paragraphs[3][0]
    elif 2 in section_paragraphs and section_paragraphs[2]:
        # flash 报告：分节 2 可能是附录
        end_idx = section_paragraphs[2][0]

    return {
        "found": True,
        "start_paragraph": start_idx,
        "end_paragraph": end_idx,
        "paragraphs_count": end_idx - start_idx,
        "context": f"段落 {start_idx} 到 {end_idx}，共 {end_idx - start_idx} 个段落"
    }


def find_elements_yaml(word_path: Path | str) -> Path | None:
    """查找与 Word 文件配对的 elements.yaml。

    Args:
        word_path: Word 文件路径（Path 或 str）

    Returns:
        找到的 elements.yaml 路径，未找到返回 None
    """
    word_path = Path(word_path) if isinstance(word_path, str) else word_path
    word_dir = word_path.parent
    word_name = word_path.stem

    candidates = [
        word_dir / f"{word_name} elements.yaml",
        word_dir / f"{word_name}_elements.yaml",
        word_dir / "elements.yaml",
    ]

    for candidate in candidates:
        if candidate.exists():
            return candidate

    return None


def find_appendix_auto(doc_path: str, elements: Dict[str, Any]) -> Dict[str, Any]:
    """自动检测附录位置。

    策略：
    1. 查找 "APPENDIX" 或 "附录" 作为独立标题的段落（而不是在其他内容中）
    2. 优先选择文档后半部分的标记（真正的附录通常在文档末尾附近）
    3. 附录延伸到文档末尾或下一个分节符

    Args:
        doc_path: Word 文档路径
        elements: elements.yaml 内容

    Returns:
        附录位置信息
    """
    doc = Document(doc_path)

    # 查找附录标记 - 更严格的匹配
    # 真正的附录标记应该是单独的标题，如 "APPENDIX 1"、"附录" 等
    # 而不是 "Please see APPENDIX 1" 这种引用形式
    appendix_markers = ['APPENDIX', '附录', '信息披露', 'Disclosure']

    candidates = []  # 存储所有找到的候选位置

    for i, p in enumerate(doc.paragraphs):
        text = p.text.strip()
        # 跳过太短的段落（可能是引用形式）
        if len(text) < 3:
            continue
        for marker in appendix_markers:
            if text == marker or text.startswith(marker + ' ') or text.startswith(marker + '\n'):
                # 找到独立标题形式的附录标记
                candidates.append({
                    "para_idx": i,
                    "marker": marker,
                    "text": text
                })
                print(f"[DEBUG] 找到附录候选 at 段落 {i}: '{text[:30]}'")
                break

    if not candidates:
        return {"found": False, "reason": "未找到附录标记（APPENDIX/附录/Summary）"}

    # 选择最后一个候选（通常真正的附录在文档末尾）
    # 或者选择文档后半部分的第一个候选
    mid_point = len(doc.paragraphs) // 2
    best_candidate = None

    for c in candidates:
        if c["para_idx"] >= mid_point:
            best_candidate = c
            break

    if best_candidate is None:
        # 如果后半部分没有，选择最后一个
        best_candidate = candidates[-1]

    start_para_idx = best_candidate["para_idx"]
    marker_found = best_candidate["marker"]

    print(f"[DEBUG] 选择附录标记 at 段落 {start_para_idx}: '{best_candidate['text'][:30]}'")

    # 附录延伸到文档末尾
    end_para_idx = len(doc.paragraphs)

    # 检查是否有分节符在附录之后（附录通常在新的一页开始）
    for i in range(start_para_idx, len(doc.paragraphs)):
        p = doc.paragraphs[i]
        pPr = p._element.pPr
        if pPr is not None:
            sectPr = pPr.find('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}sectPr')
            if sectPr is not None:
                end_para_idx = i + 1
                print(f"[DEBUG] 找到分节符 at 段落 {i}")
                break

    # 提取附录文本
    appendix_texts = []
    for i in range(start_para_idx, end_para_idx):
        text = doc.paragraphs[i].text.strip()
        if text:
            appendix_texts.append(text)

    appendix_text = '\n'.join(appendix_texts)

    return {
        "found": True,
        "type": "paragraphs",
        "start_paragraph": start_para_idx,
        "end_paragraph": end_para_idx,
        "marker": marker_found,
        "text": appendix_text,
        "preview": appendix_text[:100] if len(appendix_text) > 100 else appendix_text,
        "context": f"段落 {start_para_idx} 到 {end_para_idx}（标记：{marker_found}）"
    }


# 辅助函数

def _detect_section_boundaries(doc: Document) -> List[int]:
    """检测所有分节边界的段落索引。

    分节边界是段落属性中包含 sectPr 的段落。
    """
    section_boundaries = []

    for i, paragraph in enumerate(doc.paragraphs):
        pPr = paragraph._element.pPr
        if pPr is not None:
            sectPr = pPr.find('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}sectPr')
            if sectPr is not None:
                section_boundaries.append(i)

    return section_boundaries


def _get_section_paragraphs(doc: Document) -> Dict[int, List[int]]:
    """获取每个分节包含的段落索引范围。

    Returns:
        字典，键为分节索引，值为段落索引列表
    """
    section_boundaries = _detect_section_boundaries(doc)

    section_paragraphs = {}
    current_section = 0

    for i in range(len(doc.paragraphs)):
        if i in section_boundaries:
            if current_section not in section_paragraphs:
                section_paragraphs[current_section] = []
            section_paragraphs[current_section].append(i)
            current_section += 1
        else:
            if current_section not in section_paragraphs:
                section_paragraphs[current_section] = []
            section_paragraphs[current_section].append(i)

    return section_paragraphs


def find_abstract_by_text(doc_path: str, start_text: str, end_text: str) -> Dict[str, Any]:
    """根据开始和结束文字定位摘要范围。

    在整个文档 XML 中搜索 start_text 和 end_text，提取它们之间的所有内容作为摘要。

    Args:
        doc_path: Word 文档路径
        start_text: 摘要开始的文字（前几个字）
        end_text: 摘要结束的文字（后几个字）

    Returns:
        摘要位置信息
    """
    doc = Document(doc_path)
    body_xml = doc.element.body.xml

    # 在 XML 中查找开始和结束位置
    start_pos = body_xml.find(start_text)
    end_pos = body_xml.find(end_text)

    if start_pos < 0:
        return {"found": False, "reason": f"未找到开始文字: '{start_text}'"}
    if end_pos < 0:
        return {"found": False, "reason": f"未找到结束文字: '{end_text}'"}
    if end_pos <= start_pos:
        return {"found": False, "reason": "结束位置在开始位置之前"}

    # 提取开始和结束之间的所有文本
    xml_segment = body_xml[start_pos:end_pos + len(end_text)]

    # 尝试多种文本提取模式
    # 模式1: 标准 <w:t>text</w:t>
    text_pattern1 = r'<w:t[^>]*>([^<]*)</w:t>'
    texts = re.findall(text_pattern1, xml_segment)

    # 模式2: 如果模式1没有匹配，尝试更宽松的模式（允许 < 在内容中）
    if not texts:
        text_pattern2 = r'<w:t[^>]*>(.*?)</w:t>'
        texts = re.findall(text_pattern2, xml_segment, re.DOTALL)

    # 模式3: 如果还是没有，直接提取所有纯文本（去除 XML 标签）
    if not texts:
        # 去除所有 XML 标签
        clean_text = re.sub(r'<[^>]+>', '', xml_segment)
        abstract_text = clean_text.strip()
        print(f"[DEBUG] 使用模式3提取文本，长度: {len(abstract_text)}")
    else:
        abstract_text = ''.join(texts)
        print(f"[DEBUG] 使用 w:t 标签提取文本，段数: {len(texts)}, 总长: {len(abstract_text)}")

    # 返回 XML 范围信息，用于直接替换
    return {
        "found": True,
        "type": "xml_range",
        "xml_start": start_pos,
        "xml_end": end_pos + len(end_text),
        "start_text": start_text,
        "end_text": end_text,
        "text": abstract_text,
        "preview": abstract_text[:100] if len(abstract_text) > 100 else abstract_text,
        "context": f"XML 范围 {start_pos} 到 {end_pos + len(end_text)}"
    }
