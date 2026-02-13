## Why

建立系统的基础认证与权限能力，为后续报告功能提供安全、可扩展的访问控制基础。
本变更重点是把“谁可以使用管理功能”与“谁可以读取业务基础数据”明确分离，避免权限语义混淆。

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
- Token 有效期 24 小时（到期重新登录）

验收要点：
- 未登录访问受保护页面会跳转到登录页。
- 登录失败有明确错误提示。
- Token 失效时前端自动清理登录态并跳转登录页。

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
- 创建用户
- 编辑用户信息
- 修改用户角色（Admin/SA/Analyst）
- 删除用户
- 启用/禁用用户
- Admin 直接修改用户密码

权限：
- 仅 Admin 可访问与操作。

账号状态规则：
- 用户被禁用后无法登录系统。
- 已禁用用户可由 Admin 重新启用，启用后恢复正常登录能力。

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

### 5.2 后端 API（FastAPI）
- 认证接口：`/api/auth/login`, `/api/auth/logout`, `/api/auth/me`
- 密码能力（按常见网站做法）：
  - `POST /api/auth/forgot-password`：用户在登录页点击“忘记密码”后触发，发送重置邮件（邮件链接跳转 Supabase 托管重置页）
  - 管理员改密归属用户管理接口：`PUT /api/users/{id}/password`
- 用户管理 API：`/api/users`（CRUD、角色调整、启用/禁用、管理员改密）
- Region 管理 API：`/api/regions`
- Analyst 信息 API：`/api/analyst-info`

### 5.3 前端界面
- 登录页面（含“忘记密码”入口）
- 桌面主页（功能卡片 + 导航栏）
- 用户管理页面（仅 Admin）
- Region 管理页面（仅 Admin）
- Analyst 信息管理页面（仅 Admin）
- Axios 拦截器与路由守卫

### 5.4 运维与发布要求
- 默认 Admin 账号在部署初始化流程创建，首次上线后建议尽快修改（不强制）。
- 所有调试端点（debug/config、debug/test-rls 等）在生产环境必须关闭。

## 6. Key Decisions

1. 角色存储在 Supabase Auth `app_metadata`，仅服务端可改，避免用户自行提权。
2. 用户账号系统与 Analyst 信息系统解耦，独立管理。
3. 权限采用双层模型：功能权限与数据权限分离。
4. 管理功能仅 Admin；基础数据读取按业务需求向已认证用户开放。
5. 密码能力保持简化：用户忘记密码邮件重置 + 管理员直接改密；不增加额外复杂安全机制。
6. 非 Admin 强行访问管理路由返回 403 页面（文案：`No permission`）。
7. 前后端与数据库时间统一使用北京时间（UTC+8）。
8. 生产环境必须关闭调试端点。
