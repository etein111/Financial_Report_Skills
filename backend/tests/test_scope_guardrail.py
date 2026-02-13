def test_api_and_page_scope_guardrail(app):
    paths = {route.path for route in app.routes}

    required_paths = {
        "/login",
        "/desktop",
        "/users",
        "/regions",
        "/analyst-info",
        "/403",
        "/api/auth/login",
        "/api/auth/logout",
        "/api/auth/me",
        "/api/auth/forgot-password",
        "/api/users",
        "/api/users/{user_id}",
        "/api/users/{user_id}/password",
        "/api/users/{user_id}/role",
        "/api/users/{user_id}/toggle-status",
        "/api/users/{user_id}",
        "/api/regions",
        "/api/regions/{region_id}",
        "/api/analyst-info",
        "/api/analyst-info/{analyst_id}",
        "/api/analyst-info/check-email",
    }
    assert required_paths.issubset(paths)

    # Scope guardrail: these endpoints are explicitly out-of-scope in this change.
    assert "/api/auth/reset-password" not in paths
    assert "/api/admin-init" not in paths

