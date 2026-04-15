"""post_processor.py - 后处理模块

提供渲染完成后的处理功能：验证附录、字体约束、分析师认证扩展等。
"""

import zipfile
from typing import Dict, Any
from lxml import etree

try:
    from docx import Document
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False
    Document = None

import common
W = common.W_NS


def _verify_appendix_with_lxml(doc_path: str) -> Dict[str, Any]:
    """使用 lxml 验证文档中是否存在法律附录。

    python-docx 的 doc.paragraphs 会漏读嵌套在复杂结构中的段落，
    所以需要直接用 lxml 解析 XML 来检测。

    Args:
        doc_path: 文档路径

    Returns:
        {"found": bool, "location": str, "text": str}
    """
    appendix_keywords = ['附录APPENDIX', 'IMPORTANT DISCLOSURE']

    try:
        with zipfile.ZipFile(doc_path, 'r') as z:
            with z.open('word/document.xml') as f:
                tree = etree.parse(f)

        # 搜索段落中的附录标记
        for idx, p in enumerate(tree.iter(f'{W}p')):
            text = common.get_element_text(p)
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
                    cell_text = common.get_element_text(tc)
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


def _apply_font_constraints(docx_path: str, chinese_font: str = '楷体', latin_font: str = 'Calibri') -> bool:
    """应用字体约束：中文使用楷体，英文使用 Calibri。

    直接修改 docx 的 XML，确保所有文本使用指定的字体。

    Args:
        docx_path: 文档路径
        chinese_font: 中文字体名称
        latin_font: 拉丁字体名称

    Returns:
        是否成功
    """
    if not DOCX_AVAILABLE:
        return False

    try:
        files = common.read_docx_zip(docx_path)

        if 'word/document.xml' not in files:
            return False

        doc_tree = etree.fromstring(files['word/document.xml'])

        def process_element(elem):
            if elem.tag == f'{W}r':
                # Run 元素
                rFonts = elem.find(f'{W}rFonts')
                if rFonts is None:
                    rFonts = etree.SubElement(elem, f'{W}rFonts')
                    # 插入到最前面
                    elem.insert(0, rFonts)

                rFonts.set(f'{W}ascii', latin_font)
                rFonts.set(f'{W}hAnsi', latin_font)
                rFonts.set(f'{W}eastAsia', chinese_font)
                rFonts.set(f'{W}cs', chinese_font)

            elif elem.tag == f'{W}p':
                # 段落属性
                pPr = elem.find(f'{W}pPr')
                if pPr is not None:
                    rPr = pPr.find(f'{W}rPr')
                    if rPr is not None:
                        rFonts = rPr.find(f'{W}rFonts')
                        if rFonts is None:
                            rFonts = etree.SubElement(rPr, f'{W}rFonts')

                        # 只设置 latin 和 eastAsia，保留其他设置
                        for attr in ['ascii', 'hAnsi']:
                            rFonts.set(f'{W}{attr}', latin_font)
                        for attr in ['eastAsia', 'cs']:
                            rFonts.set(f'{W}{attr}', chinese_font)

                # 处理段落内的 runs
                for child in elem:
                    process_element(child)

            elif elem.tag in [f'{W}tbl', f'{W}tr', f'{W}tc']:
                # 表格元素，递归处理
                for child in elem:
                    process_element(child)

        # 处理文档主体
        body = doc_tree.find(f'{W}body')
        if body is not None:
            for elem in body:
                process_element(elem)

        files['word/document.xml'] = etree.tostring(
            doc_tree, xml_declaration=True, encoding='UTF-8', standalone=True
        )

        common.write_docx_zip(docx_path, files)

        return True

    except Exception as e:
        print(f"  应用字体约束失败: {e}")
        return False


def set_run_font(run, font_name: str, font_type: str = 'ascii'):
    """设置 run 的字体。

    Args:
        run: run 元素
        font_name: 字体名称
        font_type: 字体类型 (ascii, hAnsi, eastAsia, cs)
    """
    rPr = run.get_or_add_rPr()
    rFonts = rPr.find(f'{W}rFonts')
    if rFonts is None:
        rFonts = etree.SubElement(rPr, f'{W}rFonts')

    rFonts.set(f'{W}{font_type}', font_name)


def expand_analyst_certification(docx_path: str, elements: Dict[str, Any]) -> int:
    """扩展分析师认证声明段落。

    为多个分析师复制声明段落。模板中只有一个占位符段落，
    需要根据分析师数量复制多份。

    Args:
        docx_path: 文档路径
        elements: 要素字典

    Returns:
        新增的分析师声明段落数量
    """
    if not DOCX_AVAILABLE:
        return 0

    certification_keywords = ['分析师', 'analyst', '认证', 'certification']

    try:
        files = common.read_docx_zip(docx_path)

        if 'word/document.xml' not in files:
            return 0

        doc_tree = etree.fromstring(files['word/document.xml'])
        body = doc_tree.find(f'{W}body')

        analyst_count = 0
        for i in range(1, 9):
            if elements.get(f'a{i}_name') or elements.get(f'a{i}_cn') or elements.get(f'a{i}_en'):
                analyst_count += 1

        if analyst_count <= 1:
            return 0  # 只有一个分析师，不需要扩展

        certification_paras = []
        for p in body.findall(f'{W}p'):
            text = common.get_element_text(p)
            text_lower = text.lower()
            if any(kw in text_lower for kw in certification_keywords):
                certification_paras.append(p)

        if not certification_paras:
            return 0

        # 复制声明段落（除了第一个）
        copied_count = 0
        for _ in range(analyst_count - 1):
            for para in certification_paras:
                new_para = deepcopy(para)
                body.append(new_para)
                copied_count += 1

        if copied_count > 0:
            files['word/document.xml'] = etree.tostring(
                doc_tree, xml_declaration=True, encoding='UTF-8', standalone=True
            )

            common.write_docx_zip(docx_path, files)

        return copied_count

    except Exception as e:
        print(f"  扩展分析师认证声明失败: {e}")
        return 0
