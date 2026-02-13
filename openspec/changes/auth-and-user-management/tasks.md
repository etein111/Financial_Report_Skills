# 实施任务清单（按 proposal + design 重建）

## 使用说明

- 本清单完全以 `proposal.md` 与 `design.md` 为准。
- 技术路线固定为：FastAPI 单体 + Supabase + Jinja2/HTMX + Tailwind。
- 任务按顺序执行，每完成一项即勾选。

---

## 阶段 1：Supabase 基线与迁移治理

**目标**：建立可追踪、可增量执行的数据库变更流程（dev + prod）。

- [ ] 1.1 初始化 Supabase CLI 工程目录，建立 `supabase/migrations/` 与 `supabase/seed/`。
- [ ] 1.2 将当前数据库基线迁移为首个 migration（不再使用单一 `init.sql` 作为发布入口）。
- [ ] 1.3 建立 `region` 与 `analyst` 表结构，确保 `analyst.region_id` 使用 `ON DELETE SET NULL`。
- [ ] 1.4 落地 RLS 策略：`region`/`analyst` 认证可读、仅 Admin 可写。
- [ ] 1.5 编写幂等 seed：预置 Region 数据（China、Hong Kong、Japan、Taiwan、Korea、India、Macau、US）。
- [ ] 1.6 验证迁移历史由 `supabase_migrations.schema_migrations` 管理，不自建版本记录表。
- [ ] 1.7 形成发布规则文档：先 dev 后 prod；紧急 Dashboard 变更需当天补 migration 回写 Git。

---

## 阶段 2：认证与会话能力（FastAPI + Supabase Auth）

**目标**：完成 Cookie 会话方案和角色鉴权基线。

- [ ] 2.1 实现登录接口 `POST /api/auth/login`，登录成功写入 HttpOnly Cookie。
- [ ] 2.2 实现登出接口 `POST /api/auth/logout`，清理会话 Cookie。
- [ ] 2.3 实现当前用户接口 `GET /api/auth/me`。
- [ ] 2.4 实现忘记密码接口 `POST /api/auth/forgot-password`，并配置 Supabase 托管重置页跳转。
- [ ] 2.5 实现依赖：`get_access_token`、`get_current_user`、`require_admin`。
- [ ] 2.6 完成会话与安全设置：`HttpOnly`、`Secure`、`SameSite=Lax`。
- [ ] 2.7 校验角色来源仅使用 Auth `app_metadata.role`（服务端可改）。

---

## 阶段 3：管理能力 API（Admin 功能边界）

**目标**：完成 Users / Regions / Analyst Info 三组管理接口，并与权限模型一致。

- [ ] 3.1 用户管理接口：`GET/POST/PUT/DELETE /api/users`。
- [ ] 3.2 用户扩展接口：`PUT /api/users/{id}/password`、`PUT /api/users/{id}/role`、`PUT /api/users/{id}/toggle-status`。
- [ ] 3.3 Region 接口：`GET /api/regions`（认证可读）、`POST/PUT/DELETE`（Admin）。
- [ ] 3.4 Analyst Info 接口：`GET /api/analyst-info`（认证可读）、`POST/PUT/DELETE`（Admin）。
- [ ] 3.5 实现 `POST /api/analyst-info/check-email`（Admin）。
- [ ] 3.6 落地通用列表规则：`created_at DESC`、超过 15 条分页、每页固定 15。
- [ ] 3.7 校验 Analyst 列表搜索字段：`full_name`、`chinese_name`、`email`。
- [ ] 3.8 校验 Analyst 创建必填字段：`full_name`、`email`、`region`。

---

## 阶段 4：页面与交互（Jinja2 + HTMX + Tailwind）

**目标**：完成登录页、桌面页、管理页与 403 页，满足导航与视觉约定。

- [ ] 4.1 页面路由完成：`/login`、`/desktop`、`/users`、`/regions`、`/analyst-info`、`/403`。
- [ ] 4.2 页面访问控制：管理页仅 Admin；越权访问返回 403 页面（文案 `No permission`）。
- [ ] 4.3 落地 Desktop-as-Launcher 约定：功能卡片新标签打开；功能页无“返回桌面”按钮。
- [ ] 4.4 管理页交互使用 HTMX 完成搜索、分页、增删改局部刷新。
- [ ] 4.5 登录页与桌面页视觉对齐原型：
  - `openspec/changes/auth-and-user-management/01-login-page.jpg`
  - `openspec/changes/auth-and-user-management/02-desktop.jpg`
- [ ] 4.6 视觉基线验收：深色背景、简单大气、专业、科技感；允许小幅间距与字号微调。
- [ ] 4.7 语言与时间约束：UI 英文文案；展示时间按 UTC+8。

---

## 阶段 5：联调验收与发布准备

**目标**：确认能力完整、权限正确、迁移与运维规则可执行。

- [ ] 5.1 认证验收：登录、登出、会话失效处理、忘记密码流程通过。
- [ ] 5.2 权限验收：Admin/SA/Analyst 三角色功能权限与数据权限矩阵一致。
- [ ] 5.3 RLS 验收：数据库层验证“认证可读、Admin 可写”策略生效。
- [ ] 5.4 列表验收：排序、分页、搜索规则符合设计。
- [ ] 5.5 导航验收：桌面卡片新标签打开，功能页无返回入口，关闭标签后可继续在桌面操作。
- [ ] 5.6 运维验收：生产环境关闭调试路由，仅开发环境可启用 debug 路由。
- [ ] 5.7 迁移发布演练：在 dev 完成 `db push` 验证后再执行 prod。
- [ ] 5.8 文档收口：同步更新 README 与变更说明中的启动、迁移、发布步骤。

---

## 完成定义（DoD）

- [ ] 所有 API 与页面能力满足 proposal 范围，无额外超范围功能。
- [ ] `tasks.md` 全部勾选完成后，可直接进入 `/opsx:verify`。
- [ ] 通过验证后再进入归档流程（`/opsx:archive`）。
