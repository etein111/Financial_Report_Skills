## Why

当前系统已具备用户、Region、Analyst Info 管理能力，但报告业务的关键基础数据（Coverage、Sector 两级分类、报告模板文件）尚未落地，导致后续报告创建与审核流程无法完整运行。需要先补齐这些基础数据模块，作为 report 管理与审批 change 的前置依赖。

## What Changes

## 一、目标与背景

### 1.1 目标
- 新增 Coverage（公司覆盖）管理，支持列表、创建、编辑、删除、搜索。
- 新增 Sector（行业分类）管理，支持一级/二级结构与层级校验。
- 新增报告模板文件管理，支持 Word/Excel 模板上传、版本化与启用状态控制。
- 调整 Analyst Info 与用户管理联动：新增 Analyst 时自动创建登录账号；创建用户时支持“是否邮件确认”开关。
- 为后续 report 管理 change 提供可复用的基础数据选择源（coverage、sector、template）。

### 1.2 范围边界
- 本 change 仅建设基础数据模块，不包含 report 创建/编辑/提交流程。
- 不做模板在线编辑，仅做文件上传与版本管理。
- 不引入 Edge Functions/Realtime，保持现有 Server Actions + Supabase 模式。

### 1.3 权限模型

#### 角色功能权限矩阵

| 功能模块 | 功能能力 | Admin | SA | Analyst |
|---------|---------|-------|----|---------|
| Analyst Info 管理 | 新增 Analyst（自动创建账号） | ✅ | ❌ | ❌ |
| Users 管理 | 创建用户时选择是否邮件确认 | ✅ | ❌ | ❌ |
| Coverage 管理 | 访问页面 | ✅ | ❌ | ❌ |
| Coverage 管理 | 列表/搜索 | ✅ | ❌ | ❌ |
| Coverage 管理 | 创建/编辑/删除 | ✅ | ❌ | ❌ |
| Sector 管理 | 访问页面 | ✅ | ❌ | ❌ |
| Sector 管理 | 列表/搜索 | ✅ | ❌ | ❌ |
| Sector 管理 | 创建/编辑/删除 | ✅ | ❌ | ❌ |
| Template 管理 | 访问页面 | ✅ | ❌ | ❌ |
| Template 管理 | 上传新版本 | ✅ | ❌ | ❌ |
| Template 管理 | 启用/停用版本 | ✅ | ❌ | ❌ |
| 报告业务引用基础数据 | 读取 Coverage/Sector/Template | ✅ | ✅ | ✅ |

#### 角色数据表权限矩阵（RLS）

| 数据表 | SELECT | INSERT | UPDATE | DELETE | 说明 |
|-------|--------|--------|--------|--------|------|
| `auth.users` | Admin（通过 Admin API） | 仅 Admin | 仅 Admin | 仅 Admin | 新增 Analyst 时自动创建登录账号 |
| `coverage` | 所有已认证用户 | 仅 Admin | 仅 Admin | 仅 Admin | 基础数据可读、写入仅 Admin |
| `coverage_analyst` | 所有已认证用户 | 仅 Admin | 仅 Admin | 仅 Admin | 维护 coverage 与 analyst 关系 |
| `sector` | 所有已认证用户 | 仅 Admin | 仅 Admin | 仅 Admin | 支持两级行业分类 |
| `template` | 所有已认证用户 | 仅 Admin | 仅 Admin | 仅 Admin | 模板元数据 |
| `storage.objects`（模板桶） | 所有已认证用户（受路径约束） | 仅 Admin | 仅 Admin | 仅 Admin | 模板文件上传/替换/删除 |

## 二、需求

### 2.1 Coverage 管理
- 列表字段：ticker、english_full_name、chinese_short_name、sector、reporting_currency、updated_at。
- 字段覆盖：`country_of_domicile`、`isin`、`ads_conversion_factor`、`is_duplicate`、`approved_by`、`approved_at`。
- 支持按 ticker/name/sector 搜索。
- 维护 coverage 与 analyst 的作者角色（lead/co-author）。
- 删除 coverage 前需二次确认。

### 2.2 Sector 管理（两级）
- 一级行业：不可设置 parent。
- 二级行业：必须绑定一级 parent。
- 禁止形成循环层级、禁止二级再挂二级。
- 列表支持按层级与关键词筛选。

### 2.3 报告模板文件管理（Word/Excel）
- 模板类型：`word`、`excel`。
- 模板分类：Company / Sector / Company Flash / Sector Flash / Common。
- 支持版本号递增管理，保留历史版本。
- 支持“当前启用版本”切换；同一 report_type + file_type 仅 1 个启用版本。

### 2.4 验收标准
- [ ] Admin 可访问三类管理页面，非 Admin 访问返回 `/403`。
- [ ] Coverage/Sector/Template 均可完成 CRUD（Template 的 D 为停用或删除元数据）。
- [ ] Sector 层级约束生效（无循环、二级必须有一级父节点）。
- [ ] 模板支持上传新版本并切换启用版本。
- [ ] RLS 生效：已认证用户可读，只有 Admin 可写。
- [ ] 新增 Analyst 时，系统自动创建对应登录账号。
- [ ] 创建用户时支持“是否邮件确认”：开启则发邀请确认邮件，关闭则可直接创建可登录账号。

## 三、设计约束与规范

- 遵循 `docs/LOGIC.md` 的分层：`app`/`features`/`domain`/`lib`。
- Server-first：列表页使用 Server Components，写操作走 Server Actions。
- Repository 模式封装数据访问，禁止页面层直接拼接 Supabase 查询。
- UI 复用现有表格、分页、确认弹窗组件；桌面入口按现有 `desktop-nav` 规范扩展。
- 临时脚本放 `supabase/scripts/` 或 `tests/scripts/`，不放 `web/`。

## Capabilities

### New Capabilities
- `coverage-management`: Coverage 信息与 coverage-analyst 关系管理。
- `sector-management`: 两级行业分类管理与层级约束。
- `template-file-management`: 报告模板（Word/Excel）上传、版本与启用状态管理。

### Modified Capabilities
- `desktop-nav`: 新增 Coverage/Sector/Template 管理入口（Admin-only）。
- `role-control`: 扩展这三个管理模块的功能权限判定与路由守卫。
- `analyst-info-management`: 新增 Analyst 时自动创建账号（由原解耦策略改为联动创建）。
- `user-management`: 创建用户支持“是否邮件确认”开关。

## Impact

- Affected code:
  - `web/app/coverage/*`, `web/app/sectors/*`, `web/app/templates/*`
  - `web/features/coverage/*`, `web/features/sectors/*`, `web/features/templates/*`
  - `web/domain/schemas/*`（新增 coverage/sector/template schema）
- Database:
  - 新增/完善 `coverage`、`coverage_analyst`、`sector`、`template` 表与约束
  - 增补 RLS policies 与索引
- Storage:
  - 新增模板存储 bucket/路径规范与权限策略
- Testing:
  - 新增 E2E：coverage/sectors/templates CRUD、权限、RLS、模板版本切换
