from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace


def test_users_list_sorting_pagination_and_search(monkeypatch):
    from src.api import users as users_api

    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    dataset = []
    for idx in range(1, 21):
        dataset.append(
            {
                "id": f"u{idx}",
                "email": f"user{idx}@example.com",
                "full_name": f"User {idx}",
                "role": "analyst",
                "is_active": True,
                "created_at": base + timedelta(days=idx),
            }
        )

    monkeypatch.setattr(users_api, "_fetch_all_users", lambda: dataset)

    page_1 = users_api.list_users_data(query="", page=1)
    assert page_1["page_size"] == 15
    assert len(page_1["items"]) == 15
    assert page_1["items"][0]["id"] == "u20"
    assert page_1["items"][-1]["id"] == "u6"

    page_2 = users_api.list_users_data(query="", page=2)
    assert len(page_2["items"]) == 5
    assert page_2["items"][0]["id"] == "u5"

    searched = users_api.list_users_data(query="user2@example.com", page=1)
    assert searched["total"] == 1
    assert searched["items"][0]["id"] == "u2"


class _FakeQuery:
    def __init__(self, rows, count):
        self._rows = rows
        self._count = count
        self.or_query = None
        self.order_args = None
        self.range_args = None

    def select(self, *_args, **_kwargs):
        return self

    def or_(self, query: str):
        self.or_query = query
        return self

    def order(self, column: str, desc: bool = False):
        self.order_args = (column, desc)
        return self

    def range(self, start: int, end: int):
        self.range_args = (start, end)
        return self

    def execute(self):
        return SimpleNamespace(data=self._rows, count=self._count)


class _FakeClient:
    def __init__(self, query):
        self.query = query
        self.table_name = None

    def table(self, name: str):
        self.table_name = name
        return self.query


def test_regions_list_rule_contract(monkeypatch):
    from src.api import regions as regions_api

    query = _FakeQuery(rows=[{"id": "r1", "name": "China", "code": "CN"}], count=1)
    client = _FakeClient(query)
    monkeypatch.setattr(regions_api, "get_supabase_with_user_token", lambda _token: client)

    data = regions_api.list_regions_data("token", query="CN", page=2)
    assert client.table_name == "region"
    assert query.order_args == ("created_at", True)
    assert query.range_args == (15, 29)
    assert "name.ilike.%CN%" in query.or_query
    assert "code.ilike.%CN%" in query.or_query
    assert data["page_size"] == 15


def test_analyst_list_rule_contract(monkeypatch):
    from src.api import analyst_info as analyst_api

    rows = [
        {
            "id": "a1",
            "full_name": "Alice",
            "chinese_name": "艾丽丝",
            "email": "alice@example.com",
            "region_id": "r1",
            "region": {"name": "China"},
            "is_active": True,
            "created_at": "2026-02-10T00:00:00+00:00",
        }
    ]
    query = _FakeQuery(rows=rows, count=1)
    client = _FakeClient(query)
    monkeypatch.setattr(analyst_api, "get_supabase_with_user_token", lambda _token: client)

    data = analyst_api.list_analyst_data("token", query="alice", page=1)
    assert client.table_name == "analyst"
    assert query.order_args == ("created_at", True)
    assert "full_name.ilike.%alice%" in query.or_query
    assert "chinese_name.ilike.%alice%" in query.or_query
    assert "email.ilike.%alice%" in query.or_query
    assert data["items"][0]["region_name"] == "China"


def test_rls_policy_present_and_role_source_correct():
    migration = Path("..") / "supabase" / "migrations" / "202602131000_auth_and_user_management_baseline.sql"
    sql = migration.read_text(encoding="utf-8")

    assert "alter table public.region enable row level security;" in sql
    assert "alter table public.analyst enable row level security;" in sql
    assert "create policy region_select_authenticated" in sql
    assert "create policy region_write_admin" in sql
    assert "create policy analyst_select_authenticated" in sql
    assert "create policy analyst_write_admin" in sql
    assert "(auth.jwt()->'app_metadata'->>'role') = 'admin'" in sql

