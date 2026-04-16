# 设计文档：去掉 SECURITY DEFINER + reuse_template 拼接优化

> 日期：2026-04-15
> 来源：审查 `docs/todo/sql-optimize-validate-and-reuse.md` 后重新评估
> 优先级：P3
> 状态：待实现

---

## 背景

P2 schema redesign 后，`validate_report` 的 3 个原始优化项随架构变更自动解决（analyst_emails 移入 report 表、word_path/pdf_path 移入 report 表）。

本次清理聚焦两个遗留问题：

1. 全库 `SECURITY DEFINER` 审计——5 处中 4 处无必要
2. `reuse_template` 中重复字符串拼接

## 方案

逐函数判断是否保留 SECURITY DEFINER。去掉 4 处无必要的，保留 1 处（`create_coverage`，analyst 角色也需要调用）。

不扩大范围——不动 coverage 写入策略，不引入新的 RLS policy。

---

## 变更清单

### 变更 1：get_template_storage_paths — 去掉 SECURITY DEFINER

**文件：** squash 迁移第 139 行
**改动：** `LANGUAGE "sql" STABLE SECURITY DEFINER` → `LANGUAGE "sql" STABLE`

纯计算函数，拼接路径字符串返回，不读写任何表。SECURITY DEFINER 在此无作用。

### 变更 2：resolve_coverage — 去掉 SECURITY DEFINER

**文件：** squash 迁移第 377 行
**改动：** `LANGUAGE "plpgsql" STABLE SECURITY DEFINER` → `LANGUAGE "plpgsql" STABLE`

只读 coverage + coverage_analyst 两张表。SELECT 策略均为 `USING (true)`，所有 authenticated 用户可见。无需提权。

### 变更 3：reuse_template — 去掉 SECURITY DEFINER + 提取拼接变量

**文件：** squash 迁移第 446-479 行

#### 3a. 去掉 SECURITY DEFINER

`LANGUAGE "plpgsql" SECURITY DEFINER` → `LANGUAGE "plpgsql"`

调用方为 admin，RLS 策略 `dict_write` 已放行 admin 写入 report_template。

#### 3b. 提取重复拼接为变量

`p_same_as_report_type || '_' || p_language` 出现 3 次（第 459、463、468 行）。

提取为 `v_source_id text`，函数开头赋值一次，后续引用变量。

### 变更 4：upsert_template_record — 去掉 SECURITY DEFINER

**文件：** squash 迁移第 690-708 行
**改动：** `LANGUAGE "plpgsql" SECURITY DEFINER` → `LANGUAGE "plpgsql"`

同变更 3a，调用方为 admin。

### 不动

`create_coverage`（第 27 行）保留 SECURITY DEFINER——analyst 角色也需要创建 coverage。

---

## 验证

- 4 个函数去掉 SECURITY DEFINER 后，admin 角色 RPC 调用均应正常
- `reuse_template` 的 3 个现有测试通过：
  - test_reuse_copies_paths
  - test_reuse_self_raises
  - test_reuse_nonexistent_source_raises
- `resolve_coverage` 相关调用（create_report 流程）不受影响

## 不在范围内

- coverage 写入策略调整
- `create_coverage` 的 SECURITY DEFINER 处理
- `validate_report` 的 unnest 合并（性能影响可忽略）
- `reuse_template` 的 `= '' or ... is null` 简化为 nullif（用户确认不改）
