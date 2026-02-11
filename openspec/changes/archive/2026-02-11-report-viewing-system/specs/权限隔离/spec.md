## ADDED Requirements

### Requirement: 角色权限定义

系统 SHALL 定义 Analyst 和 Admin 两种角色的权限范围。

#### Scenario: Analyst 角色权限
- **WHEN** 用户具有 Analyst 角色
- **THEN** 用户只能查看自己作为作者的报告
- **AND** 用户无法访问 Admin 管理页面
- **AND** 用户无法修改邮箱配置
- **AND** 用户无法管理订阅
- **AND** 用户无法查看发送记录

#### Scenario: Admin 角色权限
- **WHEN** 用户具有 Admin 角色
- **THEN** 用户可以查看所有报告
- **AND** 用户可以访问 Admin 管理页面
- **AND** 用户可以管理邮箱配置
- **AND** 用户可以管理订阅
- **AND** 用户可以查看发送记录

### Requirement: API 权限控制

系统 SHALL 在 API 层面实施权限控制。

#### Scenario: 报告列表 API 权限
- **WHEN** 用户调用 GET /api/v1/reports 接口
- **THEN** 系统必须检查用户角色
- **AND** 如果是 Analyst，系统必须只返回该用户作为作者的报告
- **AND** 如果是 Admin，系统必须返回所有报告

#### Scenario: 报告详情 API 权限
- **WHEN** 用户调用 GET /api/v1/reports/{id} 接口
- **THEN** 系统必须检查用户是否有权限访问该报告
- **AND** 如果是 Analyst 且不是报告作者，系统必须返回 403 Forbidden
- **AND** 如果是 Admin 或是报告作者，系统必须返回报告详情

#### Scenario: Admin API 权限
- **WHEN** 用户调用 Admin 相关 API（邮箱配置、订阅管理、发送记录）
- **THEN** 系统必须检查用户是否为 Admin 角色
- **AND** 如果不是 Admin，系统必须返回 403 Forbidden

### Requirement: 前端路由权限

系统 SHALL 在前端路由层面实施权限控制。

#### Scenario: Analyst 访问 Admin 页面
- **WHEN** Analyst 角色用户尝试访问 Admin 管理页面
- **THEN** 系统必须重定向到报告列表页面
- **AND** 系统必须显示权限不足的提示

#### Scenario: 未登录用户访问
- **WHEN** 未登录用户尝试访问任何受保护的页面
- **THEN** 系统必须重定向到登录页面
- **AND** 登录成功后必须重定向回原请求页面

### Requirement: 数据隔离

系统 SHALL 在数据库层面确保数据隔离。

#### Scenario: Analyst 数据查询隔离
- **WHEN** Analyst 用户查询报告数据
- **THEN** 系统必须在 SQL 查询中自动添加 analyst_id 过滤条件
- **AND** 系统必须确保无法通过修改请求参数绕过过滤

#### Scenario: 报告关联数据隔离
- **WHEN** Analyst 用户查询报告详情
- **THEN** 系统必须同时检查报告附件的访问权限
- **AND** 系统必须确保附件下载链接包含权限验证

### Requirement: 权限错误处理

系统 SHALL 提供友好的权限错误提示。

#### Scenario: 权限不足提示
- **WHEN** 用户执行无权限的操作
- **THEN** 系统必须显示明确的权限不足提示
- **AND** 系统必须记录权限违规日志（包含用户 ID、操作类型、时间）

#### Scenario: 隐藏无权限功能
- **WHEN** 用户访问页面
- **THEN** 系统必须隐藏用户无权限访问的功能入口
- **AND** Admin 管理菜单只对 Admin 角色显示
