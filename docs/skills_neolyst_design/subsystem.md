# neolyst Skill 子系统实现文档

neolyst 子系统的实现细节与接口契约。整体规则见 [global.md](./global.md)。

## 1. 设计决策

### 1.1 身份与会话实现（原 §2.4）

身份与权限全局规则见 [global.md §4](./global.md)。本节记录实现细节。

- 使用 `email + password` 登录。账号和密码保存在 skill 根目录（`skills/neolyst/`）的 `user.json`；登录态保存在同目录的 `session.json`。两者都不提交到版本库。
- `connection.py` 启动时先尝试用 `session.json` 中的 `access_token` + `refresh_token` 恢复 session；若已过期或失效，则回退到 `user.json` 中的 `email + password` 重新登录，并只回写 `session.json`。
- `user.json` 不存在时，调用方需向用户索取邮箱和密码，使用 `get_client(email=..., password=...)` 完成首次登录。成功后自动写入 `user.json` 与 `session.json`，后续无需再次手动输入。

### 1.2 技术访问方式（原 §2.6）

- 本 skill 使用 Python `supabase-py` 与 Neolyst Supabase 交互，并通过 `uv` 管理依赖与执行环境。
- 数据库结构真相以本地 Supabase 实例和 `supabase/migrations/*.sql` 为准；本设计文档需要与它们保持同步。
- Storage 全局规则（bucket 与 RLS）见 [global.md §4.3](./global.md)。本节记录路径实现细节。
- 模板 bucket 路径规则：`templates/{report_type}/{language}/template.docx` 和 `templates/{report_type}/{language}/schema.yaml`。`template_file_path` / `schema_file_path` 字段存储含 bucket 前缀的完整路径；路径由 Supabase RPC `get_template_storage_paths` 统一生成，`storage.py` 只负责上传/下载。
- 报告 bucket 路径规则：`reports/{report_id}/v{version_no}/{原始文件名}`。路径由 `draft_report.py` 在调用 draft 保存 RPC 前生成，文件名保留调用方传入的原始文件名（`Path(local_path).name`），版本间文件存储在独立目录下互不覆盖。
- `resolve_template(client, report_type, language, dest_dir=".")` 将模板文件下载到 `dest_dir/templates/{report_type}/{language}/` 下，文件名与 bucket 中一致（`template.docx`、`schema.yaml`）。

### 1.3 Supabase 连接配置（原 §2.7）

- Supabase URL 和 anon key 由 skill 负责确定，写在 `skills/neolyst/neolyst.yaml` 中，随 skill 一起提交到版本库。anon key 是公开的客户端 key，不是密钥，可以安全提交。
- `neolyst.yaml` 格式：`supabase_url: "..."` 和 `anon_key: "..."`。
- `neolyst.yaml` 是运行时默认配置，当前仓库版本可以指向 staging，不能视为本地测试默认环境。
- 本地测试必须通过 `NEOLYST_URL` 和 `NEOLYST_ANON_KEY` 环境变量覆盖 yaml 中的值；测试入口再由 `NEOLYST_TEST_URL` / `NEOLYST_TEST_ANON_KEY` 映射过去，禁止回落到 yaml 默认值。

### 1.4 接口清单（原 §2.1）

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

### 1.5 接口契约（原 §2.2 部分内容 + §2.3 部分内容 + §2.5 部分内容）

- draft 输入采用全打平结构，业务字段和本地文件路径都位于顶层。
- draft 输入不携带执行上下文字段，例如 `workspace_root`、`trace_id`、`server_url_override`、`dry_run`。
- `save_draft_report` 的文件输入统一使用本地路径，由 `neolyst` 上传到 Storage。
- `company` / `company_flash` 在 draft 阶段允许暂时缺少 `coverage_id`，提交前必须补齐。
- `contact_person` 在 draft 阶段允许暂时缺少；该字段存储 analyst email，提交前必须由 `report_maker` 负责确认和填充。
- `report_language` 作为模板选择字段，由 `report_maker` 自动识别并向用户确认后写入 draft。
- `save_draft_report` 输入中的 `report_file`、`pdf_file`、`model_file` 仅用于上传前定位本地文件；文件路径的唯一准源是 `report_version.word_file_path`、`report_version.pdf_file_path`、`report_version.model_file_path`。`snapshot_json` 如保留文件字段，只作为版本快照，不作为校验和提交的判定来源。
- `save_draft_report` 成功时至少返回 `report_id` 和 `version_no`。
- `save_draft_report` 不要求当前版本已经满足最终提交条件。
- `submit_report` 仅负责将已有 draft 推进到 `submitted`。

### 1.6 校验与错误语义（原 §2.9）

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

### 1.7 Coverage 历史查询（原 §6 部分内容）

- 新增 `list_coverage_history(ticker, first_analyst_email)` 能力，面向"报告尚未写完、只有 ticker 和 1作信息"的前置查询场景。
- coverage 的定位逻辑沿用现有 `resolve_coverage`：按 `ticker + coverage_analyst.analyst_email` 命中唯一 coverage。
- 只返回 `status = 'published'` 的历史报告；`submitted`、`draft`、`rejected` 均不纳入结果。
- 返回字段固定为：`report_id`、`title`、`rating`、`target_price`、`published_at`。
- 结果按 `published_at desc` 排序。
- coverage 已找到但没有历史发布记录时返回空列表，不抛错。
- 该读取带业务判定，按仓库约定下沉到 Supabase RPC；Python 侧只做参数整理和调用。

## 2. 实现落地（原 §3）

### 2.1 resolve_coverage 执行流程（原 §3.1）

`resolve_coverage` 的输入为 `ticker` 和 `first_analyst_email`。执行时先按 `ticker` 查询候选 `coverage`，再关联 `coverage_analyst` 过滤出包含该 `first_analyst_email` 的记录。只要该分析师出现在某条 `coverage` 的分析师列表中，就视为命中，不要求其在 `coverage_analyst` 中维护额外角色字段。

命中唯一 `coverage` 时返回 `coverage_id`；命中多条时抛出"无法自动确定"的具体错误；未命中时抛出"需要进入 create_coverage 流程"的具体错误。

`resolve_coverage` 只负责解析和确认 `coverage_id`，不修改数据库，也不承担补数据或自动创建逻辑。

`resolve_coverage` 的候选查询、分析师关联过滤和唯一性判定优先在 Supabase 侧通过 RPC / 稳定接口实现；skill 侧负责组织输入并调用该接口。

### 2.2 create_coverage 执行流程（原 §3.2）

`create_coverage` 的输入为创建 `coverage` 所需的完整业务字段，以及初始 `coverage_analyst` 列表。创建 `coverage` 时至少写入 `ticker`、`english_name`、`sector_id`、`isin`、`country_of_domicile`；如已具备中文信息，可同时写入 `chinese_name` 和 `traditional_chinese`。随后再写入对应的 `coverage_analyst` 关系。

初始 `coverage_analyst` 与本次报告分析师列表保持一致，最多支持 8 位分析师，其中必须包含报告 `1作 analyst_email`。分析师排序统一写入 `author_order`，其中 `author_order = 1` 代表报告 1 作。创建成功后返回新的 `coverage_id`，供上游写回当前 draft。

`create_coverage` 是显式创建接口，不由 `submit_report` 隐式触发。只有在 `resolve_coverage` 未命中，且上游已经与用户确认"该 Coverage 已完成审批"后，才进入 `create_coverage`。失败时直接抛出具体错误。

`create_coverage` 的主数据写入、一致性校验和 `coverage_analyst` 关系创建优先在 Supabase 侧通过 RPC / 稳定接口实现；skill 侧负责参数整理并调用该接口。

### 2.3 save_draft_report 执行流程（原 §3.3）

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

### 2.4 validate_draft 执行流程（原 §3.4）

`validate_draft` 只接收 `report_id`，用于判断该报告当前版本是否满足进入 `submit_report` 的条件。实际被校验的版本由 `report.current_version_no` 决定；校验通过时返回真实 `version_no`。

当前实现的校验范围如下：

- `report` 存在，且 `status` 为 `draft` 或 `rejected`
- `report.current_version_no > 0`，且对应的 `report_version` 行存在
- `report_version.word_file_path` 与 `report_version.pdf_file_path` 非空
- 必填字段：`title`、`report_type`、`report_language`、`investment_thesis`、`contact_person`
- `report_analyst` 至少存在 1 位分析师，且 `contact_person` 必须属于当前报告分析师列表（大小写不敏感）
- 每位分析师都必须在 `analyst` 表中存在且 `is_active = true`
- `company` 类型必须存在有效 `coverage_id`
- `sector_id` / `region_code` 有值时，需分别命中有效 `sector` / `region`

结果语义：

- 校验通过：返回被校验通过的 `report_id` 和 `version_no`
- 校验失败：全量收集错误后一次性抛出具体错误

`validate_draft` 当前由 `skills/neolyst/scripts/validators.py` 提供实现。它负责字段完整性判断、主数据校验和版本一致性校验，但不负责状态流转，也不负责写库。

### 2.5 submit_report 执行流程（原 §3.5）

`submit_report` 只接收 `report_id`，用于提交 `report.current_version_no` 指向的当前版本。若调用方需要完整字段校验，应先显式调用 `validate_draft(report_id)`；`submit_report` 自身不在 Python 侧重复校验。

执行顺序：

1. 获取已认证的 Neolyst 访问连接
2. 调用 Supabase RPC `submit_report(p_report_id)`
3. RPC 校验报告存在、状态为 `draft` / `rejected`、`current_version_no > 0`，且当前版本行存在
4. RPC 执行提交动作，将报告状态推进到 `submitted`，并将真实版本号写入 `report_status_log`
5. 返回提交结果

提交结果至少包括：

- `report_id`
- `status`
- `version_no`

`submit_report` 不负责隐式创建 `coverage`，也不负责补字段或做人机交互。执行失败时直接抛出具体错误。

### 2.6 模块拆分（原 §3.6）

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
- `resolve_template` 直接查询 `report_template` 表读取 `template_file_path` / `schema_file_path`（无业务逻辑，不需要 RPC），再将文件下载到 `dest_dir/templates/{report_type}/{language}/` 目录

`coverage.py` 负责 `resolve_coverage` 和 `create_coverage`。凡是与 `coverage`、`coverage_analyst` 相关的查询和写入都通过该模块调用 Supabase 侧对应 RPC / 稳定接口完成。

`draft_report.py` 负责 `save_draft_report`，处理 draft 版本创建、文件上传和调用 Supabase 侧 draft 保存 RPC。

`validators.py` 模块对外暴露的业务接口名是 `validate_draft`。当前实现直接查询 `report`、`report_version`、`report_analyst`、`analyst`、`coverage`、`sector`、`region` 等表完成提交前校验，不调用 RPC，也不执行提交。

`submit_report.py` 负责提交已有 draft，直接调用 Supabase 侧提交 RPC。当前版本定位、最低一致性保护、状态流转和提交审计都在 RPC 侧完成；`report` 主表当前态字段和 `current_version_no` 已由 `save_draft_report` 在保存 draft 时同步更新。

模块之间的依赖关系保持单向：`draft_report` 可以调用 `connection` 和 `storage`；`submit_report` 只依赖 `connection`；`validators` 可以调用 `connection` 并直接查询相关表；`template` 可以调用 `connection` 和 `storage`；`coverage`、`analyst` 与 `storage` 只依赖 `connection`；`connection` 不依赖任何业务模块。

## 3. 联调与环境（原 §4）

### 3.1 联调测试环境

- `neolyst.yaml` 仅作为运行时默认连接配置，当前仓库版本可指向 staging
- 本地测试必须显式提供 `NEOLYST_TEST_URL`、`NEOLYST_TEST_ANON_KEY`、`NEOLYST_TEST_EMAIL`、`NEOLYST_TEST_PASSWORD`
- pytest 启动时会把 `NEOLYST_TEST_URL` / `NEOLYST_TEST_ANON_KEY` 映射到 `NEOLYST_URL` / `NEOLYST_ANON_KEY`，确保测试不会回落到 `neolyst.yaml`
