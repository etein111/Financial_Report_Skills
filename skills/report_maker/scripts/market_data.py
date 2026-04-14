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

    yf_ticker = ticker
    if not ('.' in ticker or '^' in ticker):
        if ticker.isdigit() and len(ticker) == 4:
            yf_ticker = f"{ticker}.HK"

    try:
        stock = yf.Ticker(yf_ticker)
    except Exception as exc:
        logger.warning("fetch_recommendation_history: yf.Ticker 失败: %s", exc)
        return []

    recommendations = []
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

        try:
            pub_date_only = pub_dt.date() if hasattr(pub_dt, 'date') else pub_dt
            start_dt = datetime(pub_date_only.year, pub_date_only.month, pub_date_only.day)
            end_dt = start_dt + timedelta(days=7)
            hist = stock.history(start=start_dt, end=end_dt)
            if hist.empty:
                continue
            price = float(hist['Close'].iloc[0])
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
