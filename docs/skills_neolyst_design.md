# skills_neolyst 设计文档

## 1. 定位与边界

`neolyst` 是 `neoskills` 中面向 Neolyst 的数据库操作 skill。它负责承接所有需要访问和操作 Neolyst 数据库的能力。`submit_report` 是当前优先落地的能力之一。

`report_maker` 负责生成报告产物、补齐业务所需信息，并组装出满足 `neolyst` 契约的输入。`neolyst` 负责拿到完整输入后执行查询、校验、文件上传、数据写入和提交相关操作。

`neolyst` 对上游暴露的是稳定的业务接口，而不是底层数据库操作集合。

`neolyst` 明确不负责以下事项：

- 与用户对话补字段
- 替上游做业务决策
- 对上游暴露零散的底层数据库动作

## 2. 设计决策

### 2.1 接口形态

- `neolyst` 对外暴露八个接口：`resolve_analyst_by_email`、`resolve_template`、`upsert_template`、`resolve_coverage`、`create_coverage`、`save_draft_report`、`validators` 与 `submit_report`。
- `resolve_analyst_by_email` 用于根据 analyst email 解析并确认 `analyst_id`。
- `resolve_template` 用于根据模板报告类型和模板语言查询当前使用的模板资产。
- `upsert_template` 用于新增或更新当前使用的模板资产。
- `resolve_coverage` 用于解析并确认 `coverage_id`。
- `create_coverage` 用于创建新的 `coverage` 与 `coverage_analyst` 关系。
- `save_draft_report` 用于保存机器处理后的 draft。
- `validators` 用于校验指定 `report_id + version_no` 的 draft 版本是否满足提交条件。
- `submit_report` 用于提交已有 draft。
- 不单独暴露 `upload file` 等更底层中间接口。

### 2.2 draft 与提交契约

- `save_draft_report` 的输入由 `neolyst` 定义并维护，`report_maker` 依赖该契约，而不是反过来。
- draft 输入采用全打平结构，业务字段和文件路径字段都位于顶层。
- draft 输入不携带执行上下文字段，例如 `workspace_root`、`trace_id`、`server_url_override`、`dry_run`。
- 文件输入统一使用本地路径，由 `neolyst` 自行上传到 Neolyst Storage。
- `save_draft_report` 的输入文件字段使用本地路径；保存成功后的 draft 版本和 `report_version` 记录使用上传后的 storage 路径。
- `report_id` 在首次保存 draft 时为空；机器处理后的 draft 和后续人工修订版都沿用同一个 `report_id` 追加新版本。
- draft 分为“可保存字段”和“提交前必补齐字段”两层契约。
- `company` / `company_flash` 在 draft 阶段允许暂时缺少 `coverage_id`；提交前必须补齐。
- `contact_person_id` 在 draft 阶段允许暂时缺少；提交前必须由 `report_maker` 负责确认和填充。
- `report_language` 作为模板选择字段，由 `report_maker` 自动识别并向用户确认后写入 draft。
- `certificate_confirmed` 固定写为 `true`。
- `save_draft_report` 成功时至少返回 `report_id` 和 `version_no`。
- `validators` 接收 `report_id` 和 `version_no`，针对指定 draft 版本执行提交前校验。
- `submit_report` 接收 `report_id` 和 `version_no`，针对指定 draft 版本执行提交。

### 2.3 report_type 与模板类型

- 模板接口使用 `template_report_type`，其取值沿用 `report_maker` 的源报告类型：`company`、`sector`、`flash`、`company_flash`、`sector_flash`、`macro`、`strategy`、`quantitative`、`bond`。
- draft 与提交接口使用 Neolyst `report_type`，其取值为：`company`、`sector`、`company_flash`、`sector_flash`、`common`。
- `report_maker` 在取模板时使用 `template_report_type`，在保存 draft 和提交时使用 Neolyst `report_type`。

### 2.4 身份与会话策略

- Neolyst Supabase 的登录身份由 `neolyst` 管理和复用，`save_draft_report`、`validators` 与 `submit_report` 的相关读写都使用该身份。
- 使用 `email + password` 登录，账号、密码和登录态保存在工作目录根目录的 `/.neolyst`；只支持一个登录身份，会话失效时重新登录并更新 `/.neolyst`。
- 提交相关的用户归属与审计字段统一使用 `connection` 当前登录的 Neolyst 用户；`resolve_analyst_by_email` 只用于确定报告分析师身份，不用于决定提交执行用户。
- 本 skill 不做代理执行，因为这会破坏 Neolyst 的安全性，也不符合实际业务关系。

### 2.5 技术访问方式

- 本 skill 直接使用 `@supabase/supabase-js` 与 Neolyst Supabase 交互，不使用 Supabase CLI 作为业务入口。
- 本 skill 的 TypeScript 脚本通过 `pnpm` 管理和执行。

### 2.6 Supabase URL

- Supabase URL 由 skill 负责确定；skill 内置默认 Supabase URL，`/.neolyst.server.url` 可作为覆盖项。

### 2.7 提交流程

- 报告生命周期采用 draft 驱动：机器处理后的结果先保存为 draft，人工确认后再执行提交。
- `save_draft_report` 用于保存 draft，不要求当前版本已经满足最终提交条件。
- `submit_report` 仅负责将已有 draft 推进到 `submitted`。
- 提交失败后的重新提交沿用原 `report_id`，在原 report 下创建新版本，不创建新的 report 对象。
- 整体行为对齐 Neolyst Web 的 `Analyst Submit`，不引入独立提交流程。

### 2.8 校验与错误语义

- 提交前校验由 `neolyst` 负责，`validators(report_id, version_no)` 用于校验指定 draft 版本是否满足提交条件。
- `resolve_coverage` 按 `ticker` 查询候选 `coverage`，再通过 `coverage_analyst` 判断报告 `1作 analyst_id` 是否属于该 `coverage` 的分析师列表；只要该 `1作` 出现在列表中，不要求其在 `coverage_analyst` 中也必须是 `role = 1`。
- `resolve_coverage` 命中唯一 `coverage` 时返回 `coverage_id`；命中多条或未命中时直接抛出具体错误。
- `create_coverage` 创建成功时返回新的 `coverage_id`；创建失败时直接抛出具体错误。
- `save_draft_report`、`validators` 和 `submit_report` 在失败时都直接抛出具体错误，不返回包裹态结果；错误信息必须足够明确，让上游 LLM 或人工据此补字段、重新确认，或中止流程。

## 3. 实现落地

### 3.1 resolve_coverage 执行流程

`resolve_coverage` 的输入为 `ticker` 和 `first_analyst_id`。执行时先按 `ticker` 查询候选 `coverage`，再关联 `coverage_analyst` 过滤出包含该 `first_analyst_id` 的记录。只要该分析师存在于某条 `coverage` 的分析师列表中，就视为命中，不要求该分析师在 `coverage_analyst` 中的 `role` 也等于 `1`。

若命中唯一 `coverage`，则返回该 `coverage_id`。若命中多条 `coverage`，则直接抛出具体错误，说明同一 `ticker` 下存在多条匹配记录，无法自动确定。若未命中任何 `coverage`，则直接抛出具体错误，表示需要进入 `create_coverage` 流程。

`resolve_coverage` 不修改数据库，不创建任何业务对象，只负责解析和确认 `coverage_id`。它的职责是为公司类报告提交提供稳定的 `coverage` 入口，而不是承担补数据或自动创建逻辑。

### 3.2 create_coverage 执行流程

`create_coverage` 的输入为创建 `coverage` 所需的完整业务字段，以及初始 `coverage_analyst` 列表。创建 `coverage` 时至少写入 `ticker`、公司名称、`sector_id`、`isin`、`country_of_domicile` 等必填字段；创建完成后，再写入对应的 `coverage_analyst` 关系。

`create_coverage` 创建的分析师列表以报告分析师列表为基础，其中报告 `1作 analyst_id` 必须包含在新建的 `coverage_analyst` 中。新建 `coverage` 时，初始 `coverage_analyst` 与本次报告分析师列表保持一致，最多支持 8 位分析师。创建完成后返回新的 `coverage_id`，供上游写回当前 draft 并继续后续校验和提交。

`create_coverage` 是显式创建接口，不由 `submit_report` 隐式触发。只有在 `resolve_coverage` 未命中现有 `coverage` 时，才进入 `create_coverage`。创建失败时直接抛出具体错误，不返回包裹态结果。

### 3.3 save_draft_report 执行流程

`save_draft_report` 接收扁平化的 draft 输入，用于保存机器处理后的 draft。示例如下：

```json
{
  "report_id": null,
  "report_type": "company",
  "title": "Vertiv: AI demand drives earnings growth",
  "coverage_id": "57ed4bf9-b4ac-485d-a3a5-5891f02d7c95",
  "ticker": "VRT US",
  "rating": "OUTPERFORM",
  "target_price": 140,
  "region_code": null,
  "sector_id": null,
  "report_language": "en",
  "contact_person_id": "58020af7-0844-471d-ad19-6b66a73178b6",
  "investment_thesis": "AI-driven demand and margin expansion support earnings growth.",
  "certificate_confirmed": true,
  "analysts": [
    {
      "analyst_id": "58020af7-0844-471d-ad19-6b66a73178b6",
      "role": 1,
      "sort_order": 1
    },
    {
      "analyst_id": "431bcf7b-3108-4d1d-9b32-62616f72f1c1",
      "role": 2,
      "sort_order": 2
    }
  ],
  "report_file": "/abs/path/report.docx",
  "pdf_file": "/abs/path/report.pdf",
  "model_file": "/abs/path/model.xlsx"
}
```

`save_draft_report` 在首次调用时创建新的 `report_id`，并保存机器处理后的第一个 draft 版本。保存过程中，本地文件路径会先上传到 storage，再写入 draft 版本记录。后续人工修订也沿用同一个 `report_id` 继续追加版本。

`save_draft_report` 成功时至少返回：

```json
{
  "report_id": "uuid",
  "version_no": 1,
  "status": "draft"
}
```

`save_draft_report` 不要求当前版本已经满足最终提交条件。它的职责是把不同阶段的报告结果保存到 Neolyst，使人工可以直接在 Neolyst 中查看和继续处理。

### 3.4 validators 执行流程

`validators` 接收 `report_id` 和 `version_no`，用于判断该 draft 版本是否满足进入 `submit_report` 的条件。

校验范围：

- 结构校验
- 必填字段校验
- 主数据校验
- 公司类报告校验
- 文件路径校验

结构校验：

- 指定的 draft 版本必须存在
- `analysts` 必须为非空列表
- `analysts` 最多支持 8 位分析师
- `analysts[].analyst_id`、`role`、`sort_order` 必须完整
- `analysts` 中必须恰好存在一位 `role = 1` 的分析师，作为报告 `1作 analyst_id`
- `analysts[].sort_order` 必须唯一
- draft 版本中的文件字段必须已经是有效的 storage 路径或已持久化文件引用

draft 可保存字段：

- `title`
- `report_type`
- `report_language`
- `analysts`
- `report_file`
- `pdf_file`

提交前必填字段：

- `title`
- `report_type`
- `report_language`
- `contact_person_id`
- `investment_thesis`
- `certificate_confirmed = true`
- `analysts`
- `report_file`
- `pdf_file`

按类型要求：

- `company`：`coverage_id`、`ticker`、`rating`、`target_price`、`model_file`
- `company_flash`：`coverage_id`、`ticker`
- `sector`：`region_code`、`sector_id`
- `sector_flash`：`region_code`、`sector_id`
- `common`：`region_code`

主数据校验：

- `report_type` 必须对应有效启用的 report type
- `report_language` 必须为有效模板语言
- `region_code` 必须对应有效 region
- `sector_id` 必须对应有效 sector
- `analysts[].analyst_id` 必须对应有效 analyst
- `contact_person_id` 必须属于 `analysts[].analyst_id`

公司类报告校验：

- `coverage_id` 必须对应存在的 `coverage`
- `coverage.ticker` 必须与输入 `ticker` 一致
- 报告 `1作 analyst_id` 必须存在于该 `coverage` 的 `coverage_analyst` 列表中
- 对已有 `coverage`，提交时不自动改写 `coverage_analyst`；报告分析师关系独立写入 `report_analyst`

结果语义：

- 校验通过：返回被校验通过的 `report_id` 和 `version_no`
- 校验失败：直接抛出具体错误，不返回包裹态结果

### 3.5 submit_report 执行流程

`submit_report` 接收 `report_id` 和 `version_no`，用于提交该 draft 版本。它要求对应 draft 在进入该接口前已经完成必要的 `resolve_coverage`、`create_coverage` 补充以及 `validators` 校验。

执行顺序：

1. 获取已认证的 Neolyst 访问连接
2. 定位 `report_id + version_no` 对应的 draft 版本
3. 再次执行提交前校验，确认该 draft 版本仍然满足提交条件
4. 执行提交动作，将报告状态推进到 `submitted`
5. 返回提交结果

提交结果至少包括：

- `report_id`
- `status`
- `version_no`

`submit_report` 不负责隐式创建 `coverage`，也不负责补字段或做人机交互。执行失败时直接抛出具体错误，不返回包裹态结果。

### 3.6 模块拆分

实现层按八个模块拆分：`connection`、`storage`、`analyst`、`template`、`coverage`、`draft-report`、`validators`、`submit-report`。

目录结构如下：

```text
neolyst/
  SKILL.md
  scripts/
    connection.ts
    storage.ts
    analyst.ts
    template.ts
    coverage.ts
    draft-report.ts
    validators.ts
    submit-report.ts
```

`SKILL.md` 负责声明 `resolve_analyst_by_email`、`resolve_template`、`upsert_template`、`resolve_coverage`、`create_coverage`、`save_draft_report`、`validators`、`submit_report` 八个对外接口，说明高层输入输出约定，以及 `/.neolyst` 的使用方式。具体实现细节放在 `scripts/*.ts`，不放在 `SKILL.md`。

`connection.ts` 负责连接相关能力，包括读取和写入 `/.neolyst`、创建 Supabase client、恢复 session、失效后重新登录，以及对外提供已认证的访问连接。

`storage.ts` 负责模板文件和报告文件的上传，以及统一的 storage 路径生成规则。

`analyst.ts` 负责 `resolve_analyst_by_email`。凡是 analyst 身份解析相关的查询都放在该模块内。

`template.ts` 负责 `resolve_template` 和 `upsert_template`。`upsert_template` 接收本地 Word 模板路径和本地 `schema.yaml` 路径，由 `neolyst` 负责上传到 storage 并写入模板记录；`resolve_template` 负责将运行时模板和对应的 `schema.yaml` 下载到本地可用路径并返回。

`coverage.ts` 负责 `resolve_coverage` 和 `create_coverage`。凡是与 `coverage`、`coverage_analyst` 相关的查询和写入都放在该模块内。

`draft-report.ts` 负责 `save_draft_report`。凡是 draft 版本创建、文件上传和版本追加都放在该模块内。

`validators.ts` 负责提交前校验。它根据 `report_id` 和 `version_no` 判断指定 draft 版本是否满足提交条件，不负责创建业务对象，也不执行提交。

`submit-report.ts` 负责提交已有 draft。它串联连接获取、draft 版本定位、提交前校验和状态推进动作。

模块之间的依赖关系保持单向：`draft-report` 可以调用 `connection`、`storage` 和 `coverage`；`submit-report` 可以调用 `connection` 和 `validators`；`validators` 可以调用 `analyst`、`coverage` 和 `connection`；`template` 可以调用 `connection` 和 `storage`；`coverage`、`analyst` 与 `storage` 只依赖 `connection`；`connection` 不依赖任何业务模块。

## 4. 联调与环境

### 4.1 联调测试环境

- URL：`http://47.57.213.88:80`
- Admin username：`admin@neolyst.com`
- Admin password：`Admin123`

## 5. report_maker 对接 neolyst 的改造要求

### 5.1 生成阶段从 neolyst 取模板与查询数据

`report_maker` 对接 `neolyst` 时，不改变现有草稿解析、字段确认、模板渲染和输出 Word/PDF 的主流程。Neolyst 的 draft 能力贯穿整个处理过程。

`report_maker` 在报告生成阶段也可以调用 `neolyst` 的查询能力。凡是生成报告所需的 Neolyst 数据读取，应通过 `neolyst` 提供的查询接口完成，不直接绕过 `neolyst` 访问数据库。

模板选择也通过 `neolyst` 完成。`report_maker` 根据 `template_report_type` 和 `report_language` 调用 `resolve_template` 获取当前使用的模板资产，不再从本地 `templates/` 目录读取模板，也不依赖本地目录映射决定最终模板。运行时使用的 Word 模板和对应 `schema.yaml` 都以 `neolyst` 中保存的模板记录为准。

机器处理并生成 Word/PDF 后，`report_maker` 调用 `save_draft_report` 将机器处理结果保存为第一个 draft 版本。进入人工确认前，Neolyst 中已经存在该 `report_id` 下可查看的 draft 版本。

### 5.2 新增提交字段确认能力

`report_maker` 负责补齐提交所需但不属于报告渲染本身的业务字段，并在必要时通过对话确认后写入提交数据。

`contact_person_id` 由 `report_maker` 负责确认和填充，规则如下：

- 单 analyst 场景，直接使用该 analyst 作为 `contact_person_id`
- 多 analyst 场景，通过对话确认后填入
- `contact_person_id` 必须属于本次报告的 `analysts` 列表

`report_maker` 需要能够明确得到以下提交所需的分析师信息：

- 报告分析师列表
- 每个分析师对应的 `analyst_id`
- 每个分析师在本次报告中的 `role`
- 每个分析师的 `sort_order`
- 报告 `1作 analyst_id`

`report_maker` 通过 `resolve_analyst_by_email(email)` 将现有分析师 email 映射为 `analyst_id`。分析师列表最多支持 8 人。新建 `coverage` 时，该列表用于初始化 `coverage_analyst`；对已有 `coverage`，只要求报告 `1作 analyst_id` 存在于 `coverage_analyst` 中。

`report_language` 由 `report_maker` 自动识别，并通过对话确认后写入。该字段用于确定提交所对应的模板语言。

`certificate_confirmed` 由 `report_maker` 直接写为 `true`。

对于公司类报告，`report_maker` 还负责准备以下 `coverage` 相关输入：

- `ticker`
- 报告 `1作 analyst_id`
- 新建 `coverage` 所需字段，包括公司名称、`sector_id`、`isin`、`country_of_domicile`

新建 `coverage` 时，`report_maker` 使用本次报告分析师列表初始化 `coverage_analyst`。对已有 `coverage`，`report_maker` 不通过提交流程改写其既有 `coverage_analyst`，报告作者关系独立进入 `report_analyst`。

### 5.3 新增 draft 组装能力

`report_maker` 在机器处理完成后，需要将内部数据显式转换为 `neolyst` 所要求的扁平 draft 输入。`elements.yaml`、渲染上下文和输出目录结构不直接等价于 draft 输入，需要单独映射。

draft 输入按两层组装：

- 保存 draft 时的最小字段：`title`、`report_type`、`report_language`、`analysts`、`report_file`、`pdf_file`
- 提交前补齐字段：`contact_person_id`、`investment_thesis`、`certificate_confirmed`，以及按报告类型要求的 `coverage_id`、`ticker`、`rating`、`target_price`、`region_code`、`sector_id`、`model_file`

draft 输入可包含以下字段：

- 报告基本字段：`title`、`report_id`、`report_type`、`report_language`、`investment_thesis`
- 分析师与联系人字段：`analysts`、`contact_person_id`
- 公司类报告字段：`coverage_id`、`ticker`、`rating`、`target_price`
- 行业类报告字段：`region_code`、`sector_id`
- 合规字段：`certificate_confirmed`
- 文件字段：`report_file`、`pdf_file`、`model_file`

文件字段映射规则如下：

- draft 使用最终生成的 Word 文件路径作为 `report_file`
- draft 使用最终生成的 PDF 文件路径作为 `pdf_file`
- `model_file` 仅在公司类报告提交时提供

`report_maker` 需要同时维护模板报告类型和 Neolyst 提交类型两套映射。

模板报告类型保持原始报告类型不变：

- `company -> company`
- `sector -> sector`
- `flash -> flash`
- `company_flash -> company_flash`
- `sector_flash -> sector_flash`
- `macro -> macro`
- `strategy -> strategy`
- `quantitative -> quantitative`
- `bond -> bond`

Neolyst 提交类型映射规则如下：

- `company -> company`
- `sector -> sector`
- `flash -> common`
- `company_flash -> company_flash`
- `sector_flash -> sector_flash`
- `macro -> common`
- `strategy -> common`
- `quantitative -> common`
- `bond -> common`

### 5.4 机器处理后的 draft 供人工在 neolyst 查看

`report_maker` 不再等待所有字段完全正确后才把结果写入 Neolyst。机器处理结果通过 `save_draft_report` 直接保存为 draft。

`save_draft_report` 成功后返回 `report_id` 和 `version_no`。这样人工可以直接在 Neolyst 中查看该版本的机器处理结果、核对内容，并决定是否继续提交。

### 5.5 新增提交前检查能力

在人工确认提交前，Neolyst 或其他上层流程根据 `report_id` 和 `version_no` 调用 `validators(report_id, version_no)` 对指定 draft 版本执行提交前校验。

对于公司类报告，提交前仍需要完成 `resolve_coverage`、必要时的 `create_coverage`、`contact_person_id` 确认以及其他提交必填字段补齐。只有被校验的 draft 版本满足提交条件后，才允许进入 `submit_report`。

### 5.6 人工确认后的报告提交

人工在 Neolyst 中查看并确认指定 draft 版本后，调用 `submit_report(report_id, version_no)` 将该版本提交为 `submitted`。

`report_maker` 的职责默认止于 draft 保存，不自动执行最终提交。最终提交动作以人工确认后的指定 draft 版本为准。

### 5.7 新增提交失败处理

当 `save_draft_report`、`resolve_coverage`、`create_coverage`、`validators` 或 `submit_report` 抛出具体错误时，`report_maker` 或人工流程负责根据错误内容继续补字段、重新确认或终止流程。

字段缺失、字段歧义、联系人确认和 `coverage` 创建信息不足等问题，由 `report_maker` 继续通过对话处理。多轮补充、重新保存 draft、重新校验和重新提交都围绕同一个 `report_id` 继续进行。

提交失败后的重新提交沿用原 `report_id`，在原 report 下创建新版本，不创建新的 report 对象。

## 6. template_maker 对接 neolyst 的改造要求

### 6.1 模板资产写入 neolyst

`template_maker` 不再将模板发布停留在本地 `templates/` 目录。模板创建或修改完成后，`template_maker` 调用 `upsert_template`，并将最终 Word 模板的本地路径和对应 `schema.yaml` 的本地路径交给 `neolyst`。由 `neolyst` 负责上传到 storage 并写入对应的模板记录。

`upsert_template` 的输入至少包括：

- `template_report_type`
- `report_language`
- `name`
- `template_file_path`
- `schema_file_path`

模板发布完成后，`neolyst` 中保存的模板记录成为 `report_maker` 后续取模板的唯一来源。模板记录同时保存 `template_file_path` 和 `schema_file_path`，二者共同构成一套完整模板资产。

`schema.yaml` 是模板的一部分，不是独立的附属文件。它定义当前模板需要抽取的字段，以及这些字段在分析师原始报告中的大致位置和特征，用于约束结构化抽取过程。

### 6.2 模板映射关系写入 neolyst

`template_maker` 负责维护报告类型与模板语言对应的模板关系。模板关系不再只保留在本地 `router.yaml` 或本地目录结构中，而是通过 `upsert_template` 直接写入 `neolyst`。

对于同一个 `template_report_type + report_language`，`template_maker` 维护对应的模板记录。后续 `report_maker` 调用 `resolve_template(template_report_type, report_language)` 时，直接使用这条记录返回的本地 Word 模板路径和本地 `schema.yaml` 路径。

### 6.3 本地模板目录的定位变化

本地 `templates/` 目录保留为模板制作阶段的工作目录，用于编辑、验证和预览模板。模板一旦发布，`report_maker` 不再直接读取该目录中的模板文件。

模板的运行时来源统一为 `neolyst.resolve_template` 返回的模板资产；本地目录不再作为运行时模板来源。
