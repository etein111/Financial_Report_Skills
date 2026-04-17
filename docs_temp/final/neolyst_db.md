# Neolyst-DB 规范

## 数据库规范

### 表规范

- 主键：默认 `uuid`。
- 时间字段：`created_at` / `updated_at`，使用 `timestamptz`。
- 外键：显式声明 `ON DELETE` 语义（如 `set null` / `cascade` / `restrict`）。
- 唯一性：通过唯一约束或唯一索引在 DB 层保证。
- 日志表必须 append-only（例如报告状态历史）。
- 优先逻辑删除（is_active）或状态驱动，避免引用失效或外键问题。

### 授权规范

- RLS 是最终授权裁判。
- 角色判断统一来源于 JWT 角色字段。

### 命名规范

### 存储架构规范

- 模板文件与报告文件统一使用 Supabase Storage。
- 文件访问权限由RLS控制。

#### 模板文件

- 路径由 RPC 统一生成，客户端禁止硬编码。
- 多个 `report_type` 可复用同一路径，共用模板资产。
- 当前路径格式：`templates/{report_type}/{language}/template.docx` 和 `schema.yaml`。

#### 报告文件

- 上传路径由服务端 RPC 生成，客户端禁止硬编码。
- 仅 `draft` / `rejected` 状态的报告允许生成上传路径。
- 当前路径格式：`reports/{report_id}/{category}/{timestamp}/`（`category` 为 `report` 或 `model`）。

### 数据库工程

- Neolyst-DB 的唯一事实源是 `supabase/migrations/`。
- 迁移、测试、环境部署等工程规范统一遵循 [SUPABASE.md](../../principles/SUPABASE.md)。
