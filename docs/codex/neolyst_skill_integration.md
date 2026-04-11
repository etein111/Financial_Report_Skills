# report_maker 与 template_maker 对接 neolyst 的改造

本文只描述两个相关 skill 为接入 `neolyst` 需要做的改造。`neolyst` 自身的接口、存储、校验与实现边界，另见 [neolyst_skill_design.md](/mnt/c/_code/neoskills/docs/codex/neolyst_skill_design.md)。

## 1. 总体要求

- 运行时与 Neolyst 相关的数据读取、模板解析、draft 保存和提交，统一通过 `neolyst` 暴露的业务接口完成
- 不再把本地目录结构、`router.yaml` 或零散数据库动作当作运行时事实来源
- 上游 skill 负责补齐业务输入、处理人与系统的交互；`neolyst` 负责持久化、校验和提交

本次对接依赖的 `neolyst` 接口如下：

- `resolve_analyst_by_email`
- `resolve_template`
- `upsert_template`
- `reuse_template`
- `resolve_coverage`
- `create_coverage`
- `save_draft_report`
- `validate_draft`
- `submit_report`

## 2. report_maker 的改造

### 2.1 模板与查询来源

`report_maker` 保持现有草稿解析、字段确认、模板渲染和输出 Word/PDF 的主流程不变，但生成阶段所需的 Neolyst 数据读取统一通过 `neolyst` 接口完成。

模板选择也改为通过 `neolyst.resolve_template(report_type, language)` 完成：

- `language` 来自当前报告的 `report_language`
- 运行时使用的 Word 模板和 `schema.yaml` 以 `report_template` 中保存的记录为准
- 若多个 `report_type` 共用同一模板，则这些 `report_type` 在运行时都会解析到同一套模板资产
- `report_maker` 不再直接从本地 `templates/` 目录读取运行时模板

### 2.2 提交字段确认职责

`report_maker` 负责补齐提交所需但不属于报告渲染本身的业务字段，并在必要时通过对话确认后写入 draft。

分析师相关要求：

- 需要明确得到报告分析师列表
- 每位分析师都需要有 `analyst_email`
- 每位分析师都需要有 `author_order`
- 必须能确定报告 `1作 analyst_email`
- 分析师列表最多支持 8 人

`report_maker` 通过 `resolve_analyst_by_email(email)` 校验输入 email 是否对应有效 analyst，并获取标准化后的 analyst 信息。

`contact_person` 的处理规则如下：

- 单 analyst 场景，使用该 analyst 的 email 作为 `contact_person`
- 多 analyst 场景，通过对话确认后填入
- `contact_person` 必须属于本次报告的 `analysts[].analyst_email`

`report_language` 由 `report_maker` 自动识别，并通过对话确认后写入。该字段同时用于确定提交所对应的模板语言。

### 2.3 coverage 相关输入准备

对于公司类报告，`report_maker` 负责准备以下 `coverage` 相关输入：

- `ticker`
- 报告 `1作 analyst_email`
- 新建 `coverage` 所需字段：`english_name`、`sector_id`、`isin`、`country_of_domicile`
- 如已具备中文信息，同时准备 `chinese_name` 和 `traditional_chinese`

处理规则如下：

- 新建 `coverage` 时，使用本次报告分析师列表初始化 `coverage_analyst`
- 对已有 `coverage`，不通过提交流程改写其既有 `coverage_analyst`
- 当 `resolve_coverage` 未命中且需要进入 `create_coverage` 时，先与用户确认“该 Coverage 已完成审批”，确认后才继续调用 `create_coverage`

### 2.4 draft 组装方式

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

文件字段映射规则：

- draft 使用最终生成的 Word 文件路径作为 `report_file`
- draft 使用最终生成的 PDF 文件路径作为 `pdf_file`
- `model_file` 仅在公司类报告提交时提供

### 2.5 draft 保存、查看、校验与提交

机器处理并生成 Word/PDF 后，`report_maker` 调用 `save_draft_report` 将机器处理结果保存为第一个 draft 版本。人工确认前，Neolyst 中已经存在该 `report_id` 下可查看的 draft。

流程改为：

1. 先保存 draft，不再等待所有字段完全正确
2. 人工在 Neolyst 中查看 draft
3. 提交前由上层流程调用 `validate_draft(report_id, version_no)` 做校验
4. 校验通过后，再调用 `submit_report(report_id, version_no)` 提交

`report_maker` 的职责默认止于 draft 保存，不自动执行最终提交。

### 2.6 失败处理

当 `save_draft_report`、`resolve_coverage`、`create_coverage`、`validate_draft` 或 `submit_report` 抛出具体错误时，`report_maker` 或人工流程负责根据错误内容继续补字段、重新确认或终止流程。

以下问题继续由 `report_maker` 通过对话处理：

- 字段缺失
- 字段歧义
- 联系人确认
- `coverage` 创建信息不足

多轮补充、重新保存 draft、重新校验和重新提交，都围绕同一个 `report_id` 进行。

## 3. template_maker 的改造

### 3.1 模板资产写入 neolyst

`template_maker` 负责提供 `report_type + language` 和本地源文件路径；`neolyst` 负责上传到 Storage，并调用 Supabase 侧模板发布接口完成幂等写入。

主模板发布上传实际的 Word 模板和 `schema.yaml`。共享模板发布只声明“当前 `report_type` 复用另一个已发布 `report_type` 的模板”，不重复上传文件。

对应输入如下：

- `upsert_template`：`report_type`、`language`、`template_local_path`、`schema_local_path`
- `reuse_template`：`report_type`、`language`、`same_as_report_type`

发布完成后，运行时模板来源统一为 `report_template` 表。记录中的 `template_file_path` 和 `schema_file_path` 共同定义一套模板资产。

### 3.2 共享模板关系写入方式

模板关系通过 `upsert_template` 与 `reuse_template` 直接写入 `neolyst`，不再以本地 `router.yaml` 或目录结构作为运行时事实来源。

共享模板的使用方式如下：

- 若多个 `report_type` 共用同一模板，先用 `upsert_template` 发布主模板
- 再用 `reuse_template` 为其他 `report_type` 写入共享关系
- 共享关系采用静态复制；若主模板后续重新上传并生成新路径，需要重新执行 `reuse_template`

`reuse_template` 至少要覆盖以下错误：

- 源模板未发布
- `language` 不一致
- `report_type` 复用自己

### 3.3 本地模板目录的定位变化

本地 `templates/` 目录保留为模板制作阶段的工作目录，用于编辑、验证和预览模板。

模板一旦发布，运行时来源统一为 `neolyst.resolve_template` 返回的模板资产，`report_maker` 不再直接读取该目录中的模板文件。

`router.yaml` 等本地辅助组织方式如果继续保留，也只服务于模板制作阶段的人类维护体验；它们不再是运行时模板选择的事实来源，也不参与 `report_type -> 模板` 的最终判定。
