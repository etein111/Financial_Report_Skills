## Why

在系统框架与 Users 管理跑通之后，需要补齐基础数据管理能力（Regions、Analyst Info）与对应的权限控制，支撑后续业务（例如报告创建时选择 Region、按 Analyst 信息展示等）。

## Goals

- 实现 Regions 管理（Admin-only 页面与操作）：
  - 列表、创建、编辑、删除
  - 唯一性校验（name/code）
  - 系统预置 Region：China、Hong Kong、Japan、Taiwan、Korea、India、Macau、US
  - 删除 Region 时不做关联阻断；若被 Analyst 引用，按数据库策略 `ON DELETE SET NULL` 自动置空关联
- 实现 Analyst Info 管理（Admin-only 页面与操作）：
  - 列表、创建、编辑、删除
  - email 唯一性校验
  - 关联 Region（`region_id`，Region 删除后 `ON DELETE SET NULL`）
  - 列表展示字段：`full_name`、`chinese_name`、`email`、`region`、`is_active`
  - 创建必填字段：`full_name`、`email`、`region`
  - 支持按 `full_name`、`chinese_name`、`email` 搜索
- 权限控制：
  - 功能权限：只有 Admin 看得到入口、进得去页面、执行得了写操作
  - 数据权限：RLS 作为兜底（认证可读，Admin 可写）
- Desktop 增加两个入口卡片（Admin-only 展示）并遵循新标签页打开契约。

## 关键约束（从旧大 change 继承的基线）

- Analyst 信息与 Auth Users 解耦：创建/删除 Analyst 信息不自动创建/删除用户账号；Analyst 业务数据通过 email 与未来业务逻辑关联，不做外键强绑定到 Auth 用户。
- 本阶段不做字段脱敏（例如 `analyst.email` 不做部分隐藏）。
- 列表默认按 `created_at DESC`；超过 15 条分页；每页固定 15 条；不提供每页条数切换。

## Non-Goals

- 不扩展角色体系与 Users 管理（以 `auth-and-users-mvp` 为准）。
- 不引入 Edge Functions / Realtime / Storage。

## 依赖与前置

- 数据表与 RLS 迁移已存在：`supabase/migrations/20260214094418_auth_and_user_management_baseline.sql`
- 本 change 主要实现页面与交互，以及验证权限策略与 CRUD 流程
