"""composer.py - 文档合并模块

提供使用 docxcompose 进行文档合并的功能。
"""

import shutil
import zipfile
from pathlib import Path
from copy import deepcopy
from typing import Dict, Any, Optional

try:
    from docx import Document
    from docxcompose.composer import Composer
    DOCXCOMPOSE_AVAILABLE = True
except ImportError:
    DOCXCOMPOSE_AVAILABLE = False
    Document = None
    Composer = None

import sys
SCRIPTS_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPTS_DIR))

import common
from sectpr_manager import (
    _save_all_template_sectPrs,
    _restore_all_sectPrs,
    _restore_final_sectPr,
    _save_template_final_sectPr,
)
from image_handler import _copy_media_between_docx

# 占位符标记
BODY_MARKER = common.BODY_MARKER


def insert_body_at_marker_compose(
    doc_path: str,
    body_path: str,
    marker: str,
    output_path: str,
    template_path: str = None,
    header_footer_mappings: Dict[str, Dict[str, str]] = None,
) -> bool:
    """使用 docxcompose 三段式合并：在 marker 位置插入 body。

    模板已分为 4 个 section（封面/body/英文摘要/法律披露），
    每个 section 自带 sectPr（含 header/footer 引用）。
    body 内容插入 body section 后自动继承该 section 的 header/footer，
    无需额外处理页眉页脚。

    Args:
        doc_path: 渲染后的模板路径
        body_path: body 文档路径
        marker: 占位符标记
        output_path: 输出路径
        template_path: 原始模板路径（用于恢复文档末尾 sectPr）
        header_footer_mappings: 已废弃参数，保留兼容性

    Returns:
        是否成功插入
    """
    if not DOCXCOMPOSE_AVAILABLE:
        print("  ⚠️ docxcompose 不可用，无法使用三段式合并")
        return False

    try:
        # 0. 保存模板的所有 sectPrs（docxcompose 会损坏它们）
        template_sectPrs = None
        if template_path:
            template_sectPrs = _save_all_template_sectPrs(template_path)

        # 1. 找到 marker 位置
        doc = Document(doc_path)
        body_elem = doc.element.body
        all_elements = list(body_elem)

        marker_idx = None
        for i, elem in enumerate(all_elements):
            text = ''.join(t.text or '' for t in elem.iter() if t.text)
            if marker in text:
                marker_idx = i
                break

        if marker_idx is None:
            return False

        # 2. 创建 part1（marker 之前的内容 = 封面 section）
        part1_path = Path(output_path).parent / "temp_part1.docx"
        shutil.copy(doc_path, str(part1_path))

        part1_doc = Document(str(part1_path))
        part1_body = part1_doc.element.body
        part1_elements = list(part1_body)

        for elem in part1_elements[marker_idx:]:
            tag = elem.tag.split('}')[-1]
            if tag != 'sectPr':
                part1_body.remove(elem)

        part1_doc.save(str(part1_path))

        # 3. 创建 part3（marker 之后的内容 = 英文摘要 + 法律披露 sections）
        part3_path = Path(output_path).parent / "temp_part3.docx"
        shutil.copy(doc_path, str(part3_path))

        part3_doc = Document(str(part3_path))
        part3_body = part3_doc.element.body
        part3_elements = list(part3_body)

        has_part3_content = False
        for elem in part3_elements[:marker_idx + 1]:
            tag = elem.tag.split('}')[-1]
            if tag != 'sectPr':
                part3_body.remove(elem)

        for elem in part3_body:
            tag = elem.tag.split('}')[-1]
            if tag in ['p', 'tbl', 'sdt']:
                text = ''.join(t.text or '' for t in elem.iter() if t.text)
                if text.strip():
                    has_part3_content = True
                    break

        if has_part3_content:
            part3_doc.save(str(part3_path))

        # 4. 合并：part1(封面) + body + part3(英文摘要+法律披露)
        master = Document(str(part1_path))
        composer = Composer(master)

        body_doc = Document(body_path)
        composer.append(body_doc, remove_property_fields=False)

        if has_part3_content:
            part3_for_merge = Document(str(part3_path))
            composer.append(part3_for_merge, remove_property_fields=False)

        composer.save(output_path)

        # 5. 恢复所有 sectPrs（docxcompose 会损坏 header/footer rId 引用）
        if template_sectPrs is not None:
            _restore_all_sectPrs(output_path, template_sectPrs)

        # 6. 补救：复制 body 中的图片资源
        copied_count = _copy_media_between_docx(body_path, output_path)
        if copied_count > 0:
            print(f"  已补充复制 {copied_count} 张图片（修复 docxcompose 图片丢失）")

        # 7. 清理临时文件
        part1_path.unlink(missing_ok=True)
        if has_part3_content:
            part3_path.unlink(missing_ok=True)

        return True

    except Exception as e:
        print(f"  docxcompose 三段式合并失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def _copy_headers_footers_between_docs(body_path: str, output_path: str) -> Dict[str, str]:
    """从 body 文档复制 header/footer 文件到输出文档。

    Args:
        body_path: body 文档路径
        output_path: 输出文档路径

    Returns:
        rId 映射字典
    """
    mapping = {}

    try:
        with zipfile.ZipFile(body_path, 'r') as z:
            body_files = {name: z.read(name) for name in z.namelist() if 'header' in name.lower() or 'footer' in name.lower()}

        with zipfile.ZipFile(output_path, 'r') as z:
            output_files = {name: z.read(name) for name in z.namelist()}

        # 复制 header/footer 文件
        for name, content in body_files.items():
            target_name = name
            if target_name not in output_files:
                output_files[target_name] = content

        import os
        os.remove(output_path)
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as z:
            for name, content in output_files.items():
                z.writestr(name, content)

    except Exception as e:
        print(f"  复制 headers/footers 时出错: {e}")

    return mapping
