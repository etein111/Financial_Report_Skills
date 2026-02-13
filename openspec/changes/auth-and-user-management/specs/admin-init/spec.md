## ADDED Requirements

### Requirement: 系统提供初始 Admin 账号初始化能力
系统 SHALL 提供初始化流程，用于在系统首次部署时创建可登录的 Admin 账号。

#### Scenario: 首次初始化
- **WHEN** 目标环境尚未存在 Admin 账号
- **THEN** 系统 MUST 创建一个角色为 `admin` 的可登录账号
- **AND** 角色信息 MUST 写入 Supabase Auth `app_metadata.role`

### Requirement: 初始化流程必须幂等
系统 SHALL 保证初始化重复执行不会创建重复 Admin 账号。

#### Scenario: 重复执行初始化
- **WHEN** 环境中已存在 Admin 账号
- **THEN** 初始化流程 MUST 跳过重复创建
- **AND** 系统状态 MUST 保持一致

### Requirement: 初始化流程不通过业务管理接口暴露
系统 SHALL 将 Admin 初始化能力限制在部署流程或运维脚本中，不作为普通业务 API 提供。

#### Scenario: 运行时业务访问
- **WHEN** 普通业务请求尝试触发 Admin 初始化
- **THEN** 系统 MUST 拒绝该请求
