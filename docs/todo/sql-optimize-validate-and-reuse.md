# SQL 函数优化：validate_report + reuse_template

> 记录日期：2026-04-13
> 来源：/simplify 代码审查
> 优先级：P2（当前数据量下不构成性能瓶颈）
> 前置条件：下次修改这些函数时顺便优化

---

## 变更 1：validate_report — count(*) 改 exists()

**文件：** 迁移文件中 `validate_report` 函数
**当前（约第 75-80 行）：**

```sql
select count(*)
  into v_analyst_count
  from public.report_analyst
 where report_id = p_report_id;

if v_analyst_count = 0 then
    v_errors := v_errors || '报告没有分析师（report_analyst 为空）';
```

**改为：**

```sql
if not exists (
    select 1 from public.report_analyst where report_id = p_report_id
) then
    v_errors := v_errors || '报告没有分析师（report_analyst 为空）';
```

**原因：** `exists()` 在找到第一行后立即返回，`count(*)` 会扫描全部行。同时可删除 `v_analyst_count` 变量声明。

---

## 变更 2：validate_report — 合并两次 report_analyst 查询

**当前：** 分析师校验段查了两次 `report_analyst`：
1. 检查 contact_person 是否在分析师列表中（EXISTS 子查询）
2. LEFT JOIN analyst 收集问题分析师（FOR LOOP）

**改为：** 用一次查询同时完成两项检查，将 contact_person 判断整合进 FOR LOOP 结果集。

---

## 变更 3：validate_report — report + report_version 合并为一次 JOIN

**当前：** report 行和 report_version 行分两次 SELECT INTO 获取。

**改为：** 用 LEFT JOIN 一次查出 report + version 字段，减少一次查询往返：

```sql
select r.status, r.current_version_no, r.title, ...
       rv.word_file_path, rv.pdf_file_path
  into v_report
  from public.report r
  left join public.report_version rv
    on rv.report_id = r.id and rv.version_no = r.current_version_no
 where r.id = p_report_id;
```

**注意：** 需要调整后续条件分支逻辑（version 字段在 LEFT JOIN 无匹配时为 null）。

---

## 变更 4：reuse_template — 提取重复拼接为变量

**文件：** 迁移文件中 `reuse_template` 函数
**当前：** `p_same_as_report_type || '_' || p_language` 出现 3 次（SELECT、两个 RAISE EXCEPTION）。

**改为：** 声明变量 `v_source_id text;`，在函数开头赋值一次，后续引用变量。

```sql
declare
    v_source    public.report_template%rowtype;
    v_source_id text;
    v_target_id text;
begin
    v_source_id := p_same_as_report_type || '_' || p_language;

    select * into v_source
    from public.report_template
    where id = v_source_id;

    if not found then
        raise exception '源模板未找到：''%''', v_source_id;
    end if;

    if nullif(v_source.template_file_path, '') is null then
        raise exception '源模板未发布（路径为空）：''%''', v_source_id;
    end if;
    ...
```

**附带优化：** `= '' or is null` 简化为 `nullif(..., '') is null`。
