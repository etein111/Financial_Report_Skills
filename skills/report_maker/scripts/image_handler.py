"""image_handler.py - 图片处理模块

提供图表插入、Jinja2 转义、图片复制等功能。
"""

import hashlib
from typing import Dict, Any
from pathlib import Path
from lxml import etree

import common
W = common.W_NS

# 图片宽高比（4:3）
_ASPECT_RATIO = 0.75
# EMU (English Metric Units) per centimeter (1 cm = 914400 EMU)
EMU_PER_CM = 914400
# Jinja2 escape tokens for chart XML
_JINJA_LBRACE_ESC = '__JINJA_LBRACE__'
_JINJA_RBRACE_ESC = '__JINJA_RBRACE__'

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
        files = common.read_docx_zip(docx_path)

        for name, content in files.items():
            if not (name.startswith('word/charts/') and name.endswith('.xml')):
                continue
            text = content.decode('utf-8')
            escaped = text.replace('{{', _JINJA_LBRACE_ESC).replace('}}', _JINJA_RBRACE_ESC)
            if escaped != text:
                escaped_files[name] = text
                files[name] = escaped.encode('utf-8')

        if escaped_files:
            common.write_docx_zip(docx_path, files)

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
        files = common.read_docx_zip(docx_path)

        for name, original in escaped_files.items():
            restored = original.replace(
                _JINJA_LBRACE_ESC, '{{').replace(_JINJA_RBRACE_ESC, '}}')
            files[name] = restored.encode('utf-8')

        common.write_docx_zip(docx_path, files)

    except Exception as e:
        print(f"  恢复图表 Jinja2 语法时出错: {e}")


def _replace_in_nested_tables(doc, elem, placeholder, image_path, width_cm=None):
    """处理嵌套表格中的占位符，直接遍历不递归。"""
    from docx.oxml.ns import qn
    
    replaced = False
    processed_runs = set()  # 避免重复处理同一个 run
    
    # 直接遍历 body 中所有的 w:r 元素
    for r_elem in elem.iter(qn('w:r')):
        # 跳过已处理的
        if id(r_elem) in processed_runs:
            continue
        
        combined = common.get_element_text(r_elem)

        if placeholder in combined:
            # 找到包含占位符的 run
            p_elem = r_elem.getparent()
            while p_elem is not None and p_elem.tag != qn('w:p'):
                p_elem = p_elem.getparent()
            
            if p_elem is not None:
                from docx.text.paragraph import Paragraph
                para_obj = Paragraph(p_elem, doc)
                
                for run_obj in para_obj.runs:
                    run_combined = common.get_element_text(run_obj._element)
                    if placeholder in run_combined:
                        # 标记为已处理
                        processed_runs.add(id(run_obj._element))
                        
                        run_obj.text = run_obj.text.replace(placeholder, '')
                        if width_cm:
                            from docx.shared import Cm
                            run_obj.add_picture(image_path, width=Cm(width_cm))
                        else:
                            run_obj.add_picture(image_path)
                        replaced = True
                        break
    
    return replaced


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

        # 1. 先在段落中查找
        for para in doc.paragraphs:
            if placeholder in para.text:
                for run in para.runs:
                    if placeholder in run.text:
                        run.text = run.text.replace(placeholder, '')
                        if width_cm:
                            from docx.shared import Cm
                            run.add_picture(image_path, width=Cm(width_cm))
                        else:
                            run.add_picture(image_path)
                        return True

        # 2. 在文档 body 中递归搜索所有嵌套表格
        body = doc.element.body
        if _replace_in_nested_tables(doc, body, placeholder, image_path, width_cm):
            return True

        return False

    except Exception as e:
        print(f"  插入图片失败: {e}")
        return False


def _copy_media_between_docx(source_path: str, target_path: str) -> int:
    """从源 docx 复制所有媒体资源到目标 docx。

    使用 common.read_docx_zip / write_docx_zip 操作，确保图片文件被正确复制。
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
        source_files = common.read_docx_zip(source_path)

        for name, media_bytes in source_files.items():
            if name.startswith('word/media/'):
                media_hash = hashlib.md5(media_bytes).hexdigest()
                source_rid_to_media[f'_h_{media_hash}'] = (name[5:], media_bytes, media_hash)

        rels_xml = source_files.get('word/_rels/document.xml.rels')
        if rels_xml:
            rels_tree = etree.fromstring(rels_xml)
            ns = {'r': 'http://schemas.openxmlformats.org/package/2006/relationships'}
            for rel in rels_tree.findall('r:Relationship', ns):
                rel_id = rel.get('Id')
                target = rel.get('Target')
                rel_type = rel.get('Type')
                if target and target.startswith('media/') and 'image' in rel_type:
                    media_name = target
                    media_bytes = source_files.get(f'word/{media_name}')
                    if media_bytes:
                        media_hash = hashlib.md5(media_bytes).hexdigest()
                        source_rid_to_media[rel_id] = (media_name, media_bytes, media_hash)

        target_files = common.read_docx_zip(target_path)
        target_rels = {}
        target_rels_xml = target_files.get('word/_rels/document.xml.rels')
        if target_rels_xml:
            rels_tree = etree.fromstring(target_rels_xml)
            ns = {'r': 'http://schemas.openxmlformats.org/package/2006/relationships'}
            for rel in rels_tree.findall('r:Relationship', ns):
                rid = rel.get('Id')
                target_rels[rid] = rel.get('Target', '')

        missing_media = []
        for rid, (media_name, media_bytes, media_hash) in source_rid_to_media.items():
            if rid not in target_rels:
                missing_media.append((media_name, media_bytes))

        if missing_media:
            for media_name, media_bytes in missing_media:
                target_media_name = f'word/media/{Path(media_name).name}'
                if target_media_name not in target_files:
                    target_files[target_media_name] = media_bytes
                    copied_count += 1

            common.write_docx_zip(target_path, target_files)

    except Exception as e:
        print(f"  复制媒体文件时出错: {e}")

    return copied_count
