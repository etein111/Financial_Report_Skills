"""文档分析函数。

用于查找摘要位置、正文范围、附录标记等。

使用 lxml 直接解析 document.xml，确保嵌套表格也能完整读取。
"""

import re
import zipfile
from typing import Dict, Any, List
from lxml import etree


W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'


def _parse_docx_xml(doc_path: str) -> etree._Element:
    """直接解析 document.xml，完整读取所有内容（包括嵌套表格）。

    Args:
        doc_path: docx 文件路径

    Returns:
        document.xml 的根元素
    """
    with zipfile.ZipFile(doc_path, 'r') as z:
        with z.open('word/document.xml') as f:
            return etree.parse(f).getroot()


def _build_body_para_index_map(tree: etree._Element) -> Dict[int, int]:
    """建立XML段落索引到python-docx段落索引的映射。

    python-docx的doc.paragraphs只包含body直接子元素中的<w:p>，
    而tree.iter('{W}p')会遍历所有<w:p>（包括嵌套在表格内的）。
    这个函数建立两者之间的映射关系。

    Args:
        tree: document.xml 根元素

    Returns:
        {xml_para_index: docx_para_index, ...} 映射字典
    """
    body = tree.find(f'{W}body')
    if body is None:
        return {}

    # 收集body直接子元素中的所有<w:p>元素
    body_direct_p_elements = []
    for child in body:
        tag = etree.QName(child.tag).localname
        if tag == 'p':
            body_direct_p_elements.append(child)
        # 表格内的段落不计入python-docux的段落索引

    # 建立映射：xml全局索引 -> body直接子元素中的p索引
    xml_all_paras = list(tree.iter(f'{W}p'))

    # 创建从xml索引到docx索引的映射
    xml_to_docx_map = {}
    docx_idx = 0

    for xml_idx, p_elem in enumerate(xml_all_paras):
        # 检查这个p元素是否是body的直接子元素
        if p_elem in body_direct_p_elements:
            xml_to_docx_map[xml_idx] = docx_idx
            docx_idx += 1
        # 如果不是body直接子元素，不建立映射

    return xml_to_docx_map


def _get_para_text(para: etree._Element) -> str:
    """获取段落的所有文本。

    Args:
        para: 段落元素

    Returns:
        段落文本
    """
    return ''.join(t.text or '' for t in para.iter(f'{W}t'))


def _get_cell_text(tc: etree._Element) -> str:
    """获取单元格的所有文本（包括嵌套表格）。

    Args:
        tc: 单元格元素

    Returns:
        单元格文本
    """
    texts = []
    for t in tc.iter(f'{W}t'):
        if t.text:
            texts.append(t.text)
    return ''.join(texts)


# ==================== 摘要查找 ====================

def find_abstract_by_elements(doc_path: str, elements: dict) -> Dict[str, Any]:
    """根据 elements.yaml 中定义的字段，智能查找摘要位置。

    摘要判断逻辑：
    1. 摘要是一段连贯的文本，包含投资观点、核心分析结论
    2. 摘要不包含评级(RATING)、目标价(TARGET PRICE)等单独字段
    3. 摘要通常是自然段落，不是表格中的键值对
    4. 跳过标题字段（title, title_ch, title_en），避免将标题误判为摘要

    使用 lxml 直接解析，确保嵌套表格不漏读。

    Args:
        doc_path: 文档路径
        elements: elements.yaml 内容

    Returns:
        {
            "found": bool,
            "table": int,       # 表格索引（如果有的话）
            "row": int,         # 行索引
            "col_start": int,   # 起始列
            "col_end": int,     # 结束列
            "context": str      # 上下文描述
        }
    """
    tree = _parse_docx_xml(doc_path)
    paragraphs, tables = _get_paragraphs_and_tables(tree)

    # 收集所有字段值用于匹配
    field_values = []
    for field_name, field_value in elements.items():
        if field_value and isinstance(field_value, str) and len(field_value) > 5:
            field_values.append((field_name, field_value.strip()))

    # 按长度降序排列（优先匹配更长的文本）
    field_values.sort(key=lambda x: len(x[1]), reverse=True)

    # 在文档中搜索字段值对应的位置
    for field_name, field_value in field_values:
        # 跳过分析师相关字段（不适合作为摘要内容）
        if field_name.startswith('a') and any(s in field_name for s in ['_cn', '_en', '_sfc', '_email']):
            continue

        # 跳过标题相关字段（标题不是摘要）
        if field_name in ('title', 'title_ch', 'title_en'):
            continue

        # 在段落中搜索
        for para_idx, para in enumerate(paragraphs):
            para_text = _get_para_text(para)
            if field_value in para_text:
                # 检查这个段落是否像摘要（长文本，没有明显的键值对格式）
                if _is_likely_abstract_paragraph(para_text, field_value):
                    # 提取预览文本（原文的前80个字符）
                    preview_text = para_text[:80] if len(para_text) > 80 else para_text
                    return {
                        "found": True,
                        "table": None,
                        "row": None,
                        "col_start": None,
                        "col_end": None,
                        "start_paragraph": para_idx,
                        "preview": preview_text,
                        "context": f"段落 {para_idx}: {para_text[:50]}..."
                    }

        # 在表格中搜索（使用 lxml，嵌套表格不漏读）
        for tbl_idx, table in enumerate(tables):
            for row_idx, row in enumerate(table.findall(f'{W}tr')):
                for col_idx, tc in enumerate(row.findall(f'{W}tc')):
                    cell_text = _get_cell_text(tc)
                    if field_value in cell_text:
                        # 检查这个单元格是否像摘要
                        if _is_likely_abstract_cell_text(cell_text, field_value, tc):
                            # 提取预览文本（原文的前80个字符）
                            preview_text = cell_text[:80] if len(cell_text) > 80 else cell_text
                            return {
                                "found": True,
                                "table": tbl_idx,
                                "row": row_idx,
                                "col_start": col_idx,
                                "col_end": col_idx,
                                "preview": preview_text,
                                "context": f"表格 {tbl_idx} 行 {row_idx} 列 {col_idx}: {cell_text[:50]}..."
                            }

    return {"found": False, "reason": "未找到匹配的摘要内容"}


def find_abstract_by_markers(doc_path: str) -> Dict[str, Any]:
    """根据标记词查找中文摘要（核心观点）位置。

    摘要结构特征：
    1. 固定开始标记：如"核心观点"、"摘要"、"投资要点"、"Executive Summary"等
    2. 通常位于文档开头（首页之后，第一节正文之前）
    3. 长度适中，通常包含多个投资观点
    4. 后续通常是正文标题（如"一、xxx"）

    使用 lxml 直接解析 document.xml，确保嵌套表格不漏读。
    返回的索引是 python-docux 兼容的。

    Args:
        doc_path: 文档路径

    Returns:
        {
            "found": bool,
            "start_paragraph": int,  # 开始段落索引（python-docux兼容）
            "end_paragraph": int,    # 结束段落索引（python-docux兼容）
            "preview_start": str,    # 开头内容预览
            "preview_end": str,      # 结尾内容预览
            "context": str
        }
    """
    tree = _parse_docx_xml(doc_path)

    paragraphs = list(tree.iter(f'{W}p'))
    total_paragraphs = len(paragraphs)

    # 建立XML索引到python-docux索引的映射
    xml_to_docx = _build_body_para_index_map(tree)

    # 在文档前半部分搜索（摘要通常在正文开头）
    # 跳过前几个段落（通常是标题、提示语等）
    # 注意：正文段落通常在 xml 索引 30 之后
    start_search_idx = 1
    end_search_idx = min(total_paragraphs // 2, 50)  # 只搜索前50个段落或前半部分

    # 搜索摘要起始标记
    for idx in range(start_search_idx, end_search_idx):
        p = paragraphs[idx]
        text = _get_para_text(p).strip()
        text_upper = text.upper()

        # 跳过空段落
        if not text:
            continue

        # 跳过太长的段落（标题通常较短，但核心观点可能较长）
        if len(text) > 500:
            continue

        # 跳过包含明显不是摘要的标记
        if any(word in text_upper for word in ['APPENDIX', 'IMPORTANT', 'DISCLOSURE', '附录', '重要']):
            continue

        is_abstract_title = False

        # 检查是否是摘要标题
        # 1. "核心观点" 开头
        if '核心观点' in text:
            is_abstract_title = True

        # 2. "摘要" 开头（但不是"本文摘要"之类太长的）
        elif text_upper.startswith('摘要') and len(text) < 50:
            is_abstract_title = True

        # 3. "投资要点" 开头
        elif '投资要点' in text:
            is_abstract_title = True

        # 4. "Executive Summary" 开头
        elif text_upper.startswith('EXECUTIVE SUMMARY'):
            is_abstract_title = True

        if is_abstract_title:
            # 找到结束位置：下一个章节标题（如"一、"、"（一）"等）或 APPENDIX
            end_idx = idx + 1
            preview_start = text
            preview_end = ""
            last_content_text = ""

            for next_idx in range(idx + 1, total_paragraphs):
                next_text = _get_para_text(paragraphs[next_idx]).strip()
                next_text_upper = next_text.upper()

                if not next_text:
                    continue

                # 记录最后一个有内容的段落（用于结尾预览）
                last_content_text = next_text

                # 遇到章节标题就结束（一、二、三 或 （一）、（二）等）
                if (next_text.startswith('一、') or next_text.startswith('二、') or
                    next_text.startswith('三、') or next_text.startswith('四、') or
                    next_text.startswith('五、') or next_text.startswith('六、') or
                    next_text.startswith('七、') or next_text.startswith('八、') or
                    next_text.startswith('九、') or
                    next_text.startswith('（一）') or next_text.startswith('（二）') or
                    next_text.startswith('（三）') or
                    next_text.startswith('1.') or next_text.startswith('2.') or
                    next_text.startswith('3.') or
                    # 投资建议
                    '投资建议' in next_text_upper or
                    # 风险提示
                    '风险提示' in next_text_upper or
                    # 正文章节开头
                    ('海外' in next_text and ('板块' in next_text or '市场' in next_text)) or
                    ('互联网' in next_text) or
                    ('航空' in next_text) or
                    # APPENDIX
                    'APPENDIX' in next_text_upper):
                    end_idx = next_idx
                    # 结尾预览使用结束标记之前的最后一个有内容段落
                    # 向前查找最后一个有内容的段落
                    for prev_idx in range(next_idx - 1, idx, -1):
                        prev_text = _get_para_text(paragraphs[prev_idx]).strip()
                        if prev_text:
                            preview_end = prev_text[-80:] if len(prev_text) > 80 else prev_text
                            break
                    break

            # 转换为docx索引
            docx_start = xml_to_docx.get(idx, idx)
            if end_idx in xml_to_docx:
                docx_end = xml_to_docx[end_idx]
            else:
                # 向前找最近的一个在映射中的xml索引
                docx_end = None
                for prev_idx in range(end_idx - 1, idx, -1):
                    if prev_idx in xml_to_docx:
                        docx_end = xml_to_docx[prev_idx]
                        break
                if docx_end is None:
                    docx_end = max(xml_to_docx.values()) if xml_to_docx else 0

            # 如果没有找到结尾预览，使用最后记录的内容
            if not preview_end and last_content_text:
                preview_end = last_content_text[-80:] if len(last_content_text) > 80 else last_content_text

            return {
                "found": True,
                "start_paragraph": docx_start,
                "end_paragraph": docx_end,
                "preview_start": preview_start[:80] if len(preview_start) > 80 else preview_start,
                "preview_end": preview_end,
                "context": f"段落 {docx_start} 到 {docx_end}"
            }

    return {"found": False, "reason": "未找到摘要标记"}


def _is_likely_abstract_paragraph(text: str, field_value: str) -> bool:
    """判断段落是否像摘要。

    Args:
        text: 段落完整文本
        field_value: 字段值

    Returns:
        True 如果像摘要
    """
    # 检查是否有键值对格式的标记（如冒号后是短文本）
    lines = text.split('\n')
    for line in lines:
        if ':' in line:
            parts = line.split(':', 1)
            if len(parts) == 2 and len(parts[1].strip()) < 50:
                # 这更像是键值对，不是摘要
                return False

    # 摘要通常是较长的文本
    if len(field_value) < 100:
        return False

    return True


def _is_likely_abstract_cell_text(cell_text: str, field_value: str, tc: etree._Element = None) -> bool:
    """判断单元格是否像摘要。

    Args:
        cell_text: 单元格文本
        field_value: 字段值
        tc: 单元格元素（可选，用于检查段落数量）

    Returns:
        True 如果像摘要
    """
    # 如果单元格文本较短，可能不是摘要
    if len(cell_text) < 100:
        return False

    # 如果提供了元素，检查段落数量
    if tc is not None:
        # 计算单元格中的段落数量
        para_count = len(list(tc.iter(f'{W}p')))
        if para_count == 1:
            return True

    return True


# ==================== 正文范围查找 ====================

def find_body_range_by_sections(doc_path: str, abstract_end_hint: int = None) -> Dict[str, Any]:
    """根据分节符位置确定正文范围。

    正文范围逻辑：
    1. 正文开始位置：
       - 如果有多个分节符，且第一个分节符在文档前 30%，正文从该分节符之后开始（首页结束）
       - 否则使用 abstract_end_hint（如果提供）
       - 都没有则从段落 0 开始
    2. 正文结束位置：
       - 最后一个分节符之前，或 APPENDIX 标题之前

    使用 lxml 直接解析 document.xml，确保完整读取。
    返回的索引是 python-docux 兼容的。

    Args:
        doc_path: 文档路径
        abstract_end_hint: 摘要结束位置提示（可选），用于辅助确定正文起始

    Returns:
        {
            "found": bool,
            "start_paragraph": int,
            "end_paragraph": int,
            "preview_start": str,    # 开头内容预览
            "preview_end": str,      # 结尾内容预览
            "context": str
        }
    """
    tree = _parse_docx_xml(doc_path)
    paragraphs = list(tree.iter(f'{W}p'))
    total_paragraphs = len(paragraphs)

    # 建立XML索引到python-docux索引的映射
    xml_to_docx = _build_body_para_index_map(tree)

    sect_pr_indices = []  # [xml_paragraph_index, ...]

    for para_idx, para in enumerate(paragraphs):
        # 检查段落是否有分节符
        pPr = para.find(f'{W}pPr')
        if pPr is not None:
            sect_pr = pPr.find(f'{W}sectPr')
            if sect_pr is not None:
                sect_pr_indices.append(para_idx)

    # 确定正文开始位置
    start_paragraph = 0

    if len(sect_pr_indices) >= 2:
        # 有多个分节符：第一个通常是首页结束
        first_sect_idx = sect_pr_indices[0]
        # 如果第一个分节符在文档前 30%，认为是首页结束
        if first_sect_idx < total_paragraphs * 0.3:
            start_paragraph = xml_to_docx.get(first_sect_idx + 1, first_sect_idx + 1)
        elif abstract_end_hint is not None:
            start_paragraph = abstract_end_hint + 1
    elif len(sect_pr_indices) == 1:
        # 只有一个分节符（通常是法律披露开始）
        # 尝试使用 abstract_end_hint
        if abstract_end_hint is not None:
            start_paragraph = abstract_end_hint + 1
        # 否则从 0 开始（保守策略）
    else:
        # 没有分节符
        if abstract_end_hint is not None:
            start_paragraph = abstract_end_hint + 1

    # 确定正文结束位置
    end_paragraph = total_paragraphs

    if sect_pr_indices:
        # 使用最后一个分节符作为正文结束
        last_sect_idx = sect_pr_indices[-1]
        end_paragraph = xml_to_docx.get(last_sect_idx + 1, last_sect_idx + 1)

    # 同时检查 APPENDIX 标题位置（可能比分节符更早）
    appendix_result = find_first_appendix_position(doc_path)
    if appendix_result.get("found"):
        appendix_start = appendix_result["start_paragraph"]
        # 转换为docx索引
        appendix_start_docx = xml_to_docx.get(appendix_start, appendix_start)
        if appendix_start_docx < end_paragraph:
            end_paragraph = appendix_start_docx

    # 确保 start < end
    if start_paragraph >= end_paragraph:
        start_paragraph = 0

    # 获取正文开头预览（第一段非空内容）
    preview_start = ""
    for i in range(start_paragraph, min(start_paragraph + 10, end_paragraph)):
        if i < len(paragraphs):
            para_text = _get_para_text(paragraphs[i]).strip()
            if para_text and len(para_text) > 10:
                preview_start = para_text[:80] if len(para_text) > 80 else para_text
                break

    # 获取正文结尾预览（最后一段非空内容）
    preview_end = ""
    for i in range(end_paragraph - 1, max(start_paragraph, end_paragraph - 10) - 1, -1):
        if i < len(paragraphs) and i >= 0:
            para_text = _get_para_text(paragraphs[i]).strip()
            if para_text and len(para_text) > 10:
                preview_end = para_text[-80:] if len(para_text) > 80 else para_text
                break

    return {
        "found": True,
        "start_paragraph": start_paragraph,
        "end_paragraph": end_paragraph,
        "preview_start": preview_start,
        "preview_end": preview_end,
        "context": f"段落 {start_paragraph} 到 {end_paragraph - 1}"
    }


# ==================== 附录查找 ====================

def find_appendix_by_markers(doc_path: str) -> Dict[str, Any]:
    """根据标记词查找附录（法律披露）位置。

    支持的附录标记：
    1. 中文标记："附录APPENDIX"、"附录 APPENDIX"
    2. 英文标记：APPENDIX 开头的大写标题
    3. 重要披露："IMPORTANT DISCLOSURES"、"重要信息披露"

    使用 lxml 直接解析 document.xml，确保嵌套表格不漏读。

    Args:
        doc_path: 文档路径

    Returns:
        {
            "found": bool,
            "start_paragraph": int,
            "preview": list[str],
            "has_page_break_before": bool,
            "context": str
        }
    """
    tree = _parse_docx_xml(doc_path)

    # 附录关键词（用于搜索 w:t 元素）
    appendix_keywords = ['附录APPENDIX', 'IMPORTANT DISCLOSURE']

    # 先搜索段落中的附录标记
    for idx, p in enumerate(tree.iter(f'{W}p')):
        text = _get_para_text(p)
        for kw in appendix_keywords:
            if kw in text.upper():
                # 检查前面是否有分页符
                has_page_break = False
                pPr = p.find(f'{W}pPr')
                if pPr is not None:
                    last_pPr = list(pPr.iter())[-1] if len(list(pPr)) > 0 else None
                    if last_pPr is not None and etree.QName(last_pPr.tag).localname == 'lastRenderedPageBreak':
                        has_page_break = True

                return {
                    "found": True,
                    "start_paragraph": idx,
                    "preview": [text[:100] if text else ''],
                    "has_page_break_before": has_page_break,
                    "context": f"段落 {idx}: {text[:50]}"
                }

    # 搜索表格中的附录标记
    for tbl in tree.iter(f'{W}tbl'):
        # 获取表格标题
        caption = tbl.find(f'{W}tblPr/{W}tblCaption')
        caption_val = caption.get(f'{W}val') if caption is not None else ''

        # 遍历表格所有单元格
        for row_idx, tr in enumerate(tbl.findall(f'{W}tr')):
            for col_idx, tc in enumerate(tr.findall(f'{W}tc')):
                cell_text = _get_cell_text(tc)
                for kw in appendix_keywords:
                    if kw in cell_text.upper():
                        return {
                            "found": True,
                            "start_paragraph": None,
                            "table_caption": caption_val,
                            "row": row_idx,
                            "col": col_idx,
                            "preview": [cell_text[:100] if cell_text else ''],
                            "has_page_break_before": False,
                            "context": f"表格 {caption_val} 行 {row_idx} 列 {col_idx}: {cell_text[:50]}"
                        }

    return {"found": False, "reason": "未找到附录标记"}


def find_summary_by_markers(doc_path: str) -> Dict[str, Any]:
    """根据标记词查找英文 Summary 位置。

    Summary 结构特征：
    1. 固定开始标记：如 "APPENDIX 1 Summary"、"APPENDIX 1"（后面紧跟 Summary 内容）
    2. 标题段落通常较短（< 100 字符）
    3. 不是引导语（排除包含 "see"、"Please" 等的段落）
    4. 通常位于文档后半部分

    使用 lxml 直接解析 document.xml，确保嵌套表格不漏读。
    返回的索引是 python-docux 兼容的。

    Args:
        doc_path: 文档路径

    Returns:
        {
            "found": bool,
            "start_paragraph": int,  # 开始段落索引（python-docux兼容）
            "end_paragraph": int,    # 结束段落索引（python-docux兼容）
            "preview_start": str,    # 开头内容预览
            "preview_end": str,      # 结尾内容预览
            "context": str
        }
    """
    tree = _parse_docx_xml(doc_path)

    paragraphs = list(tree.iter(f'{W}p'))
    total_paragraphs = len(paragraphs)

    # 建立XML索引到python-docux索引的映射
    xml_to_docx = _build_body_para_index_map(tree)

    # 只在文档后半部分搜索（Summary 通常在 APPENDIX 中）
    start_search_idx = total_paragraphs // 2

    # 搜索 Summary 起始标记
    for idx in range(start_search_idx, total_paragraphs):
        p = paragraphs[idx]
        text = _get_para_text(p).strip()
        text_upper = text.upper()

        # 跳过空段落
        if not text:
            continue

        # 跳过太长的段落（标题通常较短）
        if len(text) > 100:
            continue

        # 跳过引导语（包含 "see"、"please" 等）
        if any(word in text_upper for word in ['SEE ', 'PLEASE', 'REFER TO', '请参阅', '详见']):
            continue

        is_summary_title = False

        # 检查是否是 Summary 标题
        # 1. "APPENDIX 1 Summary" 或 "APPENDIX 1" 开头
        if text_upper.startswith('APPENDIX 1'):
            # 检查是否包含 Summary
            if 'SUMMARY' in text_upper:
                is_summary_title = True
            # 或者就是 "APPENDIX 1"，后面紧跟内容
            elif text_upper.strip() == 'APPENDIX 1':
                is_summary_title = True

        # 2. "Executive Summary" 开头
        if text_upper.startswith('EXECUTIVE SUMMARY'):
            is_summary_title = True

        # 3. 独立的 "Summary" 标题（但要排除太短的）
        if text_upper == 'SUMMARY' or text_upper.startswith('SUMMARY:'):
            is_summary_title = True

        if is_summary_title:
            # 找到结束位置：下一个 APPENDIX 标题或法律披露标题
            end_idx = total_paragraphs
            preview_start = text  # 默认使用标题
            preview_end = ""
            last_content_text = ""

            for next_idx in range(idx + 1, total_paragraphs):
                next_text = _get_para_text(paragraphs[next_idx]).strip()
                next_text_upper = next_text.upper()
                if not next_text:
                    continue

                # 记录最后一个有内容的段落
                last_content_text = next_text

                # 如果还没找到预览内容，取第一个非空的正文段落
                if preview_start == text and len(next_text) > 20:
                    preview_start = next_text[:80] if len(next_text) > 80 else next_text

                # 遇到下一个 APPENDIX 或法律披露标题就结束
                if (next_text_upper.startswith('APPENDIX') and next_idx != idx) or \
                   '附录' in next_text_upper or \
                   'IMPORTANT DISCLOSURE' in next_text_upper or \
                   '重要信息披露' in next_text_upper:
                    end_idx = next_idx
                    # 向前查找最后一个有内容的段落作为结尾预览
                    for prev_idx in range(next_idx - 1, idx, -1):
                        prev_text = _get_para_text(paragraphs[prev_idx]).strip()
                        if prev_text:
                            preview_end = prev_text[-80:] if len(prev_text) > 80 else prev_text
                            break
                    break

            # 转换为docx索引
            docx_start = xml_to_docx.get(idx, idx)
            # 如果end_idx不在映射中（可能在表格内），向前找最近的有效docx索引
            if end_idx in xml_to_docx:
                docx_end = xml_to_docx[end_idx]
            else:
                # 向前找最近的一个在映射中的xml索引
                docx_end = None
                for prev_idx in range(end_idx - 1, idx, -1):
                    if prev_idx in xml_to_docx:
                        docx_end = xml_to_docx[prev_idx]
                        break
                if docx_end is None:
                    docx_end = max(xml_to_docx.values()) if xml_to_docx else 0

            # 如果没有找到结尾预览，使用最后记录的内容
            if not preview_end and last_content_text:
                preview_end = last_content_text[-80:] if len(last_content_text) > 80 else last_content_text

            return {
                "found": True,
                "start_paragraph": docx_start,
                "end_paragraph": docx_end,
                "preview_start": preview_start,
                "preview_end": preview_end,
                "context": f"段落 {docx_start} 到 {docx_end}"
            }

    return {"found": False, "reason": "未找到 Summary 标记"}


def find_first_appendix_position(doc_path: str) -> Dict[str, Any]:
    """找到文档中法律披露附录的位置（优先）。

    正文应该结束于法律披露附录之前，这样法律披露内容可以被原样保留。
    法律披露附录的特征：
    1. "附录APPENDIX" + "重要信息" / "IMPORTANT DISCLOSURES"
    2. "IMPORTANT DISCLOSURES" 单独出现

    如果没有找到法律披露附录，则返回第一个 APPENDIX 标题（如 "APPENDIX 1 Summary"）。

    使用 lxml 直接解析 document.xml，确保嵌套表格不漏读。
    返回的索引是 python-docux 兼容的。

    Args:
        doc_path: 文档路径

    Returns:
        {
            "found": bool,
            "start_paragraph": int,
            "text": str,
            "context": str,
            "is_legal_disclosure": bool  # 是否是法律披露附录
        }
    """
    tree = _parse_docx_xml(doc_path)
    paragraphs = list(tree.iter(f'{W}p'))

    # 建立XML索引到python-docux索引的映射
    xml_to_docx = _build_body_para_index_map(tree)

    legal_disclosure_para = None  # 法律披露附录段落
    any_appendix_para = None  # 任何 APPENDIX 段落

    for i, para in enumerate(paragraphs):
        text = _get_para_text(para).strip()
        text_upper = text.upper()

        if not text:
            continue

        is_legal_disclosure = False
        is_appendix_title = False

        # 1. 法律披露附录：中英混合格式 + 重要信息披露
        if '附录' in text and 'APPENDIX' in text_upper and ('重要信息' in text or 'IMPORTANT DISCLOSURE' in text_upper):
            is_legal_disclosure = True
            is_appendix_title = True
        # 2. 法律披露附录：单独的 IMPORTANT DISCLOSURES
        elif 'IMPORTANT DISCLOSURE' in text_upper:
            is_legal_disclosure = True
            is_appendix_title = True
        # 3. 纯英文 APPENDIX 开头（如 "APPENDIX 1 Summary"）
        elif text_upper.startswith('APPENDIX'):
            is_appendix_title = True
        # 4. 独立的中文"附录"（后面没有其他内容）
        elif text.startswith('附录') and len(text) < 50:
            is_appendix_title = True

        if is_appendix_title:
            # 转换为docx索引
            docx_idx = xml_to_docx.get(i, i)

            # 优先记录法律披露附录
            if is_legal_disclosure and legal_disclosure_para is None:
                legal_disclosure_para = {
                    "found": True,
                    "start_paragraph": docx_idx,
                    "text": text[:100],
                    "context": f"段落 {docx_idx}: {text[:50]}",
                    "is_legal_disclosure": True
                }
            # 记录第一个遇到的任何 APPENDIX 作为后备
            elif any_appendix_para is None:
                any_appendix_para = {
                    "found": True,
                    "start_paragraph": docx_idx,
                    "text": text[:100],
                    "context": f"段落 {docx_idx}: {text[:50]}",
                    "is_legal_disclosure": False
                }

            # 如果找到了法律披露附录，直接返回（优先使用法律披露）
            if legal_disclosure_para is not None:
                return legal_disclosure_para

    # 如果没有找到法律披露附录，返回任何 APPENDIX 标题
    if any_appendix_para is not None:
        return any_appendix_para

    return {"found": False, "reason": "未找到 APPENDIX 相关标题"}
