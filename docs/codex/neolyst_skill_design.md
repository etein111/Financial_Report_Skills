# neolyst skill 设计

本文只描述 `neolyst` skill 自身的定位、接口、契约、实现边界与联调要求。`report_maker` 和 `template_maker` 的配套改造，另见 [neolyst_skill_integration.md](/mnt/c/_code/neoskills/docs/codex/neolyst_skill_integration.md)。

## 1. 定位与边界

`neolyst` 是 `neoskills` 中面向 Neolyst 的数据库操作 skill，负责承接所有需要访问和操作 Neolyst 数据库的能力。

`neolyst` 对上游暴露的是稳定的业务接口，不是底层数据库动作集合。它负责认证、文件上传、参数整理、调用 Supabase 暴露的稳定接口，并返回可直接消费的业务结果。

`neolyst` 明确不负责以下事项：

- 与用户对话补字段
- 替上游做业务决策
- 对上游暴露零散的底层数据库动作

## 2. 对外接口

`neolyst` 对外只暴露以下业务接口：

- `resolve_analyst_by_email`
- `resolve_template`
- `upsert_template`
- `reuse_template`
- `resolve_coverage`
- `create_coverage`
- `list_coverage_history`
- `save_draft_report`
- `validate_draft`
- `submit_report`

接口语义如下：

- `resolve_analyst_by_email`：校验并返回标准化后的 analyst 记录，业务主键为 `analyst_email`
- `resolve_template`：解析模板资产
- `upsert_template`：发布主模板
- `reuse_template`：发布共享模板关系
- `resolve_coverage`、`create_coverage`：负责 `coverage` 解析与创建
- `list_coverage_history`：查询指定 coverage 下的已发布历史报告
- `save_draft_report`：保存 draft
- `validate_draft`：校验当前 draft 的当前版本是否可提交
- `submit_report`：提交当前 draft 的当前版本

## 3. 核心契约

### 3.1 draft 与提交契约

- `save_draft_report` 的输入由 `neolyst` 定义并维护，上游依赖该契约
- draft 输入采用全打平结构，业务字段和本地文件路径都位于顶层
- draft 输入不携带执行上下文字段，例如 `workspace_root`、`trace_id`、`server_url_override`、`dry_run`
- `save_draft_report` 的文件输入统一使用本地路径，由 `neolyst` 上传到 Storage
- `report_id` 在首次保存 draft 时为空；后续版本沿用同一个 `report_id`
- draft 契约分为“可保存字段”和“提交前必填字段”两层
- `company` / `company_flash` 在 draft 阶段允许暂时缺少 `coverage_id`，提交前必须补齐
- `contact_person` 在 draft 阶段允许暂时缺少；该字段存储 analyst email
- `report_language` 作为模板选择字段参与 draft 保存
- `analysts`、`coverage_analyst`、`report_analyst` 统一以 `analyst_email` 作为业务键，排序字段统一使用 `author_order`
- `report_file`、`pdf_file`、`model_file` 仅用于上传前定位本地文件；文件路径的唯一准源是 `report_version.word_file_path`、`report_version.pdf_file_path`、`report_version.model_file_path`
- `save_draft_report` 成功时至少返回 `report_id` 和 `version_no`
- `validate_draft` 与 `submit_report` 都以 `report_id + version_no` 为输入

可保存字段的最小集合：

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
- `contact_person`
- `investment_thesis`
- `analysts`
- `report_version.word_file_path`
- `report_version.pdf_file_path`

按类型要求的补充字段：

- `company`：`coverage_id`、`ticker`、`rating`、`target_price`、`report_version.model_file_path`
- `company_flash`：`coverage_id`、`ticker`
- `sector`：`region_code`、`sector_id`
- `sector_flash`：`region_code`、`sector_id`
- `macro`：`region_code`
- `strategy`：`region_code`
- `quantitative`：`region_code`
- `bond`：`region_code`

### 3.2 研报类型与模板契约

- 统一使用 `report_type`，取值为：`company`、`sector`、`company_flash`、`sector_flash`、`macro`、`strategy`、`quantitative`、`bond`
- 模板接口在业务语义上使用 `report_type + language` 做定位
- 实现上以 `{report_type}_{language}` 对应的 `report_template.id` 锁定目标记录；若出现重复记录，应视为数据异常
- `report_template.report_type` 就是报告类型本身，不引入 `template_type`
- 多个 `report_type` 可以共用同一套模板资产
- `reuse_template` 的复用是静态复制，不是动态引用

### 3.3 coverage 与历史查询契约

`resolve_coverage` 的输入为 `ticker` 和 `first_analyst_email`。执行时先按 `ticker` 查询候选 `coverage`，再关联 `coverage_analyst` 过滤出包含该 `first_analyst_email` 的记录。

结果语义如下：

- 命中唯一 `coverage`：返回 `coverage_id`
- 命中多条：抛出无法自动确定的具体错误
- 未命中：抛出需要进入 `create_coverage` 流程的具体错误

`create_coverage` 的输入为创建 `coverage` 所需的完整业务字段，以及初始 `coverage_analyst` 列表。创建成功后返回新的 `coverage_id`。

`list_coverage_history(ticker, first_analyst_email)` 的契约如下：

- coverage 定位逻辑沿用 `resolve_coverage`
- 只返回 `status = 'published'` 的历史报告
- 返回字段固定为：`report_id`、`title`、`rating`、`target_price`、`published_at`
- 结果按 `published_at desc` 排序
- coverage 已找到但没有历史发布记录时返回空列表，不抛错

### 3.4 身份与会话策略

- Neolyst Supabase 的登录身份由 `neolyst` 管理和复用
- 使用 `email + password` 登录
- 账号和密码保存在 `skills/neolyst/user.json`，登录态保存在 `skills/neolyst/session.json`
- `connection.py` 启动时先尝试用 `session.json` 恢复 session；失效后再回退到 `user.json` 重新登录，并只回写 `session.json`
- `user.json` 不存在时，调用方需向用户索取邮箱和密码，使用 `get_client(email=..., password=...)` 完成首次登录；成功后自动写入 `user.json` 与 `session.json`
- 当前库的 RLS 通过 `current_app_role()` 读取 `auth.jwt().app_metadata.role`，按 `admin`、`sa`、`analyst` 做权限控制
- 报告所有者与执行审计均以当前登录身份为准
- `resolve_analyst_by_email` 只用于确定报告分析师身份，不用于决定执行审计用户

## 4. 业务逻辑落点

- 涉及业务数据一致性、状态流转、关系维护、主表/版本表同步的逻辑，优先在 Supabase 侧实现为稳定接口
- 复杂读操作或复杂写操作，默认在 Supabase 侧封装为 RPC / 稳定接口，而不是在 skill 侧拼接多次底层表操作
- `neolyst` skill 主要负责认证、文件上传、参数整理以及调用 Supabase 暴露的接口/函数，不在 skill 侧重复实现核心业务一致性规则

当前实现边界如下：

- `upsert_template` / `reuse_template`：由 Supabase 侧负责锁定目标模板记录并落库
- `save_draft_report`：由 Supabase 侧负责在一次业务接口调用中同步维护 `report`、`report_version`、`report_analyst`
- `submit_report`：通过 RPC 完成状态流转
- `validate_draft`：暂时保留在 Python 侧，以 SELECT 查询完成提交前校验

## 5. 技术设计

### 5.1 技术栈与数据真相

- 使用 Python `supabase-py` 与 Neolyst Supabase 交互，并通过 `uv` 管理依赖与执行环境
- 数据库结构真相以本地 Supabase 实例和 `supabase/migrations/*.sql` 为准

### 5.2 Storage 设计

Storage 使用两个独立 bucket：

- 模板 bucket：`templates`
- 报告 bucket：`reports`

Storage RLS 策略：

- `templates`：所有已认证用户可下载；仅 `admin` 可上传、更新、删除
- `reports`：`admin` 可读写全部；`analyst` 可读写自己 `draft` / `submitted` 状态的报告文件；`sa` 可读 `submitted` / `published` / `rejected` 状态的报告文件

数据库中存储的所有 Storage 路径统一包含 bucket 前缀，格式为 `{bucket}/{path}`。路径规则如下：

- 模板文件：`templates/{report_type}/{language}/template.docx`、`templates/{report_type}/{language}/schema.yaml`
- 报告文件：`reports/{report_id}/v{version_no}/{原始文件名}`

### 5.3 Supabase 连接配置

- Supabase URL 和 anon key 写在 `skills/neolyst/neolyst.yaml` 中，随 skill 一起提交
- `anon_key` 是公开客户端 key，可以提交到版本库
- `neolyst.yaml` 是运行时默认配置，当前仓库版本可以指向 staging，不能视为本地测试默认环境
- 本地测试必须通过 `NEOLYST_URL` 和 `NEOLYST_ANON_KEY` 环境变量覆盖 yaml 中的值
- 测试入口再由 `NEOLYST_TEST_URL` / `NEOLYST_TEST_ANON_KEY` 映射过去，禁止回落到 yaml 默认值

### 5.4 模块拆分

实现层模块如下：

- `connection`
- `storage`
- `analyst`
- `template`
- `coverage`
- `draft_report`
- `validators`
- `submit_report`

目录结构如下：

```text
neolyst/
  SKILL.md
  neolyst.yaml
  user.json
  session.json
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

各模块职责如下：

- `connection.py`：负责凭据读取、session 恢复、重新登录和 client 创建
- `storage.py`：负责模板文件和报告文件上传下载，对外暴露 `upload` 与 `download`
- `analyst.py`：负责 `resolve_analyst_by_email`
- `template.py`：负责 `resolve_template`、`upsert_template`、`reuse_template`
- `coverage.py`：负责 `resolve_coverage` 和 `create_coverage`
- `draft_report.py`：负责 `save_draft_report`
- `validators.py`：负责 `validate_draft`
- `submit_report.py`：负责提交已有 draft，串联连接获取、版本定位、校验和提交 RPC

模块依赖保持单向：

- `draft_report` 可以调用 `connection` 和 `storage`
- `submit_report` 可以调用 `connection` 和 `validators`
- `validators` 可以调用 `connection` 并直接查询相关表
- `template` 可以调用 `connection` 和 `storage`
- `coverage`、`analyst` 与 `storage` 只依赖 `connection`
- `connection` 不依赖任何业务模块

## 6. 关键流程

### 6.1 save_draft_report

`save_draft_report` 接收扁平化 draft 输入，用于保存机器处理后的 draft。保存过程中，本地文件先上传到 Storage，再写入 `report_version.word_file_path`、`report_version.pdf_file_path`、`report_version.model_file_path`。同时同步更新 `report` 主表当前态字段、`current_version_no`，并按当前 `analysts` 列表刷新 `report_analyst`。

成功时至少返回：

```json
{
  "report_id": "uuid",
  "version_no": 1,
  "status": "draft"
}
```

### 6.2 validate_draft

`validate_draft(report_id)` 用于校验当前 draft 的当前版本是否满足提交条件。当前实现保留在 Python 侧，通过只读 SELECT 查询完成。

校验范围包括：

- 结构校验
- 必填字段校验
- 主数据校验
- 公司类报告校验
- 文件路径校验

关键约束包括：

- draft 版本必须存在
- `analysts` 必须为非空列表，且最多支持 8 位分析师
- `analysts[].analyst_email`、`author_order` 必须完整
- `analysts` 中必须恰好存在一位 `author_order = 1`
- `analysts[].author_order` 必须唯一
- 文件路径判定以 `report_version.word_file_path`、`report_version.pdf_file_path`、`report_version.model_file_path` 为准
- `report_type`、`report_language`、`region_code`、`sector_id`、`analysts[].analyst_email` 等主数据必须有效
- `contact_person` 必须属于 `analysts[].analyst_email`

公司类报告额外校验：

- `coverage_id` 必须对应存在的 `coverage`
- `coverage.ticker` 必须与输入 `ticker` 一致
- 报告 `1作 analyst_email` 必须存在于该 `coverage` 的 `coverage_analyst` 列表中
- 对已有 `coverage`，提交时不自动改写 `coverage_analyst`

### 6.3 submit_report

`submit_report` 接收 `report_id` 和 `version_no`，执行顺序如下：

1. 获取已认证的 Neolyst 访问连接
2. 定位 `report_id + version_no` 对应的 draft 版本
3. 再次执行提交前校验
4. 执行提交动作，将报告状态推进到 `submitted`
5. 返回提交结果

提交结果至少包括：

- `report_id`
- `status`
- `version_no`

## 7. 联调与环境

- `neolyst.yaml` 仅作为运行时默认连接配置，当前仓库版本可指向 staging
- 本地测试必须显式提供 `NEOLYST_TEST_URL`、`NEOLYST_TEST_ANON_KEY`、`NEOLYST_TEST_EMAIL`、`NEOLYST_TEST_PASSWORD`
- pytest 启动时会把 `NEOLYST_TEST_URL` / `NEOLYST_TEST_ANON_KEY` 映射到 `NEOLYST_URL` / `NEOLYST_ANON_KEY`

## 8. 后续待做

- Coverage 审批链路。当前设计在用户确认“该 Coverage 已完成审批”后允许 `create_coverage` 直接创建 coverage；后续需要补上首次覆盖场景下的正式审批流程，并与 `resolve_coverage` / `create_coverage` 的调用时机重新收口
