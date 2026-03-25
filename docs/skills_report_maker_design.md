# report_maker 设计文档

## 1. 目录结构

```
report_maker/
├── SKILL.md
├── scripts/
│   ├── __init__.py
│   ├── common.py      # 常量、YAML 工具
│   ├── extractor.py   # LLM 要素提取
│   ├── splitter.py    # 摘要/正文拆分
│   └── renderer.py    # 模板渲染 + PDF 转换
└── tests/
    ├── test_extractor.py
    ├── test_splitter.py
    └── test_renderer.py
```

## 2. 核心数据结构

### 报告目录结构

```
reports/<report_name>/
├── draft.docx           # 原始草稿
├── elements.yaml        # 提取的要素（与 schema 一致）
├── abstract.docx        # 摘要片段
├── body.docx            # 正文片段
├── output.docx          # 最终 Word
└── output.pdf           # 最终 PDF
```

### elements.yaml 结构

与 `schema.yaml` 严格保持一致，所有字段都存在（包括空字段）：

```yaml
a1_cn: "杨斌"
a1_email: "harryyang@hfisec.com.hk"
a1_en: "Bin Yang"
a1_sfc: "BSQ313"
abstract: "abstract.docx"
body: "body.docx"
company: "西锐飞机"
current_price: ""
current_price_date: ""
market_cap: ""
one_year_high: ""
one_year_low: ""
rating: "OUTPERFORM"
report_date: "21 Oct 2025"
shares_in_issue: ""
target_price: "86.72"
ticker: "2507.HK"
title: "首次覆盖：安全..."
```

**注意**：
- 字段名与 `schema.yaml` 中的键名完全一致
- 空字段使用空字符串 `""`
- `abstract` 和 `body` 的值为文件路径引用

## 3. 两阶段流程

### 第一阶段：抽取与确认（交互式）

**LLM 决策 + Python 执行**

```python
# 1. 接收草稿和报告类型（人工指定）
report_type = "company"  # 用户指定
draft_path = save_draft(file)

# 2. 获取模板名
template_name = get_template(report_type)  # 从 router.yaml

# 3. 创建报告目录
report_dir = f"reports/{report_name}/"
os.makedirs(report_dir)

# 4. 加载 schema
schema = load_yaml(f"templates/{template_name}/schema.yaml")

# 5. LLM 提取要素
elements = extract_elements(draft_path, schema)

# 6. 交互式确认
for field_name in schema.keys():
    if field_name in ['abstract', 'body']:
        continue  # 特殊处理

    extracted_value = elements.get(field_name, "")

    # 展示并确认
    print(f"{field_name}: {extracted_value}")

    if not extracted_value:
        # LLM 未提取到，询问用户
        user_input = input(f"未提取到 {field_name}，留空吗？(直接回车留空，或输入值): ")
        elements[field_name] = user_input if user_input else ""
    else:
        # LLM 提取到了，让用户确认
        confirm = input("确认？(y/n/修改): ")
        if confirm == 'n':
            elements[field_name] = ""
        elif confirm.startswith('修改'):
            new_value = confirm.split(' ', 1)[1] if ' ' in confirm else ""
            elements[field_name] = new_value

# 7. 确保所有字段都存在（包括空字段）
for field_name in schema.keys():
    if field_name not in elements:
        elements[field_name] = ""

# 8. 保存 elements
save_yaml(f"{report_dir}/elements.yaml", elements)

# 9. 拆分摘要和正文
abstract_doc = extract_abstract(draft_path, schema['abstract']['scope'])
body_doc = extract_body(draft_path, schema['body']['scope'])
abstract_doc.save(f"{report_dir}/abstract.docx")
body_doc.save(f"{report_dir}/body.docx")

# 10. 展示摘要并等待用户确认继续
show_summary(elements)
```

### 第二阶段：渲染与输出

**纯 Python 实现**

```python
# 1. 更新修正后的 elements
elements = load_yaml(f"{report_dir}/elements.yaml")
elements.update(corrections)
save_yaml(f"{report_dir}/elements.yaml", elements)

# 2. 渲染短字段（Jinja2）
template = DocxTemplate(f"templates/{template_name}/template.docx")
template.render(elements)

# 3. 插入长文本片段（python-docx）
insert_fragment(template.doc, elements['abstract'])
insert_fragment(template.doc, elements['body'])

# 4. 保存 output.docx
template.save(f"{report_dir}/output.docx")

# 5. 转换 PDF
convert_to_pdf(f"{report_dir}/output.docx", f"{report_dir}/output.pdf")
```

## 4. 模块职责

| 模块 | 职责 |
|------|------|
| **common.py** | 常量定义、YAML 工具函数（与 template_maker 共享） |
| **extractor.py** | LLM 要素提取，基于 schema.yaml 约束 |
| **splitter.py** | 摘要/正文拆分，基于 schema 中的 scope 描述 |
| **renderer.py** | 模板渲染（Jinja2）+ 片段插入 + PDF 转换 |

### 关键函数接口

```python
# common.py
load_yaml(path) -> dict
save_yaml(path, data) -> None
get_template(report_type) -> str  # 从 router.yaml 获取模板名

# extractor.py
extract_elements(draft_path, schema) -> dict  # LLM 提取

# splitter.py
extract_abstract(draft_path, scope) -> Document
extract_body(draft_path, scope) -> Document

# renderer.py
render_and_save(template_path, elements, abstract_path, body_path, output_dir) -> None
```

## 5. 与 template_maker 的协作

```
template_maker                    report_maker
     |                                |
     v                                v
templates/                        reports/
├── router.yaml  <-------------- 读取路由
├── company/                      |
│   ├── schema.yaml  <--------- 读取提取规则
│   └── template.docx  <------- 读取并渲染
```

### 边界原则

- report_maker **只读** `templates/`
- report_maker **只写** `reports/`
- 不修改任何模板资产

### 数据流向

```
router.yaml -> 报告类型 -> 模板名
schema.yaml -> 提取规则 -> elements.yaml
template.docx + elements.yaml + abstract.docx + body.docx -> output.docx
```

## 6. 设计要点总结

1. **目录结构简洁**：4 个核心模块
2. **数据结构严格一致**：elements.yaml 与 schema.yaml 字段名完全对应
3. **两阶段流程**：
   - 第一阶段：LLM 语义理解 + 交互式确认
   - 第二阶段：纯 Python 确定性渲染
4. **与 template_maker 清晰隔离**：只读 templates/，只写 reports/
5. **空字段处理**：所有字段都存在，值为空字符串
