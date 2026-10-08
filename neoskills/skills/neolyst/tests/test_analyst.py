"""
test_analyst.py — resolve_analyst_by_email 集成测试。

测试数据在 module scope 内创建并清理，不依赖预置 seed 数据。
要求 admin 角色（dict_write RLS）。
"""
import uuid
import pytest


# 使用随机后缀避免与现有数据冲突
_SUFFIX = uuid.uuid4().hex[:8]
ACTIVE_EMAIL = f"test.active.{_SUFFIX}@neolyst-test.com"
INACTIVE_EMAIL = f"test.inactive.{_SUFFIX}@neolyst-test.com"


@pytest.fixture(scope="module")
def active_analyst(neolyst_client):
    """创建在职测试分析师，模块结束后删除。"""
    client = neolyst_client
    record = {
        "email": ACTIVE_EMAIL,
        "english_name": "Test Active Analyst",
        "chinese_name": "测试在职分析师",
        "is_active": True,
    }
    client.table("analyst").insert(record).execute()
    yield record
    client.table("analyst").delete().eq("email", ACTIVE_EMAIL).execute()


@pytest.fixture(scope="module")
def inactive_analyst(neolyst_client):
    """创建停用测试分析师，模块结束后删除。"""
    client = neolyst_client
    record = {
        "email": INACTIVE_EMAIL,
        "english_name": "Test Inactive Analyst",
        "is_active": False,
    }
    client.table("analyst").insert(record).execute()
    yield record
    client.table("analyst").delete().eq("email", INACTIVE_EMAIL).execute()


_UPSERT_SUFFIX = uuid.uuid4().hex[:8]
UPSERT_EMAIL = f"test.upsert.{_UPSERT_SUFFIX}@neolyst-test.com"

_SET_ACTIVE_SUFFIX = uuid.uuid4().hex[:8]
SET_ACTIVE_EMAIL = f"test.setactive.{_SET_ACTIVE_SUFFIX}@neolyst-test.com"


@pytest.fixture(scope="class")
def upsert_cleanup(neolyst_client):
    """清理 upsert 测试数据。"""
    yield
    neolyst_client.table("analyst").delete().eq("email", UPSERT_EMAIL).execute()


@pytest.fixture(scope="class")
def set_active_analyst(neolyst_client):
    """创建测试分析师（活跃），类结束后删除。"""
    neolyst_client.table("analyst").upsert(
        {"email": SET_ACTIVE_EMAIL, "english_name": "Set Active Test", "is_active": True},
        on_conflict="email",
    ).execute()
    yield
    neolyst_client.table("analyst").delete().eq("email", SET_ACTIVE_EMAIL).execute()


class TestResolveAnalystByEmail:
    def test_found_returns_full_record(self, neolyst_client, active_analyst):
        from skills.neolyst.scripts import analyst

        result = analyst.resolve_analyst_by_email(neolyst_client, active_analyst["email"])

        assert result["email"] == active_analyst["email"]
        assert result["english_name"] == active_analyst["english_name"]
        assert result["is_active"] is True

    def test_email_is_case_insensitive(self, neolyst_client, active_analyst):
        from skills.neolyst.scripts import analyst

        result = analyst.resolve_analyst_by_email(
            neolyst_client, active_analyst["email"].upper()
        )

        assert result["email"] == active_analyst["email"]

    def test_not_found_raises_value_error(self, neolyst_client):
        from skills.neolyst.scripts import analyst

        with pytest.raises(ValueError, match="找不到分析师"):
            analyst.resolve_analyst_by_email(
                neolyst_client, f"nonexistent.{_SUFFIX}@neolyst-test.com"
            )

    def test_inactive_raises_value_error(self, neolyst_client, inactive_analyst):
        from skills.neolyst.scripts import analyst

        with pytest.raises(ValueError, match="分析师已停用"):
            analyst.resolve_analyst_by_email(neolyst_client, inactive_analyst["email"])


class TestSearchAnalystByName:
    def test_match_english_name(self, neolyst_client, active_analyst):
        from skills.neolyst.scripts import analyst

        results = analyst.search_analyst_by_name(
            neolyst_client, active_analyst["english_name"].split()[0]
        )

        assert len(results) >= 1
        assert any(r["email"] == active_analyst["email"] for r in results)

    def test_match_chinese_name(self, neolyst_client, active_analyst):
        from skills.neolyst.scripts import analyst

        chinese = active_analyst["chinese_name"]
        if chinese:
            results = analyst.search_analyst_by_name(
                neolyst_client, chinese[:2]
            )
            assert len(results) >= 1
            assert any(r["email"] == active_analyst["email"] for r in results)

    def test_no_match_returns_empty_list(self, neolyst_client):
        from skills.neolyst.scripts import analyst

        results = analyst.search_analyst_by_name(neolyst_client, "zzz_nonexistent_xxx")

        assert results == []

    def test_inactive_not_returned(self, neolyst_client, inactive_analyst):
        from skills.neolyst.scripts import analyst

        results = analyst.search_analyst_by_name(
            neolyst_client, inactive_analyst["english_name"].split()[0]
        )

        assert not any(r["email"] == inactive_analyst["email"] for r in results)

    def test_returns_only_select_fields(self, neolyst_client, active_analyst):
        from skills.neolyst.scripts import analyst

        results = analyst.search_analyst_by_name(
            neolyst_client, active_analyst["english_name"].split()[0]
        )

        assert len(results) >= 1
        record = results[0]
        assert set(record.keys()) == {"email", "english_name", "chinese_name"}

    def test_wildcard_escaped(self, neolyst_client, active_analyst):
        from skills.neolyst.scripts import analyst

        results = analyst.search_analyst_by_name(neolyst_client, "%")

        assert len(results) < 5


class TestUpsertAnalyst:
    def test_create_new_analyst(self, neolyst_client, upsert_cleanup):
        from skills.neolyst.scripts import analyst

        result = analyst.upsert_analyst(
            neolyst_client,
            email=UPSERT_EMAIL,
            english_name="Test Upsert Analyst",
            chinese_name="测试Upsert分析师",
            suffix="CFA",
            sfc="S12345",
            region_code="CN",
        )

        assert result["email"] == UPSERT_EMAIL
        assert result["english_name"] == "Test Upsert Analyst"
        assert result["chinese_name"] == "测试Upsert分析师"
        assert result["suffix"] == "CFA"
        assert result["sfc"] == "S12345"
        assert result["region_code"] == "CN"
        assert result["is_active"] is True

    def test_update_existing_analyst(self, neolyst_client, upsert_cleanup):
        from skills.neolyst.scripts import analyst

        analyst.upsert_analyst(
            neolyst_client,
            email=UPSERT_EMAIL,
            english_name="Original Name",
        )

        result = analyst.upsert_analyst(
            neolyst_client,
            email=UPSERT_EMAIL,
            english_name="Updated Name",
            chinese_name="更新后姓名",
        )

        assert result["english_name"] == "Updated Name"
        assert result["chinese_name"] == "更新后姓名"

    def test_email_case_insensitive(self, neolyst_client, upsert_cleanup):
        from skills.neolyst.scripts import analyst

        analyst.upsert_analyst(
            neolyst_client,
            email=UPSERT_EMAIL.upper(),
            english_name="Case Test",
        )

        resp = (
            neolyst_client.table("analyst")
            .select("email")
            .eq("email", UPSERT_EMAIL)
            .execute()
        )
        assert len(resp.data) == 1


class TestSetAnalystActive:
    def test_deactivate_analyst(self, neolyst_client, set_active_analyst):
        from skills.neolyst.scripts import analyst

        result = analyst.set_analyst_active(neolyst_client, SET_ACTIVE_EMAIL, is_active=False)

        assert result["is_active"] is False

    def test_reactivate_analyst(self, neolyst_client, set_active_analyst):
        from skills.neolyst.scripts import analyst

        # 先停用，再恢复
        analyst.set_analyst_active(neolyst_client, SET_ACTIVE_EMAIL, is_active=False)
        result = analyst.set_analyst_active(neolyst_client, SET_ACTIVE_EMAIL, is_active=True)

        assert result["is_active"] is True

    def test_nonexistent_email_raises_value_error(self, neolyst_client):
        from skills.neolyst.scripts import analyst

        with pytest.raises(ValueError, match="找不到分析师"):
            analyst.set_analyst_active(
                neolyst_client, f"nonexistent.{_SET_ACTIVE_SUFFIX}@neolyst-test.com", is_active=False
            )

    def test_email_case_insensitive(self, neolyst_client, set_active_analyst):
        from skills.neolyst.scripts import analyst

        result = analyst.set_analyst_active(
            neolyst_client, SET_ACTIVE_EMAIL.upper(), is_active=False
        )

        assert result["is_active"] is False
