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

SCRIPTS_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPTS_DIR))

try:
    from docx import Document
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


W = common.W_NS

# 法律披露附录的识别标记（extract_appendix 和 validate_appendix 共用）
_APPENDIX_MARKERS = [
    'APPENDIX',
    '附录',
    '重要信息披露',
    'IMPORTANT DISCLOSURES',
    'Disclaimer',
    '免责声明',
    '[Table_disclaimer]',
]


def _remove_elements_outside_range(body, elements: list, start_idx: int, end_idx: int) -> None:
    """移除 [start_idx, end_idx) 范围外的元素，保留 sectPr 元素。

    按倒序收集待删除元素，避免索引偏移。被 extract_fragment_by_markers、
    extract_body、extract_english_summary 三个函数共用。

    Args:
        body: document.xml 的 body 元素
        elements: body 的直接子元素列表
        start_idx: 保留范围起始索引（包含）
        end_idx: 保留范围结束索引（不包含）
    """
    elements_to_remove = []

    # 倒序删除 end_idx 之后的元素
    for i in range(len(elements) - 1, end_idx - 1, -1):
        elem = elements[i]
        tag = elem.tag.split('}')[-1]
        if tag != 'sectPr':
            elements_to_remove.append(elem)

    # 倒序删除 start_idx 之前的元素
    for i in range(start_idx - 1, -1, -1):
        elem = elements[i]
        tag = elem.tag.split('}')[-1]
        if tag != 'sectPr':
            elements_to_remove.append(elem)

    for elem in elements_to_remove:
        try:
            body.remove(elem)
        except ValueError:
            pass



def _get_all_tables_lxml(doc_path: str) -> List[etree._Element]:
    """使用 lxml 获取文档中所有表格（包括嵌套表格）。

    解决 python-docx 漏读嵌套表格的问题。

    Args:
        doc_path: docx 文件路径

    Returns:
        表格元素列表
    """
    files = common.read_docx_zip(doc_path)
    tree = etree.fromstring(files['word/document.xml'])
    return list(tree.iter(f'{W}tbl'))



def extract_fragment_by_markers(
    draft_path: str,
    start_marker: str,
    end_marker: str,
    output_path: str
) -> Path:
    """通用 fragment 提取函数，根据 LLM 识别的开始和结束标记提取内容。

    使用"复制整个文档 → 删除范围外元素"的方式，
    确保所有格式、图片和表格都被完整保留。

    Args:
        draft_path: 草稿文件路径
        start_marker: 开始标记文本（LLM 从草稿中识别）
        end_marker: 结束标记文本（LLM 从草稿中识别）
        output_path: 输出路径

    Returns:
        输出文件路径
    """
    if Document is None:
        return Path(output_path)

    out_path = Path(output_path)

    try:
        # 复制到临时文件（避免 Windows 文件锁定问题）
        import tempfile
        import uuid
        temp_dir = Path(tempfile.gettempdir())
        temp_path = temp_dir / f"fragment_temp_{uuid.uuid4().hex[:8]}.docx"
        shutil.copy(draft_path, str(temp_path))

        # 打开临时文件进行编辑
        doc = Document(str(temp_path))
        body = doc.element.body
        elements = list(body)

        # 找到开始和结束位置
        start_idx = None
        end_idx = None

        for i, elem in enumerate(elements):
            text = common.get_element_text(elem).strip()
            text_upper = text.upper()

            # 找开始位置（不区分大小写）
            if start_idx is None and start_marker.upper() in text_upper:
                start_idx = i
                print(f"找到开始标记: 元素 {i}, 文本: {text[:50]}...")

            # 找结束位置（在找到开始位置之后）
            if start_idx is not None and end_idx is None and i > start_idx:
                if end_marker.upper() in text_upper:
                    end_idx = i
                    print(f"找到结束标记: 元素 {i}, 文本: {text[:50]}...")
                    break

        # 如果没找到开始标记
        if start_idx is None:
            print(f"警告：未找到开始标记 '{start_marker}'")
            # 返回空文档
            empty_doc = Document()
            empty_doc.save(str(out_path))
            temp_path.unlink(missing_ok=True)
            return out_path

        # 如果没找到结束标记，使用文档末尾
        if end_idx is None:
            end_idx = len(elements)
            print(f"警告：未找到结束标记 '{end_marker}'，使用文档末尾")

        print(f"提取范围: 元素 {start_idx} - {end_idx}")

        # 🔑 关键：在删除元素前，找到范围内的 sectPr 页边距
        # 因为这些 sectPr 定义了内容应该使用的页边距
        margins_to_preserve = _find_sectpr_margins_for_range(elements, start_idx, end_idx, W)

        # 删除范围外的元素
        _remove_elements_outside_range(body, elements, start_idx, end_idx)

        # 🔑 关键：将保存的页边距应用到最终的 sectPr
        if margins_to_preserve:
            _apply_margins_to_final_sectpr(body, margins_to_preserve, W)

        # 保存到输出路径
        doc.save(str(out_path))

        # 释放文档对象，避免文件锁定
        del doc

        # 清理临时文件（忽略错误，让系统自动清理）
        try:
            temp_path.unlink()
        except (PermissionError, OSError):
            pass  # Windows 上可能仍被锁定，忽略错误

        # 验证结果
        final_doc = Document(str(out_path))
        print(f"Fragment 提取完成: {len(final_doc.paragraphs)} 段落, {len(final_doc.tables)} 表格")

        return out_path

    except Exception as e:
        print(f"提取 fragment 失败: {e}")
        import traceback
        traceback.print_exc()
        # 清理临时文件
        if 'temp_path' in locals():
            try:
                temp_path.unlink()
            except (PermissionError, OSError):
                pass
        return out_path


def extract_abstract(draft_path: str, scope: str, output_path: Optional[str] = None,
                     start_marker: Optional[str] = None, end_marker: Optional[str] = None,
                     appendix_notice: Optional[str] = None) -> Path:
    """提取摘要片段，保留完整格式。

    优先使用 LLM 提供的 start_marker 和 end_marker。
    如果未提供，则使用基于启发式规则的备用逻辑。

    Args:
        draft_path: 草稿文件路径
        scope: 位置描述（如"首页右侧"）
        output_path: 输出路径（可选）
        start_marker: 开始标记文本（LLM 从草稿中识别）
        end_marker: 结束标记文本（LLM 从草稿中识别）
        appendix_notice: 摘要前的提示文本（如 "Please see APPENDIX 1 for English summary"）

    Returns:
        abstract.docx 文件路径
    """
    out_path = Path(output_path or common.FILE_ABSTRACT)

    # 如果提供了 start_marker 和 end_marker，使用通用函数
    if start_marker and end_marker:
        print(f"使用 LLM 提供的标记提取摘要: '{start_marker}' -> '{end_marker}'")
        result_path = extract_fragment_by_markers(draft_path, start_marker, end_marker, str(out_path))

        # 如果有 appendix_notice，需要添加到 abstract 内容之前
        if appendix_notice:
            _prepend_abstract_notice(str(result_path), appendix_notice)

        return result_path

    # 备用逻辑：使用启发式规则
    print("使用启发式规则提取摘要（未提供 LLM 标记）")

    if Document is None:
        return out_path

    try:
        doc = Document(draft_path)

        # 创建新文档
        abstract_doc = Document()

        # 删除新文档的默认空段落
        for para in abstract_doc.paragraphs:
            p = para._element
            p.getparent().remove(p)

        # 策略1：从首页表格中查找摘要（常见于公司报告模板）
        abstract_found = False
        all_tables = _get_all_tables_lxml(draft_path)

        if all_tables:
            first_table = all_tables[0]

            # 收集所有候选单元格（按长度排序，优先选择长文本）
            candidate_cells = []
            for row_idx, row in enumerate(first_table.findall(f'{W}tr')):
                for col_idx, tc in enumerate(row.findall(f'{W}tc')):
                    cell_text = common.get_element_text(tc).strip()

                    # 跳过模板占位符单元格
                    if '[Table_' in cell_text:
                        continue

                    # 跳过太短的单元格
                    if len(cell_text) < 200:
                        continue

                    # 计算权重（长度 + 位置偏好）
                    # 优先选择不在第一列的单元格（第一列通常是标签）
                    position_bonus = 100 if col_idx > 0 else 0
                    weight = len(cell_text) + position_bonus

                    candidate_cells.append((weight, tc, cell_text))

            # 按权重排序，选择最佳候选
            candidate_cells.sort(key=lambda x: -x[0])

            if candidate_cells:
                _, best_tc, cell_text = candidate_cells[0]
                print(f"找到摘要单元格，长度: {len(cell_text)}")

                # 复制单元格内容
                for para_elem in best_tc.findall(f'{W}p'):
                    if common.get_element_text(para_elem).strip():
                        new_para = deepcopy(para_elem)
                        abstract_doc.element.body.append(new_para)
                abstract_found = True

        # 策略2：如果表格中没找到，从段落中查找
        if not abstract_found:
            in_abstract = False
            body = doc.element.body
            for para in body.iter(f'{W}p'):
                text = common.get_element_text(para).strip()

                if any(marker in text for marker in ['摘要', '投资亮点', '核心观点']):
                    in_abstract = True
                    continue

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


def _find_sectpr_margins_for_range(elements: list, start_idx: int, end_idx: int, W: str) -> Optional[Dict[str, str]]:
    """查找适用于指定范围内容的 sectPr 页边距设置。

    Word 文档中，sectPr 定义的是**该节结束时**的属性。
    因此，对于 start_idx 到 end_idx 范围内的内容：
    1. 首先查找范围内是否有 sectPr（定义该范围使用的页边距）
    2. 如果范围内没有 sectPr，查找范围后最近的 sectPr（不包括文档末尾的 sectPr）
    3. 如果都找不到，返回 None（使用文档末尾的 sectPr）

    Args:
        elements: body 的直接子元素列表
        start_idx: 开始索引
        end_idx: 结束索引
        W: Word 命名空间前缀

    Returns:
        页边距字典 {'top': ..., 'bottom': ..., 'left': ..., 'right': ...}，如果找不到返回 None
    """
    def _extract_margins(sectPr):
        """从 sectPr 提取页边距"""
        pgMar = sectPr.find(f'{W}pgMar')
        if pgMar is None:
            return None
        return common.extract_margins_from_pgMar(pgMar) or None

    # 1. 首先在范围内查找 sectPr（从后往前找）
    for i in range(min(end_idx, len(elements)) - 1, start_idx - 1, -1):
        elem = elements[i]
        tag = elem.tag.split('}')[-1]

        if tag == 'p':
            pPr = elem.find(f'{W}pPr')
            if pPr is not None:
                sectPr = pPr.find(f'{W}sectPr')
                if sectPr is not None:
                    margins = _extract_margins(sectPr)
                    if margins:
                        print(f"找到范围内的 sectPr（元素 {i}），页边距: {margins}")
                        return margins

    # 2. 范围内没有 sectPr，查找范围后最近的 sectPr（不包括文档末尾的直接 sectPr）
    for i in range(end_idx, len(elements)):
        elem = elements[i]
        tag = elem.tag.split('}')[-1]

        # 跳过文档末尾的直接 sectPr
        if tag == 'sectPr':
            continue

        if tag == 'p':
            pPr = elem.find(f'{W}pPr')
            if pPr is not None:
                sectPr = pPr.find(f'{W}sectPr')
                if sectPr is not None:
                    margins = _extract_margins(sectPr)
                    if margins:
                        print(f"找到范围后的 sectPr（元素 {i}），页边距: {margins}")
                        return margins

    return None


def _apply_margins_to_final_sectpr(body, margins: Dict[str, str], W: str) -> bool:
    """将页边距应用到文档末尾的 sectPr，并清除 header/footer 引用。

    清除 header/footer 引用很重要，因为 body.docx 的 sectPr 可能包含封面 section
    的 header 引用（如 rId14 -> header8.xml 有 logo），而不是正文 section 的
    header 引用（rId9 -> header4.xml 无 logo）。

    清除后，body 内容会继承模板中对应位置的 header/footer 设置。

    Args:
        body: document.xml 的 body 元素
        margins: 页边距字典
        W: Word 命名空间前缀

    Returns:
        是否成功
    """
    # 找到末尾的 sectPr
    elements = list(body)
    for elem in reversed(elements):
        tag = elem.tag.split('}')[-1]
        if tag == 'sectPr':
            # 清除所有 headerReference 和 footerReference
            # 因为 body.docx 的 sectPr 可能包含封面 section 的 header 引用
            # 注意：使用 findall() 获取所有引用（first、default、even 类型），逐一删除
            for ref_tag in ['headerReference', 'footerReference']:
                refs = elem.findall(f'{W}{ref_tag}')
                for ref in refs:
                    elem.remove(ref)
                    ref_type = ref.get(f'{W}type', 'unknown')
                    print(f"  已清除 sectPr 中的 {ref_tag} (type={ref_type})")

            # 应用页边距
            pgMar = elem.find(f'{W}pgMar')
            if pgMar is not None:
                for attr, val in margins.items():
                    pgMar.set(f'{W}{attr}', val)
                print(f"已将页边距应用到最终 sectPr: {margins}")
                return True
    return False


def _prepend_abstract_notice(docx_path: str, notice_text: str) -> bool:
    """在 abstract.docx 内容之前插入提示文本。

    用于保留 "(Please see APPENDIX 1 for English summary)" 等提示文本。

    Args:
        docx_path: abstract.docx 文件路径
        notice_text: 要插入的提示文本

    Returns:
        是否成功
    """
    try:
        doc = Document(docx_path)
        body = doc.element.body

        # 创建提示段落
        from docx.oxml import OxmlElement
        from docx.oxml.ns import qn

        # 创建段落元素 <w:p>
        notice_para = OxmlElement('w:p')

        # 创建 run 元素 <w:r>
        r = OxmlElement('w:r')
        notice_para.append(r)

        # 创建文本内容 <w:t>
        t = OxmlElement('w:t')
        t.set(qn('xml:space'), 'preserve')
        t.text = notice_text
        r.append(t)

        # 在 body 第一个段落之前插入提示段落
        children = list(body)
        if children:
            body.insert(0, notice_para)
        else:
            body.append(notice_para)

        doc.save(docx_path)
        print(f"  已在 abstract.docx 开头添加提示文本: {notice_text[:50]}...")
        return True

    except Exception as e:
        print(f"  添加 abstract 提示文本失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def _clear_paragraph_indents(docx_path: str) -> bool:
    """清除 Word 文档中所有段落的缩进设置。

    用于清除 draft 中的错误缩进（如负缩进），
    让内容在渲染时继承 template 的格式。

    Args:
        docx_path: Word 文档路径

    Returns:
        是否成功
    """
    try:
        cleared_count = [0]

        def _clear_inds(tree):
            for ind in tree.findall(f'.//{W}ind'):
                parent = ind.getparent()
                if parent is not None:
                    parent.remove(ind)
                    cleared_count[0] += 1

        common.modify_docx_xml(docx_path, _clear_inds)

        if cleared_count[0] > 0:
            print(f"  已清除 {cleared_count[0]} 个段落缩进设置")

        return True

    except Exception as e:
        print(f"清除段落缩进失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def extract_body(draft_path: str, scope: str, output_path: Optional[str] = None,
                 start_marker: Optional[str] = None, end_marker: Optional[str] = None) -> Path:
    """提取正文片段，保留完整格式、表格和图片。

    优先使用 LLM 提供的 start_marker 和 end_marker。
    如果未提供，则使用基于启发式规则的备用逻辑。

    Args:
        draft_path: 草稿文件路径
        scope: 位置描述（如"从第三页开始"）
        output_path: 输出路径（可选）
        start_marker: 正文开始标记文本（LLM 从草稿中识别）
        end_marker: 正文结束标记文本（LLM 从草稿中识别）

    Returns:
        body.docx 文件路径
    """
    out_path = Path(output_path or common.FILE_BODY)

    # 如果提供了 start_marker 和 end_marker，使用通用函数
    if start_marker and end_marker:
        print(f"使用 LLM 提供的标记提取正文: '{start_marker}' -> '{end_marker}'")
        return extract_fragment_by_markers(draft_path, start_marker, end_marker, str(out_path))

    # 备用逻辑：使用启发式规则
    print("使用启发式规则提取正文（未提供完整 LLM 标记）")

    if Document is None:
        return out_path

    try:
        # 复制整个文档到临时文件（保留所有资源引用）
        import tempfile
        import uuid
        temp_dir = Path(tempfile.gettempdir())
        temp_path = temp_dir / f"body_temp_{uuid.uuid4().hex[:8]}.docx"
        shutil.copy(draft_path, str(temp_path))

        # 打开临时文件进行编辑
        doc = Document(str(temp_path))
        body = doc.element.body
        elements = list(body)

        # 找到正文的起始和结束位置
        start_idx = None
        end_idx = len(elements)
        toc_idx = None

        # 结束标记：优先使用 LLM 提供的 end_marker
        if end_marker:
            end_markers = [end_marker]
            print(f"使用 LLM 提供的结束标记: '{end_marker}'")
        else:
            end_markers = [
                'Summary',  # 英文摘要标题（优先检查，避免 body 包含英文摘要）
                '重要信息披露',
                '[Table_disclaimer]',
                '免责声明',
                'APPENDIX',
                '附录',
            ]
            print("使用默认结束标记列表")

        # 找目录位置和正文结束位置
        for i, elem in enumerate(elements):
            text = common.get_element_text(elem).strip()
            text_upper = text.upper()
            tag = elem.tag.split('}')[-1]

            # 找目录位置
            if toc_idx is None:
                if text == '目录':
                    toc_idx = i
                    print(f"找到目录位置: 元素 {i}")
                elif tag == 'sdt' and '目录' in text:
                    toc_idx = i
                    print(f"找到目录控件: 元素 {i}")

            # 找结束位置
            for marker in end_markers:
                if marker.upper() in text_upper:
                    # 找到结束标记后，检查结束标记之前是否有分页符段落
                    # 如果有，应该把分页符也包含在 body 中（确保正文结束后换页）
                    page_break_idx = None
                    for j in range(i - 1, max(0, i - 5), -1):
                        prev_elem = elements[j]
                        prev_tag = prev_elem.tag.split('}')[-1]
                        if prev_tag == 'p':
                            # 检查是否包含分页符
                            has_page_break = False
                            for br in prev_elem.iter(f'{W}br'):
                                br_type = br.get(f'{W}type', '')
                                if br_type == 'page':
                                    has_page_break = True
                                    break
                            if has_page_break:
                                page_break_idx = j
                                print(f"找到正文结束前的分页符: 元素 {j}")
                                break
                            # 如果段落有文本就停止查找
                            prev_text = common.get_element_text(prev_elem).strip()
                            if prev_text:
                                break

                    end_idx = page_break_idx if page_break_idx is not None else i
                    print(f"找到正文结束标记: 元素 {i}, 匹配 '{marker}', 文本: {text[:50]}...")
                    if page_break_idx is not None:
                        print(f"  正文范围扩展到分页符: 元素 {page_break_idx}")
                    break
            if end_idx < len(elements):
                break

        # 确定起始位置
        if start_marker:
            # 使用 LLM 提供的开始标记
            for i, elem in enumerate(elements):
                text = common.get_element_text(elem).strip()
                if start_marker.upper() in text.upper():
                    start_idx = i
                    print(f"找到正文开始标记: 元素 {i}, 文本: {text[:50]}...")
                    break
        elif toc_idx is not None:
            start_idx = toc_idx
        else:
            # 找正文第一章
            for i, elem in enumerate(elements):
                text = common.get_element_text(elem).strip()
                if text.startswith('1 ') or text.startswith('1.'):
                    if '\t' not in text and text and not text[-1].isdigit():
                        start_idx = i
                        break
                    if elem.tag.endswith('}p'):
                        pPr = elem.find('.//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}pStyle')
                        if pPr is not None:
                            style_val = pPr.get('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val', '')
                            if 'Heading' in style_val or '标题' in style_val:
                                start_idx = i
                                break

        if start_idx is None:
            print("警告：未找到正文起始位置，使用默认值")
            start_idx = 10

        print(f"正文范围: 元素 {start_idx} - {end_idx}")

        # 🔑 关键：在删除元素前，找到范围内的 sectPr 页边距
        # 因为这些 sectPr 定义了正文内容应该使用的页边距
        margins_to_preserve = _find_sectpr_margins_for_range(elements, start_idx, end_idx, W)

        # 删除范围外的元素
        _remove_elements_outside_range(body, elements, start_idx, end_idx)

        # 🔑 关键：将保存的页边距应用到最终的 sectPr
        if margins_to_preserve:
            _apply_margins_to_final_sectpr(body, margins_to_preserve, W)

        doc.save(str(out_path))

        # 清理临时文件
        try:
            temp_path.unlink()
        except Exception:
            pass

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
    # 遍历 body 的子元素，找到表格的位置，然后计算前面有多少段落

    try:
        table_element = table._element
        body = doc.element.body

        # 遍历 body 的直接子元素
        para_count = 0
        for child in body:
            if child is table_element:
                # 找到表格，返回之前的段落数
                return para_count
            # 检查是否是段落元素
            if child.tag.endswith('}p'):
                para_count += 1

    except Exception:
        pass

    # 如果无法精确定位，返回一个估计值
    # 假设表格大致分布在文档中
    return int(len(doc.paragraphs) * (table_index + 1) / (len(doc.tables) + 1))


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
        appendix_markers = _APPENDIX_MARKERS

        # 查找附录起始位置
        start_idx = None
        for i, elem in enumerate(elements):
            text = common.get_element_text(elem).strip()

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
        appendix_keywords = _APPENDIX_MARKERS

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
            text = common.get_element_text(elem).strip()

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


def extract_english_summary(draft_path: str, scope: str, output_path: Optional[str] = None,
                            start_marker: Optional[str] = None, end_marker: Optional[str] = None) -> Path:
    """提取英文摘要片段（APPENDIX 1 Summary）。

    优先使用 LLM 提供的 start_marker 和 end_marker。
    如果未提供，则使用基于启发式规则的备用逻辑（查找分页符作为结束）。

    Args:
        draft_path: 草稿文件路径
        scope: 位置描述（如"正文之后一页"）
        output_path: 输出路径（可选）
        start_marker: 开始标记文本（LLM 从草稿中识别）
        end_marker: 结束标记文本（LLM 从草稿中识别）

    Returns:
        english_summary.docx 文件路径
    """
    out_path = Path(output_path or common.FILE_ENGLISH_SUMMARY)

    # 如果提供了 start_marker 和 end_marker，使用通用函数
    if start_marker and end_marker:
        print(f"使用 LLM 提供的标记提取英文摘要: '{start_marker}' -> '{end_marker}'")
        result_path = extract_fragment_by_markers(draft_path, start_marker, end_marker, str(out_path))

        # 🔑 关键：清除提取后文档中的段落缩进
        # draft 中的 english_summary 可能有错误的缩进（如负缩进），
        # 清除后让内容继承 template 的 "APPENDIX 1 Summary" 格式
        _clear_paragraph_indents(str(result_path))

        return result_path

    # 备用逻辑：使用启发式规则
    print("使用启发式规则提取英文摘要（未提供完整 LLM 标记）")

    if Document is None:
        return out_path

    try:
        # 复制到临时文件以避免文件锁定问题
        import tempfile
        import uuid
        temp_dir = Path(tempfile.gettempdir())
        temp_path = temp_dir / f"english_summary_temp_{uuid.uuid4().hex[:8]}.docx"
        shutil.copy(draft_path, str(temp_path))

        doc = Document(str(temp_path))
        body = doc.element.body
        elements = list(body)

        # 英文摘要的起始标记
        if start_marker:
            summary_keywords = [start_marker]
        else:
            summary_keywords = [
                'Summary',  # 简单的 Summary 标题
                'APPENDIX 1 SUMMARY',
                'APPENDIX 1 Summary',
                'Appendix 1 Summary',
                'EXECUTIVE SUMMARY',
                'Executive Summary',
            ]

        # 找到英文摘要的起始和结束位置
        start_idx = None
        end_idx = len(elements)

        # 找起始位置
        for i, elem in enumerate(elements):
            text = common.get_element_text(elem).strip()

            for kw in summary_keywords:
                if kw.upper() in text.upper():
                    start_idx = i
                    print(f"找到英文摘要起始位置: 元素 {i}")
                    break
            if start_idx is not None:
                break

        if start_idx is None:
            print("警告：未找到英文摘要起始标记")
            empty_doc = Document()
            empty_doc.save(str(out_path))
            return out_path

        # 找结束位置
        if end_marker:
            # 使用 LLM 提供的结束标记
            for i in range(start_idx + 1, len(elements)):
                text = common.get_element_text(elements[i]).strip()
                if end_marker.upper() in text.upper():
                    end_idx = i
                    print(f"找到英文摘要结束标记: 元素 {i}")
                    break
        else:
            # 备用：查找分页符或结束标记
            end_markers_fallback = ['APPENDIX', '附录', '重要信息披露', '[Table_disclaimer]']
            for i in range(start_idx + 1, len(elements)):
                elem = elements[i]
                tag = elem.tag.split('}')[-1]
                text = common.get_element_text(elem).strip()

                # 先检查结束标记
                for marker in end_markers_fallback:
                    if marker.upper() in text.upper():
                        end_idx = i
                        print(f"找到英文摘要结束标记: 元素 {i}, 匹配 '{marker}'")
                        break
                if end_idx < len(elements):
                    break

                # 再检查分页符
                has_page_break = False

                if tag == 'p':
                    for br in elem.iter(f'{W}br'):
                        br_type = br.get(f'{W}type', '')
                        if br_type == 'page':
                            has_page_break = True
                            break
                    if not has_page_break:
                        for _ in elem.iter(f'{W}lastRenderedPageBreak'):
                            has_page_break = True
                            break

                if tag == 'p' and not has_page_break:
                    pPr = elem.find(f'{W}pPr')
                    if pPr is not None:
                        sectPr = pPr.find(f'{W}sectPr')
                        if sectPr is not None:
                            has_page_break = True

                if has_page_break:
                    end_idx = i
                    print(f"找到英文摘要结束位置（分页符）: 元素 {i}")
                    break

        print(f"英文摘要范围: 元素 {start_idx} - {end_idx}")

        # 🔑 关键：在删除元素前，找到范围内的 sectPr 页边距
        # 因为这些 sectPr 定义了英文摘要内容应该使用的页边距
        margins_to_preserve = _find_sectpr_margins_for_range(elements, start_idx, end_idx, W)

        # 删除范围外的元素
        _remove_elements_outside_range(body, elements, start_idx, end_idx)

        # 🔑 清除段落的缩进设置，让 english_summary 对齐 template 的格式
        # draft 中的 english_summary 可能有错误的缩进（如负缩进），
        # 清除后让内容继承 template 的 "APPENDIX 1 Summary" 格式
        for p in body.findall(f'.//{W}p'):
            pPr = p.find(f'{W}pPr')
            if pPr is not None:
                ind = pPr.find(f'{W}ind')
                if ind is not None:
                    pPr.remove(ind)
                    print(f"  已清除段落缩进")

        # 🔑 关键：将保存的页边距应用到最终的 sectPr
        if margins_to_preserve:
            _apply_margins_to_final_sectpr(body, margins_to_preserve, W)

        doc.save(str(out_path))

        # 清理临时文件
        try:
            temp_path.unlink()
        except Exception:
            pass

        final_doc = Document(str(out_path))
        print(f"英文摘要提取完成: {len(final_doc.paragraphs)} 段落, "
              f"{len(final_doc.tables)} 表格")

        return out_path

    except Exception as e:
        print(f"提取英文摘要失败: {e}")
        import traceback
        traceback.print_exc()
        return out_path
