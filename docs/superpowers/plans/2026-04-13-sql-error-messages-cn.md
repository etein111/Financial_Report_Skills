# SQL 错误消息中文化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 4 个 SQL 函数中的 11 处英文错误消息统一为中文，同步更新 Python 测试断言和接口文档。

**Architecture:** 新建一个 Supabase 迁移文件，用 `create or replace function` 重写受影响的 4 个函数，仅替换 raise exception 中的消息文本。同步修改 Python 集成测试的 `match=` 字符串和接口文档中的错误描述。

**Tech Stack:** PostgreSQL (Supabase migration), Python (pytest), Markdown

---

## File Structure

| 操作 | 文件 | 职责 |
|------|------|------|
| Create | `supabase/migrations/20260413000500_114_sql_error_messages_cn.sql` | 新迁移：4 函数错误消息英→中 |
| Modify | `skills/neolyst/tests/test_analyst.py:68,76` | 测试断言匹配中文消息 |
| Modify | `skills/neolyst/tests/test_template.py:91,96` | 测试断言匹配中文消息 |
| Modify | `skills/neolyst/references/interfaces.md:16,229` | 接口文档中的错误描述 |

---

### Task 1: 更新 test_analyst.py 断言（RED）

**Files:**
- Modify: `skills/neolyst/tests/test_analyst.py:68,76`

- [ ] **Step 1: 修改 test_not_found_raises_value_error 断言**

将第 68 行：
```python
        with pytest.raises(ValueError, match="Analyst not found"):
```
改为：
```python
        with pytest.raises(ValueError, match="找不到分析师"):
```

- [ ] **Step 2: 修改 test_inactive_raises_value_error 断言**

将第 76 行：
```python
        with pytest.raises(ValueError, match="Analyst is inactive"):
```
改为：
```python
        with pytest.raises(ValueError, match="分析师已停用"):
```

- [ ] **Step 3: 运行测试验证 FAIL**

Run: `cd /mnt/c/_code/neoskills && python -m pytest skills/neolyst/tests/test_analyst.py -v -k "test_not_found or test_inactive" 2>&1 | tail -20`

Expected: 2 个测试 FAIL，因为数据库中的 RPC 仍返回英文消息 `Analyst not found` 和 `Analyst is inactive`，与中文 match 不匹配。

---

### Task 2: 更新 test_template.py 断言（RED）

**Files:**
- Modify: `skills/neolyst/tests/test_template.py:91,96`

- [ ] **Step 1: 修改 test_reuse_self_raises 断言**

将第 91 行：
```python
        with pytest.raises(ValueError, match="self"):
```
改为：
```python
        with pytest.raises(ValueError, match="不能复用自身"):
```

- [ ] **Step 2: 修改 test_reuse_nonexistent_source_raises 断言**

将第 96 行：
```python
        with pytest.raises(ValueError, match="not found"):
```
改为：
```python
        with pytest.raises(ValueError, match="未找到"):
```

- [ ] **Step 3: 运行测试验证 FAIL**

Run: `cd /mnt/c/_code/neoskills && python -m pytest skills/neolyst/tests/test_template.py -v -k "test_reuse_self or test_reuse_nonexistent" 2>&1 | tail -20`

Expected: 2 个测试 FAIL，因为 RPC 仍返回英文消息 `Cannot reuse self` 和 `Source template not found`。

注意：TestResolveTemplate 下的 `test_resolve_unpublished_raises`（line 128）和 `test_resolve_nonexistent_raises`（line 135）不需要改——它们匹配的是 Python 侧 raise 的英文消息，不走 RPC。

---

### Task 3: 创建 SQL 迁移文件（GREEN）

**Files:**
- Create: `supabase/migrations/20260413000500_114_sql_error_messages_cn.sql`

- [ ] **Step 1: 创建迁移文件**

文件内容如下（4 个 `create or replace function`，仅改 raise exception 消息文本）：

```sql
-- 20260413000500_114_sql_error_messages_cn.sql
-- 统一 SQL 函数 raise exception 消息为中文
-- 受影响函数：validate_sector_hierarchy, report_enforce_status_transition,
--             resolve_analyst_by_email, reuse_template

-- ===================================================================
-- 1. validate_sector_hierarchy：5 处英文 → 中文
-- ===================================================================

create or replace function public.validate_sector_hierarchy()
returns trigger
language plpgsql
as $$
declare
  v_parent_level smallint;
  v_parent_parent uuid;
begin
  if new.parent_id is not null and new.parent_id = new.id then
    raise exception 'sector 父级不能引用自身';
  end if;

  if new.level = 1 then
    if new.parent_id is not null then
      raise exception '一级行业不能设置父级';
    end if;
    return new;
  end if;

  select s.level, s.parent_id
    into v_parent_level, v_parent_parent
  from public.sector s
  where s.id = new.parent_id;

  if not found then
    raise exception '二级行业必须引用已存在的父级';
  end if;

  if v_parent_level <> 1 then
    raise exception '二级行业的父级必须是一级行业';
  end if;

  if v_parent_parent is not null then
    raise exception '行业层级最多支持两级';
  end if;

  return new;
end;
$$;

-- ===================================================================
-- 2. report_enforce_status_transition：1 处英文 → 中文
-- ===================================================================

create or replace function public.report_enforce_status_transition()
returns trigger
language plpgsql
as $$
begin
  if tg_op = 'UPDATE' and new.status is distinct from old.status then
    if not public.report_status_is_valid(old.status, new.status) then
      raise exception '无效的报告状态转换：% → %', old.status, new.status;
    end if;
  end if;
  return new;
end;
$$;

-- ===================================================================
-- 3. resolve_analyst_by_email：2 处英文 → 中文
--    基于 105 版本（无 SECURITY DEFINER），保持属性不变
-- ===================================================================

create or replace function public.resolve_analyst_by_email(
    p_email text
)
returns public.analyst
language plpgsql stable
as $$
declare
    v_email text;
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

-- ===================================================================
-- 4. reuse_template：3 处英文 → 中文
-- ===================================================================

create or replace function public.reuse_template(
    p_report_type         text,
    p_language            text,
    p_same_as_report_type text
)
returns void
language plpgsql security definer
as $$
declare
    v_source    public.report_template%rowtype;
    v_target_id text;
begin
    if p_report_type = p_same_as_report_type then
        raise exception '不能复用自身：report_type=''%''', p_report_type;
    end if;

    select * into v_source
    from public.report_template
    where id = p_same_as_report_type || '_' || p_language;

    if not found then
        raise exception '源模板未找到：''%''',
            p_same_as_report_type || '_' || p_language;
    end if;

    if v_source.template_file_path = '' or v_source.template_file_path is null then
        raise exception '源模板未发布（路径为空）：''%''',
            p_same_as_report_type || '_' || p_language;
    end if;

    v_target_id := p_report_type || '_' || p_language;

    insert into public.report_template (id, report_type, language, template_file_path, schema_file_path)
    values (v_target_id, p_report_type, p_language, v_source.template_file_path, v_source.schema_file_path)
    on conflict (id) do update
        set template_file_path = excluded.template_file_path,
            schema_file_path   = excluded.schema_file_path;
end;
$$;
```

- [ ] **Step 2: 重置数据库应用迁移**

Run: `supabase db reset`

Expected: 所有迁移（含新建的 114）成功应用，无错误。

---

### Task 4: 验证测试通过（GREEN）

- [ ] **Step 1: 运行 test_analyst.py 验证**

Run: `cd /mnt/c/_code/neoskills && python -m pytest skills/neolyst/tests/test_analyst.py -v 2>&1 | tail -20`

Expected: 全部 PASS。

- [ ] **Step 2: 运行 test_template.py 验证**

Run: `cd /mnt/c/_code/neoskills && python -m pytest skills/neolyst/tests/test_template.py -v 2>&1 | tail -20`

Expected: 全部 PASS（包括 TestResolveTemplate 的测试，它们匹配 Python 侧消息，不受影响）。

- [ ] **Step 3: 运行全量测试验证无回归**

Run: `cd /mnt/c/_code/neoskills && python -m pytest skills/neolyst/tests/ -v 2>&1 | tail -30`

Expected: 全部 PASS，无回归。

---

### Task 5: 更新接口文档

**Files:**
- Modify: `skills/neolyst/references/interfaces.md:16,229`

- [ ] **Step 1: 更新第 16 行**

将：
```
- `is_active=False` 的分析师抛出 `ValueError: Analyst is inactive: {email}`
```
改为：
```
- `is_active=False` 的分析师抛出 `ValueError: 分析师已停用：{email}`
```

- [ ] **Step 2: 更新第 229 行**

将：
```
报错内容："找不到分析师" 或 "Analyst is inactive"
```
改为：
```
报错内容："找不到分析师" 或 "分析师已停用"
```

---

### Task 6: 提交

- [ ] **Step 1: 提交所有变更**

```bash
cd /mnt/c/_code/neoskills
git add supabase/migrations/20260413000500_114_sql_error_messages_cn.sql
git add skills/neolyst/tests/test_analyst.py
git add skills/neolyst/tests/test_template.py
git add skills/neolyst/references/interfaces.md
git add docs/superpowers/specs/2026-04-13-sql-error-messages-cn.md
git add docs/superpowers/plans/2026-04-13-sql-error-messages-cn.md
git commit -m "feat(neolyst): SQL 错误消息统一为中文

4 个函数 11 处 raise exception 英文消息改为中文：
- validate_sector_hierarchy (5处)
- report_enforce_status_transition (1处)
- resolve_analyst_by_email (2处)
- reuse_template (3处)

同步更新 Python 测试断言和接口文档。"
```
