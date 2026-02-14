# 认证与权限系统设计文档（Next.js App Router + Supabase）

## 1. Context

本设计对应 `auth-and-user-management` 变更，技术方案统一为：

- 应用：Next.js（App Router）
- 平台：Supabase（Auth / Postgres / RLS / PostgREST）
- 交互：Server-first（Server Components + Server Actions），必要时局部引入 Client Components
- 会话：使用 `@supabase/ssr` 的 cookies 会话（不强制 HttpOnly）；`middleware.ts` 负责会话刷新与路由保护基线
- 管理能力：不使用 Supabase Edge Functions；所有需要 `SUPABASE_SERVICE_ROLE_KEY` 的管理操作在 Next.js 服务端执行

目标是把“功能权限”（是否允许使用管理页面/操作）与“数据权限”（数据库 RLS）明确分离，并将角色事实源收敛到 Supabase Auth 的 `app_metadata.role`，避免权限漂移。

---

## 2. 设计目标与非目标

### 2.1 目标

- 登录、登出、会话验证、当前用户信息获取（用于页面鉴权与展示）。
- 角色模型：Admin / SA / Analyst。
- Users 管理（邀请制创建、角色调整、禁用/启用、管理员改密、删除）。
- Regions 管理、Analyst Info 管理（数据层由 RLS 兜底）。
- 登录页、桌面页、管理页、403 页面。

### 2.2 非目标

- 不包含 Coverage/Sector/Template。
- 不包含报告创建/编辑/审核。
- 不引入 OAuth Providers（本阶段仅邮箱+密码）。
- 不引入 Edge Functions / Realtime / Storage（本阶段不需要）。

---

## 3. 总体架构

```text
Browser
  -> Next.js (App Router)
      - Server Components / Server Actions / Route Handlers
      - Middleware: refresh session + route protection baseline
      -> Supabase Auth
      -> Supabase Postgres (RLS) + PostgREST
```

架构约束：

- Next.js 是唯一应用入口（页面 + 服务端能力）。
- 业务数据 CRUD 直接复用 Supabase PostgREST + RLS，不构建对外稳定的内部 REST API 合同（`/api/*` 不是本阶段承诺的接口面）。
- 所有“管理员密钥能力”（邀请、角色修改、禁用/启用、管理员改密、删除用户）必须在 Next.js 服务端执行，浏览器侧永不接触 `SUPABASE_SERVICE_ROLE_KEY`。

---

## 4. 权限模型（功能权限 vs 数据权限）

### 4.1 角色定义

- Admin：本阶段全部管理权限。
- SA：本阶段不具备管理权限（与 Analyst 一致）。
- Analyst：本阶段不具备管理权限。

### 4.2 功能权限矩阵

| 功能能力 | Admin | SA | Analyst |
|---|---|---|---|
| 登录/登出 | ✅ | ✅ | ✅ |
| 忘记密码（邮件重置） | ✅ | ✅ | ✅ |
| 用户管理（页面与操作） | ✅ | ❌ | ❌ |
| Region 管理（页面与操作） | ✅ | ❌ | ❌ |
| Analyst 信息管理（页面与操作） | ✅ | ❌ | ❌ |
| 管理员改密 | ✅ | ❌ | ❌ |

### 4.3 数据权限矩阵（RLS）

| 数据资源 | SELECT | INSERT | UPDATE | DELETE |
|---|---|---|---|---|
| `region` | 所有已认证用户 | 仅 Admin | 仅 Admin | 仅 Admin |
| `analyst` | 所有已认证用户 | 仅 Admin | 仅 Admin | 仅 Admin |

说明：基础数据“认证可读”不等于开放管理功能页面；页面入口与写操作仍由功能权限控制。

---

## 5. 认证与会话设计

### 5.1 会话策略（Supabase SSR cookies）

- 会话存储在 cookies，由 `@supabase/ssr` 管理；不使用 `localStorage`。
- 不强制对 Supabase 会话 cookies 施加额外 `HttpOnly` 自定义（遵循 Supabase SSR 推荐做法，避免破坏 refresh 链路）。
- 受保护路由的“是否已登录”判断，服务端必须使用 `supabase.auth.getUser()` 获取用户并完成 token 重新校验；不能用 `getSession()` 作为权限依据。
- 会话有效期遵循 Supabase 默认机制（access token 自动 refresh），不强制“24 小时必须重新登录”。

### 5.2 Supabase Client 分层（建议落地为工具函数）

1) Browser Client（Client Components 使用）

- Key：`NEXT_PUBLIC_SUPABASE_URL` + `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`（或 anon key）
- 创建：`createBrowserClient(...)`

2) Server Client（Server Components / Server Actions / Route Handlers 使用）

- Key：同上（publishable/anon）+ cookies（从 Next.js `cookies()` 读取/回写）
- 创建：`createServerClient(...)`

3) Admin Client（仅管理员动作使用）

- Key：`SUPABASE_SERVICE_ROLE_KEY`（仅服务端 env）
- 创建：`createClient(url, serviceRoleKey)`（不绑定 cookies）

### 5.3 Middleware（会话刷新 + 路由保护基线）

在 `middleware.ts` 中：

- 每个请求调用 `supabase.auth.getUser()` 触发刷新逻辑并回写 cookies。
- 未登录访问受保护路由：重定向到 `/login`。
- 已登录但访问 Admin-only 路由且非 Admin：返回 403 页面（路径 `/403`，文案 `No permission`）。

### 5.4 统一认证回调（单机制）

我们只保留一个回调入口（例如 `GET /auth/callback`）来处理 Supabase 各类认证回调参数：

- 若 URL 参数包含 `code`：走 `exchangeCodeForSession(code)`（兼容 OAuth/PKCE 类回调）。
- 若包含 `token_hash` + `type`：走 `verifyOtp({ token_hash, type })`（兼容邀请/确认/重置等邮件链接类回调）。
- 成功后重定向到 `next`（默认为 `/desktop`，且必须校验为相对路径）。
- 失败统一重定向到 `/auth/auth-code-error`。

---

## 6. 数据模型与 RLS 设计

### 6.1 核心数据结构

- `region`：地区字典（`name`/`code` 唯一）。
- `analyst`：业务分析师信息（`email` 唯一，`region_id` 外键，`ON DELETE SET NULL`）。

约束要求：

- 删除 Region 时不做业务阻断，关联 Analyst 的 `region_id` 自动置空。
- Analyst 业务数据与 Auth Users 解耦：维护 `analyst` 不自动创建/删除/修改 Auth 用户账号。

### 6.2 RLS 策略

RLS 以 JWT 的 `app_metadata.role` 为角色事实源：

- `region`/`analyst`：认证可读（`to authenticated using (true)`）。
- 写操作：仅 Admin（`auth.jwt()->'app_metadata'->>'role' = 'admin'`）。

实现以迁移为准：`supabase/migrations/20260214094418_auth_and_user_management_baseline.sql`。

### 6.3 数据访问策略（实现边界）

- 页面数据读写通过 Supabase PostgREST（`supabase.from('region')...`）完成。
- 不建设对外稳定的 `/api/regions`、`/api/analyst-info` 等 CRUD JSON API；如需 Route Handler，仅作为 Next.js 内部实现细节使用。

---

## 7. 列表与分页（统一规则）

规则：

- 默认按 `created_at DESC`。
- 超过 15 条启用分页。
- 每页固定 15 条。
- 不提供用户自定义每页条数。

落地方式（Supabase Query）：

- `order('created_at', { ascending: false })`
- `range(start, end)`（其中 `start=(page-1)*15`，`end=start+14`）

---

## 8. 页面与路由设计（App Router）

### 8.1 页面路由（建议）

- `/login`：登录页（含“忘记密码”入口）。
- `/desktop`：桌面启动器（登录后默认落地页）。
- `/users`：用户管理（Admin-only）。
- `/regions`：Region 管理（Admin-only）。
- `/analyst-info`：Analyst Info 管理（Admin-only）。
- `/403`：无权限页面（文案 `No permission`）。

Auth 相关：

- `/auth/callback`：统一认证回调（Route Handler）。
- `/auth/auth-code-error`：回调错误页。

### 8.2 Desktop-as-Launcher 导航契约

- 桌面功能卡片必须使用新标签页打开目标功能页。
- Users/Regions/Analyst Info 页面不提供“返回桌面”链接，用户通过关闭标签页回到桌面。

### 8.3 UI 语言与时间

- UI 英文文案。
- 时间展示按 UTC+8（Asia/Shanghai）。

---

## 9. 用户与管理员能力设计（Supabase Auth Admin）

### 9.1 用户创建（Invite-only）

- Admin 在用户管理页输入邮箱并选择角色，服务端调用 Supabase Admin `inviteUserByEmail` 发送邀请邮件。
- Supabase Auth 必须关闭公开注册（public signups），防止绕过邀请创建账号。

### 9.2 角色调整（唯一事实源）

- 角色仅存储在 `app_metadata.role`。
- Admin 调整角色通过 Admin API 更新 `app_metadata.role`。

### 9.3 禁用/启用（单机制：ban / unban）

- 禁用/启用账号仅使用 Supabase Auth 的 ban/unban 机制。
- 不使用 `app_metadata.is_active` 作为账号状态事实源。

### 9.4 管理员改密

- Admin 可为任意用户设置新密码（不要求旧密码）。
- 通过 Supabase Admin API 更新用户密码。

### 9.5 默认 Admin（初始化）

默认 Admin 账号由 migration 幂等初始化（仅用于 Dev/引导）：

- email：`jiang_jiahong@qq.com`
- password：`Admin123`

生产环境 MUST 在对外开放前完成改密或替换为更安全的初始化方案。

实现以迁移为准：`supabase/migrations/20260213165658_init_default_admin.sql`。

---

## 10. 运维与配置（关键约束）

- Node.js 依赖与命令使用 `pnpm` + 项目本地 `node_modules`。
- `SUPABASE_SERVICE_ROLE_KEY` 严禁下发到浏览器。
- Dev 环境允许将 Supabase 连接信息与 key 提交到 Git（用于上手速度）；生产环境严禁提交/硬编码任何密钥。
- 禁止提交个人身份的 Supabase Access Token（例如 `SUPABASE_ACCESS_TOKEN`）。

