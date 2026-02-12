## ADDED Requirements

### Requirement: 用户可以使用邮箱和密码登录系统

系统 SHALL 提供基于 Supabase Auth 的用户认证功能，支持使用邮箱和密码登录。

#### Scenario: 成功登录
- **WHEN** 用户在登录页输入有效的邮箱和密码
- **AND** 点击 "Login" 按钮
- **THEN** 系统调用 Supabase Auth API 验证凭据（`sign_in_with_password`）
- **AND** 验证成功后返回 Supabase Auth 原生 JWT access token（ES256 算法）
- **AND** Token 包含用户角色信息（从 `app_metadata.role`）
- **AND** 前端将 JWT token 存储在 localStorage
- **AND** 用户被重定向到桌面主页

#### Scenario: 登录失败
- **WHEN** 用户输入无效的邮箱或密码
- **AND** 点击 "Login" 按钮
- **THEN** 系统显示错误提示 "Invalid email or password"
- **AND** 用户停留在登录页

#### Scenario: JWT token 自动附加到请求
- **WHEN** 用户已登录（localStorage 中有有效 token）
- **AND** 前端发送 API 请求
- **THEN** Axios 拦截器自动从 localStorage 读取 JWT token
- **AND** 将 token 添加到请求的 `Authorization` header（格式: `Bearer <token>`）

### Requirement: 用户可以登出系统

系统 SHALL 提供登出功能，清除本地认证状态。

#### Scenario: 成功登出
- **WHEN** 用户点击桌面右上角的 "Logout" 按钮
- **THEN** 系统清除 localStorage 中的 JWT token
- **AND** 清除前端的用户状态
- **AND** 重定向到登录页

### Requirement: 系统验证每个 API 请求的 JWT token

系统 SHALL 在后端验证每个受保护 API 请求的 JWT token。

#### Scenario: 有效的 JWT token
- **WHEN** API 请求包含有效的 Supabase Auth JWT token
- **THEN** 后端使用 `supabase_client.auth.get_user(jwt=token)` 验证 token
- **AND** 验证成功后从 `user.app_metadata` 中提取角色信息
- **AND** 请求正常处理，返回数据

#### Scenario: 无效或过期的 JWT token
- **WHEN** API 请求包含无效或过期的 JWT token
- **THEN** 后端返回 401 Unauthorized 错误
- **AND** 前端拦截器捕获 401 错误
- **AND** 清除本地 token
- **AND** 重定向到登录页

#### Scenario: 缺少 JWT token
- **WHEN** API 请求未包含 `Authorization` header
- **THEN** 后端返回 401 Unauthorized 错误
- **AND** 前端重定向到登录页

### Requirement: 系统提供获取当前用户信息的 API

系统 SHALL 提供 API 接口让前端获取当前登录用户的信息。

#### Scenario: 获取当前用户成功
- **WHEN** 前端调用 GET /api/auth/me
- **AND** 请求包含有效的 Supabase Auth JWT token
- **THEN** 后端使用 `supabase_client.auth.get_user()` 验证并获取用户信息
- **AND** 从 `user.app_metadata` 提取角色，从 `user.user_metadata` 提取姓名
- **AND** 返回用户 ID、邮箱、角色、姓名等信息
- **AND** 不需要额外查询数据库

### Requirement: 系统提供初始化 Admin 用户的脚本

系统 SHALL 提供独立的初始化脚本，用于创建默认的 Admin 用户。

#### Scenario: 创建默认 Admin 用户
- **WHEN** 开发者在后端目录运行 `uv run scripts/init_admin.py`
- **THEN** 脚本连接到 Supabase
- **AND** 使用 Supabase Admin API 创建用户
- **AND** 用户邮箱为硬编码值（如 admin@neolyst.com）
- **AND** 密码为硬编码默认值（如 Admin123）
- **AND** 用户角色设置在 **app_metadata** 中为 admin（仅服务端可修改）
- **AND** 用户姓名设置在 user_metadata 中（如 full_name: "System Administrator"）
- **AND** 脚本输出创建成功信息

#### Scenario: Admin 用户已存在
- **WHEN** 运行初始化脚本
- **AND** Admin 用户已存在
- **THEN** 脚本显示 "Admin user already exists"
- **AND** 不重复创建用户

### Requirement: 未登录用户无法访问受保护页面

系统 SHALL 使用路由守卫阻止未登录用户访问受保护页面。

#### Scenario: 未登录访问受保护页面
- **WHEN** 用户未登录（localStorage 中无 token）
- **AND** 尝试直接访问 /desktop 或其他受保护路由
- **THEN** Vue Router 守卫拦截请求
- **AND** 自动重定向到登录页

#### Scenario: 已登录访问登录页
- **WHEN** 用户已登录（localStorage 中有有效 token）
- **AND** 尝试访问 /login 路由
- **THEN** Vue Router 守卫拦截请求
- **AND** 自动重定向到 /desktop
