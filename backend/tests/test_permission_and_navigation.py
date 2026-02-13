from fastapi import HTTPException

from src.models.auth import CurrentUser


def _mock_resolve_current_user(monkeypatch):
    from src.api import pages as pages_api
    from src.core import auth as auth_core

    def resolver(token: str) -> CurrentUser:
        if token == "admin-token":
            return CurrentUser(
                id="u-admin",
                email="admin@example.com",
                full_name="Admin",
                role="admin",
                is_active=True,
                access_token=token,
            )
        if token == "sa-token":
            return CurrentUser(
                id="u-sa",
                email="sa@example.com",
                full_name="SA",
                role="sa",
                is_active=True,
                access_token=token,
            )
        if token == "analyst-token":
            return CurrentUser(
                id="u-analyst",
                email="analyst@example.com",
                full_name="Analyst",
                role="analyst",
                is_active=True,
                access_token=token,
            )
        raise HTTPException(status_code=401, detail="Invalid credentials")

    monkeypatch.setattr(auth_core, "resolve_current_user", resolver)
    monkeypatch.setattr(pages_api, "resolve_current_user", resolver)


def test_permission_matrix_and_403_behavior(client, monkeypatch):
    _mock_resolve_current_user(monkeypatch)

    client.cookies.set("access_token", "sa-token")
    sa_users_page = client.get("/users")
    assert sa_users_page.status_code == 403
    assert "No permission" in sa_users_page.text

    sa_users_api = client.get("/api/users")
    assert sa_users_api.status_code == 403
    assert sa_users_api.json()["detail"] == "No permission"

    client.cookies.set("access_token", "admin-token")
    admin_users_page = client.get("/users")
    assert admin_users_page.status_code == 200


def test_desktop_navigation_contract(client, monkeypatch):
    _mock_resolve_current_user(monkeypatch)

    client.cookies.set("access_token", "admin-token")
    admin_desktop = client.get("/desktop")
    assert admin_desktop.status_code == 200
    assert 'href="/users"' in admin_desktop.text
    assert 'href="/regions"' in admin_desktop.text
    assert 'href="/analyst-info"' in admin_desktop.text
    assert 'target="_blank"' in admin_desktop.text

    admin_users = client.get("/users")
    assert admin_users.status_code == 200
    assert "Back to Desktop" not in admin_users.text

    client.cookies.set("access_token", "analyst-token")
    analyst_desktop = client.get("/desktop")
    assert analyst_desktop.status_code == 200
    assert 'href="/users"' not in analyst_desktop.text
    assert 'href="/regions"' not in analyst_desktop.text
    assert 'href="/analyst-info"' not in analyst_desktop.text

