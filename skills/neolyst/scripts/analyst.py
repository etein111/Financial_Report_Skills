"""
analyst.py — Neolyst analyst 查询模块。
"""

from supabase import Client


def resolve_analyst_by_email(client: Client, email: str) -> dict:
    """
    根据邮箱查询并返回 analyst 记录。

    邮箱大小写不敏感，内部统一 lowercase/strip。
    is_active=False 的分析师抛出 ValueError。

    Args:
        client: 已认证的 Supabase client
        email: 分析师邮箱

    Returns:
        dict: analyst 记录全部字段

    Raises:
        ValueError: 找不到分析师，或分析师已停用
    """
    email_lower = email.strip().lower()
    resp = (
        client.table("analyst")
        .select("*")
        .eq("email", email_lower)
        .execute()
    )
    if not resp.data:
        raise ValueError(f"找不到分析师：{email}")
    record = resp.data[0]
    if not record.get("is_active", True):
        raise ValueError(f"分析师已停用：{email}")
    return record
