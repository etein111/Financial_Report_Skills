"""
analyst.py — Neolyst analyst 查询与管理模块。

接口：
1. resolve_analyst_by_email — 按邮箱精确查询一人（直接查表）
2. search_analyst_by_name — 按姓名模糊查询活跃分析师
3. upsert_analyst — 以 email 为键创建或更新分析师（需 admin）
4. set_analyst_active — 更新分析师在职状态（需 admin）
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


def search_analyst_by_name(client: Client, name: str) -> list[dict]:
    """
    按姓名模糊查询活跃分析师，返回精简字段。

    同时匹配 english_name 和 chinese_name（ilike 模糊匹配）。
    只返回 is_active=True 的分析师。
    返回字段：email、english_name、chinese_name。
    name 中的 % 和 _ 在 Python 侧 escape，防止通配符注入。
    无匹配时返回空列表。

    Args:
        client: 已认证的 Supabase client
        name: 待匹配的姓名（部分即可）

    Returns:
        list[dict]: 匹配的分析师列表，每条含 email, english_name, chinese_name
    """
    escaped = name.replace("%", "\\%").replace("_", "\\_")
    resp = (
        client.table("analyst")
        .select("email,english_name,chinese_name")
        .or_(f"english_name.ilike.%{escaped}%,chinese_name.ilike.%{escaped}%")
        .eq("is_active", True)
        .execute()
    )
    return resp.data if resp.data else []


def upsert_analyst(
    client: Client,
    email: str,
    english_name: str,
    chinese_name: str | None = None,
    suffix: str | None = None,
    sfc: str | None = None,
    region_code: str | None = None,
    is_active: bool = True,
) -> dict:
    """
    以 email 为键创建或更新分析师。

    email 在 Python 侧做 strip().lower()，与 DB CHECK 约束一致。
    返回 upsert 后的完整记录。DB 触发器 trg_analyst_updated_at 自动维护 updated_at。

    Args:
        client: 已认证的 Supabase client（需 admin 角色）
        email: 分析师邮箱
        english_name: 英文姓名
        chinese_name: 中文姓名
        suffix: 姓名后缀/头衔
        sfc: 证券期货从业资格编号
        region_code: 所属区域编码
        is_active: 是否在职

    Returns:
        dict: upsert 后的完整记录

    Raises:
        ValueError: RPC 返回错误（如 RLS 权限不足）
    """
    email_lower = email.strip().lower()
    record = {
        "email": email_lower,
        "english_name": english_name,
        "chinese_name": chinese_name,
        "suffix": suffix,
        "sfc": sfc,
        "region_code": region_code,
        "is_active": is_active,
    }
    resp = client.table("analyst").upsert(record, on_conflict="email").execute()
    if not resp.data:
        raise ValueError(f"创建或更新分析师失败：{email}")
    return resp.data[0]


def set_analyst_active(client: Client, email: str, is_active: bool) -> dict:
    """
    更新分析师的在职状态。

    email 不存在时抛出 ValueError。
    email 在 Python 侧做 strip().lower()。

    Args:
        client: 已认证的 Supabase client（需 admin 角色）
        email: 分析师邮箱
        is_active: 是否在职

    Returns:
        dict: 更新后的完整记录

    Raises:
        ValueError: 找不到分析师
    """
    email_lower = email.strip().lower()
    resp = (
        client.table("analyst")
        .update({"is_active": is_active})
        .eq("email", email_lower)
        .execute()
    )
    if not resp.data:
        raise ValueError(f"找不到分析师：{email}")
    return resp.data[0]
