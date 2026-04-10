"""Pytest 配置文件 - neolyst skill 测试。"""
import os
import sys
import pytest
from pathlib import Path

# 将项目根目录加入 Python 路径，支持 `from skills.neolyst.scripts import ...`
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

LOCAL_NEOLYST_URL = os.environ.get("NEOLYST_TEST_URL", "http://127.0.0.1:54321")
LOCAL_NEOLYST_ANON_KEY = os.environ.get(
    "NEOLYST_TEST_ANON_KEY",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9."
    "CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0",
)

# 测试必须显式使用本地 Supabase，不能回落到 skills/neolyst/neolyst.yaml。
os.environ["NEOLYST_URL"] = LOCAL_NEOLYST_URL
os.environ["NEOLYST_ANON_KEY"] = LOCAL_NEOLYST_ANON_KEY

NEOLYST_TEST_DIR = Path(os.environ.get("NEOLYST_TEST_DIR", Path.home() / "tmp" / "neolyst_test"))
NEOLYST_TEST_EMAIL = os.environ.get("NEOLYST_TEST_EMAIL", "yangxue@opendelp.com")
NEOLYST_TEST_PASSWORD = os.environ.get("NEOLYST_TEST_PASSWORD", "Admin123")


@pytest.fixture(scope="session")
def neolyst_client():
    """返回已认证的 Supabase client（session 级，整个测试会话复用）。"""
    from skills.neolyst.scripts import connection

    NEOLYST_TEST_DIR.mkdir(parents=True, exist_ok=True)

    return connection.get_client(
        neolyst_dir=str(NEOLYST_TEST_DIR),
        email=NEOLYST_TEST_EMAIL,
        password=NEOLYST_TEST_PASSWORD,
    )


@pytest.fixture(scope="session", autouse=True)
def ensure_buckets(neolyst_client):
    """确保 templates 和 reports bucket 存在（幂等）。"""
    for bucket in ("templates", "reports"):
        try:
            neolyst_client.storage.create_bucket(bucket, options={"public": False})
        except Exception:
            pass  # 已存在则忽略
