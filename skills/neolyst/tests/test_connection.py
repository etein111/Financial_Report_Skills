import json
import os
import pytest
from pathlib import Path

NEOLYST_DIR = Path(os.environ.get("NEOLYST_TEST_DIR", Path.home() / "tmp" / "neolyst_test"))
NEOLYST_TEST_URL = os.environ.get("NEOLYST_TEST_URL", "http://127.0.0.1:54321")

@pytest.fixture(autouse=True)
def clean_neolyst_file():
    """每个测试前清除 .neolyst 文件，但保留 server.url 覆盖"""
    NEOLYST_DIR.mkdir(parents=True, exist_ok=True)
    # 确保 URL override 存在
    url_file = NEOLYST_DIR / ".neolyst.server.url"
    url_file.write_text(NEOLYST_TEST_URL)
    neolyst_file = NEOLYST_DIR / ".neolyst"
    neolyst_file.unlink(missing_ok=True)
    yield
    # 测试后不清除，方便检查

def test_get_client_with_credentials_writes_session(tmp_path):
    """用 email+password 登录后写入 .neolyst 文件"""
    from skills.neolyst.scripts import connection

    client = connection.get_client(
        neolyst_dir=str(NEOLYST_DIR),
        email="yangxue@opendelp.com",
        password="Admin123",
    )
    assert client is not None
    neolyst_file = NEOLYST_DIR / ".neolyst"
    assert neolyst_file.exists()
    data = json.loads(neolyst_file.read_text())
    assert data["email"] == "yangxue@opendelp.com"
    assert "access_token" in data
    assert "refresh_token" in data
    assert "expires_at" in data

def test_get_client_reuses_session(tmp_path):
    """已有有效 session 时不重新登录（access_token 相同）"""
    from skills.neolyst.scripts import connection

    # 先登录写入 session
    client1 = connection.get_client(
        neolyst_dir=str(NEOLYST_DIR),
        email="yangxue@opendelp.com",
        password="Admin123",
    )
    data1 = json.loads((NEOLYST_DIR / ".neolyst").read_text())
    token1 = data1["access_token"]

    # 再次获取 client，应复用 session
    client2 = connection.get_client(neolyst_dir=str(NEOLYST_DIR))
    data2 = json.loads((NEOLYST_DIR / ".neolyst").read_text())
    assert data2["access_token"] == token1

def test_get_client_no_file_no_credentials_raises():
    """没有 .neolyst 文件也没有传 credentials 时应抛出错误"""
    from skills.neolyst.scripts import connection

    with pytest.raises(Exception, match="credentials"):
        connection.get_client(neolyst_dir=str(NEOLYST_DIR))
