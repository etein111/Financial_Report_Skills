# Supabase Baseline Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 在仓库内建立可回放的 Supabase 基线目录，把当前本地数据库结构固化为 5 个初始化 migration，并配置 `init_seed.sql` 与独立的测试数据文件。

**Architecture:** 以当前本地 Supabase 数据库为唯一输入，先导出 `public` schema 作为参考，再按依赖顺序手工拆分为 5 个 migration。`000` 只放 bootstrap 级对象（扩展、数据库时区、无表依赖公用函数），表级约束和索引与各自表定义放在一起，表绑定函数与触发器单独放在后置 migration，最后再落 RLS、policy 与 grant。

**Tech Stack:** Supabase CLI 2.x、PostgreSQL、SQL migration、Docker 本地 Supabase

---

### Task 1: 建立 Supabase 目录骨架

**Files:**
- Create: `supabase/config.toml`
- Create: `supabase/seed.sql`
- Create: `supabase/seeds/init_seed.sql`
- Create: `supabase/tests/test_data.sql`
- Create: `supabase/migrations/20260409000100_000_bootstrap.sql`
- Create: `supabase/migrations/20260409000200_010_reference_tables.sql`
- Create: `supabase/migrations/20260409000300_020_core_tables.sql`
- Create: `supabase/migrations/20260409000400_030_table_functions_and_triggers.sql`
- Create: `supabase/migrations/20260409000500_040_security.sql`
- Modify: `.gitignore`

**Step 1: 初始化 Supabase 目录**

Run: `supabase init`
Expected: 生成 `supabase/config.toml` 和基础目录，不覆盖现有 `supabase/SUPABASE_STANDARDS.md`

**Step 2: 清理 CLI 自动生成但不需要入库的临时文件**

Run: `find supabase -maxdepth 2 -type f | sort`
Expected: 只保留将要纳管的配置与说明文件，不保留 `.temp/` 等中间产物

**Step 3: 配置 seed 目录**

写入 `supabase/config.toml`：

```toml
[db.seed]
enabled = true
sql_paths = ["./seeds/init_seed.sql"]
```

创建占位文件：

```sql
-- supabase/seeds/init_seed.sql
-- 初始化主数据，仅保留需要随 db reset 自动加载的稳定数据。
```

```sql
-- supabase/tests/test_data.sql
-- 测试数据，默认不随 db reset 自动执行，按需手工导入。
```

**Step 4: 忽略本地状态目录**

在 `.gitignore` 增加：

```gitignore
.supabase/
supabase/.temp/
```

**Step 5: 验证目录结构**

Run: `find supabase -maxdepth 2 -type f | sort`
Expected: 出现 `config.toml`、`seed.sql`、`seeds/init_seed.sql`、`tests/test_data.sql`、5 个 migration 文件

### Task 2: 导出本地数据库结构作为拆分参考

**Files:**
- Create: `/tmp/neoskills_public_schema.sql`
- Create: `/tmp/neoskills_public_policies.sql`
- Create: `/tmp/neoskills_public_grants.txt`

**Step 1: 导出 public schema**

Run: `supabase db dump --local --schema public -f /tmp/neoskills_public_schema.sql`
Expected: 成功导出当前 `public` schema，用于手工拆分 migration

**Step 2: 导出 policy 参考**

Run: `psql 'postgresql://postgres:postgres@127.0.0.1:54322/postgres' -P pager=off -c "select schemaname, tablename, policyname, qual, with_check from pg_policies where schemaname = 'public' order by tablename, policyname;" > /tmp/neoskills_public_policies.sql`
Expected: 保存当前 `public` policy 参考输出

**Step 3: 导出 grant 参考**

Run: `psql 'postgresql://postgres:postgres@127.0.0.1:54322/postgres' -P pager=off -c "select table_schema, table_name, grantee, string_agg(privilege_type, ', ' order by privilege_type) as privileges from information_schema.role_table_grants where table_schema = 'public' group by table_schema, table_name, grantee order by table_name, grantee;" > /tmp/neoskills_public_grants.txt`
Expected: 保存当前表级 grant 参考输出

**Step 4: 核对依赖前提**

Run: `psql 'postgresql://postgres:postgres@127.0.0.1:54322/postgres' -P pager=off -c "select extname from pg_extension order by 1;"`
Expected: 至少包含 `pgcrypto`，并确认当前业务对象不依赖 `uuid-ossp`

### Task 3: 编写 Bootstrap Migration

**Files:**
- Modify: `supabase/migrations/20260409000100_000_bootstrap.sql`

**Step 1: 写入扩展与数据库时区**

```sql
create extension if not exists pgcrypto with schema extensions;
alter database postgres set timezone to 'Asia/Shanghai';
```

**Step 2: 写入无表依赖的公用函数**

```sql
create or replace function public.current_app_role() returns text ...
create or replace function public.report_status_is_valid(from_status text, to_status text) returns boolean ...
create or replace function public.set_updated_at_utc() returns trigger ...
```

**Step 3: 检查函数边界**

规则：
- `validate_sector_hierarchy()` 不进入此文件，因为依赖 `public.sector`
- `report_enforce_status_transition()` 不进入此文件，因为依赖 `report_status_is_valid()` 且只服务 `report` 触发器

**Step 4: 验证 bootstrap 文件可读性**

Run: `sed -n '1,220p' supabase/migrations/20260409000100_000_bootstrap.sql`
Expected: 只包含扩展、时区设置、公用函数，不包含任何建表语句

### Task 4: 编写 Reference Tables Migration

**Files:**
- Modify: `supabase/migrations/20260409000200_010_reference_tables.sql`

**Step 1: 依次写入参考/字典表**

表顺序：
1. `analyst`
2. `rating`
3. `region`
4. `report_type`
5. `report_template`
6. `sector`

**Step 2: 每张表内部保持如下结构**

```sql
create table if not exists public.<table> (...);
alter table public.<table> enable row level security; -- 暂不写，这一步不要做
create unique index ...;
create index ...;
```

约束规则：
- 主键、唯一约束、check 直接写在 `create table`
- 与该表强绑定的索引紧跟在表定义后
- 不在此文件创建触发器

**Step 3: sector 特别规则**

`sector` 表定义中保留：
- `sector_level_check`
- `sector_level_parent_check`
- 表级索引

但不要在此文件创建：
- `validate_sector_hierarchy()`
- `trg_sector_hierarchy`
- `trg_sector_updated_at`

**Step 4: 验证表内对象完整性**

Run: `sed -n '1,260p' supabase/migrations/20260409000200_010_reference_tables.sql`
Expected: 每张表后紧跟本表索引，未混入触发器和 policy

### Task 5: 编写 Core Tables Migration

**Files:**
- Modify: `supabase/migrations/20260409000300_020_core_tables.sql`

**Step 1: 按外键依赖顺序写表**

顺序：
1. `coverage`
2. `report`
3. `coverage_analyst`
4. `report_analyst`
5. `report_status_log`
6. `report_version`

**Step 2: 每张表内保留当前真实结构**

要求：
- `id default gen_random_uuid()` 原样保留
- 现有 check 原样保留
- 仅保留当前真实存在的外键，不额外补新外键
- 每张表的索引紧跟本表定义

**Step 3: 特别注意 report 系列表**

依赖关系：
- `report_analyst` 依赖 `report`
- `report_status_log` 依赖 `report`
- `report_version` 依赖 `report`

因此 `report` 必须先定义，再定义 3 张子表

**Step 4: 验证核心表顺序**

Run: `sed -n '1,320p' supabase/migrations/20260409000300_020_core_tables.sql`
Expected: `report` 出现在所有 `report_*` 子表之前，`coverage` 出现在 `coverage_analyst` 之前

### Task 6: 编写表绑定函数与触发器 Migration

**Files:**
- Modify: `supabase/migrations/20260409000400_030_table_functions_and_triggers.sql`

**Step 1: 写入表绑定函数**

顺序：
1. `validate_sector_hierarchy()`
2. `report_enforce_status_transition()`

依赖说明：
- `validate_sector_hierarchy()` 读取 `public.sector`
- `report_enforce_status_transition()` 调用 `public.report_status_is_valid()`

**Step 2: 创建触发器**

按表分组创建：
- `analyst`, `coverage`, `coverage_analyst`, `region`, `report`, `report_analyst`, `report_template`, `report_type`, `sector` 的 `updated_at` 触发器
- `sector` 的层级校验触发器
- `report` 的状态流转触发器

**Step 3: 保持触发器顺序**

规则：
- 先 `create or replace function`
- 后 `create trigger`
- `report` 先挂 `set_updated_at_utc()`，再挂状态流转触发器

**Step 4: 验证触发器文件**

Run: `sed -n '1,260p' supabase/migrations/20260409000400_030_table_functions_and_triggers.sql`
Expected: 只包含表绑定函数和触发器，不包含 RLS / policy / grant

### Task 7: 编写 Security Migration

**Files:**
- Modify: `supabase/migrations/20260409000500_040_security.sql`

**Step 1: 启用 RLS**

对 12 张 `public` 表执行：

```sql
alter table public.<table> enable row level security;
```

**Step 2: 按依赖顺序创建 policy**

推荐顺序：
1. `analyst`
2. `rating`
3. `region`
4. `report_type`
5. `report_template`
6. `sector`
7. `coverage`
8. `coverage_analyst`
9. `report`
10. `report_analyst`
11. `report_status_log`
12. `report_version`

说明：
- 所有 policy 依赖 `current_app_role()`
- `report_*` 三张子表的 policy 还依赖 `report`
- 因此先建 `report` policy，再建其子表 policy

**Step 3: 写入 grant**

保留当前真实行为：
- 表级 grant 按当前库导出结果恢复
- 函数执行权限按当前库导出结果恢复

**Step 4: 验证安全文件**

Run: `sed -n '1,360p' supabase/migrations/20260409000500_040_security.sql`
Expected: 只包含 RLS、policy、grant，不包含建表或触发器定义

### Task 8: 配置与验证 Seed 文件

**Files:**
- Modify: `supabase/config.toml`
- Modify: `supabase/seed.sql`
- Modify: `supabase/seeds/init_seed.sql`
- Modify: `supabase/tests/test_data.sql`

**Step 1: 统一 seed 入口**

`supabase/seed.sql` 只做兼容性说明：

```sql
-- Legacy entrypoint kept for compatibility.
-- Primary seed file is supabase/seeds/init_seed.sql.
```

**Step 2: 编写 init seed**

原则：
- 只放稳定初始化数据
- 不写 DDL
- 语句幂等，优先 `insert ... on conflict do nothing`

**Step 3: 编写 test data**

原则：
- 只放测试或演示用数据
- 不纳入 `config.toml` 的 `sql_paths`

**Step 4: 验证 seed 配置**

Run: `sed -n '1,220p' supabase/config.toml`
Expected: `sql_paths` 只包含 `./seeds/init_seed.sql`

### Task 9: 验证 Baseline 可回放

**Files:**
- Modify: `supabase/migrations/20260409000100_000_bootstrap.sql`
- Modify: `supabase/migrations/20260409000200_010_reference_tables.sql`
- Modify: `supabase/migrations/20260409000300_020_core_tables.sql`
- Modify: `supabase/migrations/20260409000400_030_table_functions_and_triggers.sql`
- Modify: `supabase/migrations/20260409000500_040_security.sql`
- Modify: `supabase/seeds/init_seed.sql`

**Step 1: 从零重建本地数据库**

Run: `supabase db reset`
Expected: 所有 migration 顺序执行成功，`init_seed.sql` 自动执行成功

**Step 2: 核对关键对象**

Run: `psql 'postgresql://postgres:postgres@127.0.0.1:54322/postgres' -P pager=off -c "select tablename from pg_tables where schemaname = 'public' order by 1;"`
Expected: 返回 12 张业务表

**Step 3: 核对关键函数**

Run: `psql 'postgresql://postgres:postgres@127.0.0.1:54322/postgres' -P pager=off -c "select proname from pg_proc p join pg_namespace n on n.oid = p.pronamespace where n.nspname = 'public' order by 1;"`
Expected: 至少包含 `current_app_role`、`report_status_is_valid`、`set_updated_at_utc`、`validate_sector_hierarchy`、`report_enforce_status_transition`

**Step 4: 核对数据库时区**

Run: `psql 'postgresql://postgres:postgres@127.0.0.1:54322/postgres' -P pager=off -c "show timezone;"`
Expected: `Asia/Shanghai`

**Step 5: 核对 RLS**

Run: `psql 'postgresql://postgres:postgres@127.0.0.1:54322/postgres' -P pager=off -c "select relname, relrowsecurity from pg_class c join pg_namespace n on n.oid = c.relnamespace where n.nspname = 'public' and c.relkind = 'r' order by relname;"`
Expected: 12 张表的 `relrowsecurity` 都为 `t`

**Step 6: 提交**

```bash
git add .gitignore supabase/config.toml supabase/seed.sql supabase/seeds/init_seed.sql supabase/tests/test_data.sql supabase/migrations docs/plans/2026-04-09-supabase-baseline.md
git commit -m "chore: add supabase baseline migrations"
```
