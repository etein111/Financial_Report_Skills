## ADDED Requirements

### Requirement: 系统提供 Region 数据模型并保证名称与代码唯一
系统 SHALL 提供 `region` 数据模型，包含唯一的 `name` 与 `code` 字段。

#### Scenario: 创建或更新 Region
- **WHEN** Admin 创建或更新 Region
- **THEN** 系统 MUST 校验 `name` 和 `code` 的唯一性
- **AND** 重复值 MUST 被拒绝

### Requirement: 系统提供 Region CRUD 能力并执行角色权限
系统 SHALL 对 Region 提供读写能力，遵循“认证可读，Admin 可写”。

#### Scenario: 认证用户读取 Region
- **WHEN** 已认证用户访问 Region 数据（例如 Regions 页面需要加载列表）
- **THEN** 系统 MUST 允许读取 Region 列表

#### Scenario: Admin 写入 Region
- **WHEN** Admin 在 Regions 页面执行新增、编辑或删除
- **THEN** 系统 MUST 允许操作

#### Scenario: 非 Admin 写入 Region
- **WHEN** SA 或 Analyst 尝试写入 Region
- **THEN** 系统 MUST 拒绝写操作并返回无权限提示（403 页面或等效处理）

### Requirement: 系统预置 Region 基础数据
系统 SHALL 预置并维护固定 Region 基础数据集合。

#### Scenario: 初始化基础数据
- **WHEN** 系统完成数据库初始化
- **THEN** 系统 MUST 包含以下 Region：China、Hong Kong、Japan、Taiwan、Korea、India、Macau、US

### Requirement: 删除 Region 时自动解除 Analyst 关联
系统 SHALL 在删除 Region 时将关联 `analyst.region_id` 置为 `NULL`，不阻断删除流程。

#### Scenario: Region 存在 Analyst 引用
- **WHEN** Admin 删除已被 Analyst 引用的 Region
- **THEN** 系统 MUST 删除该 Region
- **AND** 关联 Analyst 的 `region_id` MUST 自动置为 `NULL`

### Requirement: Region 列表遵循统一分页排序规则
系统 SHALL 按统一规则返回 Region 列表数据。

#### Scenario: 查询 Region 列表
- **WHEN** 用户查询 Region 列表
- **THEN** 系统 MUST 按 `created_at DESC` 排序
- **AND** 当记录超过 15 条时 MUST 启用分页
- **AND** 每页条数 MUST 固定为 15

