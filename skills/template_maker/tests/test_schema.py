"""测试 schema.py 模块的函数。"""
import pytest
import tempfile
from pathlib import Path

# 导入被测试的模块
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from schema import (
    generate_schema,
    load_schema,
    save_schema,
    update_field,
    update_fragment,
    DEFAULT_ABSTRACT,
    DEFAULT_BODY
)


class TestGenerateSchema:
    """测试 generate_schema 函数。"""

    def test_generate_schema_with_basic_elements(self):
        """测试：从基本 elements 生成 schema。"""
        elements = {
            "company": "西锐飞机",
            "ticker": "2507.HK",
            "analyst": "张三"
        }

        result = generate_schema(elements)

        # 验证普通字段
        assert "company" in result
        assert result["company"]["description"] == "company"
        assert result["company"]["format"] == "西锐飞机"

        assert "ticker" in result
        assert result["ticker"]["format"] == "2507.HK"

        # analysts 应该被排除
        assert "analysts" not in result

        # abstract 应该存在
        assert "abstract" in result
        assert result["abstract"]["type"] == "fragment"

    def test_generate_schema_with_null_values(self):
        """测试：处理 null 值的元素。"""
        elements = {
            "company": "测试公司",
            "rating": "null",
            "target_price": None
        }

        result = generate_schema(elements)

        # null 值不应包含 format
        assert "company" in result
        assert result["company"]["format"] == "测试公司"

        # "null" 字符串和 None 都不应包含 format
        assert "rating" in result
        assert "format" not in result["rating"]

        assert "target_price" in result
        assert "format" not in result["target_price"]

    def test_generate_schema_excludes_analysts(self):
        """测试：analysts 字段应被排除。"""
        elements = {
            "company": "测试",
            "analysts": ["张三", "李四"]
        }

        result = generate_schema(elements)

        assert "company" in result
        assert "analysts" not in result

    def test_generate_schema_always_has_abstract(self):
        """测试：abstract 必须始终存在。"""
        elements = {}

        result = generate_schema(elements)

        assert "abstract" in result
        assert result["abstract"]["type"] == "fragment"
        assert result["abstract"]["description"] == "报告摘要部分"

    def test_generate_schema_body_enabled_by_default(self):
        """测试：body 默认启用。"""
        elements = {"company": "测试"}

        result = generate_schema(elements)

        assert "body" in result
        assert result["body"]["type"] == "fragment"

    def test_generate_schema_body_can_be_disabled(self):
        """测试：body 可以通过 {"enabled": False} 禁用。"""
        elements = {"company": "测试"}

        result = generate_schema(elements, body_config={"enabled": False})

        assert "body" not in result

    def test_generate_schema_body_config_none_enables_body(self):
        """测试：body_config=None 时启用 body。"""
        elements = {"company": "测试"}

        # 测试 None 的默认行为（应该启用 body）
        result = generate_schema(elements, body_config=None)

        assert "body" in result

    def test_generate_schema_with_custom_abstract_config(self):
        """测试：可以自定义 abstract 配置。"""
        elements = {"company": "测试"}
        custom_config = {
            "scope": "自定义摘要位置",
            "hints": ["自定义提示1", "自定义提示2"]
        }

        result = generate_schema(elements, abstract_config=custom_config)

        assert result["abstract"]["scope"] == "自定义摘要位置"
        assert result["abstract"]["hints"] == ["自定义提示1", "自定义提示2"]


class TestSchemaFileOperations:
    """测试 schema 文件的加载和保存。"""

    def test_save_and_load_schema(self):
        """测试：保存和加载 schema 文件。"""
        schema = {
            "name": "test_template",
            "fields": {
                "company": {
                    "description": "公司名称",
                    "format": "西锐飞机"
                }
            }
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            schema_path = Path(tmpdir) / "schema.yaml"

            # 保存
            save_schema(str(schema_path), schema)

            # 验证文件存在
            assert schema_path.exists()

            # 加载
            loaded = load_schema(str(schema_path))

            # 验证内容
            assert loaded["name"] == "test_template"
            assert loaded["fields"]["company"]["format"] == "西锐飞机"

    def test_load_schema_from_nonexistent_file_raises_error(self):
        """测试：加载不存在的文件应抛出异常。"""
        with pytest.raises(FileNotFoundError):
            load_schema("/nonexistent/path/schema.yaml")


class TestUpdateField:
    """测试 update_field 函数。"""

    def test_update_field_adds_new_field(self):
        """测试：添加新字段。"""
        schema = {"company": {"description": "公司"}}

        result = update_field(schema, "ticker", "股票代码", "2507.HK")

        assert result["ticker"]["description"] == "股票代码"
        assert result["ticker"]["format"] == "2507.HK"

    def test_update_field_updates_existing_field(self):
        """测试：更新已有字段。"""
        schema = {"company": {"description": "公司"}}

        result = update_field(schema, "company", "公司名称", "西锐飞机")

        assert result["company"]["description"] == "公司名称"
        assert result["company"]["format"] == "西锐飞机"

    def test_update_field_without_format(self):
        """测试：不提供 format 时只更新描述。"""
        schema = {"company": {"description": "公司"}}

        result = update_field(schema, "company", "公司名称")

        assert result["company"]["description"] == "公司名称"
        assert "format" not in result["company"]

    def test_update_field_returns_new_schema(self):
        """测试：返回新 schema，不修改原 schema（不可变性）。"""
        schema = {"company": {"description": "公司"}}

        result = update_field(schema, "company", "新公司")

        # 原 schema 不应被修改
        assert schema["company"]["description"] == "公司"
        # 新 schema 被修改
        assert result["company"]["description"] == "新公司"


class TestUpdateFragment:
    """测试 update_fragment 函数。"""

    def test_update_fragment_abstract_scope(self):
        """测试：更新 abstract 的 scope。"""
        schema = {"abstract": DEFAULT_ABSTRACT.copy()}

        result = update_fragment(schema, "abstract", scope="新位置")

        assert result["abstract"]["scope"] == "新位置"

    def test_update_fragment_abstract_hints(self):
        """测试：更新 abstract 的 hints。"""
        schema = {"abstract": DEFAULT_ABSTRACT.copy()}
        new_hints = ["新提示1", "新提示2"]

        result = update_fragment(schema, "abstract", hints=new_hints)

        assert result["abstract"]["hints"] == new_hints

    def test_update_fragment_body_scope_and_hints(self):
        """测试：同时更新 body 的 scope 和 hints。"""
        schema = {"body": DEFAULT_BODY.copy()}

        result = update_fragment(
            schema,
            "body",
            scope="新正文位置",
            hints=["正文提示1", "正文提示2"]
        )

        assert result["body"]["scope"] == "新正文位置"
        assert result["body"]["hints"] == ["正文提示1", "正文提示2"]

    def test_update_fragment_returns_new_schema(self):
        """测试：返回新 schema，不修改原 schema（不可变性）。"""
        schema = {"abstract": DEFAULT_ABSTRACT.copy()}

        result = update_fragment(schema, "abstract", scope="新位置")

        # 原 schema 不应被修改
        assert schema["abstract"]["scope"] != "新位置"
        # 新 schema 被修改
        assert result["abstract"]["scope"] == "新位置"
