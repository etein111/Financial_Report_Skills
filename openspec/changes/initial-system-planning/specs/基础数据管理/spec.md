# 基础数据管理规格

## ADDED Requirements

### Requirement: Analyst 管理

系统管理员应该能够管理 Analyst(分析师)信息。

#### Scenario: 创建新的 Analyst

- **WHEN** 管理员输入 Analyst 信息并保存
- **THEN** 系统应该创建新的 Analyst 记录
- **AND** 如果邮箱已存在,应该提示重复并阻止创建
- **AND** 所有必填字段(Full Name, Email, Region)都必须填写

#### Scenario: 查看 Analyst 列表

- **WHEN** 管理员访问 Analyst 管理页面
- **THEN** 应该显示所有 Analyst 的列表
- **AND** 显示 Full Name, Chinese Name, Email, Region 等关键信息

#### Scenario: 编辑 Analyst 信息

- **WHEN** 管理员修改 Analyst 信息并保存
- **THEN** 系统应该更新 Analyst 记录
- **AND** 如果修改邮箱为已存在的邮箱,应该提示重复

### Requirement: Coverage 管理

系统管理员应该能够管理 Coverage(公司覆盖)信息。

#### Scenario: 创建新的 Coverage

- **WHEN** 管理员输入 Coverage 信息并保存
- **THEN** 系统应该创建新的 Coverage 记录
- **AND** ticker + analyst 组合必须唯一
- **AND** 必须关联一个有效的 Sector 和 Analyst
- **AND** 支持选择多个 Analyst(团队模式)

#### Scenario: 创建重复 Ticker 的 Coverage

- **WHEN** 管理员创建的 Coverage ticker 已被其他 Analyst 覆盖
- **THEN** 系统应该显示警告信息
- **AND** 警告信息应该显示已覆盖该 ticker 的 Analyst 信息
- **AND** 提示用户"该 ticker 已被 [Analyst Name] 覆盖,是否继续创建?"
- **AND** 用户必须明确确认才能继续创建
- **AND** 系统应该记录审批操作(当前操作人作为研究主管批准)

#### Scenario: 查看 Coverage 列表

- **WHEN** 管理员访问 Coverage 管理页面
- **THEN** 应该显示所有 Coverage 的列表
- **AND** 显示 ticker, English Full Name, Chinese Short Name, Sector, Analyst 等信息

#### Scenario: 编辑 Coverage 信息

- **WHEN** 管理员修改 Coverage 信息并保存
- **THEN** 系统应该更新 Coverage 记录
- **AND** 不能修改为已存在的 ticker + analyst 组合

### Requirement: Sector 管理

系统应该支持两级行业分类管理。

#### Scenario: 创建一级 Sector

- **WHEN** 管理员创建新的一级 Sector
- **THEN** 系统应该创建一级 Sector 记录
- **AND** 行业中文名和英文名必须填写

#### Scenario: 创建二级 Sector

- **WHEN** 管理员创建新的二级 Sector
- **THEN** 系统应该创建二级 Sector 记录
- **AND** 必须选择一个一级 Sector 作为父级
- **AND** 行业中文名和英文名必须填写

#### Scenario: 查看 Sector 树形结构

- **WHEN** 管理员访问 Sector 管理页面
- **THEN** 应该以树形结构显示所有 Sector
- **AND** 支持展开/收起查看二级 Sector
- **AND** 显示行业中文名、英文名、Wind 行业名

#### Scenario: 编辑 Sector 信息

- **WHEN** 管理员修改 Sector 信息并保存
- **THEN** 系统应该更新 Sector 记录

### Requirement: Region 管理

系统应该支持地区(国家)管理。

#### Scenario: 查看预设 Region

- **WHEN** 管理员访问 Region 管理页面
- **THEN** 应该显示所有预设 Region(China, Hong Kong, Japan, Taiwan, Korea, India, Macau, US)

#### Scenario: 添加自定义 Region

- **WHEN** 管理员添加新的 Region
- **THEN** 系统应该创建新的 Region 记录
- **AND** Region 名称不能与现有 Region 重复

### Requirement: Word 模板管理

系统应该能够管理不同类型报告的 Word 模板文件。

#### Scenario: 上传 Word 模板

- **WHEN** 管理员上传新的 Word 模板文件
- **THEN** 系统应该保存模板文件
- **AND** 必须指定模板对应的报告类型(Company, Sector, Flash 等)

#### Scenario: 查看模板列表

- **WHEN** 管理员访问模板管理页面
- **THEN** 应该显示所有模板的列表
- **AND** 显示模板名称、报告类型、上传时间等信息

#### Scenario: 下载模板

- **WHEN** 管理员点击下载模板
- **THEN** 系统应该下载对应的 Word 文件

#### Scenario: 更新模板

- **WHEN** 管理员重新上传模板文件
- **THEN** 系统应该替换原有模板文件
- **AND** 保留模板版本历史
