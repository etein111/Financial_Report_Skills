# SQL 函数清理：去掉 SECURITY DEFINER + reuse_template 拼接优化

> 记录日期：2026-04-15
> 来源：审查 docs/todo/sql-optimize-validate-and-reuse.md 原始问题后重新评估
> 优先级：P3

---

## 背景

P2 schema redesign 后，`validate_report` 的 3 个原始优化项已随架构变更自动解决（analyst_emails 移入 report 表、word_path/pdf_path 移入 report 表、不再查 report_analyst/report_version）。

本次清理聚焦两个遗留问题：

1. 全库 `SECURITY DEFINER` 审计——5 处中 4 处无必要，应去掉
2. `reuse_template` 中重复字符串拼接

---

## 变更 1：去掉 4 个函数的 SECURITY DEFINER

### 1a. get_template_storage_paths

**迁移文件行：** 139
**现状：** `LANGUAGE "sql" STABLE SECURITY DEFINER`
**改为：** `LANGUAGE "sql" STABLE`
**原因：** 纯计算函数，拼接路径字符串返回，不读写任何表。SECURITY DEFINER 在此毫无作用。

### 1b. resolve_coverage

**迁移文件行：** 377
**现状：** `LANGUAGE "plpgsql" STABLE SECURITY DEFINER`
**改为：** `LANGUAGE "plpgsql" STABLE`
**原因：** 只读 coverage + coverage_analyst 两张表，SELECT 策略均为 `USING (true)`（所有 authenticated 用户可见）。SECURITY DEFINER 无存在意义。

### 1c. reuse_template

**迁移文件行：** 447
**现状：** `LANGUAGE "plpgsql" SECURITY DEFINER`
**改为：** `LANGUAGE "plpgsql"`
**原因：** 调用方为 admin，RLS 策略 `dict_write` 已放行 admin 写入 report_template。

### 1d. upsert_template_record

**迁移文件行：** 691
**现状：** `LANGUAGE "plpgsql" SECURITY DEFINER`
**改为：** `LANGUAGE "plpgsql"`
**原因：** 同 1c，调用方为 admin。

### 不动

`create_coverage`（行 27）保留 SECURITY DEFINER——analyst 角色也需要创建 coverage。

---

## 变更 2：reuse_template 提取重复拼接为变量

**迁移文件行：** 449-469
**现状：** `p_same_as_report_type || '_' || p_language` 出现 3 次（第 459、463、468 行）

**改为：**

```sql
declare
    v_source    public.report_template%rowtype;
    v_source_id text;   -- 新增
    v_target_id text;
begin
    if p_report_type = p_same_as_report_type then
        raise exception '不能复用自身：report_type=''%''', p_report_type;
    end if;

    v_source_id := p_same_as_report_type || '_' || p_language;  -- 赋值一次

    select * into v_source
    from public.report_template
    where id = v_source_id;                                      -- 引用变量

    if not found then
        raise exception '源模板未找到：''%''', v_source_id;       -- 引用变量
    end if;

    if v_source.template_file_path = '' or v_source.template_file_path is null then
        raise exception '源模板未发布（路径为空）：''%''', v_source_id;  -- 引用变量
    end if;
    ...
```

---

## 验证方式

- 4 个函数去掉 SECURITY DEFINER 后，用 admin 角色 RPC 调用均应正常
- `reuse_template` 的 3 个现有测试（test_reuse_copies_paths、test_reuse_self_raises、test_reuse_nonexistent_source_raises）均应通过
