"""
金融推荐走势图
- 主曲线：股票收盘价走势
- 目标价：阶梯图/水平线段
- 标注点：推荐序号
"""

import yfinance as yf
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.font_manager as fm
import numpy as np
import os
from datetime import datetime
from typing import List, Dict

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

    return dates, prices, stock


def plot_recommendation_chart(
    ticker: str,
    ticker_name: str,
    start_date: datetime,
    end_date: datetime,
    recommendations: List[Dict],
    output_path: str = None
):
    """
    绘制金融推荐走势图

    Args:
        ticker: 股票代码
        ticker_name: 股票名称
        start_date: 开始日期
        end_date: 结束日期
        recommendations: 推荐历史列表
            例如: [{"date": "2020-08-24", "rating": "OUTPERFORM", "price": 11.16, "target": 14.6}, ...]
        output_path: 输出路径
    """
    # 获取股票数据
    stock = yf.Ticker(ticker)
    hist = stock.history(start=start_date, end=end_date)

    dates = hist.index
    prices = hist['Close'].values

    # 转换推荐日期为datetime
    recs = []
    for i, rec in enumerate(recommendations):
        rec_date = datetime.strptime(rec['date'], '%Y-%m-%d')
        recs.append({
            'seq': i + 1,
            'date': rec_date,
            'rating': rec['rating'],
            'price': rec['price'],
            'target': rec['target']
        })

    # 创建图表（留出更多空间给下方的推荐信息）
    # 尺寸：高10.58cm，宽17.64cm (1cm=0.3937in)
    fig = plt.figure(figsize=(6.94, 4.17), dpi=150)
    fig.patch.set_facecolor('white')

    # 主面板：价格走势 + 目标价
    ax1 = fig.add_axes([0.08, 0.30, 0.85, 0.60])
    ax1.set_facecolor('white')

    # 绘制价格曲线
    ax1.plot(dates, prices, color='#23558C', linewidth=2, label='Price')

    # 绘制目标价水平线段
    for i, rec in enumerate(recs):
        # 找到推荐日期在数据中的位置
        rec_idx = None
        for j, d in enumerate(dates):
            d_compare = d.replace(tzinfo=None) if hasattr(d, 'tzinfo') and d.tzinfo is not None else d
            if d_compare >= rec['date']:
                rec_idx = j
                break

        if rec_idx is not None:
            # 确定线段的结束日期（下一个推荐日期或数据末尾）
            if i < len(recs) - 1:
                end_date_rec = recs[i + 1]['date']
            else:
                end_date_rec = dates[-1] if hasattr(dates[-1], 'replace') else dates[-1]

            # 绘制目标价水平线（从目标价纵坐标延伸）
            ax1.hlines(y=rec['target'], xmin=dates[rec_idx], xmax=end_date_rec,
                       color='#808080', linewidth=3, linestyle='-', alpha=0.9)

            # 在推荐日期绘制垂直辅助线（灰色实线）
            ax1.axvline(x=dates[rec_idx], color='#808080', linewidth=2,
                       linestyle='-', alpha=0.7)

            # 标注序号（蓝色，纯数字，无方框）
            ax1.text(dates[rec_idx], ax1.get_ylim()[1] * 0.98, f"{rec['seq']}",
                    fontsize=12, fontweight='bold', color='#23558C',
                    ha='center', va='top')

    # Y轴设置 - 根据价格和目标价范围动态调整
    all_prices = list(prices) + [rec['price'] for rec in recs] + [rec['target'] for rec in recs]
    price_min = min(all_prices)
    price_max = max(all_prices)
    y_margin = (price_max - price_min) * 0.15
    ax1.set_ylim(price_min * 0.9, price_max * 1.1)

    # 网格线
    ax1.yaxis.grid(True, linestyle='--', alpha=0.5, color='lightgray')
    ax1.set_axisbelow(True)

    # 去掉边框
    ax1.spines['top'].set_visible(False)
    ax1.spines['right'].set_visible(False)

    # 标题
    ax1.set_title(f'{ticker_name} - {ticker}', fontsize=20, fontweight='bold', pad=20)

    # Y轴标签（去掉）

    # X轴设置 - 每隔4个月标注一个，格式为 Jun-2020（横向显示）
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%b-%Y'))
    ax1.xaxis.set_major_locator(mdates.MonthLocator(interval=4))

    if len(dates) > 0:
        ax1.set_xlim(dates[0], dates[-1])

    # ========== 下方面板：推荐信息文本 ==========
    ax2 = fig.add_axes([0.08, 0.05, 0.85, 0.18])
    ax2.axis('off')

    # 格式化推荐信息文本，分段固定间距渲染
    calibri_prop = fm.FontProperties(family='Calibri')
    for i, rec in enumerate(recs):
        date_str = rec['date'].strftime('%d %b %Y')
        price_str = f"{rec['price']:.2f}"
        target_str = f"{rec['target']:.2f}"
        y_pos = 0.85 - i * 0.35

        # 各部分固定 x 位置（一个英文空格距离）
        x_seq = 0.02
        x_date = 0.06
        x_rating = 0.13
        x_price = 0.21
        x_target = 0.25

        # 渲染各部分
        ax2.text(x_seq, y_pos, f"{rec['seq']}.",
                 fontproperties=calibri_prop, fontsize=11, color='#212121', va='center')
        ax2.text(x_date, y_pos, date_str,
                 fontproperties=calibri_prop, fontsize=11, color='#212121', va='center')
        ax2.text(x_rating, y_pos, rec['rating'],
                 fontproperties=calibri_prop, fontsize=11, color='#212121', va='center')
        ax2.text(x_price, y_pos, price_str,
                 fontproperties=calibri_prop, fontsize=11, color='#212121', va='center')
        ax2.text(x_target, y_pos, "target " + target_str,
                 fontproperties=calibri_prop, fontsize=11, color='#212121', va='center')

    if output_path:
        plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
        print(f"图表已保存至: {output_path}")

    plt.show()


if __name__ == "__main__":
    import sys
    import json
    import os

    if len(sys.argv) >= 3:
        ticker = sys.argv[1]
        ticker_name = sys.argv[2]
        recommendations = json.loads(sys.argv[3]) if len(sys.argv) > 3 else []
        output_path = sys.argv[4] if len(sys.argv) > 4 else "reports/recommendation_chart.png"
        # 动态计算日期范围：最近5年
        end_date = datetime.now()
        start_date = datetime(end_date.year - 5, end_date.month, end_date.day)
    else:
        # 默认示例
        ticker = "0700.HK"  # 腾讯
        ticker_name = "Tencent"
        end_date = datetime.now()
        start_date = datetime(end_date.year - 5, end_date.month, end_date.day)
        output_path = "reports/recommendation_chart.png"

        # 推荐历史
        recommendations = [
            {"date": "2020-08-24", "rating": "OUTPERFORM", "price": 491.16, "target": 484.6},
            {"date": "2021-03-03", "rating": "OUTPERFORM", "price": 361.14, "target": 360.2},
            {"date": "2023-04-26", "rating": "OUTPERFORM", "price": 321.69, "target": 320.8},
        ]

    # 确保输出目录存在
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else "reports", exist_ok=True)

    plot_recommendation_chart(
        ticker=ticker,
        ticker_name=ticker_name,
        start_date=start_date,
        end_date=end_date,
        recommendations=recommendations,
        output_path=output_path
    )
