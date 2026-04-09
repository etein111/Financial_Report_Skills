# Neolyst Iter 1: connection + analyst Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 完成 neolyst skill 的 analyst 模块，补全测试基础设施，更新 SKILL.md 接口描述与当前设计对齐。

**Architecture:** `analyst.py` 封装对 `analyst` 表的查询，`conftest.py` 提供共享的已认证 Supabase client fixture，集成测试直接打 local Supabase（不用 mock）。

**Tech Stack:** Python 3.12, supabase-py ≥ 2.0, pytest, uv（依赖管理）

---

## 背景与约束

- `analyst` 表以 `email`（lowercase）为主键，无 `id` UUID 字段
- RLS：`dict_select` 允许所有 authenticated 用户读；`dict_write` 只允许 `admin` 角色写
- 本地 Supabase URL：`http://localhost:54321`（anon key 已在 connection.py 内置）
- 测试凭据通过环境变量覆盖：`NEOLYST_TEST_URL`、`NEOLYST_TEST_EMAIL`、`NEOLYST_TEST_PASSWORD`
- 默认测试账号：`yangxue@opendelp.com` / `Admin123`（admin 角色，seed.sql 内置）
- 原设计文档 4.1 节的 `admin@neolyst.com` / `Admin123` 是远程服务器账号，本地不适用
- 测试目录：`~/tmp/neolyst_test`（通过 `NEOLYST_TEST_DIR` 覆盖）
- 项目根目录下不得创建临时文件，临时文件只允许放 `/tmp/` 或 `~/tmp/`

## 文件结构

| 操作 | 文件 | 说明 |
|------|------|------|
| Create | `skills/neolyst/scripts/analyst.py` | resolve_analyst_by_email 实现 |
| Modify | `skills/neolyst/tests/conftest.py` | 新增 neolyst_client session 级 fixture |
| Create | `skills/neolyst/tests/test_analyst.py` | analyst 集成测试 |
| Modify | `skills/neolyst/SKILL.md` | 修正 analyst 接口描述 |

---

## Task 1: 实现 analyst.py

**Files:**
- Create: `skills/neolyst/scripts/analyst.py`

- [ ] **Step 1: 创建 analyst.py**

```python
"""
analyst.py — Neolyst analyst 查询模块。
"""

from supabase import Client


def resolve_analyst_by_email(client: Client, email: str) -> dict:
    """
    根据邮箱查询并返回标准化的 analyst 记录。

    业务主键为 analyst_email（表中强制小写存储）。

    Args:
        client: 已认证的 Supabase client
        email: 分析师邮箱（大小写不敏感）

    Returns:
        dict: analyst 记录，含 email, english_name, chinese_name, suffix,
              sfc, region_code, is_active, created_at, updated_at 字段

    Raises:
        ValueError: 找不到对应的 analyst，或 analyst 已停用（is_active=False）
    """
    normalized = email.strip().lower()
    resp = client.table("analyst").select("*").eq("email", normalized).execute()

    if not resp.data:
        raise ValueError(f"Analyst not found: {email!r}")

    record = resp.data[0]
    if not record.get("is_active", True):
        raise ValueError(f"Analyst is inactive: {email!r}")

    return record
```

- [ ] **Step 2: 验证文件可 import**

```bash
cd /mnt/c/_code/neoskills
uv run python -c "from skills.neolyst.scripts import analyst; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add skills/neolyst/scripts/analyst.py
git commit -m "feat: add analyst.resolve_analyst_by_email"
```

---

## Task 2: 补全 conftest.py 并写集成测试

**Files:**
- Modify: `skills/neolyst/tests/conftest.py`
- Create: `skills/neolyst/tests/test_analyst.py`

- [ ] **Step 1: 更新 conftest.py**

完整替换为以下内容（保留原有 sys.path 设置，新增 neolyst_client fixture）：

```python
"""Pytest 配置文件 - neolyst skill 测试。"""
import os
import sys
import pytest
from pathlib import Path

# 将项目根目录加入 Python 路径，支持 `from skills.neolyst.scripts import ...`
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

NEOLYST_TEST_DIR = Path(os.environ.get("NEOLYST_TEST_DIR", Path.home() / "tmp" / "neolyst_test"))
NEOLYST_TEST_URL = os.environ.get("NEOLYST_TEST_URL", "http://localhost:54321")
NEOLYST_TEST_EMAIL = os.environ.get("NEOLYST_TEST_EMAIL", "admin@neolyst.com")
NEOLYST_TEST_PASSWORD = os.environ.get("NEOLYST_TEST_PASSWORD", "Admin123")


@pytest.fixture(scope="session")
def neolyst_client():
    """返回已认证的 Supabase client（session 级，整个测试会话复用）。"""
    from skills.neolyst.scripts import connection

    NEOLYST_TEST_DIR.mkdir(parents=True, exist_ok=True)
    url_file = NEOLYST_TEST_DIR / ".neolyst.server.url"
    url_file.write_text(NEOLYST_TEST_URL)

    return connection.get_client(
        neolyst_dir=str(NEOLYST_TEST_DIR),
        email=NEOLYST_TEST_EMAIL,
        password=NEOLYST_TEST_PASSWORD,
    )
```

- [ ] **Step 2: 创建 test_analyst.py**

```python
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

        with pytest.raises(ValueError, match="not found"):
            analyst.resolve_analyst_by_email(
                neolyst_client, f"nonexistent.{_SUFFIX}@neolyst-test.com"
            )

    def test_inactive_raises_value_error(self, neolyst_client, inactive_analyst):
        from skills.neolyst.scripts import analyst

        with pytest.raises(ValueError, match="inactive"):
            analyst.resolve_analyst_by_email(neolyst_client, inactive_analyst["email"])
```

- [ ] **Step 3: 运行测试确认通过**

```bash
cd /mnt/c/_code/neoskills
uv run pytest skills/neolyst/tests/test_analyst.py -v
```

Expected（4 tests PASSED）:
```
PASSED test_analyst.py::TestResolveAnalystByEmail::test_found_returns_full_record
PASSED test_analyst.py::TestResolveAnalystByEmail::test_email_is_case_insensitive
PASSED test_analyst.py::TestResolveAnalystByEmail::test_not_found_raises_value_error
PASSED test_analyst.py::TestResolveAnalystByEmail::test_inactive_raises_value_error
```

- [ ] **Step 4: 确认已有 connection 测试仍通过**

```bash
uv run pytest skills/neolyst/tests/test_connection.py -v
```

Expected: 3 tests PASSED

- [ ] **Step 5: Commit**

```bash
git add skills/neolyst/tests/conftest.py skills/neolyst/tests/test_analyst.py
git commit -m "test: add neolyst_client fixture and analyst integration tests"
```

---

## Task 3: 更新 SKILL.md 接口描述

**Files:**
- Modify: `skills/neolyst/SKILL.md`

当前问题：analyst 接口描述返回 `str(analyst.id)`，但 `analyst` 表无 `id` 字段，主键是 `email`，且接口应返回完整 dict。

- [ ] **Step 1: 修改 SKILL.md 第 62-64 行**

将：
```python
analyst_id = analyst.resolve_analyst_by_email(client, email)
# 返回：str（analyst.id）
# 找不到时：抛出 ValueError
```

改为：
```python
record = analyst.resolve_analyst_by_email(client, email)
# 返回：dict（analyst 记录，含 email, english_name, chinese_name, suffix, sfc, region_code, is_active 等）
# 找不到或已停用时：抛出 ValueError
```

- [ ] **Step 2: Commit**

```bash
git add skills/neolyst/SKILL.md
git commit -m "docs: fix analyst interface description in SKILL.md"
```

---

## 自检

- [x] `analyst.py` 实现：normalize email，查询，检查 is_active，返回 dict，ValueError on miss/inactive
- [x] `conftest.py`：session 级 `neolyst_client` fixture，读取 env vars，写 `.neolyst.server.url`
- [x] `test_analyst.py`：4 个集成测试（found / case-insensitive / not-found / inactive），module 级 setup/teardown
- [x] `SKILL.md`：analyst 接口返回类型已修正
- [x] 全部现有测试（test_connection.py）仍然通过

---

## Post-iter1 补丁（同次 session 完成）

iter1 计划执行完毕后，根据用户反馈对认证配置做了重构：

**变更内容：**
- 新增 `skills/neolyst/neolyst.yaml`：将 Supabase URL 和 anon key 从硬编码迁移到此文件，随 skill 发布。
- 重构 `connection.py`：
  - URL / anon key 从 `neolyst.yaml` 读取（通过 `NEOLYST_URL` / `NEOLYST_ANON_KEY` 环境变量覆盖，用于测试）
  - `.neolyst` 凭据文件默认存放在 skill 根目录（`skills/neolyst/`），不再依赖调用方的 cwd
  - `set_session` 加了 try/except，防止跨服务器 token 导致崩溃
- 更新 `conftest.py`：改用 `os.environ.setdefault("NEOLYST_URL", ...)` 替代写 `.neolyst.server.url` 文件。
- 更新 `SKILL.md`：认证配置说明完整化，补充首次使用流程（让 Claude 向用户询问凭据）。
- 更新 `.gitignore`：加入 `.neolyst` 和 `skills/neolyst/.neolyst`。
- 更新设计文档 `docs/skills_neolyst_design.md`：2.4、2.7、3.6、4.1 节同步对齐。