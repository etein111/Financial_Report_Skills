# report_maker 端到端自动化测试提示词

本提示词用于自动化测试 report_maker skill。用户指定测试文件后，整个流程自动执行，无需任何确认。

---

## 使用方法

将本文件作为 prompt 提供给 AI，自动执行测试。

---

## 输入

用户需提供：
1. 测试文件路径（Word 草稿 .docx）
2. 输出目录名（如 `test_xxx`）

---

## 自动化执行流程

### 第一步：环境设置

```bash
# 设置代理（如果需要）
export HTTP_PROXY=http://127.0.0.1:7890
export HTTPS_PROXY=http://127.0.0.1:7890

# 使用 venv Python
PYTHON=".venv/Scripts/python.exe"
```

### 第二步：确定报告类型和语言

根据文件路径和文件名自动判断：
- 路径含 `inbox/samples/company/` 或 `samples/company/` → `company`
- 路径含 `EN-` 或 `.docx` 含英文 → `en`
- 否则 → `zh`

### 第三步：预处理文档

```python
import sys
sys.path.insert(0, 'skills/report_maker/scripts')

from docx_reader import read_docx_tables, flatten_table_text
from docx import Document

# 读取表格
tables = read_docx_tables(draft_path)
table_text = flatten_table_text(tables)

# 读取段落
doc = Document(draft_path)
paragraphs = [(i, p.text.strip()) for i, p in enumerate(doc.paragraphs) if p.text.strip()]
```

### 第四步：LLM 提取字段

将表格和段落内容发送给 LLM，提取：
- schema.yaml 所有字段
- abstract/body/english_summary 的位置信息

### 第五步：提取 fragment

```python
from splitter import extract_abstract, extract_body, extract_english_summary

# 提取 abstract（如有）
if abstract_location:
    extract_abstract(draft_path, scope, output_path='{output_dir}/abstract.docx',
                     start_marker=..., end_marker=...)

# 提取 body
extract_body(draft_path, scope, output_path='{output_dir}/body.docx',
             start_marker=..., end_marker=...)

# 提取 english_summary（如有，英文报告跳过）
if has_english_summary:
    extract_english_summary(...)
```

### 第六步：创建 elements.yaml

根据提取结果生成 `elements.yaml`，包含 schema.yaml 所有字段。

### 第七步：渲染报告

```python
from renderer import render_report

result = render_report(
    template_path='templates/{report_type}/{language}/template.docx',
    elements=elements,
    abstract_path='{output_dir}/abstract.docx' if abstract_exists else '',
    body_path='{output_dir}/body.docx',
    output_path='{output_dir}/{final_output_filename}.docx',
    english_summary_path='{output_dir}/english_summary.docx' if exists else None
)
```

### 第八步：验证

```python
from docx import Document
import re

doc = Document(output_path)
placeholders = [p.text for p in doc.paragraphs if re.search(r'\{\{.*?\}\}', p.text)]

# 检查输出
assert len(placeholders) == 0, f"发现未填充占位符: {placeholders}"
assert len(doc.paragraphs) > 0, "输出文档为空"
print(f"✅ 验证通过: {len(doc.paragraphs)} 段落, {len(doc.tables)} 表格, {len(doc.inline_shapes)} 图片")
```

### 第九步：创建 PROCESS.md

生成测试过程记录文档。

---

## 完整示例

输入：`inbox/samples/company/0402威胜控股（3393.HK）首次覆盖.docx`
输出目录：`test_wasion`

执行后生成：
```
test_wasion/
├── draft.docx              # 原始草稿
├── elements.yaml           # 提取的字段
├── abstract.docx          # 摘要（如有）
├── body.docx              # 正文
├── english_summary.docx    # 英文摘要（如有）
├── relative_chart.png      # 相对收益图
├── recommendation_chart.png # 推荐走势图
├── {公司名}({ticker})：{标题}.docx  # 最终输出
└── PROCESS.md              # 测试记录
```

---

## 注意事项

1. **使用 `.venv/Scripts/python.exe`** 执行 Python 脚本
2. **设置代理** `HTTP_PROXY=http://127.0.0.1:7890` 以便 yfinance 图表生成
3. **Abstract 位置**：通常在首页表格的 Row8 Cell1（投资亮点段落）
4. **英文报告不需要 english_summary**（跳过即可）
5. **不要询问确认**，自动执行完成
6. **覆盖已有输出文件**时使用新文件名（如 `_v2`）
