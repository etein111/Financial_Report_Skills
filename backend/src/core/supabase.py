"""
Supabase Client 配置

提供 Supabase 客户端实例
"""
from .config import settings
from supabase import create_client

# 创建 Supabase 客户端（使用 service role key）
supabase_client = create_client(
    settings.SUPABASE_URL,
    settings.SUPABASE_SERVICE_ROLE_KEY
)


def get_supabase():
    """获取 Supabase 客户端"""
    return supabase_client
