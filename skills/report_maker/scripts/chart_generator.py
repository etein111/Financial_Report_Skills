"""chart_generator.py - 图表生成模块

提供相对收益图表和推荐图表的生成功能。
"""

from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any

# 图表常量
DEFAULT_CHART_DPI = 100
CHART_LOOKBACK_DAYS = 365
BENCHMARK_TICKER = "^HSI"

# 评级颜色映射
RATING_COLORS = {
    '买入': '#2ecc71', '增持': '#27ae60', '推荐': '#2ecc71',
    '持有': '#f39c12', '中性': '#f39c12', '谨慎': '#e67e22',
    '卖出': '#e74c3c', '减持': '#c0392b', '回避': '#c0392b',
}
DEFAULT_RATING_COLOR = '#3498db'

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


def _generate_relative_chart(ticker: str, output_path: str, company_name: str = None) -> bool:
    """生成相对收益对比图（relative chart）。

    Args:
        ticker: 股票代码（如 3393.HK）
        output_path: 图表输出路径
        company_name: 公司名称（可选）

    Returns:
        是否成功生成
    """
    if not CHARTS_AVAILABLE:
        print(f"  ⚠️ 图表模块不可用，跳过 relative_chart 生成")
        return False

    try:
        # 计算日期范围（最近1年）
        end_date = datetime.now()
        start_date = end_date - timedelta(days=CHART_LOOKBACK_DAYS)

        # 并行下载股票和基准数据
        with ThreadPoolExecutor(max_workers=2) as executor:
            stock_future = executor.submit(yf.download, ticker, start_date, end_date, progress=False)
            benchmark_future = executor.submit(yf.download, BENCHMARK_TICKER, start_date, end_date, progress=False)
            stock_data = stock_future.result()
            benchmark_data = benchmark_future.result()

        if stock_data.empty or benchmark_data.empty:
            print(f"  ⚠️ 数据为空，跳过 relative_chart")
            return False

        # 提取收盘价
        def get_close(df):
            if 'Adj Close' in df.columns:
                return df['Adj Close']
            for col in df.columns:
                if 'Close' in str(col):
                    return df[col]
            raise ValueError(f"No Close column found: {df.columns.tolist()}")

        stock_close = get_close(stock_data)
        benchmark_close = get_close(benchmark_data)
        stock_return = (1 + stock_close.pct_change()).cumprod() - 1
        benchmark_return = (1 + benchmark_close.pct_change()).cumprod() - 1
        relative_return = (1 + stock_return) / (1 + benchmark_return) - 1

        # 绘图
        plt.style.use('seaborn-v0_8-whitegrid')
        fig, ax = plt.subplots(figsize=(10, 5.5), dpi=DEFAULT_CHART_DPI)

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
        plt.savefig(output_path, dpi=DEFAULT_CHART_DPI, bbox_inches='tight', facecolor='white')
        plt.close()

        return True

    except Exception as e:
        print(f"  ⚠️ 生成 relative_chart 时出错: {e}")
        return False


def _generate_recommendation_chart(ticker: str, output_path: str, company_name: str = None, elements: Dict[str, Any] = None, neolyst_client=None) -> bool:
    """生成推荐走势图（recommendation chart）。

    Args:
        ticker: 股票代码（如 3393.HK）
        output_path: 图表输出路径
        company_name: 公司名称（可选）
        elements: 要素字典（可选，用于获取 recommendations 数据及 a1_email）
        neolyst_client: 已认证的 Supabase client（可选，用于从 Neolyst 获取历史推荐）

    Returns:
        是否成功生成
    """
    if not CHARTS_AVAILABLE:
        print(f"  ⚠️ 图表模块不可用，跳过 recommendation_chart 生成")
        return False

    try:
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates
        import matplotlib.font_manager as fm

        # 计算日期范围（最近5年）
        end_date = datetime.now()
        start_date = datetime(end_date.year - 5, end_date.month, end_date.day)

        # 处理 ticker 格式
        if not ('.' in ticker or '^' in ticker):
            if ticker.isdigit() and len(ticker) == 4:
                ticker = f"{ticker}.HK"

        # 获取股票数据
        stock = yf.Ticker(ticker)
        hist = stock.history(start=start_date, end=end_date)

        if hist.empty:
            print(f"  ⚠️ 无法获取 {ticker} 的历史数据，跳过 recommendation_chart")
            return False

        stock_dates = hist.index
        stock_prices = hist['Close'].values

        # 从 elements 中获取 recommendations 数据
        recommendations = []
        if elements:
            recommendations = elements.get('recommendations', [])

        # 优先从 Neolyst 获取历史推荐数据
        neolyst_fetched = False
        if neolyst_client and elements:
            first_analyst_email = elements.get('a1_email', '')
            if first_analyst_email:
                try:
                    import importlib
                    _opencode_root = str(Path(__file__).resolve().parents[3])
                    if _opencode_root not in sys.path:
                        sys.path.insert(0, _opencode_root)
                    _cov_mod = importlib.import_module("skills.neolyst.scripts.coverage")
                    import market_data as _md
                    neolyst_recs = _md.fetch_recommendation_history(
                        lambda t, e: _cov_mod.list_coverage_history(neolyst_client, t, e),
                        ticker, first_analyst_email)
                    if neolyst_recs:
                        recommendations = neolyst_recs
                        neolyst_fetched = True
                        print(f"  ✅ 从 Neolyst 获取到 {len(recommendations)} 条历史推荐")
                    else:
                        # Neolyst 有 coverage 但没有历史推荐数据，这是有效情况，不报错
                        print(f"  ⚠️ Neolyst 中该股票没有历史推荐数据")
                except Exception as e:
                    print(f"  ⚠️ 从 Neolyst 获取推荐历史失败: {e}")
                    # 如果传入了 neolyst_client 但获取失败，必须报错，不使用默认数据
                    print(f"  ❌ recommendation_chart 生成失败：无法从 Neolyst 获取数据")
                    return False
        elif not recommendations:
            # 没有传入 neolyst_client，且 elements 中也没有 recommendations，才使用默认值（仅价格线）
            print(f"  ⚠️ 未传入 neolyst_client 且 elements 中无 recommendations，将生成仅含价格线的图表")

        # 如果没有 recommendations，生成仅含价格线的图表（不显示推荐点）
        if not recommendations:
            recommendations = []

        # 转换推荐日期为 datetime
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

        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else "reports", exist_ok=True)

        # 图片尺寸：18cm x 11cm (1cm = 0.3937 inches)
        fig_width = 18 * 0.3937  # ~7.09 inches
        fig_height = 11 * 0.3937  # ~4.33 inches

        # 创建图表
        fig = plt.figure(figsize=(fig_width, fig_height))
        fig.patch.set_facecolor('white')

        # 上方面板：价格走势 + 目标价 (占上方约75%高度)
        # [left, bottom, width, height]
        ax1 = fig.add_axes([0.08, 0.28, 0.88, 0.65])
        ax1.set_facecolor('white')

        # 绘制价格曲线
        ax1.plot(stock_dates, stock_prices, color='#23558C', linewidth=2, label='Price')

        # 绘制目标价水平线段
        for i, rec in enumerate(recs):
            rec_idx = None
            for j, d in enumerate(stock_dates):
                d_compare = d.replace(tzinfo=None) if hasattr(d, 'tzinfo') and d.tzinfo is not None else d
                if d_compare >= rec['date']:
                    rec_idx = j
                    break

            if rec_idx is not None:
                if i < len(recs) - 1:
                    end_date_rec = recs[i + 1]['date']
                else:
                    end_date_rec = stock_dates[-1] if hasattr(stock_dates[-1], 'replace') else stock_dates[-1]

                ax1.hlines(y=rec['target'], xmin=stock_dates[rec_idx], xmax=end_date_rec,
                           color='#808080', linewidth=3, linestyle='-', alpha=0.9)
                ax1.axvline(x=stock_dates[rec_idx], color='#808080', linewidth=2,
                           linestyle='-', alpha=0.7)
                ax1.text(stock_dates[rec_idx], ax1.get_ylim()[1] * 0.98, f"{rec['seq']}",
                        fontsize=12, fontweight='bold', color='#23558C',
                        ha='center', va='top')

        # Y轴设置
        all_prices = list(stock_prices) + [rec['price'] for rec in recs] + [rec['target'] for rec in recs]
        price_min = min(all_prices)
        price_max = max(all_prices)
        ax1.set_ylim(price_min * 0.9, price_max * 1.1)

        ax1.yaxis.grid(True, linestyle='--', alpha=0.5, color='lightgray')
        ax1.set_axisbelow(True)
        ax1.spines['top'].set_visible(False)
        ax1.spines['right'].set_visible(False)

        ticker_display = ticker.replace('.HK', ' HK').replace('.', ' ')
        ax1.set_title(f'{company_name or ticker} - {ticker_display}', fontsize=20, fontweight='bold', pad=20)

        # 横坐标设置：根据数据长度自动调整间隔，避免重叠
        num_ticks = 6  # 横坐标刻度数量
        tick_interval = max(1, len(stock_dates) // (num_ticks * 30))  # 每月约30个交易日
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%b-%Y'))
        ax1.xaxis.set_major_locator(mdates.MonthLocator(interval=tick_interval))
        plt.setp(ax1.xaxis.get_majorticklabels(), rotation=0, ha='center', fontsize=9)

        if len(stock_dates) > 0:
            ax1.set_xlim(stock_dates[0], stock_dates[-1])

        # 下方面板：推荐信息文本 (与 ax1 左端对齐，left=0.08, width=0.88)
        ax2 = fig.add_axes([0.08, 0.05, 0.88, 0.18])
        ax2.axis('off')

        # 构建推荐信息文本，每段格式：1. 24 Aug 2020 OUTPERFORM 11.16 target 14.60
        # 各字段之间用一个英文空格分隔
        calibri_prop = fm.FontProperties(family='Calibri')
        y_positions = [0.75, 0.45, 0.15]  # 三个推荐的位置

        for i, rec in enumerate(recs):
            if i >= 3:
                break
            date_str = rec['date'].strftime('%d %b %Y')
            price_str = f"{rec['price']:.2f}"
            target_str = f"{rec['target']:.2f}"

            # 格式：序号 日期 Rating 价格 target 目标价
            rec_text = f"{i+1}. {date_str} {rec['rating']} {price_str} target {target_str}"
            ax2.text(0.01, y_positions[i], rec_text,
                    fontproperties=calibri_prop, fontsize=10, color='#212121',
                    va='center', ha='left')

        plt.savefig(output_path, dpi=DEFAULT_CHART_DPI, bbox_inches='tight', facecolor='white')
        plt.close()

        print(f"  ✅ recommendation_chart 已生成: {output_path}")
        return True

    except Exception as e:
        print(f"  ⚠️ 生成 recommendation_chart 时出错: {e}")
        return False
