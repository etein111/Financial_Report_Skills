"""docx_reader.py - Word 文档读取模块。

使用 lxml 直接解析 document.xml，递归读取嵌套表格，
解决 python-docx 的 cell.text 不包含嵌套表格内容、以及漏读表格的问题。

遵循函数式编程原则：纯函数、无副作用、I/O 分离。
"""

import zipfile
from typing import List, Dict, Any, Optional
from pathlib import Path
from lxml import etree


W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'


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
    with zipfile.ZipFile(docx_path, 'r') as z:
        with z.open('word/document.xml') as f:
            tree = etree.parse(f).getroot()

    # 提取所有表格（包括嵌套表格）
    all_tables = list(tree.iter(f'{W}tbl'))
    tables = []

    for table_idx, table_elem in enumerate(all_tables):
        table_data = _extract_table_data(table_elem, table_idx)
        tables.append(table_data)

    return tables


def read_docx_tables_with_elements(docx_path: str) -> List[Dict[str, Any]]:
    """读取 Word 文档中的所有表格（包括嵌套表格），并保留原始 lxml 元素。

    用于需要保留格式（字体、加粗、样式等）的场景。

    Args:
        docx_path: Word 文档路径

    Returns:
        表格列表，每个表格包含结构化数据和原始 lxml 元素

    Raises:
        FileNotFoundError: 文件不存在
        Exception: 文档读取错误
    """
    doc_path = Path(docx_path)
    if not doc_path.exists():
        raise FileNotFoundError(f"文件不存在: {docx_path}")

    # 使用 lxml 直接解析 document.xml
    with zipfile.ZipFile(docx_path, 'r') as z:
        with z.open('word/document.xml') as f:
            tree = etree.parse(f).getroot()

    # 提取所有表格（包括嵌套表格）
    all_tables = list(tree.iter(f'{W}tbl'))
    tables = []

    for table_idx, table_elem in enumerate(all_tables):
        table_data = _extract_table_data_with_elements(table_elem, table_idx)
        tables.append(table_data)

    return tables


def _extract_table_data_with_elements(table_elem, table_idx: int) -> Dict[str, Any]:
    """提取单个表格的数据（包括嵌套表格），保留原始 lxml 元素。

    Args:
        table_elem: lxml 表格元素
        table_idx: 表格索引

    Returns:
        表格数据字典，包含 'element' 键指向原始 lxml 元素
    """
    rows_data = []

    for row_idx, row_elem in enumerate(table_elem.findall(f'{W}tr')):
        row_data = _extract_row_data_with_elements(row_elem, row_idx)
        rows_data.append(row_data)

    return {
        'index': table_idx,
        'type': 'table',
        'element': table_elem,  # 保留原始 lxml 元素
        'rows': rows_data
    }


def _extract_row_data_with_elements(row_elem, row_idx: int) -> Dict[str, Any]:
    """提取行数据（包括嵌套表格），保留原始 lxml 元素。

    Args:
        row_elem: lxml 行元素
        row_idx: 行索引

    Returns:
        行数据字典，包含 'element' 键指向原始 lxml 元素
    """
    cells_data = []

    for cell_idx, cell_elem in enumerate(row_elem.findall(f'{W}tc')):
        cell_data = _extract_cell_data_with_elements(cell_elem, cell_idx)
        cells_data.append(cell_data)

    return {
        'index': row_idx,
        'type': 'row',
        'element': row_elem,  # 保留原始 lxml 元素
        'cells': cells_data
    }


def _extract_cell_data_with_elements(cell_elem, cell_idx: int) -> Dict[str, Any]:
    """提取单元格数据（包括嵌套表格），保留原始 lxml 元素。

    Args:
        cell_elem: lxml 单元格元素
        cell_idx: 单元格索引

    Returns:
        单元格数据字典，包含 'element' 键指向原始 lxml 元素
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
        nested_data = _extract_table_data_with_elements(nested_table, nested_idx)
        nested_tables.append(nested_data)

    return {
        'index': cell_idx,
        'type': 'cell',
        'element': cell_elem,  # 保留原始 lxml 元素
        'text': '\n'.join(paragraphs_text),
        'paragraphs': paragraphs_text,
        'nested_tables': nested_tables
    }


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


def flatten_table_text(tables: List[Dict[str, Any]]) -> List[str]:
    """扁平化表格数据为文本列表。

    用于快速搜索和匹配字段。

    Args:
        tables: 表格数据列表

    Returns:
        文本行列表
    """
    lines = []

    def _flatten_node(node: Dict[str, Any], prefix: str = "") -> None:
        """递归扁平化节点。"""
        node_type = node.get('type', '')

        if node_type == 'cell':
            # 添加单元格文本
            text = node.get('text', '').strip()
            if text:
                lines.append(text)

            # 递归处理嵌套表格
            for nested_table in node.get('nested_tables', []):
                _flatten_node(nested_table, f"{prefix}  ")

        elif node_type == 'row':
            for cell in node.get('cells', []):
                _flatten_node(cell, prefix)

        elif node_type == 'table':
            for row in node.get('rows', []):
                _flatten_node(row, prefix)

    # 处理所有表格
    for table in tables:
        _flatten_node(table)

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

    def _search_node(node: Dict[str, Any]) -> None:
        """递归搜索节点。"""
        node_type = node.get('type', '')

        if node_type == 'cell':
            text = node.get('text', '').strip()
            if keyword_lower in text.lower():
                matches.append(node)

            # 递归搜索嵌套表格
            for nested_table in node.get('nested_tables', []):
                _search_node(nested_table)

        elif node_type == 'row':
            for cell in node.get('cells', []):
                _search_node(cell)

        elif node_type == 'table':
            for row in node.get('rows', []):
                _search_node(row)

    # 搜索所有表格
    for table in tables:
        _search_node(table)

    return matches


def extract_nested_tables_only(tables: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """仅提取嵌套表格的数据。

    用于快速定位首页表格中的嵌套表格（通常包含关键字段）。

    Args:
        tables: 表格数据列表

    Returns:
        嵌套表格列表
    """
    nested_tables = []

    def _collect_nested(node: Dict[str, Any]) -> None:
        """递归收集嵌套表格。"""
        node_type = node.get('type', '')

        if node_type == 'cell':
            for nested_table in node.get('nested_tables', []):
                nested_tables.append(nested_table)
                # 递归处理更深层的嵌套
                _collect_nested(nested_table)

        elif node_type == 'row':
            for cell in node.get('cells', []):
                _collect_nested(cell)

        elif node_type == 'table':
            for row in node.get('rows', []):
                _collect_nested(row)

    # 收集所有嵌套表格
    for table in tables:
        _collect_nested(table)

    return nested_tables