# Requirements (Project-Wide)

Last updated: 2026-02-17 (by `region-and-analyst-management`).

本文件用于沉淀“当前系统应该做什么”的统一需求视图（按主题组织，非按 change 时间顺序）。

## 1. Purpose & Scope

目的：建立可演示、可扩展的系统基线，支撑后续 Coverage/Sector/Template 与 report 流程叠加。

范围（当前已覆盖）：
- 认证闭环：登录、登出、忘记密码（邮件重置）、统一认证回调（邀请/确认/重置）。
- Desktop：登录后默认落地页 `/desktop`，作为 Launcher。
- Users 管理（Admin-only）：列表/搜索/分页、邀请创建、编辑信息、改角色、ban/unban、管理员改密、删除用户。
- Region 管理（Admin-only）：列表/搜索/分页、创建、编辑、删除。
- Analyst Info 管理（Admin-only）：列表/搜索/分页、创建、编辑、删除。
- 数据层兜底：`region`/`analyst` 表启用 RLS，认证可读、仅 Admin 可写。

不在范围（当前非目标）：
- Coverage / Sector / Template 管理。
- 报告相关能力（创建/编辑/审核/发布）。
- Supabase Edge Functions / Realtime / Storage。
- OAuth providers（当前仅邮箱+密码）。

Last updated by region-and-analyst-management on 2026-02-17.

## 2. Roles & Permissions (RBAC)

角色：
- `admin`：系统管理员，拥有当前全部管理能力。
- `sa`：当前与 `analyst` 权限一致（预留后续扩展）。
- `analyst`：普通用户，不具备管理能力。

事实源：
- 角色 MUST 取自 Supabase Auth `app_metadata.role`。
- 角色更新 MUST 仅在服务端通过 Admin API 执行（避免客户端提权）。

功能权限（当前阶段）：
- 所有人：登录/登出、忘记密码。
- 仅 Admin：Users、Regions、Analyst Info 页面与所有写操作。
- SA/Analyst：不可访问上述管理页面（重定向 `/403`）。

Last updated by region-and-analyst-management on 2026-02-17.

## 3. Authentication & Sessions

- 会话 MUST 使用 Supabase SSR cookies（不使用 `localStorage`）。
- 服务端鉴权 MUST 以 `supabase.auth.getUser()` 为准（不以 `getSession()` 作为权限依据）。
- 受保护路由：至少包含 `/desktop`、`/users`、`/regions`、`/analyst-info`。
- 未登录访问受保护路由 MUST 跳转 `/login`。
- 会话 refresh 失败时 MUST 视为未登录并跳转 `/login`。
- 已登录但无权限访问 Admin-only MUST 进入 `/403`，且页面文案 MUST 包含 `No permission`。
- 统一认证回调 `/auth/callback` 支持 `next` 参数，但 MUST 校验为相对路径以防 open redirect。

## 4. Password Reset

- 忘记密码 MUST 触发 Supabase 邮件重置流程。
- 对不存在邮箱 MUST 返回统一成功提示（避免邮箱枚举）。
- 重置链接有效期沿用 Supabase 默认配置（不额外定制）。

## 5. Admin Capabilities

### 5.1 User Management

Users 管理（`/users`，Admin-only）必须支持：
- 列表：按 `created_at DESC` 排序。
- 分页：每页固定 12 条，超过 12 条启用分页。
- 搜索：按 `email` 与 `user_metadata.full_name`（大小写不敏感、包含匹配）。
- Invite-only 创建用户：public signups 必须关闭，仅允许 Admin 邀请创建。
- 角色管理：写入 `app_metadata.role`。
- 启用/禁用：仅使用 ban/unban 单机制（禁止使用 `app_metadata.is_active` 作为事实源）。
- 管理员改密：不要求旧密码。
- 删除用户：需二次确认。

### 5.2 Region Management

Region 管理（`/regions`，Admin-only）必须支持：
- 列表字段：`name`、`code`、`created_at`。
- 创建/编辑：`name`、`code`，且唯一性冲突有字段级提示。
- 删除：需二次确认。
- 删除被引用 region 时，`analyst.region_id` MUST 自动置空（`ON DELETE SET NULL`）。
- 搜索：按 `name` / `code` 模糊匹配。
- 分页：每页固定 15 条。

### 5.3 Analyst Info Management

Analyst Info 管理（`/analyst-info`，Admin-only）必须支持：
- 列表字段：`full_name`、`chinese_name`、`email`、`region`、`is_active`。
- 创建必填：`full_name`、`email`、`region`。
- 编辑：可修改所有业务字段。
- 删除：需二次确认。
- 搜索：按 `full_name`、`chinese_name`、`email` 模糊匹配。
- 分页：每页固定 15 条。
- `analyst` 与 `auth.users` 保持解耦：创建/删除 analyst 信息不自动创建/删除账号。

Last updated by region-and-analyst-management on 2026-02-17.

## 6. Navigation Contract (Desktop-as-Launcher)

- `/desktop` MUST 为登录后默认落地页。
- Desktop 功能卡片 MUST 在新标签页打开。
- 功能页 MUST NOT 提供“返回 Desktop”的入口（通过关闭标签页返回）。
- 非 Admin MUST 隐藏管理入口卡片。
- Admin 在 Desktop 的 Data Management 区域可见：Users、Regions、Analyst Info。

Last updated by region-and-analyst-management on 2026-02-17.

## 7. Data Access Baseline (RLS)

- `region` 与 `analyst` 表 MUST 启用 RLS。
- 认证用户 MUST 可读（SELECT）。
- 仅 Admin MUST 可写（INSERT/UPDATE/DELETE）。
- RLS 角色判断 MUST 来源于 `auth.jwt()->'app_metadata'->>'role'`。

## 8. Operational & Security Constraints

- `SUPABASE_SERVICE_ROLE_KEY` MUST 仅存在于服务端环境变量，严禁下发浏览器。
- public signups MUST 关闭，仅允许邀请制创建账号。
- 包管理与命令入口 MUST 使用 `pnpm`。
- 生产环境上线前 MUST 更换/改密默认 Admin 初始化方案。
- 体验约定：前端界面语言统一为英文；对外展示与业务语义时间按 `Asia/Shanghai`（UTC+8）。

## 9. Sources

- `auth-and-users-mvp`: `openspec/changes/archive/2026-02-15-auth-and-users-mvp`
- `region-and-analyst-management`: `openspec/changes/archive/2026-02-17-region-and-analyst-management`
