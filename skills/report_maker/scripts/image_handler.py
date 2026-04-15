"""image_handler.py - 图片处理模块

提供图表插入、Jinja2 转义、图片复制等功能。
"""

import zipfile
import hashlib
import re
from typing import Dict, Any
from pathlib import Path
from lxml import etree

import common
W = common.W_NS

# 尝试导入 docx
try:
    from docx import Document
    from docx.shared import Cm
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False
    Document = None
    Cm = None


def _escape_jinja_in_charts(docx_path: str) -> Dict[str, str]:
    """转义图表 XML 中的 Jinja2 语法，防止 docxtpl 解析错误。

    Word 图表的数据存储在 word/charts/*.xml 文件中，
    如果图表数据包含 {{ }} 语法，Jinja2 会尝试解析导致错误。

    Args:
        docx_path: docx 文件路径

    Returns:
        被转义的文件内容字典 {文件名: 原始内容}，用于后续恢复
    """
    escaped_files = {}

    try:
        with zipfile.ZipFile(docx_path, 'r') as z:
            chart_files = [name for name in z.namelist() if name.startswith('word/charts/') and name.endswith('.xml')]

            for chart_file in chart_files:
                content = z.read(chart_file).decode('utf-8')
                # 转义 {{ 和 }} 为临时标记
                escaped = content.replace('{{', '__JINJA_LBRACE__').replace('}}', '__JINJA_RBRACE__')
                if escaped != content:
                    escaped_files[chart_file] = content
                    # 写入转义后的内容
                    with zipfile.ZipFile(docx_path, 'a') as z_out:
                        z_out.writestr(chart_file, escaped.encode('utf-8'))

    except Exception as e:
        print(f"  转义图表 Jinja2 语法时出错: {e}")

    return escaped_files


def _restore_jinja_in_charts(docx_path: str, escaped_files: Dict[str, str]) -> None:
    """恢复图表 XML 中被转义的 Jinja2 语法。

    Args:
        docx_path: docx 文件路径
        escaped_files: 被转义的文件内容字典
    """
    if not escaped_files:
        return

    try:
        # 重新读取，打包所有文件
        with zipfile.ZipFile(docx_path, 'r') as z:
            files = {name: z.read(name) for name in z.namelist()}

        # 恢复被转义的文件
        for chart_file, original_content in escaped_files.items():
            if chart_file in files:
                # 恢复 {{ 和 }}
                restored = original_content.replace('__JINJA_LBRACE__', '{{').replace('__JINJA_RBRACE__', '}}')
                files[chart_file] = restored.encode('utf-8')

        # 写回
        import os
        os.remove(docx_path)
        with zipfile.ZipFile(docx_path, 'w', zipfile.ZIP_DEFLATED) as z:
            for name, content in files.items():
                z.writestr(name, content)

    except Exception as e:
        print(f"  恢复图表 Jinja2 语法时出错: {e}")


def _insert_image_to_placeholder(
    doc: Document,
    placeholder: str,
    image_path: str,
    width_cm: float = None
) -> bool:
    """在文档的占位符位置插入图片。

    Args:
        doc: Document 对象
        placeholder: 占位符文本
        image_path: 图片文件路径
        width_cm: 图片宽度（厘米）

    Returns:
        是否成功插入
    """
    if not DOCX_AVAILABLE:
        return False

    try:
        from docx.oxml import OxmlElement
        from docx.oxml.ns import qn

        for para in doc.paragraphs:
            if placeholder in para.text:
                # 找到包含占位符的 run
                for run in para.runs:
                    if placeholder in run.text:
                        run.text = run.text.replace(placeholder, '')

                        # 添加图片
                        run.add_picture(image_path)
                        if width_cm:
                            # 设置图片宽度
                            last_picture = run._element.getparent().findall('.//{http://schemas.openxmlformats.org/drawingml/2006/picture}pic')
                            if last_picture:
                                size = last_picture[-1].find('.//{http://schemas.openxmlformats.org/drawingml/2006/main}ext')
                                if size is not None:
                                    size.set('{http://schemas.openxmlformats.org/drawingml/2006/main}cx', str(int(width_cm * 914400)))
                                    size.set('{http://schemas.openxmlformats.org/drawingml/2006/main}cy', str(int(width_cm * 914400 * 0.75)))

                        return True

        # 尝试在表格中查找
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    if placeholder in cell.text:
                        # 简化处理：清除占位符文本
                        cell.text = cell.text.replace(placeholder, '')
                        return True

        return False

    except Exception as e:
        print(f"  插入图片失败: {e}")
        return False


def _copy_media_between_docx(source_path: str, target_path: str) -> int:
    """从源 docx 复制所有媒体资源到目标 docx。

    使用 zipfile 直接操作，确保图片文件被正确复制。
    当 body_doc 的 XML 被 deepcopy 到 master_doc 后，图片引用（rId）会被保留，
    但目标文档的 rels 文件中没有对应的关系。本函数补充这些缺失的关系。

    Args:
        source_path: 源 docx 文件路径（如 body.docx）
        target_path: 目标 docx 文件路径（如 output.docx）

    Returns:
        复制的媒体文件数量
    """
    copied_count = 0

    try:
        source_rid_to_media = {}  # {rId: (media_name, media_bytes, media_hash)}

        with zipfile.ZipFile(source_path, 'r') as z:
            for name in z.namelist():
                if name.startswith('word/media/'):
                    media_bytes = z.read(name)
                    media_hash = hashlib.md5(media_bytes).hexdigest()
                    source_rid_to_media[f'_h_{media_hash}'] = (name[5:], media_bytes, media_hash)

            if 'word/_rels/document.xml.rels' in z.namelist():
                rels_xml = z.read('word/_rels/document.xml.rels')
                rels_tree = etree.fromstring(rels_xml)
                ns = {'r': 'http://schemas.openxmlformats.org/package/2006/relationships'}
                for rel in rels_tree.findall('r:Relationship', ns):
                    rel_id = rel.get('Id')
                    target = rel.get('Target')
                    rel_type = rel.get('Type')
                    if target and target.startswith('media/') and 'image' in rel_type:
                        media_name = target
                        if f'word/{media_name}' in z.namelist():
                            media_bytes = z.read(f'word/{media_name}')
                            media_hash = hashlib.md5(media_bytes).hexdigest()
                            source_rid_to_media[rel_id] = (media_name, media_bytes, media_hash)

        with zipfile.ZipFile(target_path, 'r') as z:
            target_media = {name for name in z.namelist() if name.startswith('word/media/')}
            target_rels = {}
            if 'word/_rels/document.xml.rels' in z.namelist():
                rels_xml = z.read('word/_rels/document.xml.rels')
                rels_tree = etree.fromstring(rels_xml)
                ns = {'r': 'http://schemas.openxmlformats.org/package/2006/relationships'}
                for rel in rels_tree.findall('r:Relationship', ns):
                    rid = rel.get('Id')
                    target_rels[rid] = rel.get('Target', '')

        missing_media = []
        for rid, (media_name, media_bytes, media_hash) in source_rid_to_media.items():
            if rid not in target_rels:
                missing_media.append((media_name, media_bytes))

        if missing_media:
            with zipfile.ZipFile(target_path, 'r') as z:
                files = {name: z.read(name) for name in z.namelist()}

            for media_name, media_bytes in missing_media:
                target_media_name = f'word/media/{Path(media_name).name}'
                if target_media_name not in files:
                    files[target_media_name] = media_bytes
                    copied_count += 1

            import os
            os.remove(target_path)
            with zipfile.ZipFile(target_path, 'w', zipfile.ZIP_DEFLATED) as z:
                for name, content in files.items():
                    z.writestr(name, content)

    except Exception as e:
        print(f"  复制媒体文件时出错: {e}")

    return copied_count
