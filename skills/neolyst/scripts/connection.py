"""
connection.py — Neolyst Supabase 认证与 client 管理。

配置文件（随 skill 发布，非敏感）：
  skills/neolyst/neolyst.yaml  →  supabase_url, anon_key

凭据文件（本地，不提交）：
  skills/neolyst/user.json  →  { email, password, access_token, refresh_token, expires_at }

测试覆盖（通过环境变量）：
  NEOLYST_URL       →  覆盖 supabase_url
  NEOLYST_ANON_KEY  →  覆盖 anon_key
"""

import json
import os
import time
from pathlib import Path

import yaml
from supabase import create_client, Client

# skill 根目录（skills/neolyst/），neolyst.yaml 和 user.json 默认存放于此
SKILL_ROOT = Path(__file__).parent.parent
NEOLYST_FILE = "user.json"
CONFIG_FILE = "neolyst.yaml"


def _load_config() -> dict:
    """读取 neolyst.yaml，返回 {supabase_url, anon_key}。"""
    config_path = SKILL_ROOT / CONFIG_FILE
    if config_path.exists():
        with config_path.open() as f:
            return yaml.safe_load(f) or {}
    return {}


def _supabase_url() -> str:
    """URL 优先级：NEOLYST_URL 环境变量 > neolyst.yaml。"""
    env = os.environ.get("NEOLYST_URL")
    if env:
        return env.strip()
    config = _load_config()
    url = config.get("supabase_url", "")
    if not url:
        raise ValueError("supabase_url not found. Check skills/neolyst/neolyst.yaml.")
    return url


def _anon_key() -> str:
    """anon key 优先级：NEOLYST_ANON_KEY 环境变量 > neolyst.yaml。"""
    env = os.environ.get("NEOLYST_ANON_KEY")
    if env:
        return env.strip()
    config = _load_config()
    key = config.get("anon_key", "")
    if not key:
        raise ValueError("anon_key not found. Check skills/neolyst/neolyst.yaml.")
    return key


def _user_json_path(neolyst_dir: str | None) -> Path:
    base = Path(neolyst_dir) if neolyst_dir else SKILL_ROOT
    return base / NEOLYST_FILE


def _load_neolyst(neolyst_dir: str | None) -> dict | None:
    p = _user_json_path(neolyst_dir)
    if not p.exists():
        return None
    return json.loads(p.read_text())


def _save_neolyst(neolyst_dir: str | None, data: dict) -> None:
    p = _user_json_path(neolyst_dir)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2))


def _is_expired(expires_at: int, buffer_seconds: int = 60) -> bool:
    return time.time() >= (expires_at - buffer_seconds)


def get_client(
    neolyst_dir: str | None = None,
    email: str | None = None,
    password: str | None = None,
) -> Client:
    """
    返回已认证的 Supabase client。

    URL 和 anon_key 从 neolyst.yaml 读取（可通过环境变量覆盖）。
    用户凭据从 user.json 文件读取（默认位于 skill 根目录）。

    优先顺序：
    1. 从 user.json 恢复 session（token 过期则 refresh）
    2. 用传入的 email+password 登录
    3. 若均无，抛出 ValueError（调用方应提示用户输入凭据）

    Args:
        neolyst_dir: user.json 文件所在目录。None = 使用 skill 根目录（推荐）。
                     测试时可传入临时目录。
        email: 可选，仅在无可用 session 时使用
        password: 可选，仅在无可用 session 时使用

    Returns:
        已认证的 supabase Client
    """
    url = _supabase_url()
    key = _anon_key()
    client = create_client(url, key)
    data = _load_neolyst(neolyst_dir)

    if data and data.get("access_token"):
        if not _is_expired(data.get("expires_at", 0)):
            try:
                client.auth.set_session(data["access_token"], data["refresh_token"])
                return client
            except Exception:
                pass  # token 对当前服务器无效，继续尝试 refresh/re-login
        else:
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

    _email = email or (data.get("email") if data else None)
    _password = password or (data.get("password") if data else None)
    if not _email or not _password:
        raise ValueError(
            "No valid session and no credentials provided. "
            "Pass email+password, or ensure user.json has valid credentials."
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
