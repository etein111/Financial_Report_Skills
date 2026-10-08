# 迁移文件 Squash V2 设计：dump snapshot 方案

将 24 个本地迁移文件合并为 1 个 dump-based 迁移文件，通过 dump-diff 验证零信息丢失。

## 背景

当前 `supabase/migrations/` 下有 24 个迁移文件（时间戳 20260409000100 ~ 20260414035951），全部未推送到远端。文件包含迭代过程中的 ALTER TABLE 链、函数版本替换（v1→v2→v3）、DROP + CREATE 交替操作。目标不是"合并变更历史"，而是"得到最终数据库快照"。

## 方案选择

| 方案 | 做法 | 不选原因 |
|------|------|----------|
| A: CLI squash | `supabase migration squash` | 已知 bug：混入 auth/storage 托管 schema (#4574)、删除 storage schema (#1493)、丢失 SQL 语句 (#1618) |
| B: Declarative Schemas | `supabase/schemas/*.sql` 声明目标状态 | `migra` diff 工具无法追踪 COMMENT ON 语句；本项目有 156 条注释 |
| **C: 手动 dump** | `supabase db dump` 导出最终状态，手动补充 dump 未捕获的 2 项 | **选定方案** |

## 信息捕获分析

### dump 自动捕获（无需处理）

| 对象类型 | 数量 | 说明 |
|---------|------|------|
| 表 DDL | 全部 | 最终 CREATE TABLE 定义，含所有列、约束、索引 |
| 函数 | 全部 | 最新版本，中间版本自然丢弃（squash 目的） |
| 触发器 | 2 个 CREATE TRIGGER | 绑定关系 + 触发函数 |
| public schema RLS policy | 全部 | CREATE POLICY 完整定义 |
| COMMENT ON | **156 条**（20 个文件） | 表、列、函数注释全部保留 |
| Extension | pgcrypto | 含 schema 限定 |
| CREATE SCHEMA | extensions | 自动包含 |

### dump 不捕获（必须手动补充）

| 缺失项 | 来源 | 补充方式 |
|--------|------|----------|
| `ALTER DATABASE postgres SET timezone TO 'Asia/Shanghai'` | `bootstrap.sql:5` | 手动追加到 dump 文件末尾；`pg_dump` 不导出数据库级配置（属于 `pg_database` 系统目录） |
| storage bucket policies（`storage.objects` 上 9 条 policy） | `055_storage_policies.sql` 创建全部 9 条；`110_retract_permission.sql` 覆盖其中 `reports_insert` 和 `reports_update` | 从原始迁移文件取最终版本（以 055 为基础，用 110 中对应 2 条替换），追加到 dump 文件。不从 storage schema dump 中提取，因为该 dump 包含桶定义等 Supabase 托管内容 |

### 不受影响（无需处理）

| 内容 | 原因 |
|------|------|
| seed.sql | `supabase db reset` 在 migrations 之后独立执行 |
| storage bucket 定义（templates、reports） | 定义在 `supabase/config.toml`，由 CLI 创建，不在迁移文件中 |
| auth schema | 由 Supabase 托管，不属于 public schema |
| GRANT / REVOKE | 全部 24 个迁移文件中 0 条 GRANT/REVOKE 语句 |

## 执行步骤

### 第 1 步：建立基线

```bash
# 记录 CLI 版本（验证时必须使用同一版本）
supabase --version > /tmp/cli_version.txt

# 用全部 24 个原始迁移文件重建数据库
supabase db reset

# 导出 public schema 最终状态
supabase db dump --local --schema public > /tmp/baseline_public.sql

# 导出 storage schema 最终状态（仅用于后续 diff 对比，不用于拼接）
supabase db dump --local --schema storage > /tmp/baseline_storage.sql

# 记录 RPC 烟雾测试基线值（用于第 3 步对比）
psql -c "SELECT public.report_status_is_valid('draft', 'submitted');" > /tmp/baseline_rpc.txt
psql -c "SELECT public.report_status_is_valid('draft', 'published');" >> /tmp/baseline_rpc.txt
psql -c "SELECT public.current_app_role();" >> /tmp/baseline_rpc.txt
psql -c "SELECT tgname FROM pg_trigger WHERE tgrelid = 'public.report'::regclass ORDER BY tgname;" >> /tmp/baseline_rpc.txt

# 记录 seed 数据行数基线
psql -c "SELECT 'report_template' AS tbl, count(*) FROM report_template
         UNION ALL SELECT 'rating', count(*) FROM rating
         UNION ALL SELECT 'region', count(*) FROM region
         UNION ALL SELECT 'report_type', count(*) FROM report_type
         UNION ALL SELECT 'sector', count(*) FROM sector
         UNION ALL SELECT 'analyst', count(*) FROM analyst" > /tmp/baseline_counts.txt
```

### 第 2 步：生成 squash 迁移

```bash
# 删除全部 24 个原始迁移文件
rm supabase/migrations/*.sql

# 用 supabase migration new 创建带时间戳的新迁移文件
supabase migration new squash_all
# 得到类似 supabase/migrations/20260414HHMMSS_squash_all.sql
```

将 `/tmp/baseline_public.sql` 内容写入新迁移文件，然后追加手动补充项：

```sql
-- ===== 以下为 dump 未捕获的补充项 =====

-- 1. 数据库时区设置（ALTER DATABASE 不在 pg_dump 范围内）
-- supabase db reset 的执行顺序：重建空库 → 运行 migrations → 运行 seed
-- 因此 ALTER DATABASE 在每次 reset 时随迁移文件重新执行，持久生效
ALTER DATABASE postgres SET timezone TO 'Asia/Shanghai';

-- 2. storage bucket policies
-- 从原始迁移文件取最终版本：以 055_storage_policies.sql 为基础，
-- 用 110_retract_permission.sql 中的 reports_insert 和 reports_update 替换对应条目
-- 注意：只粘贴 CREATE POLICY 语句，不粘贴 DROP POLICY IF EXISTS（首次执行无需 DROP）
```

### 第 3 步：验证（见下节）

## 验证流程

### 核心验证：dump-diff

验证原理：`supabase db dump` 内部调用 `pg_dump`，导出数据库的声明式当前状态。同版本 `pg_dump` + 同参数对同一数据库的输出完全确定（pg_dump 从 PostgreSQL 12 起不在输出中包含 OID，输出纯文本完全由 schema 内容决定）。**两个数据库的 dump 输出文本完全相同，则两个数据库逻辑上完全等价。**

注意：diff 比较的是**数据库状态**（两侧均为 pg_dump 输出），不是迁移文件内容。只要迁移文件产生了相同的数据库状态，diff 就会通过。

```bash
# squash 后重建
supabase db reset

# 确认 CLI 版本与基线一致
supabase --version | diff - /tmp/cli_version.txt

# 导出 squash 后状态
supabase db dump --local --schema public > /tmp/after_squash_public.sql
supabase db dump --local --schema storage > /tmp/after_squash_storage.sql

# 对比——零差异即通过
diff /tmp/baseline_public.sql /tmp/after_squash_public.sql
diff /tmp/baseline_storage.sql /tmp/after_squash_storage.sql
```

通过标准：
- `diff` 输出为空（零差异）
- `supabase db reset` 过程无错误

### 补充验证 1：seed 数据

```bash
# 检查关键表行数并与基线对比
psql -c "SELECT 'report_template' AS tbl, count(*) FROM report_template
         UNION ALL SELECT 'rating', count(*) FROM rating
         UNION ALL SELECT 'region', count(*) FROM region
         UNION ALL SELECT 'report_type', count(*) FROM report_type
         UNION ALL SELECT 'sector', count(*) FROM sector
         UNION ALL SELECT 'analyst', count(*) FROM analyst" | diff - /tmp/baseline_counts.txt
```

通过标准：diff 为空（行数一致）。

### 补充验证 2：RPC 烟雾测试

dump-diff 验证结构一致性，不验证运行时行为。必须调用关键 RPC 并与第 1 步记录的基线对比：

```bash
# 执行与第 1 步相同的查询，对比基线
psql -c "SELECT public.report_status_is_valid('draft', 'submitted');" > /tmp/after_rpc.txt
psql -c "SELECT public.report_status_is_valid('draft', 'published');" >> /tmp/after_rpc.txt
psql -c "SELECT public.current_app_role();" >> /tmp/after_rpc.txt
psql -c "SELECT tgname FROM pg_trigger WHERE tgrelid = 'public.report'::regclass ORDER BY tgname;" >> /tmp/after_rpc.txt
diff /tmp/baseline_rpc.txt /tmp/after_rpc.txt
```

通过标准：diff 为空（返回值一致）。

### 补充验证 3：时区设置

```sql
-- 确认数据库级时区已正确设置
SHOW timezone;  -- 期望 'Asia/Shanghai'
```

## 验证盲区

dump-diff 验证存在以下无法覆盖的场景：

### 盲区 1：storage bucket 定义依赖 config.toml

- **现象**：storage policies 引用 `templates` 和 `reports` 两个 bucket，bucket 定义在 `config.toml` 而非迁移文件中
- **风险**：如果 `config.toml` 中 bucket 定义被删除，policies 会指向不存在的 bucket，但 dump-diff 不会发现（因为 dump 只检查 SQL 对象，不检查 bucket 是否存在）
- **缓解**：squash 前确认 `config.toml` 中 `[storage.buckets.templates]` 和 `[storage.buckets.reports]` 配置完整

### 盲区 2：dump-diff 验证结构一致性，不验证运行时行为

- **现象**：diff 为零只证明两张数据库的 schema 定义文本相同，不证明函数逻辑在业务场景下正确执行
- **风险**：如果 dump 过程中函数定义被截断或损坏（极低概率），diff 仍可通过（因为两边截断方式相同）
- **缓解**：补充验证 2 中的 RPC 烟雾测试覆盖关键路径

### 盲区 3：seed.sql 中的 auth.users 依赖

- **现象**：`seed.sql` 向 `auth.users` 插入管理员账户，auth schema 由 Supabase 托管，不在 dump 范围内
- **风险**：如果 Supabase 版本升级导致 `auth.users` 表结构变化，seed 中的 INSERT 可能失败。此风险与 squash 无关（squash 不改变 seed.sql），但容易误归因到 squash
- **缓解**：squash 验证时记录 Supabase CLI 版本，问题排查时排除 squash 因素

### 盲区 4：pg_dump 版本一致性

- **现象**：不同版本的 `pg_dump` 对同一数据库可能产生格式不同的输出（注释位置、空白、引用方式）
- **风险**：如果基线和 squash 使用不同 CLI 版本，diff 会产生大量格式差异，掩盖真实问题或制造假阳性
- **缓解**：记录基线 dump 时的 CLI 版本（`supabase --version`），验证时使用同一版本

### 盲区 5：migrations 元数据表

- **现象**：`supabase_migrations.schema_migrations` 表记录已执行的迁移列表，squash 前有 24 条记录，squash 后只有 1 条
- **风险**：如果外部工具或 CI 脚本依赖此表的记录数或文件名，squash 后行为变化
- **缓解**：全局搜索代码库中对 `schema_migrations` 的引用，确认无依赖

### 盲区 6（执行中发现）：Supabase 默认权限导致 anon 函数泄露

- **现象**：Supabase 通过 `ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON FUNCTIONS TO anon` 为 anon 角色自动授权所有函数。`pg_dump` 输出的 `REVOKE ALL ON FUNCTION ... FROM PUBLIC` 只撤销 PUBLIC 伪角色的权限，不撤销直接授予 `anon` 角色的权限。squash 后 RPC 函数（create_coverage、submit_report 等）对 anon 意外暴露
- **影响**：squash 后多出 14 条 `GRANT ALL ON FUNCTION ... TO anon`（对比 baseline），均为不应被 anon 访问的 RPC 函数
- **缓解**：在 squash 迁移文件末尾追加 `REVOKE ALL ON ALL FUNCTIONS IN SCHEMA public FROM anon;` 然后仅对 6 个安全辅助函数（current_app_role、report_enforce_status_transition、report_status_is_valid、report_write_status_log、set_updated_at_utc、validate_sector_hierarchy）重新 GRANT
- **根因**：原始迁移文件用 `REVOKE EXECUTE ON FUNCTION ... FROM public, anon` 显式移除 anon 权限，但 dump 只输出 `REVOKE ALL FROM PUBLIC`，丢失了对 `anon` 角色的撤销

### 盲区 7（执行中发现）：GRANT 语句排序不稳定

- **现象**：`pg_dump` 按对象 OID 排序输出 GRANT 语句。squash 后数据库重建，OID 与 baseline 不同，导致 GRANT 语句顺序变化。逐行 `diff` 会报告差异，但语义完全等价
- **影响**：核心验证的 `diff baseline.sql after_squash.sql` 不会得到零差异，需要用排序后的 GRANT 集合对比
- **缓解**：核心验证改为两步：1) 排除 GRANT/REVOKE 后 diff（零差异 = 结构一致）；2) 排序后对比 GRANT/REVOKE 集合（零差异 = 权限一致）

### 盲区 8（执行中发现）：FK 触发器名含 OID

- **现象**：PostgreSQL 外键约束触发器名格式为 `RI_ConstraintTrigger_a_XXXXX`（XXXXX 为 OID），每次数据库重建 OID 不同
- **影响**：RPC 烟雾测试中 `pg_trigger` 查询结果包含 FK 触发器名，与 baseline 不匹配
- **缓解**：RPC 烟雾测试对比时过滤掉 `RI_ConstraintTrigger_*` 前缀的触发器，只比较业务触发器

## 执行结果

已完成 squash，验证全部通过：

| 验证项 | 结果 |
|--------|------|
| public dump（排除 GRANT/REVOKE） | 零差异 |
| public dump（GRANT/REVOKE 排序后集合） | 零差异 |
| storage dump | 零差异 |
| seed 数据行数（6 张表） | 零差异 |
| RPC 烟雾测试（业务触发器） | 零差异 |
| 时区设置 | `Asia/Shanghai` |

squash 迁移文件：`supabase/migrations/20260414090824_squash_all.sql`（2052 行）
原始文件：24 个迁移文件已删除

## 前提条件

- 所有 24 个迁移未推送到远端，可安全替换
- 本地 Supabase 服务运行正常（`supabase start`）
- 在 worktree 中执行，main 分支不受影响
- 记录当前 `supabase --version` 输出

## 回滚方案

- worktree 隔离，main 分支不受影响
- squash 失败可 `git checkout .` 恢复全部 24 个原始文件
- 整体失败可删除 worktree，从 main 重新开始
