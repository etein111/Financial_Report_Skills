# Architecture (Project-Wide)

Last updated: 2026-02-15 (by `auth-and-users-mvp`).

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
- 明确不使用（除非后续 change 引入）：Edge Functions / Realtime / Storage / OAuth providers。

## 3. App Structure & Dependency Rules

- 目录分层（Web）：`web/app`（路由与组合）、`web/features`（业务模块）、`web/domain`（纯业务类型/规则）、`web/components`（纯 UI）、`web/lib`（基础设施）。  
- 依赖方向（默认）：`app -> features -> domain`；`domain` 不依赖 React/Next/Supabase。  
- 触库规约：仅 `web/features/*/repo/*` 允许调用 `supabase.*`；`web/app` 与 `web/components` 禁止直连 Supabase。  
- Admin 能力：所有需要 `SUPABASE_SERVICE_ROLE_KEY` 的写操作只能在服务端执行，且应通过 server-only 的 admin client。  

## 4. Auth/Session Architecture

- 使用 `@supabase/ssr`，会话以 cookies 为载体。
- 服务端鉴权以 `supabase.auth.getUser()` 为准（避免仅凭 session 误判）。
- 统一回调入口：`/auth/callback`（code exchange + token_hash/type verify，且 next 参数防 open redirect）。

参考实现位置（非合同）：
- `web/app/auth/callback/route.ts`
- `web/features/auth/repo/auth-repo.ts`

## 5. Request Boundary Gate (proxy) & Route Protection

- Next.js 16 使用 `proxy.ts` 承担“会话刷新 + 轻量门禁”。
- 门禁规则：
  - 未登录访问受保护路由（至少 `/desktop`、`/users`）重定向到 `/login`。
  - 已登录但非 Admin 访问 Admin-only（`/users`）重定向到 `/403`。

参考实现位置：`web/proxy.ts`。

## 6. Supabase Client Layering

三层 client（避免密钥泄漏并保持职责清晰）：
- Browser client：仅使用 `NEXT_PUBLIC_*`（anon/publishable），客户端组件可用。
- Server client：anon/publishable + cookies 读写，用于 Server Components/Actions/Route Handlers。
- Admin client：使用 `SUPABASE_SERVICE_ROLE_KEY`，仅服务端可达（模块需 `server-only`）。

参考实现位置：
- `web/lib/supabase/browser.ts`
- `web/lib/supabase/server.ts`
- `web/lib/supabase/admin.ts`

## 7. Data Layer (PostgREST + RLS, Time Semantics)

- 业务数据读取优先复用 Supabase PostgREST；授权最终由 RLS 裁决（defense in depth）。
- RLS 基线：`region`/`analyst` 认证可读、仅 Admin 可写，角色来源 JWT `app_metadata.role`。
- 时间语义：DB 存储使用 `timestamptz` 的 UTC 语义；展示层按 `Asia/Shanghai` 转换（不要把本地时间写入 `timestamptz`）。

参考迁移：
- `supabase/migrations/20260215122000_region_analyst_rls_baseline.sql`

## 8. Supabase Migration 规范

**核心原则：Migration 只放生产环境需要的 Schema 变更**

- **Migration (`supabase/migrations/`)**：仅用于生产环境的数据库结构变更（DDL），如表创建、字段修改、索引、RLS 策略等。
- **Seed (`supabase/seed/`)**：用于开发环境的初始数据，如基础区域数据、配置项等。
- **测试数据**：测试用户、测试数据集等**禁止**放入 migration 或 seed。应在测试前通过脚本或 API 动态创建。

### 8.1 用户创建规范

**所有用户创建必须使用 Supabase Admin API**，禁止直接插入 `auth.users` 表。

原因：
- 直接 SQL 插入会绕过 Supabase Auth 的内部逻辑
- 可能导致密码哈希、审计字段、触发器等不正确
- 与生产环境的用户管理流程不一致
- 可能导致认证流程异常

正确方式：
- **生产环境**：通过应用 UI 注册或 Supabase Dashboard
- **开发/测试环境**：使用 `web/scripts/create-test-users.mjs`

```bash
cd web && node ./scripts/create-test-users.mjs
```

该脚本使用 `@supabase/supabase-js` 的 `admin.createUser()` API，确保用户数据完整性。

示例目录结构：
```
supabase/
├── migrations/          # 仅 Schema 变更，会上生产
│   └── 20260215_xxx.sql
├── seed/                # 开发环境初始数据
│   └── regions.sql
web/
└── scripts/             # 管理脚本
    └── create-test-users.mjs  # 使用 Admin API 创建用户
```

## 9. Operational/Security Notes

- `SUPABASE_SERVICE_ROLE_KEY` 严禁下发浏览器；所有管理类写操作必须服务端执行。
- Dev 环境允许提交 Dev key 以提高上手速度；Prod 环境严禁提交/硬编码密钥。
- 默认 Admin 初始化用于 Dev/引导；生产必须替换或改密（不要在本文重复默认密码）。

## 9. Sources

- `auth-and-users-mvp`: `openspec/changes/archive/2026-02-15-auth-and-users-mvp`
