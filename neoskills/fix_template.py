#!/usr/bin/env python3
"""修复 template.py 中的 save_document_with_cleanup 函数"""

with open('skills/template_maker/scripts/template.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_func = '''def save_document_with_cleanup(doc: Document, output_path: str) -> None:
    """保存 Word 文档并清理孤立的嵌入对象（图表、Excel 等）。

    当删除正文区域后，原有的图表和嵌入对象可能不再被引用，
    此函数会自动清理这些孤立文件，减小文档大小。

    Args:
        doc: Document 对象
        output_path: 输出路径
    """
    import zipfile
    import tempfile
    from lxml import etree

    with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as tmp:
        tmp_path = tmp.name
    doc.save(tmp_path)

    used_files = set()
    try:
        with zipfile.ZipFile(tmp_path, 'r') as z:
            rId_to_target = {}
            try:
                with z.open('word/_rels/document.xml.rels') as f:
                    tree = etree.parse(f)
                    for rel in tree.iter('{http://schemas.openxmlformats.org/package/2006/relationships}Relationship'):
                        rid = rel.get('Id')
                        target = rel.get('Target')
                        if rid and target:
                            rId_to_target[rid] = target
            except KeyError:
                pass

            chart_ole_refs = set()
            for name in z.namelist():
                if name.startswith('word/charts/_rels/') and name.endswith('.xml.rels'):
                    try:
                        with z.open(name) as f:
                            chart_tree = etree.parse(f)
                            for rel in chart_tree.iter('{http://schemas.openxmlformats.org/package/2006/relationships}Relationship'):
                                target = rel.get('Target')
                                rel_type = rel.get('Type')
                                if target and ('oleObject' in rel_type or 'Workbook' in target):
                                    if 'embeddings/' in target:
                                        fname = target.split('embeddings/')[-1]
                                        chart_ole_refs.add(f'embeddings/{fname}')
                                    elif target.startswith('embeddings/'):
                                        chart_ole_refs.add(target)
                    except Exception:
                        pass

            for rid, target in rId_to_target.items():
                if 'embeddings/' in target:
                    used_files.add(target)
                elif target.startswith('../embeddings/'):
                    used_files.add(target.replace('../', ''))
            for ref in chart_ole_refs:
                if 'embeddings/' in ref:
                    used_files.add(ref)

            essential_files = {'word/document.xml', 'word/styles.xml', 'word/settings.xml',
                             'word/numbering.xml', 'Content_Types.xml', '[Content_Types].xml'}

            referenced_charts = set()
            for rid, target in rId_to_target.items():
                if 'charts/chart' in target:
                    if target.startswith('charts/'):
                        referenced_charts.add(f'word/{target}')
                    elif target.startswith('word/charts/'):
                        referenced_charts.add(target)

            referenced_embeddings = set()
            for rid, target in rId_to_target.items():
                if 'embeddings/' in target:
                    referenced_embeddings.add(f'word/{target}')
                elif target.startswith('../embeddings/'):
                    referenced_embeddings.add(f'word/{target.replace("../", "")}')
            for ref in chart_ole_refs:
                if ref.startswith('embeddings/'):
                    referenced_embeddings.add(f'word/{ref}')

            all_files = set(z.namelist())
            files_to_delete = set()
            for f in all_files:
                if f in essential_files or f.startswith('word/_rels/'):
                    continue
                if '/_rels/' in f or f.endswith('.rels'):
                    continue
                if f.startswith('word/charts/chart'):
                    if f.endswith('.xml.rels'):
                        continue
                    if f not in referenced_charts:
                        files_to_delete.add(f)
                        files_to_delete.add(f + '.rels')
                elif f.startswith('word/embeddings/'):
                    if f not in referenced_embeddings:
                        files_to_delete.add(f)

            if not files_to_delete:
                with open(output_path, 'wb') as dst:
                    with open(tmp_path, 'rb') as src:
                        dst.write(src.read())
                Path(tmp_path).unlink(missing_ok=True)
                return

            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as new_z:
                for item in z.namelist():
                    if item not in files_to_delete:
                        new_z.writestr(item, z.read(item))
            Path(tmp_path).unlink(missing_ok=True)
            print(f'  已清理 {len(files_to_delete)} 个孤立文件')
    except Exception as e:
        import shutil
        shutil.copy(tmp_path, output_path)
        Path(tmp_path).unlink(missing_ok=True)
        print(f'  清理失败，使用原始保存: {e}')'''

new_func = '''def save_document_with_cleanup(doc: Document, output_path: str) -> None:
    """保存 Word 文档并清理孤立的嵌入对象（图表、Excel 等）。

    当删除正文区域后，原有的图表和嵌入对象可能不再被引用，
    此函数会自动清理这些孤立文件，减小文档大小。

    Args:
        doc: Document 对象
        output_path: 输出路径
    """
    import zipfile
    import io
    from lxml import etree

    # 先保存到内存
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    doc_bytes = buffer.read()

    used_files = set()
    try:
        with zipfile.ZipFile(io.BytesIO(doc_bytes), 'r') as z:
            rId_to_target = {}
            try:
                with z.open('word/_rels/document.xml.rels') as f:
                    tree = etree.parse(f)
                    for rel in tree.iter('{http://schemas.openxmlformats.org/package/2006/relationships}Relationship'):
                        rid = rel.get('Id')
                        target = rel.get('Target')
                        if rid and target:
                            rId_to_target[rid] = target
            except KeyError:
                pass

            chart_ole_refs = set()
            for name in z.namelist():
                if name.startswith('word/charts/_rels/') and name.endswith('.xml.rels'):
                    try:
                        with z.open(name) as f:
                            chart_tree = etree.parse(f)
                            for rel in chart_tree.iter('{http://schemas.openxmlformats.org/package/2006/relationships}Relationship'):
                                target = rel.get('Target')
                                rel_type = rel.get('Type')
                                if target and ('oleObject' in rel_type or 'Workbook' in target):
                                    if 'embeddings/' in target:
                                        fname = target.split('embeddings/')[-1]
                                        chart_ole_refs.add(f'embeddings/{fname}')
                                    elif target.startswith('embeddings/'):
                                        chart_ole_refs.add(target)
                    except Exception:
                        pass

            for rid, target in rId_to_target.items():
                if 'embeddings/' in target:
                    used_files.add(target)
                elif target.startswith('../embeddings/'):
                    used_files.add(target.replace('../', ''))
            for ref in chart_ole_refs:
                if 'embeddings/' in ref:
                    used_files.add(ref)

            essential_files = {'word/document.xml', 'word/styles.xml', 'word/settings.xml',
                             'word/numbering.xml', 'Content_Types.xml', '[Content_Types].xml'}

            referenced_charts = set()
            for rid, target in rId_to_target.items():
                if 'charts/chart' in target:
                    if target.startswith('charts/'):
                        referenced_charts.add(f'word/{target}')
                    elif target.startswith('word/charts/'):
                        referenced_charts.add(target)

            referenced_embeddings = set()
            for rid, target in rId_to_target.items():
                if 'embeddings/' in target:
                    referenced_embeddings.add(f'word/{target}')
                elif target.startswith('../embeddings/'):
                    referenced_embeddings.add(f'word/{target.replace("../", "")}')
            for ref in chart_ole_refs:
                if ref.startswith('embeddings/'):
                    referenced_embeddings.add(f'word/{ref}')

            all_files = set(z.namelist())
            files_to_delete = set()
            for f in all_files:
                if f in essential_files or f.startswith('word/_rels/'):
                    continue
                if '/_rels/' in f or f.endswith('.rels'):
                    continue
                if f.startswith('word/charts/chart'):
                    if f.endswith('.xml.rels'):
                        continue
                    if f not in referenced_charts:
                        files_to_delete.add(f)
                        files_to_delete.add(f + '.rels')
                elif f.startswith('word/embeddings/'):
                    if f not in referenced_embeddings:
                        files_to_delete.add(f)

            if not files_to_delete:
                with open(output_path, 'wb') as dst:
                    dst.write(doc_bytes)
                return

            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as new_z:
                for item in z.namelist():
                    if item not in files_to_delete:
                        new_z.writestr(item, z.read(item))
            print(f'  已清理 {len(files_to_delete)} 个孤立文件')
    except Exception as e:
        with open(output_path, 'wb') as dst:
            dst.write(doc_bytes)
        print(f'  清理失败，使用原始保存: {e}')'''

if old_func in content:
    new_content = content.replace(old_func, new_func)
    with open('skills/template_maker/scripts/template.py', 'w', encoding='utf-8') as f:
        f.write(new_content)
    print('Function updated successfully')
else:
    print('Could not find old function to replace')
