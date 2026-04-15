# Spec 2: resolve_template 按 report_type + language 查询

## 变更

将 `resolve_template` 的查询条件从拼组合 id 改为按 report_type + language 两个自然字段查询。

## Python 侧（scripts/template.py L90-96）

```python
# 改前
record_id = f"{report_type}_{language}"
resp = client.table("report_template").select("template_file_path, schema_file_path").eq("id", record_id).execute()

# 改后
resp = (
    client.table("report_template")
    .select("template_file_path, schema_file_path")
    .eq("report_type", report_type)
    .eq("language", language)
    .execute()
)
```

- Python 侧不再依赖 id 拼接规则 `{report_type}_{language}`
- 已有索引 `idx_template_group` 覆盖 (report_type, language)

## SQL 侧

无变化。

## 不涉及

- 模板的其他操作（upsert、reuse）
- 测试用例（test_template.py 中 resolve_template 的测试应直接通过）
