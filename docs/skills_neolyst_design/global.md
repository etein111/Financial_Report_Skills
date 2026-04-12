# neolyst Skill 全局设计文档

整体长期规则与跨接口共享规则。实现细节与接口契约见 [subsystem.md](./subsystem.md)。

## 1. 定位与边界

`neolyst` 是 `neoskills` 中面向 Neolyst 的数据库操作 skill。它负责承接所有需要访问和操作 Neolyst 数据库的能力。

`report_maker` 负责生成报告产物、补齐业务所需信息，并组装出满足 `neolyst` 契约的输入。`neolyst` 负责拿到完整输入后执行查询、校验、文件上传、数据写入和提交相关操作。

`neolyst` 对上游暴露的是稳定的业务接口，而不是底层数据库操作集合。

`neolyst` 明确不负责以下事项：

- 与用户对话补字段
- 替上游做业务决策
- 对上游暴露零散的底层数据库动作

## 2. 设计决策

### 2.1 draft 与提交契约

- 契约主权：`save_draft_report` 的输入由 `neolyst` 定义并维护，`report_maker` 依赖该契约，而不是反过来。
- 模板文件位于模板 bucket，最终路径以 `report_template.template_file_path` 与 `report_template.schema_file_path` 为准，不由 `report_type` 公式推导。
- 报告文件位于报告 bucket，持久化字段中的 Storage 路径包含 bucket 前缀 `reports/`；bucket 内相对路径固定为 `{report_id}/v{version_no}/{原始文件名}`，文件名保留调用方传入的原始文件名，版本间通过版本目录隔离。
- `report_id` 在首次保存 draft 时为空；机器处理后的 draft 和后续人工修订版都沿用同一个 `report_id` 追加新版本。
- draft 契约分为"可保存字段"和"提交前必填字段"两层。
- `analysts` 列表与 `coverage_analyst` / `report_analyst` 统一以 `analyst_email` 作为业务键，排序字段统一使用 `author_order`；不再引入 `analyst_id`、`role`、`sort_order` 三套并存的表示。
- `validate_draft` 与 `submit_report` 都只以 `report_id` 为输入，实际作用版本由 `report.current_version_no` 决定。

### 2.2 研报类型与模板记录

- draft、提交和模板接口统一使用研报类型 `report_type`，其取值为：`company`、`sector`、`company_flash`、`sector_flash`、`macro`、`strategy`、`quantitative`、`bond`。
- 模板接口在业务语义上使用 `report_type + language` 做定位；当前数据库层只有 `report_template.id` 主键，以及 `(report_type, language)` 普通索引，没有这组字段的唯一约束。实现上应以 `{report_type}_{language}` 对应的 `report_template.id` 锁定目标记录；若出现同一 `report_type + language` 的重复记录，应视为数据异常。
- `report_template.report_type` 就是报告类型本身，不引入单独的 `template_type` 概念。
- 多个 `report_type` 可以共用同一套模板资产；发布时先上传一次主模板，再让其他 `report_type` 复用该主模板对应的 `template_file_path` 与 `schema_file_path`。
- `reuse_template` 的复用是静态复制当前路径，不是动态引用；若主模板后续重新上传并变更路径，需要重新执行一次 `reuse_template` 才能同步到复用方。

### 2.3 业务逻辑落点

- 凡涉及业务数据一致性、状态流转、关系维护、主表/版本表同步的逻辑，均优先在 Supabase 侧实现为稳定接口。
- 凡涉及复杂读操作或复杂写操作，均默认在 Supabase 侧封装为 RPC / 稳定接口，而不是在 skill 侧拼接多次底层表操作。这里的"复杂"包括但不限于：需要按固定规则确定模板或报告文件路径、需要同时维护多张表、需要做跨表一致性判断、需要把业务校验与写入合并为一个原子操作。
- `neolyst` skill 主要负责认证、文件上传、参数整理以及调用 Supabase 暴露的接口/函数，不在 skill 侧重复实现核心业务一致性规则。
- 适合下沉到 Supabase 侧的逻辑包括：模板发布与复用、模板解析、coverage 解析与创建、draft 保存、提交状态流转，以及 `report` / `report_version` / `report_analyst` 之间的一致性维护。
- 当前实现边界：`upsert_template` / `reuse_template` 由 Supabase 侧负责锁定目标模板记录并落库；`save_draft_report` 由 Supabase 侧负责在一次业务接口调用中同步维护 `report`、`report_version`、`report_analyst`；`submit_report` 继续通过 RPC 完成状态流转；`validate_draft` 暂时保留在 Python 侧，以 SELECT 查询完成提交前校验，不下沉为 RPC。

### 2.4 提交流程

- 报告生命周期采用 draft 驱动：机器处理后的结果先保存为 draft，人工确认后再执行提交。
- 提交失败后的重新提交沿用原 `report_id`，在原 report 下创建新版本。
- 整体行为对齐 Neolyst Web 的 `Analyst Submit`，不引入独立提交流程。

### 2.5 Supabase 侧实现原则

- 复杂读写默认走 Supabase 侧 RPC / 稳定接口。
- 原则上尽量不用外键，跨表一致性由 RPC 负责。

## 3. 后续待做

- Coverage 审批链路。当前设计在用户确认"该 Coverage 已完成审批"后允许 `create_coverage` 直接创建 Coverage；后续需要补上首次覆盖场景下的正式审批流程，并与 `resolve_coverage` / `create_coverage` 的调用时机重新收口。

## 4. 权限与身份规则

### 4.1 身份边界

- Neolyst Supabase 的登录身份由 `neolyst` 管理和复用。
- 报告所有者与执行审计均以当前登录身份为准。`owner_user_id`、`report_version.created_by`、`report_status_log.action_by` 等字段遵循"谁保存/提交，系统就记谁"；`resolve_analyst_by_email` 只用于确定报告分析师身份，不用于决定执行审计用户。
- 本 skill 不做代理执行，因为这会破坏 Neolyst 的安全性，也不符合实际业务关系。

### 4.2 角色模型

- 当前库的 RLS 通过 `current_app_role()` 读取 `auth.jwt().app_metadata.role`，按 `admin`、`sa`、`analyst` 做权限控制；skill 设计必须与该角色模型兼容。

### 4.3 Storage 权限

- Storage 使用两个独立 bucket：
  - 模板 bucket：`templates`，存放模板资产
  - 报告 bucket：`reports`，存放报告版本资产
- Storage RLS 策略：
  - `templates`：所有已认证用户可下载；仅 `admin` 角色可上传/更新/删除
  - `reports`：`admin` 可读写全部；`analyst` 可读写自己 `draft`/`submitted` 状态的报告文件；`sa` 可读 `submitted`/`published`/`rejected` 状态的报告文件

### 4.4 Coverage 历史查询权限

- 新增 RLS policy `report_select_published`，允许 `analyst` 角色读取所有 `status = 'published'` 的报告行，无需 SECURITY DEFINER。
