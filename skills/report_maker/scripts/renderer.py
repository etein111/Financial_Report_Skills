"""renderer.py - 模板渲染模块（主入口）

负责 Word 模板渲染、fragment 插入和 PDF 转换。
实际功能分散到以下模块：
- context.py: 上下文准备
- chart_generator.py: 图表生成
- image_handler.py: 图片处理
- placeholder_fixer.py: 占位符修复
- sectpr_manager.py: sectPr 管理
- composer.py: 文档合并
- content_inserter.py: 内容插入
- post_processor.py: 后处理
"""

from typing import Dict, Any
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import sys

SCRIPTS_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPTS_DIR))

# 尝试导入依赖
try:
    from docx import Document
    from docxtpl import DocxTemplate
    DOCX_AVAILABLE = True
except ImportError as e:
    print(f"Warning: {e}")
    Document = None
    DocxTemplate = None
    DOCX_AVAILABLE = False

import common

# 从各模块导入函数
from context import (
    enrich_company_names_with_yfinance,
    prepare_context_with_analysts,
)

from chart_generator import (
    _generate_relative_chart,
    _generate_recommendation_chart,
)

from image_handler import (
    _escape_jinja_in_charts,
    _restore_jinja_in_charts,
    _insert_image_to_placeholder,
    _copy_media_between_docx,
)

from placeholder_fixer import _fix_split_placeholders_in_docx

from sectpr_manager import (
    _save_template_final_sectPr,
    _restore_final_sectPr,
    _get_template_english_summary_margins,
)

from composer import insert_body_at_marker_compose

from content_inserter import (
    insert_abstract_to_cell,
    _insert_abstract_at_paragraph,
    _apply_english_summary_margins_doc,
)

from post_processor import (
    _verify_appendix_with_lxml,
    _apply_font_constraints,
    expand_analyst_certification,
)


def render_report(
    template_path: str,
    elements: Dict[str, Any],
    abstract_path: str,
    body_path: str,
    output_path: str,
    english_summary_path: str = None,
    neolyst_client=None,
) -> bool:
    """渲染报告，正确处理分析师字段、abstract、body 和 english_summary。

    模板已分为 4 个 section（封面/body/英文摘要/法律披露），
    每个 section 自带 sectPr（含 header/footer 引用）。
    插入内容后自动继承对应 section 的 header/footer，
    无需额外处理页眉页脚。

    Args:
        template_path: 模板文件路径
        elements: 要素字典
        abstract_path: 摘要文件路径
        body_path: 正文文件路径
        output_path: 输出文件路径
        english_summary_path: 英文摘要文件路径（可选）
        neolyst_client: 已认证的 Supabase client（可选，用于获取历史推荐数据）

    Returns:
        是否成功
    """
    if not DOCX_AVAILABLE:
        print("Error: python-docx or docxtpl not installed")
        return False

    try:
        elements = enrich_company_names_with_yfinance(elements)

        context = prepare_context_with_analysts(elements)


        context['abstract'] = common.ABSTRACT_MARKER
        context['body'] = common.BODY_MARKER
        context['english_summary'] = common.ENGLISH_SUMMARY_MARKER
        context['relative_chart'] = common.RELATIVE_CHART_MARKER
        context['recommendation_chart'] = common.RECOMMENDATION_CHART_MARKER

        temp_path = Path(output_path).parent / "temp_rendered.docx"
        fixed_template_path = Path(output_path).parent / "temp_fixed_template.docx"
        _fix_split_placeholders_in_docx(template_path, str(fixed_template_path))

        escaped_chart_files = _escape_jinja_in_charts(str(fixed_template_path))
        if escaped_chart_files:
            print(f"  已转义 {len(escaped_chart_files)} 个图表文件中的 Jinja2 语法")

        expanded_analysts = expand_analyst_certification(str(fixed_template_path), elements)
        if expanded_analysts > 0:
            print(f"  已扩展分析师认证声明（新增 {expanded_analysts} 个分析师）")

        ticker = elements.get('ticker', '')
        relative_chart_generated = False
        recommendation_chart_generated = False

        if ticker:
            report_dir = Path(output_path).parent
            relative_chart_path = report_dir / "relative_chart.png"
            recommendation_chart_path = report_dir / "recommendation_chart.png"

            with ThreadPoolExecutor(max_workers=2) as executor:
                rel_future = executor.submit(
                    _generate_relative_chart,
                    ticker, str(relative_chart_path), elements.get('company_en')
                )
                rec_future = executor.submit(
                    _generate_recommendation_chart,
                    ticker, str(recommendation_chart_path),
                    elements.get('company_en') or elements.get('company_cn', ''), elements,
                    neolyst_client
                )
                relative_chart_generated = rel_future.result()
                recommendation_chart_generated = rec_future.result()

            if relative_chart_generated:
                print(f"  ✅ relative_chart 已生成")
            else:
                print(f"  ⚠️ relative_chart 生成失败")
            if recommendation_chart_generated:
                print(f"  ✅ recommendation_chart 已生成")
            else:
                print(f"  ⚠️ recommendation_chart 生成失败")
        else:
            print(f"  ⚠️ 无 ticker，跳过图表生成")

        template = DocxTemplate(str(fixed_template_path))
        template.render(context)
        template.save(str(temp_path))

        doc = Document(str(temp_path))

        if Path(abstract_path).exists() and Path(abstract_path).stat().st_size > 0:
            abstract_doc = Document(abstract_path)
            abstract_inserted = insert_abstract_to_cell(doc, abstract_doc, common.ABSTRACT_MARKER)
            if abstract_inserted:
                print(f"  已在 ABSTRACT_MARKER 位置插入 abstract")
            else:
                abstract_inserted = _insert_abstract_at_paragraph(doc, abstract_doc, common.ABSTRACT_MARKER)
                if abstract_inserted:
                    print(f"  已在段落中插入 abstract")
                else:
                    print(f"  ⚠️ 未找到 ABSTRACT_MARKER，abstract 未插入")

        doc.save(str(temp_path))

        if Path(body_path).exists() and Path(body_path).stat().st_size > 0:
            body_inserted = insert_body_at_marker_compose(
                str(temp_path), body_path, common.BODY_MARKER, output_path,
                template_path=template_path
            )

            if body_inserted:
                print(f"  已使用 docxcompose 三段式合并插入 body")
                doc = Document(output_path)
            else:
                print(f"  ⚠️ 未找到 BODY_MARKER，使用 docxcompose 追加 body")
                from docxcompose.composer import Composer
                doc = Document(str(temp_path))
                composer = Composer(doc)
                composer.append(Document(body_path), remove_property_fields=False)
                composer.save(output_path)

                template_final_sectPr = _save_template_final_sectPr(template_path)
                if template_final_sectPr is not None:
                    _restore_final_sectPr(output_path, template_final_sectPr)

                copied_count = _copy_media_between_docx(body_path, output_path)
                if copied_count > 0:
                    print(f"  已补充复制 {copied_count} 张图片")

                doc = Document(output_path)

        else:
            doc = Document(str(temp_path))
            body_elem = doc.element.body
            for elem in list(body_elem):
                text = common.get_element_text(elem)
                if common.BODY_MARKER in text:
                    body_elem.remove(elem)
                    print(f"  已删除 BODY_MARKER（无 body 文件）")
                    break
            doc.save(output_path)

        if english_summary_path and Path(english_summary_path).exists() and Path(english_summary_path).stat().st_size > 0:
            english_summary_doc = Document(english_summary_path)

            es_margins = _get_template_english_summary_margins(str(fixed_template_path))
            if es_margins:
                print(f"  模板 ENGLISH_SUMMARY 页边距: top={es_margins.get('top')}, bottom={es_margins.get('bottom')}, left={es_margins.get('left')}")

            es_inserted = insert_abstract_to_cell(doc, english_summary_doc, common.ENGLISH_SUMMARY_MARKER)
            if es_inserted:
                print(f"  已在 ENGLISH_SUMMARY_MARKER 位置插入 english_summary")
            else:
                es_inserted = _insert_abstract_at_paragraph(doc, english_summary_doc, common.ENGLISH_SUMMARY_MARKER)
                if es_inserted:
                    print(f"  已在段落中插入 english_summary")
                else:
                    print(f"  ⚠️ 未找到 ENGLISH_SUMMARY_MARKER，english_summary 未插入")

            doc.save(output_path)

            if es_margins and es_inserted:
                _apply_english_summary_margins_doc(doc, es_margins)
        else:
            body_elem = doc.element.body
            marker_removed = False
            for elem in list(body_elem):
                text = common.get_element_text(elem)
                if common.ENGLISH_SUMMARY_MARKER in text:
                    body_elem.remove(elem)
                    marker_removed = True
                    print(f"  已删除 ENGLISH_SUMMARY_MARKER（无 english_summary 文件）")
                    break
            if marker_removed:
                doc.save(output_path)

        for chart_generated, chart_name, chart_marker, chart_width in [
            (relative_chart_generated, "relative_chart", common.RELATIVE_CHART_MARKER, 6.35),
            (recommendation_chart_generated, "recommendation_chart", common.RECOMMENDATION_CHART_MARKER, 18),
        ]:
            if chart_generated:
                chart_path = Path(output_path).parent / f"{chart_name}.png"
                if chart_path.exists():
                    chart_inserted = _insert_image_to_placeholder(
                        doc, chart_marker, str(chart_path), width_cm=chart_width
                    )
                    if chart_inserted:
                        print(f"  ✅ {chart_name} 已插入到文档")
                    else:
                        print(f"  ⚠️ {chart_name} 插入失败")

        # 统一保存文档（含 english_summary 页边距和图表）
        doc.save(output_path)

        if escaped_chart_files:
            _restore_jinja_in_charts(output_path, escaped_chart_files)
            print(f"  已恢复 {len(escaped_chart_files)} 个图表文件的原始内容")

        _apply_font_constraints(output_path, chinese_font='楷体')
        print(f"  已应用字体约束：中文=楷体, 英文=Calibri")


        temp_path.unlink(missing_ok=True)
        fixed_template_path.unlink(missing_ok=True)

        # _restore_jinja_in_charts 与 _apply_font_constraints 只改 XML 属性，
        # 不影响段落/表格/图片数量，沿用内存中的 doc 即可，避免再次解析整份 docx
        image_count = sum(1 for rel in doc.part.rels.values() if 'image' in rel.reltype)

        appendix_result = _verify_appendix_with_lxml(output_path)
        appendix_found = appendix_result.get('found', False)

        print(f"  输出: 段落={len(doc.paragraphs)}, 表格={len(doc.tables)}, 图片={image_count}")
        if appendix_found:
            print(f"  ✅ 法律附录已完整保留 ({appendix_result.get('location', '')})")
        else:
            print(f"  ⚠️ 法律附录未找到")

        return True

    except Exception as e:
        print(f"渲染失败: {e}")
        import traceback
        traceback.print_exc()
        return False
