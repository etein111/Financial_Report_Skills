## Why

在基础数据（Coverage/Sector/Template）可用后，系统需要进入核心业务阶段：report 的创建、编辑、版本管理与提审发布闭环。如果缺少该能力，前序数据模块无法形成业务价值，也无法支撑 SA 的审批职责。

## What Changes

## 一、目标与背景

### 1.1 目标
- 建设 Reports 管理页面：创建、编辑、查看、提交、版本历史。
- 建设 Report Review 审批页面：SA/Admin 审批通过或拒绝。
- 落地 report 状态机：`draft -> submitted -> published/rejected`。
- 落地文件版本记录：Word/Excel 文件与基本信息快照。

### 1.2 范围边界
- 本 change 不包含外部发布站点（neoreport）展示能力。
- 不做移动端专项适配，仅保证桌面与常规响应式可用。
- 不引入实时协作编辑（同一报告多人同时编辑冲突处理不做 Realtime）。

### 1.3 权限模型

#### 角色功能权限矩阵

| 功能模块 | 功能能力 | Admin | SA | Analyst |
|---------|---------|-------|----|---------|
| Reports | 访问列表 | ✅ | ✅ | ✅（仅本人） |
| Reports | 创建报告 | ✅（可代建） | ❌ | ✅（仅为自己） |
| Reports | 编辑 draft/submitted 报告 | ✅ | ❌ | ✅（仅本人） |
| Reports | 提交审核 | ✅ | ❌ | ✅（仅本人） |
| Reports | 查看版本历史 | ✅ | ✅ | ✅（仅本人） |
| Report Review | 访问审核工作台 | ✅ | ✅ | ❌ |
| Report Review | 审批通过/拒绝 | ✅ | ✅ | ❌ |

#### 角色数据表权限矩阵（RLS）

| 数据表 | SELECT | INSERT | UPDATE | DELETE | 说明 |
|-------|--------|--------|--------|--------|------|
| `report` | Admin/SA 全部；Analyst 仅本人 | Admin/Analyst | Admin；Analyst 仅本人 draft/submitted | 仅 Admin（可选） | 状态机主体 |
| `report_version` | Admin/SA 全部；Analyst 仅本人 | Admin/Analyst | ❌ | ❌ | 仅追加，不更新 |
| `report_analyst` | Admin/SA 全部；Analyst 仅本人关联 | Admin/Analyst | Admin/Analyst | Admin | 作者关系 |
| `storage.objects`（reports bucket） | 相关报告可见范围内可读 | Admin/Analyst | Admin/Analyst | Admin | Word/Excel 文件路径与权限 |

## 二、需求

### 2.1 Reports 管理
- 列表展示：title、report_type、status、lead_analyst、updated_at。
- 创建报告时可选择 Coverage/Sector、模板版本，上传 Word/Excel。
- `draft` 与 `submitted` 允许 Analyst 按归属继续编辑；`published`/`rejected` 禁止直接编辑。
- 提交后状态变为 `submitted`，记录 `submitted_by/submitted_at`。

### 2.2 版本管理
- 每次保存（基本信息或文件）创建 `report_version` 新记录。
- 版本记录包含：快照 JSON、word_file_path、model_file_path、changed_by、changed_at。
- 支持查看历史版本列表与变更元信息。

### 2.3 审批管理（Report Review）
- SA/Admin 查看所有 `submitted` 报告。
- 审批页支持查看报告完整信息（Word 预览、Excel 下载）。
- 审批通过：状态改为 `published`，记录 `published_by/published_at`。
- 审批拒绝：状态改为 `rejected`，必须填写 `rejection_reason`。
- 审批后保留完整审计链路。
- 展示审核历史与基础统计（待审数、当日处理数）；批量审核作为可选能力。

### 2.4 验收标准
- [ ] Analyst 可创建并提交自己的报告。
- [ ] Admin 可替 Analyst 创建报告并提交。
- [ ] SA 无法创建/编辑报告，但可审批 submitted 报告。
- [ ] report 状态机按规则流转，非法流转被阻断。
- [ ] 每次保存都会新增 report_version 记录。
- [ ] RLS 生效：Analyst 不能读取/修改他人报告。

## 三、设计约束与规范

- 严格遵循 `docs/LOGIC.md` 的分层与 Server-first 架构。
- 报告写操作统一走 Server Actions，不通过客户端直连高权限接口。
- 文件上传路径规范化，避免覆盖冲突（按 report_id/version 分层）。
- 审批动作必须具备可审计字段（人、时间、结果、理由）。
- 测试覆盖最小闭环：创建->编辑->提交->审批通过/拒绝。

## Capabilities

### New Capabilities
- `report-management`: 报告创建、编辑、提交、状态管理。
- `report-versioning`: 报告基本信息与 Word/Excel 文件版本追踪。
- `report-review`: SA/Admin 审批工作台与审批动作。

### Modified Capabilities
- `role-control`: 扩展 report 与 review 场景的角色判定和路由策略。
- `desktop-nav`: 新增 Reports / Report Review 导航入口与可见性规则。

## Impact

- Affected code:
  - `web/app/reports/*`, `web/app/report-review/*`
  - `web/features/reports/*`, `web/features/report-review/*`
  - `web/features/report-versions/*`（或并入 reports）
- Database:
  - `report`、`report_version`、`report_analyst` 表与状态流转约束
  - RLS policy（按角色 + 所属关系）
- Storage:
  - reports 文件 bucket 与路径策略（word/model）
- Integration:
  - 读取 Coverage/Sector/Template 作为 report 创建依赖
- Testing:
  - E2E 覆盖 report 生命周期与审批权限矩阵
