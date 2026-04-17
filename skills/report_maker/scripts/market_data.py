"""
market_data.py — 外部行情数据获取。

从 Neolyst 获取历史推荐数据，结合 yfinance 行情，转换为 recommendation chart 所需格式。
"""

import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


def fetch_recommendation_history(
    list_coverage_history_fn,
    ticker: str,
    first_analyst_email: str,
) -> list[dict]:
    """
    获取历史推荐数据，转换为 recommendation chart 所需的格式。

    调用 list_coverage_history 获取已发布历史报告，然后用 yfinance 获取
    每个发布日期对应的股票收盘价，输出 chart 需要的 recommendations 列表。

    Args:
        list_coverage_history_fn: neolyst coverage.list_coverage_history 函数引用
        ticker: 股票代码（如 3393.HK、VRT US）
        first_analyst_email: 报告 1作分析师邮箱

    Returns:
        list[dict]: 按 date asc 排序，每项格式：
            {"date": "2024-01-15", "rating": "OUTPERFORM", "price": 12.34, "target": 15.6}
            如果无历史数据或 yfinance 不可用，返回空列表。

    Note:
        - 不抛出异常，错误时仅 log warning 并返回空列表。
        - price 字段为该报告 published_at 当日（或最近交易日）的收盘价。
        - target 字段来自报告的 target_price。
    """
    try:
        history = list_coverage_history_fn(ticker, first_analyst_email)
    except Exception as exc:
        logger.warning("fetch_recommendation_history: list_coverage_history 失败: %s", exc)
        return []

    if not history:
        return []

    try:
        import yfinance as yf
    except ImportError:
        logger.warning("fetch_recommendation_history: yfinance 不可用")
        return []

    yf_ticker = ticker.replace(" ", "")
    if not ('.' in yf_ticker or '^' in yf_ticker):
        if yf_ticker.isdigit() and len(yf_ticker) == 4:
            yf_ticker = f"{yf_ticker}.HK"
        elif yf_ticker.endswith("US"):
            yf_ticker = yf_ticker[:-2]  # 去掉 US 后缀，yfinance 识别美股

    # 解析所有发布日期，确定最早日期
    parsed_rows = []
    for row in reversed(history):
        published_at = row.get("published_at")
        rating = row.get("rating")
        target_price = row.get("target_price")

        if not published_at or not rating:
            continue

        try:
            if isinstance(published_at, str):
                pub_dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
            else:
                pub_dt = published_at
            date_str = pub_dt.strftime("%Y-%m-%d")
        except Exception:
            continue

        pub_date_only = pub_dt.date() if hasattr(pub_dt, 'date') else pub_dt
        parsed_rows.append((date_str, pub_date_only, rating, target_price))

    if not parsed_rows:
        return []

    # 一次性下载整个日期范围的行情数据，避免 N+1 API 调用
    earliest = min(r[1] for r in parsed_rows)
    start_dt = datetime(earliest.year, earliest.month, earliest.day) - timedelta(days=7)
    end_dt = datetime.now() + timedelta(days=1)

    try:
        stock = yf.Ticker(yf_ticker)
        full_hist = stock.history(start=start_dt, end=end_dt)
    except Exception as exc:
        logger.warning("fetch_recommendation_history: 下载行情失败: %s", exc)
        return []

    if full_hist.empty:
        return []

    # 为每个发布日期查找最近的交易日的收盘价
    recommendations = []
    for date_str, pub_date_only, rating, target_price in parsed_rows:
        try:
            target_date = pub_date_only if hasattr(pub_date_only, 'year') else pub_date_only
            start = target_date - timedelta(days=3)
            end = target_date + timedelta(days=7)
            mask = (full_hist.index.date >= start) & (full_hist.index.date <= end)
            window = full_hist.loc[mask]
            if window.empty:
                continue
            price = float(window['Close'].iloc[0])
        except Exception as exc:
            logger.warning("fetch_recommendation_history: 获取 %s 价格失败: %s", date_str, exc)
            continue

        rec = {
            "date": date_str,
            "rating": rating,
            "price": round(price, 2),
        }
        if target_price is not None:
            rec["target"] = float(target_price)

        recommendations.append(rec)

    return recommendations
