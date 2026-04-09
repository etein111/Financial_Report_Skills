"""
analyst.py — Neolyst analyst 查询模块。
"""

from supabase import Client


def resolve_analyst_by_email(client: Client, email: str) -> dict:
    """
    根据邮箱查询并返回标准化的 analyst 记录。

    业务主键为 analyst_email（表中强制小写存储）。

    Args:
        client: 已认证的 Supabase client
        email: 分析师邮箱（大小写不敏感）

    Returns:
        dict: analyst 记录，含 email, english_name, chinese_name, suffix,
              sfc, region_code, is_active, created_at, updated_at 字段

    Raises:
        ValueError: 找不到对应的 analyst，或 analyst 已停用（is_active=False）
    """
    normalized = email.strip().lower()
    resp = client.table("analyst").select("*").eq("email", normalized).execute()

    if not resp.data:
        raise ValueError(f"Analyst not found: {email!r}")

    record = resp.data[0]
    if not record.get("is_active", True):
        raise ValueError(f"Analyst is inactive: {email!r}")

    return record
