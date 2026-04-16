"""测试 common.py 模块的函数。"""
import pytest
import tempfile
import yaml
from pathlib import Path

from common import (
    load_yaml,
    save_yaml,
    get_template_name,
    list_report_types,
    create_report_dir,
    normalize_report_name,
    get_all_field_names,
    filter_fragment_fields,
    ensure_all_fields,
    validate_elements_against_schema,
    DIR_REPORTS,
    DIR_TEMPLATES,
    FILE_ROUTER,
)


class TestLoadYaml:
    """测试 load_yaml 函数。"""

    def test_load_yaml_from_nonexistent_file(self):
        """测试：加载不存在的文件返回空字典。"""
        result = load_yaml(Path("/nonexistent/file.yaml"))
        assert result == {}

    def test_load_yaml_from_valid_file(self):
        """测试：加载有效的 YAML 文件。"""
        content = """
ticker: "2507.HK"
company: "西锐飞机"
rating: "OUTPERFORM"
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "test.yaml"
            file_path.write_text(content)

            result = load_yaml(file_path)

            assert result["ticker"] == "2507.HK"
            assert result["company"] == "西锐飞机"
            assert result["rating"] == "OUTPERFORM"


class TestSaveYaml:
    """测试 save_yaml 函数。"""

    def test_save_yaml_creates_directory(self):
        """测试：保存时自动创建目录。"""
        data = {"ticker": "2507.HK"}

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "subdir" / "test.yaml"
            save_yaml(file_path, data)

            assert file_path.exists()
            assert file_path.parent.is_dir()

    def test_save_and_load_roundtrip(self):
        """测试：保存后加载能得到相同数据。"""
        original_data = {
            "ticker": "2507.HK",
            "company": "西锐飞机",
            "rating": "OUTPERFORM"
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "test.yaml"
            save_yaml(file_path, original_data)
            loaded_data = load_yaml(file_path)

            assert loaded_data == original_data


class TestGetTemplateName:
    """测试 get_template_name 函数。"""

    def test_get_existing_template(self):
        """测试：获取存在的模板名。"""
        content = """
mappings:
  company: company
  macro: common
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            router_path = Path(tmpdir) / FILE_ROUTER
            router_path.write_text(content)

            result = get_template_name("company", router_path)

            assert result == "company"

    def test_get_nonexistent_template(self):
        """测试：获取不存在的模板返回 None。"""
        content = """
mappings:
  company: company
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            router_path = Path(tmpdir) / FILE_ROUTER
            router_path.write_text(content)

            result = get_template_name("macro", router_path)

            assert result is None


class TestListReportTypes:
    """测试 list_report_types 函数。"""

    def test_list_all_report_types(self):
        """测试：列出所有报告类型。"""
        content = """
mappings:
  company: company
  sector: sector
  macro: common
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            router_path = Path(tmpdir) / FILE_ROUTER
            router_path.write_text(content)

            result = list_report_types(router_path)

            assert set(result) == {"company", "sector", "macro"}

    def test_list_empty_mappings(self):
        """测试：空 mappings 返回空列表。"""
        content = "mappings: {}"
        with tempfile.TemporaryDirectory() as tmpdir:
            router_path = Path(tmpdir) / FILE_ROUTER
            router_path.write_text(content)

            result = list_report_types(router_path)

            assert result == []


class TestCreateReportDir:
    """测试 create_report_dir 函数。"""

    def test_create_report_dir(self):
        """测试：创建报告目录。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            report_dir = create_report_dir("test_report", tmpdir)

            assert report_dir.exists()
            assert report_dir.name == "test_report"
            assert report_dir.parent == Path(tmpdir)

    def test_create_nested_report_dir(self):
        """测试：创建嵌套报告目录。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            report_dir = create_report_dir("2025/03/test_report", tmpdir)

            assert report_dir.exists()
            assert report_dir.is_dir()


class TestNormalizeReportName:
    """测试 normalize_report_name 函数。"""

    def test_remove_common_prefixes(self):
        """测试：去除常见前缀。"""
        assert normalize_report_name("draft_test.docx") == "test"
        assert normalize_report_name("草稿_test.docx") == "test"
        assert normalize_report_name("final_test.docx") == "test"

    def test_remove_common_suffixes(self):
        """测试：去除常见后缀。"""
        assert normalize_report_name("test_draft.docx") == "test"
        assert normalize_report_name("test_final.docx") == "test"
        assert normalize_report_name("test_v2.docx") == "test"

    def test_remove_extension(self):
        """测试：去除文件扩展名。"""
        assert normalize_report_name("test.docx") == "test"
        assert normalize_report_name("test.pdf") == "test"

    def test_keep_clean_name(self):
        """测试：保留干净的名称。"""
        assert normalize_report_name("西锐飞机首次覆盖报告.docx") == "西锐飞机首次覆盖报告"


class TestGetAllFieldNames:
    """测试 get_all_field_names 函数。"""

    def test_get_all_field_names(self):
        """测试：获取所有字段名。"""
        schema = {
            "ticker": {"description": "股票代码"},
            "company": {"description": "公司名"},
            "rating": {"description": "评级"}
        }

        result = get_all_field_names(schema)

        assert result == ["ticker", "company", "rating"]


class TestFilterFragmentFields:
    """测试 filter_fragment_fields 函数。"""

    def test_filter_abstract_and_body(self):
        """测试：过滤 abstract 和 body 字段。"""
        fields = ["ticker", "company", "abstract", "rating", "body"]

        result = filter_fragment_fields(fields)

        assert result == ["ticker", "company", "rating"]

    def test_no_fragment_fields(self):
        """测试：没有 fragment 字段时返回全部。"""
        fields = ["ticker", "company", "rating"]

        result = filter_fragment_fields(fields)

        assert result == ["ticker", "company", "rating"]


class TestEnsureAllFields:
    """测试 ensure_all_fields 函数。"""

    def test_add_missing_fields(self):
        """测试：添加缺失的字段。"""
        elements = {"ticker": "2507.HK", "company": "西锐飞机"}
        schema = {
            "ticker": {},
            "company": {},
            "rating": {}
        }

        result = ensure_all_fields(elements, schema)

        assert result["ticker"] == "2507.HK"
        assert result["company"] == "西锐飞机"
        assert result["rating"] == ""

    def test_preserve_existing_fields(self):
        """测试：保留已有字段。"""
        elements = {
            "ticker": "2507.HK",
            "company": "西锐飞机",
            "rating": "OUTPERFORM"
        }
        schema = {
            "ticker": {},
            "company": {},
            "rating": {}
        }

        result = ensure_all_fields(elements, schema)

        assert result["ticker"] == "2507.HK"
        assert result["company"] == "西锐飞机"
        assert result["rating"] == "OUTPERFORM"

    def test_immutability(self):
        """测试：不修改原数据（不可变性）。"""
        elements = {"ticker": "2507.HK"}
        schema = {"ticker": {}, "company": {}}

        result = ensure_all_fields(elements, schema)

        # 原 elements 不应被修改
        assert "company" not in elements
        # 新 result 包含所有字段
        assert "company" in result


class TestValidateElementsAgainstSchema:
    """测试 validate_elements_against_schema 函数。"""

    def test_valid_elements(self):
        """测试：有效的 elements 返回空错误列表。"""
        elements = {"ticker": "2507.HK", "company": "西锐飞机"}
        schema = {"ticker": {}, "company": {}}

        errors = validate_elements_against_schema(elements, schema)

        assert errors == []

    def test_missing_fields(self):
        """测试：检测缺失字段。"""
        elements = {"ticker": "2507.HK"}
        schema = {"ticker": {}, "company": {}, "rating": {}}

        errors = validate_elements_against_schema(elements, schema)

        assert len(errors) == 1
        assert "缺少字段" in errors[0]
        assert "company" in errors[0]
        assert "rating" in errors[0]

    def test_extra_fields(self):
        """测试：检测多余字段。"""
        elements = {"ticker": "2507.HK", "company": "西锐飞机", "extra": "额外字段"}
        schema = {"ticker": {}, "company": {}}

        errors = validate_elements_against_schema(elements, schema)

        assert len(errors) == 1
        assert "多余字段" in errors[0]
        assert "extra" in errors[0]

    def test_both_missing_and_extra(self):
        """测试：同时有缺失和多余字段。"""
        elements = {"ticker": "2507.HK", "extra": "额外字段"}
        schema = {"ticker": {}, "company": {}}

        errors = validate_elements_against_schema(elements, schema)

        assert len(errors) == 2
