"""测试 template.py 模块的函数。"""
import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
from docx import Document

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from template import (
    load_document,
    save_document,
    replace_field_value_in_doc,
    replace_abstract_in_doc,
    replace_body_in_doc,
    adjust_abstract_position_in_doc,
    adjust_body_range_in_doc,
    add_field_to_doc,
    remove_field_from_doc,
)


class TestLoadDocument:
    """测试 load_document 函数。"""

    @patch('template.Document')
    def test_load_document_returns_doc_object(self, mock_document_class):
        """测试：加载文档返回 Document 对象。"""
        mock_doc = Mock()
        mock_document_class.return_value = mock_doc

        result = load_document("test.docx")

        mock_document_class.assert_called_once_with("test.docx")
        assert result == mock_doc


class TestSaveDocument:
    """测试 save_document 函数。"""

    def test_save_document_calls_save_method(self):
        """测试：保存文档调用 doc.save()。"""
        mock_doc = Mock()
        output_path = "/tmp/output.docx"

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "output.docx"
            save_document(mock_doc, str(output_path))

            mock_doc.save.assert_called_once()


class TestReplaceFieldValue:
    """测试 replace_field_value_in_doc 函数。"""

    def test_replace_in_paragraphs(self):
        """测试：在段落中替换字段值。"""
        # 创建 mock 文档
        mock_doc = Mock()
        mock_para = Mock()
        mock_para.text = "公司名称：西锐飞机"

        # Mock paragraph.runs
        mock_run = Mock()
        mock_run.text = "公司名称：西锐飞机"
        mock_para.runs = [mock_run]
        mock_doc.paragraphs = [mock_para]
        mock_doc.tables = []
        mock_doc.sections = []  # 添加 sections mock

        result = replace_field_value_in_doc(mock_doc, "company", "西锐飞机")

        # 验证返回文档对象
        assert result is not None

    def test_replace_in_tables(self):
        """测试：在表格中替换字段值。"""
        # 创建 mock 文档
        mock_doc = Mock()
        mock_doc.paragraphs = []
        mock_doc.sections = []  # 添加 sections mock

        # 创建 mock 表格
        mock_table = Mock()
        mock_row = Mock()
        mock_cell = Mock()
        mock_para = Mock()
        mock_run = Mock()
        mock_run.text = "西锐飞机"
        mock_para.runs = [mock_run]
        mock_para.text = "西锐飞机"
        mock_cell.paragraphs = [mock_para]
        mock_row.cells = [mock_cell]
        mock_table.rows = [mock_row]
        mock_doc.tables = [mock_table]

        result = replace_field_value_in_doc(mock_doc, "company", "西锐飞机")

        # 验证调用
        assert result is not None


class TestReplaceAbstract:
    """测试 replace_abstract_in_doc 函数。"""

    def test_replace_abstract_in_table(self):
        """测试：在表格中替换摘要。"""
        # 创建 mock 文档和表格
        mock_doc = Mock()
        mock_table = Mock()
        mock_row = Mock()

        # 创建 3 个单元格
        mock_cells = []
        for i in range(3):
            mock_cell = Mock()
            mock_para = Mock()
            mock_run = Mock()
            mock_cell.paragraphs = [mock_para]
            mock_para.runs = [mock_run]
            mock_cells.append(mock_cell)

        mock_row.cells = mock_cells
        mock_table.rows = [mock_row]
        mock_doc.tables = [mock_table]

        result = replace_abstract_in_doc(mock_doc, 0, 0, 0, 2)

        # 验证返回文档对象
        assert result is not None

    def test_replace_abstract_with_invalid_table_index(self):
        """测试：表格索引超出范围时抛出异常。"""
        mock_doc = Mock()
        mock_doc.tables = []

        with pytest.raises(ValueError, match="表格索引.*超出范围"):
            replace_abstract_in_doc(mock_doc, 0, 0, 0, 1)

    def test_replace_abstract_with_invalid_row_index(self):
        """测试：行索引超出范围时抛出异常。"""
        mock_doc = Mock()
        mock_table = Mock()
        mock_table.rows = []
        mock_doc.tables = [mock_table]

        with pytest.raises(ValueError, match="行索引.*超出范围"):
            replace_abstract_in_doc(mock_doc, 0, 0, 0, 1)


class TestReplaceBody:
    """测试 replace_body_in_doc 函数。"""

    def test_replace_body_in_document(self):
        """测试：替换正文区域。"""
        # 创建 mock 文档
        mock_doc = Mock()

        # 创建 mock 段落
        mock_paras = []
        for i in range(5):
            mock_para = Mock()
            mock_run = Mock()
            mock_para.runs = [mock_run]
            mock_para._element = Mock()
            mock_paras.append(mock_para)

        mock_doc.paragraphs = mock_paras

        result = replace_body_in_doc(mock_doc, 1, 4)

        # 验证返回文档对象
        assert result is not None

    def test_replace_body_with_invalid_start_index(self):
        """测试：起始索引超出范围时抛出异常。"""
        mock_doc = Mock()
        mock_doc.paragraphs = []

        with pytest.raises(ValueError, match="起始段落.*超出范围"):
            replace_body_in_doc(mock_doc, 0, 1)


class TestRemoveField:
    """测试 remove_field_from_doc 函数。"""

    def test_remove_field_from_paragraphs(self):
        """测试：从段落中删除字段。"""
        # 创建 mock 文档
        mock_doc = Mock()

        # 创建包含占位符的段落
        mock_para_with_field = Mock()
        mock_para_with_field.text = "公司：{{ company }}"
        mock_element = Mock()
        mock_parent = Mock()
        mock_para_with_field._element = mock_element
        mock_element.getparent.return_value = mock_parent

        # 创建不包含占位符的段落
        mock_para_without_field = Mock()
        mock_para_without_field.text = "其他内容"
        mock_para_without_field._element = Mock()

        mock_doc.paragraphs = [mock_para_with_field, mock_para_without_field]
        mock_doc.tables = []

        result = remove_field_from_doc(mock_doc, "company")

        # 验证返回文档对象
        assert result is not None


class TestAdjustFunctions:
    """测试位置调整函数。"""

    def test_adjust_abstract_position(self):
        """测试：调整摘要位置。"""
        mock_doc = Mock()

        # 创建 mock 表格和行
        mock_table = Mock()
        mock_row = Mock()
        mock_cells = [Mock() for _ in range(2)]
        for cell in mock_cells:
            mock_para = Mock()
            mock_run = Mock()
            cell.paragraphs = [mock_para]
            mock_para.runs = [mock_run]
        mock_row.cells = mock_cells
        mock_table.rows = [mock_row]
        mock_doc.tables = [mock_table]

        # 这个函数实际上是调用 replace_abstract_in_doc
        result = adjust_abstract_position_in_doc(mock_doc, 0, 0, 0, 1)

        # 验证返回值是 Document 对象
        assert result is not None

    def test_adjust_body_range(self):
        """测试：调整正文范围。"""
        mock_doc = Mock()

        # 创建 mock 段落
        mock_paras = []
        for i in range(2):
            mock_para = Mock()
            mock_run = Mock()
            mock_para.runs = [mock_run]
            mock_para._element = Mock()
            mock_paras.append(mock_para)

        mock_doc.paragraphs = mock_paras

        # 这个函数实际上是调用 replace_body_in_doc
        result = adjust_body_range_in_doc(mock_doc, 0, 1)

        # 验证返回值是 Document 对象
        assert result is not None


class TestAddField:
    """测试 add_field_to_doc 函数。"""

    def test_add_field_after_paragraph(self):
        """测试：在指定段落之后添加字段。"""
        mock_doc = Mock()

        # 创建 mock 段落
        mock_para = Mock()
        mock_element = Mock()
        new_element = Mock()
        mock_para._element = mock_element
        mock_element.addprevious.return_value = new_element

        mock_doc.paragraphs = [mock_para]
        mock_doc.tables = []

        result = add_field_to_doc(mock_doc, "new_field", "新字段", "paragraph:0")

        # 验证函数完成不报错
        assert result is not None


class TestImmutableBehavior:
    """测试不可变性。"""

    def test_replace_field_returns_doc_object(self):
        """测试：替换字段返回 Document 对象。"""
        mock_doc = Mock()
        mock_para = Mock()
        mock_para.text = "测试"
        mock_run = Mock()
        mock_para.runs = [mock_run]
        mock_doc.paragraphs = [mock_para]
        mock_doc.tables = []
        mock_doc.sections = []  # 添加 sections mock

        result = replace_field_value_in_doc(mock_doc, "test", "测试")

        # 验证返回 Document 对象
        assert result is not None
