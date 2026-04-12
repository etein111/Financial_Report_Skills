# neolyst Skill 全局设计文档

整体长期规则与跨接口共享规则。实现细节与接口契约见 [subsystem.md](./subsystem.md)。

## 1. 定位与边界

- `neolyst` 是封装 Neolyst数据库的业务接口，供其他skills调用。
- `neolyst` 不做对话补字段、业务决策或暴露底层数据库操作。
- `report_maker` 负责生成报告并组装输入，`neolyst` 负责执行查询、校验、文件上传、写入和提交。

## 2. 核心模型

### 2.1 报告生命周期

- 报告生命周期 draft 驱动：机器结果先存 draft，人工确认后提交。
- 契约主权：`save_draft_report` 的输入由 `neolyst` 定义并维护，`report_maker` 依赖该契约，而不是反过来。
- `report_id` 首次保存时为空，后续所有 draft 和人工修订沿用同一 `report_id` 追加版本。
- draft 契约分"可保存字段"和"提交前必填字段"两层。
- `analysts` / `coverage_analyst` / `report_analyst` 统一以 `analyst_email` 为业务键、`author_order` 为排序字段；不再引入 `analyst_id`、`role`、`sort_order`。
- `validate_draft` 与 `submit_report` 只以 `report_id` 为输入，作用于 `report.current_version_no` 指向的版本。
- 重新提交沿用原 `report_id` 创建新版本。
- 整体行为对齐 Neolyst Web 的 `Analyst Submit`，不引入独立提交流程。

### 2.2 研报类型与模板记录

- `report_type` 取值：`company`、`sector`、`company_flash`、`sector_flash`、`macro`、`strategy`、`quantitative`、`bond`。draft、提交和模板接口统一使用。
- 模板以 `report_type + language` 定位。数据库层只有 `report_template.id` 主键和 `(report_type, language)` 普通索引，无唯一约束；同一组合出现重复记录视为数据异常。
- `report_template.report_type` 即报告类型本身，不引入 `template_type`。
- 多个 `report_type` 可共用同一套模板资产：先上传主模板，再让其他 `report_type` 复用其 `template_file_path` 与 `schema_file_path`。
- `reuse_template` 是静态复制，不是动态引用；主模板路径变更后需重新执行 `reuse_template` 才能同步。

### 2.3 共享路径规则

- 模板资产存储在 `templates` bucket，报告版本资产存储在 `reports` bucket。
- 模板文件路径以 `report_template.template_file_path` 与 `report_template.schema_file_path` 为准，不由 `report_type` 公式推导。
- 报告文件 Storage 路径包含 bucket 前缀 `reports/`，bucket 内路径为 `{report_id}/v{version_no}/{原始文件名}`，版本间通过版本目录隔离。

## 3. 架构原则

### 3.1 业务逻辑落点

- 业务数据一致性、状态流转、关系维护、主表/版本表同步的逻辑，均优先在 Supabase 侧实现为稳定接口。
- 复杂读写（涉及路径规则、多表维护、跨表判断、校验+写入原子操作）默认在 Supabase 侧封装为 RPC，不在 skill 侧拼接多次底层表操作。
- `neolyst` skill 负责认证、文件上传、参数整理和调用 Supabase 接口，不重复实现核心业务一致性规则。
- 适合下沉的逻辑：模板发布与复用、模板解析、coverage 解析与创建、draft 保存、提交状态流转，以及 `report` / `report_version` / `report_analyst` 一致性维护。
- 不用外键，跨表一致性由 RPC 负责。
- 当前所有涉及多表一致性的写操作已在 Supabase 侧实现；仅提交前校验暂时保留在 skill 侧。

## 4. 权限与身份规则

### 4.1 身份与角色

- `neolyst` 使用自身维护的 Neolyst 账号操作数据库，所有操作以实际执行者身份为准。
- 报告归属和操作审计遵循"谁保存/提交，系统就记谁"；分析师身份仅用于报告署名，不影响审计记录。
- 不做代理执行：会破坏安全性且不符合实际业务关系。
- 系统按 `admin`、`sa`、`analyst` 三级角色控制访问权限，skill 设计必须兼容该模型。

### 4.2 访问控制

- 模板资产：所有用户可读，仅管理员可修改。
- 报告文件：管理员全权；分析师可操作自己的草稿和待审报告；销售可查看已提交及后续状态的报告。
- 分析师可查阅所有已发布报告，不受自己署名限制。

## 5. 错误语义

- 所有接口失败时直接抛出具体错误，不做静默吞错或模糊提示。
- 错误信息必须足够明确，让上游 LLM 或人工据此补字段、重新确认或中止流程。

