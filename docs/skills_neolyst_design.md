# neolyst Skill 设计文档

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
- `validate_draft` 校验当前 draft 的当前版本是否可提交。
- `submit_report` 提交当前 draft 的当前版本。
- 不暴露 `upload_file` 之类的底层中间接口。

### 2.2 draft 与提交契约

- `save_draft_report` 的输入由 `neolyst` 定义并维护，`report_maker` 依赖该契约，而不是反过来。
- draft 输入采用全打平结构，业务字段和本地文件路径都位于顶层。
- draft 输入不携带执行上下文字段，例如 `workspace_root`、`trace_id`、`server_url_override`、`dry_run`。
- `save_draft_report` 的文件输入统一使用本地路径，由 `neolyst` 上传到 Storage。
- 模板文件位于模板 bucket，最终路径以 `report_template.template_file_path` 与 `report_template.schema_file_path` 为准，不由 `report_type` 公式推导。
- 报告文件位于报告 bucket，持久化字段中的 Storage 路径包含 bucket 前缀 `reports/`；bucket 内相对路径固定为 `{report_id}/v{version_no}/{原始文件名}`，文件名保留调用方传入的原始文件名，版本间通过版本目录隔离。
- `report_id` 在首次保存 draft 时为空；机器处理后的 draft 和后续人工修订版都沿用同一个 `report_id` 追加新版本。
- draft 契约分为"可保存字段"和"提交前必填字段"两层。
- `company` / `company_flash` 在 draft 阶段允许暂时缺少 `coverage_id`，提交前必须补齐。
- `contact_person` 在 draft 阶段允许暂时缺少；该字段存储 analyst email，提交前必须由 `report_maker` 负责确认和填充。
- `report_language` 作为模板选择字段，由 `report_maker` 自动识别并向用户确认后写入 draft。
- `analysts` 列表与 `coverage_analyst` / `report_analyst` 统一以 `analyst_email` 作为业务键，排序字段统一使用 `author_order`；不再引入 `analyst_id`、`role`、`sort_order` 三套并存的表示。
- `save_draft_report` 输入中的 `report_file`、`pdf_file`、`model_file` 仅用于上传前定位本地文件；文件路径的唯一准源是 `report_version.word_file_path`、`report_version.pdf_file_path`、`report_version.model_file_path`。`snapshot_json` 如保留文件字段，只作为版本快照，不作为校验和提交的判定来源。
- `save_draft_report` 成功时至少返回 `report_id` 和 `version_no`。
- `validate_draft` 与 `submit_report` 都只以 `report_id` 为输入，实际作用版本由 `report.current_version_no` 决定。

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
- 报告所有者与执行审计均以当前登录身份为准。`owner_user_id`、`report_version.created_by`、`report_status_log.action_by` 等字段遵循"谁保存/提交，系统就记谁"；`resolve_analyst_by_email` 只用于确定报告分析师身份，不用于决定执行审计用户。
- 本 skill 不做代理执行，因为这会破坏 Neolyst 的安全性，也不符合实际业务关系。

### 2.5 业务逻辑落点

- 凡涉及业务数据一致性、状态流转、关系维护、主表/版本表同步的逻辑，均优先在 Supabase 侧实现为稳定接口。
- 凡涉及复杂读操作或复杂写操作，均默认在 Supabase 侧封装为 RPC / 稳定接口，而不是在 skill 侧拼接多次底层表操作。这里的"复杂"包括但不限于：需要按固定规则确定模板或报告文件路径、需要同时维护多张表、需要做跨表一致性判断、需要把业务校验与写入合并为一个原子操作。
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
- 模板 bucket 路径规则：`templates/{report_type}/{language}/template.docx` 和 `templates/{report_type}/{language}/schema.yaml`。`template_file_path` / `schema_file_path` 字段存储含 bucket 前缀的完整路径；路径由 Supabase RPC `get_template_storage_paths` 统一生成，`storage.py` 只负责上传/下载。
- 报告 bucket 路径规则：`reports/{report_id}/v{version_no}/{原始文件名}`。路径由 `draft_report.py` 在调用 draft 保存 RPC 前生成，文件名保留调用方传入的原始文件名（`Path(local_path).name`），版本间文件存储在独立目录下互不覆盖。
- `resolve_template(client, report_type, language, dest_dir=".")` 将模板文件下载到 `dest_dir/templates/{report_type}/{language}/` 下，文件名与 bucket 中一致（`template.docx`、`schema.yaml`）。

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

- 提交前校验由 `neolyst` 负责，`validate_draft(report_id)` 用于校验当前 draft 的当前版本是否满足提交条件。
- `reuse_template(report_type, language, same_as_report_type)` 约束如下：
  - 源模板记录必须存在
  - 复用只能发生在同一 `language` 内
  - `report_type` 不能与 `same_as_report_type` 相同
- `reuse_template` 失败时直接抛出具体错误，至少覆盖：源模板不存在、语言不一致、试图复用自己。
- `resolve_coverage` 按 `ticker` 查询候选 `coverage`，再通过 `coverage_analyst` 判断报告 `1作 analyst_email` 是否属于该 `coverage` 的分析师列表；只要求该分析师出现在列表中，不要求其在 `coverage_analyst` 中单独维护额外角色字段。
- `resolve_coverage` 命中唯一 `coverage` 时返回 `coverage_id`；命中多条或未命中时直接抛出具体错误。
- `create_coverage` 创建成功时返回新的 `coverage_id`；创建失败时直接抛出具体错误。
- `save_draft_report`、`validate_draft` 和 `submit_report` 在失败时都直接抛出具体错误；错误信息必须足够明确，让上游 LLM 或人工据此补字段、重新确认或中止流程。

## 3. 实现落地
