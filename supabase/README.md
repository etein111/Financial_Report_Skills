# Supabase 目录说明与版本管理规范

本目录承载项目的 Supabase 配置、数据库迁移与种子数据，是数据库版本管理的唯一事实源。

原则：
- **所有 schema/RLS 变更必须通过 `supabase/migrations/*.sql` 管理**，不要在 Dashboard 里“手改完就算了”。
- **Auth/Users 相关的业务约束**（默认 Admin、RLS 策略等）同样要落在迁移里，保证可重放、可审计、可协作。
- **密钥不进 Git**：本目录下的 `*.token` / DB 密码文件仅用于本机开发，仓库已在 `.gitignore` 忽略。

## 目录结构与职责

```
supabase/
  config.toml                   # Supabase 项目配置（本地端口 + 云端 Auth/Redirect 等）
  migrations/                   # 数据库迁移（唯一版本历史）
  seed/                         # 种子数据（可选执行）
  .temp/                        # CLI 临时文件（不提交）
  supabase_access.token         # Supabase PAT（只用于本机 CLI/管理 API）
  supabase_db_password.token    # 远端 Postgres `postgres` 用户密码（只用于本机 db push）
```

### `config.toml`

这里既包含本地开发端口，也包含云端 Auth 配置（例如 `site_url`、`additional_redirect_urls`、`enable_signup=false`）。

约定：
- `auth.enable_signup = false` 必须保持关闭（invite-only）。
- `auth.site_url` 必须匹配本地 dev URL（默认 `http://localhost:3000`）。
- `auth.additional_redirect_urls` 必须覆盖 `http://localhost:3000/**`（便于 `/auth/callback`）。

### `migrations/`

迁移文件命名规则：`YYYYMMDDHHMMSS_description.sql`（UTC 时间戳，秒级）。

硬约定：
- **迁移一旦合入，不回改**。修正用“新迁移”覆盖。
- 迁移尽量**幂等**（`create ... if not exists`、`drop policy if exists`、`create or replace function`），以支持“重建库/重跑迁移”。
- 时间字段：`timestamptz default now()`，禁止 `timezone('Asia/Shanghai', now())` 写入 `timestamptz`（展示层再做 `Asia/Shanghai` 转换）。
- RLS 策略：角色判断必须用 `auth.jwt()->'app_metadata'->>'role'`。

### `seed/`

种子数据通过 `config.toml` 的 `[db.seed]` 管理，使用 `supabase db push --include-seed` 执行。

约定：
- seed 应尽量幂等（例如 `insert ... on conflict do nothing`）。
- seed 不写入“带时区语义容易误解”的时间数据。

### `*.token`

本仓库采用“文件落盘”而不是把 token 发进聊天的方式：
- `supabase/supabase_access.token`：Supabase Personal Access Token（PAT），用于 CLI 调 Supabase 管理 API。
- `supabase/supabase_db_password.token`：远端数据库密码，用于 `supabase db push` 的 `-p` 参数。

安全要求：
- 这两个文件**绝不能提交 Git**（仓库已忽略 `*.token`）。
- 若 token 泄漏，必须立刻在 Supabase 侧 revoke/rotate。

## 标准工作流（推荐）

下面工作流覆盖“新变更 -> 迁移 -> 推送云端 -> 验证 -> 回滚策略”的完整闭环。

### 0. 准备：配置 CLI 认证

两种方式二选一：

1. 环境变量（临时、不会落盘）：
```powershell
$env:SUPABASE_ACCESS_TOKEN = (Get-Content -Raw supabase/supabase_access.token).Trim()
```

2. `supabase login --token`（会写入本机 Supabase CLI 配置）：
```powershell
supabase login --token (Get-Content -Raw supabase/supabase_access.token).Trim()
```

### 1. 关联项目（link）

只要更换了 Supabase 项目（新建 project、重建 project ref），必须重新 link：
```powershell
supabase link --project-ref <project-ref>
```

说明：
- link 会更新 `supabase/.temp/*`（已忽略，不提交）。

### 2. 推送配置（config push）

把 `supabase/config.toml` 的 Auth/Redirect 等配置推到云端：
```powershell
supabase config push --project-ref <project-ref> --yes
```

经验：
- `config push` 会显示 diff。确认无意外项再推，避免误改邮件/MFA 默认配置。
- 本项目已明确要求：关闭 signup、设置 site_url 与 redirect urls。

### 3. 编写迁移（migrations）

迁移内容建议遵循这些实践：
- extension：`create extension if not exists ...;`
- trigger/function：`create or replace function ...;`
- policy：先 `drop policy if exists ...` 再 `create policy ...`
- 表：`create table if not exists ...`

### 4. 推送迁移到云端（db push）

注意：本机安装的 Supabase CLI（例如 `2.75.0`）`db push` 默认推送到 linked project，
且**不支持** `--project-ref` 参数（这是常见踩坑点）。

远端 push 标准命令（含 seed）：
```powershell
$pw = (Get-Content -Raw supabase/supabase_db_password.token).Trim()
supabase db push --include-seed -p $pw --yes
```

### 5. 验证迁移是否生效（migration list）

```powershell
supabase migration list --linked
```

你应该看到 Local/Remote 的版本对齐。

### 6. 验收脚本（不依赖 Docker/psql）

为避免本机缺 Docker/psql 导致无法验收，我补了两个脚本：

- DB 直连验收（默认 Admin 幂等 + RLS）：`web/scripts/verify/verify-db-admin-and-rls.mjs`
```powershell
cd web
node scripts/verify/verify-db-admin-and-rls.mjs
```

- Auth 故障诊断（直连 Postgres 看 `auth.*` 基础表与默认 Admin）：`web/scripts/verify/diagnose-auth-500.mjs`

## 云端阻塞排障经验（Auth 500）

我们遇到过这种现象：
- PostgREST 查询 `public.region` 正常；
- 但 Auth API 返回 500（例如 `Database error querying schema`、`Database error finding users`），导致：
  - `signInWithPassword` 失败
  - `auth.admin.listUsers` 失败

排障步骤（推荐顺序）：
1. 先用 `web/scripts/verify/diagnose-auth-500.mjs` 直连数据库确认 `auth` schema 与 `auth.users` 是否存在、默认 Admin 行是否存在。
2. 若 DB 本身没问题，优先对项目执行一次 **pause + restore**（相当于软重启服务）：
   - 仓库提供脚本：`supabase/scripts/pause-restore.ps1`

## 版本管理与协作规范（必须遵守）

- 迁移是数据库版本历史，review 必须看迁移 SQL，而不是只看 Dashboard 截图。
- 合并策略：一个 PR 可以包含多个迁移，但每个迁移要小、可解释、可回滚（通过追加迁移回滚逻辑）。
- 发生“删库重建”时：
  - 先清理并重建 `migrations/`（从 000 开始也可以，但要确保远端 migration history 对齐）。
  - 立刻执行一次 `supabase migration list --linked` 确认 Local/Remote 一致。
  - DB 验收必须跑一遍（至少 RLS + 默认 Admin）。
