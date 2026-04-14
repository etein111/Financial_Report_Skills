# 迁移文件 Squash 设计

将 23 个本地迁移文件合并为 5 个有序文件，按关注点组织，不丢失任何信息。

## 前提

- 所有迁移未推送到远端，可安全 squash
- 本地 Supabase 服务运行正常

## 目标结构

| 序号 | 文件名 | 内容 | 来源迁移 |
|------|--------|------|----------|
| 000 | `_bootstrap.sql` | extensions、timezone、通用工具函数（`current_app_role`、`report_status_is_valid`、`set_updated_at_utc`） | 000_bootstrap |
| 010 | `_tables.sql` | 所有表的最终 DDL（含所有列、约束、索引） | 010_reference + 020_core + p1_iter_a/b 新增列 |
| 020 | `_functions.sql` | 所有 RPC 函数的最终版本 + COMMENT | 030~114 中所有函数，取最后出现的版本 |
| 030 | `_security.sql` | RLS enable/policies + storage policies | 040_security + 055_storage |
| 040 | `_triggers.sql` | 触发器函数 + trigger 绑定 | 030_triggers + p1_iter_b 的 status_log trigger |

## 执行步骤

1. **备份** `supabase/migrations/` 到 `/tmp/migrations_backup`
2. **reset + dump A**：用原始 23 个文件构建数据库，dump 作为基准快照
3. **手工提取**：遍历所有 23 个文件，按分类提取每个对象的最终版本
4. **写入新文件**：用 `supabase migration new` 生成 5 个文件，填入内容
5. **reset + dump B**：用新文件构建数据库，dump
6. **diff A B**：零差异 = 通过
7. **配置验证**：确认 timezone 为 `Asia/Shanghai`

## 提取规则

- **表 DDL**：取最终列状态的 `CREATE TABLE`，不保留中间的 `ALTER TABLE ADD COLUMN`
- **函数**：同一个函数被多次 `CREATE OR REPLACE`，只取最后出现的版本
- **COMMENT**：跟随对应的最终函数/表版本
- **DROP/移除操作**：被 drop 的对象不进入 squash（如 `105_remove_analyst_security_definer` 移除的 SECURITY DEFINER）

## 不丢失信息的保障

| 信息类型 | 保障手段 |
|----------|----------|
| 表/列/约束 | dump diff 捕获 |
| 函数签名和实现 | dump diff 捕获 |
| COMMENT ON | dump diff 捕获（pg_dump 包含注释） |
| RLS policies | dump diff 捕获 |
| 触发器绑定 | dump diff 捕获 |
| timezone 配置 | 单独 `pg_settings` 查询验证 |
| extensions | dump diff 捕获 |
| storage policies | dump diff 捕获 |

## 验证方法

三层验证，全部通过才算完成：

1. **双 dump 对比**：`diff schema_A.sql schema_B.sql`，零差异
2. **配置验证**：`pg_settings` 查询确认 timezone = `Asia/Shanghai`
3. **seed 验证**：`supabase db reset` 后查表计数一致

## 回滚方案

验证不通过时恢复 `/tmp/migrations_backup` 中的原始文件。
