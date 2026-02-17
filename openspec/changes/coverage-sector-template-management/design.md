## Context

该 change 是 report 业务前置层，负责建设 Coverage、Sector（两级）和模板文件管理三类基础数据能力。当前系统已有认证、角色控制、Users/Region/Analyst Info 基础能力，可复用既有的 Server-first + Repository 架构；本次主要新增数据模型、页面交互与 RLS 扩展。

## Goals / Non-Goals

**Goals:**
- 提供可被后续 report 流程直接引用的 Coverage/Sector/Template 数据源。
- 建立 Sector 两级结构的严格数据约束与管理交互。
- 建立模板文件版本化能力，支持 Word/Excel 模板启用版本切换。
- 确保权限模型一致：功能层 Admin-only、数据层 RLS 兜底。
- 对齐 initial 要求：新增 Analyst 自动创建账号、创建用户支持是否邮件确认。

**Non-Goals:**
- 不实现 report 创建、编辑、提交、审批。
- 不实现模板内容在线编辑和 diff 对比。
- 不开放 SA/Analyst 对基础数据的写入权限。

## Decisions

### 1) 设计基线
- 继续使用 Next.js App Router + Supabase（DB/PostgREST/RLS/Storage）。
- 页面渲染使用 Server Components；写操作统一走 Server Actions。
- 采用 Repository 模式集中封装 SQL/查询逻辑。

备选方案：Route Handlers + client fetch。  
未选原因：与现有项目风格不一致，且会增加权限校验分散风险。

### 2) 数据模型
- `sector`：`id`,`level`,`parent_id`,`name_en`,`name_cn`,`wind_name`,`is_active`,`created_at`,`updated_at`。
- `coverage`：`id`,`ticker`,`english_full_name`,`chinese_short_name`,`traditional_chinese`,`sector_id`,`isin`,`reporting_currency`,`ads_conversion_factor`,`is_active`,`created_at`,`updated_at`。
- `coverage` 扩展字段：`country_of_domicile`,`is_duplicate`,`approved_by`,`approved_at`。
- `coverage_analyst`：`coverage_id`,`analyst_id`,`role`,`sort_order`，唯一约束 `(coverage_id, analyst_id)`。
- `template`：`id`,`name`,`report_type`,`file_type`,`file_path`,`version`,`is_active`,`created_at`,`updated_at`,`uploaded_by`。

关键约束：
- `sector.level=1` 时 `parent_id is null`；`level=2` 时 `parent_id` 必须引用 `level=1`。
- 同一 `(report_type, file_type, version)` 唯一。
- 同一 `(report_type, file_type)` 同时仅允许一个 `is_active=true`（部分唯一索引）。

### 3) 权限与安全
- 功能层：`requireAdmin()` 保护 `/coverage`、`/sectors`、`/templates` 页面及所有写操作。
- 数据层：三表 RLS 统一策略为“authenticated 可读，Admin 可写”。
- Storage：模板 bucket 写操作仅 Admin，读取允许 authenticated（按路径策略）。
- 上传流程：Server Action 生成路径并执行写入，避免客户端直接持有高权限凭据。
- 用户联动：新增 Analyst 时通过服务端 Admin API 在 `auth.users` 创建账号；“是否邮件确认”映射为邀请确认流程开关，仅 Admin 可操作。

### 4) 页面交互
- Coverage 页面：列表 + 搜索 + 分页 + 创建/编辑弹窗 + 删除确认。
- Sector 页面：按树形（一级下挂二级）展示，支持层级筛选与弹窗维护。
- Template 页面：按 `report_type + file_type` 分组展示当前启用版本与历史版本，支持上传新版本与启用切换。
- Desktop 导航：Admin 新增 3 个入口卡片，保持新标签页打开契约。

### 5) 技术实现方案
- `web/app/*/page.tsx` 负责鉴权与初始数据装配。
- `web/features/*/repo/*.ts` 负责查询与事务处理。
- `web/features/*/actions.ts` 负责写入命令、权限校验、错误映射。
- `web/domain/schemas/*.ts` 提供 zod 校验与表单类型。
- `supabase/migrations/*` 完成表结构、索引、RLS、Storage policy。
- `web/features/analyst-info/actions.ts` 与 `web/features/users/actions.ts` 增补联动逻辑与确认策略参数。
- 代码质量要求：实现代码需通过 Prettier/ESLint（前端）与既有仓库检查规范。

### 6) 存储路径规范
- 模板文件：
  - `templates/{template_id}/{version}/template.docx`
  - `templates/{template_id}/{version}/template.xlsx`
- 报告文件（由后续 report change 使用）：
  - `reports/{report_id}/word/{version}/report.docx`
  - `reports/{report_id}/model/{version}/model.xlsx`

## Risks / Trade-offs

- [Sector 层级约束复杂] → 用 DB CHECK + 触发器双重校验，并在 Server Action 做前置校验。  
- [模板版本并发上传冲突] → 通过事务内计算 `version=max+1` 与唯一约束兜底。  
- [Admin-only 影响业务协作速度] → 保持“读全员、写仅 Admin”，后续按流程再开放 SA 局部写权限。  
- [Storage 权限误配导致越权] → 先在测试环境执行白盒用例验证 read/write/delete 策略。

## Migration Plan

1. 新增迁移：创建/调整 `sector`、`coverage`、`coverage_analyst`、`template` 及索引约束。  
2. 新增迁移：配置 RLS policy 和模板 bucket policy。  
3. 部署应用代码与页面路由守卫。  
4. 回填最小种子数据（可选）：示例 sector、template。  
5. 回滚策略：回滚应用版本；DB 采用逆向迁移恢复新增对象。

## Open Questions

- 是否需要在本 change 就支持 template “软删除 + 恢复”？默认仅停用。  
- Coverage 的 `is_duplicate` 与审批字段是否本阶段纳入 UI？默认先不开放。  
- 模板下载是否需要记录审计日志（谁在何时下载）？默认下一阶段补充。
