## ADDED Requirements

### Requirement: 报告详情查询

系统 SHALL 显示报告的完整详细信息。

#### Scenario: 查看报告基本信息
- **WHEN** 用户访问报告详情页面
- **THEN** 系统必须显示报告标题、报告类型、报告作者（多个作者用,号分割）、Ticker(Company类型)、Rating(Company类型)、Target Price(Company类型)、Region(Sector类型)、Sector(Sector类型)、发布日期、报告摘要（富文本框）
- **AND** 系统必须显示报告的状态（已发布）

#### Scenario: 查看报告附件列表
- **WHEN** 用户访问报告详情页面
- **THEN** 系统必须显示该报告的所有附件文件
- **AND** 附件列表必须包含文件名、文件类型、文件大小
- **AND** 每个附件必须提供下载按钮

### Requirement: 报告附件下载

系统 SHALL 支持下载报告附件文件。

#### Scenario: 下载报告附件
- **WHEN** 用户点击附件的下载按钮
- **THEN** 系统必须发起文件下载请求
- **AND** 系统必须以原始文件名保存文件
- **AND** 下载进度必须可见

#### Scenario: 文件不存在时的处理
- **WHEN** 用户请求下载的文件在文件系统中不存在
- **THEN** 系统必须显示友好的错误提示
- **AND** 系统必须记录错误日志

### Requirement: 报告详情权限控制

系统 SHALL 根据用户角色控制报告详情的访问权限。

#### Scenario: Analyst 访问自己的报告详情
- **WHEN** Analyst 角色用户访问自己作为作者的报告详情
- **THEN** 系统必须正常显示报告详情
- **AND** 系统必须允许下载附件

#### Scenario: Analyst 访问他人的报告详情
- **WHEN** Analyst 角色用户尝试访问非自己作者的报告详情
- **THEN** 系统必须返回 403 Forbidden 错误
- **AND** 系统必须显示权限不足的提示

#### Scenario: Admin 访问任意报告详情
- **WHEN** Admin 角色用户访问任意报告详情
- **THEN** 系统必须正常显示报告详情
- **AND** 系统必须允许下载附件

### Requirement: 报告详情导航

系统 SHALL 提供报告详情页面的导航功能。

#### Scenario: 返回报告列表
- **WHEN** 用户点击"返回列表"按钮
- **THEN** 系统必须导航回报告列表页面
- **AND** 系统必须保持之前的筛选条件

#### Scenario: 报告不存在时的处理
- **WHEN** 用户访问不存在的报告 ID
- **THEN** 系统必须显示 404 页面
- **AND** 系统必须提供返回列表的链接
