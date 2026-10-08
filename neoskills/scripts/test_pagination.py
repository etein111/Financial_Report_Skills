"""test_pagination.py - 测试 Word 文档的分页结构

使用方法：
    python scripts/test_pagination.py <docx文件路径> [--use-word]

示例：
    python scripts/test_pagination.py inbox/samples/company/xxx.docx
    python scripts/test_pagination.py xxx.docx --use-word  # 使用 Word 获取真实页码（仅 Windows）

输出说明：
    - [元素 N] 表示该元素在 body 中的索引位置
    - (段落 N) 表示该元素对应的段落编号
    - 分页符位于哪个元素，就表示在该元素之后分页
"""

import sys
import re
from pathlib import Path
from docx import Document
from docx.oxml.ns import qn

# 添加 skills 目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

# Word 命名空间
W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'


def get_paragraph_style(para) -> str:
    """获取段落样式名称"""
    style = para.style
    if style and style.name:
        return style.name
    return 'Normal'


def get_paragraph_text_with_tables(para, doc) -> str:
    """获取段落完整文本（包括嵌套表格内容）"""
    # 获取段落本身的文本
    text_parts = []
    for run in para.runs:
        if run.text:
            text_parts.append(run.text)

    # 检查是否有嵌套表格
    p_element = para._element
    for tbl in p_element.iter(f'{{{W}}}tbl'):
        tbl_text = extract_table_text(tbl)
        if tbl_text:
            text_parts.append(f"[表格: {tbl_text[:50]}...]" if len(tbl_text) > 50 else f"[表格: {tbl_text}]")

    return ''.join(text_parts).strip()


def extract_table_text(tbl) -> str:
    """提取表格所有文本"""
    texts = []
    for row in tbl.iter(f'{{{W}}}tr'):
        row_texts = []
        for cell in row.iter(f'{{{W}}}tc'):
            cell_text = ''.join(t.text or '' for t in cell.iter(f'{{{W}}}t'))
            if cell_text.strip():
                row_texts.append(cell_text.strip())
        if row_texts:
            texts.append(' | '.join(row_texts))
    return ' || '.join(texts)


def try_get_page_via_word(docx_path: str):
    """尝试通过 Word COM 接口获取真实页码（仅 Windows）"""
    try:
        import win32com.client
        import pythoncom

        pythoncom.CoInitialize()
        word = win32com.client.Dispatch("Word.Application")
        word.Visible = False

        doc = word.Documents.Open(str(Path(docx_path).resolve()))
        word.ActiveDocument.ComputeStatistics(2)  # wdStatisticPages = 2

        page_count = doc.ComputeStatistics(2)
        doc.Close(False)
        word.Quit()
        pythoncom.CoUninitialize()

        return page_count
    except Exception as e:
        return None


def analyze_pagination(docx_path: str, use_word: bool = False):
    """分析 Word 文档的分页结构

    Args:
        docx_path: docx 文件路径
        use_word: 是否使用 Word COM 获取真实页码（仅 Windows）
    """
    doc = Document(docx_path)

    # 尝试获取总页数
    total_pages = "（需用 Word 查看）"
    if use_word:
        pages = try_get_page_via_word(docx_path)
        if pages:
            total_pages = pages

    print(f"=" * 70)
    print(f"文档: {docx_path}")
    print(f"总段落数: {len(doc.paragraphs)}")
    print(f"总表格数: {len(doc.tables)}")
    print(f"估算总页数: {total_pages}")
    print(f"=" * 70)
    print()

    body = doc.element.body
    elements = list(body)

    print(f"Body 子元素总数: {len(elements)}")
    print()

    # 建立段落索引映射（元素索引 -> (段落索引, 段落对象)）
    para_index_map = {}
    para_idx = 0
    for elem_idx, elem in enumerate(elements):
        if elem.tag.split('}')[-1] == 'p':
            para_index_map[elem_idx] = para_idx
            para_idx += 1

    # 存储分页信息
    pagination_info = []

    # 检查每个元素
    for i, elem in enumerate(elements):
        tag = elem.tag.split('}')[-1]

        if tag == 'p':
            # 获取完整段落文本
            para = None
            para_idx_in_doc = para_index_map.get(i)
            if para_idx_in_doc is not None and para_idx_in_doc < len(doc.paragraphs):
                para = doc.paragraphs[para_idx_in_doc]

            full_text = get_paragraph_text_with_tables(para, doc) if para else ""
            style_name = get_paragraph_style(para) if para else 'Unknown'

            # 检查分页符
            has_page_break = False
            break_type = None
            break_detail = ""

            for br in elem.iter(f'{{{W}}}br'):
                br_type = br.get(f'{{{W}}}type', '')
                if br_type == 'page':
                    has_page_break = True
                    break_type = 'explicit-page-break'
                    break_detail = "（显式分页符，强制分页）"
                elif br_type == 'column':
                    has_page_break = True
                    break_type = 'column-break'
                    break_detail = "（栏分隔符）"

            # 检查 lastRenderedPageBreak
            if not has_page_break:
                for lrb in elem.iter(f'{{{W}}}lastRenderedPageBreak'):
                    has_page_break = True
                    break_type = 'last-rendered-page-break'
                    break_detail = "（Word渲染页断点）"

            # 检查 sectPr
            pPr = elem.find(f'{{{W}}}pPr')
            has_sectPr = False
            sectPr_type = None
            sectPr_margins = {}

            if pPr is not None:
                sectPr = pPr.find(f'{{{W}}}sectPr')
                if sectPr is not None:
                    has_sectPr = True
                    type_elem = sectPr.find(f'{{{W}}}type')
                    if type_elem is not None:
                        sectPr_type = type_elem.get(f'{{{W}}}val', 'continuous')
                    pgMar = sectPr.find(f'{{{W}}}pgMar')
                    if pgMar is not None:
                        for attr in ['top', 'bottom', 'left', 'right']:
                            val = pgMar.get(f'{{{W}}}{attr}')
                            if val:
                                sectPr_margins[attr] = val

            # 输出有分页符或 sectPr 的段落
            if has_page_break or has_sectPr:
                info_parts = []
                if has_page_break:
                    info_parts.append(f"分页符: {break_type} {break_detail}")
                if has_sectPr:
                    type_str = "连续" if sectPr_type == 'continuous' else ("新页" if sectPr_type == 'page' else sectPr_type or "默认")
                    info_parts.append(f"sectPr: {type_str} (type={sectPr_type})")

                pagination_info.append({
                    'elem_idx': i,
                    'para_idx': para_idx_in_doc,
                    'text': full_text,
                    'style': style_name,
                    'has_page_break': has_page_break,
                    'break_type': break_type,
                    'has_sectPr': has_sectPr,
                    'sectPr_type': sectPr_type,
                    'sectPr_margins': sectPr_margins,
                    'info': ' | '.join(info_parts)
                })

        elif tag == 'tbl':
            # 记录表格信息
            tbl_text = extract_table_text(elem)
            pagination_info.append({
                'elem_idx': i,
                'para_idx': None,
                'text': tbl_text[:100] + '...' if len(tbl_text) > 100 else tbl_text,
                'style': '表格',
                'has_page_break': False,
                'has_sectPr': False,
                'info': f'表格元素 (共 {len([r for r in elem.iter(f"{{{W}}}tr")])} 行)'
            })

        elif tag == 'sectPr':
            pgMar = elem.find(f'{{{W}}}pgMar')
            if pgMar is not None:
                margins = {attr: pgMar.get(f'{{{W}}}{attr}') for attr in ['top', 'bottom', 'left', 'right'] if pgMar.get(f'{{{W}}}{attr}')}
                pagination_info.append({
                    'elem_idx': i,
                    'para_idx': None,
                    'text': '',
                    'style': '分节符',
                    'has_page_break': False,
                    'has_sectPr': True,
                    'sectPr_type': 'body-end',
                    'sectPr_margins': margins,
                    'info': f'Body 末尾分节符: 页边距 top={margins.get("top")} bottom={margins.get("bottom")}'
                })

    # 打印分页详情
    print("=" * 70)
    print("分页详情（按出现顺序）：")
    print("=" * 70)

    for info in pagination_info:
        elem_idx = info['elem_idx']
        para_idx = info['para_idx']
        text = info['text']
        style = info['style']
        info_str = info['info']

        # 标题行
        header = f"[元素 {elem_idx}]"
        if para_idx is not None:
            header += f" (段落 {para_idx})"
        header += f" [{style}]"

        print()
        print(header)
        print(f"  类型: {info_str}")

        if text:
            # 显示文本内容（限制长度）
            display_text = text.replace('\n', ' ').replace('\r', ' ')
            if len(display_text) > 100:
                display_text = display_text[:100] + '...'
            print(f"  内容: {display_text}")
        else:
            print(f"  内容: （无文本）")

        # sectPr 详细信息
        if info['has_sectPr'] and info.get('sectPr_margins'):
            m = info['sectPr_margins']
            print(f"  页边距: top={m.get('top','-')} bottom={m.get('bottom','-')} left={m.get('left','-')} right={m.get('right','-')}")

    # 总结
    print()
    print("=" * 70)
    print("分页相关元素总结:")
    print("=" * 70)

    # 统计
    explicit_page = sum(1 for p in pagination_info if p.get('break_type') == 'explicit-page-break')
    column_break = sum(1 for p in pagination_info if p.get('break_type') == 'column-break')
    last_rendered = sum(1 for p in pagination_info if p.get('break_type') == 'last-rendered-page-break')
    sectPr_count = sum(1 for p in pagination_info if p.get('has_sectPr'))
    table_count = sum(1 for p in pagination_info if p['style'] == '表格')

    print(f"  显式分页符 (page break): {explicit_page}")
    print(f"  栏分隔符 (column break): {column_break}")
    print(f"  渲染页断点 (lastRenderedPageBreak): {last_rendered}")
    print(f"  分节符 (sectPr): {sectPr_count}")
    print(f"  表格元素: {table_count}")
    print()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python scripts/test_pagination.py <docx文件路径> [--use-word]")
        print("示例: python scripts/test_pagination.py inbox/samples/company/xxx.docx")
        print("      python scripts/test_pagination.py xxx.docx --use-word  # 使用 Word 获取真实页码")
        sys.exit(1)

    docx_path = sys.argv[1]
    use_word = '--use-word' in sys.argv

    if not Path(docx_path).exists():
        print(f"错误: 文件不存在 - {docx_path}")
        sys.exit(1)

    analyze_pagination(docx_path, use_word=use_word)
