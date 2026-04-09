---
name: neolyst
description: "Neolyst Supabase 数据访问层。当你需要操作 Neolyst 平台数据库时——无论是查询分析师信息、解析或上传模板、管理 coverage、保存报告草稿、校验或提交报告——必须使用此 skill，绝不能自行构造原始 Supabase 查询。触发场景包括但不限于：调用方提到 analyst 邮箱查询、模板同步、coverage 创建、draft 保存、报告提交、或任何需要读写 Neolyst 数据库的操作。"
---

# neolyst

Neolyst 平台的 Supabase 访问层。封装所有业务接口，供 `report_maker`、`template_maker` 等 skill 调用。

**实现位置：** `skills/neolyst/scripts/`

---

## 认证：获取 client

所有接口都需要先拿到已认证的 Supabase client。

```python
from skills.neolyst.scripts import connection

client = connection.get_client()
```

### 配置文件（随 skill 发布，非敏感，已提交到仓库）

`skills/neolyst/neolyst.yaml` — Supabase 连接配置：

```yaml
supabase_url: "http://127.0.0.1:54321"   # 本地 Supabase 服务地址
anon_key: "eyJhbG..."                     # Supabase anon/publishable key（非密钥）
```

anon key 是公开的客户端 key，不是敏感信息，可以安全提交到版本库。

### 凭据文件（本地保存，不提交）

`skills/neolyst/user.json` — 用户登录凭据及 session token：

```json
{
  "email": "user@example.com",
  "password": "...",
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "expires_at": 1712345678
}
```

### 首次使用：询问并记录凭据

**如果 `skills/neolyst/user.json` 文件不存在**，说明用户尚未登录过。此时必须：

1. 告知用户需要 Neolyst 账号凭据（邮箱 + 密码）
2. 向用户请求邮箱和密码
3. 调用 `get_client(email=..., password=...)` 完成首次登录
4. 登录成功后凭据自动保存到 `skills/neolyst/user.json`，后续调用无需再次输入

```python
# 首次登录示例
client = connection.get_client(email="user@neolyst.com", password="your_password")
```

### Session 自动管理

`get_client` 的完整认证顺序：
1. 读取 `user.json`，用 `access_token` 恢复 session
2. token 过期时自动用 `refresh_token` 刷新，回写文件
3. refresh 失败时用文件里存的 `email + password` 重新登录，回写文件
4. 以上均失败（凭据无效、账号不存在等）→ 抛出 `ValueError`，**此时必须向用户索取邮箱和密码**，再调用 `get_client(email=..., password=...)`

**access token 有效期约 1 小时**，refresh token 随之轮换。长时间不用后需要重新登录属于正常现象。

---

## 接口

### 1. resolve_analyst_by_email ✅ 已实现

根据邮箱查询并返回标准化的 analyst 记录。

```python
from skills.neolyst.scripts import analyst

record = analyst.resolve_analyst_by_email(client, "alice@neolyst.com")
# 返回：dict，含 email, english_name, chinese_name, suffix, sfc, region_code, is_active
# 找不到或已停用：抛出 ValueError（含具体原因）
```

- 邮箱大小写不敏感，内部统一 lowercase
- `is_active=False` 的分析师会抛出 `ValueError: 分析师已停用`
- 业务主键是 `email`，无 `id` 字段

---

### 2. resolve_template ✅ 已实现

按 `report_type + language` 查询模板记录，将模板文件和 schema 下载到本地并返回路径。

```python
from skills.neolyst.scripts import template

result = template.resolve_template(client, report_type="company", language="en")
# 返回：{"template_local_path": "...", "schema_local_path": "..."}
# 找不到模板或路径为空：抛出 ValueError
```

---

### 3. upsert_template ✅ 已实现

上传本地模板文件到 Storage，并写入/更新对应的 `report_template` 记录。

```python
template.upsert_template(
    client,
    report_type="company",
    language="en",
    template_local_path="/abs/path/template.docx",
    schema_local_path="/abs/path/schema.yaml",
)
# 返回：None。幂等操作，多次调用安全。
```

---

### 4. reuse_template ✅ 已实现

让某个 `report_type` 的模板记录静态复制另一个 `report_type` 的文件路径（共用模板资产）。

```python
template.reuse_template(
    client,
    report_type="quantitative",
    language="en",
    same_as_report_type="macro",
)
# 返回：None
# 注意：必须先通过 upsert_template 发布源模板，才能调用 reuse_template
# 失败场景（直接抛出 ValueError）：源模板不存在、language 不一致、report_type 复用自己
```

---

### 5. resolve_coverage ✅ 已实现

按 `ticker` 查询 coverage，并验证 `first_analyst_email` 在该 coverage 的分析师列表中。

```python
from skills.neolyst.scripts import coverage

coverage_id = coverage.resolve_coverage(client, ticker="VRT US", first_analyst_email="alice@neolyst.com")
# 命中唯一：返回 str（coverage.id UUID）
# 未命中：抛出 ValueError（需进入 create_coverage 流程）
# 命中多条：抛出 ValueError（无法自动确定）
```

---

### 6. create_coverage ✅ 已实现

创建新的 coverage 记录及初始 `coverage_analyst` 关系。

```python
coverage_id = coverage.create_coverage(
    client,
    ticker="VRT US",
    english_name="Vertiv Holdings Co",
    sector_id="00000000-0000-0000-0000-000000000019",  # Electronics
    isin="US92537N1081",
    country_of_domicile="United States",
    analysts=[
        {"analyst_email": "alice@neolyst.com", "author_order": 1},
        {"analyst_email": "bob@neolyst.com", "author_order": 2},
    ],
    # 可选
    chinese_name="威图科技",
    traditional_chinese="威圖科技",
)
# 返回：str（新创建的 coverage.id UUID）
# 必须先经过 resolve_coverage 未命中，且用户已确认"该 Coverage 已完成审批"，才可调用
```

---

### 7. save_draft_report ✅ 已实现

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

报告文件存储路径：`reports/{report_id}/v{version_no}/{原始文件名}`，各版本独立目录，不互相覆盖。

**字段分层：**
- 保存 draft 最小字段：`title`、`report_type`、`report_language`、`analysts`、`report_file`、`pdf_file`
- 提交前必须补齐：`contact_person`、`investment_thesis`，以及按类型要求的字段（见 validators）

---

### 8. validate_draft ✅ 已实现

校验指定 draft 版本是否满足提交条件。全量收集所有错误后一次性抛出。

```python
from skills.neolyst.scripts.validators import validate_draft

result = validate_draft(client, report_id="uuid", version_no=1)
# 通过：返回 {"report_id": "uuid", "version_no": 1}
# 失败：抛出 ValueError（消息以"；"分隔所有失败项，足以让调用方据此补字段）
```

**校验内容：** report 存在且状态为 draft/rejected、版本存在、word/pdf 文件路径非空、必填字段（title/report_type/report_language/investment_thesis/contact_person）、分析师列表非空且 contact_person 在内、每个分析师存在且 is_active、company 类型必须有 coverage_id 且存在、sector_id/region_code 有值时验证存在性。

---

### 9. submit_report ✅ 已实现

将已校验的 draft/rejected 版本提交为 `submitted` 状态。

```python
from skills.neolyst.scripts import submit_report

result = submit_report.submit_report(client, report_id="uuid", version_no=1)
# 返回：{"report_id": "uuid", "status": "submitted", "version_no": 1}
# 内部先调用 validate_draft，校验失败则抛出异常
# 成功后原子更新 report.status 并写入 report_status_log
```

---

## 错误处理

所有接口在失败时直接抛出具体异常，错误信息必须足够明确，让调用方知道如何处置：

| 场景 | 异常类型 |
|------|---------|
| 记录不存在 | `ValueError`，含缺失的标识符 |
| 分析师已停用 | `ValueError: 分析师已停用` |
| 模板数据异常（重复记录） | `ValueError`，说明重复情况 |
| Coverage 未命中 | `ValueError`，含"未找到匹配的 Coverage"，提示创建 |
| Coverage ticker/isin 重复 | `ValueError`，含"Coverage 已存在" |
| 提交前校验失败 | `ValueError`，列出所有失败字段 |
| 文件不存在 | `FileNotFoundError` |
| token 过期 | 自动处理（refresh → re-login），对调用方透明 |

---

## 业务约束（调用方须知）

- `save_draft_report` 的 `report_id` 首次为 `None`，后续版本传已有 ID，沿用同一 report 追加版本
- `create_coverage` 只能在 `resolve_coverage` 未命中、且用户已确认"Coverage 已完成审批"后才调用
- `submit_report` 之前必须先通过 `validators`
- `reuse_template` 的复用是静态路径复制；主模板重新上传后需重新执行一次 `reuse_template`
- `contact_person` 必须属于本次报告的 `analysts[].analyst_email`
