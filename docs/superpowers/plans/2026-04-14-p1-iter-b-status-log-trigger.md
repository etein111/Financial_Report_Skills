# P1 Iter B：状态日志 metadata + 触发器 — 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新增 `rejection_reason` 字段、`metadata` 快照字段和 AFTER UPDATE 触发器，统一接管状态变更的日志写入。

**Architecture:** 单迁移文件，DDL 新增字段 → 触发器函数 → 重写 RPC 移除手动 INSERT。Python 测试补充 metadata 断言。

**Tech Stack:** PostgreSQL (Supabase), PL/pgSQL, Python (supabase-py, pytest)

**Prerequisite:** Iter A（分析师字段合并）已完成。`report` 表已有 `lead_analyst_email` 和 `analyst_emails` 字段。

---

## File Structure

| 操作 | 文件 | 职责 |
|------|------|------|
| Create | `supabase/migrations/<ts>_p1_iter_b_status_log_trigger.sql` | DDL + 触发器 + RPC 重写 |
| Modify | `skills/neolyst/tests/test_submit_report.py` | 补充 metadata 断言 |
| Modify | `skills/neolyst/tests/test_retract_report.py` | 补充 metadata 断言 |

---

### Task 1: 创建迁移文件 — DDL（新增字段）

**Files:**
- Create: `supabase/migrations/<ts>_p1_iter_b_status_log_trigger.sql`

- [ ] **Step 1: 用 supabase CLI 创建迁移文件**

Run:
```bash
supabase migration new p1_iter_b_status_log_trigger
```

Expected: 生成 `supabase/migrations/<timestamp>_p1_iter_b_status_log_trigger.sql`

- [ ] **Step 2: 写入 DDL SQL**

```sql
-- P1 Iter B: 状态日志 metadata + 触发器
-- 1. report 表新增 rejection_reason
alter table public.report
  add column rejection_reason text;

-- 2. report_status_log 表新增 metadata
alter table public.report_status_log
  add column metadata jsonb not null default '{}';
```

- [ ] **Step 3: Commit**

```bash
git add supabase/migrations/<timestamp>_p1_iter_b_status_log_trigger.sql
git commit -m "feat(p1-b): add rejection_reason and metadata columns"
```

---

### Task 2: 迁移文件 — 新增 AFTER UPDATE 触发器

**Files:**
- Modify: `supabase/migrations/<ts>_p1_iter_b_status_log_trigger.sql`

- [ ] **Step 1: 追加触发器函数和触发器**

在迁移文件末尾追加：

```sql
-- 3. AFTER UPDATE 触发器：状态变更时自动写日志 + metadata
create or replace function public.report_write_status_log()
returns trigger
language plpgsql
as $$
declare
    v_version  record;
    v_metadata jsonb;
begin
    if new.status is distinct from old.status then
        -- 读取当前版本文件路径
        select rv.word_file_path, rv.pdf_file_path, rv.model_file_path
          into v_version
          from public.report_version rv
         where rv.report_id = new.id
           and rv.version_no = new.current_version_no;

        -- 构建业务快照
        v_metadata := jsonb_build_object(
            'title',              new.title,
            'report_type',        new.report_type,
            'lead_analyst_email', new.lead_analyst_email,
            'analyst_emails',     new.analyst_emails,
            'coverage_id',        new.coverage_id,
            'ticker',             new.ticker,
            'sector_id',          new.sector_id,
            'region_code',        new.region_code,
            'rating',             new.rating,
            'target_price',       new.target_price,
            'investment_thesis',  new.investment_thesis,
            'report_language',    new.report_language,
            'contact_person',     new.contact_person,
            'word_path',          v_version.word_file_path,
            'pdf_path',           v_version.pdf_file_path,
            'model_path',         v_version.model_file_path
        );

        insert into public.report_status_log (
            report_id, from_status, to_status,
            action_by, action_by_name, version_no,
            reason, metadata
        ) values (
            new.id, old.status, new.status,
            auth.uid(), auth.jwt()->>'email',
            new.current_version_no,
            case when new.status = 'rejected' then new.rejection_reason else null end,
            v_metadata
        );
    end if;

    return null;
end;
$$;

comment on function public.report_write_status_log is
'AFTER UPDATE 触发器函数：当 report.status 变化时自动写入 report_status_log + metadata 快照。
不声明 SECURITY DEFINER，以调用者身份执行，依赖 rsl_insert RLS policy。';

create trigger trg_report_write_status_log
after update on public.report
for each row
execute function public.report_write_status_log();
```

- [ ] **Step 2: Commit**

```bash
git add supabase/migrations/<timestamp>_p1_iter_b_status_log_trigger.sql
git commit -m "feat(p1-b): add AFTER UPDATE trigger for status log + metadata"
```

---

### Task 3: 迁移文件 — 重写 submit_report RPC

**Files:**
- Modify: `supabase/migrations/<ts>_p1_iter_b_status_log_trigger.sql`

- [ ] **Step 1: 追加 submit_report 重写**

在迁移文件末尾追加：

```sql
-- 4. 重写 submit_report（触发器接管日志 + 清除 rejection_reason）
create or replace function public.submit_report(
    p_report_id uuid
)
returns table(report_id uuid, version_no integer, status text)
language plpgsql
as $$
declare
    v_current_status     text;
    v_current_version_no integer;
begin
    select r.status, r.current_version_no
      into v_current_status, v_current_version_no
      from public.report r
     where r.id = p_report_id;

    if not found then
        raise exception '报告不存在: %', p_report_id;
    end if;

    if v_current_status not in ('draft', 'rejected') then
        raise exception '报告状态为 %，无法提交（仅 draft/rejected 可提交）',
            v_current_status;
    end if;

    if coalesce(v_current_version_no, 0) <= 0 then
        raise exception '报告当前没有可提交版本';
    end if;

    if not exists (
        select 1
          from public.report_version rv
         where rv.report_id = p_report_id
           and rv.version_no = v_current_version_no
    ) then
        raise exception '当前版本 v% 不存在', v_current_version_no;
    end if;

    -- 字段完整性守门
    perform public.validate_report(p_report_id);

    -- 更新状态并清除 rejection_reason（触发器自动写日志）
    update public.report
       set status = 'submitted', rejection_reason = null
     where id = p_report_id;

    return query
        select p_report_id, v_current_version_no, 'submitted'::text;
end;
$$;

comment on function public.submit_report is
'将 draft/rejected 报告当前版本提交为 submitted。触发器自动写入 report_status_log。';

revoke execute on function public.submit_report(uuid) from public, anon;
grant execute on function public.submit_report(uuid) to authenticated;
```

- [ ] **Step 2: Commit**

```bash
git add supabase/migrations/<timestamp>_p1_iter_b_status_log_trigger.sql
git commit -m "feat(p1-b): rewrite submit_report, remove manual status_log insert"
```

---

### Task 4: 迁移文件 — 重写 retract_report RPC

**Files:**
- Modify: `supabase/migrations/<ts>_p1_iter_b_status_log_trigger.sql`

- [ ] **Step 1: 追加 retract_report 重写**

在迁移文件末尾追加：

```sql
-- 5. 重写 retract_report（触发器接管日志 + 清除 rejection_reason）
create or replace function public.retract_report(
    p_report_id uuid
)
returns table(report_id uuid, version_no integer, status text)
language plpgsql
as $$
declare
    v_current_status     text;
    v_current_version_no integer;
begin
    select r.status, r.current_version_no
      into v_current_status, v_current_version_no
      from public.report r
     where r.id = p_report_id;

    if not found then
        raise exception '报告不存在: %', p_report_id;
    end if;

    if v_current_status not in ('submitted', 'rejected') then
        raise exception '报告状态为 %，无法撤回（仅 submitted/rejected 可撤回）', v_current_status;
    end if;

    -- 更新状态并清除 rejection_reason（触发器自动写日志）
    update public.report
       set status = 'draft', rejection_reason = null
     where id = p_report_id;

    return query
        select p_report_id, v_current_version_no, 'draft'::text;
end;
$$;

comment on function public.retract_report is
'将 submitted/rejected 报告撤回为 draft。触发器自动写入 report_status_log。';

revoke execute on function public.retract_report(uuid) from public, anon;
grant execute on function public.retract_report(uuid) to authenticated;
```

- [ ] **Step 2: Commit**

```bash
git add supabase/migrations/<timestamp>_p1_iter_b_status_log_trigger.sql
git commit -m "feat(p1-b): rewrite retract_report, remove manual status_log insert"
```

---

### Task 5: 应用迁移并验证数据库

**Files:** 无文件变更

- [ ] **Step 1: 重置本地数据库**

Run:
```bash
supabase db reset
```

Expected: 迁移全部成功（含 Iter A 和 Iter B），无错误输出

- [ ] **Step 2: 验证 rejection_reason 字段存在**

Run:
```bash
supabase db execute --sql "SELECT column_name, is_nullable FROM information_schema.columns WHERE table_name = 'report' AND column_name = 'rejection_reason';"
```

Expected: 一行结果，`is_nullable = YES`

- [ ] **Step 3: 验证 metadata 字段存在**

Run:
```bash
supabase db execute --sql "SELECT column_name, data_type, column_default FROM information_schema.columns WHERE table_name = 'report_status_log' AND column_name = 'metadata';"
```

Expected: 一行结果，`data_type = jsonb`，`column_default` 含 `'{}'`

- [ ] **Step 4: 验证触发器存在**

Run:
```bash
supabase db execute --sql "SELECT trigger_name, event_manipulation, action_timing FROM information_schema.triggers WHERE event_object_table = 'report' AND trigger_name = 'trg_report_write_status_log';"
```

Expected: 一行结果，`event_manipulation = UPDATE`，`action_timing = AFTER`

---

### Task 6: 更新测试 — test_submit_report.py

**Files:**
- Modify: `skills/neolyst/tests/test_submit_report.py`

- [ ] **Step 1: 补充 metadata 断言**

将 `test_status_log_created` 方法（第 93-106 行）替换为：

```python
    def test_status_log_created(self, neolyst_client, submitted_report):
        """report_status_log 有 draft→submitted 记录，含 metadata 快照。"""
        resp = (
            neolyst_client.table("report_status_log")
            .select("*")
            .eq("report_id", submitted_report["report_id"])
            .execute()
        )
        assert resp.data
        log = resp.data[0]
        assert log["from_status"] == "draft"
        assert log["to_status"] == "submitted"
        assert log["version_no"] == 1
        assert "@" in (log["action_by_name"] or "")
        assert log["metadata"]
        assert log["metadata"]["title"] == "Submit Test Report"
        assert log["metadata"]["lead_analyst_email"] == TEST_ANALYST
```

- [ ] **Step 2: Commit**

```bash
git add skills/neolyst/tests/test_submit_report.py
git commit -m "test(p1-b): add metadata assertions to submit_report tests"
```

---

### Task 7: 更新测试 — test_retract_report.py

**Files:**
- Modify: `skills/neolyst/tests/test_retract_report.py`

- [ ] **Step 1: 补充 metadata 断言**

将 `test_retract_submitted_report` 方法中日志验证部分（约第 99-112 行）替换为：

```python
            # 3. 状态日志：submitted → draft，含 metadata 快照
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
            assert log["metadata"]
```

- [ ] **Step 2: Commit**

```bash
git add skills/neolyst/tests/test_retract_report.py
git commit -m "test(p1-b): add metadata assertions to retract_report tests"
```

---

### Task 8: 运行全量测试

**Files:** 无文件变更

- [ ] **Step 1: 运行全部 neolyst 测试**

Run:
```bash
cd /mnt/c/_code/neoskills && uv run pytest skills/neolyst/tests/ -v
```

Expected: 全部测试通过，无失败

- [ ] **Step 2: 如有失败，排查并修复**

常见失败原因：
- 触发器写入日志与 submit/retract 的手动 INSERT 重复 → 确认 RPC 中已删除手动 INSERT
- metadata 为空 → 检查触发器是否正确读取了 report_version
- RLS 阻止触发器 INSERT → 确认 `rsl_insert` policy 允许对应的状态流转
