"""
connection.py — Neolyst Supabase 认证与 client 管理。

配置文件（随 skill 发布，非敏感）：
  skills/neolyst/neolyst.yaml  →  supabase_url, anon_key

凭据文件（本地，不提交）：
  skills/neolyst/user.json     →  { email, password }
  skills/neolyst/session.json  →  { access_token, refresh_token, expires_at }

测试覆盖（通过环境变量）：
  NEOLYST_URL       →  覆盖 supabase_url
  NEOLYST_ANON_KEY  →  覆盖 anon_key
"""

import json
import logging
import os
import time
from pathlib import Path

import yaml
from supabase import create_client, Client

logger = logging.getLogger(__name__)

# skill 根目录（skills/neolyst/），neolyst.yaml 和 user.json 默认存放于此
SKILL_ROOT = Path(__file__).parent.parent
USER_FILE = "user.json"
SESSION_FILE = "session.json"
CONFIG_FILE = "neolyst.yaml"

_config_cache: dict | None = None


def _load_config() -> dict:
    """读取 neolyst.yaml，返回 {supabase_url, anon_key}。结果按进程缓存。"""
    global _config_cache
    if _config_cache is not None:
        return _config_cache
    config_path = SKILL_ROOT / CONFIG_FILE
    if config_path.exists():
        with config_path.open(encoding="utf-8") as f:
            _config_cache = yaml.safe_load(f) or {}
    else:
        _config_cache = {}
    return _config_cache


def _supabase_url(config: dict) -> str:
    """URL 优先级：NEOLYST_URL 环境变量 > neolyst.yaml。"""
    env = os.environ.get("NEOLYST_URL")
    if env:
        return env.strip()
    url = config.get("supabase_url", "")
    if not url:
        raise ValueError("未找到 supabase_url，请检查 skills/neolyst/neolyst.yaml。")
    return url


def _anon_key(config: dict) -> str:
    """anon key 优先级：NEOLYST_ANON_KEY 环境变量 > neolyst.yaml。"""
    env = os.environ.get("NEOLYST_ANON_KEY")
    if env:
        return env.strip()
    key = config.get("anon_key", "")
    if not key:
        raise ValueError("未找到 anon_key，请检查 skills/neolyst/neolyst.yaml。")
    return key


def _file_path(neolyst_dir: str | None, filename: str) -> Path:
    base = Path(neolyst_dir) if neolyst_dir else SKILL_ROOT
    return base / filename


def _load_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    return json.loads(path.read_text())


def _save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))


def _load_user(neolyst_dir: str | None) -> dict | None:
    return _load_json(_file_path(neolyst_dir, USER_FILE))


def _load_session(neolyst_dir: str | None) -> dict | None:
    return _load_json(_file_path(neolyst_dir, SESSION_FILE))


def _save_user(neolyst_dir: str | None, data: dict) -> None:
    _save_json(_file_path(neolyst_dir, USER_FILE), data)


def _save_session(neolyst_dir: str | None, data: dict) -> None:
    _save_json(_file_path(neolyst_dir, SESSION_FILE), data)


def _is_expired(expires_at: int, buffer_seconds: int = 60) -> bool:
    return time.time() >= (expires_at - buffer_seconds)


def _extract_session_data(session) -> dict:
    """从 Supabase session 对象提取持久化所需的三个字段。"""
    return {
        "access_token": session.access_token,
        "refresh_token": session.refresh_token,
        "expires_at": session.expires_at,
    }


def get_client(
    neolyst_dir: str | None = None,
    email: str | None = None,
    password: str | None = None,
) -> Client:
    """
    返回已认证的 Supabase client。

    URL 和 anon_key 从 neolyst.yaml 读取（可通过环境变量覆盖）。
    用户凭据从 user.json 读取，登录态从 session.json 读取（默认位于 skill 根目录）。

    优先顺序：
    1. 从 session.json 恢复 session（token 过期或无效则 refresh）
    2. refresh 失败后，用传入的 email+password 或 user.json 中的凭据登录
    3. 若均无，抛出 ValueError（调用方应提示用户输入凭据）

    Args:
        neolyst_dir: user.json / session.json 所在目录。None = 使用 skill 根目录（推荐）。
                     测试时可传入临时目录。
        email: 可选，仅在无可用 session 时使用
        password: 可选，仅在无可用 session 时使用

    Returns:
        已认证的 supabase Client
    """
    config = _load_config()
    url = _supabase_url(config)
    key = _anon_key(config)
    client = create_client(url, key)
    user_data = _load_user(neolyst_dir)
    session_data = _load_session(neolyst_dir)

    if session_data and session_data.get("access_token"):
        if not _is_expired(session_data.get("expires_at", 0)):
            try:
                client.auth.set_session(session_data["access_token"], session_data["refresh_token"])
                client.auth.get_user()  # 验证 token 对当前服务器是否有效
                return client
            except Exception as exc:
                logger.debug("set_session 失败，将尝试 refresh: %s", exc)
        # token 过期或无效，尝试 refresh
        try:
            resp = client.auth.refresh_session(session_data["refresh_token"])
            _save_session(neolyst_dir, _extract_session_data(resp.session))
            return client
        except Exception as exc:
            logger.debug("refresh_session 失败，将尝试密码登录: %s", exc)

    _email = email or (user_data.get("email") if user_data else None)
    _password = password or (user_data.get("password") if user_data else None)
    if not _email or not _password:
        raise ValueError(
            "无可用 session 且未提供凭据。请传入 email+password，"
            "或确保 user.json 包含有效凭据。"
        )

    try:
        resp = client.auth.sign_in_with_password({"email": _email, "password": _password})
    except Exception as e:
        raise ValueError(
            f"认证失败（{_email!r}）: {e}。"
            "请使用有效凭据调用 get_client(email=..., password=...)。"
        ) from e
    _save_user(neolyst_dir, {"email": _email, "password": _password})
    _save_session(neolyst_dir, _extract_session_data(resp.session))
    return client
