## ADDED Requirements

### Requirement: Admin 可以直接修改任意用户密码
系统 SHALL 提供管理员改密接口，允许 Admin 为指定用户设置新密码。

#### Scenario: Admin 改密成功
- **WHEN** Admin 调用 `PUT /api/users/{id}/password` 并提交新密码
- **THEN** 系统 MUST 更新目标用户密码
- **AND** 目标用户后续登录 MUST 使用新密码

### Requirement: 管理员改密不要求提供旧密码
系统 SHALL 在管理员改密场景下仅要求目标用户标识和新密码，不要求旧密码。

#### Scenario: 不提供旧密码
- **WHEN** Admin 发起改密请求且请求体不含旧密码
- **THEN** 系统 MUST 允许处理该请求

### Requirement: 非 Admin 不得调用管理员改密接口
系统 SHALL 对管理员改密接口实施 Admin 角色限制。

#### Scenario: 非 Admin 调用改密接口
- **WHEN** SA 或 Analyst 调用 `PUT /api/users/{id}/password`
- **THEN** 系统 MUST 返回 403 无权限
