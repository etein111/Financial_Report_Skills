# Project Decisions (Cross-Cutting)

本文件用于收敛 `openspec/*` 的 proposal/design 中对未来开发有长期影响的约束，避免约定散落在历史 change 里。

## 技术栈与边界

- 应用唯一入口：Next.js（App Router）。
- 后端能力：Supabase（Auth/Postgres/RLS/PostgREST）。
- Supabase 部署：使用 Supabase 云服务，不使用本地开发环境（`supabase start`）。Supabase CLI 仅用于迁移版本管理（`db push`、`migration list`）。
- 不使用：Edge Functions / Realtime / Storage / OAuth providers（除非新 change 明确引入）。
- 交互策略：Server-first（Server Components + Server Actions），仅必要时引入 Client Components。
- 包管理：`pnpm`（禁止 npm/yarn 作为项目命令入口）。

## 认证与会话

- 会话：Supabase SSR cookies（`@supabase/ssr`），不使用 `localStorage`。
- 服务端鉴权：以 `supabase.auth.getUser()` 为准，不以 `getSession()` 作为权限依据。
- Redirect 安全：所有 `next` 参数必须是相对路径，禁止 open redirect。

## 角色与权限（RBAC）

- 角色：`admin` / `sa` / `analyst`。
- 角色事实源：Supabase Auth `app_metadata.role`。
- 管理操作（邀请/改角色/ban/改密/删除）：必须服务端执行，使用 service role key，禁止下发浏览器。
- 账号禁用：只用 ban/unban 单机制，不使用 `app_metadata.is_active`。

## 数据权限（RLS）

- `region` / `analyst`：认证可读、仅 Admin 可写。
- RLS 角色判断：`auth.jwt()->'app_metadata'->>'role'`。

## 时间语义

- DB 存储：`timestamptz` 默认语义（UTC），禁止把本地时间写入 `timestamptz`。
- 展示语义：对外展示按 `Asia/Shanghai` 转换。

## 文案与界面语言

- 前端界面语言默认英文（按钮、标题、提示文案）。

## 导航契约（Desktop-as-Launcher）

- `/desktop` 为登录后默认落地页。
- Desktop 功能卡片在新标签页打开目标页面。
- 功能页不提供“返回 Desktop”入口（通过关闭标签页返回）。
- 非 Admin 默认隐藏管理入口（例如 Users）。
