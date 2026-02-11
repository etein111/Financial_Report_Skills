## ADDED Requirements

### Requirement: 系统提供 Analyst 数据模型

系统 SHALL 提供 Analyst（分析师）数据模型，支持存储分析师基本信息和关联 Region。

#### Scenario: Analyst 表结构
- **WHEN** 查看 analyst 表结构
- **THEN** 包含以下字段:
  - `id`: UUID 主键
  - `full_name`: VARCHAR 英文全名
  - `chinese_name`: VARCHAR 中文名（可选）
  - `email`: VARCHAR 邮箱（唯一，关联 Supabase Auth）
  - `suffix`: VARCHAR 后缀（如 "CFA"）
  - `region_id`: UUID 外键关联 region 表（可选）
  - `sfc`: VARCHAR SFC 执照号（可选）
  - `is_active`: BOOLEAN 是否启用（默认 true）
  - `created_at`: TIMESTAMP 创建时间
  - `updated_at`: TIMESTAMP 更新时间

#### Scenario: Email 唯一性约束
- **WHEN** 创建或更新 Analyst
- **THEN** email 字段必须在 analyst 表中唯一
- **AND** 重复的 email 无法插入或更新

### Requirement: 系统 CRUD 操作受 RLS 保护

系统 SHALL 在 analyst 表上启用 Row Level Security (RLS)，根据角色控制访问。

#### Scenario: 所有认证用户可以查看 Analyst
- **WHEN** 任何已认证用户查询 analyst 表
- **THEN** RLS policy 允许 SELECT 操作
- **AND** 用户可以查看所有 Analyst 记录（用于下拉选择等）

#### Scenario: 只有 Admin 可以创建或修改 Analyst
- **WHEN** Admin 用户执行 INSERT 或 UPDATE 操作
- **THEN** RLS policy 允许操作
- **AND** 数据成功写入或更新

#### Scenario: 非 Admin 用户不能修改 Analyst 表
- **WHEN** SA 或 Analyst 角色的用户尝试 INSERT 或 UPDATE analyst 表
- **THEN** RLS policy 拒绝操作
- **AND** 数据库返回权限错误

### Requirement: 创建 Analyst 时自动创建 Supabase Auth 用户

系统 SHALL 在创建 Analyst 记录时，自动在 Supabase Auth 中创建对应的认证用户。

#### Scenario: 创建新的 Analyst 和 Auth 用户
- **WHEN** Admin 用户调用 POST /api/analysts
- **AND** 提供的 email 在 Supabase Auth 中不存在
- **THEN** 后端首先在 analyst 表创建记录
- **AND** 然后使用 Supabase Admin API 创建 Auth 用户
- **AND** Auth 用户的 user_metadata 包含 full_name
- **AND** Auth 用户的 app_metadata 包含 role（"analyst"）和 analyst_id
- **AND** 生成随机密码或默认密码
- **AND** 返回 Analyst 记录和生成的密码

#### Scenario: Email 已存在于 Supabase Auth
- **WHEN** Admin 用户调用 POST /api/analysts
- **AND** 提供的 email 已在 Supabase Auth 中存在
- **THEN** 后端返回 400 错误
- **AND** 错误消息: "Email already exists in authentication system. Please use a different email or recover the existing account."

#### Scenario: Email 已存在于 analyst 表
- **WHEN** Admin 用户调用 POST /api/analysts
- **AND** 提供的 email 已在 analyst 表中存在
- **THEN** 后端返回 400 错误
- **AND** 错误消息: "Analyst with this email already exists"

#### Scenario: 创建失败时回滚
- **WHEN** 创建 Auth 用户失败（如 Supabase 服务错误）
- **THEN** 后端删除已创建的 analyst 记录（回滚）
- **AND** 返回 500 错误
- **AND** 错误消息包含 Supabase 错误详情

### Requirement: 系统提供 Analyst CRUD API

系统 SHALL 提供完整的 Analyst 创建、读取、更新、删除接口。

#### Scenario: 获取 Analyst 列表
- **WHEN** 前端调用 GET /api/analysts
- **AND** 用户已认证
- **THEN** 后端返回所有 Analyst 记录
- **AND** 返回数据按 created_at 倒序排列
- **AND** 可以通过 query 参数搜索（按 full_name 或 email）

#### Scenario: 创建 Analyst
- **WHEN** Admin 用户调用 POST /api/analysts
- **AND** 请求体包含: full_name, email, role 等字段
- **THEN** 后端验证必填字段
- **AND** 后端检查 email 唯一性
- **AND** 创建 analyst 记录和 Auth 用户
- **AND** 返回创建的 Analyst 对象
- **AND** 返回 201 状态码

#### Scenario: 更新 Analyst 基本信息
- **WHEN** Admin 用户调用 PUT /api/analysts/{id}
- **AND** 请求体包含要更新的字段
- **THEN** 后端验证 Analyst 存在
- **AND** 更新 analyst 表记录
- **AND** 如果更新了 email，同步更新 Supabase Auth 用户邮箱（使用 Admin API）
- **AND** 返回更新后的 Analyst 对象

#### Scenario: 启用/禁用 Analyst 账号
- **WHEN** Admin 用户调用 PUT /api/analysts/{id}/toggle-status
- **THEN** 后端切换 is_active 字段（true ↔ false）
- **AND** 同时在 Supabase Auth 中禁用/启用用户（使用 Admin API 的 ban_user 方法）
- **AND** 返回更新后的 Analyst 对象

#### Scenario: 重置 Analyst 密码
- **WHEN** Admin 用户调用 POST /api/analysts/{id}/reset-password
- **THEN** 后端生成新的随机密码
- **AND** 使用 Supabase Admin API 更新用户密码
- **AND** 返回新密码（仅一次显示机会）
- **AND** 或发送邮件给用户（Phase 1 暂缓，只记录到日志）

#### Scenario: 删除 Analyst
- **WHEN** Admin 用户调用 DELETE /api/analysts/{id}
- **THEN** 后端验证 Analyst 存在
- **AND** 删除 analyst 表记录
- **AND** 删除 Supabase Auth 中的用户（使用 Admin API）
- **AND** 返回 204 状态码

### Requirement: 前端提供 Analyst 管理页面

系统 SHALL 提供 Analyst 管理页面，允许 Admin 管理分析师信息。

#### Scenario: Analyst 管理页面布局
- **WHEN** Admin 用户访问 /analysts 路由
- **THEN** 显示 Analyst 管理页面
- **AND** 页面包含 Analyst 列表（表格形式）
- **AND** 页面顶部有搜索框（按姓名或邮箱搜索）
- **AND** 页面顶部有 "Create Analyst" 按钮（Admin only）
- **AND** 每个 Analyst 行有操作按钮（Edit, Reset Password, Toggle Status, Delete）

#### Scenario: 创建 Analyst 表单
- **WHEN** 用户点击 "Create Analyst" 按钮
- **THEN** 显示表单对话框或页面
- **AND** 表单包含:
  - Full Name 输入框（必填）
  - Chinese Name 输入框（可选）
  - Email 输入框（必填）
  - Role 选择器（必填: Analyst, SA, Admin）
  - Region 下拉选择（可选，从 Region 表获取）
  - Suffix 输入框（可选）
  - SFC License 输入框（可选）
  - Submit 按钮
- **AND** 表单验证必填字段和 email 格式

#### Scenario: 创建 Analyst 成功
- **WHEN** 用户提交创建表单
- **AND** 后端返回成功
- **THEN** 显示成功提示
- **AND** 如果后端返回了密码，显示生成的密码（仅一次）
- **AND** 提示管理员将密码安全地传达给用户
- **AND** 关闭对话框并刷新列表

#### Scenario: 编辑 Analyst
- **WHEN** 用户点击某个 Analyst 的 Edit 按钮
- **THEN** 显示编辑表单（预填充现有数据）
- **AND** 用户修改字段
- **AND** 提交后调用 PUT /api/analysts/{id}
- **AND** 成功后关闭对话框并刷新列表

#### Scenario: 重置密码
- **WHEN** 用户点击 "Reset Password" 按钮
- **THEN** 显示确认对话框
- **AND** 确认后调用 POST /api/analysts/{id}/reset-password
- **AND** 显示新生成的密码
- **AND** 提示密码仅显示一次

#### Scenario: 启用/禁用账号
- **WHEN** 用户点击启用/禁用按钮
- **THEN** 切换账号状态
- **AND** 成功后刷新列表并更新按钮文本（如 "Enable" ↔ "Disable"）

#### Scenario: 删除 Analyst
- **WHEN** 用户点击某个 Analyst 的 Delete 按钮
- **THEN** 显示确认对话框（警告：此操作将删除 Auth 用户和所有数据）
- **AND** 确认后调用 DELETE /api/analysts/{id}
- **AND** 成功后从列表中移除该 Analyst

### Requirement: 非 Admin 用户无法访问 Analyst 管理

系统 SHALL 限制只有 Admin 用户可以访问 Analyst 管理功能。

#### Scenario: SA 或 Analyst 访问 Analyst 管理
- **WHEN** SA 或 Analyst 角色的用户尝试访问 /analysts
- **THEN** 前端权限检查隐藏 Analyst 管理卡片或页面
- **AND** 或显示权限不足提示
- **AND** 桌面上的 Analysts 卡片标记为 "Admin Only"

### Requirement: 系统检查 Email 唯一性

系统 SHALL 在创建或更新 Analyst 前检查 email 的唯一性。

#### Scenario: Email 检查 API
- **WHEN** 前端调用 POST /api/analysts/check-email
- **AND** 提供 email 参数
- **THEN** 后端检查 email 是否可用
- **AND** 返回:
  - `available`: true/false
  - `exists_in_db`: 是否在 analyst 表中存在
  - `exists_in_auth`: 是否在 Supabase Auth 中存在
  - `message`: 提示信息
