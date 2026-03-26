#!/usr/bin/env python3
"""
独立脚本：复制 body.docx 的页眉页脚到 output.docx

用法:
    python copy_headers_footers.py <output_path> <body_path>

此脚本可用于在文档合并后复制页眉页脚。
"""
import sys
from pathlib import Path
from copy import deepcopy
from docx import Document


def copy_headers_footers(output_path: str, body_path: str, verbose: bool = False) -> bool:
    """
    复制 body.docx 的页眉页脚到 output.docx

    Args:
        output_path: 输出文档路径
        body_path: body.docx 路径
        verbose: 是否输出详细信息

    Returns:
        bool: 是否成功
    """
    try:
        output_doc = Document(output_path)
        body_doc = Document(body_path)

        # 只复制 body section 0 的页眉页脚到 output section 1
        # （section 0 是封面，section 1 是正文开始）
        if len(body_doc.sections) > 0 and len(output_doc.sections) > 1:
            source_section = body_doc.sections[0]
            target_section = output_doc.sections[1]

            # 复制设置
            target_section.different_first_page_header_footer = source_section.different_first_page_header_footer

            # 复制默认页眉
            target_section.header.is_linked_to_previous = False
            for child in list(target_section.header._element):
                target_section.header._element.remove(child)
            for child in source_section.header._element:
                target_section.header._element.append(deepcopy(child))

            # 复制默认页脚
            target_section.footer.is_linked_to_previous = False
            for child in list(target_section.footer._element):
                target_section.footer._element.remove(child)
            for child in source_section.footer._element:
                target_section.footer._element.append(deepcopy(child))

            # 复制首页页眉
            try:
                target_section.first_page_header.is_linked_to_previous = False
                for child in list(target_section.first_page_header._element):
                    target_section.first_page_header._element.remove(child)
                for child in source_section.first_page_header._element:
                    target_section.first_page_header._element.append(deepcopy(child))
            except Exception:
                pass

            # 复制首页页脚
            try:
                target_section.first_page_footer.is_linked_to_previous = False
                for child in list(target_section.first_page_footer._element):
                    target_section.first_page_footer._element.remove(child)
                for child in source_section.first_page_footer._element:
                    target_section.first_page_footer._element.append(deepcopy(child))
            except Exception:
                pass

        output_doc.save(output_path)
        if verbose:
            print(f"已复制页眉页脚: {body_path} -> {output_path}")
        return True

    except Exception as e:
        print(f"复制页眉页脚失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"用法: {sys.argv[0]} <output_path> <body_path>")
        sys.exit(1)

    output_path = sys.argv[1]
    body_path = sys.argv[2]

    if not Path(output_path).exists():
        print(f"错误: 文件不存在: {output_path}")
        sys.exit(1)

    if not Path(body_path).exists():
        print(f"错误: 文件不存在: {body_path}")
        sys.exit(1)

    success = copy_headers_footers(output_path, body_path, verbose=True)
    sys.exit(0 if success else 1)
