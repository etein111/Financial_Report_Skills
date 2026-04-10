import json
import os
import pytest
from pathlib import Path

NEOLYST_DIR = Path(os.environ.get("NEOLYST_TEST_DIR", Path.home() / "tmp" / "neolyst_test"))

@pytest.fixture(autouse=True)
def clean_auth_files():
    """每个测试前清除认证文件，确保测试从干净状态开始。"""
    NEOLYST_DIR.mkdir(parents=True, exist_ok=True)
    for filename in ("user.json", "session.json"):
        (NEOLYST_DIR / filename).unlink(missing_ok=True)
    yield

def test_get_client_with_credentials_writes_session():
    """用 email+password 登录后分别写入 user.json 和 session.json。"""
    from skills.neolyst.scripts import connection

    client = connection.get_client(
        neolyst_dir=str(NEOLYST_DIR),
        email="yangxue@opendelp.com",
        password="Admin123",
    )
    assert client is not None
    user_json = NEOLYST_DIR / "user.json"
    session_json = NEOLYST_DIR / "session.json"
    assert user_json.exists()
    assert session_json.exists()

    user_data = json.loads(user_json.read_text())
    session_data = json.loads(session_json.read_text())
    assert user_data["email"] == "yangxue@opendelp.com"
    assert user_data["password"] == "Admin123"
    assert "access_token" in session_data
    assert "refresh_token" in session_data
    assert "expires_at" in session_data

def test_get_client_reuses_session():
    """已有有效 session 时不重新登录（access_token 相同）"""
    from skills.neolyst.scripts import connection

    client1 = connection.get_client(
        neolyst_dir=str(NEOLYST_DIR),
        email="yangxue@opendelp.com",
        password="Admin123",
    )
    assert client1 is not None
    data1 = json.loads((NEOLYST_DIR / "session.json").read_text())
    token1 = data1["access_token"]

    client2 = connection.get_client(neolyst_dir=str(NEOLYST_DIR))
    assert client2 is not None
    data2 = json.loads((NEOLYST_DIR / "session.json").read_text())
    assert data2["access_token"] == token1

def test_get_client_no_file_no_credentials_raises():
    """没有 user.json/session.json 且未传 credentials 时应抛出错误。"""
    from skills.neolyst.scripts import connection

    with pytest.raises(Exception, match="credentials"):
        connection.get_client(neolyst_dir=str(NEOLYST_DIR))
