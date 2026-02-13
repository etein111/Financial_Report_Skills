from functools import lru_cache

from supabase import Client, create_client

from .config import get_settings


def _must(value: str, name: str) -> str:
    if not value:
        raise RuntimeError(f"缺少环境变量: {name}")
    return value


@lru_cache(maxsize=1)
def get_supabase_anon() -> Client:
    settings = get_settings()
    return create_client(
        _must(settings.supabase_url, "SUPABASE_URL"),
        _must(settings.supabase_anon_key, "SUPABASE_ANON_KEY"),
    )


@lru_cache(maxsize=1)
def get_supabase_service() -> Client:
    settings = get_settings()
    return create_client(
        _must(settings.supabase_url, "SUPABASE_URL"),
        _must(settings.supabase_service_role_key, "SUPABASE_SERVICE_ROLE_KEY"),
    )


def get_supabase_with_user_token(token: str) -> Client:
    settings = get_settings()
    client = create_client(
        _must(settings.supabase_url, "SUPABASE_URL"),
        _must(settings.supabase_anon_key, "SUPABASE_ANON_KEY"),
    )
    client.postgrest.auth(token)
    return client

