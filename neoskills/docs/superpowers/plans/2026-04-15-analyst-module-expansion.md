# Analyst 模块扩展实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 `analyst.py` 中新增 `search_analyst_by_name`、`upsert_analyst`、`set_analyst_active` 三个接口，同步更新测试和文档。

**Architecture:** 所有接口放在 `skills/neolyst/scripts/analyst.py`，不新增文件。读操作（search）走 PostgREST ilike 查询；写操作（upsert、set_active）走 PostgREST upsert/update，受 `dict_write` RLS 约束（仅 admin）。测试复用现有 `neolyst_client` fixture（admin 角色）。

**Tech Stack:** Python, Supabase (PostgREST), pytest

---

## File Structure

| 操作 | 文件 | 职责 |
|------|------|------|
| Modify | `skills/neolyst/scripts/analyst.py` | 新增 3 个函数 |
| Modify | `skills/neolyst/tests/test_analyst.py` | 新增 3 个测试类 |
| Modify | `skills/neolyst/SKILL.md` | 接口表从 1 行扩展为 4 行 |
| Modify | `skills/neolyst/references/interfaces.md` | 新增接口 #2 #3 #4 的完整签名和示例 |

---

### Task 1: search_analyst_by_name — 测试

**Files:**
- Test: `skills/neolyst/tests/test_analyst.py`

- [ ] **Step 1: 在 test_analyst.py 末尾追加 TestSearchAnalystByName 类**

```python
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

        # % 和 _ 是 SQL 通配符，不应被当作通配符
        results = analyst.search_analyst_by_name(neolyst_client, "%")

        # 不应返回所有活跃分析师
        assert len(results) < 5
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd /mnt/c/_code/neoskills && uv run pytest skills/neolyst/tests/test_analyst.py::TestSearchAnalystByName -v`
Expected: FAIL — `ImportError: cannot import name 'search_analyst_by_name'`

---

### Task 2: search_analyst_by_name — 实现

**Files:**
- Modify: `skills/neolyst/scripts/analyst.py`

- [ ] **Step 1: 在 analyst.py 中追加 search_analyst_by_email 函数**

在 `resolve_analyst_by_email` 函数之后追加：

```python
def search_analyst_by_name(client: Client, name: str) -> list[dict]:
    """
    按姓名模糊查询活跃分析师，返回精简字段。

    同时匹配 english_name 和 chinese_name（ilike 模糊匹配）。
    只返回 is_active=True 的分析师。
    返回字段：email、english_name、chinese_name。
    name 中的 % 和 _ 在 Python 侧 escape，防止通配符注入。
    无匹配时返回空列表。

    Args:
        client: 已认证的 Supabase client
        name: 待匹配的姓名（部分即可）

    Returns:
        list[dict]: 匹配的分析师列表，每条含 email, english_name, chinese_name
    """
    escaped = name.replace("%", "\\%").replace("_", "\\_")
    resp = (
        client.table("analyst")
        .select("email,english_name,chinese_name")
        .or_(f"english_name.ilike.%{escaped}%,chinese_name.ilike.%{escaped}%")
        .eq("is_active", True)
        .execute()
    )
    return resp.data if resp.data else []
```

- [ ] **Step 2: 运行测试验证通过**

Run: `cd /mnt/c/_code/neoskills && uv run pytest skills/neolyst/tests/test_analyst.py::TestSearchAnalystByName -v`
Expected: 6 tests PASS

- [ ] **Step 3: Commit**

```bash
git add skills/neolyst/scripts/analyst.py skills/neolyst/tests/test_analyst.py
git commit -m "feat: add search_analyst_by_name with tests"
```

---

### Task 3: upsert_analyst — 测试

**Files:**
- Test: `skills/neolyst/tests/test_analyst.py`

- [ ] **Step 1: 在 test_analyst.py 末尾追加 TestUpsertAnalyst 类**

```python
_UPSERT_SUFFIX = uuid.uuid4().hex[:8]
UPSERT_EMAIL = f"test.upsert.{_UPSERT_SUFFIX}@neolyst-test.com"


@pytest.fixture(scope="class")
def upsert_cleanup(neolyst_client):
    """清理 upsert 测试数据。"""
    yield
    neolyst_client.table("analyst").delete().eq("email", UPSERT_EMAIL).execute()


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

        # 先创建
        analyst.upsert_analyst(
            neolyst_client,
            email=UPSERT_EMAIL,
            english_name="Original Name",
        )

        # 再更新
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

        # 用小写查询确认已标准化
        resp = (
            neolyst_client.table("analyst")
            .select("email")
            .eq("email", UPSERT_EMAIL)
            .execute()
        )
        assert len(resp.data) == 1
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd /mnt/c/_code/neoskills && uv run pytest skills/neolyst/tests/test_analyst.py::TestUpsertAnalyst -v`
Expected: FAIL — `ImportError: cannot import name 'upsert_analyst'`

---

### Task 4: upsert_analyst — 实现

**Files:**
- Modify: `skills/neolyst/scripts/analyst.py`

- [ ] **Step 1: 在 analyst.py 中追加 upsert_analyst 函数**

在 `search_analyst_by_name` 函数之后追加：

```python
def upsert_analyst(
    client: Client,
    email: str,
    english_name: str,
    chinese_name: str | None = None,
    suffix: str | None = None,
    sfc: str | None = None,
    region_code: str | None = None,
    is_active: bool = True,
) -> dict:
    """
    以 email 为键创建或更新分析师。

    email 在 Python 侧做 strip().lower()，与 DB CHECK 约束一致。
    返回 upsert 后的完整记录。DB 触发器 trg_analyst_updated_at 自动维护 updated_at。

    Args:
        client: 已认证的 Supabase client（需 admin 角色）
        email: 分析师邮箱
        english_name: 英文姓名
        chinese_name: 中文姓名
        suffix: 姓名后缀/头衔
        sfc: 证券期货从业资格编号
        region_code: 所属区域编码
        is_active: 是否在职

    Returns:
        dict: upsert 后的完整记录

    Raises:
        ValueError: RPC 返回错误（如 RLS 权限不足）
    """
    email_lower = email.strip().lower()
    record = {
        "email": email_lower,
        "english_name": english_name,
        "chinese_name": chinese_name,
        "suffix": suffix,
        "sfc": sfc,
        "region_code": region_code,
        "is_active": is_active,
    }
    resp = client.table("analyst").upsert(record, on_conflict="email").execute()
    if not resp.data:
        raise ValueError(f"创建或更新分析师失败：{email}")
    return resp.data[0]
```

- [ ] **Step 2: 运行测试验证通过**

Run: `cd /mnt/c/_code/neoskills && uv run pytest skills/neolyst/tests/test_analyst.py::TestUpsertAnalyst -v`
Expected: 3 tests PASS

- [ ] **Step 3: Commit**

```bash
git add skills/neolyst/scripts/analyst.py skills/neolyst/tests/test_analyst.py
git commit -m "feat: add upsert_analyst with tests"
```

---

### Task 5: set_analyst_active — 测试

**Files:**
- Test: `skills/neolyst/tests/test_analyst.py`

- [ ] **Step 1: 在 test_analyst.py 末尾追加 TestSetAnalystActive 类**

```python
_SET_ACTIVE_SUFFIX = uuid.uuid4().hex[:8]
SET_ACTIVE_EMAIL = f"test.setactive.{_SET_ACTIVE_SUFFIX}@neolyst-test.com"


@pytest.fixture(scope="class")
def set_active_cleanup(neolyst_client):
    """清理 set_active 测试数据。"""
    yield
    neolyst_client.table("analyst").delete().eq("email", SET_ACTIVE_EMAIL).execute()


class TestSetAnalystActive:
    def test_deactivate_analyst(self, neolyst_client, set_active_cleanup):
        from skills.neolyst.scripts import analyst

        # 创建活跃分析师
        neolyst_client.table("analyst").insert({
            "email": SET_ACTIVE_EMAIL,
            "english_name": "Set Active Test",
            "is_active": True,
        }).execute()

        # 停用
        result = analyst.set_analyst_active(neolyst_client, SET_ACTIVE_EMAIL, is_active=False)

        assert result["is_active"] is False

    def test_reactivate_analyst(self, neolyst_client, set_active_cleanup):
        from skills.neolyst.scripts import analyst

        # 创建停用分析师
        neolyst_client.table("analyst").insert({
            "email": SET_ACTIVE_EMAIL,
            "english_name": "Set Active Test",
            "is_active": False,
        }).execute()

        # 恢复
        result = analyst.set_analyst_active(neolyst_client, SET_ACTIVE_EMAIL, is_active=True)

        assert result["is_active"] is True

    def test_nonexistent_email_raises_value_error(self, neolyst_client):
        from skills.neolyst.scripts import analyst

        with pytest.raises(ValueError, match="找不到分析师"):
            analyst.set_analyst_active(
                neolyst_client, f"nonexistent.{_SET_ACTIVE_SUFFIX}@neolyst-test.com", is_active=False
            )

    def test_email_case_insensitive(self, neolyst_client, set_active_cleanup):
        from skills.neolyst.scripts import analyst

        neolyst_client.table("analyst").insert({
            "email": SET_ACTIVE_EMAIL,
            "english_name": "Set Active Test",
            "is_active": True,
        }).execute()

        # 用大写邮箱调用
        result = analyst.set_analyst_active(
            neolyst_client, SET_ACTIVE_EMAIL.upper(), is_active=False
        )

        assert result["is_active"] is False
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd /mnt/c/_code/neoskills && uv run pytest skills/neolyst/tests/test_analyst.py::TestSetAnalystActive -v`
Expected: FAIL — `ImportError: cannot import name 'set_analyst_active'`

---

### Task 6: set_analyst_active — 实现

**Files:**
- Modify: `skills/neolyst/scripts/analyst.py`

- [ ] **Step 1: 在 analyst.py 中追加 set_analyst_active 函数**

在 `upsert_analyst` 函数之后追加：

```python
def set_analyst_active(client: Client, email: str, is_active: bool) -> dict:
    """
    更新分析师的在职状态。

    email 不存在时抛出 ValueError。
    email 在 Python 侧做 strip().lower()。

    Args:
        client: 已认证的 Supabase client（需 admin 角色）
        email: 分析师邮箱
        is_active: 是否在职

    Returns:
        dict: 更新后的完整记录

    Raises:
        ValueError: 找不到分析师
    """
    email_lower = email.strip().lower()
    resp = (
        client.table("analyst")
        .update({"is_active": is_active})
        .eq("email", email_lower)
        .execute()
    )
    if not resp.data:
        raise ValueError(f"找不到分析师：{email}")
    return resp.data[0]
```

- [ ] **Step 2: 运行测试验证通过**

Run: `cd /mnt/c/_code/neoskills && uv run pytest skills/neolyst/tests/test_analyst.py::TestSetAnalystActive -v`
Expected: 4 tests PASS

- [ ] **Step 3: Commit**

```bash
git add skills/neolyst/scripts/analyst.py skills/neolyst/tests/test_analyst.py
git commit -m "feat: add set_analyst_active with tests"
```

---

### Task 7: 全量测试 + 模块注释更新

**Files:**
- Modify: `skills/neolyst/scripts/analyst.py`

- [ ] **Step 1: 更新 analyst.py 模块注释**

将第 1-2 行：
```python
"""
analyst.py — Neolyst analyst 查询模块。
"""
```
替换为：
```python
"""
analyst.py — Neolyst analyst 查询与管理模块。

接口：
1. resolve_analyst_by_email — 按邮箱精确查询一人（直接查表）
2. search_analyst_by_name — 按姓名模糊查询活跃分析师
3. upsert_analyst — 以 email 为键创建或更新分析师（需 admin）
4. set_analyst_active — 更新分析师在职状态（需 admin）
"""
```

- [ ] **Step 2: 运行全部 analyst 测试**

Run: `cd /mnt/c/_code/neoskills && uv run pytest skills/neolyst/tests/test_analyst.py -v`
Expected: 17 tests PASS（4 原有 + 6 search + 3 upsert + 4 set_active）

- [ ] **Step 3: Commit**

```bash
git add skills/neolyst/scripts/analyst.py
git commit -m "docs: update analyst.py module docstring"
```

---

### Task 8: 更新 SKILL.md 接口表

**Files:**
- Modify: `skills/neolyst/SKILL.md`

- [ ] **Step 1: 在接口表中扩展 analyst 行**

将接口 #1 的行：
```
| 1 | `resolve_analyst_by_email(client, email)` | `analyst` | 按邮箱查询 analyst 记录（直接查表） |
```
替换为 4 行：
```
| 1 | `resolve_analyst_by_email(client, email)` | `analyst` | 按邮箱精确查询 analyst 记录（直接查表） |
| 1a | `search_analyst_by_name(client, name)` | `analyst` | 按姓名模糊查询活跃分析师，返回精简字段 |
| 1b | `upsert_analyst(client, email, english_name, ...)` | `analyst` | 以 email 为键创建或更新分析师（需 admin） |
| 1c | `set_analyst_active(client, email, is_active)` | `analyst` | 更新分析师在职状态（需 admin） |
```

- [ ] **Step 2: Commit**

```bash
git add skills/neolyst/SKILL.md
git commit -m "docs: add 3 new analyst interfaces to SKILL.md"
```

---

### Task 9: 更新 interfaces.md

**Files:**
- Modify: `skills/neolyst/references/interfaces.md`

- [ ] **Step 1: 在 §1 resolve_analyst_by_email 之后追加新接口文档**

在 `## 2. resolve_template` 之前插入：

```markdown
## 1a. search_analyst_by_name

按姓名模糊查询活跃分析师，返回精简字段（直接查表）。

```python
from skills.neolyst.scripts import analyst

results = analyst.search_analyst_by_name(client, "Alice")
# 返回：[{"email": "alice@neolyst.com", "english_name": "Alice Chen", "chinese_name": "陈小明"}, ...]
# 无匹配：返回 []
```

- 同时匹配 `english_name` 和 `chinese_name`（ilike 模糊匹配）
- 只返回 `is_active=True` 的分析师
- 返回字段：`email`、`english_name`、`chinese_name`
- `name` 中的 `%` 和 `_` 在 Python 侧 escape，防止通配符注入
- 受 `dict_select` RLS 约束，所有认证用户可调用

## 1b. upsert_analyst

以 email 为键创建或更新分析师记录（需 admin 角色）。

```python
from skills.neolyst.scripts import analyst

record = analyst.upsert_analyst(
    client,
    email="alice@neolyst.com",
    english_name="Alice Chen",
    chinese_name="陈小明",
    suffix="CFA",
    sfc="S12345",
    region_code="CN",
)
# 返回：dict，完整 analyst 记录（含 email, english_name, chinese_name, suffix, sfc, region_code, is_active, created_at, updated_at）
```

- email 自动做 `strip().lower()` 标准化
- 已存在时更新，不存在时创建
- 受 `dict_write` RLS 约束，仅 admin 角色可执行

## 1c. set_analyst_active

更新分析师的在职状态（需 admin 角色）。

```python
from skills.neolyst.scripts import analyst

record = analyst.set_analyst_active(client, "alice@neolyst.com", is_active=False)
# 返回：dict，更新后的完整 analyst 记录
# 邮箱不存在：抛出 ValueError（"找不到分析师：{email}"）
```

- email 自动做 `strip().lower()` 标准化
- 受 `dict_write` RLS 约束，仅 admin 角色可执行
```

- [ ] **Step 2: Commit**

```bash
git add skills/neolyst/references/interfaces.md
git commit -m "docs: add search/upsert/set_active analyst interfaces to interfaces.md"
```
