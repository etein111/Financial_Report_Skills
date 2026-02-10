# 报告管理规格

## ADDED Requirements

### Requirement: 报告权限控制

系统应该基于用户角色控制报告的访问和操作权限。

#### Scenario: Analyst 查看报告列表

- **WHEN** Analyst 登录系统访问报告列表
- **THEN** 应该只显示该 Analyst 创建的报告
- **AND** 不应该显示其他 Analyst 的报告
- **AND** 应该显示报告的当前状态(草稿/已提交/已发布/已拒绝)

#### Scenario: SA 查看报告列表

- **WHEN** SA 登录系统访问报告列表
- **THEN** 应该显示所有 Analyst 的报告
- **AND** 应该能够按 Analyst 筛选报告
- **AND** 应该显示报告的当前状态

#### Scenario: Admin 查看报告列表

- **WHEN** Admin 登录系统访问报告列表
- **THEN** 应该显示所有报告
- **AND** 应该能够按 Analyst 筛选报告
- **AND** 应该显示报告的当前状态

#### Scenario: 权限验证

- **WHEN** Analyst 尝试访问其他 Analyst 的报告
- **THEN** 系统应该拒绝访问并显示权限不足提示
- **AND** 返回报告列表页面

### Requirement: 报告创建

Analyst 和 Admin 应该能够创建新的研究报告，初始状态为"草稿"。

#### Scenario: Analyst 创建报告

- **WHEN** Analyst 创建新报告
- **THEN** 报告的 created_by 应该自动设置为当前 Analyst
- **AND** 报告的初始状态应该为"草稿"(draft)
- **AND** Analyst 不能修改 created_by 字段
- **AND** 所有必填字段必须填写

#### Scenario: Admin 替 Analyst 创建报告

- **WHEN** Admin 创建新报告时
- **THEN** 系统应该显示"创建给哪个 Analyst"的选择器
- **AND** Admin 必须从 Analyst 列表中选择一个 Analyst
- **AND** 报告的 created_by 应该设置为选中的 Analyst
- **AND** 报告的初始状态应该为"草稿"(draft)
- **AND** 所有必填字段必须填写

#### Scenario: 创建 Company 类型报告

- **WHEN** 用户选择 Company 类型并填写报告信息
- **THEN** 系统应该显示 Company 类型特有的字段(Ticker, Rating, Target Price)
- **AND** 所有必填字段必须填写
- **AND** Ticker 必须存在于 Coverage 中
- **AND** 支持选择多个 Analyst(团队模式)
- **AND** 必须上传 Word 文档和 Excel Model 文件

#### Scenario: 创建 Sector 类型报告

- **WHEN** 用户选择 Sector 类型并填写报告信息
- **THEN** 系统应该显示 Sector 类型特有的字段(Region, Sector)
- **AND** 所有必填字段必须填写
- **AND** Sector 必须从 Sector 列表中选择
- **AND** 必须上传 Word 文档

#### Scenario: 创建 Flash 类型报告

- **WHEN** 用户选择 Flash 类型(Company Flash 或 Sector Flash)
- **THEN** 系统应该根据子类型显示相应字段
- **AND** 所有必填字段必须填写
- **AND** 必须上传 Word 文档

#### Scenario: 创建 Common 类型报告

- **WHEN** 用户选择 Common 类型(Macro/Strategy/Quantitative/Bond)
- **THEN** 系统应该显示通用字段(Report Language, Report Title, Analyst, Investment Thesis)
- **AND** 所有必填字段必须填写
- **AND** 必须上传 Word 文档

### Requirement: 报告编辑

只有报告创建者(Analyst)和 Admin 能够编辑草稿状态的报告。

#### Scenario: Analyst 编辑自己的草稿报告

- **WHEN** Analyst 编辑自己创建的草稿状态报告
- **THEN** 系统应该允许修改
- **AND** 每次修改应该创建一个新的版本
- **AND** 记录修改人和修改时间

#### Scenario: Analyst 编辑已提交的报告

- **WHEN** Analyst 编辑已提交状态的报告
- **THEN** 系统应该允许修改
- **AND** 每次修改应该创建一个新的版本
- **AND** 记录修改人和修改时间
- **AND** 报告保持"已提交"状态，仍在审核队列中
- **AND** SA 看到的是最新版本

#### Scenario: Admin 编辑任何报告

- **WHEN** Admin 编辑任何报告
- **THEN** 系统应该允许修改
- **AND** 每次修改应该创建一个新的版本
- **AND** 记录修改人为 Admin

#### Scenario: SA 不能编辑报告

- **WHEN** SA 尝试编辑任何报告
- **THEN** 系统应该拒绝编辑
- **AND** 显示权限不足提示
- **AND** 数据库 RLS 策略阻止 SA 更新任何报告

#### Scenario: 修改报告基本信息

- **WHEN** 用户修改报告的任何基本信息字段
- **THEN** 系统应该创建一个新的版本
- **AND** 记录修改人和修改时间
- **AND** 保留所有历史版本

#### Scenario: 重新上传 Word 文档

- **WHEN** 用户重新上传报告的 Word 文档
- **THEN** 系统应该替换现有 Word 文档
- **AND** 创建一个新的版本
- **AND** 记录修改人和修改时间
- **AND** 保留所有历史版本

#### Scenario: 重新上传 Excel Model 文件

- **WHEN** 用户重新上传报告的 Excel Model 文件
- **THEN** 系统应该替换现有 Excel 文件
- **AND** 创建一个新的版本
- **AND** 记录修改人和修改时间
- **AND** 保留所有历史版本

### Requirement: 报告提交审核

Analyst 应该能够提交草稿报告给 SA 审核。

#### Scenario: Analyst 提交报告审核

- **WHEN** Analyst 点击"提交审核"按钮
- **THEN** 系统应该将报告状态从"草稿"更改为"已提交"(submitted)
- **AND** 记录提交时间(submitted_at)和提交人(submitted_by)
- **AND** 报告应该进入 SA 的审核队列
- **AND** Analyst 将无法再编辑该报告

#### Scenario: 验证提交条件

- **WHEN** Analyst 尝试提交报告审核
- **THEN** 系统应该验证所有必填字段已填写
- **AND** 验证 Word 文档和 Excel Model 文件(如需要)已上传
- **AND** 如果验证失败,应该阻止提交并提示缺少的信息

#### Scenario: 编辑已提交的报告

- **WHEN** 报告状态为"已提交"且 Analyst 修改了报告内容
- **THEN** 系统应该允许编辑
- **AND** 创建新的版本记录
- **AND** 报告保持"已提交"状态
- **AND** SA 在审核页面看到的是最新版本
- **AND** 通知 SA 该报告已更新（可选）

### Requirement: 报告列表查看

用户应该能够查看报告列表，根据角色显示不同的报告。

#### Scenario: Analyst 查看报告列表

- **WHEN** Analyst 访问报告管理页面
- **THEN** 应该只显示该 Analyst 创建的报告
- **AND** 显示报告标题、类型、状态、修改时间等关键信息
- **AND** 支持按报告状态筛选(草稿/已提交/已发布/已拒绝)
- **AND** 支持搜索报告标题
- **AND** 状态为"草稿"的报告显示"编辑"和"提交审核"按钮
- **AND** 状态为"已提交"的报告显示"编辑"和"等待审核"提示
- **AND** 状态为"已发布"的报告显示"查看"按钮
- **AND** 状态为"已拒绝"的报告显示"查看"和"重新编辑"按钮

#### Scenario: SA 查看报告列表

- **WHEN** SA 访问报告管理页面
- **THEN** 应该显示所有 Analyst 的报告
- **AND** 显示报告标题、类型、Analyst、状态等关键信息
- **AND** 支持按报告状态、Analyst 筛选
- **AND** 支持搜索报告标题
- **AND** 状态为"已提交"的报告高亮显示，提示需要审核
- **AND** 提供链接跳转到"报告审核"页面

#### Scenario: Admin 查看报告列表

- **WHEN** Admin 访问报告管理页面
- **THEN** 应该显示所有报告
- **AND** 显示报告标题、类型、Analyst、状态等关键信息
- **AND** 支持按报告状态、Analyst 筛选
- **AND** 支持搜索报告标题
- **AND** 提供完整的操作按钮(编辑、删除、查看)

### Requirement: 版本管理

系统应该保留报告的所有修改历史,支持合规检查。

#### Scenario: 查看报告版本历史

- **WHEN** 用户点击"查看版本历史"
- **THEN** 应该显示报告的所有版本列表
- **AND** 显示每个版本的修改时间、修改人
- **AND** 显示修改的内容类型(根据字段判断: basic_info_snapshot有值表示基本信息修改, word_file_path有值表示Word修改, model_file_path有值表示Model修改, 可同时显示多个)
- **AND** 只有有权限查看该报告的用户才能查看版本历史

#### Scenario: 查看特定版本的详细信息

- **WHEN** 用户选择某个历史版本
- **THEN** 应该显示该版本的完整信息
- **AND** 显示基本信息快照
- **AND** 提供该版本的 Word 和 Model 文件下载

#### Scenario: 对比两个版本

- **WHEN** 用户选择两个版本进行对比
- **THEN** 应该显示两个版本的差异
- **AND** 高亮显示修改的字段

### Requirement: 报告状态流转

报告应该支持完整的状态流转: 草稿 → 已提交 → (已发布/已拒绝)。

#### Scenario: 草稿 → 已提交

- **WHEN** Analyst 点击"提交审核"
- **THEN** 报告状态从"草稿"变为"已提交"
- **AND** 记录 submitted_at 和 submitted_by

#### Scenario: 已提交 → 已发布

- **WHEN** SA 在报告审核页面点击"批准发布"
- **THEN** 报告状态从"已提交"变为"已发布"
- **AND** 记录 published_at 和 published_by(为 SA)
- **AND** 报告在 Analyst 列表中显示为"已发布"
- **AND** 报告可以被外部系统查询

#### Scenario: 已提交 → 已拒绝

- **WHEN** SA 在报告审核页面点击"拒绝发布"
- **THEN** 报告状态从"已提交"变为"已拒绝"
- **AND** 记录 rejected_at 和 rejected_by(为 SA)
- **AND** 记录拒绝理由(可选)
- **AND** 报告在 Analyst 列表中显示为"已拒绝"
- **AND** Analyst 可以查看拒绝理由并重新编辑

#### Scenario: 已拒绝 → 草稿

- **WHEN** Analyst 在已拒绝报告上点击"重新编辑"
- **THEN** 报告状态从"已拒绝"变为"草稿"
- **AND** 清除 rejected_at、rejected_by 和 rejection_reason
- **AND** Analyst 可以重新编辑报告
- **AND** 编辑完成后需要再次点击"提交审核"来提交报告

### Requirement: 报告文件下载

系统应该支持下载报告文件。

#### Scenario: 下载当前版本文件

- **WHEN** 用户点击下载 Word 或 Model 文件
- **THEN** 系统应该下载最新版本的文件
- **AND** 只有有权限查看该报告的用户才能下载

#### Scenario: 下载历史版本文件

- **WHEN** 用户从版本历史中下载文件
- **THEN** 系统应该下载指定版本的文件
