# desktop-nav Specification

## Purpose
TBD - created by archiving change auth-and-users-mvp. Update Purpose after archive.
## Requirements
### Requirement: 登录后默认进入 Desktop
系统 SHALL 将桌面页作为登录后默认落地页。

#### Scenario: 登录后进入桌面
- **WHEN** 用户登录成功
- **THEN** 系统 MUST 将用户引导到 `/desktop`

### Requirement: Desktop 作为 Launcher（Desktop-as-Launcher 契约）
系统 SHALL 采用 Desktop-as-Launcher 导航契约。

#### Scenario: 从桌面打开功能页
- **WHEN** 用户点击桌面功能卡片
- **THEN** 系统 MUST 使用新标签页打开目标功能页

#### Scenario: 功能页导航约束
- **WHEN** 用户在 Users 等功能页操作
- **THEN** 页面 MUST NOT 提供“返回桌面”链接
- **AND** 用户通过关闭标签页返回桌面

### Requirement: Desktop 需提供真实 Logout
系统 SHALL 在桌面页提供真实登出能力，而非仅做跳转。

#### Scenario: 点击 Logout
- **WHEN** 已登录用户点击 Logout
- **THEN** 系统 MUST 清理 cookies 会话
- **AND** 系统 MUST 将用户引导回 `/login`

### Requirement: Desktop 风格需与 UI 原型规格一致
系统 SHALL 保持桌面页视觉风格与 UI 原型规格一致。

#### Scenario: 视觉验收
- **WHEN** 进行桌面页验收
- **THEN** 页面风格 MUST 与 `openspec/specs/ui-prototype-desktop/spec.md` 一致

### Requirement: Desktop 显示仅 Admin 可见的管理卡片
The system SHALL 仅在 Desktop 为 Admin 用户显示 Regions 和 Analyst Info 管理卡片。

#### Scenario: Admin 看到管理卡片
- **当** Admin 用户访问 Desktop 页面
- **则** 系统显示 Regions 卡片
- **且** 系统显示 Analyst Info 卡片
- **且** 两个卡片都在 Data Management 区域可见

#### Scenario: 非 Admin 看不到管理卡片
- **当** 非 Admin 用户（SA 或 Analyst）访问 Desktop 页面
- **则** 系统不显示 Regions 卡片
- **且** 系统不显示 Analyst Info 卡片

### Requirement: 管理卡片在新标签页打开
The system SHALL 在点击时在新标签页打开管理页面，遵循 Desktop-as-Launcher 约定。

#### Scenario: 点击 Regions 卡片
- **当** Admin 用户点击 Regions 卡片
- **则** 系统在新标签页打开 `/regions` 页面
- **且** Desktop 页面在原标签页保持打开

#### Scenario: 点击 Analyst Info 卡片
- **当** Admin 用户点击 Analyst Info 卡片
- **则** 系统在新标签页打开 `/analyst-info` 页面
- **且** Desktop 页面在原标签页保持打开

