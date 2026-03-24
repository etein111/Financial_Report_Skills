"""测试 utils.py。"""

import pytest
from pathlib import Path
from skills.template_maker.scripts.utils import find_elements_yaml

def test_find_elements_yaml_with_pair(tmp_path):
    """测试找到配对的 elements.yaml。"""
    # 创建测试文件
    (tmp_path / "sample.docx").touch()
    (tmp_path / "sample elements.yaml").touch()

    result = find_elements_yaml(tmp_path / "sample.docx")
    assert result == tmp_path / "sample elements.yaml"

def test_find_elements_yaml_not_found(tmp_path):
    """测试找不到 elements.yaml。"""
    (tmp_path / "sample.docx").touch()

    result = find_elements_yaml(tmp_path / "sample.docx")
    assert result is None

def test_find_elements_yaml_with_underscore(tmp_path):
    """测试找到带下划线的 elements.yaml。"""
    (tmp_path / "report.docx").touch()
    (tmp_path / "report_elements.yaml").touch()

    result = find_elements_yaml(tmp_path / "report.docx")
    assert result == tmp_path / "report_elements.yaml"

def test_find_elements_yaml_directory_level(tmp_path):
    """测试找到目录级别的 elements.yaml。"""
    (tmp_path / "analysis.docx").touch()
    (tmp_path / "elements.yaml").touch()

    result = find_elements_yaml(tmp_path / "analysis.docx")
    assert result == tmp_path / "elements.yaml"

def test_find_elements_yaml_priority(tmp_path):
    """测试优先级：配对文件优先于目录级别。"""
    (tmp_path / "data.docx").touch()
    (tmp_path / "data elements.yaml").touch()
    (tmp_path / "elements.yaml").touch()

    result = find_elements_yaml(tmp_path / "data.docx")
    assert result == tmp_path / "data elements.yaml"
