---
name: neolyst
description: "当其他 skill（如 report_maker）需要访问 Neolyst Supabase 数据库时调用此技能。负责读取分析师、模板、coverage 信息，保存 draft 报告，校验和提交报告。凡是涉及 Neolyst 平台数据库操作（analyst 查询、模板同步、coverage 管理、报告保存/提交）时，必须使用此技能，不得自行构造 Supabase 查询。"
---

# neolyst

Neolyst 平台 Supabase 访问层。封装所有对 Neolyst 数据库的业务操作，供其他 skill 调用。

## 何时使用

当你需要：
- 根据邮箱查询分析师 ID
- 从远端同步模板文件（template.docx / schema.yaml）到本地
- 上传新模板文件到远端
- 查询或创建 coverage（股票覆盖记录）
- 保存报告草稿到 Neolyst
- 校验或提交报告

**不适用**：本地 Word 文档操作 → 使用 `report_maker` 或 `template_maker`

---

## 身份认证

身份信息存储在 `{cwd}/.neolyst` 文件（JSON 格式）：

```json
{
  "email": "analyst@example.com",
  "password": "...",
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "expires_at": 1712345678
}
```

**使用规则**：
1. 每次操作前，读取 `.neolyst` 文件，检查 `expires_at`（Unix 时间戳）
2. 如果 token 已过期（当前时间 > `expires_at`），用 `email` + `password` 重新登录，更新文件
3. 如果 `.neolyst` 文件不存在，提示用户提供凭据并写入文件

**实现参考**：

```python
from skills.neolyst.scripts import connection

# 获取已认证的 Supabase 客户端（自动处理 token 刷新）
client = connection.get_client(cwd)
```

---

## 对外接口

### 1. `resolve_analyst_by_email`

根据邮箱查询分析师 ID。

```python
from skills.neolyst.scripts import analyst

record = analyst.resolve_analyst_by_email(client, email)
# 返回：dict（analyst 记录，含 email, english_name, chinese_name, suffix, sfc, region_code, is_active 等）
# 找不到或已停用时：抛出 ValueError
```

---

### 2. `resolve_template`

从 Neolyst 下载模板文件到本地，返回本地路径。

```python
from skills.neolyst.scripts import template

result = template.resolve_template(client, report_type, language)
# 返回：{"template_local_path": "...", "schema_local_path": "..."}
# report_type: 如 "company", "sector", "company_flash" 等
# language: "zh" 或 "en"
```

**下载逻辑**：
- 查询 `templates` 表，找到对应 `report_type` + `language` 的记录
- 按 `template_file_path` / `schema_file_path` 字段从 Storage bucket 下载
- 本地缓存路径：`{cwd}/templates/{report_type}_{language}/`

---

### 3. `upsert_template`

将本地模板文件上传到 Neolyst，并更新数据库记录。

```python
from skills.neolyst.scripts import template

template.upsert_template(
    client,
    report_type,       # 如 "company"
    language,          # "zh" 或 "en"
    name,              # 模板显示名称
    template_local_path,  # 本地 template.docx 路径
    schema_local_path,    # 本地 schema.yaml 路径
)
# 返回：None
```

**上传逻辑**：
- 上传文件到 Storage bucket（路径由 `template_file_path` / `schema_file_path` 字段定义）
- Upsert `templates` 表记录（以 `report_type` + `language` 为唯一键）

---

### 4. `reuse_template`

将某个 report_type 的模板指向另一个 report_type 的模板（共用）。

```python
from skills.neolyst.scripts import template

template.reuse_template(
    client,
    report_type,            # 要配置的报告类型，如 "strategy"
    language,               # "zh" 或 "en"
    same_as_report_type,    # 要复用的来源类型，如 "common"
)
# 返回：None
```

**行为**：在数据库中为 `report_type` 创建一条记录，`template_file_path` 和 `schema_file_path` 指向 `same_as_report_type` 对应记录的路径。

---

### 5. `resolve_coverage`

根据 ticker 和主分析师 ID 查询 coverage_id。

```python
from skills.neolyst.scripts import coverage

coverage_id = coverage.resolve_coverage(client, ticker, first_analyst_id)
# 返回：str（coverage.id）
# 未命中或命中多条时：抛出 ValueError（含具体错误信息）
```

---

### 6. `create_coverage`

创建新的股票覆盖记录。

```python
from skills.neolyst.scripts import coverage

coverage_id = coverage.create_coverage(
    client,
    ticker,                # 如 "2507.HK"
    english_full_name,     # 公司英文全称
    sector_id,             # 行业 ID（UUID）
    isin,                  # ISIN 代码（可为 None）
    country_of_domicile,   # 注册国，如 "CN"
    analysts,              # 分析师列表，[{"analyst_id": "...", "role": "primary"}, ...]
    **kwargs,              # 其他可选字段
)
# 返回：str（新创建的 coverage.id）
```

---

### 7. `save_draft_report`

将报告草稿数据保存到 Neolyst（同时上传报告文件到 Storage）。

```python
from skills.neolyst.scripts import draft_report

result = draft_report.save_draft_report(client, draft_input)
# draft_input: dict，包含报告元数据和本地文件路径
# 返回：{"report_id": "...", "version_no": 1, "status": "draft"}
```

**Storage 文件路径格式**：

```
{report_id}/{report_id}_{version_no3}_{label}_{ts}.{ext}
```

- `version_no3`：version_no 补零至 3 位，如 `001`
- `label`：文件用途标签，如 `output`、`body`、`abstract`
- `ts`：上传时间戳（秒级 Unix）
- `ext`：文件扩展名，如 `docx`、`pdf`

**示例**：`a1b2c3d4/a1b2c3d4_001_output_1712345678.docx`

---

### 8. `validators`

校验报告是否满足提交条件。

```python
from skills.neolyst.scripts.validators import validators

result = validators(client, report_id, version_no)
# 返回：{"report_id": "...", "version_no": 1}
# 校验失败时：抛出 ValueError，包含失败原因
```

**校验内容**（示例）：
- 报告状态为 `draft`
- 必填字段已填写
- 关联 coverage 存在
- 文件已上传到 Storage

---

### 9. `submit_report`

提交报告进入审批流程。

```python
from skills.neolyst.scripts.submit_report import submit_report

result = submit_report(client, report_id, version_no)
# 返回：{"report_id": "...", "status": "submitted", "version_no": 1}
# 提交前会自动调用 validators，校验失败则抛出异常
```

---

## 错误处理规范

| 场景 | 处理方式 |
|------|---------|
| token 过期 | 自动重新登录，透明处理 |
| 找不到记录 | 返回 None 或抛出 ValueError（见各接口说明） |
| 网络超时 | 抛出异常，附带可读错误信息 |
| 校验失败 | 抛出 ValueError，说明具体原因 |
| 文件不存在 | 抛出 FileNotFoundError |

**原则**：不吞掉任何错误，每层都记录错误上下文，向调用方提供可操作的错误信息。

---

## 目录结构

```
skills/neolyst/
├── SKILL.md
├── scripts/
│   ├── __init__.py
│   ├── connection.py      # Supabase 客户端 + token 管理
│   ├── storage.py         # Storage bucket 上传/下载工具
│   ├── analyst.py         # resolve_analyst_by_email
│   ├── template.py        # resolve_template / upsert_template / reuse_template
│   ├── coverage.py        # resolve_coverage / create_coverage
│   ├── draft_report.py    # save_draft_report
│   ├── validators.py      # validators
│   └── submit_report.py   # submit_report
└── tests/
    └── __init__.py
```

---

## 注意事项

1. **只负责 Neolyst 数据操作**：本 skill 不处理 Word 文档结构，不生成报告内容
2. **幂等设计**：`upsert_template` 和 `save_draft_report` 多次调用不产生副作用
3. **本地缓存**：`resolve_template` 下载后缓存到本地，避免重复下载
4. **不存储敏感信息**：access_token 只读写 `.neolyst` 文件，不写入代码或日志
5. **测试使用真实联调环境**：测试连接联调 Supabase，凭据从环境变量读取（`NEOLYST_TEST_URL`、`NEOLYST_TEST_EMAIL`、`NEOLYST_TEST_PASSWORD`），不使用 mock
