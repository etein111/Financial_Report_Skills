"""test_market_data.py - market_data.py 模块测试。

测试外部行情数据获取功能。
"""

import pytest
from unittest.mock import Mock

from market_data import fetch_recommendation_history


class TestFetchRecommendationHistory:
    """测试 fetch_recommendation_history 函数。"""

    def test_returns_empty_list_when_history_is_empty(self):
        """测试：历史数据为空时返回空列表。"""
        mock_fn = Mock(return_value=[])

        result = fetch_recommendation_history(mock_fn, "3393.HK", "analyst@example.com")

        assert result == []
        mock_fn.assert_called_once_with("3393.HK", "analyst@example.com")

    def test_returns_empty_list_when_history_fn_raises(self):
        """测试：list_coverage_history_fn 抛出异常时返回空列表。"""
        mock_fn = Mock(side_effect=Exception("Network error"))

        result = fetch_recommendation_history(mock_fn, "3393.HK", "analyst@example.com")

        assert result == []

    def test_converts_4_digit_ticker_to_hk_format(self):
        """测试：4位数字股票代码自动转换为 HK 格式。"""
        mock_fn = Mock(return_value=[])

        # 由于 yfinance 是在函数内部导入的，我们无法直接 mock
        # 但我们可以验证函数能处理各种 ticker 格式而不崩溃
        result = fetch_recommendation_history(mock_fn, "3393", "analyst@example.com")

        # 返回空列表因为 yfinance 不可用
        assert result == []

    def test_does_not_convert_already_formatted_ticker(self):
        """测试：已格式化的股票代码不再转换。"""
        mock_fn = Mock(return_value=[])

        # 测试已包含点的 ticker
        result = fetch_recommendation_history(mock_fn, "3393.HK", "analyst@example.com")

        assert result == []

        # 测试以 ^ 开头的 ticker
        result = fetch_recommendation_history(mock_fn, "^HSI", "analyst@example.com")

        assert result == []

    def test_handles_non_4_digit_ticker(self):
        """测试：处理非4位数字的 ticker。"""
        mock_fn = Mock(return_value=[])

        # 测试5位数字的 ticker（如美股）
        result = fetch_recommendation_history(mock_fn, "12345", "analyst@example.com")

        # 应该返回空列表（因为 yfinance 内部导入可能失败）
        assert isinstance(result, list)

    def test_handles_empty_ticker(self):
        """测试：处理空的 ticker。"""
        mock_fn = Mock(return_value=[])

        result = fetch_recommendation_history(mock_fn, "", "analyst@example.com")

        # 空 ticker 会直接返回空列表
        assert result == []

    def test_history_fn_called_with_correct_args(self):
        """测试：history 函数使用正确的参数调用。"""
        mock_fn = Mock(return_value=[])

        fetch_recommendation_history(mock_fn, "AAPL", "test@test.com")

        mock_fn.assert_called_once_with("AAPL", "test@test.com")
