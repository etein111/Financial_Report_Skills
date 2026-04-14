# Supabase 迁移文件 Squash 指南

将多个本地迁移文件合并为单个 dump-based 快照，适用于未推送到远端的开发阶段迁移。

## 适用条件

- 全部迁移文件未推送到远端，可安全替换
- 本地 Supabase 服务运行正常（`supabase start`）
- 在 worktree 中执行，main 分支不受影响

## 执行步骤

### 第 1 步：建立基线

```bash
# 记录 CLI 版本（验证时必须使用同一版本）
supabase --version > /tmp/cli_version.txt

# 用全部原始迁移文件重建数据库
supabase db reset

# 导出 public schema 最终状态
supabase db dump --local --schema public > /tmp/baseline_public.sql 2>/dev/null

# 导出 storage schema（用于后续 diff 对比）
supabase db dump --local --schema storage > /tmp/baseline_storage.sql 2>/dev/null

# 记录 RPC 烟雾测试基线值
psql "$DB_URL" -t -A -c "SELECT your_function('test_arg');" > /tmp/baseline_rpc.txt

# 记录 seed 数据行数基线
psql "$DB_URL" -t -A -c "SELECT 'table_a' AS tbl, count(*) FROM table_a
         UNION ALL SELECT 'table_b', count(*) FROM table_b" > /tmp/baseline_counts.txt
```

### 第 2 步：生成 squash 迁移

```bash
# 删除全部原始迁移文件
rm supabase/migrations/*.sql

# 创建新迁移文件
supabase migration new squash_all
```

将 `/tmp/baseline_public.sql` 内容写入新迁移文件，然后在末尾追加 dump 未捕获的补充项。

### 第 3 步：验证

见下文「验证流程」。

## dump 捕获范围

### 自动捕获（无需处理）

- 表 DDL（最终 CREATE TABLE 定义，含所有列、约束、索引）
- 函数（最新版本，中间版本自然丢弃）
- 触发器（绑定关系 + 触发函数）
- public schema RLS policy
- COMMENT ON（表、列、函数注释）
- Extension
- GRANT / REVOKE / ALTER DEFAULT PRIVILEGES

### 不捕获（必须手动补充）

需要检查项目迁移文件中是否包含以下内容，如有则手动追加到 dump 文件末尾：

| 缺失项 | 检查方式 | 典型语句 |
|--------|----------|----------|
| 数据库级配置 | `grep -i "ALTER DATABASE" supabase/migrations/*.sql` | `ALTER DATABASE postgres SET timezone TO '...'` |
| storage bucket policies | `grep -i "storage.objects" supabase/migrations/*.sql` | `CREATE POLICY ... ON storage.objects` |

补充 storage policies 时：
- 从原始迁移文件取最终版本（如果多个文件修改了同一 policy，以最后一个为准）
- 只保留 CREATE POLICY，不保留 DROP POLICY IF EXISTS（首次执行无需 DROP）

### 不受影响

- `seed.sql`：`supabase db reset` 在 migrations 之后独立执行
- storage bucket 定义：在 `supabase/config.toml` 中配置，由 CLI 创建
- auth schema：由 Supabase 托管

## 验证流程

### 核心验证：dump-diff

```bash
supabase db reset

# 确认 CLI 版本一致
supabase --version | diff - /tmp/cli_version.txt

# 导出 squash 后状态
supabase db dump --local --schema public > /tmp/after_public.sql 2>/dev/null
supabase db dump --local --schema storage > /tmp/after_storage.sql 2>/dev/null

# 对比
diff /tmp/baseline_public.sql /tmp/after_public.sql
diff /tmp/baseline_storage.sql /tmp/after_storage.sql
```

通过标准：diff 无实质性差异（见下文已知差异）。

### 补充验证 1：seed 数据

```bash
psql "$DB_URL" -t -A -c "SELECT 'table_a' AS tbl, count(*) FROM table_a ..." | diff - /tmp/baseline_counts.txt
```

通过标准：diff 为空。

### 补充验证 2：RPC 烟雾测试

```bash
psql "$DB_URL" -t -A -c "SELECT your_function('test_arg');" > /tmp/after_rpc.txt
diff /tmp/baseline_rpc.txt /tmp/after_rpc.txt
```

通过标准：diff 为空（排除系统生成名，见已知差异）。

### 补充验证 3：手动补充项

逐项确认 dump 未捕获的内容已生效（如 `SHOW timezone`）。

## 已知差异（非 squash 问题）

以下差异在 dump-diff 中会出现，但不影响功能正确性：

### 1. GRANT 语句排序不稳定

- `pg_dump` 按对象 OID 排序输出 GRANT 语句
- squash 后 OID 变化导致排序不同，但权限集合完全一致
- 验证方式：`diff <(grep "^GRANT\|^REVOKE" baseline.sql | sort) <(grep "^GRANT\|^REVOKE" after.sql | sort)`

### 2. FK 触发器名含 OID

- PostgreSQL 外键约束触发器名格式 `RI_ConstraintTrigger_a_XXXXX`（OID 生成）
- 每次数据库重建 OID 不同
- RPC 烟雾测试对比时过滤掉 `RI_ConstraintTrigger_*` 前缀

### 3. Supabase 默认 anon 函数权限泄露

- Supabase 通过 `ALTER DEFAULT PRIVILEGES ... GRANT ALL ON FUNCTIONS TO anon` 自动授权
- dump 的 `REVOKE ALL ON FUNCTION ... FROM PUBLIC` 不撤销直接授予 anon 的权限
- 必须在 squash 文件末尾追加：

```sql
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA public FROM anon;

-- 仅对需要 anon 访问的函数重新授权
GRANT ALL ON FUNCTION public.your_public_function() TO anon;
```

## 回滚方案

- worktree 隔离，main 分支不受影响
- squash 失败可 `git checkout .` 恢复全部原始文件
- 整体失败可删除 worktree，从 main 重新开始
