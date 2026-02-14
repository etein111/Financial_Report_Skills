# Web 逻辑处理规范（Next.js App Router + Supabase）

> 目的：统一“逻辑应该放哪里、怎么写、怎么报错、怎么鉴权、怎么做权限控制与数据读写”，确保后续从原型升级到真实 Supabase 时不漂移、不泄漏密钥、不产生重复实现。
>
> 本文是默认做法：必须有规范，但避免过死/过复杂。确有必要突破时允许例外，但必须说明原因，并把突破控制在最小范围，后续再收敛回规范。

## TL;DR（硬约定）

- 分层：`app/` 只路由与组合；业务逻辑在 `features/`；纯 UI 在 `components/`；基础设施在 `lib/`；纯业务类型/规则在 `domain/`。
- 依赖方向：默认 `app → features → domain`；`domain` 不依赖 React/Next/Supabase；`app` 允许对 `domain` 做 **type-only import**（但业务能力不要绕过 `features`）。
- 触库规约：**只在 `features/*/repo/*` 调用 `supabase.*`**（`from(...)`/`auth.*`/`auth.admin.*` 都算）；`app/` 与 `components/` 禁止直连 Supabase。
- Feature 公共入口：`app/` 只能 import `features/<feature>`（`index.ts`）；`repo/` 默认不对外暴露。
- Result 统一：repo 与 server actions 默认返回 `Result<T> = { ok: true; data: T } | { ok: false; error: string }`（建议定义在 `lib/result.ts`）。
- Supabase SDK：统一 `@supabase/ssr`；不要混用 `@supabase/auth-helpers-nextjs`。
- Middleware：只做会话刷新 + 轻量门禁；资源级鉴权必须在 action/route handler + RLS。

## 0. 总原则（必须遵守）

- **服务端为真**：权限判断、写操作校验、敏感字段处理必须在服务端完成；客户端校验只用于提升体验。
- **RLS 为最终裁判**：UI/Next.js 的鉴权只做体验与提前拦截，真正授权必须落在数据库 RLS（服务端 action/route handler 调用同样受 RLS 约束）。
- **最小可达面**：浏览器侧只能使用 `NEXT_PUBLIC_*`（publishable/anon）；任何需要 `SUPABASE_SERVICE_ROLE_KEY` 的逻辑必须只在服务端执行。
- **错误不外泄**：对外展示统一的用户可理解错误文案；内部错误只用于日志/调试。
- **一致性优先**：同类问题使用同一种方案解决（例如统一的 `ActionResult` 结构、统一的 redirect 规则）。

## 1. 分层与依赖方向（A 方案：简单一致）

### 1.1 目录结构（推荐）

```text
web/
  app/                 # 路由与页面组合（不写触库逻辑）
  features/            # 按业务模块组织（repo/actions/components...）
  domain/              # 纯业务类型与规则（无 React/Next/Supabase 依赖）
  components/          # 纯 UI 组件（不触库、不写业务）
  lib/                 # 基础设施与通用工具（supabase client 工厂、result、time...）
```

### 1.2 依赖方向（允许/禁止）

允许（默认）：
- `app/*` → `features/*`（通过 feature 的公共入口导入，例如 `features/users`）
- `features/*` → `domain/*`、`components/ui/*`、`lib/*`
- `components/*` → `lib/*`（允许为 props 引入 `domain/*` 的 type-only 类型）
- `app/*` → `components/ui/*`、`lib/*`（基础设施）
- `app/*` → `domain/*` 的 **type-only import**（A 方案允许：用于页面 props/类型注解，但不要把业务能力绕过 features）

禁止（默认）：
- `app/*` 直接依赖 `features/*/repo/*`（页面层不直连 repo）
- `components/*` 依赖 `features/*`（UI 纯净，不要引业务模块）
- `domain/*` 依赖 React/Next/Supabase（domain 必须保持框架无关）
- 任何 Client Components 依赖 server-only 模块（尤其是 admin client / service role）

例外规则（保持不过死）：
- 若必须突破以上规则（例如临时调试、过渡重构），必须在变更说明中写清原因，并保证例外代码范围最小，随后跟进收敛。

### 1.3 Features 模块最小骨架（推荐）

> 不强制 service 层。先用最小骨架保证一致性，复杂了再加层。

```text
features/<feature>/
  index.ts             # 公共入口（给 app/ 导入）
  actions.ts           # Server Actions（权限校验 + 调 repo）
  repo/                # 唯一触库处（唯一允许调用 supabase.* 的业务代码）
  components/          # 业务 UI（可 Client，可调用 actions）
```

### 1.4 Feature 公共入口（index.ts）

推荐约定：
- `app/*` 只能从 `features/<feature>`（`index.ts`）导入，不允许跨过入口直连 `repo/`。
- `index.ts` 默认只 re-export：页面级组合需要的组件/类型/常量；`repo/*` 不 re-export。
- Client Components 避免直接依赖 `repo/*` 与 server-only 模块；需要调用写操作时，优先通过 Server Actions（可由 Server Component 引入并通过 props 传入，或在同 feature 内集中绑定）。

### 1.5 Domain 边界（允许“纯规则”，禁止框架/IO）

`domain/*` 允许：
- 业务类型（例如 `UserRole`）、常量、纯函数规则（校验/转换/格式化，不触网不读写文件不读 cookies）

`domain/*` 禁止：
- React/Next/Supabase 依赖
- 任何 IO（数据库、HTTP、cookies、localStorage 等）

## 2. 执行上下文与职责划分（App Router）

### 2.1 Server Components（默认）

适合：
- 读取当前用户（`getUser()`）做鉴权与渲染分支
- 读取列表数据（只读）并渲染页面

约束：
- 不做浏览器交互（无 `useState/useEffect`）
- 不直接持有 service role key（即使在服务端也要通过统一的 admin client 封装）

### 2.2 Client Components（仅必要时）

适合：
- 表单输入与交互（登录、搜索输入、弹窗开关、toast 等）
- 纯视觉动效（粒子背景）

约束：
- 不能包含任何服务端密钥逻辑
- 不允许直接调用 Supabase Admin API（禁止使用 service role）

### 2.3 Server Actions（默认写操作入口）

适合：
- Invite / Edit user / Change role / Ban-Unban / Reset password / Delete user
- 登录/登出/忘记密码（最终必须建立/清理 cookies 会话）

约束：
- 必须在 action 内重新做权限检查（例如 `requireAdmin()`）
- 必须做输入校验（不要只信客户端）
- 返回统一结构（见第 6 节）

### 2.4 Route Handlers（必须用时才用）

适合：
- `/auth/callback` 这种“第三方回调 + 设置 cookies + redirect”的场景

约束：
- 参数 `next` 必须防 open redirect（见第 5.3 节）

### 2.5 Middleware（会话刷新 + 轻量路由保护）

放：
- cookie session 刷新 / 轻量路由保护（例如未登录重定向）

不放：
- 资源级鉴权（“是否能编辑 invoice 123”之类必须在 action/route handler + RLS）

## 3. Supabase 集成方式（官方推荐形态）

### 3.1 统一使用 `@supabase/ssr`

- 浏览器侧：`createBrowserClient(...)`
- 服务端：`createServerClient(...)`（带 cookies 读写桥）

### 3.2 Supabase client 分层（强制三层）

> `lib/supabase/*` 只放 client 工厂与会话刷新工具；业务触库只在 `features/*/repo/*`。

#### Browser client（浏览器可达）

- 只用 `NEXT_PUBLIC_SUPABASE_URL` + `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`（或 legacy anon key）
- 只用于浏览器侧必须的调用（尽量少用）

#### Server client（SSR + cookies）

- 用 publishable/anon key + cookies 读写
- 用于服务端读取当前用户、读取业务数据（RLS 兜底）

#### Admin client（service role，仅服务端）

- 只用 `SUPABASE_SERVICE_ROLE_KEY`
- 模块必须显式 `import "server-only";`
- 所有用户管理写操作都必须走 admin client（invite/role/ban/reset/delete）

## 4. Repo 层触库规约（最重要）

### 4.1 唯一触库点

- **只在 `features/*/repo/*` 调用 `supabase.*`**（包括 `from(...)`、`auth.*`、`auth.admin.*`）。
- `app/*`、`components/*` 禁止直接触 Supabase（只能调用 feature 的 actions/service）。

### 4.2 两类 repo（建议）

- Public repo：使用 server client（RLS 兜底，权限以 JWT 与 RLS 为准）。
- Admin repo：使用 admin client（service role，仅服务端可达）。

### 4.3 Repo 输出形态

- repo 不返回 Supabase 原始 Response 给 UI（避免在 UI 层散落 `.error` 判定）。
- repo 返回领域友好的结构（可直接给 actions/service 做业务编排）。

## 5. 鉴权与 RBAC 约定

### 5.1 角色事实源

- 角色必须来源于 Supabase Auth `app_metadata.role`
- 允许角色：`admin` / `sa` / `analyst`
- 禁止客户端提交 role 作为权限依据

### 5.2 页面权限策略（最小集）

- 受保护（必须登录）：至少包含 `/desktop`、`/users`
- Admin-only：至少包含 `/users` 以及所有“用户管理写操作”
- 非 Admin 访问 Admin-only：返回 `/403`（文案必须包含 `No permission`）

### 5.3 Redirect 安全（防 open redirect）

涉及 redirect 的入口（例如 `/auth/callback`、登录成功后跳转）：
- 允许的 `next` 只能是相对路径：以 `/` 开头，且不包含 `://`、不包含主机名
- 非法 `next` 一律忽略，回退到默认 `/desktop`

## 6. 逻辑错误处理与返回结构（统一）

### 6.1 Server Actions 返回结构（推荐）

约定统一的结果类型：
- 成功：`{ ok: true, data?: ... }`
- 失败：`{ ok: false, error: string }`

错误文案规范：
- 面向用户、可执行（例如 “Invalid email or password.”）
- 不暴露内部实现细节（不要把 Supabase 原始 error message 直接透出）
- 忘记密码必须返回统一成功提示（防邮箱枚举）

### 6.2 客户端展示策略

- 成功：统一 `toast.success(..., { title: "Success" })`
- 失败：统一 `toast.error(..., { title: "Error" })`
- 若需要字段级错误：使用 `Input error` 展示（但服务端仍需校验）

## 7. 输入校验与安全策略

校验原则：
- 客户端校验：快速反馈（必填、email 格式）
- 服务端校验：强制兜底（所有写操作必须校验）

安全策略：
- 忘记密码：永远返回相同成功提示
- 管理操作：服务端再次校验 `role === "admin"`
- 禁止引入 `SUPABASE_SERVICE_ROLE_KEY` 到 Client Components（通过模块边界 + `server-only` 兜底）

## 8. 时间处理规范（Asia/Shanghai 展示）

问题背景：
- `timestamptz` 在数据库存储的是绝对时间（通常以 UTC 语义写入）
- 前端直接 `new Date(iso)` 会按本地时区解释，导致展示不一致

约定：
- 展示必须显式指定 `timeZone: "Asia/Shanghai"`
- 不依赖浏览器本地时区

推荐实现方式（示例，不强制代码位置）：
```ts
export function formatShanghai(iso: string) {
  const d = new Date(iso);
  return new Intl.DateTimeFormat("en-GB", {
    timeZone: "Asia/Shanghai",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(d);
}
```

## 9. 从原型到真实逻辑的升级路径（不改 UI 先改逻辑）

约定：
- 先保持 UI 原型稳定（`components/ui/*` 与页面布局尽量不动）
- 再逐步替换 mock：
  - `/login`：从模拟 -> `signInWithPassword` + cookies 会话 + 成功跳 `/desktop`
  - `/desktop`：Logout 从纯链接 -> 服务端登出清 cookies -> 跳 `/login`
  - `/users`：列表从 mock -> repo 返回真实列表（服务端分页/搜索/排序）
  - 写操作从本地 state -> Server Actions（服务端权限校验 + admin repo）

## 10. 轻量强制（建议，后续实施）

> 文档约束需要可执行，但不宜过重。建议用最少的 ESLint 规则防止越层触库与密钥泄漏：

- 禁止 `app/*` import `features/*/repo/*`
- 禁止 `components/*` import `features/*`
- 禁止 Client Components import `lib/supabase/admin`（或任何 server-only 模块）
