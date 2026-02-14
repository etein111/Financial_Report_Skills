## ADDED Requirements

### Requirement: 用户可以通过邮箱密码登录并建立 cookies 会话（Supabase SSR）
系统 SHALL 使用 Supabase Auth 验证邮箱与密码，并在验证成功后建立基于 cookies 的会话（用于 SSR）。

#### Scenario: 登录成功
- **WHEN** 用户在登录页 `/login` 提交有效邮箱和密码
- **THEN** 系统 MUST 调用 Supabase Auth `signInWithPassword` 完成身份验证
- **AND** 系统 MUST 建立 cookies 会话（遵循 Supabase SSR 默认 cookie 行为，不强制 HttpOnly）
- **AND** 用户 MUST 进入桌面页 `/desktop`

#### Scenario: 登录失败
- **WHEN** 用户在 `/login` 提交无效邮箱或密码
- **THEN** 系统 MUST 返回认证失败提示
- **AND** 系统 MUST NOT 建立登录会话

### Requirement: 用户可以登出并清理会话
系统 SHALL 提供登出能力，并在登出时清除当前会话凭据。

#### Scenario: 登出成功
- **WHEN** 已登录用户触发登出
- **THEN** 系统 MUST 清除 cookies 会话
- **AND** 后续访问受保护页面 MUST 视为未登录并跳转 `/login`

### Requirement: 系统可获取当前登录用户信息用于鉴权与展示
系统 SHALL 在服务端获取当前登录用户信息，并以 `app_metadata.role` 作为角色事实源。

#### Scenario: 访问受保护页面
- **WHEN** 用户访问 `/desktop` 或其他受保护页面
- **THEN** 系统 MUST 获取当前用户的 `id`、`email` 与 `app_metadata.role`
- **AND** 系统 MUST 基于角色执行页面访问控制

#### Scenario: 未登录访问受保护页面
- **WHEN** 未登录用户访问受保护页面
- **THEN** 系统 MUST 跳转到 `/login`

### Requirement: 会话有效期遵循 Supabase 默认机制
系统 SHALL 遵循 Supabase 默认会话机制（access token 自动 refresh），不强制 24 小时重新登录。

#### Scenario: 会话失效或 refresh 失败
- **WHEN** 用户会话无效或 refresh 失败
- **THEN** 系统 MUST 将用户视为未登录
- **AND** 系统 MUST 跳转到 `/login`

