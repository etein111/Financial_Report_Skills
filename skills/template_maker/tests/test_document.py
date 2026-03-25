"""测试 document.py 模块的函数。"""
import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, MagicMock

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from document import (
    find_elements_yaml,
)


class TestFindElementsYaml:
    """测试 find_elements_yaml 函数。"""

    def test_find_with_space_separator(self):
        """测试：查找带空格分隔符的 elements.yaml。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # 创建测试文件
            (tmpdir / "test_sample.docx").touch()
            (tmpdir / "test_sample elements.yaml").touch()

            result = find_elements_yaml(tmpdir / "test_sample.docx")

            assert result is not None
            assert result.name == "test_sample elements.yaml"

    def test_find_with_underscore_separator(self):
        """测试：查找带下划线分隔符的 elements.yaml。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # 创建测试文件
            (tmpdir / "test_sample.docx").touch()
            (tmpdir / "test_sample_elements.yaml").touch()

            result = find_elements_yaml(tmpdir / "test_sample.docx")

            assert result is not None
            assert result.name == "test_sample_elements.yaml"

    def test_find_with_generic_elements_yaml(self):
        """测试：查找通用的 elements.yaml。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # 创建测试文件
            (tmpdir / "test_sample.docx").touch()
            (tmpdir / "elements.yaml").touch()

            result = find_elements_yaml(tmpdir / "test_sample.docx")

            assert result is not None
            assert result.name == "elements.yaml"

    def test_find_returns_none_when_not_found(self):
        """测试：找不到文件时返回 None。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # 只创建 Word 文件，不创建 elements.yaml
            (tmpdir / "test_sample.docx").touch()

            result = find_elements_yaml(tmpdir / "test_sample.docx")

            assert result is None

    def test_find_priority_order(self):
        """测试：按优先级顺序查找（带空格 > 带下划线 > 通用）。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # 创建测试文件
            (tmpdir / "test_sample.docx").touch()
            (tmpdir / "test_sample elements.yaml").touch()
            (tmpdir / "test_sample_elements.yaml").touch()
            (tmpdir / "elements.yaml").touch()

            result = find_elements_yaml(tmpdir / "test_sample.docx")

            # 应该优先返回带空格的版本
            assert result.name == "test_sample elements.yaml"

    def test_find_with_path_object(self):
        """测试：支持 Path 对象作为参数。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # 创建测试文件
            (tmpdir / "test_sample.docx").touch()
            (tmpdir / "test_sample elements.yaml").touch()

            # 传入 Path 对象（不是字符串）
            result = find_elements_yaml(tmpdir / "test_sample.docx")

            assert result is not None
            assert isinstance(result, Path)

    def test_find_with_string_path(self):
        """测试：支持字符串路径作为参数。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # 创建测试文件
            (tmpdir / "test_sample.docx").touch()
            (tmpdir / "test_sample elements.yaml").touch()

            # 传入字符串路径
            result = find_elements_yaml(str(tmpdir / "test_sample.docx"))

            assert result is not None
            assert isinstance(result, Path)


class TestDocumentAnalysisWithRealFiles:
    """使用真实 Word 文件测试文档分析函数。"""

    @pytest.fixture
    def sample_doc_path(self):
        """获取测试样本文档路径。"""
        # 检查多个可能的 fixtures 目录位置
        possible_paths = [
            Path(__file__).parent.parent / "test" / "fixtures" / "company_sample.docx",
            Path("/mnt/c/code/neoskills/skills/template_maker/test/fixtures/company_sample.docx"),
        ]

        for path in possible_paths:
            if path.exists():
                yield path
                return

        pytest.skip(f"测试文件不存在，尝试了: {possible_paths}")

    def test_find_content_location_in_real_document(self, sample_doc_path):
        """测试：在真实文档中查找内容位置。"""
        from document import find_content_location

        # 查找已知存在的文本
        result = find_content_location(str(sample_doc_path), "西锐飞机")

        assert result["found"] is True
        assert result["type"] in ["table", "paragraph"]
        assert "context" in result

    def test_get_document_structure_of_real_document(self, sample_doc_path):
        """测试：获取真实文档的结构信息。"""
        from document import get_document_structure

        result = get_document_structure(str(sample_doc_path))

        assert "paragraphs_count" in result
        assert "tables_count" in result
        assert result["paragraphs_count"] > 0
        assert isinstance(result["tables"], list)

    def test_find_abstract_by_elements(self, sample_doc_path):
        """测试：根据 elements 查找摘要位置。"""
        from document import find_abstract_by_elements

        elements = {"company": "西锐飞机", "ticker": "2507.HK"}

        result = find_abstract_by_elements(str(sample_doc_path), elements)

        # 摘要应该在文档中找到
        assert isinstance(result, dict)
        assert "found" in result

    def test_find_elements_yaml_with_sample(self, sample_doc_path):
        """测试：查找样本文档的 elements.yaml。"""
        result = find_elements_yaml(sample_doc_path)

        # company_sample.docx 应该有对应的 elements.yaml
        assert result is not None
        assert "elements.yaml" in result.name
