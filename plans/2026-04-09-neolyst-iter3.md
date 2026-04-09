# Neolyst Iter 3: coverage 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 neolyst skill 的 coverage 模块，包含 `resolve_coverage` 和 `create_coverage` 两个接口；同时将 analyst 模块（SQL + Python）的错误信息改为中文。

**Architecture:**
- **Supabase 侧**：新增迁移文件，定义 `resolve_coverage` 和 `create_coverage` 两个 RPC，并用 `create or replace` 把 `resolve_analyst_by_email` 错误消息改为中文
- **`coverage.py`**：调用 RPC，不含业务逻辑，失败时包装为 `ValueError`
- **`analyst.py`**（补丁）：Python 侧的英文兜底错误消息改为中文
- **集成测试**：直接打 local Supabase，复用 `neolyst_client` fixture，module 级 teardown 清理数据

**原则：** 业务逻辑只在 Supabase 侧（RPC 里），Python 只做参数整理和调用；所有 schema 变更写入 `supabase/migrations/`。

---

## 背景与约束

- `coverage` 表唯一约束：`uidx_coverage_ticker_lower`（`lower(btrim(ticker))`）、`uidx_coverage_isin_upper`（`upper(btrim(isin))`）
- `coverage_analyst` 表唯一约束：`UNIQUE(coverage_id, analyst_email)`、`UNIQUE(coverage_id, author_order)`；FK `coverage_id` → `coverage.id` ON DELETE CASCADE
- RLS 已有：coverage INSERT 允许 admin/sa/analyst；coverage_analyst INSERT 允许 admin/sa/analyst；SELECT 均为全量 authenticated
- 测试账号：`yangxue@opendelp.com` / `Admin123`（admin 角色）
- 测试 URL：`http://127.0.0.1:54321`（`neolyst.yaml` 默认值）

---

## 文件结构

| 文件 | 操作 | 说明 |
|------|------|------|
| `supabase/migrations/20260409000630_060_coverage_functions.sql` | 新建 | `resolve_coverage`、`create_coverage` RPC；`resolve_analyst_by_email` 中文错误补丁 |
| `skills/neolyst/scripts/coverage.py` | 新建 | `resolve_coverage`、`create_coverage` Python 接口 |
| `skills/neolyst/scripts/analyst.py` | 修改 | Python 侧英文兜底错误消息改为中文 |
| `skills/neolyst/tests/test_coverage.py` | 新建 | coverage 集成测试（10 个测试） |

---

## Task 1: Supabase 迁移 — coverage RPC + analyst 错误中文补丁

**Files:**
- Create: `supabase/migrations/20260409000630_060_coverage_functions.sql`

- [ ] **Step 1: 创建迁移文件**

```sql
-- 20260409000630_060_coverage_functions.sql
-- coverage 解析与创建 RPC；resolve_analyst_by_email 错误消息改为中文

-- ----------------------------------------------------------------
-- 补丁：resolve_analyst_by_email 错误消息改为中文
-- ----------------------------------------------------------------

create or replace function public.resolve_analyst_by_email(
    p_email text
)
returns public.analyst
language plpgsql stable security definer
as $$
declare
    v_email  text;
    v_record public.analyst%rowtype;
begin
    v_email := lower(trim(p_email));

    select * into v_record
    from public.analyst
    where email = v_email;

    if not found then
        raise exception '找不到分析师：%', p_email;
    end if;

    if not coalesce(v_record.is_active, true) then
        raise exception '分析师已停用：%', p_email;
    end if;

    return v_record;
end;
$$;

comment on function public.resolve_analyst_by_email is
'根据邮箱查询 analyst 记录。自动 lowercase/trim，不存在或 is_active=false 时抛出中文异常。';

-- ----------------------------------------------------------------
-- resolve_coverage
-- ----------------------------------------------------------------

create or replace function public.resolve_coverage(
    p_ticker        text,
    p_analyst_email text
)
returns table(coverage_id uuid)
language plpgsql stable security definer
as $$
declare
    v_ticker text;
    v_email  text;
    v_id     uuid;
begin
    v_ticker := lower(btrim(p_ticker));
    v_email  := lower(btrim(p_analyst_email));

    select c.id into v_id
    from public.coverage c
    join public.coverage_analyst ca on ca.coverage_id = c.id
    where lower(btrim(c.ticker))         = v_ticker
      and lower(btrim(ca.analyst_email)) = v_email;

    if not found then
        raise exception '未找到匹配的 Coverage（ticker=''%''，分析师=''%''）。请先创建 Coverage。',
            p_ticker, p_analyst_email;
    end if;

    return query select v_id;
end;
$$;

comment on function public.resolve_coverage is
'按 ticker + 分析师邮箱查询唯一 coverage。未命中时抛出中文异常，提示创建 Coverage。';

revoke execute on function public.resolve_coverage from public, anon;
grant execute on function public.resolve_coverage to authenticated;

-- ----------------------------------------------------------------
-- create_coverage
-- ----------------------------------------------------------------

create or replace function public.create_coverage(
    p_ticker              text,
    p_english_name        text,
    p_sector_id           uuid,
    p_isin                text,
    p_country_of_domicile text,
    p_analysts            jsonb,
    p_chinese_name        text default null,
    p_traditional_chinese text default null
)
returns table(coverage_id uuid)
language plpgsql security definer
as $$
declare
    v_coverage_id uuid;
    v_analyst     jsonb;
    v_email       text;
    v_order       integer;
begin
    begin
        insert into public.coverage (
            ticker, english_name, chinese_name, traditional_chinese,
            sector_id, isin, country_of_domicile
        ) values (
            p_ticker,
            p_english_name,
            p_chinese_name,
            p_traditional_chinese,
            p_sector_id,
            upper(btrim(p_isin)),
            p_country_of_domicile
        )
        returning id into v_coverage_id;
    exception
        when unique_violation then
            raise exception 'Coverage 已存在：ticker=''%'' 或 isin=''%'' 已被占用。',
                p_ticker, p_isin;
    end;

    for v_analyst in select * from jsonb_array_elements(p_analysts)
    loop
        v_email := lower(btrim(v_analyst->>'analyst_email'));
        v_order := (v_analyst->>'author_order')::integer;

        insert into public.coverage_analyst (coverage_id, analyst_email, author_order)
        values (v_coverage_id, v_email, v_order);
    end loop;

    return query select v_coverage_id;
end;
$$;

comment on function public.create_coverage is
'创建 coverage 及初始 coverage_analyst 关系。ticker/isin 冲突时抛出中文异常。';

revoke execute on function public.create_coverage from public, anon;
grant execute on function public.create_coverage to authenticated;
```

- [ ] **Step 2: 应用迁移**

```bash
cd /mnt/c/_code/neoskills
supabase db reset
```

若不想全量 reset，仅推新迁移：
```bash
supabase migration up
```

- [ ] **Step 3: 验证 RPC 存在且中文错误正常**

```bash
cd /mnt/c/_code/neoskills
uv run python -c "
from skills.neolyst.scripts import connection
client = connection.get_client()
try:
    client.rpc('resolve_coverage', {'p_ticker': 'GHOST', 'p_analyst_email': 'ghost@x.com'}).execute()
except Exception as e:
    print('resolve_coverage 错误（期望含"未找到"）:', e)
try:
    client.rpc('resolve_analyst_by_email', {'p_email': 'ghost@x.com'}).execute()
except Exception as e:
    print('resolve_analyst_by_email 错误（期望含"找不到分析师"）:', e)
print('验证完成')
"
```

Expected: 输出包含 `未找到匹配的 Coverage` 和 `找不到分析师`

---

## Task 2: 实现 coverage.py

**Files:**
- Create: `skills/neolyst/scripts/coverage.py`

- [ ] **Step 1: 创建 coverage.py**

```python
"""
coverage.py — Neolyst coverage 解析与创建接口。

业务逻辑全部在 Supabase RPC 侧实现，本模块只做参数整理和调用。
"""

from supabase import Client


def resolve_coverage(client: Client, ticker: str, first_analyst_email: str) -> str:
    """
    按 ticker + 1作分析师邮箱查询唯一 coverage，返回 coverage_id。

    Args:
        client: 已认证的 Supabase client
        ticker: 股票代码（大小写不敏感）
        first_analyst_email: 报告 1作分析师邮箱（大小写不敏感）

    Returns:
        str: coverage_id（uuid 字符串）

    Raises:
        ValueError: 未命中（提示创建 Coverage）或数据异常
    """
    try:
        resp = client.rpc("resolve_coverage", {
            "p_ticker": ticker,
            "p_analyst_email": first_analyst_email,
        }).execute()
    except Exception as e:
        raise ValueError(str(e)) from e

    return str(resp.data[0]["coverage_id"])


def create_coverage(
    client: Client,
    ticker: str,
    english_name: str,
    sector_id: str,
    isin: str,
    country_of_domicile: str,
    analysts: list[dict],
    chinese_name: str | None = None,
    traditional_chinese: str | None = None,
) -> str:
    """
    创建 coverage 及初始 coverage_analyst 关系，返回新 coverage_id。

    Args:
        client: 已认证的 Supabase client
        ticker: 股票代码
        english_name: 公司英文名
        sector_id: 所属行业 UUID（字符串）
        isin: ISIN 码
        country_of_domicile: 注册国家/地区
        analysts: 分析师列表，格式：[{"analyst_email": "...", "author_order": 1}, ...]
                  author_order=1 代表报告 1作分析师
        chinese_name: 公司中文名（可选）
        traditional_chinese: 公司繁体中文名（可选）

    Returns:
        str: 新建 coverage 的 coverage_id（uuid 字符串）

    Raises:
        ValueError: ticker 或 isin 已存在等创建失败场景
    """
    try:
        resp = client.rpc("create_coverage", {
            "p_ticker": ticker,
            "p_english_name": english_name,
            "p_sector_id": sector_id,
            "p_isin": isin,
            "p_country_of_domicile": country_of_domicile,
            "p_analysts": analysts,
            "p_chinese_name": chinese_name,
            "p_traditional_chinese": traditional_chinese,
        }).execute()
    except Exception as e:
        raise ValueError(str(e)) from e

    return str(resp.data[0]["coverage_id"])
```

- [ ] **Step 2: 验证 import**

```bash
cd /mnt/c/_code/neoskills
uv run python -c "from skills.neolyst.scripts import coverage; print('OK')"
```

Expected: `OK`

---

## Task 3: 补丁 analyst.py — 英文兜底错误消息改为中文

**Files:**
- Modify: `skills/neolyst/scripts/analyst.py`

- [ ] **Step 1: 修改 analyst.py 中的英文错误消息**

将 `if not resp.data` 分支的错误消息从 `"Analyst not found: {email!r}"` 改为中文：

```python
"""
analyst.py — Neolyst analyst 查询模块。
"""

from supabase import Client


def resolve_analyst_by_email(client: Client, email: str) -> dict:
    """
    根据邮箱查询并返回标准化的 analyst 记录。

    业务主键为 analyst_email（表中强制小写存储）。
    is_active 校验在 Supabase RPC 侧执行。

    Args:
        client: 已认证的 Supabase client
        email: 分析师邮箱（大小写不敏感）

    Returns:
        dict: analyst 记录，含 email, english_name, chinese_name, suffix,
              sfc, region_code, is_active, created_at, updated_at 字段

    Raises:
        ValueError: 找不到对应的 analyst，或 analyst 已停用（is_active=False）
    """
    try:
        resp = client.rpc("resolve_analyst_by_email", {"p_email": email}).execute()
    except Exception as e:
        raise ValueError(str(e)) from e

    if not resp.data:
        raise ValueError(f"找不到分析师：{email!r}")

    return resp.data
```

- [ ] **Step 2: 验证 import**

```bash
uv run python -c "from skills.neolyst.scripts import analyst; print('OK')"
```

Expected: `OK`

---

## Task 4: 集成测试

**Files:**
- Create: `skills/neolyst/tests/test_coverage.py`

- [ ] **Step 1: 创建 test_coverage.py**

```python
"""
test_coverage.py — coverage 接口集成测试。
"""
import uuid
import pytest

_SUFFIX = uuid.uuid4().hex[:8]
TEST_TICKER = f"TEST{_SUFFIX[:4].upper()}"
TEST_ISIN = f"US{_SUFFIX.upper()[:10]}"
TEST_ANALYST = "yangxue@opendelp.com"


@pytest.fixture(scope="module")
def test_sector_id(neolyst_client):
    """获取第一个可用的 sector id（测试用）。"""
    resp = neolyst_client.table("sector").select("id").eq("is_active", True).limit(1).execute()
    assert resp.data, "需要至少一条 sector 记录，请先运行 supabase db reset"
    return resp.data[0]["id"]


@pytest.fixture(scope="module")
def created_coverage_id(neolyst_client, test_sector_id):
    """
    创建测试用 coverage，模块结束后删除（coverage_analyst 随 coverage 级联删除）。
    """
    from skills.neolyst.scripts import coverage as cov
    coverage_id = cov.create_coverage(
        neolyst_client,
        ticker=TEST_TICKER,
        english_name="Test Coverage Company",
        sector_id=test_sector_id,
        isin=TEST_ISIN,
        country_of_domicile="China",
        analysts=[{"analyst_email": TEST_ANALYST, "author_order": 1}],
    )
    yield coverage_id
    neolyst_client.table("coverage").delete().eq("id", coverage_id).execute()


class TestCreateCoverage:
    def test_create_success_returns_uuid(self, neolyst_client, created_coverage_id):
        """create_coverage 返回非空的 coverage_id uuid 字符串。"""
        assert created_coverage_id
        uuid.UUID(created_coverage_id)  # 格式校验：合法 UUID 不抛异常

    def test_create_coverage_record_exists(self, neolyst_client, created_coverage_id):
        """coverage 表中有对应记录，核心字段正确。"""
        resp = (
            neolyst_client.table("coverage")
            .select("*")
            .eq("id", created_coverage_id)
            .execute()
        )
        assert resp.data
        record = resp.data[0]
        assert record["english_name"] == "Test Coverage Company"
        assert record["country_of_domicile"] == "China"
        assert record["isin"] == TEST_ISIN.upper()

    def test_create_coverage_analyst_record_exists(self, neolyst_client, created_coverage_id):
        """coverage_analyst 表中有对应分析师记录，author_order=1。"""
        resp = (
            neolyst_client.table("coverage_analyst")
            .select("*")
            .eq("coverage_id", created_coverage_id)
            .execute()
        )
        assert len(resp.data) == 1
        assert resp.data[0]["analyst_email"] == TEST_ANALYST
        assert resp.data[0]["author_order"] == 1

    def test_create_duplicate_ticker_raises(self, neolyst_client, test_sector_id, created_coverage_id):
        """ticker 重复时抛出含"已存在"的 ValueError。"""
        from skills.neolyst.scripts import coverage as cov
        with pytest.raises(ValueError, match="已存在"):
            cov.create_coverage(
                neolyst_client,
                ticker=TEST_TICKER,
                english_name="Duplicate Ticker Company",
                sector_id=test_sector_id,
                isin=f"US{uuid.uuid4().hex[:10].upper()}",
                country_of_domicile="China",
                analysts=[{"analyst_email": TEST_ANALYST, "author_order": 1}],
            )

    def test_create_duplicate_isin_raises(self, neolyst_client, test_sector_id, created_coverage_id):
        """ISIN 重复时抛出含"已存在"的 ValueError。"""
        from skills.neolyst.scripts import coverage as cov
        with pytest.raises(ValueError, match="已存在"):
            cov.create_coverage(
                neolyst_client,
                ticker=f"DUP{uuid.uuid4().hex[:4].upper()}",
                english_name="Duplicate ISIN Company",
                sector_id=test_sector_id,
                isin=TEST_ISIN,
                country_of_domicile="China",
                analysts=[{"analyst_email": TEST_ANALYST, "author_order": 1}],
            )


class TestResolveCoverage:
    def test_resolve_found(self, neolyst_client, created_coverage_id):
        """ticker + 分析师匹配时返回正确的 coverage_id。"""
        from skills.neolyst.scripts import coverage as cov
        result = cov.resolve_coverage(neolyst_client, TEST_TICKER, TEST_ANALYST)
        assert result == created_coverage_id

    def test_resolve_case_insensitive_ticker(self, neolyst_client, created_coverage_id):
        """ticker 大小写不敏感，小写 ticker 同样命中。"""
        from skills.neolyst.scripts import coverage as cov
        result = cov.resolve_coverage(neolyst_client, TEST_TICKER.lower(), TEST_ANALYST)
        assert result == created_coverage_id

    def test_resolve_case_insensitive_email(self, neolyst_client, created_coverage_id):
        """analyst_email 大小写不敏感，大写 email 同样命中。"""
        from skills.neolyst.scripts import coverage as cov
        result = cov.resolve_coverage(neolyst_client, TEST_TICKER, TEST_ANALYST.upper())
        assert result == created_coverage_id

    def test_resolve_not_found_ticker_raises(self, neolyst_client):
        """ticker 不存在时抛出含"未找到"的 ValueError。"""
        from skills.neolyst.scripts import coverage as cov
        with pytest.raises(ValueError, match="未找到"):
            cov.resolve_coverage(neolyst_client, "GHOST_TICKER_99", TEST_ANALYST)

    def test_resolve_analyst_not_in_coverage_raises(self, neolyst_client, created_coverage_id):
        """ticker 存在但分析师不在 coverage_analyst 列表中时抛出含"未找到"的 ValueError。"""
        from skills.neolyst.scripts import coverage as cov
        with pytest.raises(ValueError, match="未找到"):
            cov.resolve_coverage(neolyst_client, TEST_TICKER, "nobody@example.com")
```

- [ ] **Step 2: 运行 coverage 测试**

```bash
cd /mnt/c/_code/neoskills
NEOLYST_URL=http://127.0.0.1:54321 uv run --with pytest pytest skills/neolyst/tests/test_coverage.py -v
```

Expected: 10 tests PASSED

- [ ] **Step 3: 全量测试**

```bash
NEOLYST_URL=http://127.0.0.1:54321 uv run --with pytest pytest skills/neolyst/tests/ -v
```

Expected: 全部通过（含 iter1 + iter2 的 16 个已有测试，合计 26 个）

- [ ] **Step 4: Commit**

```bash
git add \
    supabase/migrations/20260409000630_060_coverage_functions.sql \
    skills/neolyst/scripts/coverage.py \
    skills/neolyst/scripts/analyst.py \
    skills/neolyst/tests/test_coverage.py
git commit -m "feat: add coverage module with resolve/create RPC, update error messages to Chinese"
```

---

## Task 5: 更新文档和路线图

**Files:**
- Modify: `plans/2026-04-07-neolyst-skill-roadmap.md`

- [ ] **Step 1: 标记 Iter 3 完成**

将 `plans/2026-04-07-neolyst-skill-roadmap.md` 中：

```
| Iter 3 | coverage | 未开始 | — |
```

改为：

```
| Iter 3 | coverage | 已完成 | [2026-04-09-neolyst-iter3.md](2026-04-09-neolyst-iter3.md) |
```

- [ ] **Step 2: 检查设计文档**

确认 `docs/skills_neolyst_design.md` 中 coverage 相关章节（2.9、3.1、3.2）与实现一致。本迭代未改变接口契约，无需更新设计文档。

- [ ] **Step 3: Commit**

```bash
git add plans/2026-04-07-neolyst-skill-roadmap.md
git commit -m "docs: mark iter3 complete, update roadmap"
```

---

## 自检

- [ ] 迁移文件包含：`resolve_coverage`、`create_coverage` 两个 RPC，`resolve_analyst_by_email` 中文错误补丁
- [ ] 所有 RPC 错误消息为中文
- [ ] `coverage.py`：两个函数，无业务逻辑，失败时包装为 `ValueError`
- [ ] `analyst.py`：Python 侧英文兜底错误消息已改为中文
- [ ] 10 个集成测试通过（含大小写不敏感测试、错误场景测试）
- [ ] 全量 26 个测试通过
- [ ] roadmap Iter 3 标记已完成
