# 接口参考

## 报告生命周期

### save_report

保存或更新报告元数据。不操作文件、不生成版本号。

```python
from skills.neolyst.scripts.report import save_report

result = save_report(client, {
    "report_id": None,          # 首次为 None；后续传已有 report_id
    "report_type": "company",
    "title": "Vertiv: AI demand drives earnings growth",
    "coverage_id": "57ed4bf9-...",
    "ticker": "VRT US",
    "rating": "OUTPERFORM",
    "target_price": 140,
    "report_language": "en",
    "contact_person": "alice@neolyst.com",
    "investment_thesis": "AI-driven demand supports earnings growth.",
    "sector_id": "00000000-0000-0000-0000-000000000019",
    "region_code": "CN",
    "analysts": [
        {"analyst_email": "alice@neolyst.com", "author_order": 1},
        {"analyst_email": "bob@neolyst.com", "author_order": 2},
    ],
    # 以下字段会被自动剥离，不影响 RPC 调用
    "report_file": "/abs/path/report.docx",
    "pdf_file": "/abs/path/report.pdf",
    "model_file": "/abs/path/model.xlsx",
})
# 返回：{"report_id": "uuid"}
```

字段分层：
- 保存最小字段：`title`、`report_type`、`analysts`
- 提交前必须补齐：`contact_person`、`investment_thesis`、`report_language`，以及按类型要求的字段

### upload_report_files

上传 Word + PDF 文件，并回写 `report.word_path` / `report.pdf_path`。

```python
from skills.neolyst.scripts import upload_files

result = upload_files.upload_report_files(
    client,
    report_id="uuid",
    report_file="/abs/path/report.docx",
    pdf_file="/abs/path/report.pdf",
)
# 返回：{"report_id": "uuid", "word_path": "reports/{id}/report/{ts}/report.docx", "pdf_path": "reports/{id}/report/{ts}/report.pdf"}
# 路径前缀由 generate_upload_path RPC 生成，客户端只拼接文件名
```

要求 report 处于 draft 或 rejected 状态。同一报告可多次调用，每次生成新时间戳目录，旧文件保留。

### upload_model_file

上传 Model 文件，并回写 `report.model_path`。

```python
from skills.neolyst.scripts import upload_files

result = upload_files.upload_model_file(
    client,
    report_id="uuid",
    model_file="/abs/path/model.xlsx",
)
# 返回：{"report_id": "uuid", "model_path": "reports/{id}/model/{ts}/model.xlsx"}
```

### validate_report

调用 DB 侧 `validate_report` RPC，校验报告是否满足提交条件。全量收集所有错误后一次性返回。

```python
from skills.neolyst.scripts.report import validate_report

result = validate_report(client, report_id="uuid")
# 通过：返回 {"report_id": "uuid"}
# 失败：抛出 ValueError（消息以"；"分隔所有失败项）
```

只负责校验，不自动补字段、不自动重试、不自动保存。

校验范围：
- report 存在且状态为 draft/rejected
- `word_path` 和 `pdf_path` 非空
- 必填字段：title / report_type / report_language / investment_thesis / contact_person
- 分析师列表非空，且 contact_person 在分析师列表中（大小写不敏感）
- 每个分析师存在且 is_active
- company / company_flash 类型：coverage_id 必填且存在
- sector_id / region_code 有值时验证存在性

### submit_report

将 draft/rejected 报告提交为 `submitted`。

```python
from skills.neolyst.scripts.report import submit_report

result = submit_report(client, report_id="uuid")
# 返回：{"report_id": "uuid", "status": "submitted"}
# RPC 内部调用 validate_report 做字段守门，字段不完整时抛出 ValueError
# 如需提前获取全量错误展示，先显式调用 validate_report(client, report_id="uuid")
```

### retract_report

将 submitted/rejected 报告撤回为 draft。

```python
from skills.neolyst.scripts.report import retract_report

result = retract_report(client, report_id="uuid")
# 返回：{"report_id": str, "status": "draft"}
# 报告不存在或非 submitted/rejected 状态：抛出 ValueError
```

- 撤回后报告回到 draft 状态，可重新编辑和提交
- `report_status_log` 由数据库触发器自动记录

### publish_report

将 submitted 报告发布为 published。

```python
from skills.neolyst.scripts.report import publish_report

result = publish_report(client, report_id)
# 返回：{"report_id": str, "status": "published"}
# 报告不存在或非 submitted 状态：抛出 ValueError
```

- 自动记录 `published_by`（当前用户）和 `published_at`（当前时间）
- 仅 SA 或 admin 角色可执行

### reject_report

将 submitted 报告退回为 rejected。

```python
from skills.neolyst.scripts.report import reject_report

result = reject_report(client, report_id, reason="数据不完整，请补充")
# 返回：{"report_id": str, "status": "rejected"}
# 退回原因为空：抛出 ValueError
# 报告不存在或非 submitted 状态：抛出 ValueError
```

- `reason`：退回原因，必填
- 仅 SA 或 admin 角色可执行

### deactivate_report

将报告标记为废弃（is_active = false），不影响 status 状态机。

```python
from skills.neolyst.scripts.report import deactivate_report

result = deactivate_report(client, report_id)
# 返回：{"report_id": str, "is_active": False}
# 报告不存在：抛出 ValueError（"报告不存在：{report_id}"）
# 报告已废弃：抛出 ValueError（"报告已废弃：{report_id}"）
```

- 直接查表 update，不走 RPC
- admin only（受 report 表 RLS 约束）
- 废弃后查询报告需加 `.eq("is_active", True)` 过滤

## Coverage

### resolve_coverage

按 `ticker` 查询 coverage，并验证 `first_analyst_email` 在该 coverage 的分析师列表中。

```python
from skills.neolyst.scripts import coverage

coverage_id = coverage.resolve_coverage(client, ticker="VRT US", first_analyst_email="alice@neolyst.com")
# 命中唯一：返回 str（coverage.id UUID）
# 未命中：抛出 ValueError，由调用方决定后续处理
# 命中多条：抛出 ValueError（无法自动确定）
```

只读操作。不修改数据库，不自动创建 coverage。

### create_coverage

创建新的 coverage 记录及初始 `coverage_analyst` 关系。

```python
coverage_id = coverage.create_coverage(
    client,
    ticker="VRT US",
    english_name="Vertiv Holdings Co",
    sector_id="00000000-0000-0000-0000-000000000019",
    isin="US92537N1081",
    country_of_domicile="United States",
    analysts=[
        {"analyst_email": "alice@neolyst.com", "author_order": 1},
        {"analyst_email": "bob@neolyst.com", "author_order": 2},
    ],
    chinese_name="威图科技",          # 可选
    traditional_chinese="威圖科技",   # 可选
)
# 返回：str（新创建的 coverage.id UUID）
```

必填字段：`ticker`、`english_name`、`sector_id`、`isin`、`country_of_domicile`。初始 `coverage_analyst` 与报告分析师列表一致（最多 8 人，必须包含 `author_order=1` 的第一作者）。显式创建接口，仅在 `resolve_coverage` 未命中且用户确认"Coverage 已完成审批"后调用。

### list_coverage_history

按 `ticker + first_analyst_email` 定位唯一 coverage，返回该 coverage 下所有已发布历史报告。

```python
from skills.neolyst.scripts import coverage

rows = coverage.list_coverage_history(
    client,
    ticker="VRT US",
    first_analyst_email="alice@neolyst.com",
)
# 返回：
# [
#   {
#     "report_id": "uuid",
#     "title": "Vertiv: AI demand drives earnings growth",
#     "rating": "OUTPERFORM",
#     "target_price": 140,
#     "published_at": "2026-04-09T08:00:00+00:00",
#   },
#   ...
# ]
# 按 published_at desc 排序
# coverage 找不到：抛出 ValueError
# coverage 找到但没有已发布历史：返回 []
```

## 分析师

### resolve_analyst_by_email

按邮箱查询 analyst 记录（直接查表，非 RPC）。

```python
from skills.neolyst.scripts import analyst

record = analyst.resolve_analyst_by_email(client, "alice@neolyst.com")
# 返回：dict，含 email, english_name, chinese_name, suffix, sfc, region_code, is_active, created_at, updated_at
# 找不到或已停用：抛出 ValueError（含具体原因）
```

- Python 侧做 `strip().lower()` 标准化
- `is_active=False` 的分析师抛出 `ValueError: 分析师已停用：{email}`

### search_analyst_by_name

按姓名模糊查询活跃分析师，返回精简字段（直接查表）。

```python
from skills.neolyst.scripts import analyst

results = analyst.search_analyst_by_name(client, "Alice")
# 返回：[{"email": "alice@neolyst.com", "english_name": "Alice Chen", "chinese_name": "陈小明"}, ...]
# 无匹配：返回 []
```

- 同时匹配 `english_name` 和 `chinese_name`（ilike 模糊匹配）
- 只返回 `is_active=True` 的分析师
- 返回字段：`email`、`english_name`、`chinese_name`
- `name` 中的 `%` 和 `_` 在 Python 侧 escape，防止通配符注入
- 受 `dict_select` RLS 约束，所有认证用户可调用

### upsert_analyst

以 email 为键创建或更新分析师记录（需 admin 角色）。

```python
from skills.neolyst.scripts import analyst

record = analyst.upsert_analyst(
    client,
    email="alice@neolyst.com",
    english_name="Alice Chen",
    chinese_name="陈小明",
    suffix="CFA",
    sfc="S12345",
    region_code="CN",
)
# 返回：dict，完整 analyst 记录（含 email, english_name, chinese_name, suffix, sfc, region_code, is_active, created_at, updated_at）
```

- email 自动做 `strip().lower()` 标准化
- 已存在时更新，不存在时创建
- 受 `dict_write` RLS 约束，仅 admin 角色可执行

### set_analyst_active

更新分析师的在职状态（需 admin 角色）。

```python
from skills.neolyst.scripts import analyst

record = analyst.set_analyst_active(client, "alice@neolyst.com", is_active=False)
# 返回：dict，更新后的完整 analyst 记录
# 邮箱不存在：抛出 ValueError（"找不到分析师：{email}"）
```

- email 自动做 `strip().lower()` 标准化
- 受 `dict_write` RLS 约束，仅 admin 角色可执行

## 模板

### resolve_template

按 `report_type + language` 查询模板记录，将模板文件和 schema 下载到本地并返回路径。

```python
from skills.neolyst.scripts import template

result = template.resolve_template(client, report_type="company", language="en")
# 返回：{"template_local_path": "...", "schema_local_path": str | None}
# 找不到模板或路径为空：抛出 ValueError
```

- `dest_dir`：下载根目录，默认 `"."`，文件落在 `{dest_dir}/templates/{report_type}/{language}/`
- 本地文件名为 `template.docx` 和 `schema.yaml`（与 bucket 中路径一致）
- `schema_local_path` 在 schema 不存在或下载失败时返回 `None`

### upsert_template

上传本地模板文件到 Storage，并写入/更新对应的 `report_template` 记录。

```python
template.upsert_template(
    client,
    report_type="company",
    language="en",
    template_local_path="/abs/path/template.docx",
    schema_local_path="/abs/path/schema.yaml",  # 可选，默认 None
)
# 返回：None。幂等操作，多次调用安全。
```

执行顺序：
1. 调用 RPC `get_template_storage_paths(report_type, language)` 获取 Storage 目标路径
2. 将本地文件上传到返回的路径
3. 调用 RPC `upsert_template_record(report_type, language)` upsert 记录

### reuse_template

让某个 `report_type` 的模板记录静态复制另一个 `report_type` 的文件路径（共用模板资产）。

```python
template.reuse_template(
    client,
    report_type="quantitative",
    language="en",
    same_as_report_type="macro",
)
# 返回：None
# 必须先通过 upsert_template 发布源模板
# 失败场景（抛出 ValueError）：源模板不存在、report_type 复用自己
```

若主模板重新上传并变更路径，需重新执行 `reuse_template` 才能同步。

## 错误处理策略

调用接口遇到 ValueError 时，不要直接把异常信息抛给用户。根据场景采取以下策略：

### resolve_coverage 未命中

报错内容："未找到匹配的 Coverage"

→ 向用户说明该 ticker + 分析师组合没有对应 coverage，询问是否需要创建。只有当用户明确确认"Coverage 已完成审批"后才调用 `create_coverage`。不要自动创建。

### resolve_analyst_by_email 找不到或已停用

报错内容："找不到分析师" 或 "分析师已停用"

→ 提示用户检查邮箱拼写是否正确。如果邮箱无误但报 inactive，说明该分析师账号已被停用，需要联系管理员恢复。不要尝试用其他邮箱绕过。

### validate_report 校验失败

报错内容：多条错误以"；"分隔

→ 将错误逐条展示给用户，明确指出缺什么字段、哪个条件不满足。用户修正后，重新调用 `save_report`（传入相同 report_id）更新元数据，再 `upload_report_files` 更新文件，然后重新 validate。不要尝试自动补字段。

### save_report 失败

常见原因：title 为 None（NOT NULL 违规）、analysts 为空、RPC 内部校验不通过。

→ 将具体错误信息展示给用户，让用户补充缺失信息后重试。

### submit_report 失败

常见原因：报告状态不是 draft/rejected、word_path 或 pdf_path 为空。

→ 如果是路径为空，说明需要先调用 `upload_report_files` 上传文件。如果是状态不对，说明该报告已提交过，无需重复操作。

### 认证失败

报错内容："No valid session and no credentials" 或 "Authentication failed"

→ 向用户索取邮箱和密码，调用 `get_client(email=..., password=...)` 重新认证。不要尝试从其他来源猜测凭据。
