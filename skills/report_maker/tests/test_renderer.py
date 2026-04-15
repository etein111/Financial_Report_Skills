"""测试 renderer 相关模块的函数。

renderer.py 已拆分为多个子模块：
- context.py: prepare_context_with_analysts, clean_value
- renderer.py: render_report（集成测试，此处只测准备阶段）
"""
import pytest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from context import prepare_context_with_analysts, clean_value


class TestCleanValue:
    """测试 clean_value 函数。"""

    def test_string_passthrough(self):
        assert clean_value("OUTPERFORM") == "OUTPERFORM"

    def test_none_returns_empty(self):
        assert clean_value(None) == ""

    def test_list_joins(self):
        assert clean_value(["a", "b"]) == "a, b"

    def test_int_converts(self):
        assert clean_value(42) == "42"


class TestPrepareContextWithAnalysts:
    """测试 prepare_context_with_analysts 函数。"""

    def test_basic_fields_copied(self):
        """基本字段直接复制到 context。"""
        elements = {
            "ticker": "2507.HK",
            "company": "西锐飞机",
            "rating": "OUTPERFORM",
        }

        context = prepare_context_with_analysts(elements)

        assert context["ticker"] == "2507.HK"
        assert context["company"] == "西锐飞机"
        assert context["rating"] == "OUTPERFORM"

    def test_analyst_fields_expanded(self):
        """a1~a8 字段展开为独立变量。"""
        elements = {
            "ticker": "2507.HK",
            "a1_name": "杨斌",
            "a1_email": "yang@test.com",
            "a2_name": "张三",
        }

        context = prepare_context_with_analysts(elements)

        assert context["a1_name"] == "杨斌"
        assert context["a1_email"] == "yang@test.com"
        assert context["a2_name"] == "张三"

    def test_target_price_converted_to_float(self):
        """target_price 转换为浮点数。"""
        elements = {
            "target_price": "73.40",
        }

        context = prepare_context_with_analysts(elements)

        assert context["target_price"] == 73.40

    def test_invalid_target_price_kept_as_is(self):
        """无效 target_price 保持原值。"""
        elements = {
            "target_price": "N/A",
        }

        context = prepare_context_with_analysts(elements)

        assert context["target_price"] == "N/A"

    def test_analyst_display_from_list(self):
        """analysts 列表生成 analyst_display 字段。"""
        elements = {
            "analysts": [
                {"name": "杨斌"},
                {"name": "张三"},
            ],
        }

        context = prepare_context_with_analysts(elements)

        assert context["analyst_display"] == "杨斌 / 张三"

    def test_analyst_display_empty_list(self):
        """空 analysts 列表不生成 analyst_display。"""
        elements = {
            "analysts": [],
        }

        context = prepare_context_with_analysts(elements)

        assert "analyst_display" not in context

    def test_immutability(self):
        """不修改原始 elements。"""
        elements = {"rating": "BUY", "target_price": "100"}

        context = prepare_context_with_analysts(elements)

        # elements 不应被修改
        assert elements["rating"] == "BUY"
        assert elements["target_price"] == "100"
