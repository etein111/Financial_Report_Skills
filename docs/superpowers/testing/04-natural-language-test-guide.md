# neolyst 接入 - 自然语言对话测试指南

本文档用于在 OpenCode 中通过纯自然语言对话，测试 template_maker 和 report_maker 与 neolyst 的每个对接功能。

---

## 环境准备

### 1. 确认 Supabase 连接配置

确保 `skills/neolyst/neolyst.yaml` 已配置远程 Supabase：

```yaml
supabase_url: "https://neolyst-test.zeabur.app"
anon_key: "<你的 anon key>"
```

### 2. 验证连接

```
帮我执行这个命令验证 Supabase 连接：

docker exec supabase-db psql -U supabase_admin -d _supabase -c "SELECT email FROM analyst LIMIT 3;"

如果连接远程，改为：
psql -h <远程IP> -p 31280 -U supabase_admin -d postgres -c "SELECT email FROM analyst LIMIT 3;"
```

### 3. 确认数据库有测试数据

```
帮我检查数据库是否有这些测试数据：
- analyst 表有 harryyang@hfisec.com.hk 和 dengyida@hfisec.com.hk
- coverage 表有 3393.HK (威胜控股)
- report_template 表有 company_zh 模板
```

---

## 对话测试流程

---

### 第一轮：发布模板

**你说：**
```
帮我把 templates/company_zh 模板发布到 neolyst
```

**AI 应该执行：**
```bash
python skills/template_maker/scripts/invoke.py publish \
  --report-type company \
  --language zh \
  --template templates/company_zh/template.docx \
  --schema templates/company_zh/schema.yaml
```

**验证：**
```
帮我检查数据库，确认模板已发布：
psql -h <远程IP> -p 31280 -U supabase_admin -d postgres -c "SELECT id, report_type, language, is_published FROM report_template WHERE id='company_zh';"
```

---

### 第二轮：复用模板

**你说：**
```
我想创建一份威胜控股的报告，复用 company_zh 模板
```

**AI 应该执行：**
```bash
python skills/template_maker/scripts/invoke.py reuse \
  --report-type wasion_zh \
  --language zh \
  --same-as company
```

**验证：**
```
帮我检查数据库，确认新模板已创建：
psql -h <远程IP> -p 31280 -U supabase_admin -d postgres -c "SELECT * FROM report_template WHERE id='wasion_zh';"
```

---

### 第三轮：解析模板

**你说：**
```
我需要一份 company 类型的报告模板，帮我从 neolyst 获取
```

**AI 应该执行：**
```python
from skills.report_maker.scripts.neolyst_integration import resolve_template_for_report

result = resolve_template_for_report(
    report_type="company",
    report_language="zh"
)
print(result)
```

**验证：**
```
AI 应该返回类似：
{"template_local_path": "templates/company/zh/template.docx", "schema_local_path": "templates/company/zh/schema.yaml"}
```

---

### 第四轮：解析分析师

**你说：**
```
帮我解析这份报告的分析师：harryyang@hfisec.com.hk 是第一作者，dengyida@hfisec.com.hk 是第二作者
```

**AI 应该执行：**
```python
from skills.report_maker.scripts.neolyst_integration import resolve_analysts_from_elements, get_contact_person_options

elements = {
    "a1": "harryyang@hfisec.com.hk",
    "a2": "dengyida@hfisec.com.hk",
}

analysts = resolve_analysts_from_elements(elements)
contact_options = get_contact_person_options(analysts)
print(f"分析师: {analysts}")
print(f"Contact Person 可选: {contact_options}")
```

**验证：**
```
帮我检查数据库中这两个分析师的信息：
psql -h <远程IP> -p 31280 -U supabase_admin -d postgres -c "SELECT email, english_name FROM analyst WHERE email IN ('harryyang@hfisec.com.hk', 'dengyida@hfisec.com.hk');"
```

---

### 第五轮：解析 Coverage

**你说：**
```
帮我查找 3393.HK 这支股票的基本信息
```

**AI 应该执行：**
```python
from skills.report_maker.scripts.neolyst_integration import resolve_coverage_for_report

coverage = resolve_coverage_for_report(ticker="3393.HK")
print(coverage)
```

**验证：**
```
帮我检查数据库中 3393.HK 的信息：
psql -h <远程IP> -p 31280 -U supabase_admin -d postgres -c "SELECT ticker, english_name, chinese_name FROM coverage WHERE ticker='3393.HK';"
```

---

### 第六轮：语言自动判断

**你说：**
```
帮我判断这两个标题是什么语言：
1. "首次覆盖：配网投资与AI算力双轮驱动"
2. "Cirrus Aircraft Initiates Coverage"
```

**AI 应该执行：**
```python
from skills.report_maker.scripts.neolyst_integration import detect_language_from_title

lang_zh = detect_language_from_title("首次覆盖：配网投资与AI算力双轮驱动")
lang_en = detect_language_from_title("Cirrus Aircraft Initiates Coverage")
print(f"中文标题: {lang_zh}")
print(f"英文标题: {lang_en}")
```

**预期输出：**
```
中文标题: zh
英文标题: en
```

---

### 第七轮：投资要点压缩

**你说：**
```
帮我把这段很长的摘要压缩到 150 字符以内：
"这是很长的摘要内容。" * 50
```

**AI 应该执行：**
```python
from skills.report_maker.scripts.neolyst_integration import compress_investment_thesis

long_text = "这是很长的摘要内容。" * 50
compressed = compress_investment_thesis(long_text)
print(f"原文长度: {len(long_text)}")
print(f"压缩后长度: {len(compressed)}")
print(f"压缩后内容: {compressed}")
```

**预期输出：**
```
原文长度: 500
压缩后长度: 150
压缩后内容: 这是很长的摘要内容。这是很长的摘要内容。...(150字符)
```

---

### 第八轮：保存草稿

**你说：**
```
帮我把威胜控股的报告保存为草稿

报告信息：
- 标题：威胜控股首次覆盖
- 类型：公司报告
- 语言：中文
- 分析师：harryyang@hfisec.com.hk
- ticker: 3393.HK
- rating: Buy
- 目标价: 15.0
```

**AI 应该：**
1. 先解析分析师
2. 先解析 coverage
3. 映射字段
4. 调用 save_draft

**验证：**
```
帮我检查数据库，确认草稿已保存：
psql -h <远程IP> -p 31280 -U supabase_admin -d postgres -c "SELECT id, title, report_type, status, created_at FROM report_draft ORDER BY created_at DESC LIMIT 5;"
```

---

### 第九轮：提交草稿

**你说：**
```
帮我提交刚才保存的威胜控股报告草稿
```

**AI 应该执行：**
```python
# 先获取最新的草稿 ID
from skills.report_maker.scripts.neolyst_integration import submit_draft

# 假设草稿 ID 是刚才返回的
draft_id = "<草稿ID>"
submit_draft(draft_id)
print(f"草稿 {draft_id} 已提交")
```

**验证：**
```
帮我检查数据库，确认草稿状态已变为 submitted：
psql -h <远程IP> -p 31280 -U supabase_admin -d postgres -c "SELECT id, title, status FROM report_draft WHERE status='submitted';"
```

---

### 第十轮：完整工作流

**你说：**
```
帮我执行完整的报告生成流程：
1. 从 neolyst 获取 company_zh 模板
2. 解析分析师 harryyang@hfisec.com.hk
3. 解析 coverage 3393.HK
4. 将 elements.yaml 映射为草稿格式
5. 保存为草稿
6. 提交草稿

elements.yaml 的路径是: reports/威胜控股(3393)_20250402/elements.yaml
```

**AI 应该自动编排：**
```python
# 1. 获取模板
template = resolve_template_for_report("company", "zh")

# 2. 解析分析师
from skills.report_maker.scripts.neolyst_integration import resolve_analysts_from_elements
elements = {"a1": "harryyang@hfisec.com.hk"}
analysts = resolve_analysts_from_elements(elements)

# 3. 解析 Coverage
coverage = resolve_coverage_for_report(ticker="3393.HK")

# 4. 映射字段
from skills.report_maker.scripts.neolyst_integration import map_elements_to_draft
draft = map_elements_to_draft(...)

# 5. 保存草稿
draft_id = save_draft(draft)

# 6. 提交草稿
submit_draft(draft_id)
```

---

## 完整对话示例

---

**你说：**
```
我想测试 neolyst 接入的所有功能，请按以下顺序进行：

1. 发布 templates/company_zh 到 neolyst
2. 确认数据库有分析师 harryyang@hfisec.com.hk
3. 确认数据库有 coverage 3393.HK
4. 解析 company/zh 模板
5. 解析分析师信息
6. 解析 3393.HK 的 coverage
7. 测试语言判断功能
8. 测试摘要压缩功能
9. 保存一份威胜控股报告草稿
10. 提交刚才的草稿

每步完成后用数据库查询验证结果。
```

---

## 数据库查询命令速查

```bash
# 查看分析师
psql -h <IP> -p 31280 -U supabase_admin -d postgres -c "SELECT * FROM analyst;"

# 查看 Coverage
psql -h <IP> -p 31280 -U supabase_admin -d postgres -c "SELECT * FROM coverage;"

# 查看模板
psql -h <IP> -p 31280 -U supabase_admin -d postgres -c "SELECT * FROM report_template;"

# 查看草稿
psql -h <IP> -p 31280 -U supabase_admin -d postgres -c "SELECT * FROM report_draft ORDER BY created_at DESC;"

# 查看草稿状态
psql -h <IP> -p 31280 -U supabase_admin -d postgres -c "SELECT id, title, status FROM report_draft;"
```

---

## 注意事项

1. **对话中使用中文**，AI 会自动路由到对应功能
2. **不需要写代码**，只需描述你想做什么
3. **每步用数据库验证**，确保操作真正生效
4. **按顺序测试**，因为后续步骤依赖前面的数据
