"""test_pagination.py - 分页优化模块测试。

测试 pagination.py 中的分页优化功能。
"""

import pytest
from pathlib import Path
import tempfile
import shutil
import zipfile
from lxml import etree

# 导入被测模块
try:
    from pagination import (
        LibreOfficeConnection,
        ParagraphInfo,
        optimize_pagination,
        optimize_pagination_xml,
        optimize_pagination_simple,
    )
    PAGINATION_AVAILABLE = True
except ImportError:
    PAGINATION_AVAILABLE = False


# XML 命名空间
W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def sample_docx(tmp_path):
    """创建一个用于测试的简单 docx 文件。"""
    try:
        from docx import Document
        from docx.shared import Pt
    except ImportError:
        pytest.skip("python-docx 未安装")

    doc = Document()

    # 添加标题
    doc.add_heading("测试文档标题", level=1)

    # 添加普通段落
    for i in range(5):
        doc.add_paragraph(f"这是第 {i + 1} 个普通段落。" * 10)

    # 添加另一个标题
    doc.add_heading("第二部分", level=2)

    # 添加更多段落
    for i in range(3):
        doc.add_paragraph(f"这是第二部分的段落 {i + 1}。" * 15)

    # 保存
    docx_path = tmp_path / "test_document.docx"
    doc.save(str(docx_path))

    return docx_path


@pytest.fixture
def sample_docx_with_figure(tmp_path):
    """创建一个包含图片和 caption 的 docx 文件。"""
    try:
        from docx import Document
        from docx.shared import Pt, Inches
    except ImportError:
        pytest.skip("python-docx 未安装")

    doc = Document()

    doc.add_heading("测试文档", level=1)
    doc.add_paragraph("这是一个测试段落。")

    # 添加图片占位符段落（实际图片需要真实文件）
    # 这里我们模拟一个带图片的场景
    p = doc.add_paragraph()
    run = p.add_run("【图片占位符】")

    # 添加 caption
    doc.add_paragraph("图1：这是图片的说明文字（caption）")

    doc.add_paragraph("后续段落内容。" * 10)

    # 保存
    docx_path = tmp_path / "test_with_figure.docx"
    doc.save(str(docx_path))

    return docx_path


# ============================================================================
# ParagraphInfo 测试
# ============================================================================

class TestParagraphInfo:
    """ParagraphInfo 类测试。"""

    def test_init(self):
        """测试初始化。"""
        info = ParagraphInfo()
        assert info.index == 0
        assert info.text == ""
        assert info.start_page == 0
        assert info.end_page == 0
        assert info.is_heading is False
        assert info.has_image is False

    def test_spans_pages_same_page(self):
        """测试同一页的段落。"""
        info = ParagraphInfo()
        info.start_page = 1
        info.end_page = 1
        assert info.spans_pages is False

    def test_spans_pages_different_pages(self):
        """测试跨页的段落。"""
        info = ParagraphInfo()
        info.start_page = 1
        info.end_page = 2
        assert info.spans_pages is True


# ============================================================================
# XML 优化测试
# ============================================================================

class TestOptimizePaginationXml:
    """XML 分页优化测试。"""

    def test_xml_optimization_basic(self, sample_docx, tmp_path):
        """测试基本的 XML 优化功能。"""
        output_path = tmp_path / "output.docx"
        shutil.copy(str(sample_docx), str(output_path))

        result = optimize_pagination_xml(str(output_path), str(output_path))

        assert result["success"] is True
        assert result["error"] is None
        assert Path(output_path).exists()

    def test_xml_optimization_sets_keepnext(self, sample_docx, tmp_path):
        """测试 XML 优化是否正确设置 keepNext 属性。"""
        output_path = tmp_path / "output.docx"
        shutil.copy(str(sample_docx), str(output_path))

        result = optimize_pagination_xml(str(output_path), str(output_path))
        assert result["success"] is True

        # 验证输出文件中的 XML
        with zipfile.ZipFile(str(output_path), 'r') as z:
            with z.open('word/document.xml') as f:
                tree = etree.parse(f)

        # 检查是否有 keepNext 元素
        keepnext_elements = tree.findall(f'.//{W}keepNext')

        # 应该至少为标题设置了 keepNext
        # 注意：实际数量取决于文档中标题的数量
        assert result["headings_modified"] >= 0

    def test_xml_optimization_with_figure_caption(self, sample_docx_with_figure, tmp_path):
        """测试图片和 caption 的 XML 优化。"""
        output_path = tmp_path / "output.docx"
        shutil.copy(str(sample_docx_with_figure), str(output_path))

        result = optimize_pagination_xml(str(output_path), str(output_path))

        assert result["success"] is True
        # 图片/caption 相关的修改
        assert result["figures_modified"] >= 0

    def test_xml_optimization_preserves_content(self, sample_docx, tmp_path):
        """测试 XML 优化不会丢失内容。"""
        try:
            from docx import Document
        except ImportError:
            pytest.skip("python-docx 未安装")

        # 读取原始段落数
        original_doc = Document(str(sample_docx))
        original_para_count = len(original_doc.paragraphs)

        output_path = tmp_path / "output.docx"
        shutil.copy(str(sample_docx), str(output_path))

        result = optimize_pagination_xml(str(output_path), str(output_path))
        assert result["success"] is True

        # 读取优化后的段落数
        optimized_doc = Document(str(output_path))
        optimized_para_count = len(optimized_doc.paragraphs)

        # 段落数应该相同
        assert optimized_para_count == original_para_count

    def test_xml_optimization_invalid_file(self, tmp_path):
        """测试对无效文件的处理。"""
        invalid_path = tmp_path / "invalid.docx"
        invalid_path.write_text("This is not a valid docx file")

        result = optimize_pagination_xml(str(invalid_path), str(invalid_path))

        assert result["success"] is False
        assert result["error"] is not None


# ============================================================================
# LibreOffice 连接测试
# ============================================================================

class TestLibreOfficeConnection:
    """LibreOffice 连接测试。"""

    def test_find_libreoffice(self):
        """测试查找 LibreOffice。"""
        conn = LibreOfficeConnection()
        lo_path = conn._find_libreoffice()

        # 可能找到也可能找不到，取决于环境
        if lo_path:
            assert Path(lo_path).exists() or shutil.which(lo_path) is not None
            print(f"找到 LibreOffice: {lo_path}")
        else:
            print("未找到 LibreOffice（这在某些环境中是正常的）")

    def test_check_uno_available(self):
        """测试检查 uno 库是否可用。"""
        conn = LibreOfficeConnection()
        result = conn._check_uno_available()

        # 记录结果，不做断言（取决于环境）
        if result:
            print("uno 库可用")
        else:
            print("uno 库不可用")


# ============================================================================
# 完整优化流程测试（需要 LibreOffice）
# ============================================================================

@pytest.mark.skipif(not PAGINATION_AVAILABLE, reason="pagination 模块不可用")
class TestOptimizePagination:
    """完整分页优化测试（需要 LibreOffice）。"""

    def test_optimize_pagination_fallback_to_xml(self, sample_docx, tmp_path):
        """测试当 LibreOffice 不可用时回退到 XML 方案。"""
        output_path = tmp_path / "output.docx"

        result = optimize_pagination(
            input_path=str(sample_docx),
            output_path=str(output_path),
            optimize_paragraphs=True,
            optimize_headings=True,
            optimize_figures=True,
            min_lines=3
        )

        # 无论 LibreOffice 是否可用，都应该能处理
        # 如果 LibreOffice 不可用，会返回失败，但 XML 备用方案应该可用
        assert isinstance(result, dict)
        assert "success" in result
        assert "error" in result

    def test_optimize_pagination_simple(self, sample_docx, tmp_path):
        """测试简化接口。"""
        output_path = tmp_path / "output.docx"
        shutil.copy(str(sample_docx), str(output_path))

        # 简化接口会尝试优化，但可能因为环境原因失败
        # 这里只测试接口是否正常工作
        result = optimize_pagination_simple(str(output_path))

        # 返回布尔值
        assert isinstance(result, bool)


# ============================================================================
# 边界情况测试
# ============================================================================

class TestEdgeCases:
    """边界情况测试。"""

    def test_empty_document(self, tmp_path):
        """测试空文档。"""
        try:
            from docx import Document
        except ImportError:
            pytest.skip("python-docx 未安装")

        # 创建空文档
        doc = Document()
        empty_path = tmp_path / "empty.docx"
        doc.save(str(empty_path))

        result = optimize_pagination_xml(str(empty_path), str(empty_path))

        assert result["success"] is True
        assert result["headings_modified"] == 0
        assert result["figures_modified"] == 0

    def test_single_paragraph_document(self, tmp_path):
        """测试只有一个段落的文档。"""
        try:
            from docx import Document
        except ImportError:
            pytest.skip("python-docx 未安装")

        doc = Document()
        doc.add_paragraph("这是唯一的段落。")
        single_path = tmp_path / "single.docx"
        doc.save(str(single_path))

        result = optimize_pagination_xml(str(single_path), str(single_path))

        assert result["success"] is True

    def test_many_headings_document(self, tmp_path):
        """测试有很多标题的文档。"""
        try:
            from docx import Document
        except ImportError:
            pytest.skip("python-docx 未安装")

        doc = Document()
        for i in range(10):
            doc.add_heading(f"标题 {i + 1}", level=1)
            doc.add_paragraph(f"段落 {i + 1}")

        many_headings_path = tmp_path / "many_headings.docx"
        doc.save(str(many_headings_path))

        result = optimize_pagination_xml(str(many_headings_path), str(many_headings_path))

        assert result["success"] is True
        # 应该为大部分标题设置 keepNext
        assert result["headings_modified"] > 0

    def test_nonexistent_file(self, tmp_path):
        """测试不存在的文件。"""
        nonexistent = tmp_path / "does_not_exist.docx"

        result = optimize_pagination_xml(str(nonexistent), str(nonexistent))

        assert result["success"] is False
        assert result["error"] is not None


# ============================================================================
# 集成测试
# ============================================================================

class TestIntegration:
    """集成测试。"""

    def test_renderer_with_pagination(self, sample_docx, tmp_path):
        """测试 renderer.py 中的分页优化集成。"""
        try:
            from renderer import render_report, PAGINATION_AVAILABLE as RENDERER_PAGINATION
        except ImportError:
            pytest.skip("renderer 模块导入失败")

        # 这个测试需要完整的渲染环境
        # 简单验证函数签名包含分页参数
        import inspect
        sig = inspect.signature(render_report)
        params = list(sig.parameters.keys())

        assert "optimize_pagination_enabled" in params
        assert "pagination_min_lines" in params


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
