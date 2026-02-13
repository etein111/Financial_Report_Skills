from types import SimpleNamespace


class FakeAuth:
    def __init__(self):
        self.reset_calls: list[tuple[str, dict]] = []

    def sign_in_with_password(self, payload: dict):
        if payload["password"] != "CorrectPass123":
            raise ValueError("invalid credentials")

        user = SimpleNamespace(
            id="user-1",
            email=payload["email"],
            app_metadata={"role": "admin", "is_active": True},
            user_metadata={"full_name": "Admin User"},
        )
        session = SimpleNamespace(access_token="token-admin")
        return SimpleNamespace(user=user, session=session)

    def get_user(self, jwt: str):
        if jwt != "token-admin":
            raise ValueError("invalid token")
        user = SimpleNamespace(
            id="user-1",
            email="admin@example.com",
            app_metadata={"role": "admin", "is_active": True},
            user_metadata={"full_name": "Admin User"},
        )
        return SimpleNamespace(user=user)

    def reset_password_email(self, email: str, options: dict):
        self.reset_calls.append((email, options))


class FakeSupabase:
    def __init__(self):
        self.auth = FakeAuth()


def _patch_supabase(monkeypatch):
    fake = FakeSupabase()
    from src.api import auth as auth_api
    from src.core import auth as auth_core

    monkeypatch.setattr(auth_api, "get_supabase_anon", lambda: fake)
    monkeypatch.setattr(auth_core, "get_supabase_anon", lambda: fake)
    return fake


def test_auth_login_logout_me_and_forgot_password_flow(client, monkeypatch):
    fake = _patch_supabase(monkeypatch)

    login_resp = client.post(
        "/api/auth/login",
        json={"email": "admin@example.com", "password": "CorrectPass123"},
    )
    assert login_resp.status_code == 200
    set_cookie = login_resp.headers.get("set-cookie", "")
    assert "access_token=token-admin" in set_cookie
    assert "HttpOnly" in set_cookie
    assert "Secure" in set_cookie
    assert "SameSite=lax" in set_cookie
    assert "Max-Age=86400" in set_cookie

    client.cookies.set("access_token", "token-admin")
    me_resp = client.get("/api/auth/me")
    assert me_resp.status_code == 200
    assert me_resp.json()["data"]["role"] == "admin"

    forgot_known = client.post("/api/auth/forgot-password", json={"email": "admin@example.com"})
    forgot_unknown = client.post("/api/auth/forgot-password", json={"email": "nobody@example.com"})
    assert forgot_known.status_code == 200
    assert forgot_unknown.status_code == 200
    assert forgot_known.json()["message"] == forgot_unknown.json()["message"]
    assert len(fake.auth.reset_calls) == 2

    logout_resp = client.post("/api/auth/logout")
    assert logout_resp.status_code == 200
    assert "access_token=" in logout_resp.headers.get("set-cookie", "")

    client.cookies.clear()

    me_after_logout = client.get("/api/auth/me")
    assert me_after_logout.status_code == 401


def test_auth_login_invalid_credentials(client, monkeypatch):
    _patch_supabase(monkeypatch)
    resp = client.post(
        "/api/auth/login",
        json={"email": "admin@example.com", "password": "WrongPass123"},
    )
    assert resp.status_code == 401
    assert "set-cookie" not in resp.headers
