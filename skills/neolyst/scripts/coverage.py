"""
coverage.py — Neolyst coverage 解析与创建接口。

业务逻辑全部在 Supabase RPC 侧实现，本模块只做参数整理和调用。
"""

from supabase import Client

from . import rpc


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
        ValueError: 未命中（提示创建 Coverage）或数据异常
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
