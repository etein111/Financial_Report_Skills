import os

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def setup_env():
    os.environ["APP_ENV"] = "development"
    os.environ["DEBUG"] = "true"
    os.environ["SUPABASE_URL"] = "https://example.supabase.co"
    os.environ["SUPABASE_ANON_KEY"] = "anon-key"
    os.environ["SUPABASE_SERVICE_ROLE_KEY"] = "service-role-key"
    os.environ["SUPABASE_PASSWORD_RESET_REDIRECT"] = "https://example.supabase.co/reset"
    os.environ["SESSION_COOKIE_NAME"] = "access_token"
    os.environ["SESSION_COOKIE_MAX_AGE"] = "86400"
    os.environ["SESSION_COOKIE_SECURE"] = "true"
    os.environ["SESSION_COOKIE_SAMESITE"] = "lax"
    os.environ["PAGE_SIZE"] = "15"
    os.environ["TIMEZONE"] = "Asia/Shanghai"

    from src.core.config import get_settings
    from src.core.supabase import get_supabase_anon, get_supabase_service

    get_settings.cache_clear()
    get_supabase_anon.cache_clear()
    get_supabase_service.cache_clear()
    yield
    get_settings.cache_clear()
    get_supabase_anon.cache_clear()
    get_supabase_service.cache_clear()


@pytest.fixture
def app():
    from src.main import app as fastapi_app

    return fastapi_app


@pytest.fixture
def client(app):
    with TestClient(app) as test_client:
        yield test_client

