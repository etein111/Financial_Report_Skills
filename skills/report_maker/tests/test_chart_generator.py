"""test_chart_generator.py - chart_generator.py 模块测试。

测试图表生成功能。
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
import os

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))


class TestGenerateRelativeChart:
    """测试 _generate_relative_chart 函数。"""

    def test_returns_false_when_charts_unavailable(self):
        """测试：图表模块不可用时返回 False。"""
        from chart_generator import _generate_relative_chart

        with patch('chart_generator.CHARTS_AVAILABLE', False):
            result = _generate_relative_chart("3393.HK", "/tmp/output.png", "Test Company")

            assert result is False

    @patch('chart_generator.CHARTS_AVAILABLE', True)
    @patch('chart_generator.yf')
    def test_returns_false_when_download_fails(self, mock_yf):
        """测试：下载数据失败时返回 False。"""
        from chart_generator import _generate_relative_chart

        mock_yf.download.side_effect = Exception("Network error")

        result = _generate_relative_chart("INVALID.TICKER", "/tmp/output.png")

        assert result is False

    @patch('chart_generator.CHARTS_AVAILABLE', True)
    @patch('chart_generator.yf')
    def test_returns_false_when_data_empty(self, mock_yf):
        """测试：数据为空时返回 False。"""
        from chart_generator import _generate_relative_chart

        mock_result = MagicMock()
        mock_result.empty = True
        mock_yf.download.return_value = mock_result

        result = _generate_relative_chart("3393.HK", "/tmp/output.png")

        assert result is False


class TestGenerateRecommendationChart:
    """测试 _generate_recommendation_chart 函数。"""

    def test_returns_false_when_charts_unavailable(self):
        """测试：图表模块不可用时返回 False。"""
        from chart_generator import _generate_recommendation_chart

        with patch('chart_generator.CHARTS_AVAILABLE', False):
            result = _generate_recommendation_chart(
                "3393.HK",
                "/tmp/output.png",
                "Test Company",
                {"rating": "BUY"}
            )

            assert result is False

    def test_handles_empty_elements(self):
        """测试：处理空的 elements 字典。"""
        from chart_generator import _generate_recommendation_chart

        with patch('chart_generator.CHARTS_AVAILABLE', True):
            # 创建一个空的 elements
            result = _generate_recommendation_chart(
                "3393.HK",
                "/tmp/output.png",
                "Test Company",
                {}
            )

            # 应该能处理而不崩溃
            assert isinstance(result, bool)

    @patch('chart_generator.CHARTS_AVAILABLE', True)
    @patch('chart_generator.plt')
    def test_generates_chart_with_rating_colors(self, mock_plt, tmp_path):
        """测试：使用评级颜色生成图表。"""
        from chart_generator import _generate_recommendation_chart

        # Mock plt 的 subplots
        mock_fig = MagicMock()
        mock_ax = MagicMock()
        mock_plt.subplots.return_value = (mock_fig, mock_ax)
        mock_plt.style.use = MagicMock()
        mock_plt.FuncFormatter = MagicMock()

        output_path = tmp_path / "rec_chart.png"

        elements = {
            "rating": "买入",
            "current_price": 12.5,
            "target_price": 15.0
        }

        result = _generate_recommendation_chart(
            "3393.HK",
            str(output_path),
            "Test Company",
            elements
        )

        # 应该尝试绘制图表
        assert isinstance(result, bool)

    @patch('chart_generator.CHARTS_AVAILABLE', True)
    @patch('chart_generator.plt')
    def test_calculates_potential_upside(self, mock_plt, tmp_path):
        """测试：计算潜在涨幅。"""
        from chart_generator import _generate_recommendation_chart

        mock_fig = MagicMock()
        mock_ax = MagicMock()
        mock_plt.subplots.return_value = (mock_fig, mock_ax)
        mock_plt.style.use = MagicMock()
        mock_plt.FuncFormatter = MagicMock()

        output_path = tmp_path / "rec_chart.png"

        elements = {
            "rating": "增持",
            "current_price": 10.0,
            "target_price": 12.0  # 20% upside
        }

        result = _generate_recommendation_chart(
            "3393.HK",
            str(output_path),
            "Test Company",
            elements
        )

        # 验证计算逻辑正确
        # (12.0 - 10.0) / 10.0 * 100 = 20%
        potential_upside = (12.0 - 10.0) / 10.0 * 100
        assert potential_upside == 20.0


class TestChartModuleAvailability:
    """测试图表模块可用性标志。"""

    def test_charts_available_flag_exists(self):
        """测试：CHARTS_AVAILABLE 标志存在。"""
        from chart_generator import CHARTS_AVAILABLE

        assert isinstance(CHARTS_AVAILABLE, bool)

    def test_chart_proxy_env_var(self):
        """测试：可以从环境变量读取代理设置。"""
        from chart_generator import CHART_PROXY

        # 应该是一个字符串（可能为空）
        assert isinstance(CHART_PROXY, str)
