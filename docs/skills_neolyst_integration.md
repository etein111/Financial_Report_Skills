# report_maker 与 template_maker 对接 neolyst 的改造要求

## 1. report_maker 对接 neolyst 的改造要求

### 1.1 模板与查询

`report_maker` 保持现有草稿解析、字段确认、模板渲染和输出 Word/PDF 主流程不变。生成阶段所需的 Neolyst 数据读取统一通过 `neolyst` 接口完成。

模板选择也通过 `neolyst` 完成。`report_maker` 根据 `report_type` 和 `language` 调用 `resolve_template` 获取当前使用的模板资产，不再从本地 `templates/` 目录读取模板。这里的 `language` 来自当前报告的 `report_language`。运行时使用的 Word 模板和对应 `schema.yaml` 都以 `neolyst` 中保存的模板记录为准。若多个 `report_type` 共用同一模板，则这些 `report_type` 在运行时都会解析到同一套模板资产路径。

机器处理并生成 Word/PDF 后，`report_maker` 调用 `save_draft_report` 将机器处理结果保存为第一个 draft 版本。人工确认前，Neolyst 中已经存在该 `report_id` 下可查看的 draft。

### 1.2 提交字段确认

`report_maker` 负责补齐提交所需但不属于报告渲染本身的业务字段，并在必要时通过对话确认后写入 draft。

`contact_person` 由 `report_maker` 负责确认和填充，规则如下：

- 单 analyst 场景，使用该 analyst 的 email 作为 `contact_person`
- 多 analyst 场景，通过对话确认后填入
- `contact_person` 必须属于本次报告的 `analysts[].analyst_email`

`report_maker` 需要能够明确得到以下提交所需的分析师信息：

- 报告分析师列表
- 每个分析师对应的 `analyst_email`
- 每个分析师的 `author_order`
- 报告 `1作 analyst_email`

`report_maker` 通过 `resolve_analyst_by_email(email)` 校验输入 email 是否对应有效 analyst，并获取标准化后的 analyst 信息。分析师列表最多支持 8 人。新建 `coverage` 时，该列表用于初始化 `coverage_analyst`；对已有 `coverage`，只要求报告 `1作 analyst_email` 存在于 `coverage_analyst` 中。

`report_language` 由 `report_maker` 自动识别，并通过对话确认后写入。该字段用于确定提交所对应的模板语言。

对于公司类报告，`report_maker` 还负责准备以下 `coverage` 相关输入：

- `ticker`
- 报告 `1作 analyst_email`
- 新建 `coverage` 所需字段，包括 `english_name`、`sector_id`、`isin`、`country_of_domicile`
- 如已具备中文信息，同时准备 `chinese_name` 和 `traditional_chinese`

新建 `coverage` 时，`report_maker` 使用本次报告分析师列表初始化 `coverage_analyst`。对已有 `coverage`，`report_maker` 不通过提交流程改写其既有 `coverage_analyst`，报告作者关系独立进入 `report_analyst`。

当 `resolve_coverage` 未命中且需要进入 `create_coverage` 时，`report_maker` 先与用户对话确认"该 Coverage 已完成审批"，确认后才继续调用 `create_coverage`。

### 1.3 draft 组装

`report_maker` 在机器处理完成后，需要将内部数据显式转换为 `neolyst` 所要求的扁平 draft 输入。`elements.yaml`、渲染上下文和输出目录结构不直接等价于 draft 输入，需要单独映射。

draft 输入分两层：

- 保存 draft 时的最小字段：`title`、`report_type`、`report_language`、`analysts`、`report_file`、`pdf_file`
- 提交前补齐字段：`contact_person`、`investment_thesis`，以及按研报类型要求的 `coverage_id`、`ticker`、`rating`、`target_price`、`region_code`、`sector_id`、`model_file`

draft 输入可包含以下字段：

- 报告基本字段：`title`、`report_id`、`report_type`、`report_language`、`investment_thesis`
- 分析师与联系人字段：`analysts`、`contact_person`
- 公司类报告字段：`coverage_id`、`ticker`、`rating`、`target_price`
- 行业类报告字段：`region_code`、`sector_id`
- 文件字段：`report_file`、`pdf_file`、`model_file`

文件字段映射：

- draft 使用最终生成的 Word 文件路径作为 `report_file`
- draft 使用最终生成的 PDF 文件路径作为 `pdf_file`
- `model_file` 仅在公司类报告提交时提供

模板解析规则：

- `resolve_template` 以 `report_type + language` 解析目标模板，但最终应落到唯一的 `report_template.id = {report_type}_{language}` 记录；若数据库中出现重复组合，应直接报数据异常
- 若多个 `report_type` 共用同一模板资产，则这些 `report_type` 最终解析到同一组 `template_file_path` 与 `schema_file_path`
- `report_maker` 不再维护额外的"报告类型 -> 模板类型"映射表

### 1.4 draft 查看

`report_maker` 不再等待所有字段完全正确后才把结果写入 Neolyst。机器处理结果通过 `save_draft_report` 直接保存为 draft，人工可以直接在 Neolyst 中查看该版本、核对内容，并决定是否继续提交。

### 1.5 提交前校验

在人工确认提交前，Neolyst 或其他上层流程根据 `report_id` 和 `version_no` 调用 `validate_draft(report_id, version_no)` 对指定 draft 版本执行提交前校验。

对于公司类报告，提交前仍需要完成 `resolve_coverage`、必要时的 `create_coverage`、`contact_person` 确认以及其他提交必填字段补齐。只有该 draft 版本满足提交条件后，才允许进入 `submit_report`。

### 1.6 报告提交

人工在 Neolyst 中查看并确认指定 draft 版本后，调用 `submit_report(report_id, version_no)` 将该版本提交为 `submitted`。

`report_maker` 的职责默认止于 draft 保存，不自动执行最终提交。

### 1.7 失败处理

当 `save_draft_report`、`resolve_coverage`、`create_coverage`、`validate_draft` 或 `submit_report` 抛出具体错误时，`report_maker` 或人工流程负责根据错误内容继续补字段、重新确认或终止流程。

字段缺失、字段歧义、联系人确认和 `coverage` 创建信息不足等问题，由 `report_maker` 继续通过对话处理。多轮补充、重新保存 draft、重新校验和重新提交都围绕同一个 `report_id` 进行。

## 2. template_maker 对接 neolyst 的改造要求

### 2.1 模板资产写入 neolyst

`template_maker` 负责提供 `report_type + language` 和本地源文件路径；`neolyst` 负责上传到 Storage，并调用 Supabase 侧模板发布接口完成幂等写入。

主模板发布上传实际的 Word 模板和 `schema.yaml`。共享模板发布只声明"当前 `report_type` 复用另一个已发布 `report_type` 的模板"，不重复上传文件。

`upsert_template` 输入字段：

- `report_type`
- `language`
- `template_local_path`
- `schema_local_path`

`reuse_template` 输入字段：

- `report_type`
- `language`
- `same_as_report_type`

发布完成后，运行时模板来源统一为 `report_template` 表。记录中的 `template_file_path` 和 `schema_file_path` 共同定义一套模板资产。

`schema.yaml` 是模板资产的一部分，用于描述抽取字段和抽取约束。

### 2.2 共享模板关系写入 neolyst

模板关系通过 `upsert_template` 与 `reuse_template` 直接写入 `neolyst`，不再以本地 `router.yaml` 或目录结构作为运行时事实来源。

若多个 `report_type` 共用同一模板，先用 `upsert_template` 发布主模板，再用 `reuse_template` 为其他 `report_type` 写入共享关系。例如先发布 `macro + en`，再声明 `quantitative + en` 复用 `macro`。

共享关系采用静态复制。若主模板后续重新上传并生成新路径，需要重新执行 `reuse_template`。

`reuse_template` 至少覆盖以下错误：

- 源模板未发布
- `language` 不一致
- `report_type` 复用自己

### 2.3 本地模板目录的定位变化

本地 `templates/` 目录保留为模板制作阶段的工作目录，用于编辑、验证和预览模板。模板一旦发布，运行时来源统一为 `neolyst.resolve_template` 返回的模板资产，`report_maker` 不再直接读取该目录中的模板文件。

`router.yaml` 等本地辅助组织方式如果继续保留，也只服务于模板制作阶段的人类维护体验；它们不再是运行时模板选择的事实来源，也不参与 `report_type -> 模板` 的最终判定。
