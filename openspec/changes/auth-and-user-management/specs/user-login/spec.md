## ADDED Requirements

### Requirement: 用户可以通过邮箱密码登录并建立服务端会话
系统 SHALL 使用 Supabase Auth 验证邮箱与密码，并在验证成功后由 FastAPI 建立服务端会话。

#### Scenario: 登录成功
- **WHEN** 用户向 `POST /api/auth/login` 提交有效邮箱和密码
- **THEN** 系统 MUST 调用 Supabase Auth `sign_in_with_password` 完成身份验证
- **AND** 系统 MUST 写入 `HttpOnly`、`Secure`、`SameSite=Lax` 的会话 Cookie
- **AND** 用户进入桌面页 `/desktop`

#### Scenario: 登录失败
- **WHEN** 用户向 `POST /api/auth/login` 提交无效邮箱或密码
- **THEN** 系统 MUST 返回认证失败错误
- **AND** 系统 MUST NOT 写入会话 Cookie

### Requirement: 用户可以登出并清理会话
系统 SHALL 提供登出能力，并在登出时清除当前会话凭据。

#### Scenario: 登出成功
- **WHEN** 已登录用户调用 `POST /api/auth/logout`
- **THEN** 系统 MUST 清除会话 Cookie
- **AND** 后续受保护请求 MUST 视为未登录

### Requirement: 系统可以返回当前登录用户信息
系统 SHALL 提供当前用户信息接口，用于页面鉴权与展示。

#### Scenario: 获取当前用户
- **WHEN** 已登录用户调用 `GET /api/auth/me`
- **THEN** 系统 MUST 返回用户标识、邮箱、姓名和角色信息

#### Scenario: 凭据失效
- **WHEN** 用户会话 Cookie 缺失或 token 无效
- **THEN** `GET /api/auth/me` MUST 返回未登录错误

### Requirement: 会话有效期遵循 24 小时策略
系统 SHALL 采用 24 小时会话有效期，过期后要求用户重新登录。

#### Scenario: 会话过期
- **WHEN** 登录会话超过 24 小时有效期
- **THEN** 后续受保护接口 MUST 返回未登录或无效凭据错误
- **AND** 用户 MUST 重新登录后才可继续访问受保护页面
