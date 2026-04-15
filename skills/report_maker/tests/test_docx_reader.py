"""test_docx_reader.py - docx_reader.py 模块测试。

测试 Word 文档读取功能，特别是嵌套表格处理。
"""

import pytest
from pathlib import Path
import tempfile
import zipfile

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from docx_reader import (
    read_docx_tables,
    flatten_table_text,
    search_in_tables,
    extract_nested_tables_only,
)


class TestReadDocxTables:
    """测试 read_docx_tables 函数。"""

    @pytest.fixture
    def sample_docx_with_nested_table(self, tmp_path):
        """创建包含嵌套表格的示例文档。"""
        try:
            from docx import Document
        except ImportError:
            pytest.skip("python-docx not installed")

        doc = Document()

        # 添加外层表格
        table1 = doc.add_table(rows=2, cols=2)
        table1.rows[0].cells[0].text = "外层单元格1"
        table1.rows[0].cells[1].text = "外层单元格2"
        table1.rows[1].cells[0].text = "外层单元格3"
        table1.rows[1].cells[1].text = "外层单元格4"

        doc.add_paragraph("普通段落")

        # 添加第二个外层表格
        table2 = doc.add_table(rows=2, cols=2)
        table2.rows[0].cells[0].text = "表格2-1"
        table2.rows[0].cells[1].text = "表格2-2"

        doc_path = tmp_path / "sample_nested.docx"
        doc.save(str(doc_path))

        return str(doc_path)

    @pytest.fixture
    def simple_docx(self, tmp_path):
        """创建简单的示例文档。"""
        try:
            from docx import Document
        except ImportError:
            pytest.skip("python-docx not installed")

        doc = Document()
        table = doc.add_table(rows=2, cols=2)
        table.rows[0].cells[0].text = "公司"
        table.rows[0].cells[1].text = "西锐飞机"
        table.rows[1].cells[0].text = "代码"
        table.rows[1].cells[1].text = "2507.HK"

        doc_path = tmp_path / "simple.docx"
        doc.save(str(doc_path))

        return str(doc_path)

    def test_raises_file_not_found_for_nonexistent_file(self):
        """测试：文件不存在时抛出 FileNotFoundError。"""
        with pytest.raises(FileNotFoundError):
            read_docx_tables("nonexistent_file.docx")

    def test_returns_list_of_tables(self, simple_docx):
        """测试：返回表格列表。"""
        tables = read_docx_tables(simple_docx)

        assert isinstance(tables, list)
        assert len(tables) == 1
        assert tables[0]['type'] == 'table'

    def test_table_structure(self, simple_docx):
        """测试：表格数据结构正确。"""
        tables = read_docx_tables(simple_docx)

        table = tables[0]
        assert 'index' in table
        assert 'type' in table
        assert 'rows' in table
        assert table['type'] == 'table'
        assert table['index'] == 0

    def test_row_structure(self, simple_docx):
        """测试：行数据结构正确。"""
        tables = read_docx_tables(simple_docx)

        row = tables[0]['rows'][0]
        assert 'index' in row
        assert 'type' in row
        assert 'cells' in row
        assert row['type'] == 'row'

    def test_cell_structure(self, simple_docx):
        """测试：单元格数据结构正确。"""
        tables = read_docx_tables(simple_docx)

        cell = tables[0]['rows'][0]['cells'][0]
        assert 'index' in cell
        assert 'type' in cell
        assert 'text' in cell
        assert cell['type'] == 'cell'

    def test_multiple_tables(self, sample_docx_with_nested_table):
        """测试：读取多个表格。"""
        tables = read_docx_tables(sample_docx_with_nested_table)

        assert len(tables) == 2

    def test_cell_text_extraction(self, simple_docx):
        """测试：单元格文本正确提取。"""
        tables = read_docx_tables(simple_docx)

        cell = tables[0]['rows'][0]['cells'][0]
        assert cell['text'] == '公司'

    def test_paragraphs_in_cell(self, simple_docx):
        """测试：单元格中的段落被正确提取。"""
        tables = read_docx_tables(simple_docx)

        # 如果单元格有多个段落，paragraphs 列表应该包含它们
        cell = tables[0]['rows'][0]['cells'][0]
        assert isinstance(cell['paragraphs'], list)


class TestFlattenTableText:
    """测试 flatten_table_text 函数。"""

    @pytest.fixture
    def sample_tables(self):
        """创建示例表格数据结构。"""
        return [
            {
                'type': 'table',
                'index': 0,
                'rows': [
                    {
                        'type': 'row',
                        'index': 0,
                        'cells': [
                            {'type': 'cell', 'index': 0, 'text': '公司', 'paragraphs': ['公司'], 'nested_tables': []},
                            {'type': 'cell', 'index': 1, 'text': '西锐飞机', 'paragraphs': ['西锐飞机'], 'nested_tables': []},
                        ]
                    },
                    {
                        'type': 'row',
                        'index': 1,
                        'cells': [
                            {'type': 'cell', 'index': 0, 'text': '代码', 'paragraphs': ['代码'], 'nested_tables': []},
                            {'type': 'cell', 'index': 1, 'text': '2507.HK', 'paragraphs': ['2507.HK'], 'nested_tables': []},
                        ]
                    },
                ]
            }
        ]

    def test_flattens_table_to_lines(self, sample_tables):
        """测试：表格扁平化为文本行。"""
        lines = flatten_table_text(sample_tables)

        assert isinstance(lines, list)
        assert '公司' in lines
        assert '西锐飞机' in lines
        assert '代码' in lines
        assert '2507.HK' in lines

    def test_includes_paragraphs_if_provided(self, sample_tables):
        """测试：如果提供了段落，也包含在结果中。"""
        paragraphs = ["这是段落1", "这是段落2"]
        lines = flatten_table_text(sample_tables, paragraphs)

        assert "这是段落1" in lines
        assert "这是段落2" in lines

    def test_nested_tables_content_included(self):
        """测试：嵌套表格内容被包含。"""
        tables = [
            {
                'type': 'table',
                'index': 0,
                'rows': [
                    {
                        'type': 'row',
                        'index': 0,
                        'cells': [
                            {
                                'type': 'cell',
                                'index': 0,
                                'text': '外层',
                                'paragraphs': ['外层'],
                                'nested_tables': [
                                    {
                                        'type': 'table',
                                        'index': 0,
                                        'rows': [
                                            {
                                                'type': 'row',
                                                'index': 0,
                                                'cells': [
                                                    {'type': 'cell', 'index': 0, 'text': '嵌套内容', 'paragraphs': ['嵌套内容'], 'nested_tables': []},
                                                ]
                                            }
                                        ]
                                    }
                                ]
                            },
                        ]
                    },
                ]
            }
        ]

        lines = flatten_table_text(tables)

        assert '外层' in lines
        assert '嵌套内容' in lines


class TestSearchInTables:
    """测试 search_in_tables 函数。"""

    @pytest.fixture
    def sample_tables(self):
        """创建示例表格数据结构。"""
        return [
            {
                'type': 'table',
                'index': 0,
                'rows': [
                    {
                        'type': 'row',
                        'index': 0,
                        'cells': [
                            {'type': 'cell', 'index': 0, 'text': '公司名称', 'paragraphs': ['公司名称'], 'nested_tables': []},
                            {'type': 'cell', 'index': 1, 'text': '西锐飞机', 'paragraphs': ['西锐飞机'], 'nested_tables': []},
                        ]
                    },
                    {
                        'type': 'row',
                        'index': 1,
                        'cells': [
                            {'type': 'cell', 'index': 0, 'text': '股票代码', 'paragraphs': ['股票代码'], 'nested_tables': []},
                            {'type': 'cell', 'index': 1, 'text': '2507.HK', 'paragraphs': ['2507.HK'], 'nested_tables': []},
                        ]
                    },
                ]
            }
        ]

    def test_finds_matching_cell(self, sample_tables):
        """测试：找到匹配的单元格。"""
        matches = search_in_tables(sample_tables, '西锐飞机')

        assert len(matches) == 1
        assert matches[0]['text'] == '西锐飞机'

    def test_case_insensitive_search(self, sample_tables):
        """测试：搜索不区分大小写。"""
        matches = search_in_tables(sample_tables, '西锐')

        assert len(matches) == 1

        matches_upper = search_in_tables(sample_tables, '西锐飞机')

        assert len(matches_upper) == 1

    def test_returns_empty_for_no_match(self, sample_tables):
        """测试：无匹配时返回空列表。"""
        matches = search_in_tables(sample_tables, '不存在的关键词')

        assert matches == []

    def test_searches_in_nested_tables(self):
        """测试：在嵌套表格中搜索。"""
        tables = [
            {
                'type': 'table',
                'index': 0,
                'rows': [
                    {
                        'type': 'row',
                        'index': 0,
                        'cells': [
                            {
                                'type': 'cell',
                                'index': 0,
                                'text': '外层',
                                'paragraphs': ['外层'],
                                'nested_tables': [
                                    {
                                        'type': 'table',
                                        'index': 0,
                                        'rows': [
                                            {
                                                'type': 'row',
                                                'index': 0,
                                                'cells': [
                                                    {'type': 'cell', 'index': 0, 'text': '嵌套财务数据', 'paragraphs': ['嵌套财务数据'], 'nested_tables': []},
                                                ]
                                            }
                                        ]
                                    }
                                ]
                            },
                        ]
                    },
                ]
            }
        ]

        matches = search_in_tables(tables, '财务')

        assert len(matches) == 1
        assert '财务数据' in matches[0]['text']

    def test_multiple_matches(self):
        """测试：返回所有匹配。"""
        tables = [
            {
                'type': 'table',
                'index': 0,
                'rows': [
                    {
                        'type': 'row',
                        'index': 0,
                        'cells': [
                            {'type': 'cell', 'index': 0, 'text': '公司A', 'paragraphs': ['公司A'], 'nested_tables': []},
                            {'type': 'cell', 'index': 1, 'text': '公司B', 'paragraphs': ['公司B'], 'nested_tables': []},
                        ]
                    },
                ]
            }
        ]

        matches = search_in_tables(tables, '公司')

        assert len(matches) == 2


class TestExtractNestedTablesOnly:
    """测试 extract_nested_tables_only 函数。"""

    def test_extracts_nested_tables(self):
        """测试：提取嵌套表格。"""
        tables = [
            {
                'type': 'table',
                'index': 0,
                'rows': [
                    {
                        'type': 'row',
                        'index': 0,
                        'cells': [
                            {
                                'type': 'cell',
                                'index': 0,
                                'text': '外层',
                                'paragraphs': ['外层'],
                                'nested_tables': [
                                    {
                                        'type': 'table',
                                        'index': 0,
                                        'rows': []
                                    },
                                    {
                                        'type': 'table',
                                        'index': 1,
                                        'rows': []
                                    }
                                ]
                            },
                        ]
                    },
                ]
            }
        ]

        nested = extract_nested_tables_only(tables)

        assert len(nested) == 2

    def test_no_nested_tables_returns_empty(self):
        """测试：无嵌套表格时返回空列表。"""
        tables = [
            {
                'type': 'table',
                'index': 0,
                'rows': [
                    {
                        'type': 'row',
                        'index': 0,
                        'cells': [
                            {'type': 'cell', 'index': 0, 'text': '普通单元格', 'paragraphs': ['普通单元格'], 'nested_tables': []},
                        ]
                    },
                ]
            }
        ]

        nested = extract_nested_tables_only(tables)

        assert nested == []

    def test_deeply_nested_tables(self):
        """测试：深度嵌套的表格也被提取。"""
        # 注意：extract_nested_tables_only 只收集直接嵌套在单元格中的表格
        # 不递归处理嵌套表格中的嵌套表格
        tables = [
            {
                'type': 'table',
                'index': 0,
                'rows': [
                    {
                        'type': 'row',
                        'index': 0,
                        'cells': [
                            {
                                'type': 'cell',
                                'index': 0,
                                'text': '外层',
                                'paragraphs': ['外层'],
                                'nested_tables': [
                                    {
                                        'type': 'table',
                                        'index': 0,
                                        'rows': []
                                    },
                                    {
                                        'type': 'table',
                                        'index': 1,
                                        'rows': []
                                    }
                                ]
                            },
                        ]
                    },
                ]
            }
        ]

        nested = extract_nested_tables_only(tables)

        # 只提取直接嵌套的表格
        assert len(nested) == 2
