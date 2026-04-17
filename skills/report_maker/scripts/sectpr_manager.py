"""sectpr_manager.py - sectPr 管理模块

提供页边距、页眉页脚的保存、恢复和应用功能。
docxcompose 在合并文档时会破坏 sectPr，本模块用于修复这些问题。
"""

from lxml import etree
from copy import deepcopy
from typing import Dict, Any, Optional

import common
W = common.W_NS
R = common.R_NS


def _save_template_final_sectPr(template_path: str) -> Optional[Any]:
    """保存模板的文档末尾 sectPr（控制附录 section 的格式）。

    docxcompose 在 append 时会移除被追加文档的 body-level sectPr，
    因此需要在合并前保存、合并后恢复。

    Args:
        template_path: 模板文件路径

    Returns:
        深拷贝的 sectPr XML 元素，或 None
    """
    sectPrs = _save_all_template_sectPrs(template_path)
    return sectPrs.get('appendix') if sectPrs else None


def _save_all_template_sectPrs(template_path: str) -> Optional[Dict[str, Any]]:
    """保存模板中所有 sectPr，用于合并后恢复。

    模板有 4 个 section，按顺序：
    - cover: continuous sectPr
    - body: nextPage sectPr
    - english_summary: nextPage sectPr
    - appendix: body-level sectPr

    Args:
        template_path: 模板文件路径

    Returns:
        {'cover': sectPr, 'body': sectPr, 'english_summary': sectPr, 'appendix': sectPr}
        或 None
    """
    try:
        files = common.read_docx_zip(template_path)
        doc_xml = files['word/document.xml']

        doc_tree = etree.fromstring(doc_xml)
        body = doc_tree.find(f'{W}body')
        if body is None:
            return None

        result = {}
        para_sectPrs = []

        for elem in body:
            if elem.tag == f'{W}p':
                pPr = elem.find(f'{W}pPr')
                if pPr is not None:
                    sectPr = pPr.find(f'{W}sectPr')
                    if sectPr is not None:
                        para_sectPrs.append(deepcopy(sectPr))
            elif elem.tag == f'{W}sectPr':
                result['appendix'] = deepcopy(elem)

        if len(para_sectPrs) >= 1:
            result['cover'] = para_sectPrs[0]
        if len(para_sectPrs) >= 2:
            result['body'] = para_sectPrs[1]
        if len(para_sectPrs) >= 3:
            result['english_summary'] = para_sectPrs[2]

        return result

    except Exception as e:
        print(f"  保存模板 sectPrs 失败: {e}")
        return None


def _restore_all_sectPrs(docx_path: str, template_sectPrs: Dict[str, Any]) -> bool:
    """将输出文档的所有 sectPrs 替换为模板版本。

    Word 的 sectPr 定义的是它之前内容的页面格式。
    因此必须按语义位置分配，而非按出现顺序。

    分配策略：
    1. continuous sectPr → 封面 sectPr
    2. "APPENDIX 1" 段落之前的最后一个 sectPr → 正文 sectPr (left=3600)
    3. "APPENDIX 1" 段落之后、法律附录之前的最后一个 sectPr → 英文摘要 sectPr
    4. body-level sectPr → 附录 sectPr

    Args:
        docx_path: 输出文档路径
        template_sectPrs: 从 _save_all_template_sectPrs 获取的模板 sectPrs

    Returns:
        是否成功
    """
    try:
        result = False

        def _restore(tree):
            nonlocal result
            body = tree.find(f'{W}body')
            if body is None:
                return

            all_elements = list(body)

            para_sectPrs = []
            for idx, elem in enumerate(all_elements):
                if elem.tag == f'{W}p':
                    pPr = elem.find(f'{W}pPr')
                    if pPr is not None:
                        sectPr = pPr.find(f'{W}sectPr')
                        if sectPr is not None:
                            para_sectPrs.append((idx, elem, sectPr))

            cover_sectPr = template_sectPrs.get('cover')
            body_sectPr = template_sectPrs.get('body')
            es_sectPr = template_sectPrs.get('english_summary')
            appendix_sectPr = template_sectPrs.get('appendix')

            appendix1_idx = None
            for idx, elem in enumerate(all_elements):
                if elem.tag == f'{W}p':
                    text = common.get_element_text(elem).strip()
                    if text == common.APPENDIX_1_MARKER:
                        appendix1_idx = idx
                        break

            disclaimer_idx = None
            for idx, elem in enumerate(all_elements):
                if elem.tag == f'{W}tbl':
                    text = common.get_element_text(elem)
                    if '附录APPENDIX' in text or 'Table_disclaimer' in text:
                        disclaimer_idx = idx
                        break

            # 计算正文边界：APPENDIX 1 存在时用它，不存在时用 disclaimer
            body_boundary = appendix1_idx if appendix1_idx is not None else disclaimer_idx

            print(f"  关键位置: APPENDIX 1={appendix1_idx}, 法律附录={disclaimer_idx}, 正文边界={body_boundary}")

            for idx, para, old_sectPr in para_sectPrs:
                pPr = para.find(f'{W}pPr')
                sect_type = old_sectPr.find(f'{W}type')
                type_val = sect_type.get(f'{W}val') if sect_type is not None else 'nextPage'

                pPr.remove(old_sectPr)

                replacement = None
                if type_val == 'continuous':
                    replacement = cover_sectPr
                    label = 'cover'
                elif body_boundary is not None and idx < body_boundary:
                    # 有 APPENDIX 1 时：body_boundary=appendix1_idx，正文之前是 body
                    # 没有 APPENDIX 1 时：body_boundary=disclaimer_idx，正文之前也是 body
                    replacement = body_sectPr
                    label = 'body'
                elif disclaimer_idx is not None and idx < disclaimer_idx:
                    # 只有当有 APPENDIX 1 时才到这里（english_summary）
                    replacement = es_sectPr
                    label = 'english_summary'
                else:
                    label = 'dropped'

                if replacement is not None:
                    pPr.append(deepcopy(replacement))

                if type_val == 'continuous' or replacement is not None:
                    source_sectPr = replacement if replacement is not None else old_sectPr
                    pgMar = source_sectPr.find(f'{W}pgMar')
                    left = pgMar.get(f'{W}left') if pgMar is not None else '?'
                    print(f"  [{idx}] type={type_val} → {label} (left={left})")

            # 替换 body-level sectPr (appendix)
            if appendix_sectPr is not None:
                for elem in list(body):
                    if elem.tag == f'{W}sectPr':
                        body.remove(elem)
                        break
                body.append(deepcopy(appendix_sectPr))

            result = True

        common.modify_docx_xml(docx_path, _restore)

        if result:
            print(f"  已恢复所有 sectPrs（按位置语义分配）")
        return result

    except Exception as e:
        print(f"  恢复 sectPrs 失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def _restore_final_sectPr(docx_path: str, template_sectPr) -> bool:
    """恢复文档末尾的 sectPr 为模板原始值。

    Args:
        docx_path: 输出文档路径
        template_sectPr: 从模板保存的 sectPr 元素

    Returns:
        是否成功
    """
    try:
        result = False

        def _restore(tree):
            nonlocal result
            body = tree.find(f'{W}body')
            if body is None:
                return

            for elem in list(body):
                if elem.tag == f'{W}sectPr':
                    body.remove(elem)
                    break

            body.append(deepcopy(template_sectPr))
            result = True

        common.modify_docx_xml(docx_path, _restore)

        if result:
            print(f"  已恢复文档末尾 sectPr（来自模板）")
        return result

    except Exception as e:
        print(f"  恢复 final sectPr 失败: {e}")
        return False


def _get_template_english_summary_margins(template_path: str) -> Dict[str, str]:
    """从模板的 ENGLISH_SUMMARY_MARKER 位置获取页边距。

    模板中的 "APPENDIX 1 Summary" 部分有自己的页边距设置，
    这个函数提取该位置的 sectPr 页边距，用于渲染时的格式化。

    Args:
        template_path: 模板文件路径

    Returns:
        页边距字典 {'top': '...', 'bottom': '...', 'left': '...', 'right': '...', ...}
    """
    ENGLISH_SUMMARY_MARKER = common.APPENDIX_1_MARKER
    margins = {}

    try:
        files = common.read_docx_zip(template_path)
        tree = etree.fromstring(files['word/document.xml'])

        body = tree.find(f'{W}body')
        if body is None:
            return margins

        # 找到 ENGLISH_SUMMARY_MARKER 的位置
        all_elements = list(body)
        marker_idx = None
        for idx, elem in enumerate(all_elements):
            text = common.get_element_text(elem)
            if ENGLISH_SUMMARY_MARKER in text:
                marker_idx = idx
                print(f"  找到 ENGLISH_SUMMARY_MARKER 在元素 {idx}")
                break

        if marker_idx is None:
            print(f"  未找到 ENGLISH_SUMMARY_MARKER")
            return margins

        # 在 marker 位置附近查找 sectPr
        for offset in [0, -1, -2, 1, 2]:
            check_idx = marker_idx + offset
            if 0 <= check_idx < len(all_elements):
                elem = all_elements[check_idx]
                tag = common.local_tag(elem)

                if tag == 'p':
                    pPr = elem.find(f'{W}pPr')
                    if pPr is not None:
                        sectPr = pPr.find(f'{W}sectPr')
                        if sectPr is not None:
                            pgMar = sectPr.find(f'{W}pgMar')
                            if pgMar is not None:
                                margins = common.extract_margins_from_pgMar(pgMar)
                                if margins:
                                    print(f"  从模板 ENGLISH_SUMMARY_MARKER 位置获取页边距: {margins}")
                                return margins

        # 如果在附近没找到，查找 marker 之前的最后一个 sectPr
        for i in range(marker_idx - 1, -1, -1):
            elem = all_elements[i]
            tag = common.local_tag(elem)

            if tag == 'p':
                pPr = elem.find(f'{W}pPr')
                if pPr is not None:
                    sectPr = pPr.find(f'{W}sectPr')
                    if sectPr is not None:
                        pgMar = sectPr.find(f'{W}pgMar')
                        if pgMar is not None:
                            margins = common.extract_margins_from_pgMar(pgMar)
                            if margins:
                                print(f"  从模板 marker 之前获取页边距: {margins}")
                            return margins

    except Exception as e:
        print(f"  读取模板 english_summary 页边距失败: {e}")

    return margins
