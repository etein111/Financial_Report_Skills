## ADDED Requirements

### Requirement: 系统提供 Region 数据模型

系统 SHALL 提供 Region（地区）数据模型，支持存储地区信息。

#### Scenario: Region 表结构
- **WHEN** 查看 region 表结构
- **THEN** 包含以下字段:
  - `id`: UUID 主键
  - `name`: VARCHAR 地区名称（如 "China", "USA"）
  - `code`: VARCHAR 地区代码（如 "CN", "US", "HK"）
  - `created_at`: TIMESTAMP 创建时间
  - `updated_at`: TIMESTAMP 更新时间

#### Scenario: Region name 唯一性约束
- **WHEN** 创建或更新 Region
- **THEN** name 字段必须有唯一约束
- **AND** 重复的 name 无法插入或更新

### Requirement: 系统 CRUD 操作受 RLS 保护

系统 SHALL 在 region 表上启用 Row Level Security (RLS)，根据角色控制访问。

#### Scenario: 所有认证用户可以查看 Region
- **WHEN** 任何已认证用户查询 region 表
- **THEN** RLS policy 允许 SELECT 操作
- **AND** 用户可以查看所有 Region 记录

#### Scenario: 只有 Admin 可以创建或修改 Region
- **WHEN** Admin 用户执行 INSERT 或 UPDATE 操作
- **THEN** RLS policy 允许操作
- **AND** 数据成功写入或更新

#### Scenario: 非 Admin 用户不能修改 Region 表
- **WHEN** SA 或 Analyst 角色的用户尝试 INSERT 或 UPDATE region 表
- **THEN** RLS policy 拒绝操作
- **AND** 数据库返回权限错误

### Requirement: 系统提供 Region CRUD API

系统 SHALL 提供完整的 Region 创建、读取、更新、删除接口。

#### Scenario: 获取 Region 列表
- **WHEN** 任何已认证用户调用 GET /api/regions
- **THEN** 后端返回所有 Region 记录
- **AND** 返回数据按 created_at 倒序排列（新创建的在前）

#### Scenario: 创建 Region
- **WHEN** Admin 用户调用 POST /api/regions
- **AND** 请求体包含: `{"name": "China", "code": "CN"}`
- **THEN** 后端验证 name 和 code 不为空
- **AND** 后端检查 name 是否已存在
- **AND** 创建成功返回新创建的 Region 对象
- **AND** 返回 201 状态码

#### Scenario: 创建 Region 时名称重复
- **WHEN** Admin 用户调用 POST /api/regions
- **AND** 请求体的 name 已存在
- **THEN** 后端返回 400 错误
- **AND** 错误消息: "Region with this name already exists"

#### Scenario: 更新 Region
- **WHEN** Admin 用户调用 PUT /api/regions/{id}
- **AND** 请求体包含更新后的 name 或 code
- **THEN** 后端验证 Region 存在
- **AND** 检查新 name 是否与其他 Region 重复
- **AND** 更新成功返回更新后的 Region 对象

#### Scenario: 删除 Region
- **WHEN** Admin 用户调用 DELETE /api/regions/{id}
- **THEN** 后端验证 Region 存在
- **AND** 检查是否有 Analyst 关联此 Region（可选，后期实现）
- **AND** 删除成功返回 204 状态码

### Requirement: 前端提供 Region 管理页面

系统 SHALL 提供 Region 管理页面，允许 Admin 管理地区数据。

#### Scenario: Region 管理页面布局
- **WHEN** Admin 用户访问 /regions 路由
- **THEN** 显示 Region 管理页面
- **AND** 页面包含 Region 列表（表格形式）
- **AND** 页面顶部有 "Create Region" 按钮（Admin only）
- **AND** 每个 Region 行有操作按钮（Edit, Delete）

#### Scenario: 创建 Region 对话框
- **WHEN** 用户点击 "Create Region" 按钮
- **THEN** 显示表单对话框
- **AND** 表单包含:
  - Name 输入框（必填）
  - Code 输入框（必填）
  - Submit 按钮
- **AND** 表单验证非空

#### Scenario: 编辑 Region
- **WHEN** 用户点击某个 Region 的 Edit 按钮
- **THEN** 显示编辑对话框（预填充现有数据）
- **AND** 用户修改 Name 或 Code
- **AND** 提交后调用 PUT /api/regions/{id}
- **AND** 成功后关闭对话框并刷新列表

#### Scenario: 删除 Region
- **WHEN** 用户点击某个 Region 的 Delete 按钮
- **THEN** 显示确认对话框
- **AND** 确认后调用 DELETE /api/regions/{id}
- **AND** 成功后从列表中移除该 Region

### Requirement: 非 Admin 用户无法访问 Region 管理

系统 SHALL 限制只有 Admin 用户可以访问 Region 管理功能。

#### Scenario: SA 或 Analyst 访问 Region 管理
- **WHEN** SA 或 Analyst 角色的用户尝试访问 /regions
- **THEN** 前端权限检查阻止显示卡片或页面
- **AND** 或显示权限不足提示
