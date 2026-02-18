# Supabase 数据库版本管理规范

本规范基于 Supabase 官方 Local Development 指引整理，定义本项目数据库版本管理的职责边界与执行方式。

## 1. 职责边界（强制）

- `supabase db push`：只负责 schema（`supabase/migrations/*.sql`）。
- `supabase seed --local`：只负责 SQL seed（由 `supabase/config.toml` 的 `[db.seed].sql_paths` 决定）。
- `supabase/seed.ts`：只负责 Auth 用户初始化与需要程序逻辑的初始化。

禁止项：
- 禁止在 migration 中写业务 seed 数据。
- 禁止通过 SQL 直接写 `auth.users`。
- Auth 用户写入规则以 `docs/DECISIONS.md` 的 `D-014` 为主定义。

## 2. 推荐目录结构

```text
supabase/
  migrations/
    001_init.sql
    002_rls_and_triggers.sql
  seed/
    01_base.sql
    02_demo.sql          # 可选，本地/测试
  seed.ts                # Auth 初始化（Admin API）
  config.toml
scripts/
  db-init.sh             # 一键执行 push + seed + seed.ts
```

## 3. `config.toml` 约定

`[db.seed].sql_paths` 是 SQL seed 的唯一入口配置。可写单文件、数组或通配符。

示例（不使用总入口 `seed.sql`）：

```toml
[db.seed]
enabled = true
sql_paths = ["./seed/01_base.sql", "./seed/02_demo.sql"]
```

说明：
- 推荐显式列出文件，保证执行顺序稳定。
- 也可用 `./seed/*.sql`，但顺序可控性较弱。
- `supabase db reset` 默认会在重置后运行 seed；可用 `--no-seed` 跳过。

## 4. Migrations 规范

- 仅包含：表结构、索引、约束、函数、触发器、RLS policy。
- 允许定义 `auth.users` 触发器（如自动补齐 `profiles`），但不允许直接插入 Auth 用户。
- migration 必须可审查、可回放，不依赖临时环境状态。

## 5. SQL Seed 规范

- 只放业务基础静态数据（字典表、配置表、缺省值、可选 demo 数据）。
- 全部幂等：`on conflict do update` 或 `on conflict do nothing`。
- 测试专用数据不进入公共 seed 文件。

## 6. `seed.ts` 规范（Auth + 逻辑初始化）

本节只定义规则，不内嵌示例代码。

- 必须只读取：
  - `SUPABASE_URL`
  - `SUPABASE_SERVICE_ROLE_KEY`
- 必须通过 `supabase.auth.admin.*` 创建/更新 Auth 用户。
- 必须先查后建（按 email），重复执行结果一致。
- 业务侧映射表（如 `user_roles` / `profiles`）统一 `upsert`。
- `seed.ts` 失败时必须非零退出并打印可定位错误。

## 7. 一键初始化命令

`scripts/db-init.sh`：

```bash
#!/usr/bin/env bash
set -euo pipefail

supabase db push
supabase seed --local
pnpm -s run seed:auth
```

`package.json`：

```json
{
  "scripts": {
    "seed:auth": "tsx supabase/seed.ts",
    "db:init": "bash scripts/db-init.sh"
  }
}
```

## 8. 环境与安全

- `SUPABASE_SERVICE_ROLE_KEY` 仅用于服务端脚本与 CI Secret。
- 默认账号密码仅允许本地/测试使用；生产环境通过安全渠道注入与轮换。
- 若配置文件中使用 `env()`，仅用于声明变量来源，不应提交真实密钥。

## 9. 参考

- Supabase Local Development Overview：`https://supabase.com/docs/guides/local-development/overview`
- Supabase CLI Config Reference：`https://supabase.com/docs/guides/local-development/cli/config`
