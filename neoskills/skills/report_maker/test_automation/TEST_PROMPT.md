# Report Maker 自动化回归测试 - 执行提示词

**使用方式：**
1. CC 读取本文件
2. 按照以下步骤执行测试
3. 在每个验证点报告 PASS/FAIL
4. 最终输出完整测试报告

---

## 阶段 0：环境检查

### 0.1 检查 Python 依赖

执行：
```bash
python -c "import docx, docxtpl, docxcompose, yaml; print('OK')"
```

**预期**：输出 `OK`

---

## 阶段 1：第一阶段 - 提取与确认

### 1.1 扫描草稿文件

执行：
```bash
ls -la inbox/samples/company/
```

**预期**：找到 `0402威胜控股（3393.HK）首次覆盖：配网投资与AI算力双轮驱动，能源计量龙头再启航.docx`

---

### 1.2 预处理文档（表格提取）

执行：
```python
from docx import Document
from lxml import etree

draft_path = 'inbox/samples/company/0402威胜控股（3393.HK）首次覆盖：配网投资与AI算力双轮驱动，能源计量龙头再启航.docx'
doc = Document(draft_path)

def find_all_tables(elem):
    tables = []
    for child in elem:
        tag = child.tag.split('}')[1] if '}' in child.tag else child.tag
        if tag == 'tbl':
            tables.append(child)
        if tag in ('tc', 'p', 'tr', 'tbl', 'body'):
            tables.extend(find_all_tables(child))
    return tables

tables = find_all_tables(doc._element.body)
print(f'Total tables: {len(tables)}')

# Find Table_Info (should have [Table_Info] as first row label)
for ti, tbl in enumerate(tables):
    rows = tbl.findall('.//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tr')
    if rows:
        first_row_cells = rows[0].findall('.//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tc')
        if first_row_cells:
            first_text = ''.join(t.text or '' for t in first_row_cells[0].findall('.//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t'))
            if 'Table_Info' in first_text:
                print(f'Found Table_Info at table index {ti}')
```

**预期**：
- Total tables > 0
- 找到 Table_Info

---

### 1.3 提取段落（正文定位）

执行：
```python
from docx import Document

draft_path = 'inbox/samples/company/0402威胜控股（3393.HK）首次覆盖：配网投资与AI算力双轮驱动，能源计量龙头再启航.docx'
doc = Document(draft_path)
paragraphs = [(i, p.text.strip()) for i, p in enumerate(doc.paragraphs) if p.text.strip()]
print(f'Total paragraphs: {len(paragraphs)}')

# Find body start marker
for i, text in paragraphs:
    if '威胜控股：能源计量' in text:
        print(f'Body start: P{i} - {text[:50]}')
        break

# Find english summary start
for i, text in paragraphs:
    if 'Initial Coverage' in text:
        print(f'English summary content start: P{i} - {text[:60]}')
        break

# Find body end marker (last risk paragraph)
for i, text in paragraphs:
    if '海外市场业务增长速度慢于预期' in text:
        print(f'Body end marker: P{i} - {text[:60]}')
        break
```

**预期**：
- Total paragraphs ~115
- Body start: `1 威胜控股：能源计量与能效管理专家`
- English summary: `Initial Coverage on Wasion Holdings (3393.HK): ...`
- Body end: 风险提示段落

---

### 1.4 提取 fragments

创建输出目录并提取：

```bash
mkdir -p reports/test_output/
```

执行：
```python
import sys, shutil
from pathlib import Path
import importlib.util

spec = importlib.util.spec_from_file_location('splitter', 'skills/report_maker/scripts/splitter.py')
splitter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(splitter)

draft_path = 'inbox/samples/company/0402威胜控股（3393.HK）首次覆盖：配网投资与AI算力双轮驱动，能源计量龙头再启航.docx'
output_dir = 'reports/test_output/'
Path(output_dir).mkdir(parents=True, exist_ok=True)

# Copy draft
shutil.copy(draft_path, f'{output_dir}/draft.docx')

# Extract abstract
splitter.extract_abstract(draft_path, '首页右侧表格第8行', f'{output_dir}/abstract.docx')

# Extract body
splitter.extract_body(draft_path, 'P9到P273',
    f'{output_dir}/body.docx',
    start_marker='1 威胜控股：能源计量与能效管理专家',
    end_marker='国家电网及南方电网集采招标量价不及预期；海外市场业务增长速度慢于预期；海外生产成本上升')

# Extract english summary
splitter.extract_english_summary(draft_path, 'P275到P291',
    f'{output_dir}/english_summary.docx',
    start_marker='Initial Coverage on Wasion Holdings')
```

**验证提取结果**：

```python
from docx import Document

# Check abstract
abs_doc = Document('reports/test_output/abstract.docx')
abs_chars = sum(len(p.text) for p in abs_doc.paragraphs)
abs_paras = len([p for p in abs_doc.paragraphs if p.text.strip()])
print(f'Abstract: {abs_chars} chars, {abs_paras} paragraphs')
# 预期：~832 chars, 8 paragraphs

# Check body
body_doc = Document('reports/test_output/body.docx')
body_paras = len([p for p in body_doc.paragraphs if p.text.strip()])
body_tables = len(body_doc.tables)
print(f'Body: {body_paras} paragraphs, {body_tables} tables')
# 预期：272 paragraphs, 26 tables

# Check english summary
eng_doc = Document('reports/test_output/english_summary.docx')
eng_paras = len([p for p in eng_doc.paragraphs if p.text.strip()])
print(f'English summary: {eng_paras} paragraphs')
# 预期：19 paragraphs
```

---

### 1.5 创建 elements.yaml

```python
import yaml

elements = {
    'report_date': '2 Apr 2026',
    'company_cn': '威胜控股',
    'ticker': '3393.HK',
    'title': '首次覆盖：配网投资与AI算力双轮驱动，能源计量龙头再启航',
    'rating': '跑赢大市',
    'target_price': '40.94',
    'source': 'xxx',
    'current_price': '',
    'current_price_date': '',
    'market_cap': '',
    'shares_in_issue': '',
    'one_year_high': '',
    'one_year_low': '',
    'a1_cn': '杨斌', 'a1_en': 'Bin Yang', 'a1_sfc': 'BSQ313', 'a1_email': 'harryyang@hfisec.com.hk',
    'a2_cn': '邓轶达', 'a2_en': 'Yida Deng', 'a2_sfc': 'BVF321', 'a2_email': 'dengyida@hfisec.com.hk',
    'a3_cn': '', 'a3_en': '', 'a3_sfc': '', 'a3_email': '',
    'a4_cn': '', 'a4_en': '', 'a4_sfc': '', 'a4_email': '',
    'a5_cn': '', 'a5_en': '', 'a5_sfc': '', 'a5_email': '',
    'a6_cn': '', 'a6_en': '', 'a6_sfc': '', 'a6_email': '',
    'a7_cn': '', 'a7_en': '', 'a7_sfc': '', 'a7_email': '',
    'a8_cn': '', 'a8_en': '', 'a8_sfc': '', 'a8_email': '',
    'abstract': 'abstract.docx',
    'body': 'body.docx',
    'english_summary': 'english_summary.docx',
    'company_en': '',
    'relative_chart': '',
    'relative_chart_generated': False,
    'recommendation_chart': '',
    'recommendation_chart_generated': False,
}

with open('reports/test_output/elements.yaml', 'w') as f:
    yaml.dump(elements, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

print('elements.yaml created')
```

**验证**：
```bash
cat reports/test_output/elements.yaml | head -30
```

---

## 阶段 2：第二阶段 - 渲染与输出

### 2.1 加载模板

```bash
ls -la templates/company/zh/
```

**预期**：存在 `template.docx` 和 `schema.yaml`

---

### 2.2 渲染报告

```python
from docx import Document
from docxtpl import DocxTemplate
import yaml, re
from lxml import etree
from pathlib import Path
from copy import deepcopy
from docxcompose.composer import Composer

report_dir = 'reports/test_output'
elements = yaml.safe_load(open(f'{report_dir}/elements.yaml'))
template_path = 'templates/company/zh/template.docx'
output_path = f'{report_dir}/test_report_output.docx'

# Step 1: Render with docxtpl
tpl = DocxTemplate(template_path)
tpl.render(elements)
rendered_path = f'{report_dir}/rendered_template.docx'
tpl.save(rendered_path)
print('Template rendered')

# Step 2: Insert abstract into table cell
doc = Document(rendered_path)
abs_doc = Document(f'{report_dir}/abstract.docx')

W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'

for t in doc.tables:
    for row in t.rows:
        for cell in row.cells:
            if '{{ abstract }}' in cell.text or '(Please see APPENDIX 1' in cell.text:
                # Clear cell paragraphs
                for p in list(cell._tc.findall(f'{{{W}}}p')):
                    cell._tc.remove(p)
                # Insert abstract
                for src_p in abs_doc.paragraphs:
                    new_p = deepcopy(src_p._p)
                    cell._tc.append(new_p)
                print('Abstract inserted')

doc.save(rendered_path)

# Step 3: Compose with docxcompose
master = Document(rendered_path)
composer = Composer(master)

body_doc = Document(f'{report_dir}/body.docx')
composer.append(body_doc, remove_property_fields=False)

# Append english summary
eng_doc = Document(f'{report_dir}/english_summary.docx')
composer.append(eng_doc, remove_property_fields=False)

composer.save(output_path)
print(f'Output saved: {output_path}')
```

**验证输出文件**：
```bash
ls -la reports/test_output/*.docx
```

---

### 2.3 验证占位符

```python
import re
from docx import Document

output_path = 'reports/test_output/test_report_output.docx'
doc = Document(output_path)

placeholders = []
for p in doc.paragraphs:
    if re.search(r'\{\{.*?\}\}', p.text):
        placeholders.append(f'[P] {p.text}')
for t in doc.tables:
    for row in t.rows:
        for cell in row.cells:
            if re.search(r'\{\{.*?\}\}', cell.text):
                placeholders.append(f'[T] {cell.text[:50]}')

if placeholders:
    print(f'FAIL: Found {len(placeholders)} placeholders')
    for ph in placeholders[:5]:
        print(f'  {ph}')
else:
    print('PASS: No placeholders remaining')

print(f'Total paragraphs: {len(doc.paragraphs)}')
print(f'Total tables: {len(doc.tables)}')
```

**预期**：
- PASS: No placeholders remaining
- Total paragraphs: 270-280
- Total tables: 26-30

---

## 阶段 3：清理

```bash
rm -f reports/test_output/temp_*.docx
rm -f reports/test_output/rendered_template.docx
ls -la reports/test_output/
```

**最终输出目录应包含**：
- `draft.docx` - 原始草稿副本
- `elements.yaml` - 提取字段
- `abstract.docx` - 摘要片段
- `body.docx` - 正文片段
- `english_summary.docx` - 英文摘要片段
- `test_report_output.docx` - 最终渲染报告

---

## 测试报告模板

```
# Report Maker 回归测试报告

**测试日期**：[自动填写]
**测试用例**：威胜控股公司覆盖报告
**测试结果**：PASS / FAIL

## 验证点

| 验证项 | 预期值 | 实际值 | 结果 |
|--------|--------|--------|------|
| Python 依赖 | OK | [实际输出] | PASS/FAIL |
| 表格数量 | >0 | [实际值] | PASS/FAIL |
| 段落数量 | ~115 | [实际值] | PASS/FAIL |
| Abstract 字符数 | ~832 | [实际值] | PASS/FAIL |
| Abstract 段落数 | 8 | [实际值] | PASS/FAIL |
| Body 段落数 | 272 | [实际值] | PASS/FAIL |
| Body 表格数 | 26 | [实际值] | PASS/FAIL |
| English Summary 段落数 | 19 | [实际值] | PASS/FAIL |
| 最终报告占位符 | 0 | [实际值] | PASS/FAIL |
| 最终报告段落数 | 270-280 | [实际值] | PASS/FAIL |

## 失败项（如有）
- [列出失败的验证项及原因]
```
