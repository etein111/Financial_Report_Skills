"""
connection.py — Neolyst Supabase 认证与 client 管理。

.neolyst 文件格式：
  { "email": "...", "password": "...", "access_token": "...",
    "refresh_token": "...", "expires_at": 1712345678 }
"""

import json
import time
from pathlib import Path

from supabase import create_client, Client

DEFAULT_SUPABASE_URL = "http://47.57.213.88:80"
NEOLYST_FILE = ".neolyst"
SERVER_URL_OVERRIDE_FILE = ".neolyst.server.url"


def _supabase_url(neolyst_dir: str) -> str:
    override = Path(neolyst_dir) / SERVER_URL_OVERRIDE_FILE
    if override.exists():
        return override.read_text().strip()
    return DEFAULT_SUPABASE_URL


def _load_neolyst(neolyst_dir: str) -> dict | None:
    p = Path(neolyst_dir) / NEOLYST_FILE
    if not p.exists():
        return None
    return json.loads(p.read_text())


def _save_neolyst(neolyst_dir: str, data: dict) -> None:
    p = Path(neolyst_dir) / NEOLYST_FILE
    Path(neolyst_dir).mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2))


def _is_expired(expires_at: int, buffer_seconds: int = 60) -> bool:
    return time.time() >= (expires_at - buffer_seconds)


def get_client(
    neolyst_dir: str = ".",
    email: str | None = None,
    password: str | None = None,
) -> Client:
    """
    返回已认证的 Supabase client。

    优先顺序：
    1. 从 .neolyst 恢复 session（refresh 若已过期）
    2. 用传入的 email+password 登录
    3. 若均无，抛出 ValueError

    Args:
        neolyst_dir: .neolyst 文件所在目录（默认当前工作目录）
        email: 可选，仅在无可用 session 时使用
        password: 可选，仅在无可用 session 时使用

    Returns:
        已认证的 supabase Client
    """
    url = _supabase_url(neolyst_dir)
    anon_key_file = Path(neolyst_dir) / ".neolyst.anon_key"
    if anon_key_file.exists():
        anon_key = anon_key_file.read_text().strip()
    else:
        anon_key = _get_default_anon_key()

    client = create_client(url, anon_key)
    data = _load_neolyst(neolyst_dir)

    if data and data.get("access_token"):
        if not _is_expired(data.get("expires_at", 0)):
            # session 有效，直接恢复
            client.auth.set_session(data["access_token"], data["refresh_token"])
            return client
        else:
            # 尝试 refresh
            try:
                resp = client.auth.refresh_session(data["refresh_token"])
                session = resp.session
                _save_neolyst(neolyst_dir, {
                    "email": data.get("email", ""),
                    "password": data.get("password", ""),
                    "access_token": session.access_token,
                    "refresh_token": session.refresh_token,
                    "expires_at": session.expires_at,
                })
                return client
            except Exception:
                pass  # refresh 失败，继续尝试 password 登录

    # 用 email+password 登录
    _email = email or (data.get("email") if data else None)
    _password = password or (data.get("password") if data else None)
    if not _email or not _password:
        raise ValueError(
            "No valid session found and no credentials provided. "
            "Pass email+password or ensure .neolyst has valid credentials."
        )

    resp = client.auth.sign_in_with_password({"email": _email, "password": _password})
    session = resp.session
    _save_neolyst(neolyst_dir, {
        "email": _email,
        "password": _password,
        "access_token": session.access_token,
        "refresh_token": session.refresh_token,
        "expires_at": session.expires_at,
    })
    return client


def _get_default_anon_key() -> str:
    """联调环境的 anon key（从 Supabase 项目设置获取）。"""
    return "***REMOVED-JWT***"
