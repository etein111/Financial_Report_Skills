# report_maker 与 template_maker 对接 neolyst 的改造设计

## 1. 总体概述

本次改造的目标，是把运行时模板来源和报告提交相关业务数据统一接到 `neolyst`。

`report_maker` 保持现有草稿解析、字段确认、模板渲染和输出 Word/PDF 的主流程不变。生成阶段所需的 Neolyst 数据读取统一通过 `neolyst` 接口完成。

模板的运行时来源不再是本地 `templates/` 目录，而是 `neolyst` 中保存的模板记录。机器处理并生成 Word/PDF 后，`report_maker` 调用 `save_draft_report` 将机器处理结果保存为第一个 draft 版本。人工确认前，Neolyst 中已经存在该 `report_id` 下可查看的 draft。

本地 `templates/` 目录仍可保留为模板制作阶段的工作目录，用于编辑、验证和预览模板；但模板一旦发布，运行时事实来源统一以 `neolyst` 为准。

## 2. template_maker 制作模板调整：废弃 router.yaml

`router.yaml` 不再作为运行时模板选择的事实来源，也不再参与最终的 `report_type -> 模板` 判定。

`template_maker` 在制作模板时，不再需要维护 `router.yaml` 这套路由逻辑。若 `router.yaml` 或其他本地辅助组织方式继续保留，它们只服务于模板制作阶段的人类维护体验，不再影响运行时行为。

多个 `report_type` 共用同一模板的关系，不再通过本地路由文件表达，而是通过 `neolyst` 中的模板发布关系表达。

## 3. template_maker 发布模板：由 neolyst 负责入库

制作模板和发布模板是两件事。

`template_maker` 的主职责仍然是制作、修改、验证和预览本地模板。因为它知道做好的模板文件放在哪里，所以可以直接调用 `neolyst` 的发布接口，把模板提交到库里。

发布动作不绑定 `template_maker`。用户也可以直接指定模板文件给 `neolyst`，由 `neolyst` 独立完成模板发布。

发布时，`template_maker` 或其他调用方负责提供 `report_type + language` 和本地源文件路径；`neolyst` 负责上传到 Storage，并调用 Supabase 侧模板发布接口完成幂等写入。

主模板发布上传实际的 Word 模板和 `schema.yaml`。共享模板发布只声明当前 `report_type` 复用另一个已发布 `report_type` 的模板，不重复上传文件。

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

若多个 `report_type` 共用同一模板，先用 `upsert_template` 发布主模板，再用 `reuse_template` 为其他 `report_type` 写入共享关系。例如先发布 `macro + en`，再声明 `quantitative + en` 复用 `macro`。

共享关系采用静态复制。若主模板后续重新上传并生成新路径，需要重新执行 `reuse_template`。

`reuse_template` 至少覆盖以下错误：

- 源模板未发布
- `language` 不一致
- `report_type` 复用自己

## 4. report_maker 获取模板：运行时只从 neolyst 解析

模板选择通过 `neolyst` 完成。`report_maker` 根据 `report_type` 和 `language` 调用 `resolve_template` 获取当前使用的模板资产，不再从本地 `templates/` 目录读取模板。

这里的 `language` 来自当前报告的 `report_language`。运行时使用的 Word 模板和对应 `schema.yaml` 都以 `neolyst` 中保存的模板记录为准。

若多个 `report_type` 共用同一模板，则这些 `report_type` 在运行时都会解析到同一套模板资产路径。

模板解析规则如下：

- `resolve_template` 以 `report_type + language` 解析目标模板，但最终应落到唯一的 `report_template.id = {report_type}_{language}` 记录；若数据库中出现重复组合，应直接报数据异常
- 若多个 `report_type` 共用同一模板资产，则这些 `report_type` 最终解析到同一组 `template_file_path` 与 `schema_file_path`
- `report_maker` 不再维护额外的“报告类型 -> 模板类型”映射表

## 5. 提交前数据准备：文件、字段与确认规则

本章只整理提交报告所需字段来源，不展开纯渲染字段。

总原则：默认不做人工确认，只有字段缺失、格式异常、或 `neolyst` 校验失败时，再向用户确认。`contact_person` 是例外，始终通过交互确认。字段完整性和提交条件的最终判断，统一以 `validate_draft` 的返回结果为准，不在这里单独维护一套静态必填矩阵。

`report_maker` 在机器处理完成后，需要将内部数据显式转换为 `neolyst` 所要求的扁平 draft 输入。`elements.yaml`、渲染上下文和输出目录结构不直接等价于 draft 输入，需要单独映射。

draft 输入分两层：

- 保存 draft 时的最小字段：`title`、`report_type`、`report_language`、`analysts`、`report_file`、`pdf_file`
- 提交前补齐字段：`contact_person`、`investment_thesis`，以及按研报类型要求的 `coverage_id`、`ticker`、`rating`、`target_price`、`region_code`、`sector_id`、`model_file`

### 5.0 本轮已确认规则

- `title` 在报告制作阶段就已经与用户确认；提交阶段不再重复确认，缺失视为前序流程出错
- `report_language` 由报告 `title` 直接判断，不再交互确认
- `analysts` 由 `elements.yaml` 中 `a1 ~ a8` 作者槽位组装，再用 `resolve_analyst_by_email` 校验和标准化
- `investment_thesis` 来自报告摘要，经 LLM 缩写为 150 字以内的概述，重点表达观点并突出新的变化
- `contact_person` 一律通过交互确认；交互时可以把 `1作 analyst_email` 作为默认选项
- `model_file` 不在 `elements.yaml` 中，而是随原始报告一起进入流程；到提交准备阶段若仍缺失，再向用户索要
- `region_code`、`sector_id` 只从 `elements.yaml` 取，不从正文抽取
- 公司类报告的 `coverage_id` 通过 `resolve_coverage` 获取；未命中时，提示用户去 Neolyst 中补建或修正 Coverage，再回到当前流程继续提交

### 5.1 通用提交字段

| 字段 | 适用范围 | 来源 | 说明 |
| --- | --- | --- | --- |
| `title` | 全部报告 | 报告制作阶段已与用户确认，并进入后续渲染输入 | 提交阶段不再重复确认；缺失视为前序流程出错 |
| `report_type` | 全部报告 | 流程输入，进入 `report_maker` 前已确定 | 作为提交字段写入 draft |
| `report_language` | 全部报告 | 由报告 `title` 直接判断 | 自动写入，不再交互确认 |
| `investment_thesis` | 全部报告 | 报告摘要，经 LLM 缩写生成 | 控制在 150 字以内，重点表达观点和新的变化 |

### 5.2 分析师与联系人字段

| 字段 | 适用范围 | 来源 | 说明 |
| --- | --- | --- | --- |
| `analysts` | 全部报告 | 由 `elements.yaml` 中 `a1 ~ a8` 作者槽位组装而来 | 用 `resolve_analyst_by_email(email)` 校验并标准化；`author_order` 按槽位顺序生成；最多支持 8 人 |
| `contact_person` | 全部报告 | 通过交互指定 | 交互时可以把 `1作 analyst_email` 作为默认选项；最终值必须属于 `analysts[].analyst_email` |

### 5.3 公司类与行业类业务字段

| 字段 | 适用范围 | 来源 | 说明 |
| --- | --- | --- | --- |
| `ticker` | 公司类报告 | `elements.yaml` | 自动带入 draft |
| `rating` | 公司类报告 | `elements.yaml` | 自动带入 draft |
| `target_price` | 公司类报告 | `elements.yaml` | 自动带入 draft |
| `coverage_id` | 公司类报告 | 通过 `resolve_coverage(ticker, 1作 analyst_email)` 获取 | 未命中时，提示用户去 Neolyst 中补建或修正 Coverage，再回到当前流程继续提交 |
| `region_code` | 行业类报告 | `elements.yaml` | 只从 `elements.yaml` 取，不从正文抽取 |
| `sector_id` | 行业类报告 | `elements.yaml` | 只从 `elements.yaml` 取，不从正文抽取 |

### 5.4 文件字段

| 字段 | 适用范围 | 来源 | 说明 |
| --- | --- | --- | --- |
| `report_file` | 全部报告 | `report_maker` 合成后的最终 Word 文件 | 写入 draft 的文件字段 |
| `pdf_file` | 全部报告 | `report_maker` 生成的最终 PDF 文件 | 写入 draft 的文件字段 |
| `model_file` | 公司类报告 | 与原始报告一起进入流程的 Excel 模型文件 | 不在 `elements.yaml` 中；到提交准备阶段若仍缺失，再向用户索要 |

## 6. 保存 draft：生成结果入库并在 neolyst 查看

`report_maker` 不再等待所有字段完全正确后才把结果写入 Neolyst。机器处理结果通过 `save_draft_report` 直接保存为 draft，人工可以直接在 Neolyst 中查看该版本、核对内容，并决定是否继续提交。

文件字段映射如下：

- draft 使用最终生成的 Word 文件路径作为 `report_file`
- draft 使用最终生成的 PDF 文件路径作为 `pdf_file`
- `model_file` 仅在公司类报告提交时提供

首次保存后，Neolyst 中已经存在该 `report_id` 下可查看的第一个 draft 版本。后续如需补字段、重新保存、重新校验或重新提交，都围绕同一个 `report_id` 进行。

## 7. 提交报告：提交前校验与最终提交

在人工确认提交前，Neolyst 或其他上层流程根据 `report_id` 和 `version_no` 调用 `validate_draft(report_id, version_no)`，对指定 draft 版本执行提交前校验。

对于公司类报告，提交前仍需要完成 `resolve_coverage`。若未命中，则提示用户去 Neolyst 中补建或修正 Coverage，随后回到当前流程继续提交。同时仍需要完成 `contact_person` 确认，以及其他提交必填字段补齐。只有该 draft 版本满足提交条件后，才允许进入 `submit_report`。

人工在 Neolyst 中查看并确认指定 draft 版本后，调用 `submit_report(report_id, version_no)` 将该版本提交为 `submitted`。

`report_maker` 的职责默认止于 draft 保存，不自动执行最终提交。

当 `save_draft_report`、`resolve_coverage`、`validate_draft` 或 `submit_report` 抛出具体错误时，`report_maker` 或人工流程负责根据错误内容继续补字段、重新确认或终止流程。

字段缺失、字段歧义、联系人确认和 `coverage` 信息不足等问题，由 `report_maker` 继续通过对话处理。多轮补充、重新保存 draft、重新校验和重新提交都围绕同一个 `report_id` 进行。

## 8. 后续迭代

当前回合已经确认的字段规则都已写入正文。后续如果要继续提高自动化，再单独扩展。

后续如果要继续清理文档，建议优先补齐以下内容：

- 各类报告在 `validate_draft` 之外是否还需要额外前置校验
- `target_price`、`region_code`、`sector_id` 等字段是否需要在提交前主动预检查
- `coverage` 补建链路后续是否继续集成到 skill 内
