# skills_neolyst 设计文档

## 1. 定位与边界

`neolyst` 是 `neoskills` 中面向 Neolyst 的数据库操作 skill。它负责承接所有需要访问和操作 Neolyst 数据库的能力。

`report_maker` 负责生成报告产物、补齐业务所需信息，并组装出满足 `neolyst` 契约的输入。`neolyst` 负责拿到完整输入后执行查询、校验、文件上传、数据写入和提交相关操作。

`neolyst` 对上游暴露的是稳定的业务接口，而不是底层数据库操作集合。

`neolyst` 明确不负责以下事项：

- 与用户对话补字段
- 替上游做业务决策
- 对上游暴露零散的底层数据库动作

## 2. 设计决策

### 2.1 接口形态

- `neolyst` 对外只暴露业务接口：`resolve_analyst_by_email`、`resolve_template`、`upsert_template`、`reuse_template`、`resolve_coverage`、`create_coverage`、`save_draft_report`、`validators`、`submit_report`。
- `resolve_analyst_by_email` 解析 `analyst_id`。
- `resolve_template` 解析模板资产。
- `upsert_template` 发布主模板。
- `reuse_template` 发布共享模板关系。
- `resolve_coverage`、`create_coverage` 负责 `coverage` 解析与创建。
- `save_draft_report` 保存 draft。
- `validators` 校验指定 draft 版本是否可提交。
- `submit_report` 提交指定 draft 版本。
- 不暴露 `upload_file` 之类的底层中间接口。

### 2.2 draft 与提交契约

- `save_draft_report` 的输入由 `neolyst` 定义并维护，`report_maker` 依赖该契约，而不是反过来。
- draft 输入采用全打平结构，业务字段和本地文件路径都位于顶层。
- draft 输入不携带执行上下文字段，例如 `workspace_root`、`trace_id`、`server_url_override`、`dry_run`。
- `save_draft_report` 的文件输入统一使用本地路径，由 `neolyst` 上传到 Storage。
- 模板文件位于模板 bucket，最终路径以 `template.template_file_path` 与 `template.schema_file_path` 为准，不由 `report_type` 公式推导。
- 报告文件位于报告 bucket，bucket 内路径固定为 `{report_id}/`，文件名遵循 `ARCHITECTURE_TECHNICAL.md` 中约定的统一命名规则。
- `report_id` 在首次保存 draft 时为空；机器处理后的 draft 和后续人工修订版都沿用同一个 `report_id` 追加新版本。
- draft 契约分为“可保存字段”和“提交前必填字段”两层。
- `company` / `company_flash` 在 draft 阶段允许暂时缺少 `coverage_id`，提交前必须补齐。
- `contact_person_id` 在 draft 阶段允许暂时缺少，提交前必须由 `report_maker` 负责确认和填充。
- `report_language` 作为模板选择字段，由 `report_maker` 自动识别并向用户确认后写入 draft。
- `certificate_confirmed` 固定写为 `true`。
- `save_draft_report` 输入中的 `report_file`、`pdf_file`、`model_file` 仅用于上传前定位本地文件；文件路径的唯一准源是 `report_version.word_file_path`、`report_version.pdf_file_path`、`report_version.model_file_path`。`snapshot_json` 如保留文件字段，只作为版本快照，不作为校验和提交的判定来源。
- `save_draft_report` 成功时至少返回 `report_id` 和 `version_no`。
- `validators` 与 `submit_report` 都以 `report_id + version_no` 为输入。

### 2.3 研报类型与模板记录

- draft、提交和模板接口统一使用研报类型 `report_type`，其取值为：`company`、`sector`、`company_flash`、`sector_flash`、`macro`、`strategy`、`quantitative`、`bond`。
- 模板接口以 `report_type + language` 作为业务定位键。`resolve_template` 以这组字段解析模板资产；`upsert_template` 与 `reuse_template` 的幂等写入、一致性约束和目标记录确定由 Supabase 侧模板接口负责保证。
- `template.report_type` 就是报告类型本身，不引入单独的 `template_type` 概念。
- 多个 `report_type` 可以共用同一套模板资产；发布时先上传一次主模板，再让其他 `report_type` 复用该主模板对应的 `template_file_path` 与 `schema_file_path`。
- `reuse_template` 的复用是静态复制当前路径，不是动态引用；若主模板后续重新上传并变更路径，需要重新执行一次 `reuse_template` 才能同步到复用方。

### 2.4 身份与会话策略

- Neolyst Supabase 的登录身份由 `neolyst` 管理和复用，`save_draft_report`、`validators` 与 `submit_report` 的相关读写都使用该身份。
- 使用 `email + password` 登录，账号、密码和登录态保存在脚本执行时 `cwd` 根目录的 `/.neolyst`；只支持一个登录身份，会话失效时重新登录并更新 `/.neolyst`。
- `/.neolyst` 为 JSON 文件，格式如下：`{ "email": "...", "password": "...", "access_token": "...", "refresh_token": "...", "expires_at": 1712345678 }`。`connection.py` 启动时先用 `access_token` + `refresh_token` 恢复 session，若已过期则用 `email + password` 重新登录并回写该文件。
- 报告所有者与执行审计均以当前登录身份为准。`owner_user_id`、`changed_by`、`action_by` 等字段遵循“谁保存/提交，系统就记谁”；`resolve_analyst_by_email` 只用于确定报告分析师身份，不用于决定执行审计用户。
- 本 skill 不做代理执行，因为这会破坏 Neolyst 的安全性，也不符合实际业务关系。

### 2.5 业务逻辑落点

- 凡涉及业务数据一致性、状态流转、关系维护、主表/版本表同步的逻辑，均优先在 Supabase 侧实现为稳定接口。
- `neolyst` skill 主要负责认证、文件上传、参数整理以及调用 Supabase 暴露的接口/函数，不在 skill 侧重复实现核心业务一致性规则。
- 适合下沉到 Supabase 侧的逻辑包括：模板发布与复用、coverage 解析与创建、draft 保存、提交前校验、提交状态流转，以及 `report` / `report_version` / `report_analyst` 之间的一致性维护。

### 2.6 技术访问方式

- 本 skill 使用 Python `supabase-py` 与 Neolyst Supabase 交互，并通过 `uv` 管理依赖与执行环境。
- 数据库结构真相仍以 `docs/neolyst_supabase_schema.sql` 为准。
- Storage 使用两个独立 bucket：模板 bucket 与报告 bucket。
- 模板 bucket 仅承载模板资产，路径以 `template_file_path` / `schema_file_path` 为准；报告 bucket 仅承载报告版本资产，bucket 内路径规则为 `{report_id}/...`。

### 2.7 Supabase URL

- Supabase URL 由 skill 负责确定；skill 内置默认 Supabase URL，`/.neolyst.server.url` 可作为覆盖项。

### 2.8 提交流程

- 报告生命周期采用 draft 驱动：机器处理后的结果先保存为 draft，人工确认后再执行提交。
- `save_draft_report` 用于保存 draft，不要求当前版本已经满足最终提交条件。
- `submit_report` 仅负责将已有 draft 推进到 `submitted`。
- 提交失败后的重新提交沿用原 `report_id`，在原 report 下创建新版本。
- 整体行为对齐 Neolyst Web 的 `Analyst Submit`，不引入独立提交流程。

### 2.9 校验与错误语义

- 提交前校验由 `neolyst` 负责，`validators(report_id, version_no)` 用于校验指定 draft 版本是否满足提交条件。
- `reuse_template(report_type, language, same_as_report_type)` 约束如下：
  - 源模板记录必须存在
  - 复用只能发生在同一 `language` 内
  - `report_type` 不能与 `same_as_report_type` 相同
- `reuse_template` 失败时直接抛出具体错误，至少覆盖：源模板不存在、语言不一致、试图复用自己。
- `resolve_coverage` 按 `ticker` 查询候选 `coverage`，再通过 `coverage_analyst` 判断报告 `1作 analyst_id` 是否属于该 `coverage` 的分析师列表；只要求该分析师出现在列表中，不要求其在 `coverage_analyst` 中也为 `role = 1`。
- `resolve_coverage` 命中唯一 `coverage` 时返回 `coverage_id`；命中多条或未命中时直接抛出具体错误。
- `create_coverage` 创建成功时返回新的 `coverage_id`；创建失败时直接抛出具体错误。
- `save_draft_report`、`validators` 和 `submit_report` 在失败时都直接抛出具体错误；错误信息必须足够明确，让上游 LLM 或人工据此补字段、重新确认或中止流程。

## 3. 实现落地

### 3.1 resolve_coverage 执行流程

`resolve_coverage` 的输入为 `ticker` 和 `first_analyst_id`。执行时先按 `ticker` 查询候选 `coverage`，再关联 `coverage_analyst` 过滤出包含该 `first_analyst_id` 的记录。只要该分析师出现在某条 `coverage` 的分析师列表中，就视为命中，不要求其在 `coverage_analyst` 中也为 `role = 1`。

命中唯一 `coverage` 时返回 `coverage_id`；命中多条时抛出“无法自动确定”的具体错误；未命中时抛出“需要进入 create_coverage 流程”的具体错误。

`resolve_coverage` 只负责解析和确认 `coverage_id`，不修改数据库，也不承担补数据或自动创建逻辑。

`resolve_coverage` 的候选查询、分析师关联过滤和唯一性判定优先在 Supabase 侧实现；skill 侧负责组织输入并调用该接口。

### 3.2 create_coverage 执行流程

`create_coverage` 的输入为创建 `coverage` 所需的完整业务字段，以及初始 `coverage_analyst` 列表。创建 `coverage` 时至少写入 `ticker`、`english_full_name`、`sector_id`、`isin`、`country_of_domicile`；如已具备中文信息，可同时写入 `chinese_short_name` 和 `traditional_chinese`。随后再写入对应的 `coverage_analyst` 关系。

初始 `coverage_analyst` 与本次报告分析师列表保持一致，最多支持 8 位分析师，其中必须包含报告 `1作 analyst_id`。创建成功后返回新的 `coverage_id`，供上游写回当前 draft。

`create_coverage` 是显式创建接口，不由 `submit_report` 隐式触发。只有在 `resolve_coverage` 未命中，且上游已经与用户确认“该 Coverage 已完成审批”后，才进入 `create_coverage`。失败时直接抛出具体错误。

`create_coverage` 的主数据写入、一致性校验和 `coverage_analyst` 关系创建优先在 Supabase 侧实现；skill 侧负责参数整理并调用该接口。

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

`save_draft_report` 在首次调用时创建新的 `report_id`，并保存机器处理后的第一个 draft 版本。保存过程中，本地文件先上传到 storage，再写入 `report_version.word_file_path`、`report_version.pdf_file_path`、`report_version.model_file_path`；后续校验和提交都以这些持久化字段为准。同时同步更新 `report` 主表的当前态字段，并将 `current_version_no` 更新为本次版本号；`report_analyst` 按当前 `analysts` 列表刷新为报告最新作者关系。`report_version.snapshot_json` 保存本次 draft 输入的完整快照，本地文件路径字段除外。后续人工修订也沿用同一个 `report_id` 继续追加版本。

`save_draft_report` 的主要写入逻辑优先在 Supabase 侧实现为稳定接口；skill 侧负责准备参数、上传文件并调用该接口。

`save_draft_report` 成功时至少返回：

```json
{
  "report_id": "uuid",
  "version_no": 1,
  "status": "draft"
}
```

`save_draft_report` 不要求当前版本已经满足最终提交条件。它的职责是把机器处理结果保存到 Neolyst，供人工直接查看和继续处理。

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
- 文件路径判定以 `report_version.word_file_path`、`report_version.pdf_file_path`、`report_version.model_file_path` 为准

draft 版本需已持久化的核心内容：

- `title`
- `report_type`
- `report_language`
- `analysts`
- `report_version.word_file_path`
- `report_version.pdf_file_path`

提交前必填字段：

- `title`
- `report_type`
- `report_language`
- `contact_person_id`
- `investment_thesis`
- `certificate_confirmed = true`
- `analysts`
- `report_version.word_file_path`
- `report_version.pdf_file_path`

按类型要求：

- `company`：`coverage_id`、`ticker`、`rating`、`target_price`、`report_version.model_file_path`
- `company_flash`：`coverage_id`、`ticker`
- `sector`：`region_code`、`sector_id`
- `sector_flash`：`region_code`、`sector_id`
- `macro`：`region_code`
- `strategy`：`region_code`
- `quantitative`：`region_code`
- `bond`：`region_code`

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
- 校验失败：直接抛出具体错误

`validators` 的字段完整性判断、主数据校验和版本一致性校验优先在 Supabase 侧实现；skill 侧负责调用并透传错误。

### 3.5 submit_report 执行流程

`submit_report` 接收 `report_id` 和 `version_no`，用于提交该 draft 版本。对应 draft 在进入该接口前必须已经完成必要的 `resolve_coverage`、`create_coverage` 补充以及 `validators` 校验。

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

`submit_report` 不负责隐式创建 `coverage`，也不负责补字段或做人机交互。执行失败时直接抛出具体错误。

### 3.6 模块拆分

实现层由以下模块组成：`connection`、`storage`、`analyst`、`template`、`coverage`、`draft_report`、`validators`、`submit_report`。

目录结构如下：

```text
neolyst/
  SKILL.md
  scripts/
    connection.py
    storage.py
    analyst.py
    template.py
    coverage.py
    draft_report.py
    validators.py
    submit_report.py
```

`SKILL.md` 负责声明对外业务接口，说明高层输入输出约定，以及 `/.neolyst` 的使用方式。具体实现细节放在 `scripts/*.py`。

`connection.py` 负责连接相关能力，包括读取和写入 `/.neolyst`、创建 Supabase client、恢复 session、失效后重新登录，以及对外提供已认证的访问连接。

`storage.py` 负责模板文件和报告文件上传，以及统一的 storage 路径生成规则。

`storage.py` 内部固定维护以下 bucket 与路径规则：

- 模板 bucket：模板对象路径以 `template_file_path` / `schema_file_path` 为准，不由 `report_type` 公式推导
- 报告 bucket：存放 `{report_id}/...`

`analyst.py` 负责 `resolve_analyst_by_email`。凡是 analyst 身份解析相关的查询都放在该模块内。

`template.py` 负责 `resolve_template`、`upsert_template` 与 `reuse_template`。`upsert_template` 接收本地 Word 模板路径 `template_local_path` 和本地 `schema.yaml` 路径 `schema_local_path`，由 `neolyst` 上传到 storage 后调用 Supabase 侧模板发布接口写入主模板记录；`reuse_template` 接收目标 `report_type + language` 与源 `same_as_report_type`，调用 Supabase 侧共享模板接口，把源记录当前已有的 `template_file_path` 与 `schema_file_path` 静态复制到目标模板记录；`resolve_template` 负责将运行时模板和对应的 `schema.yaml` 下载到本地可用路径并返回。

`coverage.py` 负责 `resolve_coverage` 和 `create_coverage`。凡是与 `coverage`、`coverage_analyst` 相关的查询和写入都通过该模块调用 Supabase 侧对应接口完成。

`draft_report.py` 负责 `save_draft_report`，处理 draft 版本创建、文件上传和调用 Supabase 侧 draft 保存接口。

`validators.py` 负责提交前校验，根据 `report_id` 和 `version_no` 调用 Supabase 侧校验接口判断指定 draft 版本是否满足提交条件，不负责创建业务对象，也不执行提交。

`submit_report.py` 负责提交已有 draft，串联连接获取、draft 版本定位、提交前校验和调用 Supabase 侧提交接口。`submit_report` 的职责聚焦于状态推进与提交审计；`report` 主表当前态字段和 `current_version_no` 已由 `save_draft_report` 在保存 draft 时同步更新。

模块之间的依赖关系保持单向：`draft_report` 可以调用 `connection` 和 `storage`；`submit_report` 可以调用 `connection` 和 `validators`；`validators` 可以调用 `analyst`、`coverage` 和 `connection`；`template` 可以调用 `connection` 和 `storage`；`coverage`、`analyst` 与 `storage` 只依赖 `connection`；`connection` 不依赖任何业务模块。

## 4. 联调与环境

### 4.1 联调测试环境

- URL：`http://47.57.213.88:80`
- Admin username：`admin@neolyst.com`
- Admin password：`Admin123`

## 5. report_maker 对接 neolyst 的改造要求

### 5.1 模板与查询

`report_maker` 保持现有草稿解析、字段确认、模板渲染和输出 Word/PDF 主流程不变。生成阶段所需的 Neolyst 数据读取统一通过 `neolyst` 接口完成。

模板选择也通过 `neolyst` 完成。`report_maker` 根据 `report_type` 和 `language` 调用 `resolve_template` 获取当前使用的模板资产，不再从本地 `templates/` 目录读取模板。这里的 `language` 来自当前报告的 `report_language`。运行时使用的 Word 模板和对应 `schema.yaml` 都以 `neolyst` 中保存的模板记录为准。若多个 `report_type` 共用同一模板，则这些 `report_type` 在运行时都会解析到同一套模板资产路径。

机器处理并生成 Word/PDF 后，`report_maker` 调用 `save_draft_report` 将机器处理结果保存为第一个 draft 版本。人工确认前，Neolyst 中已经存在该 `report_id` 下可查看的 draft。

### 5.2 提交字段确认

`report_maker` 负责补齐提交所需但不属于报告渲染本身的业务字段，并在必要时通过对话确认后写入 draft。

`contact_person_id` 由 `report_maker` 负责确认和填充，规则如下：

- 单 analyst 场景，使用该 analyst 作为 `contact_person_id`
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

`certificate_confirmed` 由 `report_maker` 写为 `true`。

对于公司类报告，`report_maker` 还负责准备以下 `coverage` 相关输入：

- `ticker`
- 报告 `1作 analyst_id`
- 新建 `coverage` 所需字段，包括 `english_full_name`、`sector_id`、`isin`、`country_of_domicile`
- 如已具备中文信息，同时准备 `chinese_short_name` 和 `traditional_chinese`

新建 `coverage` 时，`report_maker` 使用本次报告分析师列表初始化 `coverage_analyst`。对已有 `coverage`，`report_maker` 不通过提交流程改写其既有 `coverage_analyst`，报告作者关系独立进入 `report_analyst`。

当 `resolve_coverage` 未命中且需要进入 `create_coverage` 时，`report_maker` 先与用户对话确认“该 Coverage 已完成审批”，确认后才继续调用 `create_coverage`。

### 5.3 draft 组装

`report_maker` 在机器处理完成后，需要将内部数据显式转换为 `neolyst` 所要求的扁平 draft 输入。`elements.yaml`、渲染上下文和输出目录结构不直接等价于 draft 输入，需要单独映射。

draft 输入分两层：

- 保存 draft 时的最小字段：`title`、`report_type`、`report_language`、`analysts`、`report_file`、`pdf_file`
- 提交前补齐字段：`contact_person_id`、`investment_thesis`、`certificate_confirmed`，以及按研报类型要求的 `coverage_id`、`ticker`、`rating`、`target_price`、`region_code`、`sector_id`、`model_file`

draft 输入可包含以下字段：

- 报告基本字段：`title`、`report_id`、`report_type`、`report_language`、`investment_thesis`
- 分析师与联系人字段：`analysts`、`contact_person_id`
- 公司类报告字段：`coverage_id`、`ticker`、`rating`、`target_price`
- 行业类报告字段：`region_code`、`sector_id`
- 合规字段：`certificate_confirmed`
- 文件字段：`report_file`、`pdf_file`、`model_file`

文件字段映射：

- draft 使用最终生成的 Word 文件路径作为 `report_file`
- draft 使用最终生成的 PDF 文件路径作为 `pdf_file`
- `model_file` 仅在公司类报告提交时提供

模板解析规则：

- `resolve_template` 直接按 `report_type + language` 查询 `template` 记录
- 若多个 `report_type` 共用同一模板资产，则这些 `report_type` 最终解析到同一组 `template_file_path` 与 `schema_file_path`
- `report_maker` 不再维护额外的“报告类型 -> 模板类型”映射表

### 5.4 draft 查看

`report_maker` 不再等待所有字段完全正确后才把结果写入 Neolyst。机器处理结果通过 `save_draft_report` 直接保存为 draft，人工可以直接在 Neolyst 中查看该版本、核对内容，并决定是否继续提交。

### 5.5 提交前校验

在人工确认提交前，Neolyst 或其他上层流程根据 `report_id` 和 `version_no` 调用 `validators(report_id, version_no)` 对指定 draft 版本执行提交前校验。

对于公司类报告，提交前仍需要完成 `resolve_coverage`、必要时的 `create_coverage`、`contact_person_id` 确认以及其他提交必填字段补齐。只有该 draft 版本满足提交条件后，才允许进入 `submit_report`。

### 5.6 报告提交

人工在 Neolyst 中查看并确认指定 draft 版本后，调用 `submit_report(report_id, version_no)` 将该版本提交为 `submitted`。

`report_maker` 的职责默认止于 draft 保存，不自动执行最终提交。

### 5.7 失败处理

当 `save_draft_report`、`resolve_coverage`、`create_coverage`、`validators` 或 `submit_report` 抛出具体错误时，`report_maker` 或人工流程负责根据错误内容继续补字段、重新确认或终止流程。

字段缺失、字段歧义、联系人确认和 `coverage` 创建信息不足等问题，由 `report_maker` 继续通过对话处理。多轮补充、重新保存 draft、重新校验和重新提交都围绕同一个 `report_id` 进行。

## 6. template_maker 对接 neolyst 的改造要求

### 6.1 模板资产写入 neolyst

`template_maker` 负责提供 `report_type + language` 和本地源文件路径；`neolyst` 负责上传到 Storage，并调用 Supabase 侧模板发布接口完成幂等写入。

主模板发布上传实际的 Word 模板和 `schema.yaml`。共享模板发布只声明“当前 `report_type` 复用另一个已发布 `report_type` 的模板”，不重复上传文件。

`upsert_template` 输入字段：

- `report_type`
- `language`
- `name`
- `template_local_path`
- `schema_local_path`

`reuse_template` 输入字段：

- `report_type`
- `language`
- `same_as_report_type`

发布完成后，运行时模板来源统一为 `template` 表。记录中的 `template_file_path` 和 `schema_file_path` 共同定义一套模板资产。

`schema.yaml` 是模板资产的一部分，用于描述抽取字段和抽取约束。

### 6.2 共享模板关系写入 neolyst

模板关系通过 `upsert_template` 与 `reuse_template` 直接写入 `neolyst`，不再以本地 `router.yaml` 或目录结构作为运行时事实来源。

若多个 `report_type` 共用同一模板，先用 `upsert_template` 发布主模板，再用 `reuse_template` 为其他 `report_type` 写入共享关系。例如先发布 `macro + en`，再声明 `quantitative + en` 复用 `macro`。

共享关系采用静态复制。若主模板后续重新上传并生成新路径，需要重新执行 `reuse_template`。

`reuse_template` 至少覆盖以下错误：

- 源模板未发布
- `language` 不一致
- `report_type` 复用自己

### 6.3 本地模板目录的定位变化

本地 `templates/` 目录保留为模板制作阶段的工作目录，用于编辑、验证和预览模板。模板一旦发布，运行时来源统一为 `neolyst.resolve_template` 返回的模板资产，`report_maker` 不再直接读取该目录中的模板文件。

`router.yaml` 等本地辅助组织方式如果继续保留，也只服务于模板制作阶段的人类维护体验；它们不再是运行时模板选择的事实来源，也不参与 `report_type -> 模板` 的最终判定。

## 7. 后续待做

- Coverage 审批链路。当前设计在用户确认“该 Coverage 已完成审批”后允许 `create_coverage` 直接创建 Coverage；后续需要补上首次覆盖场景下的正式审批流程，并与 `resolve_coverage` / `create_coverage` 的调用时机重新收口。
