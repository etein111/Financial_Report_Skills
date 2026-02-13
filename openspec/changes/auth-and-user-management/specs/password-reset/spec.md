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

### Requirement: 用户通过 Supabase 托管重置页设置新密码
系统 SHALL 使用 Supabase 托管重置页完成新密码设置，不提供站内重置密码提交接口。

#### Scenario: 重置成功
- **WHEN** 用户点击邮件中的重置链接并在 Supabase 托管重置页提交新密码
- **THEN** 用户密码 MUST 被更新
- **AND** 用户后续可以使用新密码登录本系统

#### Scenario: 重置凭据无效
- **WHEN** 用户访问过期或无效的重置链接
- **THEN** Supabase 托管重置页 MUST 返回失败提示

#### Scenario: 站内不暴露重置提交接口
- **WHEN** 客户端尝试调用 `POST /api/auth/reset-password`
- **THEN** 系统 MUST NOT 提供该接口
