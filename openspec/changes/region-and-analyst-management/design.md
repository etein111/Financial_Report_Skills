# Regions 与 Analyst Info 管理设计

## 1. 数据模型（以现有迁移为准）

- `region`：地区字典（name/code 唯一）
- `analyst`：业务分析师信息（email 唯一，`region_id` 外键，`ON DELETE SET NULL`）

迁移参考：
- `supabase/migrations/20260214094418_auth_and_user_management_baseline.sql`

系统预置 Region：
- China、Hong Kong、Japan、Taiwan、Korea、India、Macau、US

解耦原则：
- `analyst` 为业务信息表，创建/删除 Analyst 信息不自动创建/删除 Auth Users。
- Analyst 业务数据通过 email 与未来业务逻辑关联，不做外键强绑定到 Auth 用户。

## 2. 权限与安全（功能权限 + RLS 兜底）

功能权限（应用层）：
- Regions / Analyst Info 页面与写操作：Admin-only

数据权限（RLS，数据库层兜底）：
- `region`/`analyst`：认证可读
- 写操作：仅 Admin（以 JWT `app_metadata.role` 判定）

补充：
- 本阶段不做字段脱敏（例如 `analyst.email` 不做部分隐藏）。

## 3. 页面与路由

页面：
- `/regions`（Admin-only）
- `/analyst-info`（Admin-only）

导航：
- Desktop 增加两张卡片（Admin-only 显示），点击新标签页打开

## 4. 列表与分页（统一规则）

- 默认 `created_at DESC`
- 超过 15 条分页
- 每页固定 15 条

## 5. CRUD 交互建议（保持简单）

Regions：
- Create/Edit 用同一套表单（modal 或独立页二选一，建议 modal 以减少路由复杂度）
- Delete 必须二次确认
- 删除 Region 时不做关联阻断；若被 Analyst 引用，按数据库策略 `ON DELETE SET NULL` 自动置空关联。

Analyst Info：
- Create/Edit 表单字段：full_name、chinese_name、email、region、is_active
- 创建必填字段：`full_name`、`email`、`region`
- 列表支持按 `full_name`、`chinese_name`、`email` 搜索
- Delete 必须二次确认

失败提示：
- 唯一性冲突（name/code/email）必须能在 UI 上明确定位到字段或给出明确报错文案
