## Context

该 change 是 report 业务前置层。`proposal.md` 已定义业务范围、权限矩阵、验收标准与实现约束；本文仅说明技术实现方案与关键权衡。

## Goals / Non-Goals

**Goals:**
- 在现有架构内实现 Coverage/Sector/Template 的可维护数据模型与服务端写入链路。
- 通过数据库约束与事务策略保证层级、版本和启用态一致性。
- 保证权限实现“应用层校验 + RLS 兜底”的双层一致。

**Non-Goals:**
- 不实现 report 创建、编辑、提交、审批。
- 不实现模板内容在线编辑和 diff 对比。
- 不开放 SA/Analyst 对基础数据的写入权限。

## Decisions

### 1) 设计基线
- 技术基线继承既有项目约定（详见 `docs/LOGIC.md`、`docs/UI.md` 与相关规范文档）。

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
- 功能层：`requireAdmin()` 保护 `/coverage`、`/sectors`、`/templates` 页面及所有写操作（规则与矩阵以 proposal 为准）。
- 数据层：RLS 按 proposal 的表级权限矩阵实现（authenticated 可读，Admin 可写）。
- Storage：模板 bucket 权限按 proposal 的存储与权限约束实现。
- 上传流程：Server Action 生成路径并执行写入，避免客户端直接持有高权限凭据。
- 用户策略：保持 Analyst Info 与 Auth Users 解耦；“是否邮件确认”映射为用户邀请确认流程开关，仅 Admin 可操作。

### 4) 技术实现方案
- `web/app/*/page.tsx` 负责鉴权与初始数据装配。
- `web/features/*/repo/*.ts` 负责查询与事务处理。
- `web/features/*/actions.ts` 负责写入命令、权限校验、错误映射。
- `web/domain/schemas/*.ts` 提供 zod 校验与表单类型。
- `supabase/migrations/*` 完成表结构、索引、RLS、Storage policy。
- `web/features/users/actions.ts` 增补“是否邮件确认”参数的服务端处理逻辑。

### 5) 存储路径规范
- 采用 proposal 已定义的模板与报告文件路径规范，不在 design 中重复展开。

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
