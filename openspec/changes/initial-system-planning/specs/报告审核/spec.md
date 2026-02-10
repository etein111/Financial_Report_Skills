# 报告审核规格

## ADDED Requirements

### Requirement: 报告审核访问控制

只有 SA(合规人员)角色应该能够访问报告审核功能。

#### Scenario: SA 访问报告审核页面

- **WHEN** SA 登录系统
- **THEN** 应该显示"报告审核"功能卡片
- **AND** SA 可以点击进入报告审核页面

#### Scenario: Analyst 尝试访问报告审核

- **WHEN** Analyst 尝试访问报告审核页面
- **THEN** 系统应该拒绝访问
- **AND** 显示权限不足提示
- **AND** 返回桌面页面

#### Scenario: Admin 访问报告审核页面

- **WHEN** Admin 登录系统
- **THEN** 应该显示"报告审核"功能卡片
- **AND** Admin 可以访问报告审核页面(拥有 SA 的审核权限)

### Requirement: 审核队列查看

SA 应该能够查看所有待审核的报告。

#### Scenario: 查看待审核报告列表

- **WHEN** SA 访问报告审核页面
- **THEN** 应该显示所有状态为"已提交"(submitted)的报告
- **AND** 显示报告标题、类型、提交的 Analyst、提交时间等关键信息
- **AND** 按提交时间倒序排列(最新的在前)
- **AND** 高亮显示等待时间较长的报告(如超过24小时)

#### Scenario: 筛选审核队列

- **WHEN** SA 使用筛选功能
- **THEN** 应该支持按以下条件筛选:
  - 报告类型(Company/Sector/Flash/Common)
  - 提交的 Analyst
  - 提交时间范围
  - 报告语言(中文/英文)

#### Scenario: 搜索待审核报告

- **WHEN** SA 在搜索框输入关键词
- **THEN** 应该搜索报告标题
- **AND** 实时过滤显示匹配的报告

#### Scenario: 查看审核统计

- **WHEN** SA 访问报告审核页面
- **THEN** 应该显示审核统计信息:
  - 待审核报告数量
  - 今日已审核数量
  - 本周已审核数量
  - 平均审核时间

### Requirement: 报告详情查看

SA 应该能够完整查看待审核报告的所有信息。

#### Scenario: 打开待审核报告

- **WHEN** SA 点击某个待审核报告
- **THEN** 应该打开报告详情页面
- **AND** 显示完整的报告信息:
  - 基本信息(标题、类型、Analyst、投资论点等)
  - 关联的 Ticker/Sector/Region
  - Rating 和 Target Price(如有)
  - Word 文档预览或下载链接
  - Excel Model 文件下载链接(如有)
- **AND** 显示提交时间(submitted_at)
- **AND** 显示该 Analyst 的历史报告统计(可选)

#### Scenario: 预览 Word 文档

- **WHEN** SA 点击"预览 Word 文档"
- **THEN** 应该在页面内显示 Word 文档内容
- **AND** 支持滚动查看完整文档
- **AND** 提供下载文档的按钮

#### Scenario: 查看 Excel Model

- **WHEN** SA 点击"下载 Excel Model"
- **THEN** 应该下载 Excel 文件
- **AND** SA 可以在本地打开查看

#### Scenario: 查看 Analyst 历史报告

- **WHEN** SA 在报告详情页点击"查看该 Analyst 的历史报告"
- **THEN** 应该显示该 Analyst 的所有已发布报告
- **AND** 显示报告标题、发布时间、类型等
- **AND** 帮助 SA 了解该 Analyst 的报告质量和风格

### Requirement: 批准发布报告

SA 应该能够批准报告发布。

#### Scenario: 批准报告发布

- **WHEN** SA 查看完报告后点击"批准发布"按钮
- **THEN** 系统应该弹出确认对话框
- **AND** 对话框显示"确认批准该报告发布?"
- **AND** SA 确认后:
  - 报告状态从"已提交"变为"已发布"(published)
  - 记录 published_at 为当前时间
  - 记录 published_by 为当前 SA
  - 报告从审核队列移除
  - 报告出现在 Analyst 的已发布列表中
  - 报告可以被外部系统查询
- **AND** 系统应该通知 Analyst 报告已发布

#### Scenario: 验证发布条件

- **WHEN** SA 尝试批准报告
- **THEN** 系统应该验证:
  - 报告状态为"已提交"
  - 所有必填字段已填写
  - Word 文档已上传
- **AND** 如果验证失败，显示错误提示

#### Scenario: 批准后的通知

- **WHEN** SA 批准报告发布
- **THEN** 系统应该发送邮件通知给报告创建的 Analyst
- **AND** 邮件内容应该包括:
  - 报告标题
  - 批准时间
  - 批准人(SA)
  - 报告链接

### Requirement: 拒绝报告

SA 应该能够拒绝报告发布。

#### Scenario: 拒绝报告发布

- **WHEN** SA 点击"拒绝发布"按钮
- **THEN** 系统应该弹出对话框要求填写拒绝理由
- **AND** 对话框包含:
  - 拒绝理由输入框(必填)
  - 预设拒绝理由选项(可选，如: 内容不准确、格式问题、需要补充数据等)
  - 确认和取消按钮
- **AND** SA 填写拒绝理由并确认后:
  - 报告状态从"已提交"变为"已拒绝"(rejected)
  - 记录 rejected_at 为当前时间
  - 记录 rejected_by 为当前 SA
  - 记录拒绝理由
  - 报告从审核队列移除
  - 报告出现在 Analyst 的已拒绝列表中
- **AND** 系统应该通知 Analyst 报告被拒绝

#### Scenario: 拒绝理由必填

- **WHEN** SA 尝试拒绝报告但未填写拒绝理由
- **THEN** 系统应该阻止拒绝操作
- **AND** 显示提示"请填写拒绝理由"

#### Scenario: 拒绝后的通知

- **WHEN** SA 拒绝报告发布
- **THEN** 系统应该发送邮件通知给报告创建的 Analyst
- **AND** 邮件内容应该包括:
  - 报告标题
  - 拒绝时间
  - 拒绝人(SA)
  - 拒绝理由
  - 提示可以查看拒绝理由并重新编辑

### Requirement: 审核历史查看

SA 和 Analyst 应该能够查看报告的审核历史。

#### Scenario: 查看报告审核历史

- **WHEN** 用户在报告详情页点击"查看审核历史"
- **THEN** 应该显示该报告的所有审核记录:
  - 提交时间(submitted_at)和提交人(submitted_by)
  - 发布时间(published_at)和发布人(published_by)(如有)
  - 拒绝时间(rejected_at)和拒绝人(rejected_by)(如有)
  - 拒绝理由(如有)
- **AND** 按时间线形式显示

#### Scenario: Analyst 查看被拒绝原因

- **WHEN** Analyst 打开已拒绝状态的报告
- **THEN** 应该显示拒绝理由
- **AND** 显示拒绝人和拒绝时间
- **AND** 提供"重新编辑"按钮，将报告状态改回草稿

### Requirement: 批量审核操作

SA 应该能够批量审核报告(可选功能)。

#### Scenario: 批量批准报告

- **WHEN** SA 选中多个待审核报告并点击"批量批准"
- **THEN** 系统应该弹出确认对话框
- **AND** 对话框显示"确认批准这 N 份报告发布?"
- **AND** SA 确认后:
  - 批量更新报告状态为"已发布"
  - 记录每份报告的 published_at 和 published_by
  - 批量发送批准通知邮件
- **AND** 显示批量操作结果(成功数量)

#### Scenario: 批量拒绝报告

- **WHEN** SA 选中多个待审核报告并点击"批量拒绝"
- **THEN** 系统应该弹出对话框
- **AND** 对话框要求填写统一的拒绝理由
- **AND** SA 填写拒绝理由并确认后:
  - 批量更新报告状态为"已拒绝"
  - 记录每份报告的 rejected_at、rejected_by 和拒绝理由
  - 批量发送拒绝通知邮件
- **AND** 显示批量操作结果(成功数量)

### Requirement: 审核权限委托

SA 应该能够将审核权限委托给其他 SA(可选功能)。

#### Scenario: 委托审核权限

- **WHEN** SA 需要休假或暂无法审核
- **THEN** SA 可以设置"代理审核人"
- **AND** 指定另一位 SA 作为代理审核人
- **AND** 代理期间，待审核报告同时通知原审核人和代理审核人
- **AND** 两者都可以审核报告
- **AND** 代理期限到期后自动撤销代理权限
