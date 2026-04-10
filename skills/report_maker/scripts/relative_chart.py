"""
金融对比图表生成脚本
上下双面板：上方面板为相对收益对比，下方面板为成交量
数据来源：yfinance
"""

import yfinance as yf
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import os
from datetime import datetime

proxy = "http://127.0.0.1:7890"
os.environ["HTTP_PROXY"] = proxy
os.environ["HTTPS_PROXY"] = proxy


def get_stock_data(ticker: str, start_date: datetime, end_date: datetime) -> tuple:
    """获取股票数据"""
    if not ('.' in ticker or '^' in ticker):
        if ticker.isdigit() and len(ticker) == 4:
            ticker = f"{ticker}.HK"

    stock = yf.Ticker(ticker)
    hist = stock.history(start=start_date, end=end_date)

    if hist.empty:
        raise ValueError(f"无法获取 {ticker} 的历史数据")

    dates = hist.index
    prices = hist['Close'].values
    volumes = hist['Volume'].values if 'Volume' in hist.columns else None

    return dates, prices, volumes


def get_msci_china_data(start_date: datetime, end_date: datetime) -> tuple:
    """获取MSCI China指数数据"""
    try:
        mchi = yf.Ticker("MCHI")
        hist = mchi.history(start=start_date, end=end_date)
        if not hist.empty:
            return hist.index, hist['Close'].values
    except:
        pass

    try:
        mchi = yf.Ticker("2800.HK")
        hist = mchi.history(start=start_date, end=end_date)
        if not hist.empty:
            return hist.index, hist['Close'].values
    except:
        pass

    raise ValueError("无法获取MSCI China数据")


def normalize_to_100(data: np.ndarray) -> np.ndarray:
    """将数据归一化到起始点为100"""
    return (data / data[0]) * 100


def plot_relative_return_chart(
    price_return_data: list,
    msci_data: list,
    volume_data: list,
    dates: list,
    output_path: str = None
):
    """
    绘制相对收益对比图

    Args:
        price_return_data: Price Return 数据 (从100开始)
        msci_data: MSCI China 数据 (从100开始)
        volume_data: 成交量数据
        dates: 日期列表
        output_path: 输出路径
    """
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), dpi=100,
                                    gridspec_kw={'height_ratios': [3, 1]},
                                    sharex=True)

    fig.patch.set_facecolor('white')
    ax1.set_facecolor('#fafafa')
    ax2.set_facecolor('#fafafa')

    # ========== 上方面板：相对收益对比 ==========
    ax1.plot(dates, price_return_data, color='#23558C', linewidth=2, label='Price Return')
    ax1.plot(dates, msci_data, color='#808080', linewidth=2, label='MSCI China')

    # Y轴设置 - 根据数据范围动态调整
    data_min = min(min(price_return_data), min(msci_data))
    data_max = max(max(price_return_data), max(msci_data))
    y_margin = (data_max - data_min) * 0.1
    y_min = max(0, data_min - y_margin)
    y_max = data_max + y_margin
    ax1.set_ylim(y_min, y_max)

    # 自动设置Y轴刻度
    y_range = y_max - y_min
    if y_range <= 20:
        y_step = 5
    elif y_range <= 50:
        y_step = 10
    elif y_range <= 100:
        y_step = 20
    else:
        y_step = 50

    y_ticks = []
    current = int(y_min // y_step) * y_step
    while current <= y_max:
        if current >= y_min:
            y_ticks.append(current)
        current += y_step
    ax1.set_yticks(y_ticks)

    # 水平网格线
    ax1.yaxis.grid(True, linestyle='--', alpha=0.6, color='lightgray')
    ax1.set_axisbelow(True)

    # 去掉边框
    ax1.spines['top'].set_visible(False)
    ax1.spines['right'].set_visible(False)

    # 图例 - 横向分布在图表正上方
    ax1.legend(loc='upper center', bbox_to_anchor=(0.5, 1.02), ncol=2, fontsize=10, framealpha=0.9)

    # Y轴标签（去掉）

    # ========== 下方面板：成交量 ==========
    # 找出 Jul-25 的位置
    jul25_idx = None
    for i, d in enumerate(dates):
        d_compare = d.replace(tzinfo=None) if hasattr(d, 'tzinfo') and d.tzinfo is not None else d
        if d_compare.year == 2025 and d_compare.month == 7:
            jul25_idx = i
            break

    # 绘制成交量柱状图（蓝色）
    bar_colors = ['#23558C' if i == jul25_idx else '#B8D4E8' for i in range(len(volume_data))]
    bar_width = 0.8

    ax2.bar(dates, volume_data, width=bar_width, color=bar_colors, align='center')

    # Jul-25 垂直细线
    if jul25_idx is not None:
        ax2.axvline(x=dates[jul25_idx], color='#23558C', linewidth=2, alpha=0.8)

    # Y轴设置
    ax2.set_ylim(0, max(volume_data) * 1.2)
    ax2.yaxis.grid(True, linestyle='--', alpha=0.6, color='lightgray')
    ax2.set_axisbelow(True)

    # 去掉边框
    ax2.spines['top'].set_visible(False)
    ax2.spines['right'].set_visible(False)

    # Y轴标签
    ax2.set_ylabel('Volume', fontsize=11)

    # Y轴只显示刻度不显示数字
    ax2.set_yticklabels([])

    # ========== X轴设置 ==========
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%b-%y'))
    ax2.xaxis.set_major_locator(mdates.MonthLocator(interval=1))

    # 设置X轴范围
    ax2.set_xlim(dates[0], dates[-1])

    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
        print(f"图表已保存至: {output_path}")

    plt.show()


def main():
    """主函数"""
    ticker = "2507.HK"
    ticker_name = "Cirrus Aircraft"
    start_date = datetime(2024, 12, 1)
    end_date = datetime(2025, 11, 30)

    # 先获取股票上市日期
    stock = yf.Ticker(ticker)
    ipo_date = None
    try:
        info = stock.info
        if 'earliestTradeDate' in info:
            ipo_date = datetime.fromtimestamp(info['earliestTradeDate'])
        elif 'firstTradeDate' in info:
            ipo_date = datetime.fromtimestamp(info['firstTradeDate'])
    except:
        pass

    # 如果IPO日期晚于start_date，则从IPO日期开始获取数据
    if ipo_date and ipo_date > start_date:
        data_start = ipo_date
    else:
        data_start = start_date

    # 获取股票数据（从实际开始交易日期）
    stock_dates, stock_prices, volumes = get_stock_data(ticker, data_start, end_date)

    # 获取MSCI China数据（仍从原始start_date开始）
    index_dates, index_prices = get_msci_china_data(start_date, end_date)

    # 对齐两个数据集的日期
    common_dates = stock_dates
    stock_normalized = normalize_to_100(stock_prices)

    # 将MSCI数据插值到股票日期
    index_normalized = np.interp(
        mdates.date2num(common_dates),
        mdates.date2num(index_dates),
        normalize_to_100(index_prices)
    )

    plot_relative_return_chart(
        price_return_data=stock_normalized,
        msci_data=index_normalized,
        volume_data=volumes,
        dates=common_dates,
        output_path="reports/relative_return_chart.png"
    )


if __name__ == "__main__":
    import sys
    import os

    if len(sys.argv) >= 4:
        # 从命令行参数获取
        ticker = sys.argv[1]
        ticker_name = sys.argv[2]
        output_path = sys.argv[3]
    else:
        # 默认示例
        ticker = "2507.HK"
        ticker_name = "Cirrus Aircraft"
        output_path = "reports/relative_return_chart.png"

    # 确保输出目录存在
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else "reports", exist_ok=True)

    # 计算日期范围（最近1年）
    end_date = datetime.now()
    start_date = datetime(end_date.year - 1, end_date.month, end_date.day)

    # 先获取股票上市日期
    stock = yf.Ticker(ticker)
    ipo_date = None
    try:
        info = stock.info
        if 'earliestTradeDate' in info:
            ipo_date = datetime.fromtimestamp(info['earliestTradeDate'])
        elif 'firstTradeDate' in info:
            ipo_date = datetime.fromtimestamp(info['firstTradeDate'])
    except:
        pass

    # 如果IPO日期晚于start_date，则从IPO日期开始获取数据
    if ipo_date and ipo_date > start_date:
        data_start = ipo_date
    else:
        data_start = start_date

    # 获取股票数据（从实际开始交易日期）
    stock_dates, stock_prices, volumes = get_stock_data(ticker, data_start, end_date)

    # 获取MSCI China数据（仍从原始start_date开始）
    index_dates, index_prices = get_msci_china_data(start_date, end_date)

    # 对齐两个数据集的日期
    common_dates = stock_dates
    stock_normalized = normalize_to_100(stock_prices)

    # 将MSCI数据插值到股票日期
    index_normalized = np.interp(
        mdates.date2num(common_dates),
        mdates.date2num(index_dates),
        normalize_to_100(index_prices)
    )

    plot_relative_return_chart(
        price_return_data=stock_normalized,
        msci_data=index_normalized,
        volume_data=volumes,
        dates=common_dates,
        output_path=output_path
    )
