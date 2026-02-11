## ADDED Requirements

### Requirement: 报告列表查询

系统 SHALL 根据用户角色显示相应的报告列表。

#### Scenario: Analyst 查看自己的报告列表
- **WHEN** Analyst 角色用户访问报告列表页面
- **THEN** 系统必须只显示该用户作为作者的报告
- **AND** 报告必须按 publish_date 降序排列
- **AND** 列表必须包含报告标题、报告类型、作者姓名、发布日期

#### Scenario: Admin 查看所有报告列表
- **WHEN** Admin 角色用户访问报告列表页面
- **THEN** 系统必须显示所有已发布的报告
- **AND** 报告必须按 publish_date 降序排列
- **AND** 列表必须包含报告标题、报告类型、作者姓名、发布日期

### Requirement: 报告列表分页

系统 SHALL 支持报告列表的分页查询。

#### Scenario: 分页加载报告
- **WHEN** 报告列表数据超过单页显示数量（默认 20 条）
- **THEN** 系统必须提供分页控件
- **AND** 用户可以切换到不同页码
- **AND** 每页显示的数据量必须符合设置

#### Scenario: 分页参数查询
- **WHEN** 前端调用 GET /api/v1/reports 接口
- **THEN** 系统必须支持 page 和 page_size 参数
- **AND** 系统必须返回分页元数据（total、page、page_size、total_pages）

### Requirement: 报告列表筛选

系统 SHALL 支持按多种条件筛选报告列表。

#### Scenario: 按报告类型筛选报告
- **WHEN** 用户选择特定的 Type（Company/Sector/Macro 等）进行筛选 默认是All
- **THEN** 系统必须只显示该报告类型相关的报告
- **AND** URL 必须包含 report_type 查询参数

#### Scenario: 按关键词搜索报告
- **WHEN** 用户在搜索框输入关键词
- **THEN** 系统必须在报告标题和摘要中搜索该关键词
- **AND** URL 必须包含 search 查询参数

### Requirement: 报告列表导航

系统 SHALL 提供从报告列表到报告详情的导航。

#### Scenario: 点击报告进入详情页
- **WHEN** 用户点击报告列表中的某条报告
- **THEN** 系统必须导航到该报告的详情页面
- **AND** URL 必须包含 report_id 参数

#### Scenario: URL 参数保持筛选状态
- **WHEN** 用户刷新报告列表页面
- **THEN** 系统必须保持当前的筛选条件
- **AND** URL 查询参数必须被解析并应用到列表查询
