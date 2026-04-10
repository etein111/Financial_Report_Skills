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

- `neolyst` 对外只暴露业务接口：`resolve_analyst_by_email`、`resolve_template`、`upsert_template`、`reuse_template`、`resolve_coverage`、`create_coverage`、`list_coverage_history`、`save_draft_report`、`validate_draft`、`submit_report`。
- `resolve_analyst_by_email` 校验并返回标准化后的 analyst 记录，业务主键为 `analyst_email`。
- `resolve_template` 解析模板资产。
- `upsert_template` 发布主模板。
- `reuse_template` 发布共享模板关系。
- `resolve_coverage`、`create_coverage` 负责 `coverage` 解析与创建。
- `list_coverage_history` 查询 coverage 下的已发布历史报告。
- `save_draft_report` 保存 draft。
- `validate_draft` 校验指定 draft 版本是否可提交。
- `submit_report` 提交指定 draft 版本。
- 不暴露 `upload_file` 之类的底层中间接口。

### 2.2 draft 与提交契约

- `save_draft_report` 的输入由 `neolyst` 定义并维护，`report_maker` 依赖该契约，而不是反过来。
- draft 输入采用全打平结构，业务字段和本地文件路径都位于顶层。
- draft 输入不携带执行上下文字段，例如 `workspace_root`、`trace_id`、`server_url_override`、`dry_run`。
- `save_draft_report` 的文件输入统一使用本地路径，由 `neolyst` 上传到 Storage。
- 模板文件位于模板 bucket，最终路径以 `report_template.template_file_path` 与 `report_template.schema_file_path` 为准，不由 `report_type` 公式推导。
- 报告文件位于报告 bucket，bucket 内路径固定为 `{report_id}/`；文件名由 `neolyst` 在 skill 内统一生成并保持稳定，同一类产物在各版本间使用一致命名。
- `report_id` 在首次保存 draft 时为空；机器处理后的 draft 和后续人工修订版都沿用同一个 `report_id` 追加新版本。
- draft 契约分为“可保存字段”和“提交前必填字段”两层。
- `company` / `company_flash` 在 draft 阶段允许暂时缺少 `coverage_id`，提交前必须补齐。
- `contact_person` 在 draft 阶段允许暂时缺少；该字段存储 analyst email，提交前必须由 `report_maker` 负责确认和填充。
- `report_language` 作为模板选择字段，由 `report_maker` 自动识别并向用户确认后写入 draft。
- `analysts` 列表与 `coverage_analyst` / `report_analyst` 统一以 `analyst_email` 作为业务键，排序字段统一使用 `author_order`；不再引入 `analyst_id`、`role`、`sort_order` 三套并存的表示。
- `save_draft_report` 输入中的 `report_file`、`pdf_file`、`model_file` 仅用于上传前定位本地文件；文件路径的唯一准源是 `report_version.word_file_path`、`report_version.pdf_file_path`、`report_version.model_file_path`。`snapshot_json` 如保留文件字段，只作为版本快照，不作为校验和提交的判定来源。
- `save_draft_report` 成功时至少返回 `report_id` 和 `version_no`。
- `validate_draft` 与 `submit_report` 都以 `report_id + version_no` 为输入。

### 2.3 研报类型与模板记录

- draft、提交和模板接口统一使用研报类型 `report_type`，其取值为：`company`、`sector`、`company_flash`、`sector_flash`、`macro`、`strategy`、`quantitative`、`bond`。
- 模板接口在业务语义上使用 `report_type + language` 做定位；当前数据库层只有 `report_template.id` 主键，以及 `(report_type, language)` 普通索引，没有这组字段的唯一约束。实现上应以 `{report_type}_{language}` 对应的 `report_template.id` 锁定目标记录；若出现同一 `report_type + language` 的重复记录，应视为数据异常。
- `report_template.report_type` 就是报告类型本身，不引入单独的 `template_type` 概念。
- 多个 `report_type` 可以共用同一套模板资产；发布时先上传一次主模板，再让其他 `report_type` 复用该主模板对应的 `template_file_path` 与 `schema_file_path`。
- `reuse_template` 的复用是静态复制当前路径，不是动态引用；若主模板后续重新上传并变更路径，需要重新执行一次 `reuse_template` 才能同步到复用方。

### 2.4 身份与会话策略

- Neolyst Supabase 的登录身份由 `neolyst` 管理和复用，`save_draft_report`、`validate_draft` 与 `submit_report` 的相关读写都使用该身份。
- 使用 `email + password` 登录。账号和密码保存在 skill 根目录（`skills/neolyst/`）的 `user.json`；登录态保存在同目录的 `session.json`。两者都不提交到版本库。
- `connection.py` 启动时先尝试用 `session.json` 中的 `access_token` + `refresh_token` 恢复 session；若已过期或失效，则回退到 `user.json` 中的 `email + password` 重新登录，并只回写 `session.json`。
- `user.json` 不存在时，调用方需向用户索取邮箱和密码，使用 `get_client(email=..., password=...)` 完成首次登录。成功后自动写入 `user.json` 与 `session.json`，后续无需再次手动输入。
- 当前库的 RLS 通过 `current_app_role()` 读取 `auth.jwt().app_metadata.role`，按 `admin`、`sa`、`analyst` 做权限控制；skill 设计必须与该角色模型兼容。
- 报告所有者与执行审计均以当前登录身份为准。`owner_user_id`、`report_version.created_by`、`report_status_log.action_by` 等字段遵循”谁保存/提交，系统就记谁”；`resolve_analyst_by_email` 只用于确定报告分析师身份，不用于决定执行审计用户。
- 本 skill 不做代理执行，因为这会破坏 Neolyst 的安全性，也不符合实际业务关系。

### 2.5 业务逻辑落点

- 凡涉及业务数据一致性、状态流转、关系维护、主表/版本表同步的逻辑，均优先在 Supabase 侧实现为稳定接口。
- 凡涉及复杂读操作或复杂写操作，均默认在 Supabase 侧封装为 RPC / 稳定接口，而不是在 skill 侧拼接多次底层表操作。这里的“复杂”包括但不限于：需要按固定规则确定模板或报告文件路径、需要同时维护多张表、需要做跨表一致性判断、需要把业务校验与写入合并为一个原子操作。
- `neolyst` skill 主要负责认证、文件上传、参数整理以及调用 Supabase 暴露的接口/函数，不在 skill 侧重复实现核心业务一致性规则。
- 适合下沉到 Supabase 侧的逻辑包括：模板发布与复用、模板解析、coverage 解析与创建、draft 保存、提交状态流转，以及 `report` / `report_version` / `report_analyst` 之间的一致性维护。
- 当前实现边界：`upsert_template` / `reuse_template` 由 Supabase 侧负责锁定目标模板记录并落库；`save_draft_report` 由 Supabase 侧负责在一次业务接口调用中同步维护 `report`、`report_version`、`report_analyst`；`submit_report` 继续通过 RPC 完成状态流转；`validate_draft` 暂时保留在 Python 侧，以 SELECT 查询完成提交前校验，不下沉为 RPC。

### 2.6 技术访问方式

- 本 skill 使用 Python `supabase-py` 与 Neolyst Supabase 交互，并通过 `uv` 管理依赖与执行环境。
- 数据库结构真相以本地 Supabase 实例和 `supabase/migrations/*.sql` 为准；本设计文档需要与它们保持同步。
- Storage 使用两个独立 bucket：
  - 模板 bucket：`templates`，存放模板资产
  - 报告 bucket：`reports`，存放报告版本资产
- Storage RLS 策略：
  - `templates`：所有已认证用户可下载；仅 `admin` 角色可上传/更新/删除
  - `reports`：`admin` 可读写全部；`analyst` 可读写自己 `draft`/`submitted` 状态的报告文件；`sa` 可读 `submitted`/`published`/`rejected` 状态的报告文件
- 模板 bucket 路径规则：`{report_type}/{language}/template.docx` 和 `{report_type}/{language}/schema.yaml`。路径由 `storage.py` 按此规则生成，`template_file_path` / `schema_file_path` 字段存储的即是该路径。
- 报告 bucket 路径规则：`{report_id}/v{version_no}/{原始文件名}`。路径由 `draft_report.py` 在 `commit_draft_version` 前生成，文件名保留调用方传入的原始文件名（`Path(local_path).name`），版本间文件存储在独立目录下互不覆盖。
- `resolve_template` 将模板文件下载到当前工作目录的 `templates/{report_type}/{language}/` 下，文件名与 bucket 中一致（`template.docx`、`schema.yaml`）。

### 2.7 Supabase 连接配置

- Supabase URL 和 anon key 由 skill 负责确定，写在 `skills/neolyst/neolyst.yaml` 中，随 skill 一起提交到版本库。anon key 是公开的客户端 key，不是密钥，可以安全提交。
- `neolyst.yaml` 格式：`supabase_url: "..."` 和 `anon_key: "..."`。
- `neolyst.yaml` 是运行时默认配置，当前仓库版本可以指向 staging，不能视为本地测试默认环境。
- 本地测试必须通过 `NEOLYST_URL` 和 `NEOLYST_ANON_KEY` 环境变量覆盖 yaml 中的值；测试入口再由 `NEOLYST_TEST_URL` / `NEOLYST_TEST_ANON_KEY` 映射过去，禁止回落到 yaml 默认值。

### 2.8 提交流程

- 报告生命周期采用 draft 驱动：机器处理后的结果先保存为 draft，人工确认后再执行提交。
- `save_draft_report` 用于保存 draft，不要求当前版本已经满足最终提交条件。
- `submit_report` 仅负责将已有 draft 推进到 `submitted`。
- 提交失败后的重新提交沿用原 `report_id`，在原 report 下创建新版本。
- 整体行为对齐 Neolyst Web 的 `Analyst Submit`，不引入独立提交流程。

### 2.9 校验与错误语义

- 提交前校验由 `neolyst` 负责，`validate_draft(report_id, version_no)` 用于校验指定 draft 版本是否满足提交条件。
- `reuse_template(report_type, language, same_as_report_type)` 约束如下：
  - 源模板记录必须存在
  - 复用只能发生在同一 `language` 内
  - `report_type` 不能与 `same_as_report_type` 相同
- `reuse_template` 失败时直接抛出具体错误，至少覆盖：源模板不存在、语言不一致、试图复用自己。
- `resolve_coverage` 按 `ticker` 查询候选 `coverage`，再通过 `coverage_analyst` 判断报告 `1作 analyst_email` 是否属于该 `coverage` 的分析师列表；只要求该分析师出现在列表中，不要求其在 `coverage_analyst` 中单独维护额外角色字段。
- `resolve_coverage` 命中唯一 `coverage` 时返回 `coverage_id`；命中多条或未命中时直接抛出具体错误。
- `create_coverage` 创建成功时返回新的 `coverage_id`；创建失败时直接抛出具体错误。
- `save_draft_report`、`validate_draft` 和 `submit_report` 在失败时都直接抛出具体错误；错误信息必须足够明确，让上游 LLM 或人工据此补字段、重新确认或中止流程。

### 2.10 Supabase 侧实现原则

- 复杂读写默认走 Supabase 侧 RPC / 稳定接口。
- 原则上尽量不用外键，跨表一致性由 RPC 负责。

## 3. 实现落地

### 3.1 resolve_coverage 执行流程

`resolve_coverage` 的输入为 `ticker` 和 `first_analyst_email`。执行时先按 `ticker` 查询候选 `coverage`，再关联 `coverage_analyst` 过滤出包含该 `first_analyst_email` 的记录。只要该分析师出现在某条 `coverage` 的分析师列表中，就视为命中，不要求其在 `coverage_analyst` 中维护额外角色字段。

命中唯一 `coverage` 时返回 `coverage_id`；命中多条时抛出“无法自动确定”的具体错误；未命中时抛出“需要进入 create_coverage 流程”的具体错误。

`resolve_coverage` 只负责解析和确认 `coverage_id`，不修改数据库，也不承担补数据或自动创建逻辑。

`resolve_coverage` 的候选查询、分析师关联过滤和唯一性判定优先在 Supabase 侧通过 RPC / 稳定接口实现；skill 侧负责组织输入并调用该接口。

### 3.2 create_coverage 执行流程

`create_coverage` 的输入为创建 `coverage` 所需的完整业务字段，以及初始 `coverage_analyst` 列表。创建 `coverage` 时至少写入 `ticker`、`english_name`、`sector_id`、`isin`、`country_of_domicile`；如已具备中文信息，可同时写入 `chinese_name` 和 `traditional_chinese`。随后再写入对应的 `coverage_analyst` 关系。

初始 `coverage_analyst` 与本次报告分析师列表保持一致，最多支持 8 位分析师，其中必须包含报告 `1作 analyst_email`。分析师排序统一写入 `author_order`，其中 `author_order = 1` 代表报告 1 作。创建成功后返回新的 `coverage_id`，供上游写回当前 draft。

`create_coverage` 是显式创建接口，不由 `submit_report` 隐式触发。只有在 `resolve_coverage` 未命中，且上游已经与用户确认“该 Coverage 已完成审批”后，才进入 `create_coverage`。失败时直接抛出具体错误。

`create_coverage` 的主数据写入、一致性校验和 `coverage_analyst` 关系创建优先在 Supabase 侧通过 RPC / 稳定接口实现；skill 侧负责参数整理并调用该接口。

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
  "contact_person": "alice.analyst@neolyst.com",
  "investment_thesis": "AI-driven demand and margin expansion support earnings growth.",
  "analysts": [
    {
      "analyst_email": "alice.analyst@neolyst.com",
      "author_order": 1
    },
    {
      "analyst_email": "bob.analyst@neolyst.com",
      "author_order": 2
    }
  ],
  "report_file": "/abs/path/report.docx",
  "pdf_file": "/abs/path/report.pdf",
  "model_file": "/abs/path/model.xlsx"
}
```

`save_draft_report` 在首次调用时创建新的 `report_id`，并保存机器处理后的第一个 draft 版本。保存过程中，本地文件先上传到 storage，再写入 `report_version.word_file_path`、`report_version.pdf_file_path`、`report_version.model_file_path`；后续校验和提交都以这些持久化字段为准。同时同步更新 `report` 主表的当前态字段，并将 `current_version_no` 更新为本次版本号；`report_analyst` 按当前 `analysts` 列表刷新为报告最新作者关系。`report_version.snapshot_json` 保存本次 draft 输入的完整快照，本地文件路径字段除外。后续人工修订也沿用同一个 `report_id` 继续追加版本。

`save_draft_report` 的主要写入逻辑优先在 Supabase 侧实现为 RPC / 稳定接口；skill 侧负责准备参数、上传文件并调用该接口。

`save_draft_report` 成功时至少返回：

```json
{
  "report_id": "uuid",
  "version_no": 1,
  "status": "draft"
}
```

`save_draft_report` 不要求当前版本已经满足最终提交条件。它的职责是把机器处理结果保存到 Neolyst，供人工直接查看和继续处理。

### 3.4 validate_draft 执行流程

`validate_draft` 接收 `report_id` 和 `version_no`，用于判断该 draft 版本是否满足进入 `submit_report` 的条件。

校验范围：

- 结构校验
- 必填字段校验
- 主数据校验
- 公司类报告校验
- 文件路径校验

结构校验：

以下规则属于 `validate_draft` 这层业务校验要求。当前实现保留在 Python 侧，通过只读 SELECT 查询完成；它们不要求全部下沉为当前裸表 schema 的 CHECK / FK 约束。

- 指定的 draft 版本必须存在
- `analysts` 必须为非空列表
- `analysts` 最多支持 8 位分析师
- `analysts[].analyst_email`、`author_order` 必须完整
- `analysts` 中必须恰好存在一位 `author_order = 1` 的分析师，作为报告 `1作 analyst_email`
- `analysts[].author_order` 必须唯一
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
- `contact_person`
- `investment_thesis`
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

- `report_type` 必须对应存在的 report type
- `report_language` 必须为有效模板语言
- `region_code` 必须对应有效 region
- `sector_id` 必须对应有效 sector
- `analysts[].analyst_email` 必须对应有效 analyst
- `contact_person` 必须属于 `analysts[].analyst_email`

公司类报告校验：

- `coverage_id` 必须对应存在的 `coverage`
- `coverage.ticker` 必须与输入 `ticker` 一致
- 报告 `1作 analyst_email` 必须存在于该 `coverage` 的 `coverage_analyst` 列表中
- 对已有 `coverage`，提交时不自动改写 `coverage_analyst`；报告分析师关系独立写入 `report_analyst`

结果语义：

- 校验通过：返回被校验通过的 `report_id` 和 `version_no`
- 校验失败：直接抛出具体错误

`validate_draft` 当前由 `skills/neolyst/scripts/validators.py` 提供实现。它负责字段完整性判断、主数据校验和版本一致性校验，但不负责状态流转，也不负责写库。

### 3.5 submit_report 执行流程

`submit_report` 接收 `report_id` 和 `version_no`，用于提交该 draft 版本。对应 draft 在进入该接口前必须已经完成必要的 `resolve_coverage`、`create_coverage` 补充以及 `validate_draft` 校验。

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
  neolyst.yaml       ← 运行时默认 Supabase 连接配置（URL + anon_key），随 skill 发布
  user.json          ← 本地用户凭据（email/password），不提交
  session.json       ← 本地登录态（token），不提交
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

`SKILL.md` 负责声明对外业务接口，说明高层输入输出约定，以及 `user.json` / `session.json` 的使用方式。具体实现细节放在 `scripts/*.py`。

`connection.py` 负责连接相关能力，包括读取和写入 `user.json` / `session.json`、创建 Supabase client、恢复 session、失效后重新登录，以及对外提供已认证的访问连接。

`storage.py` 负责模板文件和报告文件上传/下载。对外暴露两个通用函数 `upload(client, storage_path, local_path)` 和 `download(client, storage_path, local_path)`，bucket 从路径首段自动解析，不需要调用方指定。路径由调用方传入（来自 Supabase RPC），`storage.py` 不拼路径字符串。

**路径规范：** 数据库中存储的所有 Storage 路径必须包含 bucket 前缀，格式为 `{bucket}/{path}`：

- 模板文件：`templates/{report_type}/{language}/template.docx`、`templates/{report_type}/{language}/schema.yaml`（规则定义在 Supabase 函数 `get_template_storage_paths` 和 `upsert_template_record` 中）
- 报告文件：`reports/{path}`（规则定义在 Supabase 函数中，Iter 4 实现）

`analyst.py` 负责 `resolve_analyst_by_email`。凡是 analyst 身份解析相关的查询都放在该模块内。

`template.py` 负责 `resolve_template`、`upsert_template` 与 `reuse_template`。

- `upsert_template` 的执行顺序：
  1. 调用 RPC `get_template_storage_paths(report_type, language)` 获取 Storage 目标路径（路径规则在服务端定义，skill 不拼路径）
  2. 将本地文件上传到返回的路径
  3. 调用 RPC `upsert_template_record(report_type, language)` 让服务端以相同规则生成路径并 upsert `report_template` 记录
- `reuse_template` 直接调用 RPC `reuse_template(report_type, language, same_as_report_type)`，服务端负责路径复制和合法性校验（源模板存在且已发布、不能自引用）
- `resolve_template` 直接查询 `report_template` 表读取 `template_file_path` / `schema_file_path`（无业务逻辑，不需要 RPC），再将文件下载到本地 `templates/{report_type}/{language}/` 目录

`coverage.py` 负责 `resolve_coverage` 和 `create_coverage`。凡是与 `coverage`、`coverage_analyst` 相关的查询和写入都通过该模块调用 Supabase 侧对应 RPC / 稳定接口完成。

`draft_report.py` 负责 `save_draft_report`，处理 draft 版本创建、文件上传和调用 Supabase 侧 draft 保存 RPC。

`validators.py` 模块对外暴露的业务接口名是 `validate_draft`。当前实现直接查询 `report`、`report_version`、`report_analyst`、`analyst`、`coverage`、`sector`、`region` 等表完成提交前校验，不调用 RPC，也不执行提交。

`submit_report.py` 负责提交已有 draft，串联连接获取、draft 版本定位、提交前校验和调用 Supabase 侧提交 RPC。`submit_report` 的职责聚焦于状态推进与提交审计；`report` 主表当前态字段和 `current_version_no` 已由 `save_draft_report` 在保存 draft 时同步更新。

模块之间的依赖关系保持单向：`draft_report` 可以调用 `connection` 和 `storage`；`submit_report` 可以调用 `connection` 和 `validators`；`validators` 可以调用 `connection` 并直接查询相关表；`template` 可以调用 `connection` 和 `storage`；`coverage`、`analyst` 与 `storage` 只依赖 `connection`；`connection` 不依赖任何业务模块。

## 4. 联调与环境

### 4.1 联调测试环境

- `neolyst.yaml` 仅作为运行时默认连接配置，当前仓库版本可指向 staging
- 本地测试必须显式提供 `NEOLYST_TEST_URL`、`NEOLYST_TEST_ANON_KEY`、`NEOLYST_TEST_EMAIL`、`NEOLYST_TEST_PASSWORD`
- pytest 启动时会把 `NEOLYST_TEST_URL` / `NEOLYST_TEST_ANON_KEY` 映射到 `NEOLYST_URL` / `NEOLYST_ANON_KEY`，确保测试不会回落到 `neolyst.yaml`

## 5. report_maker 对接 neolyst 的改造要求

### 5.1 模板与查询

`report_maker` 保持现有草稿解析、字段确认、模板渲染和输出 Word/PDF 主流程不变。生成阶段所需的 Neolyst 数据读取统一通过 `neolyst` 接口完成。

模板选择也通过 `neolyst` 完成。`report_maker` 根据 `report_type` 和 `language` 调用 `resolve_template` 获取当前使用的模板资产，不再从本地 `templates/` 目录读取模板。这里的 `language` 来自当前报告的 `report_language`。运行时使用的 Word 模板和对应 `schema.yaml` 都以 `neolyst` 中保存的模板记录为准。若多个 `report_type` 共用同一模板，则这些 `report_type` 在运行时都会解析到同一套模板资产路径。

机器处理并生成 Word/PDF 后，`report_maker` 调用 `save_draft_report` 将机器处理结果保存为第一个 draft 版本。人工确认前，Neolyst 中已经存在该 `report_id` 下可查看的 draft。

### 5.2 提交字段确认

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

当 `resolve_coverage` 未命中且需要进入 `create_coverage` 时，`report_maker` 先与用户对话确认“该 Coverage 已完成审批”，确认后才继续调用 `create_coverage`。

### 5.3 draft 组装

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
- `report_maker` 不再维护额外的“报告类型 -> 模板类型”映射表

### 5.4 draft 查看

`report_maker` 不再等待所有字段完全正确后才把结果写入 Neolyst。机器处理结果通过 `save_draft_report` 直接保存为 draft，人工可以直接在 Neolyst 中查看该版本、核对内容，并决定是否继续提交。

### 5.5 提交前校验

在人工确认提交前，Neolyst 或其他上层流程根据 `report_id` 和 `version_no` 调用 `validate_draft(report_id, version_no)` 对指定 draft 版本执行提交前校验。

对于公司类报告，提交前仍需要完成 `resolve_coverage`、必要时的 `create_coverage`、`contact_person` 确认以及其他提交必填字段补齐。只有该 draft 版本满足提交条件后，才允许进入 `submit_report`。

### 5.6 报告提交

人工在 Neolyst 中查看并确认指定 draft 版本后，调用 `submit_report(report_id, version_no)` 将该版本提交为 `submitted`。

`report_maker` 的职责默认止于 draft 保存，不自动执行最终提交。

### 5.7 失败处理

当 `save_draft_report`、`resolve_coverage`、`create_coverage`、`validate_draft` 或 `submit_report` 抛出具体错误时，`report_maker` 或人工流程负责根据错误内容继续补字段、重新确认或终止流程。

字段缺失、字段歧义、联系人确认和 `coverage` 创建信息不足等问题，由 `report_maker` 继续通过对话处理。多轮补充、重新保存 draft、重新校验和重新提交都围绕同一个 `report_id` 进行。

## 6. template_maker 对接 neolyst 的改造要求

### 6.1 模板资产写入 neolyst

`template_maker` 负责提供 `report_type + language` 和本地源文件路径；`neolyst` 负责上传到 Storage，并调用 Supabase 侧模板发布接口完成幂等写入。

主模板发布上传实际的 Word 模板和 `schema.yaml`。共享模板发布只声明“当前 `report_type` 复用另一个已发布 `report_type` 的模板”，不重复上传文件。

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

- Coverage 审批链路。当前设计在用户确认”该 Coverage 已完成审批”后允许 `create_coverage` 直接创建 Coverage；后续需要补上首次覆盖场景下的正式审批流程，并与 `resolve_coverage` / `create_coverage` 的调用时机重新收口。

## 补充：Coverage 历史查询

- 新增 `list_coverage_history(ticker, first_analyst_email)` 能力，面向”报告尚未写完、只有 ticker 和 1作信息”的前置查询场景。
- coverage 的定位逻辑沿用现有 `resolve_coverage`：按 `ticker + coverage_analyst.analyst_email` 命中唯一 coverage。
- 只返回 `status = 'published'` 的历史报告；`submitted`、`draft`、`rejected` 均不纳入结果。
- 返回字段固定为：`report_id`、`title`、`rating`、`target_price`、`published_at`。
- 结果按 `published_at desc` 排序。
- coverage 已找到但没有历史发布记录时返回空列表，不抛错。
- 该读取带业务判定，按仓库约定下沉到 Supabase RPC；Python 侧只做参数整理和调用。
- 权限设计：新增 RLS policy `report_select_published`，允许 `analyst` 角色读取所有 `status = 'published'` 的报告行，无需 SECURITY DEFINER。
