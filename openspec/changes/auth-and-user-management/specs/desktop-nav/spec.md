## ADDED Requirements

### Requirement: 系统提供桌面启动器页面
系统 SHALL 提供桌面页作为功能入口（Launcher）。

#### Scenario: 登录后进入桌面
- **WHEN** 用户登录成功
- **THEN** 系统 MUST 将用户引导到 `/desktop`
- **AND** 桌面页 MUST 展示可访问功能入口

### Requirement: 功能页采用新标签打开且不提供返回桌面链接
系统 SHALL 采用 Desktop-as-Launcher 导航契约。

#### Scenario: 从桌面打开功能页
- **WHEN** 用户点击桌面功能卡片
- **THEN** 系统 MUST 使用新标签页打开目标功能页

#### Scenario: 功能页导航约束
- **WHEN** 用户在 Users、Regions、Analyst Info 页面操作
- **THEN** 页面 MUST NOT 提供“返回桌面”链接
- **AND** 用户通过关闭标签页返回桌面

### Requirement: 登录页与桌面页视觉风格必须对齐原型基线
系统 SHALL 保持深色背景、简单大气、专业、科技感的视觉方向，并对齐原型页面。

#### Scenario: 视觉验收
- **WHEN** 进行登录页与桌面页验收
- **THEN** 页面风格 MUST 与下列原型保持一致：
- **AND** `openspec/changes/auth-and-user-management/01-login-page.jpg`
- **AND** `openspec/changes/auth-and-user-management/02-desktop.jpg`

### Requirement: 界面语言与时间展示遵循统一约定
系统 SHALL 使用英文界面文案，并按 UTC+8 展示时间。

#### Scenario: 页面文案与时间显示
- **WHEN** 用户访问登录页、桌面页及管理页
- **THEN** 按钮、标题、表单标签与提示文案 MUST 为英文
- **AND** 时间显示 MUST 使用 UTC+8
