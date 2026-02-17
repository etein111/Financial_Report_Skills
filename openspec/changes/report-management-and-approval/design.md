## Context

该 change 承接基础数据模块。`proposal.md` 已定义业务范围、全量权限矩阵、验收标准与特定约束；本文仅说明技术实现方案与关键权衡。

## Goals / Non-Goals

**Goals:**
- 在现有架构内实现 report 生命周期、审批流与版本追踪的数据与服务端链路。
- 通过数据库约束与事务策略保证状态流转、版本写入与权限一致性。

**Non-Goals:**
- 不建设外部查看站点（neoreport）及其对接接口。
- 不做多人实时协作冲突合并。
- 不支持在审批页面修改报告内容（仅审核决策）。

## Decisions

### 1) 设计基线
- 技术基线继承既有项目约定（详见 `docs/LOGIC.md`、`docs/UI.md` 与相关规范文档）。

备选方案：全部 client-side + RPC。  
未选原因：权限边界更难统一，且与现有项目范式不一致。

### 2) 数据模型
- `report`：主体信息 + 状态字段 + 审批字段 + 当前版本号。
- `report_version`：追加式历史记录，不允许 UPDATE/DELETE。
- `report_analyst`：报告与作者关系（lead/co-author）。
- 删除策略：报告默认逻辑删除（状态驱动），不做物理删除。

状态机约束：
- 允许：`draft -> submitted`、`submitted -> published`、`submitted -> rejected`。
- 可选：`rejected -> draft`（修改后重提），本阶段默认开启。
- `submitted` 状态允许归属 Analyst 继续编辑，编辑后保留 `submitted` 状态并追加新版本记录。
- 禁止：跨级跳转与回写（如 `published -> draft`）。

### 3) 权限与安全
- 应用层：权限规则按 proposal 的功能权限矩阵实现（Analyst 仅本人；SA 审批只读；Admin 全权限）。
- 数据层（RLS）：`report`/`report_version`/`report_analyst` 按 proposal 的表级权限矩阵落地。
- 文件安全：上传由服务端生成目标路径与文件名，避免覆盖和路径注入。

### 4) 技术实现方案
- `web/features/reports/repo/*.ts`：列表、详情、保存、提交、状态流转。
- `web/features/report-review/repo/*.ts`：审批队列、审批动作。
- `web/features/reports/actions.ts` 与 `web/features/report-review/actions.ts`：权限校验与命令编排。
- `web/domain/schemas/report*.ts`：表单与状态机参数校验。
- `supabase/migrations/*`：表结构、约束、RLS、索引、触发器（更新时间与版本号）。

### 5) 文件路径规范
- 采用 proposal 已定义的 reports 文件路径规范，不在 design 中重复展开。

## Risks / Trade-offs

- [状态机规则遗漏导致非法流转] → 在 DB 层增加约束/触发器，应用层再做前置校验。  
- [版本记录写入失败导致数据不一致] → 保存报告与写入版本放在同一事务。  
- [文件上传与版本号竞争] → 使用事务锁定当前版本号后再写入。  
- [RLS 规则复杂影响排障] → 提供策略测试脚本和最小复现查询。

## Migration Plan

1. 创建 report 相关表、索引、状态约束与触发器。  
2. 创建/更新 RLS policy，并执行策略验证脚本。  
3. 增加 reports/report-review 页面与 server actions。  
4. 打通文件上传路径策略并联调。  
5. 回滚策略：应用版本回滚 + 逆向迁移撤销新增对象（不删除已生成业务数据，先冻结入口）。

## Open Questions

- `rejected -> draft` 是否允许 SA 加备注后直接退回编辑？默认允许。  
- 审批是否需要“二次确认 + 审批意见模板”？默认先做基础文本理由。  
- 是否需要批量审批？默认不在本阶段实现。
