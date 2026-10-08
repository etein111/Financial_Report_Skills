# report_maker 端到端自动化测试提示词

本提示词用于自动化测试 report_maker skill。整个流程自动执行，无需任何确认。

---

## 使用方法

将本文件作为 prompt 提供给 AI，自动执行测试。

---

## 输入

用户需提供：
1. 输出目录名（如 `test_xxx`）

---

## 自动化执行流程

### 第一步：环境设置

```bash
# 设置代理
export HTTP_PROXY=http://127.0.0.1:7890
export HTTPS_PROXY=http://127.0.0.1:7890

# 使用 venv Python
PYTHON=".venv/Scripts/python.exe"
```

### 第二步：选择报告类型

显示报告类型菜单供用户选择：

```
【选择报告类型】
请选择要制作的研报类型：
  1. company       - 公司覆盖报告
  2. sector        - 行业研究报告
  3. flash         - 快讯
  4. company_flash - 公司快讯
  5. sector_flash  - 行业快讯
  6. macro         - 宏观报告
  7. strategy      - 策略报告
  8. quantitative  - 量化报告
  9. bond          - 债券报告
```

用户选择后，记录 `report_type`。

### 第三步：扫描测试文件

根据选择的报告类型，扫描对应目录：

| 报告类型 | 扫描目录 |
|---------|---------|
| company | `inbox/samples/company/` |
| sector | `inbox/samples/sector/` |
| flash / company_flash / sector_flash | `inbox/samples/flash/` |
| macro / strategy / quantitative / bond | `inbox/samples/macro/` |

扫描规则：
- 扫描 `.docx` 文件
- 排除 `~$` 开头的临时文件

显示扫描结果供用户选择：

```
【扫描到以下测试文件】
  1. 0402威胜控股（3393.HK）首次覆盖：配网投资与AI算力双轮驱动，能源计量龙头再启航.docx
  2. 西锐飞机首次覆盖报告（中文）提交版.docx
  ...
请选择测试文件 (1-9):
```

用户选择后，记录 `draft_path`。

### 第四步：确定语言

根据文件名判断语言：
- 文件名含 `EN-` 或全英文 → `en`
- 否则 → `zh`

### 第五步：预处理文档

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

### 第六步：LLM 提取字段

将表格和段落内容发送给 LLM，提取：
- schema.yaml 所有字段（从 `templates/{report_type}/{language}/schema.yaml` 读取）
- abstract/body/english_summary 的位置信息

### 第七步：提取 fragment

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

### 第八步：创建 elements.yaml

根据提取结果生成 `elements.yaml`，包含 schema.yaml 所有字段。

### 第九步：渲染报告

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

### 第十步：验证

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

### 第十一步：创建 PROCESS.md

生成测试过程记录文档。

---

## 完整示例

用户输入：`test_wasion`

执行流程：
1. 选择报告类型 → `1. company`
2. 扫描 `inbox/samples/company/` → 显示文件列表
3. 用户选择 `1` → `0402威胜控股（3393.HK）首次覆盖...docx`
4. 自动判断语言 → `zh`
5. 后续流程自动执行

输出目录 `test_wasion/` 结构：
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

1**不要询问确认**，自动执行完成
2**覆盖已有输出文件**时使用新文件名（如 `_v2`）
3**文件扫描结果为空时**，提示用户检查目录或选择其他报告类型
