## ADDED Requirements

### Requirement: 系统提供登录页面

系统 SHALL 提供登录页面，包含粒子背景效果和登录表单。

#### Scenario: 登录页面布局
- **WHEN** 用户访问 /login 路由
- **THEN** 显示登录页面
- **AND** 页面包含粒子背景效果（Canvas 2D）
- **AND** 背景为渐变色（深蓝色到黑色: `linear-gradient(to bottom, #0c1221 0%, #09090b 50%, #020617 100%)`）
- **AND** 中心显示登录表单框

#### Scenario: 粒子背景效果
- **WHEN** 登录页面加载完成
- **THEN** Canvas 渲染 120 个粒子
- **AND** 粒子颜色为蓝色-青色渐变（hue: 200-260）
- **AND** 粒子大小在 1-3px 之间随机
- **AND** 粒子透明度在 0.3-0.7 之间
- **AND** 粒子间距离小于 140px 时绘制连线
- **AND** 连线透明度根据距离渐变
- **AND** 粒子缓慢漂浮移动（速度系数: 2）
- **AND** 粒子有脉冲闪烁效果（脉冲速度: 0.15）
- **AND** 无鼠标交互效果

#### Scenario: 登录表单布局
- **WHEN** 用户查看登录表单
- **THEN** 登录框居中显示（尺寸: 400px × 420px）
- **AND** 登录框背景为 zinc-900 (#18181b)
- **AND** 登录框有 1px white/10 边框
- **AND** 登录框圆角为 12px
- **AND** 表单包含:
  - 标题 "The Future is Now"（32px, white-space: nowrap）
  - 副标题 "Research Report Management System"
  - Email 输入框
  - Password 输入框
  - Login 按钮

### Requirement: 登录表单验证用户输入

系统 SHALL 在提交前验证登录表单的输入。

#### Scenario: 输入框为空时提交
- **WHEN** Email 或 Password 输入框为空
- **AND** 用户点击 Login 按钮
- **THEN** 表单验证阻止提交
- **AND** 显示验证错误提示 "Email and password are required"

#### Scenario: Email 格式无效
- **WHEN** 用户输入的 Email 格式无效
- **AND** 失去焦点或尝试提交
- **THEN** 显示验证错误 "Invalid email format"

#### Scenario: 输入验证通过
- **WHEN** 用户输入有效的 Email 和密码（至少 1 个字符）
- **THEN** 表单允许提交
- **AND** 调用登录 API

### Requirement: 登录表单调用后端登录 API

系统 SHALL 在表单验证通过后调用后端登录接口。

#### Scenario: 成功调用登录 API
- **WHEN** 用户提交有效的登录表单
- **THEN** 前端调用 POST /api/auth/login
- **AND** 请求体包含: `{"email": "<user-email>", "password": "<user-password>"}`
- **AND** 显示加载状态（按钮禁用或显示 loading spinner）

#### Scenario: 登录成功后跳转
- **WHEN** 登录 API 返回成功响应
- **THEN** 前端将 JWT token 存储在 localStorage（key: "auth_token"）
- **AND** 存储用户信息（key: "user_info"）
- **AND** Vue Router 跳转到 /desktop 路由

#### Scenario: 登录失败显示错误
- **WHEN** 登录 API 返回错误（如 401）
- **THEN** 在表单顶部或输入框下方显示错误消息
- **AND** 错误消息: "Invalid email or password"
- **AND** 输入框不高亮错误状态（避免 UX 问题）
- **AND** 按钮恢复正常状态

### Requirement: 登录页面性能优化

系统 SHALL 优化登录页面的加载和渲染性能。

#### Scenario: 登录成功后停止粒子动画
- **WHEN** 用户登录成功并跳转到桌面
- **THEN** 登录页面的粒子动画立即停止
- **AND** 释放 Canvas 资源

#### Scenario: 粒子动画性能
- **WHEN** 粒子动画运行中
- **THEN** 使用 `requestAnimationFrame` 实现 60fps
- **AND** Canvas 使用 `will-change: transform` CSS 属性
- **AND** 粒子数量限制在 120（不太多，保证性能）
