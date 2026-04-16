# 直接查表操作

所有认证用户可读，写操作有角色约束。不封装函数，直接用 `client.table()` 操作。

## RLS 约束速查

| 表 | 读 | 写 |
|----|----|----|
| report | 按角色分级（见下方） | 走专用接口（interfaces.md），不直接写 |
| report_status_log | 随 report 可见 | 触发器自动写入，禁止手动 INSERT/UPDATE/DELETE |
| coverage | 所有认证用户 | admin only |
| coverage_analyst | 所有认证用户 | INSERT: admin/sa/analyst；UPDATE/DELETE: admin |
| analyst | 所有认证用户 | 走专用接口（interfaces.md） |
| report_template | 所有认证用户 | 走专用接口（interfaces.md） |
| region / sector / rating / report_type | 所有认证用户 | admin only |

### report 读权限

- **admin**：所有报告
- **SA**：submitted / published / rejected 状态的报告
- **analyst**：自己创建的（owner_user_id 匹配）+ 所有 published 报告

## report

### 查询入口

用户通常不会提供 report_id（UUID）。根据用户意图选择查询条件，从结果中获取 report_id 后再调用操作接口。

| 用户意图 | 查询条件 |
|----------|----------|
| 某只股票的报告 | `.eq("ticker", "VRT US")` |
| 某个状态的报告 | `.eq("status", "submitted")` — draft / submitted / published / rejected |
| 某分析师的报告 | `.eq("lead_analyst_email", "alice@neolyst.com")` |
| 按标题搜索 | `.ilike("title", "%AI%")` |
| 某段时间内的报告 | `.gte("created_at", "2026-04-01")` / `.lte("created_at", "2026-04-15")` |

多条件可组合。默认加 `.eq("is_active", True)` 排除废弃报告。

### 查询示例

```python
# 查某 ticker 下的所有活跃报告（按创建时间倒序）
client.table("report").select("id,title,status,rating,target_price,created_at").eq("ticker", "VRT US").eq("is_active", True).order("created_at", desc=True).execute()

# 查某分析师的 draft 报告
client.table("report").select("id,title,ticker,status").eq("lead_analyst_email", "alice@neolyst.com").eq("status", "draft").eq("is_active", True).execute()

# 按标题模糊搜索
client.table("report").select("id,title,status,ticker").ilike("title", "%Vertiv%").eq("is_active", True).execute()

# 查某时间段内的 submitted 报告（SA 审批队列）
client.table("report").select("id,title,ticker,lead_analyst_email,created_at").eq("status", "submitted").gte("created_at", "2026-04-01").eq("is_active", True).execute()
```

### 废弃报告

不直接写表。用 `deactivate_report` 接口，见 `interfaces.md`。

### 文件下载

查询 report 获取 `word_path` / `pdf_path` / `model_path`，用 `storage.download` 下载：

```python
from skills.neolyst.scripts import storage

resp = client.table("report").select("word_path,pdf_path,model_path").eq("id", report_id).execute()
row = resp.data[0]

if row["word_path"]:
    storage.download(client, row["word_path"], "./report.docx")
if row["pdf_path"]:
    storage.download(client, row["pdf_path"], "./report.pdf")
if row["model_path"]:
    storage.download(client, row["model_path"], "./model.xlsx")
```

路径格式：`reports/{report_id}/{category}/{timestamp}/{filename}`。`storage_path` 含 bucket 前缀，直接传给 `download` 即可。

## report_status_log

append-only 审计日志，记录每次状态流转。由数据库触发器自动写入，禁止手动 INSERT/UPDATE/DELETE。

字段：`id`、`report_id`、`from_status`、`to_status`、`action_by`、`action_by_name`、`action_at`、`reason`、`metadata`。

可见性随 report：admin 全部；SA 可见 submitted/published/rejected 相关记录；analyst 可见自己 owned 的。

```python
# 查某报告的完整状态流转记录
client.table("report_status_log").select("from_status,to_status,action_by_name,action_at,reason").eq("report_id", report_id).order("action_at", desc=True).execute()
```

## coverage

公司覆盖主表。字段：`id`、`ticker`、`english_name`、`chinese_name`、`traditional_chinese`、`sector_id`、`isin`、`country_of_domicile`、`reporting_currency`、`is_active`。

写操作走专用接口（`create_coverage`），见 `interfaces.md`。

```python
# 按 ticker 查 coverage
client.table("coverage").select("id,ticker,english_name,chinese_name,is_active").eq("ticker", "VRT US").execute()

# 按名称模糊搜索
client.table("coverage").select("id,ticker,english_name,chinese_name").or_("english_name.ilike.%Vertiv%,chinese_name.ilike.%威图%").eq("is_active", True).execute()

# 按行业查活跃 coverage
client.table("coverage").select("id,ticker,english_name").eq("sector_id", sector_uuid).eq("is_active", True).execute()

# 列出所有活跃 coverage
client.table("coverage").select("id,ticker,english_name,chinese_name,sector_id").eq("is_active", True).order("ticker").execute()
```

### 写入示例（admin only）

```python
# 停用 coverage
client.table("coverage").update({"is_active": False}).eq("id", coverage_id).execute()
```

## coverage_analyst

覆盖-分析师关联表。字段：`id`、`coverage_id`、`analyst_email`、`author_order`。

```python
# 查某 coverage 下的分析师（按署名排序）
client.table("coverage_analyst").select("analyst_email,author_order").eq("coverage_id", coverage_uuid).order("author_order").execute()

# 查某分析师负责的所有 coverage
client.table("coverage_analyst").select("coverage_id,author_order").eq("analyst_email", "alice@neolyst.com").execute()
```

### 写入示例

INSERT 允许 admin / SA / analyst；UPDATE / DELETE 仅 admin。

```python
# 追加分析师
client.table("coverage_analyst").insert({
    "coverage_id": coverage_uuid,
    "analyst_email": "bob@neolyst.com",
    "author_order": 2,
}).execute()

# 移除分析师（admin only）
client.table("coverage_analyst").delete().eq("coverage_id", coverage_uuid).eq("analyst_email", "bob@neolyst.com").execute()
```

## analyst

分析师表。专用接口（resolve / search / upsert / set_active）见 `interfaces.md`。

```python
# 列出全部活跃分析师
client.table("analyst").select("email,english_name,chinese_name,region_code").eq("is_active", True).execute()

# 按区域过滤
client.table("analyst").select("email,english_name,chinese_name").eq("region_code", "CN").eq("is_active", True).execute()
```

## report_template

报告模板表。专用接口（resolve / upsert / reuse）见 `interfaces.md`。

```python
# 列出全部模板
client.table("report_template").select("id,report_type,language,template_file_path").execute()

# 按 report_type 过滤
client.table("report_template").select("id,report_type,language,template_file_path").eq("report_type", "company").execute()

# 按 report_type + language 查
client.table("report_template").select("*").eq("report_type", "company").eq("language", "en").execute()
```

## 字典表（region / sector / rating / report_type）

### region

主键：`code`（text）。字段：`code`、`name_en`、`name_cn`、`is_active`。

```python
# 查全部活跃 region
client.table("region").select("code,name_en,name_cn").eq("is_active", True).execute()

# 按 code 查单个
client.table("region").select("*").eq("code", "CN").execute()

# 按名称模糊搜索
client.table("region").select("code,name_en,name_cn").or_("name_en.ilike.%Hong%,name_cn.ilike.%香港%").execute()
```

### sector

主键：`id`（uuid）。二级树结构：level 1 无 parent，level 2 的 parent_id 指向 level 1。

字段：`id`、`name_en`、`name_cn`、`wind_name`、`level`、`parent_id`、`is_active`。

```python
# 查 level 1 行业
client.table("sector").select("id,name_en,name_cn").eq("level", 1).eq("is_active", True).execute()

# 查某行业的 level 2 子行业
client.table("sector").select("id,name_en,name_cn,wind_name").eq("parent_id", parent_uuid).eq("is_active", True).execute()
```

#### sector 写入约束

`validate_sector_hierarchy` 触发器强制：
- `level=1`：`parent_id` 必须为 NULL
- `level=2`：`parent_id` 必须指向一条 `level=1` 的记录

写入示例（admin only）：

```python
# 新增 level 1 行业
client.table("sector").insert({"name_en": "Technology", "name_cn": "科技", "level": 1, "is_active": True}).execute()

# 新增 level 2 行业（parent_id 指向 level 1）
client.table("sector").insert({"name_en": "Software", "name_cn": "软件", "level": 2, "parent_id": level1_uuid, "is_active": True}).execute()

# 停用行业
client.table("sector").update({"is_active": False}).eq("id", sector_uuid).execute()
```

### rating

主键：`code`（text）。字段：`code`、`name`、`rank`。

```python
# 查全部 rating（按 rank 排序）
client.table("rating").select("code,name,rank").order("rank").execute()
```

写入示例（admin only）：

```python
# 新增/更新 rating
client.table("rating").upsert(
    {"code": "OUTPERFORM", "name": "优于大市", "rank": 1},
    on_conflict="code",
).execute()
```

### report_type

主键：`report_type`（text）。字段：`report_type`、`name`、`sort`、`is_active`。

```python
# 查活跃 report_type（按 sort 排序）
client.table("report_type").select("report_type,name,sort").eq("is_active", True).order("sort").execute()
```
