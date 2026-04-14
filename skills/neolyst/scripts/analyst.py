"""
analyst.py — Neolyst analyst 查询模块。

通过 Supabase 表查询获取 analyst 记录，校验逻辑在 Python 侧完成。
"""

from supabase import Client


def resolve_analyst_by_email(client: Client, email: str) -> dict:
    """
    根据邮箱查询并返回 analyst 记录。

    按 analyst 表主键 email 直接查询。is_active 校验在 Python 侧完成。

    Args:
        client: 已认证的 Supabase client
        email: 分析师邮箱（大小写不敏感）

    Returns:
        dict: analyst 记录，含 email, english_name, chinese_name, suffix,
              sfc, region_code, is_active, created_at, updated_at 字段

    Raises:
        ValueError: 找不到对应的 analyst，或 analyst 已停用（is_active=False）
    """
    email_lower = email.strip().lower()
    resp = client.table("analyst").select("*").eq("email", email_lower).execute()
    if not resp.data:
        raise ValueError(f"找不到分析师：{email}")
    record = resp.data[0]
    if not record.get("is_active", True):
        raise ValueError(f"分析师已停用：{email}")
    return record
