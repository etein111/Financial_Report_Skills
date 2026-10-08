# Neolyst Iter 6: coverage history 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 `neolyst` 增加 Coverage 历史查询能力，输入 `ticker + first_analyst_email`，返回该 coverage 下所有已发布报告的 `report_id`、`title`、`rating`、`target_price`、`published_at`。

**Architecture:**  
- **Supabase 侧**：新增 `list_coverage_history` RPC，内部先复用现有 `resolve_coverage` 解析唯一 coverage，再查询 `report.status = 'published'` 的历史记录并按 `published_at desc` 返回。  
- **Python 侧**：在 `skills/neolyst/scripts/coverage.py` 增加同名薄封装函数，只负责传参、调用 RPC、包装异常。  
- **测试与文档**：补充 coverage 集成测试；在 `SKILL.md` 增加接口说明；在设计文档末尾追加补充章节；在 roadmap 中插入新的 Iter 6 并将收尾顺延。

**Tech Stack:** Python 3.12+, supabase-py, PostgreSQL RPC, pytest, uuid

**已确认的设计决策：**
- 对外接口入参固定为 `ticker + first_analyst_email`
- coverage 解析沿用现有 `resolve_coverage` 逻辑，不新增第二套判定规则
- 只返回 `status = 'published'` 的历史报告
- 返回字段固定为 `report_id`、`title`、`rating`、`target_price`、`published_at`
- 结果按 `published_at desc` 排序，不做分页、不加 limit
- coverage 已找到但没有 published 历史时返回空列表，不报错
- 设计文档只在末尾追加补充章节，不修改前文内容

---

## 文件结构

| 文件 | 操作 | 说明 |
|------|------|------|
| `supabase/migrations/20260410000200_090_coverage_history_function.sql` | 新建 | `list_coverage_history` RPC |
| `skills/neolyst/scripts/coverage.py` | 修改 | 新增 `list_coverage_history` Python 接口 |
| `skills/neolyst/tests/test_coverage.py` | 修改 | 增加 Coverage 历史查询集成测试 |
| `skills/neolyst/SKILL.md` | 修改 | 增加 Coverage 历史查询接口说明 |
| `docs/skills_neolyst_design.md` | 修改 | 在末尾追加补充章节 |
| `plans/2026-04-07-neolyst-skill-roadmap.md` | 修改 | 插入新的 Iter 6，原收尾顺延为 Iter 7 |

## 背景与约束

- 现有 `resolve_coverage` RPC 已按 `ticker + coverage_analyst.analyst_email` 定位 coverage，当前实现会对 `ticker` 和邮箱做 `lower(btrim(...))`
- `report` 表已有字段：`id`、`title`、`status`、`coverage_id`、`rating`、`target_price`、`published_at`
- `published_at` 仅在 `submitted -> published` 时记录，因此“历史评级/目标价/发布日期”语义只对 `published` 成立
- 按 `AGENTS.md`，带业务判定的读取优先放在 Supabase 侧实现；Python 只做参数整理和调用
- 文档约束：`docs/skills_neolyst_design.md` 只能在最后追加补充章节，不能改前文结构

## Task 1: 先写 coverage history 集成测试

**Files:**
- Modify: `skills/neolyst/tests/test_coverage.py`

- [ ] **Step 1: 在 `test_coverage.py` 中加入新 fixture 和测试类**

```python
@pytest.fixture(scope="module")
def history_coverage_id(neolyst_client, test_sector_id):
    from skills.neolyst.scripts import coverage as cov

    suffix = uuid.uuid4().hex[:6].upper()
    coverage_id = cov.create_coverage(
        neolyst_client,
        ticker=f"HIS{suffix}",
        english_name=f"History Coverage {suffix}",
        sector_id=test_sector_id,
        isin=f"US{suffix}{'0' * (10 - len(suffix))}",
        country_of_domicile="United States",
        analysts=[{"analyst_email": TEST_ANALYST, "author_order": 1}],
    )
    yield coverage_id
    neolyst_client.table("coverage").delete().eq("id", coverage_id).execute()


@pytest.fixture(scope="module")
def history_report_rows(neolyst_client, history_coverage_id):
    user = neolyst_client.auth.get_user().user
    rows = [
        {
            "id": str(uuid.uuid4()),
            "title": "Newest Published Report",
            "report_type": "company",
            "status": "published",
            "current_version_no": 1,
            "owner_user_id": user.id,
            "coverage_id": history_coverage_id,
            "ticker": "IGNORED",
            "rating": "OUTPERFORM",
            "target_price": 120,
            "report_language": "en",
            "published_by": user.id,
            "published_at": "2026-04-09T08:00:00+00:00",
        },
        {
            "id": str(uuid.uuid4()),
            "title": "Older Published Report",
            "report_type": "company",
            "status": "published",
            "current_version_no": 1,
            "owner_user_id": user.id,
            "coverage_id": history_coverage_id,
            "ticker": "IGNORED",
            "rating": "NEUTRAL",
            "target_price": 98,
            "report_language": "en",
            "published_by": user.id,
            "published_at": "2026-03-31T08:00:00+00:00",
        },
        {
            "id": str(uuid.uuid4()),
            "title": "Submitted Report Should Be Hidden",
            "report_type": "company",
            "status": "submitted",
            "current_version_no": 1,
            "owner_user_id": user.id,
            "coverage_id": history_coverage_id,
            "ticker": "IGNORED",
            "rating": "UNDERPERFORM",
            "target_price": 80,
            "report_language": "en",
            "published_at": None,
        },
    ]
    neolyst_client.table("report").insert(rows).execute()
    yield rows
    for row in rows:
        neolyst_client.table("report").delete().eq("id", row["id"]).execute()


class TestListCoverageHistory:
    def test_returns_only_published_rows(self, neolyst_client, history_coverage_id, history_report_rows):
        from skills.neolyst.scripts import coverage as cov

        result = cov.list_coverage_history(
            neolyst_client,
            ticker=f"HIS",
            first_analyst_email=TEST_ANALYST,
        )

        assert len(result) == 2
        assert [row["title"] for row in result] == [
            "Newest Published Report",
            "Older Published Report",
        ]

    def test_returns_expected_five_fields(self, neolyst_client, history_coverage_id, history_report_rows):
        from skills.neolyst.scripts import coverage as cov

        result = cov.list_coverage_history(neolyst_client, ticker="placeholder", first_analyst_email=TEST_ANALYST)
        assert set(result[0].keys()) == {
            "report_id",
            "title",
            "rating",
            "target_price",
            "published_at",
        }

    def test_case_insensitive_inputs(self, neolyst_client, history_report_rows):
        from skills.neolyst.scripts import coverage as cov

        result = cov.list_coverage_history(
            neolyst_client,
            ticker=history_report_rows[0]["ticker"].lower(),
            first_analyst_email=TEST_ANALYST.upper(),
        )
        assert result[0]["title"] == "Newest Published Report"

    def test_returns_empty_list_when_no_published_history(self, neolyst_client, created_coverage_id):
        from skills.neolyst.scripts import coverage as cov

        result = cov.list_coverage_history(neolyst_client, TEST_TICKER, TEST_ANALYST)
        assert result == []

    def test_missing_coverage_raises(self, neolyst_client):
        from skills.neolyst.scripts import coverage as cov

        with pytest.raises(ValueError, match="未找到匹配的 Coverage"):
            cov.list_coverage_history(neolyst_client, "GHOST_TICKER_99", TEST_ANALYST)
```

- [ ] **Step 2: 修正 fixture，确保测试 ticker 使用真实创建值**

```python
@pytest.fixture(scope="module")
def history_dataset(neolyst_client, history_coverage_id):
    user = neolyst_client.auth.get_user().user
    ticker = f"HIS{uuid.uuid4().hex[:6].upper()}"

    neolyst_client.table("coverage").update({"ticker": ticker}).eq("id", history_coverage_id).execute()

    rows = [
        {
            "id": str(uuid.uuid4()),
            "title": "Newest Published Report",
            "report_type": "company",
            "status": "published",
            "current_version_no": 1,
            "owner_user_id": user.id,
            "coverage_id": history_coverage_id,
            "ticker": ticker,
            "rating": "OUTPERFORM",
            "target_price": 120,
            "report_language": "en",
            "published_by": user.id,
            "published_at": "2026-04-09T08:00:00+00:00",
        },
        {
            "id": str(uuid.uuid4()),
            "title": "Older Published Report",
            "report_type": "company",
            "status": "published",
            "current_version_no": 1,
            "owner_user_id": user.id,
            "coverage_id": history_coverage_id,
            "ticker": ticker,
            "rating": "NEUTRAL",
            "target_price": 98,
            "report_language": "en",
            "published_by": user.id,
            "published_at": "2026-03-31T08:00:00+00:00",
        },
        {
            "id": str(uuid.uuid4()),
            "title": "Submitted Report Should Be Hidden",
            "report_type": "company",
            "status": "submitted",
            "current_version_no": 1,
            "owner_user_id": user.id,
            "coverage_id": history_coverage_id,
            "ticker": ticker,
            "rating": "UNDERPERFORM",
            "target_price": 80,
            "report_language": "en",
            "published_at": None,
        },
    ]
    neolyst_client.table("report").insert(rows).execute()
    yield {"ticker": ticker, "rows": rows}
    for row in rows:
        neolyst_client.table("report").delete().eq("id", row["id"]).execute()
```

- [ ] **Step 3: 用 `history_dataset` 替换前一版占位调用**

```python
class TestListCoverageHistory:
    def test_returns_only_published_rows(self, neolyst_client, history_dataset):
        from skills.neolyst.scripts import coverage as cov

        result = cov.list_coverage_history(
            neolyst_client,
            ticker=history_dataset["ticker"],
            first_analyst_email=TEST_ANALYST,
        )

        assert len(result) == 2
        assert [row["title"] for row in result] == [
            "Newest Published Report",
            "Older Published Report",
        ]

    def test_returns_expected_five_fields(self, neolyst_client, history_dataset):
        from skills.neolyst.scripts import coverage as cov

        result = cov.list_coverage_history(
            neolyst_client,
            ticker=history_dataset["ticker"],
            first_analyst_email=TEST_ANALYST,
        )
        assert set(result[0].keys()) == {
            "report_id",
            "title",
            "rating",
            "target_price",
            "published_at",
        }

    def test_case_insensitive_inputs(self, neolyst_client, history_dataset):
        from skills.neolyst.scripts import coverage as cov

        result = cov.list_coverage_history(
            neolyst_client,
            ticker=history_dataset["ticker"].lower(),
            first_analyst_email=TEST_ANALYST.upper(),
        )
        assert result[0]["title"] == "Newest Published Report"
```

- [ ] **Step 4: 跑测试，确认先失败在“函数不存在”**

Run: `uv run pytest skills/neolyst/tests/test_coverage.py -k coverage_history -q`  
Expected: FAIL，报 `AttributeError: module 'skills.neolyst.scripts.coverage' has no attribute 'list_coverage_history'`

- [x] **Step 5: Commit**

```bash
git add skills/neolyst/tests/test_coverage.py
git commit -m "test: add coverage history integration cases"
```

## Task 2: 增加 Python 薄封装接口

**Files:**
- Modify: `skills/neolyst/scripts/coverage.py`

- [ ] **Step 1: 在 `coverage.py` 中新增最小实现**

```python
def list_coverage_history(
    client: Client,
    ticker: str,
    first_analyst_email: str,
) -> list[dict]:
    """
    按 ticker + 1作分析师邮箱查询 coverage 的已发布历史。

    Returns:
        list[dict]: 每项含 report_id/title/rating/target_price/published_at
    """
    try:
        resp = client.rpc("list_coverage_history", {
            "p_ticker": ticker,
            "p_analyst_email": first_analyst_email,
        }).execute()
    except Exception as e:
        raise ValueError(str(e)) from e

    rows = resp.data or []
    return [
        {
            "report_id": str(row["report_id"]),
            "title": row["title"],
            "rating": row["rating"],
            "target_price": row["target_price"],
            "published_at": row["published_at"],
        }
        for row in rows
    ]
```

- [ ] **Step 2: 跑测试，确认失败点前移为 “RPC 不存在”**

Run: `uv run pytest skills/neolyst/tests/test_coverage.py -k coverage_history -q`  
Expected: FAIL，错误中包含 `Could not find the function public.list_coverage_history`

- [x] **Step 3: Commit**

```bash
git add skills/neolyst/scripts/coverage.py
git commit -m "feat: add coverage history python wrapper"
```

## Task 3: 实现 Supabase RPC 并让测试转绿

**Files:**
- Create: `supabase/migrations/20260410000200_090_coverage_history_function.sql`

- [ ] **Step 1: 创建迁移文件**

```sql
-- 20260410000200_090_coverage_history_function.sql
-- coverage 历史查询 RPC：先 resolve_coverage，再返回 published 历史

create or replace function public.list_coverage_history(
    p_ticker text,
    p_analyst_email text
)
returns table(
    report_id uuid,
    title text,
    rating text,
    target_price numeric,
    published_at timestamp with time zone
)
language plpgsql stable security definer
as $$
declare
    v_coverage_id uuid;
begin
    select rc.coverage_id
    into v_coverage_id
    from public.resolve_coverage(p_ticker, p_analyst_email) rc;

    return query
    select
        r.id as report_id,
        r.title,
        r.rating,
        r.target_price,
        r.published_at
    from public.report r
    where r.coverage_id = v_coverage_id
      and r.status = 'published'
    order by r.published_at desc nulls last, r.id desc;
end;
$$;

comment on function public.list_coverage_history is
'按 ticker + 1作分析师邮箱定位 coverage，并返回该 coverage 的已发布历史报告。只返回 report_id/title/rating/target_price/published_at；coverage 已找到但无历史时返回空列表。';

revoke execute on function public.list_coverage_history from public, anon;
grant execute on function public.list_coverage_history to authenticated;
```

- [ ] **Step 2: 应用迁移**

Run: `pnpm exec supabase db reset`  
Expected: 末尾输出 `Finished supabase db reset`，无 ERROR

- [ ] **Step 3: 直接验证 RPC 行为**

Run:

```bash
uv run python -c "
from skills.neolyst.scripts import connection, coverage
client = connection.get_client()
try:
    coverage.list_coverage_history(client, 'GHOST_TICKER_99', 'ghost@example.com')
except Exception as e:
    print(str(e))
"
```

Expected: 输出包含 `未找到匹配的 Coverage`

- [ ] **Step 4: 跑 coverage 测试，确认全部通过**

Run: `uv run pytest skills/neolyst/tests/test_coverage.py -q`  
Expected: PASS，包含新增 coverage history 用例

- [x] **Step 5: Commit**

```bash
git add supabase/migrations/20260410000200_090_coverage_history_function.sql
git commit -m "feat: add coverage history rpc"
```

## Task 4: 更新 SKILL 文档、设计补充和 roadmap

**Files:**
- Modify: `skills/neolyst/SKILL.md`
- Modify: `docs/skills_neolyst_design.md`
- Modify: `plans/2026-04-07-neolyst-skill-roadmap.md`

- [ ] **Step 1: 在 `skills/neolyst/SKILL.md` 追加新接口说明**

```md
### 7. list_coverage_history ✅ 已实现

按 `ticker + first_analyst_email` 定位唯一 coverage，并返回该 coverage 的已发布历史报告。

```python
from skills.neolyst.scripts import coverage

rows = coverage.list_coverage_history(
    client,
    ticker="VRT US",
    first_analyst_email="alice@neolyst.com",
)
# 返回：
# [
#   {
#     "report_id": "uuid",
#     "title": "Vertiv: AI demand drives earnings growth",
#     "rating": "OUTPERFORM",
#     "target_price": 140,
#     "published_at": "2026-04-09T08:00:00+00:00",
#   }
# ]
# coverage 找不到：抛出 ValueError
# coverage 找到但没有已发布历史：返回 []
```
```

- [ ] **Step 2: 在设计文档末尾追加补充章节，不改前文**

```md
## 补充：Coverage 历史查询

- 新增 `list_coverage_history(ticker, first_analyst_email)` 能力，面向“报告尚未写完、只有 ticker 和 1 作信息”的前置查询场景。
- coverage 的定位逻辑沿用现有 `resolve_coverage`：按 `ticker + coverage_analyst.analyst_email` 命中唯一 coverage。
- 只返回 `status = 'published'` 的历史报告；`submitted`、`draft`、`rejected` 均不纳入结果。
- 返回字段固定为：`report_id`、`title`、`rating`、`target_price`、`published_at`。
- 结果按 `published_at desc` 排序。
- coverage 已找到但没有历史发布记录时返回空列表，不抛错。
- 该读取带业务判定，按仓库约定下沉到 Supabase RPC；Python 侧只做参数整理和调用。
```

- [ ] **Step 3: 在 roadmap 中插入新的 Iter 6，并将原收尾顺延**

```md
| Iter 5 | validators + submit | 已完成 | [2026-04-10-neolyst-iter5.md](2026-04-10-neolyst-iter5.md) |
| Iter 6 | coverage history | 进行中 | [2026-04-10-neolyst-iter6.md](2026-04-10-neolyst-iter6.md) |
| Iter 7 | 收尾 | 未开始 | — |
```

- [ ] **Step 4: 跑最小验证，确认文档引用和计划链接可打开**

Run: `rg -n "coverage history|Iter 6|list_coverage_history" skills/neolyst/SKILL.md docs/skills_neolyst_design.md plans/2026-04-07-neolyst-skill-roadmap.md plans/2026-04-10-neolyst-iter6.md`  
Expected: 4 个文件中都能命中新接口或新迭代描述

- [x] **Step 5: Commit**

```bash
git add skills/neolyst/SKILL.md docs/skills_neolyst_design.md plans/2026-04-07-neolyst-skill-roadmap.md plans/2026-04-10-neolyst-iter6.md
git commit -m "docs: add coverage history iteration plan and contract"
```

## Task 5: 完整回归与交付检查

**Files:**
- Modify: `plans/2026-04-10-neolyst-iter6.md`

- [x] **Step 1: 跑目标测试**

Run: `uv run pytest skills/neolyst/tests/test_coverage.py -q`  
Expected: PASS

- [x] **Step 2: 跑 `neolyst` 核心测试集，确认没有破坏已实现能力**

Run: `uv run pytest skills/neolyst/tests -q`  
Expected: PASS（58 passed）

- [x] **Step 3: 回填本计划的 checkbox，并记录实际补丁**

实际补丁：
- SQL 函数去掉 `SECURITY DEFINER`（改为默认 INVOKER）
- 新增 RLS policy `report_select_published`，允许 `analyst` 读取所有 `published` 报告（方案 B）
- SKILL.md 中接口编号为 10（原计划 7，因 Iter 4/5 已占用 7-9）

- [x] **Step 4: Commit**

```bash
git add plans/2026-04-10-neolyst-iter6.md
git commit -m "docs: mark coverage history iteration complete"
```
