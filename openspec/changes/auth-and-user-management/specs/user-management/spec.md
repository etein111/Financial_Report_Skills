## ADDED Requirements

### Requirement: 系统提供用户管理列表与搜索能力
系统 SHALL 提供用户管理列表，并支持按姓名或邮箱搜索。

#### Scenario: 查询用户列表
- **WHEN** Admin 调用 `GET /api/users`
- **THEN** 系统 MUST 返回用户列表
- **AND** 系统 MUST 支持姓名与邮箱搜索条件

### Requirement: 系统支持用户基础 CRUD
系统 SHALL 提供创建、编辑、删除用户能力。

#### Scenario: 创建用户
- **WHEN** Admin 调用 `POST /api/users` 并提交合法用户信息
- **THEN** 系统 MUST 创建对应用户账号

#### Scenario: 编辑与删除用户
- **WHEN** Admin 调用 `PUT /api/users/{id}` 或 `DELETE /api/users/{id}`
- **THEN** 系统 MUST 更新或删除目标用户

### Requirement: 系统支持角色调整与启用禁用
系统 SHALL 支持调整用户角色，以及启用/禁用用户状态。

#### Scenario: 调整角色
- **WHEN** Admin 调用 `PUT /api/users/{id}/role`
- **THEN** 系统 MUST 更新目标用户角色为 `admin`、`sa` 或 `analyst`

#### Scenario: 启用禁用账号
- **WHEN** Admin 调用 `PUT /api/users/{id}/toggle-status`
- **THEN** 系统 MUST 切换目标用户启用状态
- **AND** 被禁用用户 MUST 无法继续登录

### Requirement: 用户管理能力仅对 Admin 开放
系统 SHALL 对用户管理相关页面和 API 强制执行 Admin 权限。

#### Scenario: 非 Admin 访问用户管理
- **WHEN** SA 或 Analyst 访问 `/users` 或调用用户管理写操作 API
- **THEN** 系统 MUST 返回 403 无权限
