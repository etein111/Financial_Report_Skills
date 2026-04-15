"""chart_generator.py - 图表生成模块

提供相对收益图表和推荐图表的生成功能。
"""

import os
from typing import Dict, Any, Optional
from pathlib import Path

# 尝试导入图表依赖
try:
    import yfinance as yf
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    import numpy as np
    from datetime import datetime, timedelta
    CHARTS_AVAILABLE = True
except ImportError as e:
    CHARTS_AVAILABLE = False
    yf = None
    plt = None
    mdates = None
    np = None
    datetime = None

# 图表代理设置
CHART_PROXY = os.environ.get("HTTP_PROXY") or os.environ.get("HTTPS_PROXY") or ""


def _generate_relative_chart(ticker: str, output_path: str, company_name: str = None) -> bool:
    """生成相对表现图表。

    比较股票相对恒生指数的表现。

    Args:
        ticker: 股票代码
        output_path: 输出图片路径
        company_name: 公司名称（用于图表标题）

    Returns:
        是否成功生成
    """
    if not CHARTS_AVAILABLE:
        print(f"  ⚠️ 图表模块不可用，跳过相对收益图表")
        return False

    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)

        # 尝试获取数据
        try:
            stock_data = yf.download(ticker, start=start_date, end=end_date, proxy=CHART_PROXY or None, progress=False)
            benchmark_data = yf.download("^HSI", start=start_date, end=end_date, proxy=CHART_PROXY or None, progress=False)
        except Exception as e:
            print(f"  [yfinance] 下载数据失败: {e}")
            return False

        if stock_data.empty or benchmark_data.empty:
            print(f"  ⚠️ 数据为空，跳过相对收益图表")
            return False

        # 计算相对收益
        stock_return = (1 + stock_data['Adj Close'].pct_change()).cumprod() - 1
        benchmark_return = (1 + benchmark_data['Adj Close'].pct_change()).cumprod() - 1
        relative_return = (1 + stock_return) / (1 + benchmark_return) - 1

        # 绘图
        plt.style.use('seaborn-v0_8-whitegrid')
        fig, ax = plt.subplots(figsize=(10, 5.5), dpi=100)

        dates = mdates.date2num(relative_return.index.to_pydatetime())
        ax.plot_date(dates, relative_return.values * 100, '-', linewidth=2, color='#1f77b4')

        ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x:.0f}%'))

        title = f'{company_name or ticker} Relative Return vs HSI (1Y)'
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.set_ylabel('Relative Return (%)', fontsize=11)
        ax.set_xlabel('')
        ax.yaxis.grid(True, linestyle='--', alpha=0.7)
        ax.xaxis.grid(True, linestyle='--', alpha=0.7)

        plt.tight_layout()
        plt.savefig(output_path, dpi=100, bbox_inches='tight', facecolor='white')
        plt.close()

        return True

    except Exception as e:
        print(f"  生成相对收益图表失败: {e}")
        if plt:
            plt.close()
        return False


def _generate_recommendation_chart(
    ticker: str,
    output_path: str,
    company_name: str = None,
    elements: Dict[str, Any] = None,
    neolyst_client=None
) -> bool:
    """生成评级推荐图表。

    基于要素中的评级、目标价等信息生成视觉化推荐图表。

    Args:
        ticker: 股票代码
        output_path: 输出图片路径
        company_name: 公司名称
        elements: 要素字典（包含 rating, target_price, current_price 等）
        neolyst_client: neolyst 客户端（用于获取数据）

    Returns:
        是否成功生成
    """
    if not CHARTS_AVAILABLE:
        print(f"  ⚠️ 图表模块不可用，跳过推荐图表")
        return False

    if not elements:
        elements = {}

    try:
        current_price = elements.get('current_price')
        target_price = elements.get('target_price')
        rating = elements.get('rating', '')

        # 尝试从 yfinance 获取当前价格
        if not current_price and ticker:
            try:
                stock = yf.Ticker(ticker)
                info = stock.info
                current_price = info.get('currentPrice') or info.get('previousClose')
            except Exception:
                pass

        # 如果有当前价格和目标价格，计算潜在涨幅
        potential_upside = None
        if current_price and target_price:
            try:
                potential_upside = (float(target_price) - float(current_price)) / float(current_price) * 100
            except Exception:
                pass

        # 绘图
        fig, ax = plt.subplots(figsize=(12, 6), dpi=100)

        # 根据评级设置颜色
        rating_colors = {
            '买入': '#2ecc71', '增持': '#27ae60', '推荐': '#2ecc71',
            '持有': '#f39c12', '中性': '#f39c12', '谨慎': '#e67e22',
            '卖出': '#e74c3c', '减持': '#c0392b', '回避': '#c0392b',
        }
        color = rating_colors.get(rating, '#3498db') if rating else '#3498db'

        # 绘制背景条
        ax.barh([0], [100], color='#ecf0f1', height=0.5)
        ax.barh([0], [50], color='#bdc3c7', height=0.5)

        # 绘制当前价格位置
        if current_price and target_price:
            try:
                cp = float(current_price)
                tp = float(target_price)
                if cp > 0:
                    # 计算当前价格相对目标价格的位置（0-100%）
                    # 假设最大涨幅为 100%
                    max_upside = 1.0  # 100%
                    position = min(cp / tp, max_upside) * 100
                    ax.axvline(x=position, color=color, linewidth=3, label=f'Current: {cp:.2f}')

                    # 绘制目标价格标记
                    ax.axvline(x=100, color='#2ecc71', linewidth=2, linestyle='--', label=f'Target: {tp:.2f}')
            except Exception:
                pass

        # 设置图表样式
        ax.set_xlim(0, 100)
        ax.set_ylim(-0.5, 0.5)
        ax.set_yticks([])
        ax.set_xticks([0, 25, 50, 75, 100])
        ax.set_xticklabels(['0%', '25%', '50%', '75%', '100%'])
        ax.set_xlabel('Price Level (%)', fontsize=11)

        # 标题
        title = f'{company_name or ticker} - Price Target'
        if rating:
            title += f' | {rating}'
        if potential_upside is not None:
            title += f' | {potential_upside:+.1f}% upside'
        ax.set_title(title, fontsize=14, fontweight='bold')

        # 添加评级标签
        if rating:
            ax.text(0.02, 0.5, rating, transform=ax.transAxes,
                   fontsize=20, fontweight='bold', color=color,
                   verticalalignment='center')

        ax.legend(loc='upper right')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_visible(False)

        plt.tight_layout()
        plt.savefig(output_path, dpi=100, bbox_inches='tight', facecolor='white')
        plt.close()

        return True

    except Exception as e:
        print(f"  生成推荐图表失败: {e}")
        if plt:
            plt.close()
        return False
