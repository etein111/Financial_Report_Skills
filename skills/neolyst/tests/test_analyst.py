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
