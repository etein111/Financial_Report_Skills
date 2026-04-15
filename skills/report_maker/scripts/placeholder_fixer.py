"""placeholder_fixer.py - 占位符修复模块

修复 Word 中被拆分（split）的占位符。
Word 有时会将 {{ a1_email }} 这样的连续文本拆分成多个 run，
导致 Jinja2 无法正确识别和替换占位符。
"""

import zipfile
from lxml import etree
from copy import deepcopy

import common
W = common.W_NS


def fix_runs_in_parent(parent, collected_runs):
    """在父元素中合并收集的 runs。

    Args:
        parent: 父 XML 元素
        collected_runs: 要合并的 run 元素列表
    """
    if not collected_runs:
        return

    # 获取第一个 run 的索引位置
    first_run = collected_runs[0]
    parent_index = list(parent).index(first_run)

    # 合并文本内容到第一个 run
    merged_text = ''.join(run.text or '' for run in collected_runs)
    first_run.text = merged_text

    # 删除其他 runs
    for run in collected_runs[1:]:
        parent.remove(run)


def fix_element(elem, current_placeholder, collected_runs):
    """递归处理元素，收集属于同一占位符的 runs。

    Args:
        elem: 当前 XML 元素
        current_placeholder: 当前正在收集的占位符名称
        collected_runs: 收集的 run 元素列表

    Returns:
        处理完成后剩余的未完成占位符（以 {{ 开头但未找到 }}）
    """
    if elem.tag == f'{W}r':
        text = elem.text or ''

        # 检查是否包含占位符开始标记
        if PLACEHOLDER_START in text:
            if current_placeholder:
                # 之前有未完成的占位符，先合并
                fix_runs_in_parent(elem.getparent(), collected_runs)
                collected_runs.clear()
            current_placeholder = ''

        if current_placeholder is not None:
            current_placeholder += text

            if PLACEHOLDER_END in current_placeholder:
                # 找到完整的占位符
                collected_runs.append(elem)
                fix_runs_in_parent(elem.getparent(), collected_runs)
                collected_runs.clear()
                current_placeholder = None
            else:
                collected_runs.append(elem)
        else:
            # 在 {{ 之后、}} 之前的 run
            current_placeholder = text
            collected_runs.append(elem)

    elif elem.tag == f'{W}p':
        # 段落级别：先处理子元素，然后检查段落属性中的 sectPr
        current_placeholder = None
        collected_runs.clear()
        for child in elem:
            current_placeholder = fix_element(child, current_placeholder, collected_runs)

    else:
        # 其他元素：递归处理子元素
        for child in elem:
            current_placeholder = fix_element(child, current_placeholder, collected_runs)

    return current_placeholder


# 全局占位符标记
PLACEHOLDER_START = '{{'
PLACEHOLDER_END = '}}'


def _fix_split_placeholders_in_docx(docx_path: str, output_path: str = None) -> str:
    """修复模板中被拆分的占位符（Word 会把 {{ a1_email }} 拆成多个 run）。

    Args:
        docx_path: docx 文件路径
        output_path: 输出文件路径（如果为 None，则覆盖原文件）

    Returns:
        输出文件路径
    """
    if output_path is None:
        output_path = docx_path

    try:
        files = common.read_docx_zip(docx_path)

        if 'word/document.xml' not in files:
            return output_path

        doc_tree = etree.fromstring(files['word/document.xml'])
        body = doc_tree.find(f'{W}body')
        if body is None:
            return output_path

        for para in body.findall(f'.//{W}p'):
            current_placeholder = None
            collected_runs = []

            for child in para:
                current_placeholder = fix_element(child, current_placeholder, collected_runs)

        files['word/document.xml'] = etree.tostring(
            doc_tree, xml_declaration=True, encoding='UTF-8', standalone=True
        )

        common.write_docx_zip(output_path, files)

    except Exception as e:
        print(f"  修复拆分占位符时出错: {e}")

    return output_path
