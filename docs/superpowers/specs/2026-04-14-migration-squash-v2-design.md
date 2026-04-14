# 迁移文件 Squash V2 设计：逐文件增量合并

将 24 个本地迁移文件逐个合并为 5 个按关注点组织的文件，每合并一个测试一次，每 5 轮做一次 dump 对比。

## 前提

- 所有 24 个迁移未推送到远端，可安全 squash
- 本地 Supabase 服务运行正常（`supabase start`）
- 在 worktree 中执行，main 分支不受影响

## 目标结构

| 序号 | 目标文件 | 内容 | 执行顺序 |
|------|----------|------|----------|
| 1 | `000_bootstrap.sql` | extensions、timezone、utility 函数 | 最先 |
| 2 | `010_tables.sql` | 所有表的 DDL | 第二 |
| 3 | `020_triggers.sql` | trigger 函数 + trigger 绑定 | 第三 |
| 4 | `030_security.sql` | RLS enable/policies + storage policies | 第四 |
| 5 | `040_functions.sql` | 所有 RPC 函数（含后续 schema 变更） | 最后 |

## 逐文件合并计划

### 第 0 轮：基线

```bash
supabase db reset
supabase db dump --local --schema public > /tmp/baseline.sql
```

### 第 1-5 轮

| 轮次 | 原始文件 | 操作 | 归入目标 |
|------|----------|------|----------|
| 1 | `000_bootstrap` | 直接作为目标文件 | `000_bootstrap.sql` |
| 2 | `010_reference_tables` | 创建目标文件 | `010_tables.sql` |
| 3 | `020_core_tables` | 追加到已有目标 | `010_tables.sql` |
| 4 | `030_table_functions_and_triggers` | 创建目标文件 | `020_triggers.sql` |
| 5 | `040_security` | 创建目标文件 | `030_security.sql` |

第 5 轮后验证：
- `supabase db reset`（每轮都做）
- `supabase db dump --local --schema public > /tmp/dump_5.sql`
- `diff /tmp/baseline.sql /tmp/dump_5.sql` — 零差异

### 第 6-10 轮

| 轮次 | 原始文件 | 操作 | 归入目标 |
|------|----------|------|----------|
| 6 | `045_analyst_functions` | 创建目标文件 | `040_functions.sql` |
| 7 | `050_template_functions` | 追加 | `040_functions.sql` |
| 8 | `055_storage_policies` | 追加 | `030_security.sql` |
| 9 | `056_template_path_prefix` | 追加 | `040_functions.sql` |
| 10 | `060_coverage_functions` | 追加 | `040_functions.sql` |

第 10 轮后 dump 对比。

### 第 11-15 轮

| 轮次 | 原始文件 | 操作 | 归入目标 |
|------|----------|------|----------|
| 11 | `070_draft_report_functions` | 追加 | `040_functions.sql` |
| 12 | `080_submit_report_function` | 追加 | `040_functions.sql` |
| 13 | `090_coverage_history_function` | 追加 | `040_functions.sql` |
| 14 | `100_submit_report_current_version` | 追加 | `040_functions.sql` |
| 15 | `105_remove_analyst_security_definer` | 追加 | `040_functions.sql` |

第 15 轮后 dump 对比。

### 第 16-20 轮

| 轮次 | 原始文件 | 操作 | 归入目标 |
|------|----------|------|----------|
| 16 | `110_retract_permission` | 追加 | `040_functions.sql` |
| 17 | `111_remove_rejected_to_submitted` | 追加 | `040_functions.sql` |
| 18 | `112_validate_report_rpc` | 追加 | `040_functions.sql` |
| 19 | `113_submit_report_call_validate` | 追加 | `040_functions.sql` |
| 20 | `114_validate_report_all_analysts` | 追加 | `040_functions.sql` |

第 20 轮后 dump 对比。

### 第 21-24 轮

| 轮次 | 原始文件 | 操作 | 归入目标 |
|------|----------|------|----------|
| 21 | `114_sql_error_messages_cn` | 追加 | `040_functions.sql` |
| 22 | `p1_iter_a_analyst_fields` | 追加 | `040_functions.sql` |
| 23 | `p1_iter_b_status_log_trigger` | 追加 | `040_functions.sql` |
| 24 | `p2_schema_redesign_phase_a` | 追加 | `040_functions.sql` |

第 24 轮后最终 dump 对比。

## 每轮执行流程

```
1. 读取原始迁移文件内容
2. 确定目标文件归属
3. 追加内容到目标文件（首个文件则创建）
4. 删除原始迁移文件
5. supabase db reset — 无错误则继续
6. 每 5 轮：supabase db dump + diff baseline — 零差异则继续
```

## 验证标准

| 验证类型 | 频率 | 通过标准 |
|----------|------|----------|
| `supabase db reset` | 每轮 | 无错误 |
| `db dump` diff baseline | 每 5 轮 + 最终 | 零差异 |
| seed 数据 | 最终 | 表计数一致 |

## 回滚方案

- worktree 隔离，main 分支不受影响
- 每轮可 `git checkout .` 恢复到该轮开始前状态
- 整体失败可删除 worktree，从 main 重新开始

## 文件命名

使用 `supabase migration new <name>` 生成带时间戳的文件名，创建后立即用目标名称内容填充。五个文件的时间戳顺序必须保持正确（bootstrap < tables < triggers < security < functions）。
