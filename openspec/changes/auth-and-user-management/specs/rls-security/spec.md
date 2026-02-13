## ADDED Requirements

### Requirement: 核心业务表必须启用 RLS
系统 SHALL 在 `region` 与 `analyst` 表启用 Row Level Security（RLS）。

#### Scenario: 表级安全启用
- **WHEN** 数据库迁移完成
- **THEN** `region` 与 `analyst` 表 MUST 处于 RLS 启用状态

### Requirement: 数据权限执行“认证可读，Admin 可写”
系统 SHALL 对 `region` 和 `analyst` 实施统一数据权限矩阵。

#### Scenario: 认证用户读取
- **WHEN** 任意已认证用户执行 `SELECT` 读取 `region` 或 `analyst`
- **THEN** RLS policy MUST 允许读取

#### Scenario: 非 Admin 写入
- **WHEN** SA 或 Analyst 执行 `INSERT`、`UPDATE`、`DELETE`
- **THEN** RLS policy MUST 拒绝写操作

#### Scenario: Admin 写入
- **WHEN** Admin 执行 `INSERT`、`UPDATE`、`DELETE`
- **THEN** RLS policy MUST 允许写操作

### Requirement: RLS 角色判断必须来源于 Supabase JWT
系统 SHALL 使用 `auth.jwt()->'app_metadata'->>'role'` 作为 RLS 角色判断依据。

#### Scenario: 执行写操作策略判断
- **WHEN** 数据库评估写操作 RLS policy
- **THEN** 系统 MUST 通过 JWT 中 `app_metadata.role` 判断是否为 `admin`

### Requirement: 数据库变更必须使用 Supabase 迁移机制管理
系统 SHALL 使用 Supabase CLI migration 进行数据库变更管理，不自建版本记录表。

#### Scenario: 增量执行迁移
- **WHEN** 执行数据库迁移发布
- **THEN** 系统 MUST 以 `supabase_migrations.schema_migrations` 作为增量执行依据
- **AND** 所有变更 SQL MUST 保存在 `supabase/migrations/*.sql`

#### Scenario: 紧急 Dashboard 变更
- **WHEN** 发生紧急线上变更并临时通过 Dashboard 执行
- **THEN** 团队 MUST 在当天补齐对应 migration 并提交到 Git
