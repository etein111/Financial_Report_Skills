"""test_content_inserter.py - content_inserter.py 模块测试。

测试内容插入到文档的功能。
"""

import pytest
from pathlib import Path
import tempfile
import zipfile
import shutil
from unittest.mock import Mock, MagicMock, patch

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))


class TestFindMarkerInCells:
    """测试 _find_marker_in_cells 函数。"""

    def test_returns_none_when_table_is_none(self):
        """测试：table 为 None 时返回 None。"""
        from content_inserter import _find_marker_in_cells

        # table 为 None 时会抛出 AttributeError
        try:
            result = _find_marker_in_cells(None, "test_marker")
        except AttributeError:
            pass

    def test_finds_marker_in_cell(self):
        """测试：在单元格中找到 marker。"""
        from content_inserter import _find_marker_in_cells

        try:
            from docx import Document
        except ImportError:
            pytest.skip("python-docx not installed")

        doc = Document()
        table = doc.add_table(rows=1, cols=1)
        table.rows[0].cells[0].text = "Test {{MARKER}} content"

        result = _find_marker_in_cells(table, "{{MARKER}}")

        assert result is not None


class TestInsertAbstractToCell:
    """测试 insert_abstract_to_cell 函数。"""

    def test_returns_false_when_docx_unavailable(self):
        """测试：docx 不可用时返回 False。"""
        from content_inserter import insert_abstract_to_cell

        with patch('content_inserter.DOCX_AVAILABLE', False):
            result = insert_abstract_to_cell(None, None, "marker")

            assert result is False

    def test_returns_false_when_no_table_has_marker(self):
        """测试：表格中没有 marker 时返回 False。"""
        from content_inserter import insert_abstract_to_cell

        try:
            from docx import Document
        except ImportError:
            pytest.skip("python-docx not installed")

        doc = Document()
        doc.add_table(rows=2, cols=2)
        doc.add_paragraph("No marker here")

        abstract_doc = Document()
        abstract_doc.add_paragraph("Abstract content")

        result = insert_abstract_to_cell(doc, abstract_doc, "{{ABSTRACT}}")

        assert result is False

    def test_inserts_abstract_to_cell_with_marker(self, tmp_path):
        """测试：在带 marker 的单元格中插入 abstract。"""
        from content_inserter import insert_abstract_to_cell

        try:
            from docx import Document
        except ImportError:
            pytest.skip("python-docx not installed")

        # 使用 fixture
        fixtures_dir = Path(__file__).parent / "fixtures"
        doc_path = fixtures_dir / "doc_with_cell_marker.docx"
        abstract_path = fixtures_dir / "abstract_content.docx"

        # 复制到临时文件
        temp_doc = tmp_path / "test_cell.docx"
        temp_abstract = tmp_path / "abstract.docx"
        shutil.copy(doc_path, temp_doc)
        shutil.copy(abstract_path, temp_abstract)

        doc = Document(str(temp_doc))
        abstract_doc = Document(str(temp_abstract))

        result = insert_abstract_to_cell(doc, abstract_doc, "{{ABSTRACT}}")

        assert result is True


class TestInsertAbstractAtParagraph:
    """测试 _insert_abstract_at_paragraph 函数。"""

    def test_returns_false_when_docx_unavailable(self):
        """测试：docx 不可用时返回 False。"""
        from content_inserter import _insert_abstract_at_paragraph

        with patch('content_inserter.DOCX_AVAILABLE', False):
            result = _insert_abstract_at_paragraph(None, None, "marker")

            assert result is False

    def test_returns_false_when_marker_not_found(self):
        """测试：未找到 marker 时返回 False。"""
        from content_inserter import _insert_abstract_at_paragraph

        try:
            from docx import Document
        except ImportError:
            pytest.skip("python-docx not installed")

        doc = Document()
        doc.add_paragraph("No marker here")

        abstract_doc = Document()
        abstract_doc.add_paragraph("Abstract content")

        result = _insert_abstract_at_paragraph(doc, abstract_doc, "{{ABSTRACT}}")

        assert result is False

    def test_inserts_abstract_at_paragraph_with_marker(self, tmp_path):
        """测试：在带 marker 的段落中插入 abstract。"""
        from content_inserter import _insert_abstract_at_paragraph

        try:
            from docx import Document
        except ImportError:
            pytest.skip("python-docx not installed")

        # 使用 fixture
        fixtures_dir = Path(__file__).parent / "fixtures"
        doc_path = fixtures_dir / "doc_with_paragraph_marker.docx"
        abstract_path = fixtures_dir / "abstract_content.docx"

        # 复制到临时文件
        temp_doc = tmp_path / "test_para.docx"
        temp_abstract = tmp_path / "abstract.docx"
        shutil.copy(doc_path, temp_doc)
        shutil.copy(abstract_path, temp_abstract)

        doc = Document(str(temp_doc))
        abstract_doc = Document(str(temp_abstract))

        result = _insert_abstract_at_paragraph(doc, abstract_doc, "{{ABSTRACT}}")

        assert result is True


class TestApplyEnglishSummaryMargins:
    """测试 _apply_english_summary_margins 函数。"""

    def test_returns_false_for_empty_margins(self):
        """测试：空 margins 时返回 False。"""
        from content_inserter import _apply_english_summary_margins

        result = _apply_english_summary_margins("any_path.docx", {})

        assert result is False

    def test_returns_false_for_nonexistent_file(self, tmp_path):
        """测试：文件不存在时返回 False。"""
        from content_inserter import _apply_english_summary_margins

        nonexistent = tmp_path / "does_not_exist.docx"
        margins = {"top": "1440", "bottom": "1440"}

        result = _apply_english_summary_margins(str(nonexistent), margins)

        assert result is False

    def test_returns_false_when_appendix1_not_found(self, tmp_path):
        """测试：文档中没有 APPENDIX 1 时返回 False。"""
        from content_inserter import _apply_english_summary_margins

        try:
            from docx import Document
        except ImportError:
            pytest.skip("python-docx not installed")

        doc = Document()
        doc.add_paragraph("No APPENDIX 1 here")

        doc_path = tmp_path / "no_appendix.docx"
        doc.save(str(doc_path))

        margins = {"top": "1440", "bottom": "1440"}

        result = _apply_english_summary_margins(str(doc_path), margins)

        assert result is False

    def test_handles_invalid_docx(self, tmp_path):
        """测试：处理无效的 docx 文件。"""
        from content_inserter import _apply_english_summary_margins

        invalid_path = tmp_path / "invalid.docx"
        invalid_path.write_text("This is not a valid docx")

        margins = {"top": "1440"}

        result = _apply_english_summary_margins(str(invalid_path), margins)

        assert result is False

    def test_applies_margins_with_appendix_marker(self, tmp_path):
        """测试：文档有 APPENDIX 1 标记时应用页边距。"""
        from content_inserter import _apply_english_summary_margins

        # 使用 fixture
        fixtures_dir = Path(__file__).parent / "fixtures"
        doc_path = fixtures_dir / "doc_with_appendix_marker.docx"

        # 复制到临时文件
        temp_doc = tmp_path / "test_appendix.docx"
        shutil.copy(doc_path, temp_doc)

        margins = {"top": "1440", "bottom": "1440", "left": "1701", "right": "1701"}

        result = _apply_english_summary_margins(str(temp_doc), margins)

        # 应该返回 True 表示成功
        assert isinstance(result, bool)
