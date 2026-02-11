## ADDED Requirements

### Requirement: 用户登录

系统 SHALL 支持 Supabase Auth 用户登录。

#### Scenario: 用户可以使用邮箱密码登录
- **WHEN** 用户在登录页面输入有效的邮箱和密码
- **THEN** 系统必须调用 Supabase Auth API 进行验证
- **AND** 验证成功后必须返回有效的访问令牌
- **AND** 用户必须被重定向到报告列表页面

#### Scenario: 登录失败显示错误信息
- **WHEN** 用户输入错误的邮箱或密码
- **THEN** 系统必须显示登录失败的错误提示
- **AND** 用户必须保持在登录页面

#### Scenario: 未登录用户无法访问受保护页面
- **WHEN** 未登录用户尝试访问报告列表或详情页面
- **THEN** 系统必须重定向到登录页面

### Requirement: 用户角色管理

系统 SHALL 支持两种用户角色：Analyst 和 Admin。

#### Scenario: 用户具有 Analyst 角色
- **WHEN** 用户以 Analyst 角色登录
- **THEN** 用户只能查看自己作为作者的报告
- **AND** 用户无法访问 Admin 管理页面

#### Scenario: 用户具有 Admin 角色
- **WHEN** 用户以 Admin 角色登录
- **THEN** 用户可以查看所有报告
- **AND** 用户可以访问 Admin 管理页面（邮箱配置、订阅管理、发送记录）

### Requirement: 用户认证状态管理

系统 SHALL 维护用户的认证状态。

#### Scenario: 访问令牌自动刷新
- **WHEN** 用户的访问令牌即将过期
- **THEN** 系统必须自动刷新令牌
- **AND** 用户会话必须保持有效

#### Scenario: 用户登出
- **WHEN** 用户点击登出按钮
- **THEN** 系统必须清除本地存储的令牌
- **AND** 用户必须被重定向到登录页面
- **AND** 后续请求必须使用清除后的认证状态
