"""测试 core.py。"""

import pytest
from pathlib import Path
from shutil import copy, rmtree
import yaml
from skills.template_maker.core import TemplateMaker

@pytest.fixture
def sample_word(tmp_path):
    """创建示例 Word 文档。"""
    src = Path("/mnt/c/_code/neoskills/samples/西锐飞机首次覆盖报告（中文）提交版.docx")
    if src.exists():
        dst = tmp_path / "sample.docx"
        copy(src, dst)
        return dst
    pytest.skip("样本文件不存在")

@pytest.fixture
def sample_elements(tmp_path, sample_word):
    """创建示例 elements.yaml。"""
    elements = {
        "company": "西锐飞机",
        "ticker": "2507.HK",
    }
    elements_path = tmp_path / "elements.yaml"
    elements_path.write_text(yaml.dump(elements, allow_unicode=True))
    return elements_path

@pytest.fixture
def template_maker(tmp_path):
    """创建 TemplateMaker 实例。"""
    # 使用临时目录作为项目根目录
    maker = TemplateMaker(tmp_path)

    # 清理临时模板目录
    yield maker

    # 清理
    templates_dir = tmp_path / "templates"
    if templates_dir.exists():
        rmtree(templates_dir)

def test_create_template_success(template_maker, sample_word, sample_elements):
    """测试成功创建模板。"""
    result = template_maker.create_template(
        name="test_template",
        word_path=sample_word,
        elements_path=sample_elements
    )

    assert result["status"] == "success"
    assert "template_dir" in result
    assert result["fields_count"] > 0

    # 验证文件已创建
    template_dir = Path(result["template_dir"])
    assert (template_dir / "template.docx").exists()
    assert (template_dir / "schema.yaml").exists()
    assert (template_dir / "meta.yaml").exists()

def test_create_template_missing_elements(template_maker, sample_word, tmp_path):
    """测试缺少 elements.yaml。"""
    # 不创建 elements.yaml

    result = template_maker.create_template(
        name="test_template_no_elements",
        word_path=sample_word,
        elements_path=None
    )

    assert result["status"] == "error"
    assert "找不到 elements.yaml" in result["message"]

def test_create_template_auto_detect_elements(template_maker, sample_word, sample_elements):
    """测试自动检测 elements.yaml。"""
    # 将 elements.yaml 放在 Word 同目录
    result = template_maker.create_template(
        name="test_template_auto",
        word_path=sample_word,
        elements_path=None  # 自动检测
    )

    # 应该能找到同目录的 elements.yaml
    assert result["status"] == "success"

def test_create_multiple_templates(template_maker, sample_word, sample_elements):
    """测试创建多个模板。"""
    # 创建第一个模板
    result1 = template_maker.create_template(
        name="template_1",
        word_path=sample_word,
        elements_path=sample_elements
    )
    assert result1["status"] == "success"

    # 创建第二个模板
    result2 = template_maker.create_template(
        name="template_2",
        word_path=sample_word,
        elements_path=sample_elements
    )
    assert result2["status"] == "success"

    # 验证两个模板目录都存在
    assert Path(result1["template_dir"]).exists()
    assert Path(result2["template_dir"]).exists()
