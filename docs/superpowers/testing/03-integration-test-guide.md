# neolyst 接入完整测试指南

本文档帮助你通过 OpenCode 调用 template_maker 和 report_maker，验证每个 neolyst 接入功能。

---

## 环境准备

### 1. 设置环境变量

```bash
# 远程 Supabase
export NEOLYST_URL=https://<你的项目>.supabase.co
export NEOLYST_ANON_KEY=<你的 anon key>

# 或本地 Supabase
export NEOLYST_URL=http://localhost:8000
export NEOLYST_ANON_KEY=<本地 anon key>
```

### 2. 验证连接

```bash
docker exec supabase-db psql -U supabase_admin -d _supabase -c "SELECT email FROM analyst LIMIT 3;"
```

---

## 功能清单与测试方法

---

### A. template_maker - 发布模板到 neolyst

#### 实现的功能

| 函数 | 说明 |
|------|------|
| `publish_template()` | 将本地模板上传到 neolyst |
| `reuse_template_cmd()` | 复用已有模板 |

#### OpenCode 对话

**对话 1：发布本地模板**

```
帮我执行以下命令，将本地模板发布到 neolyst：

python skills/template_maker/scripts/invoke.py publish \
  --report-type company \
  --language zh \
  --template templates/company_zh/template.docx \
  --schema templates/company_zh/schema.yaml
```

#### 数据库验证

```bash
docker exec supabase-db psql -U supabase_admin -d _supabase -c \
  "SELECT id, report_type, language, is_published, template_file_path FROM report_template;"
```

**预期结果：** `report_template` 表中新增一条 `id=company_zh` 的记录，`is_published=true`

---

### B. template_maker - 复用模板

#### OpenCode 对话

**对话 2：复用模板**

```
威胜控股的报告想复用 company_zh 模板，执行：

python skills/template_maker/scripts/invoke.py reuse \
  --report-type wasion_zh \
  --language zh \
  --same-as company
```

#### 数据库验证

```bash
docker exec supabase-db psql -U supabase_admin -d _supabase -c \
  "SELECT * FROM report_template WHERE id='wasion_zh' OR id LIKE '%wasion%';"
```

**预期结果：** `report_template` 表中新增一条 `id=wasion_zh` 的记录，指向相同的模板文件

---

### C. report_maker - 模板解析

#### 实现的功能

| 函数 | 说明 |
|------|------|
| `resolve_template_for_report()` | 从 neolyst 获取模板路径 |

#### OpenCode 对话

**对话 3：解析模板（获取模板路径）**

```python
# 在 OpenCode 中执行 Python 代码

from skills.report_maker.scripts.neolyst_integration import resolve_template_for_report

# 获取 company/zh 模板路径
result = resolve_template_for_report(
    report_type="company",
    report_language="zh"
)
print("模板路径:", result)
```

**预期输出：**
```python
{"template_local_path": "templates/company/zh/template.docx", "schema_local_path": "templates/company/zh/schema.yaml"}
```

#### 数据库验证

```bash
docker exec supabase-db psql -U supabase_admin -d _supabase -c \
  "SELECT * FROM report_template WHERE report_type='company' AND language='zh';"
```

---

### D. report_maker - 分析师解析

#### 实现的功能

| 函数 | 说明 |
|------|------|
| `resolve_analysts_from_elements()` | 从 a1~a8 槽位解析分析师 |
| `get_contact_person_options()` | 获取可选的 contact_person 列表 |
| `resolve_analyst_by_email()` | 单个分析师邮箱解析 |

#### OpenCode 对话

**对话 4：解析分析师**

```python
from skills.report_maker.scripts.neolyst_integration import resolve_analysts_from_elements

elements = {
    "a1": "harryyang@hfisec.com.hk",
    "a2": "dengyida@hfisec.com.hk",
}

analysts = resolve_analysts_from_elements(elements)
print("分析师列表:", analysts)

contact_options = get_contact_person_options(analysts)
print("Contact Person 选项:", contact_options)
```

**预期输出：**
```python
[
    {"analyst_email": "harryyang@hfisec.com.hk", "author_order": 1, "analyst_id": "<uuid>"},
    {"analyst_email": "dengyida@hfisec.com.hk", "author_order": 2, "analyst_id": "<uuid>"}
]
Contact Person 选项: ["harryyang@hfisec.com.hk", "dengyida@hfisec.com.hk"]
```

#### 数据库验证

```bash
docker exec supabase-db psql -U supabase_admin -d _supabase -c \
  "SELECT email, english_name FROM analyst;"
```

**预期结果：** `analyst` 表中有 harryyang 和 dengyida 的记录

---

### E. report_maker - Coverage 解析

#### 实现的功能

| 函数 | 说明 |
|------|------|
| `resolve_coverage_for_report()` | 通过 ticker 解析 coverage_id |

#### OpenCode 对话

**对话 5：解析 Coverage**

```python
from skills.report_maker.scripts.neolyst_integration import resolve_coverage_for_report

coverage = resolve_coverage_for_report(ticker="3393.HK")
print("Coverage 信息:", coverage)
```

**预期输出：**
```python
{"coverage_id": "<uuid>", "ticker": "3393.HK", "english_name": "Wasion Holdings", "chinese_name": "威胜控股"}
```

#### 数据库验证

```bash
docker exec supabase-db psql -U supabase_admin -d _supabase -c \
  "SELECT * FROM coverage WHERE ticker='3393.HK';"
```

---

### F. report_maker - 语言自动判断

#### 实现的功能

| 函数 | 说明 |
|------|------|
| `detect_language_from_title()` | 从标题自动判断语言 |

#### OpenCode 对话

**对话 6：测试语言判断**

```python
from skills.report_maker.scripts.neolyst_integration import detect_language_from_title

lang_zh = detect_language_from_title("首次覆盖：配网投资与AI算力双轮驱动")
lang_en = detect_language_from_title("Cirrus Aircraft Initiates Coverage")
print(f"中文: {lang_zh}, 英文: {lang_en}")
```

**预期输出：** `中文: zh, 英文: en`

---

### G. report_maker - 投资要点压缩

#### 实现的功能

| 函数 | 说明 |
|------|------|
| `compress_investment_thesis()` | 长摘要压缩到 150 字符以内 |

#### OpenCode 对话

**对话 7：测试压缩功能**

```python
from skills.report_maker.scripts.neolyst_integration import compress_investment_thesis

long_text = "这是很长的摘要内容。" * 50
compressed = compress_investment_thesis(long_text)
print(f"原文: {len(long_text)}, 压缩后: {len(compressed)}, 内容: {compressed[:100]}...")
```

**预期输出：** `原文: 500, 压缩后: 150, 内容: 这是很长的摘要内容...`

---

### H. report_maker - 字段映射

#### 实现的功能

| 函数 | 说明 |
|------|------|
| `map_elements_to_draft()` | 将 elements.yaml 映射为 neolyst 草稿格式 |

#### OpenCode 对话

**对话 8：测试字段映射**

```python
from skills.report_maker.scripts.neolyst_integration import map_elements_to_draft

elements = {
    "title": "威胜控股首次覆盖报告",
    "ticker": "3393.HK",
    "rating": "Buy",
    "target_price": "15.0",
    "a1": "harryyang@hfisec.com.hk",
    "abstract": "这是摘要内容",
}

analysts = [
    {"analyst_email": "harryyang@hfisec.com.hk", "author_order": 1, "analyst_id": "xxx"}
]

draft = map_elements_to_draft(
    elements=elements,
    report_type="company",
    report_file="/path/to/report.docx",
    pdf_file="/path/to/report.pdf",
    contact_person="harryyang@hfisec.com.hk",
    analysts=analysts,
    coverage_id="<coverage_uuid>",
)

print("草稿字段:", list(draft.keys()))
print("report_language:", draft.get("report_language"))
```

**预期输出：** `report_language: zh`（根据中文标题判断）

---

### I. report_maker - 保存草稿

#### 实现的功能

| 函数 | 说明 |
|------|------|
| `save_draft()` | 保存草稿到 neolyst |

#### OpenCode 对话

**对话 9：保存草稿**

```python
from skills.report_maker.scripts.neolyst_integration import save_draft

draft_data = {
    "report_type": "company",
    "report_language": "zh",
    "coverage_id": "<coverage_uuid>",
    "ticker": "3393.HK",
    "rating": "Buy",
    "title": "威胜控股首次覆盖",
    "contact_person": "harryyang@hfisec.com.hk",
    "analysts": [{"analyst_email": "harryyang@hfisec.com.hk", "author_order": 1}],
}

draft_id = save_draft(draft_data)
print("草稿ID:", draft_id)
```

**预期输出：** 返回草稿 UUID

#### 数据库验证

```bash
docker exec supabase-db psql -U supabase_admin -d _supabase -c \
  "SELECT id, title, report_type, status FROM report_draft ORDER BY created_at DESC LIMIT 5;"
```

**预期结果：** 新增一条 `status='draft'` 的记录

---

### J. report_maker - 提交草稿

#### 实现的功能

| 函数 | 说明 |
|------|------|
| `submit_draft()` | 提交草稿（status: draft → submitted） |

#### OpenCode 对话

**对话 10：提交草稿**

```python
from skills.report_maker.scripts.neolyst_integration import submit_draft

submit_draft(draft_id="<草稿ID>")
print("草稿已提交")
```

#### 数据库验证

```bash
docker exec supabase-db psql -U supabase_admin -d _supabase -c \
  "SELECT id, title, status FROM report_draft WHERE id='<草稿ID>';"
```

**预期结果：** `status` 从 `'draft'` 变为 `'submitted'`

---

## 完整工作流测试

### 对话 11：完整流程

```
帮我执行完整的报告生成流程：

1. 解析威胜控股的模板 (company/zh)
2. 解析分析师 harryyang@hfisec.com.hk
3. 解析 coverage 3393.HK
4. 映射 elements.yaml 到草稿格式
5. 保存草稿到 neolyst
6. 提交草稿

需要我提供 elements.yaml 的路径吗？
```

---

## 数据库表结构参考

```sql
-- 分析师表
SELECT email, english_name FROM analyst;

-- Coverage 表
SELECT ticker, english_name, chinese_name FROM coverage;

-- 模板表
SELECT id, report_type, language, is_published FROM report_template;

-- 草稿表
SELECT id, title, report_type, status, created_at FROM report_draft ORDER BY created_at DESC;
```

---

## 常见错误排查

| 错误信息 | 可能原因 |
|---------|---------|
| `PGRST301: No suitable key` | JWT 验证失败，检查 anon_key 是否正确 |
| `Unauthorized` | Kong apikey 验证失败，检查 Supabase 配置 |
| `Anonymous sign-ins are disabled` | 未启用匿名登录，设置 `GOTRUE_EXTERNAL_ANONYMOUS_USERS_ENABLED=true` |
| `Template not found` | 模板未发布或 ID 不正确 |
| `Analyst not found` | 分析师邮箱在数据库中不存在 |
| `Coverage not found` | Ticker 在 coverage 表中不存在 |
