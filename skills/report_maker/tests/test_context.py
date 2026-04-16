"""test_context.py - context.py 模块测试。

测试上下文准备功能。
"""

import pytest

class TestEnrichCompanyNamesWithYfinance:
    """测试 enrich_company_names_with_yfinance 函数。"""

    def test_returns_elements_unmodified_when_no_ticker(self):
        """测试：无 ticker 时返回未修改的元素。"""
        from context import enrich_company_names_with_yfinance

        elements = {"company": "西锐飞机", "rating": "BUY"}

        result = enrich_company_names_with_yfinance(elements)

        assert result["company"] == "西锐飞机"
        assert "company_en" not in result

    def test_skips_when_company_en_already_exists(self):
        """测试：company_en 已存在时跳过。"""
        from context import enrich_company_names_with_yfinance

        elements = {"ticker": "3393.HK", "company_en": "Existing Name", "company_cn": "现有公司"}

        # 当 company_en 和 company_cn 都存在时，不会调用 yfinance
        result = enrich_company_names_with_yfinance(elements)

        assert result["company_en"] == "Existing Name"
        assert result["company_cn"] == "现有公司"

    def test_enriches_when_names_missing(self):
        """测试：名称缺失时尝试补全。"""
        from context import enrich_company_names_with_yfinance

        elements = {"ticker": "3393.HK"}

        # 由于 yfinance 可能不可用，测试只验证函数行为
        result = enrich_company_names_with_yfinance(elements)

        # 函数应该返回字典，不抛出异常
        assert isinstance(result, dict)
        assert "ticker" in result


class TestCleanValue:
    """测试 clean_value 函数。"""

    def test_returns_empty_string_for_none(self):
        """测试：None 返回空字符串。"""
        from context import clean_value

        result = clean_value(None)

        assert result == ""

    def test_joins_list_values(self):
        """测试：列表值被逗号连接。"""
        from context import clean_value

        result = clean_value([1, 2, 3])

        assert result == "1, 2, 3"

    def test_converts_string_to_string(self):
        """测试：字符串保持不变。"""
        from context import clean_value

        result = clean_value("test string")

        assert result == "test string"

    def test_converts_integer_to_string(self):
        """测试：整数转换为字符串。"""
        from context import clean_value

        result = clean_value(123)

        assert result == "123"


class TestPrepareContextWithAnalysts:
    """测试 prepare_context_with_analysts 函数。"""

    def test_preserves_non_analyst_fields(self):
        """测试：保留非分析师字段。"""
        from context import prepare_context_with_analysts

        elements = {
            "company": "西锐飞机",
            "ticker": "3393.HK",
            "rating": "BUY"
        }

        result = prepare_context_with_analysts(elements)

        assert result["company"] == "西锐飞机"
        assert result["ticker"] == "3393.HK"
        assert result["rating"] == "BUY"

    def test_expands_analyst_fields(self):
        """测试：展开分析师字段。"""
        from context import prepare_context_with_analysts

        elements = {
            "a1_name": "杨斌",
            "a1_email": "yang@example.com",
            "a1_certification": "SFC:BSQ313"
        }

        result = prepare_context_with_analysts(elements)

        assert result["a1_name"] == "杨斌"
        assert result["a1_email"] == "yang@example.com"
        assert result["a1_certification"] == "SFC:BSQ313"

    def test_converts_target_price_to_float(self):
        """测试：target_price 转换为浮点数。"""
        from context import prepare_context_with_analysts

        elements = {"target_price": "15.6"}

        result = prepare_context_with_analysts(elements)

        assert result["target_price"] == 15.6
        assert isinstance(result["target_price"], float)

    def test_keeps_invalid_target_price_as_is(self):
        """测试：无效的 target_price 保持原样。"""
        from context import prepare_context_with_analysts

        elements = {"target_price": "not a number"}

        result = prepare_context_with_analysts(elements)

        assert result["target_price"] == "not a number"

    def test_handles_analyst_abbr_for_display(self):
        """测试：处理 analyst_abbr 显示字段。"""
        from context import prepare_context_with_analysts

        elements = {
            "analysts": [
                {"name": "杨斌"},
                {"name": "其他分析师"}
            ]
        }

        result = prepare_context_with_analysts(elements)

        assert "analyst_display" in result
        assert "杨斌" in result["analyst_display"]

    def test_ignores_non_analyst_fields_starting_with_a(self):
        """测试：忽略不以数字开头的 a* 字段。"""
        from context import prepare_context_with_analysts

        elements = {
            "abstract": "Some abstract text",
            "a1_name": "分析师"
        }

        result = prepare_context_with_analysts(elements)

        assert result["abstract"] == "Some abstract text"
        assert "a1_name" in result

    def test_analyst_display_empty_list(self):
        """测试：空 analysts 列表不生成 analyst_display。"""
        from context import prepare_context_with_analysts

        elements = {
            "analysts": [],
        }

        result = prepare_context_with_analysts(elements)

        assert "analyst_display" not in result

    def test_immutability(self):
        """测试：不修改原始 elements。"""
        from context import prepare_context_with_analysts

        elements = {"rating": "BUY", "target_price": "100"}

        result = prepare_context_with_analysts(elements)

        assert elements["rating"] == "BUY"
        assert elements["target_price"] == "100"


class TestContextModuleAvailability:
    """测试 context 模块可用性标志。"""

    def test_charts_available_flag_exists(self):
        """测试：CHARTS_AVAILABLE 标志存在。"""
        from context import CHARTS_AVAILABLE

        assert isinstance(CHARTS_AVAILABLE, bool)
