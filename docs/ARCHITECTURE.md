# Architecture (Project-Wide)

Last updated: 2026-02-17 (by `region-and-analyst-management`).

本文件用于沉淀“当前系统如何实现”的统一架构视图（按主题组织，非按 change 时间顺序）。

## 1. System Overview

```text
Browser
  -> Next.js (App Router)
      - Server Components / Server Actions / Route Handlers
      - Request boundary gate: `web/proxy.ts` (session refresh + light gating)
      -> Supabase Auth
      -> Supabase PostgREST + RLS (defense in depth)
```

核心目标：Next.js 作为唯一应用入口（页面渲染 + 服务端能力），Supabase 提供 Auth 与数据层。

## 2. Tech Stack & Boundaries

- Next.js (App Router) + React + TypeScript。
- Supabase：Auth / Postgres / RLS / PostgREST。
- 当前明确不使用：Edge Functions / Realtime / Storage / OAuth providers。

Last updated by region-and-analyst-management on 2026-02-17.

## 3. App Structure & Dependency Rules

- 目录分层（Web）：`web/app`（路由与组合）、`web/features`（业务模块）、`web/domain`（纯业务类型/规则）、`web/components`（纯 UI）、`web/lib`（基础设施）。
- 依赖方向（默认）：`app -> features -> domain`；`domain` 不依赖 React/Next/Supabase。
- 触库规约：仅 `web/features/*/repo/*` 允许调用 `supabase.*`；`web/app` 与 `web/components` 禁止直连 Supabase。
- Admin 能力：所有需要 `SUPABASE_SERVICE_ROLE_KEY` 的写操作只能在服务端执行，且应通过 `server-only` admin client。

## 4. Auth/Session Architecture

- 使用 `@supabase/ssr`，会话以 cookies 为载体。
- 服务端鉴权以 `supabase.auth.getUser()` 为准。
- 统一回调入口：`/auth/callback`（code exchange + token_hash/type verify，且 next 参数防 open redirect）。

参考实现位置（非合同）：
- `web/app/auth/callback/route.ts`
- `web/features/auth/repo/auth-repo.ts`

## 5. Request Boundary Gate (`proxy.ts`) & Route Protection

- `web/proxy.ts` 负责“会话刷新 + 轻量门禁”。
- 门禁规则：
  - 未登录访问受保护路由（至少 `/desktop`、`/users`、`/regions`、`/analyst-info`）重定向到 `/login`。
  - 已登录但非 Admin 访问 Admin-only（`/users`、`/regions`、`/analyst-info`）重定向到 `/403`。

Last updated by region-and-analyst-management on 2026-02-17.

## 6. Supabase Client Layering

三层 client：
- Browser client：仅使用 `NEXT_PUBLIC_*`（anon/publishable）。
- Server client：anon/publishable + cookies 读写。
- Admin client：使用 `SUPABASE_SERVICE_ROLE_KEY`，仅服务端可达（`server-only`）。

参考实现位置：
- `web/lib/supabase/browser.ts`
- `web/lib/supabase/server.ts`
- `web/lib/supabase/admin.ts`

## 7. Data Layer (PostgREST + RLS, Time Semantics)

- 业务数据读取优先复用 Supabase PostgREST；授权最终由 RLS 裁决。
- `region` / `analyst` 数据层：
  - 表结构：`region`（name/code 唯一），`analyst`（email 唯一，`region_id` 外键 `ON DELETE SET NULL`）。
  - RLS：认证可读，仅 Admin 可写。
- 时间语义：DB 存储采用 `timestamptz` UTC 语义；展示层按 `Asia/Shanghai` 转换。

参考迁移：
- `supabase/migrations/20260215122000_region_analyst_rls_baseline.sql`

Last updated by region-and-analyst-management on 2026-02-17.

## 8. Feature Implementation Pattern (Region/Analyst)

- 路由层：
  - `web/app/regions/page.tsx`
  - `web/app/analyst-info/page.tsx`
- Feature 层：
  - `web/features/regions/*`
  - `web/features/analyst-info/*`
- 典型调用链：
  - Server Component（页面加载） -> repo 读数据
  - Server Action（写操作） -> `requireAdmin()` -> repo 写数据 -> `revalidatePath()`

## 9. Supabase Migration 规范

核心原则：Migration 只放生产环境需要的 Schema 变更。

- `supabase/migrations/`：仅 Schema 变更（DDL、RLS、索引、约束等）。
- `supabase/seed/`：开发环境初始数据。
- 测试数据：禁止放 migration/seed，应由测试脚本动态创建。

用户创建规范：
- 所有用户创建必须使用 Supabase Admin API，禁止直接插入 `auth.users`。

## 10. Operational/Security Notes

- `SUPABASE_SERVICE_ROLE_KEY` 严禁下发浏览器；管理类写操作必须服务端执行。
- Dev 环境允许提交 Dev key；Prod 环境严禁提交/硬编码密钥。
- 默认 Admin 初始化仅用于 Dev/引导；生产必须替换或改密。

## 11. Sources

- `auth-and-users-mvp`: `openspec/changes/archive/2026-02-15-auth-and-users-mvp`
- `region-and-analyst-management`: `openspec/changes/archive/2026-02-17-region-and-analyst-management`
