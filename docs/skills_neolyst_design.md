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

## 3. 实现落地
