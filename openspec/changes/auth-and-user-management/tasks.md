# 实施任务清单（按 proposal + design）

## 使用说明

- 本清单以 `proposal.md` 与 `design.md` 为准。
- 技术路线固定为：Next.js（App Router）+ Supabase（Auth/Postgres/RLS/PostgREST），不使用 Edge Functions。
- 交互策略固定为：Server-first（Server Components + Server Actions），必要时局部引入 Client Components。

---

## 阶段 0：变更文档收口（技术栈调整）

- [x] 0.1 更新 `proposal.md`：改为 Next.js App Router + Supabase 原生（cookies SSR、invite-only、ban/unban、无 Edge Functions）。
- [x] 0.2 更新 `design.md`：删除 FastAPI/Jinja2/HTMX 设计，补齐 Next.js/Supabase SSR 架构与落地边界。
- [x] 0.3 更新 `specs/*/spec.md`：删除 `/api/*`、HttpOnly、FastAPI 等旧描述，统一到 Next.js/Supabase 方案。
- [x] 0.4 校验 `tasks.md` 勾选状态：不得出现“未实现但已勾选”的任务。

---

## 阶段 1：Supabase 基线与迁移治理

**目标**：建立可追踪、可增量执行的数据库变更流程（dev + prod）。

- [x] 1.1 初始化 Supabase CLI 工程目录，建立 `supabase/migrations/` 与 `supabase/seed/`。
- [x] 1.2 将当前数据库基线迁移为 migration（不再使用单一 `init.sql` 作为发布入口）。
- [x] 1.3 建立 `region` 与 `analyst` 表结构，确保 `analyst.region_id` 使用 `ON DELETE SET NULL`。
- [x] 1.4 落地 RLS 策略：`region`/`analyst` 认证可读、仅 Admin 可写。
- [x] 1.5 编写幂等 seed：预置 Region 数据（China、Hong Kong、Japan、Taiwan、Korea、India、Macau、US）。
- [x] 1.6 初始化默认 Admin 账号（`jiang_jiahong@qq.com` / `Admin123`，仅 Dev/引导；生产必须改密/替换）。
- [ ] 1.7 迁移发布演练（Dev）：本地或 dev 云环境执行 `supabase db push` / `supabase db reset` 并完成 SQL 验证（read + write）。

---

## 阶段 2：Next.js 工程初始化 + Supabase SSR 基线

**目标**：搭建 App Router 工程骨架，完成 cookies SSR 会话与路由保护。

- [ ] 2.1 初始化 Next.js App Router + TypeScript 项目结构（约定目录、lint/format）。
- [ ] 2.2 安装依赖：`next/react`、`@supabase/supabase-js`、`@supabase/ssr`。
- [ ] 2.3 创建 Supabase 客户端封装：
- [ ] 2.3.1 Browser Client（Client Components 用）
- [ ] 2.3.2 Server Client（Server Components/Actions/Route Handlers 用，基于 cookies）
- [ ] 2.3.3 Admin Client（仅服务端，`SUPABASE_SERVICE_ROLE_KEY`）
- [ ] 2.4 实现 `middleware.ts`：会话刷新 + 受保护路由重定向 + Admin-only 路由 403。
- [ ] 2.5 实现统一认证回调 `GET /auth/callback`（单机制）：支持 `code` 与 `token_hash+type` 两种参数。
- [ ] 2.6 增加回调错误页 `/auth/auth-code-error`（简单说明 + 返回登录页）。

---

## 阶段 3：认证与基础页面（不引入边缘/额外服务）

**目标**：完成登录/登出/桌面落地，并与权限模型一致。

- [ ] 3.1 登录页 `/login`：
- [ ] 3.1.1 邮箱+密码登录（成功进入 `/desktop`）
- [ ] 3.1.2 “忘记密码”触发邮件重置（统一成功提示，避免邮箱枚举）
- [ ] 3.2 登出能力（Server Action 或 Route Handler），登出后回到 `/login`。
- [ ] 3.3 桌面页 `/desktop`（已登录可访问；作为 Launcher）。
- [ ] 3.4 403 页面 `/403`（文案 `No permission`）。

---

## 阶段 4：管理能力（Admin）

**目标**：完成 Users / Regions / Analyst Info 三组管理能力，遵循“功能权限 + RLS”双层模型。

- [ ] 4.1 Users 管理（Admin-only）：
- [ ] 4.1.1 用户列表 + 搜索 + 分页（`created_at DESC`、>15 分页、每页 15）
- [ ] 4.1.2 邀请制创建用户（invite），并可指定初始角色（`app_metadata.role`）
- [ ] 4.1.3 角色调整（唯一事实源：`app_metadata.role`）
- [ ] 4.1.4 禁用/启用（单机制：ban/unban；不使用 `app_metadata.is_active`）
- [ ] 4.1.5 管理员改密（不要求旧密码）
- [ ] 4.1.6 删除用户（如需要；谨慎暴露入口）
- [ ] 4.2 Regions 管理（Admin-only 写；认证可读）：
- [ ] 4.2.1 列表/搜索/分页（统一规则）
- [ ] 4.2.2 新增/编辑/删除（依赖 RLS）
- [ ] 4.3 Analyst Info 管理（Admin-only 写；认证可读）：
- [ ] 4.3.1 列表/搜索/分页（统一规则；搜索字段：`full_name`/`chinese_name`/`email`）
- [ ] 4.3.2 新增/编辑/删除（依赖 RLS；`full_name`/`email`/`region` 必填）
- [ ] 4.4 Desktop 卡片入口：
- [ ] 4.4.1 Admin 展示 Users/Regions/Analyst Info 卡片
- [ ] 4.4.2 SA/Analyst 隐藏管理卡片入口
- [ ] 4.5 Desktop-as-Launcher：
- [ ] 4.5.1 桌面卡片新标签打开功能页
- [ ] 4.5.2 功能页不提供“返回桌面”链接

---

## 阶段 5：联调验收与发布准备

**目标**：确认能力完整、权限正确、迁移与运维规则可执行。

- [ ] 5.1 认证验收：登录、登出、会话失效处理、忘记密码流程通过。
- [ ] 5.2 权限验收：Admin/SA/Analyst 三角色功能权限与数据权限矩阵一致。
- [ ] 5.3 RLS 验收：数据库层验证“认证可读、Admin 可写”策略生效。
- [ ] 5.4 用户创建验收：public signups 已关闭；只能通过邀请制创建用户。
- [ ] 5.5 邀请验收：用户完成邀请流程后自动进入 `/desktop`（自动建立会话，不要求再次登录）。
- [ ] 5.6 运维约束验收：生产环境关闭调试端点；`SUPABASE_SERVICE_ROLE_KEY` 未下发到浏览器。

---

## 完成定义（DoD）

- [ ] `tasks.md` 全部勾选完成后，可进入 `/opsx:verify`。
- [ ] 通过验证后再进入归档流程（`/opsx:archive`）。
