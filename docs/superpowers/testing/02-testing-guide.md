# neolyst 集成功能测试指南

本文档说明如何测试 report_maker 和 template_maker 与 neolyst 集成的各项功能。

---

## 测试环境准备

### 1. 环境要求

- Python 3.9+
- 依赖包: `supabase` Python SDK
- Supabase 项目（参见 `01-supabase-data-requirements.md` 准备数据）

### 2. 本地 Supabase 数据库连接信息

**本地 Supabase 已部署在 `D:\Program\supabase`**

#### 数据库连接信息

| 配置项 | 值 |
|--------|-----|
| **Host** | localhost |
| **Port** | 5432 |
| **Database** | _supabase |
| **Username** | supabase_admin |
| **Password** | `OzIvixnAYAXbcyoDakQS4C8gU8N6TRwu` |

#### 连接字符串（pg）

```
postgresql://supabase_admin:OzIvixnAYAXbcyoDakQS4C8gU8N6TRwu@localhost:5432/_supabase
```

#### Python 连接示例

```python
from supabase import create_client, Client

url = "http://localhost:8000"  # 本地 API Gateway
key = "***REMOVED-JWT***"  # anon key

# 使用 REST API 连接
client: Client = create_client(url, key)
```

#### 直接连接 PostgreSQL（使用 psql）

```bash
# 通过 Docker 容器连接
docker exec -it supabase-db psql -U supabase_admin -d _supabase

# 或本地 psql 连接
psql "postgresql://supabase_admin:OzIvixnAYAXbcyoDakQS4C8gU8N6TRwu@localhost:5432/_supabase"
```

#### 已创建的表

| 表名 | 说明 |
|------|------|
| `analyst` | 分析师信息 |
| `report_template` | 报告模板 |
| `sector` | 行业 |
| `region` | 区域 |
| `coverage` | 覆盖范围（股票） |
| `coverage_analyst` | 覆盖范围-分析师关联 |

#### 当前测试数据

**analyst 表：**
| email | english_name | chinese_name | is_active |
|-------|--------------|--------------|-----------|
| harryyang@hfisec.com.hk | Bin Yang | 杨斌 | true |
| dengyida@hfisec.com.hk | Yida Deng | 邓轶达 | true |

**report_template 表：**
| id | report_type | language | is_published |
|----|-------------|----------|--------------|
| company_zh | company | zh | true |

**coverage 表：**
| ticker | english_name | chinese_name | country_of_domicile |
|--------|--------------|--------------|-------------------|
| 3393.HK | Wasion Holdings | 威胜控股 | HK |

**coverage_analyst 表：**
| coverage_id | analyst_email | author_order | is_primary |
|-------------|---------------|--------------|------------|
| c3333333... | harryyang@hfisec.com.hk | 1 | true |
| c3333333... | dengyida@hfisec.com.hk | 2 | false |

### 3. 设置环境变量

```bash
# 本地 Supabase（使用本地部署的实例）
export SUPABASE_URL=http://localhost:8000
export SUPABASE_ANON_KEY=***REMOVED-JWT***
# 或使用 service role key（测试环境）
export SUPABASE_SERVICE_ROLE_KEY=***REMOVED-JWT***

# neolyst 认证（用于调用 neolyst API）
export NEOLYST_EMAIL=yechuan958@gmail.com
export NEOLYST_PASSWORD=yc123456
```

### 4. 验证连接

```python
from neolyst.connection import get_client
client = get_client()
print("连接成功")
```

---

## 测试分组

按功能分为 5 个测试组，建议按顺序执行。

---

## Group A: 模板发布与复用（template_maker）

### A-1: 发布主模板 `upsert_template`

**测试目标：** 将本地模板文件发布到 neolyst

**准备：**
- 本地 Word 模板文件路径，如 `templates/company/en/template.docx`
- 本地 schema 文件路径，如 `templates/company/en/schema.yaml`

**执行：**

```python
from neolyst.connection import get_client
from neolyst.template import upsert_template

client = get_client()
upsert_template(
    client,
    report_type="company",
    language="en",
    template_local_path="templates/company/en/template.docx",
    schema_local_path="templates/company/en/schema.yaml"
)
print("✅ 模板发布成功")
```

**验证：**

```python
# 查询数据库确认记录已创建
resp = client.table("report_template").select("*").eq("report_type", "company").eq("language", "en").execute()
print(resp.data[0])
# 应显示 template_file_path 和 schema_file_path 非空
```

---

### A-2: 复用模板 `reuse_template`

**测试目标：** 让新报告类型复用已发布的模板

**前置条件：** `macro_en` 模板已发布

**执行：**

```python
from neolyst.connection import get_client
from neolyst.template import reuse_template

client = get_client()
reuse_template(
    client,
    report_type="quantitative",  # 新报告类型
    language="en",
    same_as_report_type="macro"  # 复用 macro 的模板
)
print("✅ 模板复用配置成功")
```

**验证：**

```python
# 查询确认 quantitative_en 的路径与 macro_en 相同
resp = client.table("report_template").select("template_file_path").eq("id", "quantitative_en").execute()
print(resp.data[0]["template_file_path"])
# 应与 macro_en 的路径相同
```

---

### A-3: CLI 命令 `publish` 和 `reuse`

**测试目标：** 通过命令行发布模板

**执行：**

```bash
# 发布模板
python -m template_maker.scripts.invoke publish \
    --report-type company \
    --language en \
    --template templates/company/en/template.docx \
    --schema templates/company/en/schema.yaml

# 复用模板
python -m template_maker.scripts.invoke reuse \
    --report-type quantitative \
    --language en \
    --same-as macro
```

**验证：** 同 A-1 和 A-2

---

## Group B: 模板解析（report_maker）

### B-1: 从 neolyst 解析模板

**测试目标：** 验证 `resolve_template_for_report` 能从 neolyst 下载模板

**前置条件：** `company_en` 模板已在 `report_template` 表中，`template_file_path` 指向 Storage 中的文件

**执行：**

```python
from report_maker.scripts.neolyst_integration import resolve_template_for_report

result = resolve_template_for_report(
    report_type="company",
    report_language="en",
    dest_dir="."
)
print(f"模板路径: {result['template_local_path']}")
print(f"Schema路径: {result['schema_local_path']}")
```

**验证：**
- 返回的 `template_local_path` 文件存在
- 返回的 `schema_local_path` 文件存在（如果有）

**预期文件结构：**
```
./templates/company/en/template.docx
./templates/company/en/schema.yaml
```

---

## Group C: 分析师解析（report_maker）

### C-1: 从 elements.yaml 解析分析师

**测试目标：** 验证能从 elements.yaml 的 a1~a8 槽位解析并校验分析师

**前置条件：** `analyst` 表有 `zhangsan@example.com` 和 `lisi@example.com` 两条活跃记录

**执行：**

```python
from report_maker.scripts.neolyst_integration import resolve_analysts_from_elements, get_contact_person_options

elements = {
    "a1": "zhangsan@example.com",
    "a2": "lisi@example.com",
    "title": "Test Report"
}

analysts = resolve_analysts_from_elements(elements)
print(f"解析到 {len(analysts)} 位分析师")
for a in analysts:
    print(f"  {a['author_order']}: {a['analyst_email']} (id: {a['analyst_id']})")

options = get_contact_person_options(analysts)
print(f"contact_person 可选值: {options}")
```

**验证：**
- 返回 2 位分析师
- `author_order` 分别为 1 和 2
- `contact_person_options` = `["zhangsan@example.com", "lisi@example.com"]`

---

### C-2: 分析师未找到或已停用

**测试目标：** 验证 `resolve_analyst_by_email` 对无效邮箱抛出 ValueError

**执行：**

```python
from report_maker.scripts.neolyst_integration import resolve_analysts_from_elements

elements = {"a1": "nonexistent@example.com"}

try:
    analysts = resolve_analysts_from_elements(elements)
    print("❌ 应抛出 ValueError")
except ValueError as e:
    print(f"✅ 正确抛出异常: {e}")
```

---

## Group D: Coverage 解析（report_maker）

### D-1: 查询 coverage_id

**测试目标：** 验证能根据 ticker 和 1作分析师邮箱查询 coverage

**前置条件：** `coverage` 表有 `2507.HK` 的记录，`coverage_analyst` 关联 `zhangsan@example.com` 为 1 作

**执行：**

```python
from report_maker.scripts.neolyst_integration import resolve_coverage_for_report

coverage_id = resolve_coverage_for_report(
    ticker="2507.HK",
    first_analyst_email="zhangsan@example.com"
)
print(f"coverage_id: {coverage_id}")
```

**验证：**
- 返回非空 UUID 字符串

---

### D-2: Coverage 未命中

**测试目标：** 验证 coverage 不存在时抛出 ValueError

**执行：**

```python
from report_maker.scripts.neolyst_integration import resolve_coverage_for_report

try:
    coverage_id = resolve_coverage_for_report(
        ticker="9999.HK",
        first_analyst_email="zhangsan@example.com"
    )
    print("❌ 应抛出 ValueError")
except ValueError as e:
    print(f"✅ 正确抛出异常: {e}")
```

---

## Group E: 字段映射与草稿操作（report_maker）

### E-1: 语言自动判断

**测试目标：** 验证能从标题自动判断报告语言

**执行：**

```python
from report_maker.scripts.neolyst_integration import detect_language_from_title

# 中文标题
lang_zh = detect_language_from_title("西锐飞机首次覆盖报告")
print(f"中文标题判定: {lang_zh}")  # 应输出 "zh"

# 英文标题
lang_en = detect_language_from_title("Cirrus Aircraft Initiates Coverage")
print(f"英文标题判定: {lang_en}")  # 应输出 "en"
```

---

### E-2: 投资要点压缩

**测试目标：** 验证能将长摘要压缩为 150 字以内的投资要点

**执行：**

```python
from report_maker.scripts.neolyst_integration import compress_investment_thesis

long_abstract = "这是很长的摘要内容。" * 50  # 超过 150 字

compressed = compress_investment_thesis(long_abstract)
print(f"压缩后长度: {len(compressed)}")  # 应 <= 150
print(f"压缩后内容: {compressed[:50]}...")
```

---

### E-3: 字段映射 `map_elements_to_draft`

**测试目标：** 验证能将 elements.yaml 完整映射为 neolyst draft 格式

**前置条件：** 分析师和 coverage 数据已准备

**执行：**

```python
from report_maker.scripts.neolyst_integration import map_elements_to_draft

elements = {
    "title": "Cirrus Aircraft Initiates Coverage",
    "ticker": "2507.HK",
    "rating": "Buy",
    "target_price": "15.0",
    "a1": "zhangsan@example.com",
    "a2": "lisi@example.com",
}

analysts = [
    {"analyst_email": "zhangsan@example.com", "author_order": 1, "analyst_id": "xxx"},
    {"analyst_email": "lisi@example.com", "author_order": 2, "analyst_id": "yyy"},
]

draft = map_elements_to_draft(
    elements=elements,
    report_type="company",
    report_file="/path/to/report.docx",
    pdf_file="/path/to/report.pdf",
    contact_person="zhangsan@example.com",
    analysts=analysts,
    coverage_id="c1111111-1111-1111-1111-111111111111",
)

print(f"title: {draft['title']}")
print(f"report_language: {draft['report_language']}")  # 应为 "en"
print(f"coverage_id: {draft['coverage_id']}")
print(f"ticker: {draft['ticker']}")
print(f"rating: {draft['rating']}")
```

---

### E-4: 保存草稿 `save_draft`

**测试目标：** 验证能调用 neolyst 保存报告草稿

**前置条件：** `report_template`、`analyst` 等基础数据已准备

**执行：**

```python
from report_maker.scripts.neolyst_integration import save_draft

draft = {
    "title": "Test Report",
    "report_type": "company",
    "report_language": "en",
    "analysts": [
        {"analyst_email": "zhangsan@example.com", "author_order": 1, "analyst_id": "a1111111-1111-1111-1111-111111111111"},
    ],
    "report_file": "/path/to/report.docx",
    "pdf_file": "/path/to/report.pdf",
    "contact_person": "zhangsan@example.com",
    "investment_thesis": "Test thesis",
}

result = save_draft(draft)
report_id = result["report_id"]
print(f"✅ 草稿已保存，report_id: {report_id}")
```

**验证：**
- 返回非空 `report_id`
- Supabase `report` 表中有对应记录

---

### E-5: 校验草稿 `validate_draft`

**测试目标：** 验证能调用 neolyst 校验报告

**前置条件：** 已有保存的草稿

**执行：**

```python
from report_maker.scripts.neolyst_integration import validate_draft

try:
    validate_draft(report_id)
    print("✅ 校验通过")
except ValueError as e:
    print(f"❌ 校验失败: {e}")
```

---

### E-6: 提交报告 `submit_draft`

**测试目标：** 验证能提交报告到 submitted 状态

**前置条件：** 草稿校验通过

**执行：**

```python
from report_maker.scripts.neolyst_integration import submit_draft

result = submit_draft(report_id)
print(f"✅ 报告已提交: {result}")
# 应返回 {"report_id": "...", "status": "submitted"}
```

---

## Group F: 完整工作流（report_maker）

### F-1: `prepare_and_save_draft` 完整流程

**测试目标：** 验证从 elements.yaml 到草稿保存的完整流程

**前置条件：** 所有 Supabase 数据已准备，elements.yaml 文件存在

**执行：**

```python
from report_maker.scripts.workflow import prepare_and_save_draft

result = prepare_and_save_draft(
    elements_path="elements.yaml",
    report_type="company",
    report_file="/path/to/output.docx",
    pdf_file="/path/to/output.pdf",
    dest_dir="."
)

print(f"report_id: {result['report_id']}")
print(f"analysts: {result['analysts']}")
print(f"contact_person_options: {result['contact_person_options']}")
print(f"coverage_id: {result['coverage_id']}")
```

**验证：**
- 返回所有必要字段
- `coverage_id` 已解析（如果 ticker 在 coverage 表中）

---

### F-2: `submit_report_workflow` 完整提交流程

**测试目标：** 验证校验 → 上传文件 → 提交的完整流程

**前置条件：** 草稿已保存，`report_id` 已知

**执行：**

```python
from report_maker.scripts.workflow import submit_report_workflow

result = submit_report_workflow(
    report_id="your-report-id",
    report_file="/path/to/output.docx",
    pdf_file="/path/to/output.pdf",
    contact_person="zhangsan@example.com",
    analysts=[
        {"analyst_email": "zhangsan@example.com", "author_order": 1, "analyst_id": "xxx"},
    ],
    coverage_id="c1111111-1111-1111-1111-111111111111",
    model_file="/path/to/model.xlsx"  # 可选
)

print(f"✅ 提交流程完成: {result}")
```

---

## 测试结果汇总表

| 测试组 | 测试项 | 关键依赖 | 预期结果 |
|--------|--------|----------|----------|
| A-1 | upsert_template | report_template 表 | 记录创建，文件上传到 Storage |
| A-2 | reuse_template | macro_en 已发布 | quantitative_en 复用 macro_en 路径 |
| B-1 | resolve_template | company_en 已发布 | 模板下载到本地 |
| C-1 | resolve_analysts | analyst 表有记录 | 返回正确分析师列表 |
| D-1 | resolve_coverage | coverage 表有记录 | 返回 coverage_id |
| E-3 | map_elements_to_draft | C-1, D-1 | 字段映射正确 |
| E-4 | save_draft | 基础数据 | report_id 返回 |
| E-5 | validate_draft | E-4 草稿 | 校验通过或抛出错误 |
| E-6 | submit_draft | E-5 通过 | status="submitted" |
| F-1 | prepare_and_save_draft | 所有基础数据 | 完整返回 |
| F-2 | submit_report_workflow | F-1 草稿 | 完整流程完成 |

---

## 调试技巧

### 查看模块导入是否正常

```python
# 验证 neolyst_integration 模块可导入
from report_maker.scripts.neolyst_integration import (
    resolve_template_for_report,
    resolve_analysts_from_elements,
    map_elements_to_draft,
    save_draft,
    validate_draft,
    submit_draft,
)
print("✅ 所有函数导入成功")
```

### 查看 workflow 模块

```python
from report_maker.scripts.workflow import (
    prepare_and_save_draft,
    submit_report_workflow,
)
print("✅ workflow 导入成功")
```

### 查看 template_maker invoke

```bash
# 查看帮助
python -m template_maker.scripts.invoke --help
python -m template_maker.scripts.invoke publish --help
python -m template_maker.scripts.invoke reuse --help
```
