## ADDED Requirements

### Requirement: 系统提供 Analyst 业务数据模型并与账号系统解耦
系统 SHALL 提供 Analyst 业务数据管理，且 MUST 与 Supabase Auth 用户账号管理解耦。

#### Scenario: 维护 Analyst 数据
- **WHEN** Admin 创建或更新 Analyst 信息
- **THEN** 系统 MUST 仅更新 `analyst` 业务数据
- **AND** 系统 MUST NOT 自动创建、删除或修改 Auth 用户账号

### Requirement: 系统提供 Analyst 信息 CRUD 能力并执行角色权限
系统 SHALL 对 Analyst 信息提供读写能力，遵循“认证可读，Admin 可写”。

#### Scenario: 认证用户读取 Analyst 信息
- **WHEN** 已认证用户访问 Analyst Info 数据（例如页面加载列表）
- **THEN** 系统 MUST 允许读取 Analyst 列表

#### Scenario: Admin 写入 Analyst 信息
- **WHEN** Admin 在 Analyst Info 页面执行新增、编辑或删除
- **THEN** 系统 MUST 允许操作

#### Scenario: 非 Admin 写入 Analyst 信息
- **WHEN** SA 或 Analyst 尝试写入 Analyst 信息
- **THEN** 系统 MUST 拒绝写操作并返回无权限提示（403 页面或等效处理）

### Requirement: Analyst 列表必须支持指定搜索与展示字段
系统 SHALL 按固定字段支持搜索与展示。

#### Scenario: 搜索字段
- **WHEN** 用户在 Analyst 列表执行搜索
- **THEN** 系统 MUST 支持 `full_name`、`chinese_name`、`email` 三个搜索字段

#### Scenario: 列表展示字段
- **WHEN** 用户查看 Analyst 列表
- **THEN** 列表 MUST 展示 `full_name`、`chinese_name`、`email`、`region`、`is_active`

### Requirement: 创建 Analyst 时必须校验必填与邮箱唯一性
系统 SHALL 在创建 Analyst 时验证必填字段与邮箱唯一性。

#### Scenario: 创建必填校验
- **WHEN** Admin 创建 Analyst 信息
- **THEN** `full_name`、`email`、`region` MUST 为必填

#### Scenario: 邮箱唯一性校验
- **WHEN** Admin 创建或更新 Analyst 且邮箱与现有记录重复
- **THEN** 系统 MUST 拒绝请求并返回唯一性冲突错误

### Requirement: Analyst 列表遵循统一分页排序规则
系统 SHALL 按统一规则返回 Analyst 列表数据。

#### Scenario: 查询 Analyst 列表
- **WHEN** 用户查询 Analyst 列表
- **THEN** 系统 MUST 按 `created_at DESC` 排序
- **AND** 当记录超过 15 条时 MUST 启用分页
- **AND** 每页条数 MUST 固定为 15

