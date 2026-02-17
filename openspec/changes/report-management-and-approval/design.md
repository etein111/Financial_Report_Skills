## Context

该 change 承接基础数据模块，建设系统核心流程：报告从创建到审批发布的完整生命周期。实现范围跨越页面、数据模型、文件存储、权限与状态机，是一个高耦合的跨模块变更，需要先统一状态与权限模型再进入编码。

## Goals / Non-Goals

**Goals:**
- 实现 Reports 与 Report Review 两个页面的职责分离。
- 实现报告状态机与可审计审批流程。
- 实现 report_version 追加式版本记录（基本信息 + Word/Excel）。
- 实现基于角色和归属关系的双层权限控制（应用层 + RLS）。

**Non-Goals:**
- 不建设外部查看站点（neoreport）及其对接接口。
- 不做多人实时协作冲突合并。
- 不支持在审批页面修改报告内容（仅审核决策）。

## Decisions

### 1) 设计基线
- 沿用 Next.js App Router + Supabase + Server Actions。
- 报告列表/详情由 Server Components 渲染，关键交互用 Client Components 局部承载。
- 所有写操作必须先做角色校验，再进入 repository。

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
- 应用层：
  - Analyst 仅可操作自己报告。
  - SA 可读全部并执行审批，不可创建/编辑。
  - Admin 全权限，含代建。
- 数据层（RLS）：
  - `report`/`report_version`/`report_analyst` 按角色 + 所属关系控制。
  - `report_version` 仅 INSERT + SELECT，禁止 UPDATE/DELETE。
- 文件安全：上传由服务端生成目标路径与文件名，避免覆盖和路径注入。

### 4) 页面交互
- Reports 页面：筛选（status/type/author）+ 列表 + 创建/编辑抽屉或弹窗 + 版本历史侧栏。
- Report Review 页面：仅展示 `submitted` 队列，支持查看详情、批准、拒绝（必填拒绝理由）。
- Report Review 页面：支持 Word 预览、Excel 下载、审核历史与统计看板；高亮等待时间较长条目。
- 统一反馈：状态变更后 toast + 列表局部刷新。

### 5) 技术实现方案
- `web/features/reports/repo/*.ts`：列表、详情、保存、提交、状态流转。
- `web/features/report-review/repo/*.ts`：审批队列、审批动作。
- `web/features/reports/actions.ts` 与 `web/features/report-review/actions.ts`：权限校验与命令编排。
- `web/domain/schemas/report*.ts`：表单与状态机参数校验。
- `supabase/migrations/*`：表结构、约束、RLS、索引、触发器（更新时间与版本号）。
- 代码质量要求：实现代码需通过 Prettier/ESLint（前端）与既有仓库检查规范。

### 6) 文件路径规范
- Word 文件：`reports/{report_id}/word/{version}/report.docx`
- Excel 模型：`reports/{report_id}/model/{version}/model.xlsx`

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
