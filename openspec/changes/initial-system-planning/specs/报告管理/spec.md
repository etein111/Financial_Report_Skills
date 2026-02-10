# 报告管理规格

## ADDED Requirements

### Requirement: 报告创建

系统管理员应该能够创建新的研究报告。

#### Scenario: 创建 Company 类型报告

- **WHEN** 管理员选择 Company 类型并填写报告信息
- **THEN** 系统应该显示 Company 类型特有的字段(Ticker, Rating, Target Price)
- **AND** 所有必填字段必须填写
- **AND** Ticker 必须存在于 Coverage 中
- **AND** Analyst 必须从 Analyst 列表中选择
- **AND** 支持选择多个 Analyst
- **AND** 必须上传 Word 文档和 Excel Model 文件

#### Scenario: 创建 Sector 类型报告

- **WHEN** 管理员选择 Sector 类型并填写报告信息
- **THEN** 系统应该显示 Sector 类型特有的字段(Region, Sector)
- **AND** 所有必填字段必须填写
- **AND** Sector 必须从 Sector 列表中选择
- **AND** Analyst 必须从 Analyst 列表中选择
- **AND** 必须上传 Word 文档

#### Scenario: 创建 Flash 类型报告

- **WHEN** 管理员选择 Flash 类型(Company Flash 或 Sector Flash)
- **THEN** 系统应该根据子类型显示相应字段
- **AND** 所有必填字段必须填写
- **AND** 必须上传 Word 文档

#### Scenario: 创建 Common 类型报告

- **WHEN** 管理员选择 Common 类型(Macro/Strategy/Quantitative/Bond)
- **THEN** 系统应该显示通用字段(Report Language, Report Title, Analyst, Investment Thesis)
- **AND** 所有必填字段必须填写
- **AND** 必须上传 Word 文档

### Requirement: 报告列表查看

系统管理员应该能够查看所有未发布的报告。

#### Scenario: 查看未发布报告列表

- **WHEN** 管理员访问报告管理页面
- **THEN** 应该显示所有状态为"未发布"的报告
- **AND** 显示报告标题、类型、创建时间、状态等关键信息
- **AND** 支持按报告类型、Analyst、创建时间等字段筛选
- **AND** 支持搜索报告标题

#### Scenario: 查看已发布报告列表

- **WHEN** 管理员切换到"已发布"视图
- **THEN** 应该显示所有状态为"已发布"的报告
- **AND** 显示发布时间信息

#### Scenario: 查看已拒绝报告列表

- **WHEN** 管理员切换到"已拒绝"视图
- **THEN** 应该显示所有状态为"已拒绝"(软删除)的报告

### Requirement: 报告编辑

系统管理员应该能够编辑报告的基本信息和文件。

#### Scenario: 修改报告基本信息

- **WHEN** 管理员修改报告的任何基本信息字段
- **THEN** 系统应该创建一个新的版本
- **AND** 记录修改人和修改时间
- **AND** 保留所有历史版本

#### Scenario: 重新上传 Word 文档

- **WHEN** 管理员重新上传报告的 Word 文档
- **THEN** 系统应该替换现有 Word 文档
- **AND** 创建一个新的版本
- **AND** 记录修改人和修改时间
- **AND** 保留所有历史版本

#### Scenario: 重新上传 Excel Model 文件

- **WHEN** 管理员重新上传报告的 Excel Model 文件
- **THEN** 系统应该替换现有 Excel 文件
- **AND** 创建一个新的版本
- **AND** 记录修改人和修改时间
- **AND** 保留所有历史版本

### Requirement: 版本管理

系统应该保留报告的所有修改历史,支持合规检查。

#### Scenario: 查看报告版本历史

- **WHEN** 管理员点击"查看版本历史"
- **THEN** 应该显示报告的所有版本列表
- **AND** 显示每个版本的修改时间、修改人
- **AND** 显示修改的内容类型(基本信息/Word/Model)

#### Scenario: 查看特定版本的详细信息

- **WHEN** 管理员选择某个历史版本
- **THEN** 应该显示该版本的完整信息
- **AND** 显示基本信息快照
- **AND** 提供该版本的 Word 和 Model 文件下载

#### Scenario: 对比两个版本

- **WHEN** 管理员选择两个版本进行对比
- **THEN** 应该显示两个版本的差异
- **AND** 高亮显示修改的字段

### Requirement: 报告发布

系统管理员应该能够发布报告。

#### Scenario: 发布报告

- **WHEN** 管理员点击"发布"按钮
- **THEN** 系统应该将报告状态更改为"已发布"
- **AND** 记录发布时间和发布人
- **AND** 报告从"未发布"列表移除

#### Scenario: 验证发布条件

- **WHEN** 管理员尝试发布报告
- **THEN** 系统应该验证所有必填字段已填写
- **AND** 验证 Word 文档和 Excel Model 文件(如需要)已上传
- **AND** 如果验证失败,应该阻止发布并提示缺少的信息

### Requirement: 报告拒绝

系统管理员应该能够拒绝(软删除)报告。

#### Scenario: 拒绝报告

- **WHEN** 管理员点击"拒绝"按钮
- **THEN** 系统应该将报告状态更改为"已拒绝"
- **AND** 记录拒绝时间和操作人
- **AND** 报告从当前列表移除

#### Scenario: 恢复已拒绝报告

- **WHEN** 管理员在"已拒绝"列表中点击"恢复"
- **THEN** 系统应该将报告状态恢复为"未发布"
- **AND** 报告重新出现在"未发布"列表中

### Requirement: 报告文件下载

系统应该支持下载报告文件。

#### Scenario: 下载当前版本文件

- **WHEN** 管理员点击下载 Word 或 Model 文件
- **THEN** 系统应该下载最新版本的文件

#### Scenario: 下载历史版本文件

- **WHEN** 管理员从版本历史中下载文件
- **THEN** 系统应该下载指定版本的文件
