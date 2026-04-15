# SECURITY DEFINER 清理 + reuse_template 拼接优化 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 去掉 4 个函数的无必要 SECURITY DEFINER，reuse_template 提取重复拼接变量。

**Architecture:** 单次迁移文件，`CREATE OR REPLACE` 重建 4 个函数。无行为变更，现有测试验证正确性。

**Tech Stack:** Supabase SQL 迁移、plpgsql

---

## 文件清单

| 操作 | 文件 | 职责 |
|------|------|------|
| 创建 | `supabase/migrations/<new>_remove_unnecessary_security_definer.sql` | 重建 4 个函数（去掉 SECURITY DEFINER + reuse_template 提取变量） |

不修改现有文件。现有测试（`test_template.py`、`test_validators.py`、`test_submit_report.py`）用于验证。

---

### Task 1: 创建迁移文件

**Files:**
- 创建: `supabase/migrations/<new>_remove_unnecessary_security_definer.sql`

- [ ] **Step 1: 用 Supabase CLI 创建空迁移文件**

```bash
supabase migration new remove_unnecessary_security_definer
```

- [ ] **Step 2: 写入 4 个函数的重建语句**

将以下内容写入新生成的迁移文件：

```sql
-- 1. get_template_storage_paths: 去掉 SECURITY DEFINER（纯计算，不读写表）
CREATE OR REPLACE FUNCTION "public"."get_template_storage_paths"("p_report_type" "text", "p_language" "text") RETURNS TABLE("template_file_path" "text", "schema_file_path" "text")
    LANGUAGE "sql" STABLE
    AS $$
    select
        'templates/' || p_report_type || '/' || p_language || '/template.docx' as template_file_path,
        'templates/' || p_report_type || '/' || p_language || '/schema.yaml'    as schema_file_path;
$$;

-- 2. resolve_coverage: 去掉 SECURITY DEFINER（只读表，SELECT RLS = USING(true)）
CREATE OR REPLACE FUNCTION "public"."resolve_coverage"("p_ticker" "text", "p_analyst_email" "text") RETURNS TABLE("coverage_id" "uuid")
    LANGUAGE "plpgsql" STABLE
    AS $$
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

-- 3. reuse_template: 去掉 SECURITY DEFINER + 提取 v_source_id 变量
CREATE OR REPLACE FUNCTION "public"."reuse_template"("p_report_type" "text", "p_language" "text", "p_same_as_report_type" "text") RETURNS "void"
    LANGUAGE "plpgsql"
    AS $$
declare
    v_source    public.report_template%rowtype;
    v_source_id text;
    v_target_id text;
begin
    if p_report_type = p_same_as_report_type then
        raise exception '不能复用自身：report_type=''%''', p_report_type;
    end if;

    v_source_id := p_same_as_report_type || '_' || p_language;

    select * into v_source
    from public.report_template
    where id = v_source_id;

    if not found then
        raise exception '源模板未找到：''%''', v_source_id;
    end if;

    if v_source.template_file_path = '' or v_source.template_file_path is null then
        raise exception '源模板未发布（路径为空）：''%''', v_source_id;
    end if;

    v_target_id := p_report_type || '_' || p_language;

    insert into public.report_template (id, report_type, language, template_file_path, schema_file_path)
    values (v_target_id, p_report_type, p_language, v_source.template_file_path, v_source.schema_file_path)
    on conflict (id) do update
        set template_file_path = excluded.template_file_path,
            schema_file_path   = excluded.schema_file_path;
end;
$$;

-- 4. upsert_template_record: 去掉 SECURITY DEFINER
CREATE OR REPLACE FUNCTION "public"."upsert_template_record"("p_report_type" "text", "p_language" "text") RETURNS "void"
    LANGUAGE "plpgsql"
    AS $$
declare
    v_id                text;
    v_template_path     text;
    v_schema_path       text;
begin
    v_id            := p_report_type || '_' || p_language;
    v_template_path := 'templates/' || p_report_type || '/' || p_language || '/template.docx';
    v_schema_path   := 'templates/' || p_report_type || '/' || p_language || '/schema.yaml';

    insert into public.report_template (id, report_type, language, template_file_path, schema_file_path)
    values (v_id, p_report_type, p_language, v_template_path, v_schema_path)
    on conflict (id) do update
        set template_file_path = excluded.template_file_path,
            schema_file_path   = excluded.schema_file_path;
end;
$$;
```

- [ ] **Step 3: 提交迁移文件**

```bash
git add supabase/migrations/<timestamp>_remove_unnecessary_security_definer.sql
git commit -m "feat: 去掉 4 个函数的无必要 SECURITY DEFINER + reuse_template 提取变量"
```

---

### Task 2: 应用迁移 + 验证

- [ ] **Step 1: 应用迁移到本地 Supabase**

```bash
supabase db reset
```

预期：无报错，4 个函数成功重建。

- [ ] **Step 2: 运行现有测试**

```bash
cd /mnt/c/_code/neoskills
uv run pytest skills/neolyst/tests/test_template.py -v
```

预期：`test_reuse_copies_paths`、`test_reuse_self_raises`、`test_reuse_nonexistent_source_raises` 全部 PASS。

```bash
uv run pytest skills/neolyst/tests/test_validators.py -v
```

预期：所有 validate_report 测试 PASS。

```bash
uv run pytest skills/neolyst/tests/test_submit_report.py -v
```

预期：所有 submit_report 测试 PASS。

- [ ] **Step 3: 确认 SECURITY DEFINER 已去除**

在 Supabase SQL Editor 中执行：

```sql
select proname, prosecdef
from pg_proc
where proname in (
    'get_template_storage_paths',
    'resolve_coverage',
    'reuse_template',
    'upsert_template_record',
    'create_coverage'
)
order by proname;
```

预期：
| proname | prosecdef |
|---------|-----------|
| create_coverage | t |
| get_template_storage_paths | f |
| resolve_coverage | f |
| reuse_template | f |
| upsert_template_record | f |

- [ ] **Step 4: 提交验证结果，推送**

```bash
git push
```

---

### Task 3: 更新文档状态

- [ ] **Step 1: 将 todo 移到 done**

```bash
mv docs/todo/sql-remove-security-definer-and-reuse-cleanup.md docs/done/sql-remove-security-definer-and-reuse-cleanup.md
```

- [ ] **Step 2: 提交**

```bash
git add docs/todo/sql-remove-security-definer-and-reuse-cleanup.md docs/done/sql-remove-security-definer-and-reuse-cleanup.md
git commit -m "docs: SECURITY DEFINER 清理完成，todo → done"
```
