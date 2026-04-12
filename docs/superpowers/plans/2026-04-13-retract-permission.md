# 收紧 submitted 权限 + 增加撤回路径 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 收紧 analyst 在 submitted 状态下的 UPDATE/INSERT/Storage 权限，新增 submitted/rejected → draft 撤回路径和 `retract_report` RPC。

**Architecture:** 单个 SQL 迁移文件，修改 5 个 RLS policy + 1 个状态校验函数 + 新增 1 个 RPC。RLS 采用非对称策略：report_update USING 允许 draft/submitted/rejected（让 retract RPC 能找到行），WITH CHECK 限制为 draft only（阻止 analyst 在保持 submitted 状态下修改报告）。

**Tech Stack:** PostgreSQL / Supabase RLS / PL/pgSQL / Python (Supabase-py)

---

### Task 1: 创建迁移文件

**Files:**
- Create: `supabase/migrations/20260413000100_110_retract_permission.sql`

- [ ] **Step 1: 写迁移 SQL**

```sql
-- 20260413000100_110_retract_permission.sql
-- P0: 收紧 submitted 权限 + 增加 submitted/rejected → draft 撤回路径
--
-- 变更清单：
--   1. report_status_is_valid：新增 submitted → draft 路径
--   2. report_update RLS：非对称策略（USING 允许 draft/submitted/rejected，
--      WITH CHECK 限制 draft only）
--   3. rv_insert RLS：analyst 仅 draft 可插入版本
--   4. reports bucket INSERT/UPDATE RLS：analyst 仅 draft 可上传/修改文件
--   5. rsl_insert RLS：analyst 增加 submitted→draft、rejected→draft
--   6. 新增 retract_report RPC

-- ===================================================================
-- 1. report_status_is_valid：新增 submitted → draft (retract) 路径
-- ===================================================================

create or replace function public.report_status_is_valid(from_status text, to_status text)
returns boolean
language sql
immutable
as $$
    select (from_status = 'draft' and to_status = 'submitted')
        or (from_status = 'submitted' and to_status in ('published', 'rejected', 'draft'))
        or (from_status = 'rejected' and to_status in ('draft', 'submitted'))
$$;

comment on function public.report_status_is_valid(text, text) is
'判断报告状态流转是否合法（IMMUTABLE）。

合法路径：
  draft → submitted          （analyst 提交审阅）
  submitted → published      （sa 发布）
  submitted → rejected       （sa 退回）
  submitted → draft          （analyst 撤回，由 retract_report RPC 调用）
  rejected → draft           （analyst 撤回，由 retract_report RPC 调用）
  rejected → submitted       （analyst 重新提交）

所有其他路径均为非法，report_enforce_status_transition 触发器会在
UPDATE report 时调用本函数进行校验，非法流转将抛出异常。';

-- ===================================================================
-- 2. report_update RLS：非对称策略
--    USING:   analyst 可见 draft / submitted / rejected 行
--             → retract_report RPC 需要找到 submitted/rejected 行才能更新
--    WITH CHECK: analyst 更新后状态必须为 draft
--             → analyst 无法在保持 submitted 状态下修改任何字段
--             → analyst 无法通过直接 UPDATE 提交报告（必须走 submit_report RPC）
-- ===================================================================

drop policy if exists report_update on public.report;

create policy report_update
on public.report
for update
to authenticated
using (
    (public.current_app_role() = 'admin'::text)
    or (
        (public.current_app_role() = 'analyst'::text)
        and (owner_user_id = auth.uid())
        and (status = any (array['draft'::text, 'submitted'::text, 'rejected'::text]))
    )
)
with check (
    (public.current_app_role() = 'admin'::text)
    or (
        (public.current_app_role() = 'analyst'::text)
        and (owner_user_id = auth.uid())
        and (status = 'draft'::text)
    )
);

-- ===================================================================
-- 3. rv_insert RLS：analyst 仅可在 draft 状态下插入 report_version
--    收紧前：draft / submitted 均可插入
--    收紧后：仅 draft 可插入
-- ===================================================================

drop policy if exists rv_insert on public.report_version;

create policy rv_insert
on public.report_version
for insert
to authenticated
with check (
    exists (
        select 1
        from public.report r
        where r.id = report_version.report_id
          and (
              (public.current_app_role() = 'admin'::text)
              or (
                  (public.current_app_role() = 'analyst'::text)
                  and (r.owner_user_id = auth.uid())
                  and (r.status = 'draft'::text)
              )
          )
    )
);

-- ===================================================================
-- 4. reports bucket INSERT/UPDATE RLS：analyst 仅可在 draft 状态下上传/修改文件
--    收紧前：draft / submitted 均可上传
--    收紧后：仅 draft 可上传
-- ===================================================================

drop policy if exists reports_insert on storage.objects;

create policy reports_insert
on storage.objects
for insert
to authenticated
with check (
    bucket_id = 'reports'
    and (
        public.current_app_role() = 'admin'::text
        or exists (
            select 1
            from public.report r
            where
                r.id::text = split_part(name, '/', 1)
                and public.current_app_role() = 'analyst'::text
                and r.owner_user_id = auth.uid()
                and r.status = 'draft'::text
        )
    )
);

drop policy if exists reports_update on storage.objects;

create policy reports_update
on storage.objects
for update
to authenticated
using (
    bucket_id = 'reports'
    and (
        public.current_app_role() = 'admin'::text
        or exists (
            select 1
            from public.report r
            where
                r.id::text = split_part(name, '/', 1)
                and public.current_app_role() = 'analyst'::text
                and r.owner_user_id = auth.uid()
                and r.status = 'draft'::text
        )
    )
);

-- ===================================================================
-- 5. rsl_insert RLS：analyst 增加 submitted→draft、rejected→draft
--    收紧前：analyst 仅 draft→submitted
--    收紧后：analyst 可 draft→submitted / submitted→draft / rejected→draft
-- ===================================================================

drop policy if exists rsl_insert on public.report_status_log;

create policy rsl_insert
on public.report_status_log
for insert
to authenticated
with check (
    (public.current_app_role() = 'admin'::text)
    or (
        (public.current_app_role() = 'sa'::text)
        and (from_status = any (array['submitted'::text, 'rejected'::text]))
    )
    or (
        (public.current_app_role() = 'analyst'::text)
        and (
            (from_status = 'draft'::text and to_status = 'submitted'::text)
            or (from_status = 'submitted'::text and to_status = 'draft'::text)
            or (from_status = 'rejected'::text and to_status = 'draft'::text)
        )
        and exists (
            select 1
            from public.report r
            where r.id = report_status_log.report_id
              and r.owner_user_id = auth.uid()
        )
    )
);

-- ===================================================================
-- 6. retract_report RPC：analyst 将 submitted/rejected 报告撤回为 draft
-- ===================================================================

create or replace function public.retract_report(
    p_report_id uuid
)
returns table(report_id uuid, version_no integer, status text)
language plpgsql
as $$
declare
    v_current_status     text;
    v_current_version_no integer;
    v_action_email       text;
begin
    -- 查询报告当前状态和版本号
    select r.status, r.current_version_no
      into v_current_status, v_current_version_no
    from public.report r
    where r.id = p_report_id;

    if not found then
        raise exception '报告不存在: %', p_report_id;
    end if;

    -- 仅 submitted / rejected 可撤回
    if v_current_status not in ('submitted', 'rejected') then
        raise exception '报告状态为 %，无法撤回（仅 submitted/rejected 可撤回）', v_current_status;
    end if;

    v_action_email := auth.jwt() ->> 'email';

    -- 更新状态为 draft（依赖 report_update RLS 的 USING 子句匹配 submitted/rejected 行，
    -- WITH CHECK 要求新状态为 draft，恰好满足）
    update public.report
    set status = 'draft'
    where id = p_report_id;

    -- 写入状态流转日志
    insert into public.report_status_log (
        report_id, from_status, to_status,
        action_by, action_by_name, version_no
    ) values (
        p_report_id, v_current_status, 'draft',
        auth.uid(), v_action_email, v_current_version_no
    );

    return query
        select p_report_id, v_current_version_no, 'draft'::text;
end;
$$;

comment on function public.retract_report is
'将 submitted/rejected 状态的报告撤回为 draft。

权限：仅 analyst 且 report.owner_user_id = auth.uid() 可调用。
      admin 无此需求（admin 可直接 UPDATE）。

校验流程：
  1. 报告必须存在
  2. 当前状态必须为 submitted 或 rejected
  3. 状态流转合法性由 report_status_is_valid + trg_report_status_transition 保证
  4. RLS report_update 的 USING 允许 analyst 找到 submitted/rejected 行
  5. RLS report_update 的 WITH CHECK 要求更新后 status = draft

原子操作：
  UPDATE report.status → INSERT report_status_log，在同一事务内完成。
  任一步失败则整体回滚。

返回：report_id, version_no（撤回时的版本号）, status（固定为 draft）。

依赖：
  - report_status_is_valid 函数（已新增 submitted→draft 路径）
  - report_update RLS（非对称策略，USING 含 submitted/rejected）
  - rsl_insert RLS（已新增 analyst submitted→draft / rejected→draft）';

revoke execute on function public.retract_report from public, anon;
grant execute on function public.retract_report to authenticated;
```

- [ ] **Step 2: 检查 SQL 语法**

Run: `cd /mnt/c/_code/neoskills && cat supabase/migrations/20260413000100_110_retract_permission.sql | head -5`
Expected: 文件头部显示正确的注释

- [ ] **Step 3: 本地验证（如果 supabase 可用）**

Run: `cd /mnt/c/_code/neoskills && npx supabase db reset`
Expected: 所有迁移成功执行，无报错

然后运行验证查询：

```sql
-- 验证状态校验函数
select report_status_is_valid('submitted', 'draft');  -- 期望 true

-- 验证 retract_report 函数存在
select proname, prosrc from pg_proc where proname = 'retract_report';
```

- [ ] **Step 4: Commit**

```bash
git add supabase/migrations/20260413000100_110_retract_permission.sql
git commit -m "feat: 收紧 submitted 权限 + 增加 retract_report 撤回路径"
```

---

### Task 2: 创建 Python 撤回接口

**Files:**
- Create: `skills/neolyst/scripts/retract_report.py`

- [ ] **Step 1: 写 retract_report.py**

遵循 `submit_report.py` 的模式：调用 RPC，返回标准化的 dict。

```python
"""
retract_report.py — Neolyst 报告撤回接口。

流程：
1. 调用 retract_report RPC
2. 返回 {report_id, version_no, status}

业务逻辑（状态校验、流转日志写入）全部在 Supabase RPC 侧，本模块只做调用串联。
"""

from supabase import Client

from . import rpc


def retract_report(client: Client, report_id: str) -> dict:
    """
    将 submitted/rejected 报告撤回为 draft 状态。

    Args:
        client: 已认证的 Supabase client
        report_id: 报告 UUID 字符串

    Returns:
        dict: {"report_id": str, "version_no": int, "status": "draft"}

    Raises:
        ValueError: RPC 调用失败（报告不存在、状态不允许撤回等）
    """
    row = rpc.single_row(rpc.call_rpc(client, "retract_report", {
        "p_report_id": report_id,
    }))
    return {
        "report_id": str(row["report_id"]),
        "version_no": row["version_no"],
        "status": row["status"],
    }
```

- [ ] **Step 2: Commit**

```bash
git add skills/neolyst/scripts/retract_report.py
git commit -m "feat: 新增 retract_report Python 撤回接口"
```

---

### Task 3: 创建集成测试

**Files:**
- Create: `skills/neolyst/tests/test_retract_report.py`

- [ ] **Step 1: 写测试文件**

设计说明：撤回操作会改变报告状态，所以不能用 module 级 fixture 复用同一份 submitted 报告。
采用以下策略：
- happy path 合并为单个测试（创建→提交→撤回→断言，一条龙）
- edge case 各自独立创建报告

```python
"""
test_retract_report.py — retract_report 集成测试（4 个）。
"""
import json
import uuid
from pathlib import Path

import pytest

TEST_ANALYST = json.loads((Path(__file__).parent / "test_config.json").read_text())["email"]


def _make_files(directory: Path) -> tuple[str, str]:
    word = directory / "report.docx"
    pdf = directory / "report.pdf"
    word.write_bytes(b"fake docx")
    pdf.write_bytes(b"fake pdf")
    return str(word), str(pdf)


def _create_submitted_report(client, coverage_id, tmp_dir, title="Retract Test"):
    """辅助函数：创建 draft → 提交为 submitted → 返回提交结果。"""
    from skills.neolyst.scripts import draft_report
    from skills.neolyst.scripts import submit_report as sr

    word_path, pdf_path = _make_files(tmp_dir)
    draft = draft_report.save_draft_report(client, {
        "report_id": None,
        "title": title,
        "report_type": "company",
        "report_language": "en",
        "investment_thesis": "Test investment thesis",
        "contact_person": TEST_ANALYST,
        "analysts": [{"analyst_email": TEST_ANALYST, "author_order": 1}],
        "ticker": title[:8].upper().replace(" ", ""),
        "coverage_id": coverage_id,
        "sector_id": None,
        "region_code": None,
        "rating": "OUTPERFORM",
        "target_price": 100.0,
        "report_file": word_path,
        "pdf_file": pdf_path,
        "model_file": None,
    })
    return sr.submit_report(client, draft["report_id"])


@pytest.fixture(scope="module")
def retract_coverage_id(neolyst_client):
    from skills.neolyst.scripts import coverage as cov

    _suffix = uuid.uuid4().hex[:6].upper()
    sector_resp = neolyst_client.table("sector").select("id").eq("is_active", True).limit(1).execute()
    sector_id = sector_resp.data[0]["id"]

    cov_id = cov.create_coverage(
        neolyst_client,
        ticker=f"RET{_suffix}",
        english_name=f"Retract Test Co {_suffix}",
        sector_id=sector_id,
        isin=f"HK{_suffix}{'0' * (10 - len(_suffix))}",
        country_of_domicile="Hong Kong",
        analysts=[{"analyst_email": TEST_ANALYST, "author_order": 1}],
    )
    yield cov_id
    neolyst_client.table("coverage").delete().eq("id", cov_id).execute()


class TestRetractSubmittedReport:
    """测试 submitted → draft 撤回完整流程（单测试覆盖返回值 + DB + 日志）。"""

    def test_retract_submitted_report(self, neolyst_client, retract_coverage_id, tmp_path):
        """创建 submitted 报告 → 撤回 → 验证返回值、DB 状态、状态日志。"""
        from skills.neolyst.scripts import retract_report as rr

        submitted = _create_submitted_report(
            neolyst_client, retract_coverage_id, tmp_path / "retract_happy",
        )
        report_id = submitted["report_id"]

        try:
            result = rr.retract_report(neolyst_client, report_id)

            # 1. 返回值：status == draft
            assert result["status"] == "draft"
            uuid.UUID(result["report_id"])
            assert result["version_no"] == submitted["version_no"]

            # 2. DB 状态：report.status == draft
            resp = (
                neolyst_client.table("report")
                .select("status")
                .eq("id", report_id)
                .execute()
            )
            assert resp.data[0]["status"] == "draft"

            # 3. 状态日志：submitted → draft
            log_resp = (
                neolyst_client.table("report_status_log")
                .select("*")
                .eq("report_id", report_id)
                .eq("to_status", "draft")
                .execute()
            )
            assert log_resp.data
            log = log_resp.data[0]
            assert log["from_status"] == "submitted"
            assert log["to_status"] == "draft"
            assert log["version_no"] == submitted["version_no"]
            assert "@" in (log["action_by_name"] or "")
        finally:
            neolyst_client.table("report").delete().eq("id", report_id).execute()


class TestRetractEdgeCases:
    """测试撤回边界条件。"""

    def test_retract_draft_raises(self, neolyst_client, retract_coverage_id, tmp_path):
        """对 draft 报告调用 retract_report 抛出 ValueError。"""
        from skills.neolyst.scripts import draft_report
        from skills.neolyst.scripts import retract_report as rr

        word_path, pdf_path = _make_files(tmp_path / "draft_edge")
        draft = draft_report.save_draft_report(neolyst_client, {
            "report_id": None,
            "title": "Retract Draft Test",
            "report_type": "company",
            "report_language": "en",
            "investment_thesis": "Test investment thesis",
            "contact_person": TEST_ANALYST,
            "analysts": [{"analyst_email": TEST_ANALYST, "author_order": 1}],
            "ticker": "RETDRAFT",
            "coverage_id": retract_coverage_id,
            "sector_id": None,
            "region_code": None,
            "rating": "OUTPERFORM",
            "target_price": 100.0,
            "report_file": word_path,
            "pdf_file": pdf_path,
            "model_file": None,
        })
        try:
            with pytest.raises(ValueError, match="无法撤回"):
                rr.retract_report(neolyst_client, draft["report_id"])
        finally:
            neolyst_client.table("report").delete().eq("id", draft["report_id"]).execute()

    def test_retract_already_retracted_raises(self, neolyst_client, retract_coverage_id, tmp_path):
        """对已撤回为 draft 的报告再次撤回，抛出 ValueError。"""
        from skills.neolyst.scripts import retract_report as rr

        submitted = _create_submitted_report(
            neolyst_client, retract_coverage_id, tmp_path / "double_retract",
        )
        report_id = submitted["report_id"]

        try:
            rr.retract_report(neolyst_client, report_id)  # 第一次撤回成功
            with pytest.raises(ValueError, match="无法撤回"):
                rr.retract_report(neolyst_client, report_id)  # 第二次应失败
        finally:
            neolyst_client.table("report").delete().eq("id", report_id).execute()

    def test_retract_nonexistent_report_raises(self, neolyst_client):
        """对不存在的报告调用 retract_report 抛出 ValueError。"""
        from skills.neolyst.scripts import retract_report as rr

        with pytest.raises(ValueError, match="报告不存在"):
            rr.retract_report(neolyst_client, str(uuid.uuid4()))
```

- [ ] **Step 2: 运行测试**

Run: `cd /mnt/c/_code/neoskills && uv run pytest skills/neolyst/tests/test_retract_report.py -v`
Expected: 4 个测试全部 PASSED

- [ ] **Step 3: Commit**

```bash
git add skills/neolyst/tests/test_retract_report.py
git commit -m "test: 新增 retract_report 集成测试（4 个用例）"
```

---

### Task 4: 更新 spec 文件状态

**Files:**
- Modify: `docs/todo/schema-p0-retract-permission.md`

- [ ] **Step 1: 在文件头部追加实施状态标记**

在文件第 1 行 `# P0 Schema 调整` 之前追加：

```markdown
> **状态：已实施** — 迁移文件 `20260413000100_110_retract_permission.sql`，Python 接口 `skills/neolyst/scripts/retract_report.py`

```

- [ ] **Step 2: Commit**

```bash
git add docs/todo/schema-p0-retract-permission.md
git commit -m "docs: 标记 schema-p0-retract-permission 为已实施"
```
