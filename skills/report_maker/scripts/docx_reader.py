"""docx_reader.py - Word 文档读取模块。

使用 lxml 直接解析 document.xml，递归读取嵌套表格，
解决 python-docx 的 cell.text 不包含嵌套表格内容、以及漏读表格的问题。

遵循函数式编程原则：纯函数、无副作用、I/O 分离。
"""

from typing import List, Dict, Any, Optional
from pathlib import Path
from lxml import etree

import common
W = common.W_NS


def read_docx_tables(docx_path: str) -> List[Dict[str, Any]]:
    """读取 Word 文档中的所有表格（包括嵌套表格）。

    使用 lxml 直接解析 document.xml，确保所有表格（包括嵌套表格）都能读取。

    Args:
        docx_path: Word 文档路径

    Returns:
        表格列表，每个表格包含结构化的数据

    Raises:
        FileNotFoundError: 文件不存在
        Exception: 文档读取错误
    """
    doc_path = Path(docx_path)
    if not doc_path.exists():
        raise FileNotFoundError(f"文件不存在: {docx_path}")

    # 使用 lxml 直接解析 document.xml
    files = common.read_docx_zip(docx_path)
    tree = etree.fromstring(files['word/document.xml'])

    # 提取所有表格（包括嵌套表格）
    all_tables = list(tree.iter(f'{W}tbl'))
    tables = []

    for table_idx, table_elem in enumerate(all_tables):
        table_data = _extract_table_data(table_elem, table_idx)
        tables.append(table_data)

    return tables


def _extract_table_data(table_elem, table_idx: int) -> Dict[str, Any]:
    """提取单个表格的数据（包括嵌套表格）。

    Args:
        table_elem: lxml 表格元素
        table_idx: 表格索引

    Returns:
        表格数据字典
    """
    rows_data = []

    for row_idx, row_elem in enumerate(table_elem.findall(f'{W}tr')):
        row_data = _extract_row_data(row_elem, row_idx)
        rows_data.append(row_data)

    return {
        'index': table_idx,
        'type': 'table',
        'rows': rows_data
    }


def _extract_row_data(row_elem, row_idx: int) -> Dict[str, Any]:
    """提取行数据（包括嵌套表格）。

    Args:
        row_elem: lxml 行元素
        row_idx: 行索引

    Returns:
        行数据字典
    """
    cells_data = []

    for cell_idx, cell_elem in enumerate(row_elem.findall(f'{W}tc')):
        cell_data = _extract_cell_data(cell_elem, cell_idx)
        cells_data.append(cell_data)

    return {
        'index': row_idx,
        'type': 'row',
        'cells': cells_data
    }


def _extract_cell_data(cell_elem, cell_idx: int) -> Dict[str, Any]:
    """提取单元格数据（包括嵌套表格）。

    使用 lxml 直接解析单元格，确保嵌套表格内容不遗漏。

    Args:
        cell_elem: lxml 单元格元素
        cell_idx: 单元格索引

    Returns:
        单元格数据字典
    """
    # 提取段落文本
    paragraphs_text = []
    for para_elem in cell_elem.iter(f'{W}p'):
        # 获取段落中的所有文本
        texts = []
        for t_elem in para_elem.iter(f'{W}t'):
            if t_elem.text:
                texts.append(t_elem.text)
        text = ''.join(texts).strip()
        if text:
            paragraphs_text.append(text)

    # 提取嵌套表格
    nested_tables = []
    for nested_idx, nested_table in enumerate(cell_elem.findall(f'{W}tbl')):
        nested_data = _extract_table_data(nested_table, nested_idx)
        nested_tables.append(nested_data)

    return {
        'index': cell_idx,
        'type': 'cell',
        'text': '\n'.join(paragraphs_text),
        'paragraphs': paragraphs_text,
        'nested_tables': nested_tables
    }


def _walk_tables(tables: List[Dict[str, Any]], on_cell):
    """通用表格遍历，对每个 cell 节点调用 on_cell(cell_node)。

    递归遍历 table → row → cell 结构，遇到 cell 时执行回调，
    并自动递归进入 cell 内的嵌套表格。
    """
    def _walk(node):
        node_type = node.get('type', '')

        if node_type == 'cell':
            on_cell(node)
            for nested_table in node.get('nested_tables', []):
                _walk(nested_table)

        elif node_type == 'row':
            for cell in node.get('cells', []):
                _walk(cell)

        elif node_type == 'table':
            for row in node.get('rows', []):
                _walk(row)

    for table in tables:
        _walk(table)


def flatten_table_text(tables: List[Dict[str, Any]], paragraphs: List[str] = None) -> List[str]:
    """扁平化表格数据为文本列表。

    用于快速搜索和匹配字段。

    Args:
        tables: 表格数据列表
        paragraphs: 段落文本列表（可选，用于同时包含段落文本）

    Returns:
        文本行列表
    """
    lines = []

    def _collect_text(cell):
        text = cell.get('text', '').strip()
        if text:
            lines.append(text)

    _walk_tables(tables, _collect_text)

    if paragraphs:
        lines.extend(paragraphs)

    return lines


def search_in_tables(tables: List[Dict[str, Any]], keyword: str) -> List[Dict[str, Any]]:
    """在表格中搜索关键词。

    Args:
        tables: 表格数据列表
        keyword: 搜索关键词

    Returns:
        匹配的单元格列表
    """
    matches = []
    keyword_lower = keyword.lower()

    def _match_cell(cell):
        text = cell.get('text', '').strip()
        if keyword_lower in text.lower():
            matches.append(cell)

    _walk_tables(tables, _match_cell)

    return matches


def extract_nested_tables_only(tables: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """仅提取嵌套表格的数据。

    用于快速定位首页表格中的嵌套表格（通常包含关键字段）。

    Args:
        tables: 表格数据列表

    Returns:
        嵌套表格列表
    """
    nested = []

    def _collect_nested(cell):
        for tbl in cell.get('nested_tables', []):
            nested.append(tbl)

    _walk_tables(tables, _collect_nested)

    return nested


def preprocess_for_extraction(docx_path: str) -> None:
    """预处理文档，输出表格和段落内容供 LLM 提取。

    按三段格式打印到 stdout：
    1. 表格内容（扁平化文本）
    2. 全部非空段落（带索引，格式 [P{idx}/{total}]）
    3. 最后 50 个段落（重点搜索英文摘要）

    Args:
        docx_path: Word 文档路径
    """
    from docx import Document as _Document

    tables = read_docx_tables(docx_path)
    flat = flatten_table_text(tables)

    doc = _Document(docx_path)
    paragraphs = [
        (i, p.text.strip())
        for i, p in enumerate(doc.paragraphs)
        if p.text.strip()
    ]
    total = len(paragraphs)

    # 1. 表格内容
    print("=== 表格内容 ===")
    for line in flat:
        print(line)

    # 2. 全部段落（带索引）
    print("\n=== 段落内容（带索引）===")
    for idx, text in paragraphs:
        print(f"[P{idx}/{total}] {text}")

    # 3. 最后 50 个段落
    print("\n=== 最后 50 个段落（重点搜索 Summary）===")
    last_50 = paragraphs[-50:] if len(paragraphs) > 50 else paragraphs
    for idx, text in last_50:
        print(f"[P{idx}] {text}")