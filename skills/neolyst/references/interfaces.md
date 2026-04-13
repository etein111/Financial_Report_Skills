# 接口参考

## 1. resolve_analyst_by_email

按邮箱查询并返回标准化的 analyst 记录。

```python
from skills.neolyst.scripts import analyst

record = analyst.resolve_analyst_by_email(client, "alice@neolyst.com")
# 返回：dict，含 email, english_name, chinese_name, suffix, sfc, region_code, is_active, created_at, updated_at
# 找不到或已停用：抛出 ValueError（含具体原因）
```

- 邮箱大小写不敏感，内部统一 lowercase
- `is_active=False` 的分析师抛出 `ValueError: Analyst is inactive: {email}`

## 2. resolve_template

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

## 3. upsert_template

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

## 4. reuse_template

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

## 5. resolve_coverage

按 `ticker` 查询 coverage，并验证 `first_analyst_email` 在该 coverage 的分析师列表中。

```python
from skills.neolyst.scripts import coverage

coverage_id = coverage.resolve_coverage(client, ticker="VRT US", first_analyst_email="alice@neolyst.com")
# 命中唯一：返回 str（coverage.id UUID）
# 未命中：抛出 ValueError，由调用方决定后续处理
# 命中多条：抛出 ValueError（无法自动确定）
```

只读操作。不修改数据库，不自动创建 coverage。

## 6. create_coverage

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

## 7. save_draft_report

保存机器处理后的 draft 版本。上传本地文件到 Storage，写入 `report` / `report_version` / `report_analyst`。

```python
from skills.neolyst.scripts import draft_report

result = draft_report.save_draft_report(client, {
    "report_id": None,          # 首次保存为 None；后续版本传已有 report_id
    "report_type": "company",
    "title": "Vertiv: AI demand drives earnings growth",
    "coverage_id": "57ed4bf9-...",
    "ticker": "VRT US",
    "rating": "OUTPERFORM",
    "target_price": 140,
    "report_language": "en",
    "contact_person": "alice@neolyst.com",
    "investment_thesis": "AI-driven demand supports earnings growth.",
    "sector_id": "00000000-0000-0000-0000-000000000019",    # 可选
    "region_code": "CN",                                    # 可选
    "analysts": [
        {"analyst_email": "alice@neolyst.com", "author_order": 1},
        {"analyst_email": "bob@neolyst.com", "author_order": 2},
    ],
    "report_file": "/abs/path/report.docx",
    "pdf_file": "/abs/path/report.pdf",
    "model_file": "/abs/path/model.xlsx",   # 公司类报告必填
})
# 返回：{"report_id": "uuid", "version_no": 1, "status": "draft"}
# 不要求当前版本满足最终提交条件
```

报告文件存储路径：`reports/{report_id}/v{version_no}/{原始文件名}`，各版本独立目录。

字段分层：
- 保存 draft 最小字段：`title`、`report_type`、`report_language`、`analysts`、`report_file`、`pdf_file`
- 提交前必须补齐：`contact_person`、`investment_thesis`，以及按类型要求的字段（见 `validate_report`）

## 8. validate_report

调用 DB 侧 `validate_report` RPC，校验报告当前版本是否满足提交条件。全量收集所有错误后一次性返回。

```python
from skills.neolyst.scripts.validators import validate_report

result = validate_report(client, report_id="uuid")
# 通过：返回 {"report_id": "uuid", "version_no": 1}
# 失败：抛出 ValueError（消息以"；"分隔所有失败项）
```

只负责校验，不自动补字段、不自动重试、不自动保存 draft。

当前版本由 `report.current_version_no` 决定。

校验范围：
- report 存在且状态为 draft/rejected
- `report.current_version_no` 大于 0，且当前版本存在
- word/pdf 文件路径非空
- 必填字段：title / report_type / report_language / investment_thesis / contact_person
- 分析师列表非空，且 contact_person 在分析师列表中（大小写不敏感）
- 每个分析师存在且 is_active
- company / company_flash 类型：coverage_id 必填且存在
- sector_id / region_code 有值时验证存在性

## 9. submit_report

将当前 draft/rejected 版本提交为 `submitted`。

```python
from skills.neolyst.scripts import submit_report

result = submit_report.submit_report(client, report_id="uuid")
# 返回：{"report_id": "uuid", "status": "submitted", "version_no": 1}
# RPC 内部调用 validate_report 做字段守门，字段不完整时抛出 ValueError
# 如需提前获取全量错误展示，先显式调用 validate_report(client, report_id="uuid")
# 数据库 RPC 内部读取 report.current_version_no，并返回真实提交版本
```

## 10. list_coverage_history

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

## 错误处理策略

调用接口遇到 ValueError 时，不要直接把异常信息抛给用户。根据场景采取以下策略：

### resolve_coverage 未命中

报错内容："未找到匹配的 Coverage"

→ 向用户说明该 ticker + 分析师组合没有对应 coverage，询问是否需要创建。只有当用户明确确认"Coverage 已完成审批"后才调用 `create_coverage`。不要自动创建。

### resolve_analyst_by_email 找不到或已停用

报错内容："找不到分析师" 或 "Analyst is inactive"

→ 提示用户检查邮箱拼写是否正确。如果邮箱无误但报 inactive，说明该分析师账号已被停用，需要联系管理员恢复。不要尝试用其他邮箱绕过。

### validate_report 校验失败

报错内容：多条错误以"；"分隔

→ 将错误逐条展示给用户，明确指出缺什么字段、哪个条件不满足。用户修正后，重新调用 `save_draft_report`（传入相同 report_id）追加新版本，再重新 validate。不要尝试自动补字段。

### save_draft_report 失败

常见原因：title 为 None（NOT NULL 违规）、analysts 为空、RPC 内部校验不通过。

→ 将具体错误信息展示给用户，让用户补充缺失信息后重试。

### submit_report 失败

常见原因：报告状态不是 draft/rejected、当前没有可提交版本。

→ 如果是"当前没有可提交版本"，说明需要先 `save_draft_report` 保存内容。如果是状态不对，说明该报告已提交过，无需重复操作。

### 认证失败

报错内容："No valid session and no credentials" 或 "Authentication failed"

→ 向用户索取邮箱和密码，调用 `get_client(email=..., password=...)` 重新认证。不要尝试从其他来源猜测凭据。
