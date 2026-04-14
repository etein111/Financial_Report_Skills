"""
coverage.py — Neolyst coverage 解析与创建接口。

业务逻辑全部在 Supabase RPC 侧实现，本模块只做参数整理和调用。
"""

import logging
from datetime import datetime

from supabase import Client

from . import rpc

logger = logging.getLogger(__name__)


def resolve_coverage(client: Client, ticker: str, first_analyst_email: str) -> str:
    """
    按 ticker + 1作分析师邮箱查询唯一 coverage，返回 coverage_id。

    Args:
        client: 已认证的 Supabase client
        ticker: 股票代码（大小写不敏感）
        first_analyst_email: 报告 1作分析师邮箱（大小写不敏感）

    Returns:
        str: coverage_id（uuid 字符串）

    Raises:
        ValueError: 未命中、命中多条（无法自动确定）、数据异常
    """
    row = rpc.single_row(rpc.call_rpc(client, "resolve_coverage", {
        "p_ticker": ticker,
        "p_analyst_email": first_analyst_email,
    }))
    return str(row["coverage_id"])


def create_coverage(
    client: Client,
    ticker: str,
    english_name: str,
    sector_id: str,
    isin: str,
    country_of_domicile: str,
    analysts: list[dict],
    chinese_name: str | None = None,
    traditional_chinese: str | None = None,
) -> str:
    """
    创建 coverage 及初始 coverage_analyst 关系，返回新 coverage_id。
    仅在 resolve_coverage 未命中且用户确认"Coverage 已完成审批"后调用。

    Args:
        client: 已认证的 Supabase client
        ticker: 股票代码
        english_name: 公司英文名
        sector_id: 所属行业 UUID（字符串）
        isin: ISIN 码
        country_of_domicile: 注册国家/地区
        analysts: 分析师列表，格式：[{"analyst_email": "...", "author_order": 1}, ...]
                  author_order=1 代表报告 1作分析师
        chinese_name: 公司中文名（可选）
        traditional_chinese: 公司繁体中文名（可选）

    Returns:
        str: 新建 coverage 的 coverage_id（uuid 字符串）

    Raises:
        ValueError: ticker 或 isin 已存在等创建失败场景
    """
    row = rpc.single_row(rpc.call_rpc(client, "create_coverage", {
        "p_ticker": ticker,
        "p_english_name": english_name,
        "p_sector_id": sector_id,
        "p_isin": isin,
        "p_country_of_domicile": country_of_domicile,
        "p_analysts": analysts,
        "p_chinese_name": chinese_name,
        "p_traditional_chinese": traditional_chinese,
    }))
    return str(row["coverage_id"])


def list_coverage_history(
    client: Client,
    ticker: str,
    first_analyst_email: str,
) -> list[dict]:
    """
    按 ticker + 1作分析师邮箱查询 coverage 的已发布历史报告。

    Returns:
        list[dict]: 每项含 report_id/title/rating/target_price/published_at，
                    按 published_at desc 排序。coverage 存在但无历史时返回空列表。

    Raises:
        ValueError: coverage 未找到
    """
    resp = rpc.call_rpc(client, "list_coverage_history", {
        "p_ticker": ticker,
        "p_analyst_email": first_analyst_email,
    })
    return [
        {
            "report_id": str(row["report_id"]),
            "title": row["title"],
            "rating": row["rating"],
            "target_price": row["target_price"],
            "published_at": row["published_at"],
        }
        for row in (resp.data or [])
    ]


def fetch_recommendation_history(
    client: Client,
    ticker: str,
    first_analyst_email: str,
) -> list[dict]:
    """
    从 Neolyst 获取历史推荐数据，转换为 recommendation chart 所需的格式。

    调用 list_coverage_history 获取已发布历史报告，然后用 yfinance 获取
    每个发布日期对应的股票收盘价，输出 chart 需要的 recommendations 列表。

    Args:
        client: 已认证的 Supabase client
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
        history = list_coverage_history(client, ticker, first_analyst_email)
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
            from datetime import timedelta
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
