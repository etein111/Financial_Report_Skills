## ADDED Requirements

### Requirement: 系统支持三种用户角色

系统 SHALL 支持三种用户角色：Admin（系统管理员）、SA（合规人员）、Analyst（分析师）。

#### Scenario: 角色存储在 Supabase Auth app_metadata
- **WHEN** 创建用户时
- **THEN** 角色信息存储在 Supabase Auth 的 **app_metadata** 中（仅服务端可修改）
- **AND** user_metadata 包含用户可修改的信息: `{"full_name": "John Doe"}`
- **AND** app_metadata 包含安全相关信息: `{"role": "admin", "analyst_id": "<uuid>", "provider": "email"}`
- **AND** role 字段只存在 app_metadata 中，不存在 user_metadata 中（防止用户自行修改权限）

#### Scenario: JWT token 包含角色信息
- **WHEN** 用户成功登录
- **THEN** Supabase Auth 生成的 JWT token 包含 role 信息
- **AND** 后端和 RLS policies 可以从 JWT 中读取角色

### Requirement: 数据库提供 RLS 辅助函数

系统 SHALL 提供 PostgreSQL 函数从 JWT token 中提取当前用户的角色和 ID。

#### Scenario: 获取当前用户角色
- **WHEN** RLS policy 或数据库函数调用 `get_current_role()`
- **THEN** 函数从 JWT token 的 app_metadata 中提取 role
- **AND** 返回角色字符串: "admin", "sa", 或 "analyst"

#### Scenario: 获取当前 analyst_id
- **WHEN** RLS policy 或数据库函数调用 `get_current_analyst_id()`
- **THEN** 函数从 JWT token 的 app_metadata 中提取 analyst_id
- **AND** 返回 UUID 类型

### Requirement: analyst 表启用 RLS 并配置权限策略

系统 SHALL 在 analyst 表上启用 Row Level Security (RLS)，并根据角色配置访问策略。

#### Scenario: 所有认证用户可以查看 analyst 信息
- **WHEN** 任何已认证用户查询 analyst 表
- **THEN** RLS policy 允许 SELECT 操作
- **AND** 用户可以查看所有 analyst 记录（用于下拉选择等）

#### Scenario: 只有 Admin 可以创建或修改 analyst 记录
- **WHEN** Admin 用户执行 INSERT 或 UPDATE 操作
- **THEN** RLS policy 允许操作
- **AND** 数据成功写入或更新

#### Scenario: 非 Admin 用户不能修改 analyst 表
- **WHEN** SA 或 Analyst 角色的用户尝试 INSERT 或 UPDATE analyst 表
- **THEN** RLS policy 拒绝操作
- **AND** 数据库返回权限错误

### Requirement: JWT 验证中间件从 token 中提取用户信息

系统 SHALL 提供 FastAPI 依赖函数，从 JWT token 中提取用户信息并注入到请求中。

#### Scenario: 成功验证 JWT 并提取用户信息
- **WHEN** API 请求包含有效的 JWT token
- **THEN** JWT 验证中间件解析 token
- **AND** 提取 user_id, role, analyst_id 等信息
- **AND** 将信息注入到请求的 `state` 中
- **AND** 后续路由处理器可以访问这些信息

#### Scenario: JWT 验证失败
- **WHEN** JWT token 无效、过期或格式错误
- **THEN** JWT 验证中间件抛出 HTTPException
- **AND** 返回 401 Unauthorized 状态码
- **AND** 错误消息: "Invalid or expired token"

### Requirement: 前端提供权限检查函数库

系统 SHALL 提供前端权限检查函数，用于 UI 层面的显示控制（注意：实际权限由 RLS 保证）。

#### Scenario: 检查用户是否可以访问桌面
- **WHEN** 前端调用权限检查函数
- **THEN** 函数返回用户是否已认证（基于 localStorage 的 token）

#### Scenario: 检查用户是否为 Admin
- **WHEN** 前端调用 `can.isAdmin(user)`
- **THEN** 函数检查 user.role === 'admin'
- **AND** 返回 true 或 false

#### Scenario: 检查用户是否可以访问审核页面
- **WHEN** 前端调用 `can.accessReviewPage(user)`
- **THEN** 函数检查 user.role 是否为 'sa' 或 'admin'
- **AND** 返回 true 或 false
