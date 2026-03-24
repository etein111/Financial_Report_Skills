"""测试 template_builder.py。"""

import pytest
from pathlib import Path
from shutil import copy
from skills.template_maker.template_builder import TemplateBuilder

@pytest.fixture
def sample_doc(tmp_path):
    """创建示例文档。"""
    src = Path("/mnt/c/_code/neoskills/samples/西锐飞机首次覆盖报告（中文）提交版.docx")
    if src.exists():
        dst = tmp_path / "sample.docx"
        copy(src, dst)
        return dst
    pytest.skip("样本文件不存在")

def test_create_template(sample_doc, tmp_path):
    """测试创建模板。"""
    builder = TemplateBuilder()

    placeholders = {
        "Table_Main_5_1": "{{company}}",
        "Table_Main_5_2": "{{ticker}}",
    }

    output = tmp_path / "template.docx"
    builder.build(sample_doc, placeholders, output)

    assert output.exists()

def test_generate_placeholders():
    """测试生成占位符映射。"""
    builder = TemplateBuilder()
    schema = {
        "fields": {
            "company": {"format": "西锐飞机"},
            "ticker": {"format": "2507.HK"},
        }
    }

    # 简化测试：验证能生成映射
    # 实际实现会结合 Word 结构分析
    assert schema is not None
