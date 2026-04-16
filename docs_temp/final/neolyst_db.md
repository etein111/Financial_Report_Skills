
## 数据库规范

### 表规范

- 主键：默认 `uuid`。
- 时间字段：`created_at` / `updated_at`，使用 `timestamptz`。
- 外键：显式声明 `ON DELETE` 语义（如 `set null` / `cascade` / `restrict`）。
- 唯一性：通过唯一约束或唯一索引在 DB 层保证。
- 日志表必须 append-only（例如报告状态历史）。
- 优先逻辑删除（is_active）或状态驱动，避免引用失效或外键问题。

### 规范

- RLS 是最终授权裁判。
- 角色判断统一来源于 JWT 角色字段。

### 命名规范

### 存储架构规范

- 模板文件与报告文件统一使用 Supabase Storage。
- 文件范文权限由rls控制。

### 迁移与演进原则(todo)

- 所有 Schema/RLS 变更必须走 `supabase/migrations/*.sql`。
- 字典表等初始化数据在`supabase/seed.sql`
- 测试数据由test测试脚本创建。位置在

## neolyst-db

### 存储路径规则(todo)

### 数据库模型

* 以neoskills/supabase/migrations/ 为准
