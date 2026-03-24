"""测试 validator.py。"""

import pytest
from pathlib import Path
from shutil import copy
import yaml
from skills.template_maker.scripts.validator import TemplateValidator

@pytest.fixture
def sample_template(tmp_path):
    """创建示例模板文件。"""
    src = Path("/mnt/c/_code/neoskills/samples/西锐飞机首次覆盖报告（中文）提交版.docx")
    if src.exists():
        dst = tmp_path / "template.docx"
        copy(src, dst)
        return dst
    pytest.skip("样本文件不存在")

@pytest.fixture
def sample_elements(tmp_path):
    """创建示例 elements.yaml。"""
    elements = {
        "company": "西锐飞机",
        "ticker": "2507.HK",
    }
    elements_path = tmp_path / "elements.yaml"
    elements_path.write_text(yaml.dump(elements, allow_unicode=True))
    return elements_path

def test_validate_success(sample_template, sample_elements):
    """测试验证成功。"""
    validator = TemplateValidator()
    success, message = validator.validate(sample_template, sample_elements)

    assert success is True
    assert "验证通过" in message

def test_validate_missing_template(sample_elements):
    """测试模板文件不存在。"""
    validator = TemplateValidator()
    success, message = validator.validate(
        Path("/nonexistent/template.docx"),
        sample_elements
    )

    assert success is False
    assert "验证失败" in message

def test_validate_invalid_elements(sample_template, tmp_path):
    """测试无效的 elements.yaml。"""
    invalid_elements = tmp_path / "invalid.yaml"
    invalid_elements.write_text("invalid: yaml: content: [")

    validator = TemplateValidator()
    success, message = validator.validate(sample_template, invalid_elements)

    assert success is False
    assert "验证失败" in message
