"""
analyst.py — Neolyst analyst 查询模块。
"""

from supabase import Client


def resolve_analyst_by_email(client: Client, email: str) -> dict:
    """
    根据邮箱查询并返回标准化的 analyst 记录。

    业务主键为 analyst_email（表中强制小写存储）。
    is_active 校验在 Supabase RPC 侧执行。

    Args:
        client: 已认证的 Supabase client
        email: 分析师邮箱（大小写不敏感）

    Returns:
        dict: analyst 记录，含 email, english_name, chinese_name, suffix,
              sfc, region_code, is_active, created_at, updated_at 字段

    Raises:
        ValueError: 找不到对应的 analyst，或 analyst 已停用（is_active=False）
    """
    try:
        resp = client.rpc("resolve_analyst_by_email", {"p_email": email}).execute()
    except Exception as e:
        raise ValueError(str(e)) from e

    if not resp.data:
        raise ValueError(f"Analyst not found: {email!r}")

    return resp.data
