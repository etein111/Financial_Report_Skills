## Why

建立系统的基础认证与权限能力，为后续报告功能提供安全、可扩展的访问控制基础。
本变更重点是把“谁可以使用管理功能”与“谁可以读取业务基础数据”明确分离，避免权限语义混淆。

## 0. 技术架构与平台能力边界（技术栈调整）

本变更采用 **Next.js（App Router）+ Supabase** 的统一技术栈，不再使用 FastAPI / Jinja2 / HTMX。

应用形态：
- Next.js 作为唯一应用入口（页面渲染 + 服务端能力）。
- 所有需要管理员密钥（`SUPABASE_SERVICE_ROLE_KEY`）的能力，统一由 Next.js 服务端承载（Route Handlers 或 Server Actions）。
- 会话形态：遵循 Supabase SSR 推荐做法，使用 cookies 存储会话，不强制 HttpOnly（保证 refresh token 维护链路）。
- 交互策略：默认 Server-first（Server Components + Server Actions），仅在需要更强交互时局部引入 Client Components。
- 写操作默认使用 Server Actions（不以稳定 JSON API 作为内部主通道）；仅在认证回调等必要场景使用 Route Handlers。
- 会话刷新与路由保护基线：使用 Next.js `middleware.ts` 统一刷新会话（回写 cookies）并执行受保护路由的访问控制。

Supabase 能力取舍（明确要什么 / 不要什么）：
- 本变更使用：
  - Supabase Auth（邮箱+密码登录、会话、忘记密码邮件、Supabase 托管重置页）
  - Supabase Postgres + RLS（`region` / `analyst` 数据权限兜底）
  - Supabase PostgREST（业务数据 CRUD 直接复用平台数据 API，不自建对外稳定的业务 REST API）
  - Supabase CLI migrations/seed（数据库变更治理）
- 本变更不使用：
  - Supabase Edge Functions（原则：简单优先；不引入第二套函数部署与鉴权链路）
  - Supabase Realtime
  - Supabase Storage（本阶段不涉及文件/附件）
  - Supabase OAuth Providers（本阶段仅支持邮箱+密码）

## 1. 目标与范围

### 1.1 目标（Goals）
- 建立用户认证体系（登录、登出、Token 验证）。
- 建立角色权限体系（Admin、SA、Analyst）。
- 完成用户管理（Auth 用户的创建、编辑、删除、角色调整、管理员改密）。
- 完成 Region 管理与 Analyst 信息管理。
- 提供登录页、桌面主页、管理页面。
- 支持用户在登录页通过“忘记密码”触发邮件重置密码。

### 1.2 非目标（Non-Goals）
- 不包含 Sector、Coverage、Template 等其他基础数据管理。
- 不包含报告创建、编辑、审核等报告功能。
- 不实现 refresh token 机制。
- 不自建 refresh token 机制（遵循 Supabase 默认会话 refresh 行为，不另写自定义 refresh 流程）。
- 不在本阶段实现密码修改审计日志。

## 2. 权限模型（核心）

### 2.1 双层权限定义

- 功能使用权限（UI/API 管理能力）
  - 控制页面入口、管理按钮、管理类 API 调用。
  - 本阶段 Region/Analyst/Users 管理功能仅 Admin 可使用。

- 数据访问权限（数据库 RLS）
  - 控制底层数据读写。
  - 为保证后续业务（如报告创建时选择 Region）可用，基础字典数据允许已认证用户读取。

### 2.2 角色定义
- Admin：系统管理员，拥有本阶段全部管理权限。
- SA（Senior Analyst）：本阶段与 Analyst 权限一致，预留后续报告审核能力。
- Analyst：普通分析师，本阶段不具备管理权限。

### 2.3 功能使用权限矩阵

| 功能能力 | Admin | SA | Analyst |
|---------|-------|----|---------|
| 登录/登出 | ✅ | ✅ | ✅ |
| 忘记密码（邮件重置） | ✅ | ✅ | ✅ |
| 用户管理（Users 页面与操作） | ✅ | ❌ | ❌ |
| Region 管理（Regions 页面与操作） | ✅ | ❌ | ❌ |
| Analyst 信息管理（Analyst Info 页面与操作） | ✅ | ❌ | ❌ |
| 管理员直接修改任意用户密码 | ✅ | ❌ | ❌ |

### 2.4 数据访问权限矩阵（RLS）

| 数据资源 | SELECT | INSERT | UPDATE | DELETE |
|---------|--------|--------|--------|--------|
| `region` | 所有已认证用户 | 仅 Admin | 仅 Admin | 仅 Admin |
| `analyst` | 所有已认证用户 | 仅 Admin | 仅 Admin | 仅 Admin |

说明：
- `region` / `analyst` 的读权限向已认证用户开放，是业务数据可用性需求，不代表管理功能对非 Admin 开放。
- 本阶段不做字段脱敏（例如 analyst.email 不做部分隐藏）。

## 3. 功能分组（按功能）

### 3.1 认证与会话

用户价值：用户可安全登录系统并保持会话。

范围：
- 登录（邮箱+密码）
- 登出
- 当前用户信息获取（用于前端鉴权与展示）
- 会话有效期遵循 Supabase 默认机制（access token 自动 refresh），不强制 24 小时重新登录

验收要点：
- 未登录访问受保护页面会跳转到登录页。
- 登录失败有明确错误提示。
- Token 失效时前端自动清理登录态并跳转登录页。
- 用户在正常使用场景下 SHOULD 保持登录态（除非手动登出、被禁用或 refresh 失败）。
- 本阶段仅支持邮箱+密码登录，不引入 OAuth 登录。

### 3.2 密码能力

用户价值：兼顾用户自助恢复账号与管理员运维能力。

范围：
- 用户在登录页点击“忘记密码”，系统发送重置邮件。
- 用户通过邮件链接在 Supabase 托管重置页完成密码重置。
- Admin 可直接修改任意用户密码。

规则：
- 本提案按两类能力定义：
  - 重置密码（用户自助邮件重置，重置页面由 Supabase 托管）
  - 管理员改密（Admin 直接改任意用户密码）
- 重置密码链接有效期采用 Supabase 默认配置，不做额外自定义。
- 不额外实现“一次性使用后立即失效”等增强机制，沿用 Supabase 默认行为。
- “忘记密码”对不存在邮箱返回统一成功提示，避免邮箱枚举。
- 应用层不额外增加频率限制，保持流程简单（依赖平台默认保护）。
- 管理员改密不要求提供旧密码。
- 本阶段不要求密码修改审计日志。

### 3.3 用户管理（Users）

用户价值：Admin 可集中管理所有认证用户账号。

范围：
- 用户列表（支持按姓名/邮箱搜索）
- 创建用户（邀请制）
- 编辑用户信息
- 修改用户角色（Admin/SA/Analyst）
- 删除用户
- 启用/禁用用户
- Admin 直接修改用户密码

权限：
- 仅 Admin 可访问与操作。

用户创建规则：
- 创建用户使用 Supabase Auth Admin 的邀请机制（invite），由系统发送邀请邮件。
- 用户通过邀请邮件完成初始密码设置后，再使用邮箱+密码登录本系统。
- 用户完成邀请流程后，系统 SHOULD 自动建立会话并跳转到桌面页 `/desktop`（不要求用户再手动登录一次）。
- 本阶段不提供“创建时设置初始密码”能力；如需重置密码，使用管理员改密或用户忘记密码流程。
- Supabase Auth 配置 SHOULD 关闭公开注册（public signups），仅允许邀请制创建用户。

账号状态规则：
- 用户被禁用后无法登录系统。
- 已禁用用户可由 Admin 重新启用，启用后恢复正常登录能力。
- 禁用/启用实现：使用 Supabase Auth Admin 的 ban/unban。
- 本阶段不使用 `app_metadata.is_active` 作为状态事实源；账号状态以 ban/unban 为准。

### 3.4 Region 管理（Regions）

用户价值：Admin 可维护地区字典数据，支撑后续业务选择。

范围：
- Region 列表
- 创建 / 编辑 / 删除 Region
- 名称与代码唯一性校验
- 系统预置 Region：China、Hong Kong、Japan、Taiwan、Korea、India、Macau、US
- 删除 Region 时不做关联阻断；若被 Analyst 引用，按数据库策略 `ON DELETE SET NULL` 自动置空关联。

权限：
- 管理功能（页面与操作）仅 Admin。
- 数据读取（SELECT）对所有已认证用户开放。

列表行为：
- 遵循「3.9 列表与分页通用规则」。

### 3.5 Analyst 信息管理（Analyst Info）

用户价值：Admin 可维护 Analyst 业务信息，并与账号系统解耦。

范围：
- Analyst 列表（支持按 `full_name`、`chinese_name`、`email` 搜索）
- 创建 / 编辑 / 删除 Analyst 信息
- 邮箱唯一性校验
- 列表展示字段：`full_name`、`chinese_name`、`email`、`region`、`is_active`
- 创建必填字段：`full_name`、`email`、`region`

权限：
- 管理功能（页面与操作）仅 Admin。
- 数据读取（SELECT）对所有已认证用户开放。

解耦原则：
- 创建/删除 Analyst 信息不自动创建/删除用户账号。
- Analyst 信息通过 email 与未来报告业务做逻辑关联，不做外键强绑定到 Auth 用户。

列表行为：
- 遵循「3.9 列表与分页通用规则」。

### 3.6 桌面与导航（硬性约定）

范围：
- 桌面主页展示所有规划功能卡片。
- 当前可用管理功能：`Users`、`Regions`、`Analyst Info`（管理能力仅 Admin）。
- 非 Admin 默认不展示管理功能卡片。
- 功能卡片点击后在新标签页打开。
- 功能页面不提供“返回桌面”按钮，用户通过关闭标签页返回。
- 非 Admin 用户强行访问管理路由时，返回 403 页面（文案：`No permission`）。
- 上述导航方式为桌面启动器（Desktop-as-Launcher）契约，适用于本阶段与后续新增功能页；如需改变，必须通过新 proposal 明确变更。

### 3.7 时间与时区约定

- 前端展示时间统一使用北京时间（UTC+8）。
- 后端接口与数据库时间约定统一为北京时间（UTC+8）。

### 3.8 界面语言与数据语言约定

- 前端界面语言统一为英文（按钮、标题、表单标签、提示文案）。
- 业务数据内容支持中英文（例如姓名、报告标题、摘要等）。

### 3.9 列表与分页通用规则

- 列表默认按 `created_at` **降序**排序（最新创建在前）。
- 当列表数据超过 15 条时启用分页。
- 默认每页 15 条（按常见桌面可视区域约 12-15 行估算）。
- 不提供用户自定义每页条数切换，保持交互简单。

### 3.10 视觉风格与原型基线

- 视觉风格基线：深色背景、简单大气、专业、富有科技感。
- 登录页与桌面页必须对齐既有原型风格，作为验收依据：
  - `openspec/changes/auth-and-user-management/01-login-page.jpg`
  - `openspec/changes/auth-and-user-management/02-desktop.jpg`
- 可对间距、字号做小幅适配，但不得改变整体视觉方向与信息层级。

## 4. Capabilities

| Capability | 对应功能组 | 说明 |
|------------|------------|------|
| `user-login` | 3.1 | 登录/登出/会话验证 |
| `password-reset` | 3.2 | 用户忘记密码邮件重置流程 |
| `admin-password-change` | 3.2/3.3 | Admin 直接修改任意用户密码 |
| `role-control` | 2 | 角色权限控制（功能权限） |
| `rls-security` | 2 | 数据层 RLS 控制（数据权限） |
| `desktop-nav` | 3.6 | 桌面与导航 |
| `user-management` | 3.3 | 用户管理 |
| `region-crud` | 3.4 | Region 管理 |
| `analyst-info` | 3.5 | Analyst 信息管理 |

### Modified Capabilities
无现有能力修改。

## 5. System Impact

### 5.1 数据库层
- 新增 `region` 表与 `analyst` 表。
- RLS 采用“读写分离”策略：
  - SELECT：authenticated
  - INSERT/UPDATE/DELETE：Admin
- 初始化写入预置 Region 数据（China、Hong Kong、Japan、Taiwan、Korea、India、Macau、US）。
- 用户账号由 Supabase Auth 管理。

### 5.2 应用服务端（Next.js App Router）
- Next.js（App Router）负责页面渲染、会话校验与服务端执行环境（Server Actions / Route Handlers）。
- 本阶段不沿用既有 `/api/*` 路径契约；应用内部是否暴露 Route Handlers 属实现细节，不作为对外稳定 API 承诺。
- 认证与会话：通过 Supabase Auth 实现登录/登出/当前用户，会话使用 cookies 管理（不强制 HttpOnly）。
- 密码能力：
  - 用户忘记密码：调用 Supabase 重置密码能力发送邮件（邮件链接跳转 Supabase 托管重置页）。
  - 管理员改密：仅在 Next.js 服务端使用 `SUPABASE_SERVICE_ROLE_KEY` 调用 Supabase Auth Admin 能力执行。
- 用户管理（Admin）：创建/编辑/删除、角色调整、禁用/启用（ban/unban）、管理员改密等操作仅在 Next.js 服务端执行。
- 业务数据（Region/Analyst）：读写直接通过 Supabase PostgREST + RLS（使用 `supabase-js`），不自建对外稳定的业务 CRUD REST API。

### 5.3 前端界面
- 登录页面（含“忘记密码”入口）
- 桌面主页（功能卡片 + 导航栏）
- 用户管理页面（仅 Admin）
- Region 管理页面（仅 Admin）
- Analyst 信息管理页面（仅 Admin）
- 页面权限控制（服务端重定向/403 + 客户端 UI 隐藏入口）

### 5.4 运维与发布要求
- 默认 Admin 账号由 Supabase migration 初始化（默认邮箱 `jiang_jiahong@qq.com`，默认初始密码 `Admin123`），用于 Dev/引导；生产环境 MUST 在对外开放前完成改密或替换为更安全的初始化方案。
- 所有调试端点（debug/config、debug/test-rls 等）在生产环境必须关闭。
- Node.js 依赖与命令必须使用 `pnpm` + 项目本地 `node_modules`，禁止使用 `npm/npx` 或全局安装包执行开发命令。
- `SUPABASE_SERVICE_ROLE_KEY` 仅允许在服务端环境变量使用，严禁下发到浏览器。
- 开发阶段允许将 Dev 环境的 Supabase 连接信息与 key（例如 `SUPABASE_URL`、`SUPABASE_ANON_KEY`、`SUPABASE_PUBLISHABLE_KEY`、`SUPABASE_SERVICE_ROLE_KEY`）提交到 Git 以提升上手速度；生产环境严禁提交与硬编码任何密钥。
- 禁止提交个人身份的 Supabase Access Token（例如 `SUPABASE_ACCESS_TOKEN`）；CLI 登录/链接应通过开发者本地登录完成。
- 本轮联调与验收仅覆盖 Dev 云环境，不执行 Prod 环境测试。

## 6. Key Decisions

1. 角色存储在 Supabase Auth `app_metadata`，仅服务端可改，避免用户自行提权。
2. 用户账号系统与 Analyst 信息系统解耦，独立管理。
3. 权限采用双层模型：功能权限与数据权限分离。
4. 管理功能仅 Admin；基础数据读取按业务需求向已认证用户开放。
5. 密码能力保持简化：用户忘记密码邮件重置 + 管理员直接改密；不增加额外复杂安全机制。
6. 非 Admin 强行访问管理路由返回 403 页面（文案：`No permission`）。
7. 前后端与数据库时间统一使用北京时间（UTC+8）。
8. 生产环境必须关闭调试端点。
9. 应用框架采用 Next.js App Router；不再使用 FastAPI/Jinja2/HTMX。
10. 原则：简单优先，不使用 Supabase Edge Functions；管理员能力由 Next.js 服务端承载。
11. 业务数据 CRUD 复用 Supabase PostgREST + RLS；不自建对外稳定的业务 CRUD REST API。
12. Node.js 工具链必须使用 `pnpm` 与项目本地 `node_modules`，禁止全局 Node.js 工具链与 `npm/npx`。
13. 用户创建采用邀请制（invite）：由系统发送邀请邮件，用户自助设置初始密码。
14. 用户完成邀请流程后自动进入 `/desktop`（自动建立会话，不要求再次登录）。
15. 会话有效期遵循 Supabase 默认机制（access token 自动 refresh），不强制 24 小时重新登录。
16. 开发阶段允许提交 Dev Supabase 连接信息与 key（但生产环境严禁提交任何密钥）。
17. Supabase Auth 关闭公开注册（public signups），仅允许邀请制创建用户。
18. 本阶段仅支持邮箱+密码登录，不引入 OAuth 登录。
19. 默认 Admin 账号由 migration 初始化：`jiang_jiahong@qq.com` / `Admin123`（仅用于 Dev/引导；生产必须改密/替换）。
