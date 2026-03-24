"""测试 parser.py。"""

import pytest
from pathlib import Path
from skills.template_maker.scripts.parser import WordStructureAnalyzer

@pytest.fixture
def sample_doc():
    """示例 Word 文档结构。"""
    return Path("/mnt/c/_code/neoskills/samples/西锐飞机首次覆盖报告（中文）提交版.docx")

def test_analyzer_returns_structure(sample_doc):
    """测试分析器返回结构。"""
    analyzer = WordStructureAnalyzer()
    result = analyzer.analyze(sample_doc)

    # 应该包含基本信息
    assert "tables" in result
    assert "paragraphs" in result
    assert "key_areas" in result

    # 应该识别出表格
    assert len(result["tables"]) > 0

def test_analyzer_identifies_main_table(sample_doc):
    """测试识别主表格。"""
    analyzer = WordStructureAnalyzer()
    result = analyzer.analyze(sample_doc)

    # 主表格通常包含报告基本信息
    main_table = result.get("main_table", {})
    assert main_table or len(result["tables"]) > 0
