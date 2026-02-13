## ADDED Requirements

### Requirement: 用户可以通过忘记密码流程请求重置邮件
系统 SHALL 提供忘记密码接口，向邮箱发送重置密码链接。

#### Scenario: 提交忘记密码请求
- **WHEN** 用户调用 `POST /api/auth/forgot-password` 并提交邮箱
- **THEN** 系统 MUST 调用 Supabase 重置密码能力发送邮件
- **AND** 接口响应 MUST 使用统一提示文案

#### Scenario: 邮箱不存在
- **WHEN** 用户提交不存在的邮箱
- **THEN** 接口 MUST 返回与成功请求一致的统一提示
- **AND** 系统 MUST NOT 暴露邮箱是否存在

### Requirement: 用户可以通过重置链接设置新密码
系统 SHALL 提供重置密码接口，允许用户通过有效重置凭据设置新密码。

#### Scenario: 重置成功
- **WHEN** 用户调用 `POST /api/auth/reset-password` 并提交有效重置凭据与新密码
- **THEN** 系统 MUST 更新该用户密码
- **AND** 用户后续可以使用新密码登录

#### Scenario: 重置凭据无效
- **WHEN** 用户提交过期或无效重置凭据
- **THEN** 系统 MUST 返回重置失败错误
