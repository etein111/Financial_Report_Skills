## ADDED Requirements

### Requirement: 系统提供桌面主页

系统 SHALL 提供桌面式主页，显示功能卡片分组。

#### Scenario: 桌面主页布局
- **WHEN** 用户访问 /desktop 路由
- **THEN** 显示桌面主页
- **AND** 页面包含顶部导航栏
- **AND** 页面包含两个功能卡片分组:
  - Reports 功能组（上方）
  - Data Management 功能组（下方）
- **AND** 背景色为渐变（`linear-gradient(to bottom, #0c1221 0%, #09090b 50%, #020617 100%)`）

#### Scenario: 顶部导航栏
- **WHEN** 用户查看桌面主页
- **THEN** 顶部导航栏包含:
  - 左侧: Logo "Neolyst"
  - 右侧: 欢迎文本 "Welcome, {user_name}" 和 Logout 按钮
- **AND** 导航栏背景为 zinc-900 (#18181b)
- **AND** 导航栏底部有 1px white/10 边框
- **AND** 欢迎文本为 14px, zinc-400 颜色
- **AND** Logout 按钮有悬停效果（zinc-400 → zinc-300）

#### Scenario: Reports 功能组
- **WHEN** 用户查看桌面主页
- **THEN** Reports 功能组显示以下卡片:
  - 📝 Reports - View all reports
  - ➕ New Report - Create new report
  - ✅ Report Review - Review submitted reports (SA/Admin only)
  - 📄 Templates - Report template management
- **AND** 卡片组有标题 "Reports"（可选，或直接显示卡片）
- **AND** 卡片以网格形式排列

#### Scenario: Data Management 功能组
- **WHEN** 用户查看桌面主页
- **THEN** Data Management 功能组显示以下卡片:
  - 👤 Analyst Info - Analyst information management (Admin only)
  - 🏢 Coverage - Company coverage management
  - 🏗️ Sectors - Industry classification management
  - 🌍 Regions - Region management
- **AND** 卡片组有标题 "Data Management"（可选，或直接显示卡片）
- **AND** 卡片以网格形式排列

### Requirement: 功能卡片显示占位状态

系统 SHALL 在桌面主页显示所有功能卡片，但标记为占位状态。

#### Scenario: 所有卡片标记为 Coming Soon
- **WHEN** 用户查看桌面主页
- **THEN** 所有功能卡片显示 "Coming Soon" 标签
- **AND** 卡片可点击，但在新标签页打开后显示占位页面
- **AND** 占位页面提示 "This feature is coming soon"

#### Scenario: 功能卡片样式
- **WHEN** 用户查看功能卡片
- **THEN** 每个卡片包含:
  - 图标（emoji，40px）
  - 标题（14px, font-weight 500）
  - 描述（12px, zinc-500）
- **AND** 卡片背景为 zinc-900 (#18181b)
- **AND** 卡片有 1px white/10 边框
- **AND** 卡片有悬停效果:
  - 边框变亮为 white/20
  - 轻微上移 2px
  - 过渡动画 200ms

### Requirement: 功能卡片在新标签页打开

系统 SHALL 使用 target="_blank" 在新标签页打开功能页面。

#### Scenario: 点击功能卡片
- **WHEN** 用户点击功能卡片
- **THEN** 在新标签页打开对应功能页面
- **AND** 桌面主页保持在原标签页
- **AND** 功能页面有独立 URL（如 /reports, /analysts 等）

#### Scenario: 功能页面返回链接
- **WHEN** 用户在新标签页查看功能页面
- **THEN** 页面头部包含 "← Back to Desktop" 链接
- **AND** 点击后关闭当前标签页或跳回 /desktop

### Requirement: Logout 功能清除认证状态

系统 SHALL 提供登出功能，清除本地认证状态并重定向。

#### Scenario: 点击 Logout 按钮
- **WHEN** 用户点击顶部导航栏的 Logout 按钮
- **THEN** 清除 localStorage 中的 auth_token 和 user_info
- **AND** 清除前端的用户状态
- **AND** Vue Router 跳转到 /login 路由
- **AND** 显示成功提示 "Logged out successfully"

### Requirement: 桌面主页显示用户信息

系统 SHALL 在顶部导航栏显示当前登录用户的信息。

#### Scenario: 显示欢迎消息
- **WHEN** 用户登录并访问桌面
- **THEN** 顶部导航栏显示 "Welcome, {user_name}"
- **AND** user_name 从用户信息中获取（优先使用 full_name，如无则使用 email）
- **AND** 文本颜色为 zinc-400

#### Scenario: 未登录状态
- **WHEN** 用户未登录（localStorage 中无 token）
- **AND** 尝试访问 /desktop
- **THEN** Vue Router 守卫拦截请求
- **AND** 自动重定向到 /login
