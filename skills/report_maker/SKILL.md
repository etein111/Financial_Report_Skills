---
name: report_maker
description: "当用户说「做研报」、「生成报告」、「写研报」、「处理研报」、「生成研究报告」或上传报告草稿（.docx）时使用此技能。负责解析 Word 草稿、提取要素、交互确认，生成标准格式的研究报告。**必须使用中文与用户沟通**。"
---

# Report Maker - 研究报告生成

**工作流程**：抽取确认 → 渲染输出 → 渲染成功问询（PDF/提交/下载）

**文件交互**：
- 询问用户输入文件（草稿 .docx）的路径
- 询问用户输出目录位置（可以选择已有目录，或新建目录）
- 最终输出文件命名格式：`公司名(ticker)：标题.docx`

---

## 1. 铁律（必须遵守的核心约束）

⚠️ **以下约束是强制性的，违反任何一条将导致报告错误**

| # | 规则 | 说明 |
|---|------|------|
| 1 | **第一阶段必须用 LLM 提取** | elements 字段禁止硬编码搜索，必须用 LLM 一次性提取 |
| 2 | **第二阶段禁止 LLM** | 渲染完全使用 Python 脚本，不调用任何 LLM |
| 3 | **body 是拼接不是填充** | body.docx 使用 docxcompose 拼接，保留自己页边距；模板中无需 `{{body}}` 占位符 |
| 4 | **禁止访问项目外路径** | 所有文件操作必须在项目根目录内（templates/、reports/、inbox/samples/） |
| 5 | **必须保留空字段** | elements.yaml 中所有字段必须存在，空字段用 `""` |
| 6 | **交互确认不能跳过** | 第一阶段必须展示摘要并等待用户确认，不能直接生成 |
| 7 | **只读 templates/** | report_maker 永远不修改模板资产 |

---

## 2. 工作流程概览

```
┌─────────────────────────────────────────────────────────────┐
│  第一阶段：抽取与确认（LLM）                                   │
├─────────────────────────────────────────────────────────────┤
│  1.1 选择报告类型 → 1.2 扫描草稿 → 1.3 确认输出目录            │
│  → 1.4 加载模板 → 1.5 预处理文档 → 1.6 LLM 提取              │
│  → 1.7 确认摘要正文 → 1.8 提取摘要正文 → 1.9 确认字段 → 1.10 保存结果 │
│                              ↓ 展示摘要，暂停，等待确认         │
├─────────────────────────────────────────────────────────────┤
│  第二阶段：渲染与输出（纯脚本）                                │
├─────────────────────────────────────────────────────────────┤
│  2.1 更新修正数据 → 2.2 确认文件位置 → 2.3 渲染报告           │
│  → 2.4 验证占位符 → 2.5 转换为 PDF → 2.6 渲染成功主动问询     │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. 依赖检查

**必需的 Python 包**：`python-docx`、`docxtpl`、`docxcompose`、`PyYAML`

**检查命令**：
```bash
python3 -c "import docx, docxtpl, docxcompose, yaml; print('OK')"
```

**安装命令**（如需安装）：
```bash
uv pip install "docxtpl>=0.20.0" docxcompose
```

---

## 4. 第一阶段：抽取与确认

### 1.1 选择报告类型

**自动列出选项，让用户选择**（不是让用户输入数字）：

```
【选择报告类型】
请选择要制作的研报类型：
  1.  company        - 公司覆盖报告
  2.  sector         - 行业研究报告
  3.  flash          - 快讯
  4.  company_flash  - 公司快讯
  5.  sector_flash   - 行业快讯
  6.  macro          - 宏观报告
  7.  strategy       - 策略报告
  8.  quantitative   - 量化报告
  9.  bond           - 债券报告

请选择报告类型（输入编号）：
```

**⚠️ 禁止行为**：不要列出数字选项让用户输入，直接展示选项让用户选择。

### 1.2 扫描草稿文件

⚠️ **必须实际执行扫描命令，禁止使用硬编码示例**

**扫描后自动列出文件，让用户选择**（不是让用户输入路径）：

```
【选择草稿文件】
在 inbox/samples/company/ 目录下找到以下草稿：

  1.  某公司研究报告.docx
  2.  某行业深度报告.docx
  ...

请选择要使用的草稿文件（输入编号）：
```

**扫描目录规则**：

| 报告类型 | 扫描目录 |
|---------|---------|
| company | `inbox/samples/company/` |
| sector | `inbox/samples/sector/` |
| flash / company_flash / sector_flash | `inbox/samples/flash/` |
| macro / strategy / quantitative / bond | `inbox/samples/macro/` |

**扫描规则**：
- 扫描 `.docx` 文件
- 排除 `~$` 开头的临时文件
- 排除 `_AutoRefresh` 后缀的文件

**自动查找 elements.yaml**：选择草稿后，在同目录下查找：
- `{文件名} elements.yaml`
- `{文件名}_elements.yaml`
- `elements.yaml`

**模板映射**：

| 报告类型 | 使用模板 |
|---------|---------|
| company | `company` |
| sector | `sector` |
| flash | `flash` |
| company_flash | `company_flash` |
| sector_flash | `sector_flash` |
| macro | `macro` |
| strategy / quantitative / bond | `common` |

### 1.3 确认输出目录

**命名规则**（日期统一放在最后）：

| 报告类型 | 格式 | 示例 |
|---------|------|------|
| company | `{公司简写}({ticker})_{日期}` | `cirrus(2507)_20251021` |
| 其他类型 | `{核心主题词}_{日期}` | `new_energy_20251021` |

**主题词提取原则**：
- ✅ 主题词：新能源汽车、AI芯片、美联储、利率政策
- ❌ 描述性词汇：深度分析、研究、报告、解读、提交版

```
【确认输出目录】
草稿文件: 西锐飞机首次覆盖报告（中文）提交版.docx
建议报告名称: cirrus(2507)_20260331

输出目录将创建在: reports/cirrus(2507)_20260331/
确认？(y/n)
```

### 1.4 加载模板

**运行时模板来源：neolyst（不再从本地 templates/ 目录读取）**

根据报告类型自动加载：

```
【加载模板】
报告类型: company
语言: zh
使用模板: neolyst (resolve_template)
✓ 已下载 schema.yaml（25 个字段）→ templates/company/zh/
✓ 已下载 template.docx
```

**模板解析规则**：
- 调用 `resolve_template_for_report(report_type, language)` 从 neolyst 获取模板
- `language` 来自当前报告的 `report_language`
- 模板下载到 `{dest_dir}/templates/{report_type}/{language}/` 目录
- `dest_dir` 默认为项目根目录，**不要传入已包含 `templates/` 的路径**，否则会嵌套
- 不再维护额外的"报告类型 -> 模板类型"映射表

每个模板目录必须包含：
- `schema.yaml` - **定义要提取哪些字段**
- `template.docx` - **Word 模板文件**

**本地 templates/ 目录**：
- 仅用于模板制作阶段的工作目录
- 运行时模板来源统一以 neolyst 保存的模板记录为准

### 1.5 预处理文档

⚠️ **必须提供带位置信息的文本，而不是扁平化文本流**

**原因**：英文摘要的 "Summary" 标题在段落中，不在表格里；扁平化文本丢失位置信息。

**执行方式**：
```python
from skills.report_maker.scripts import docx_reader
from docx import Document

# 提取所有表格（包括嵌套表格）的完整内容
tables = docx_reader.read_docx_tables(draft_path)

# 提取段落文本（带位置索引）
doc = Document(draft_path)
paragraphs = [(i, p.text.strip()) for i, p in enumerate(doc.paragraphs) if p.text.strip()]

# 1. 先输出表格内容
table_text = docx_reader.flatten_table_text(tables)
print("=== 表格内容 ===")
for line in table_text:
    print(line)

# 2. 再输出段落内容（带索引）
print("\n=== 段落内容（带索引）===")
total_paras = len(paragraphs)
for idx, text in paragraphs:
    print(f"[P{idx}/{total_paras}] {text}")

# 3. 特别标注最后 50 个段落（英文摘要通常在这里）
print("\n=== 最后 50 个段落（重点搜索 Summary）===")
last_50 = paragraphs[-50:] if len(paragraphs) > 50 else paragraphs
for idx, text in last_50:
    print(f"[P{idx}] {text}")
```

**⚠️ 执行方式要求**：
- ✅ 直接在 Python REPL 或项目内脚本中执行
- ✅ 所有文件路径必须是项目内的相对路径
- ❌ 禁止创建临时 Python 脚本文件到系统目录
- ❌ 禁止将文档内容写入临时文件

### 1.6 LLM 一次性提取

⚠️ **核心原则：必须用 LLM 提取，禁止硬编码搜索**

将**预处理后的完整文档内容**和 `schema.yaml` 发送给 LLM，在**一次调用中**完成：
1. 提取所有 elements 字段
2. 判断并提取摘要位置
3. 判断并提取正文位置
4. 判断并提取英文摘要位置

**禁止以下提取方式**：
- ❌ 用 LLM 以外的其他方式（关键词匹配等）
- ❌ 跳过 LLM 步骤，直接使用 field_extractor 自动提取
- ❌ 直接读取 .docx 文件而不经过预处理

**LLM 返回格式**：
```yaml
# 字段数据（必须与 schema.yaml 完全一致）
report_date: "..."
company: "..."
ticker: "..."
current_price: "..."
# ... 其他 schema 中定义的字段 ...

# 摘要信息
has_abstract: true/false
abstract_scope: "首页右侧表格第X行，包含'投资亮点'标题下的6个段落"
abstract_notice: "(Please see APPENDIX 1 for English summary)"

# 正文信息
has_body: true/false
body_scope: "目录（P10）到英文摘要（P305）之间"
body_start_marker: "目录"
body_end_marker: "资料来源：公司公告"

# 英文摘要信息
has_english_summary: true/false
english_summary_scope: "P306-P327"
english_summary_content_start: "Initial Coverage on Wasion Holdings"
```

**⚠️ body 的结束边界规则**：
- **如果有 english_summary**：body_end_marker 是 english_summary 标题之前的最后一段内容
- **如果没有 english_summary**：body_end_marker 是附录/法律披露之前的最后一段内容
- body_end_marker 必须是正文内容本身，不能是 english_summary 或附录的标题

> 💡 **完整 LLM 提示词见「附录 A」**

### 1.7 确认摘要和正文（has_abstract / has_body）

### 1.7 展示提取结果并确认

⚠️ **不要问用户"是否有摘要/正文"——已经提取到文件了，直接展示结果让用户确认内容是否正确**

根据 LLM 提取的 `has_abstract`/`has_body` 直接调用 splitter 提取，提取完成后展示结果：

```
【确认摘要和正文】

已提取以下内容：

  内容      文件                  状态
  摘要      abstract.docx (832字符)  ✅
  正文      body.docx (271段落)     ✅
  英文摘要  english_summary.docx (19段落) ✅

确认继续？(y/n)
```

**如果用户回答 n**：
- 询问具体哪个内容有问题
- 必要时重新调用 LLM 提取范围，或让用户手动指定范围

### 1.8 提取摘要和正文

⚠️ **摘要和正文的实际提取必须使用 Python 脚本，不是 LLM**

LLM 只负责**判断位置**，实际内容提取使用 `splitter.py`：

```python
from skills.report_maker.scripts import splitter

if llm_result['has_abstract']:
    splitter.extract_abstract(
        draft_path,
        llm_result['abstract_scope'],
        output_path=f"{output_dir}/abstract.docx",
        appendix_notice=llm_result.get('abstract_notice', '')
    )

if llm_result['has_body']:
    splitter.extract_body(
        draft_path,
        llm_result['body_scope'],
        output_path=f"{output_dir}/body.docx",
        start_marker=llm_result.get('body_start_marker'),
        end_marker=llm_result.get('body_end_marker')
    )

if llm_result.get('has_english_summary'):
    splitter.extract_english_summary(
        draft_path,
        llm_result.get('english_summary_scope', '正文之后一页'),
        output_path=f"{output_dir}/english_summary.docx",
        start_marker=llm_result.get('english_summary_content_start')
    )
```

**格式保留机制**：
- 使用 `deepcopy` 复制 XML 元素，保留所有格式信息
- 摘要：复制单元格内的完整段落（字体、颜色、加粗等）
- 正文：复制整个文档片段（包括图片、表格、目录控件）

### 1.9 确认字段

展示所有提取的字段，等待用户确认或修正：

```
| 字段 | 提取值 | 状态 |
|------|--------|------|
| report_date | `21 Oct 2025` | ✅ |
| company | `西锐飞机` | ✅ |
| ticker | `2507.HK` | ✅ |
| ... | ... | ... |
```

用户可以一次性确认或修正多个字段。

### 1.10 保存结果

将提取结果保存到输出目录：

```
<输出目录>/
├── draft.docx             # 原始草稿（复制）
├── elements.yaml          # 提取的要素（含位置信息）
├── abstract.docx          # 摘要片段（仅当 has_abstract=True 时）
├── body.docx              # 正文片段（仅当 has_body=True 时）
└── english_summary.docx   # 英文摘要片段（仅当 has_english_summary=True 时）
```

**⚠️ 第一阶段完成后必须暂停，展示摘要，等待用户确认后再进入第二阶段**

### 1.11 保存草稿到 neolyst

第一阶段确认后，调用 `save_draft_report` 将机器处理结果保存为 draft：

```python
from skills.neolyst.scripts import save_report

draft_input = {
    "title": elements["title"],
    "report_type": report_type,
    "report_language": report_language,  # 从 title 自动判断
    "analysts": analysts,  # 从 elements.yaml 中 a1~a8 槽位提取并标准化
    "report_file": output_docx_path,  # 最终生成的 Word 文件
    "pdf_file": output_pdf_path,       # 最终生成的 PDF 文件
    # 以下字段可选，提交前补齐
    # "investment_thesis": "...",  # LLM 压缩摘要为 150 字
    # "ticker": "2507.HK",
    # "rating": "OUTPERFORM",
    # "target_price": "86.72",
}

report_id = save_report(client, draft_input)
print(f"已保存 draft，report_id: {report_id}")
```

**保存后**：
- Neolyst 中已存在该 `report_id` 下可查看的第一个 draft 版本
- 用户可以上 Neolyst 查看报告生成情况，人工确认后再继续提交
- 后续补字段、重新保存、重新校验都围绕同一个 `report_id` 进行

---

## 4b. 草稿确认与提交工作流（neolyst 集成）

`report_maker` 提供两个 workflow 函数，支持草稿保存后的完整提交流程：

### `prepare_and_save_draft(report_dir, report_type)`

准备并保存草稿到 neolyst：
- 加载 `report_dir/elements.yaml`
- 加载 `report_dir/draft.docx`（原始草稿）
- 合成最终 Word 和 PDF
- 调用 `save_report` 保存 draft
- 返回 `report_id`

### `submit_report_workflow(report_id)`

提交报告前的校验与提交：
1. 调用 `validate_report(report_id)` 做提交前校验
2. 校验失败时返回完整错误，与用户交互补字段
3. 校验通过后调用 `submit_report(report_id)` 提交为 `submitted`
4. 返回提交版本号

**提交前需确保**：
- 公司类报告需有有效的 `coverage_id`（通过 `resolve_coverage(ticker, first_analyst_email)` 获取）
- `contact_person` 必须属于 `analysts` 列表中的分析师

---

## 5. 第二阶段：渲染与输出

⚠️ **核心原则：渲染阶段完全不需要 LLM 介入**

### 2.1 更新修正数据

加载 `elements.yaml`，应用用户在 1.8 节的修正，保存更新后的 `elements.yaml`

### 2.2 确认文件位置

- 如果 `has_abstract=True` 且 `abstract.docx` 存在：确认文件位置
- 如果 `has_abstract=False`：跳过摘要步骤
- 如果 `has_body=True` 且 `body.docx` 存在：确认文件位置
- 如果 `has_body=False`：跳过正文步骤

**默认文件位置**：
```
abstract: <输出目录>/abstract.docx
body: <输出目录>/body.docx
```

### 2.3 渲染报告

⚠️ **渲染行为由 elements.yaml 中的 has_abstract 和 has_body 决定**

| 内容类型 | 处理方式 | 说明 |
|---------|---------|------|
| elements 字段 | **占位符替换** | `{{company}}` → `西锐飞机`，继承模板格式 |
| 摘要 (abstract) | **deepcopy 插入** | 复制到表格单元格内，继承模板单元格格式 |
| **正文 (body)** | **文档拼接** | 使用 `docxcompose.append()`，**保留 body 自己的页边距** |
| 法律附录 | 从模板直接复制 | 保持模板原样，不做任何修改 |

⚠️ **重要：body 不是占位符填充！**
- body.docx 是独立文档，有自己完整的格式
- 使用 `docxcompose` **拼接**到模板后面，而非填充到占位符
- **模板中不需要 `{{body}}` 占位符**

**完整代码示例**：
```python
from skills.report_maker.scripts import common, renderer
from skills.neolyst.scripts import connection
from pathlib import Path

report_dir = Path('reports/cirrus(2507)_20251021')
elements_path = report_dir / 'elements.yaml'
abstract_path = report_dir / 'abstract.docx'
body_path = report_dir / 'body.docx'

elements = common.load_yaml(elements_path)
output_path = common.get_report_output_path(report_dir, elements)
template_name = "company"
template_path = f'templates/{template_name}/template.docx'

renderer.render_report(
    template_path=template_path,
    elements=elements,
    abstract_path=str(abstract_path),
    body_path=str(body_path),
    output_path=str(output_path),
    english_summary_path=str(report_dir / 'english_summary.docx') if (report_dir / 'english_summary.docx').exists() else None,
)
```

**函数签名**：
```python
def render_report(
    template_path: str,           # 模板文件完整路径
    elements: Dict[str, Any],     # 要素字典
    abstract_path: str,           # 摘要文件路径
    body_path: str,               # 正文文件路径
    output_path: str,             # 输出文件路径
    english_summary_path: str = None,  # 英文摘要路径（可选）
    neolyst_client=None,           # 已认证的 Supabase client（可选，用于获取历史推荐）
) -> bool:
```

### 2.4 验证占位符

⚠️ **必须验证**：渲染后的报告中不存在任何 `{{}}` 占位符

```python
import re
from docx import Document

def verify_no_placeholders(docx_path):
    doc = Document(docx_path)
    placeholders = []
    for para in doc.paragraphs:
        if re.search(r'\{\{.*?\}\}', para.text):
            placeholders.append(para.text)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                if re.search(r'\{\{.*?\}\}', cell.text):
                    placeholders.append(cell.text)
    if placeholders:
        raise ValueError(f"发现未填充的占位符: {placeholders[:5]}")
    return True
```

**如果验证失败**：
- 排查 `elements.yaml` 中是否缺少对应字段
- 或检查模板中是否有额外占位符未在 schema 中定义

### 2.5 转换为 PDF（可选）

```bash
word2pdf convert "<输入文件>" -o "<输出目录>"
```

### 2.6 渲染成功后主动问询

⚠️ **渲染成功后必须主动询问后续操作**，不能直接结束。以下为标准问询流程：

**第一步：报告预览确认**
```
✅ 报告渲染成功！
📄 输出文件：<output_path>
📊 段落数：<N>，表格数：<M>，图片数：<K>
```

**第二步：询问后续操作**（提供选项）
```
请问接下来要：
  1. 转换为 PDF
  2. 提交草稿到 Neolyst 系统
  3. 下载到本地
  4. 仅保存 Word 文档
  5. 退出
```

**第三步：根据选择执行**
- 选择 1 → 执行 `word2pdf convert` → 完成后回到第二步
- 选择 2 → 调用 neolyst 上传草稿接口 → 返回上传结果 → 回到第二步
- 选择 3 → 复制文件到用户指定路径 → 完成后回到第二步
- 选择 4 → 仅保存，结束流程
- 选择 5 → 结束流程

**问询原则**：
- 渲染成功后**必须**询问，不能静默结束
- 每个操作完成后**必须**回到第二步再次询问
- 只有明确选择"退出"才终止流程

---

## 6. 输出文件结构

渲染完成后的报告目录结构：

```
reports/<report_name>/
├── draft.docx               # 原始草稿
├── elements.yaml            # 提取的要素
├── abstract.docx            # 摘要片段
├── body.docx                # 正文片段
├── english_summary.docx     # 英文摘要片段（如有）
├── 公司名(ticker)：标题.docx  # ✅ 最终 Word 文档
└── 公司名(ticker)：标题.pdf   # ✅ 最终 PDF（可选）
```

---

## 7. 数据格式规范

### elements.yaml 格式

**必须与 schema.yaml 严格保持一致**：

```yaml
# 所有字段都存在，空字段用空字符串
report_date: "21 Oct 2025"
company: "西锐飞机"
ticker: "2507.HK"
title: "首次覆盖：..."
rating: "OUTPERFORM"
current_price: "60.40"
target_price: "86.72"
market_cap: "22.11bn"
shares_in_issue: "365.99mn"
one_year_high: "73.40"
one_year_low: "20.50"
current_price_date: "2026 年 01 月 15 日"
analysts: "[{'chinese_name': '杨斌', 'english_name': 'Bin Yang', 'sfc_code': 'BSQ313', 'email': 'harryyang@hfisec.com.hk'}]"
source: "xxx"
abstract: "abstract.docx"
body: "body.docx"
english_summary: "english_summary.docx"
```

**字段一致性要求**：
- 字段名称相同
- 字段顺序相同
- 字段数量相同
- 空字段也必须存在（值为 `""`）

---

## 附录 A：LLM 提取提示词（完整版）

> 本附录包含完整的 LLM 提取提示词，供复制使用。

```
请分析这份研究报告草稿，一次性提取以下所有内容：

## 第一部分：字段提取
根据 schema.yaml 中定义的字段，从草稿中提取数据：
{schema_yaml_内容}

### 🔴 强制搜索要求（必须遵守）

**Word 文档表格结构说明**：
- 研究报告的封面通常是一个大表格，里面嵌套了多层子表格
- 关键数据（价格、市值、分析师等）通常在 2-3 层嵌套的子表格中
- 你必须深入到**每一层嵌套表格**中搜索字段

**强制搜索路径**（按顺序执行）：
1. **封面主表格** → 提取：report_date, company, ticker, title, rating, target_price
2. **封面右侧/底部的侧边栏嵌套表格** → 提取：
   - current_price（当前价格，通常标注为"现价"或"Price"）
   - current_price_date（从注释文字中提取，如"注：现价X为YYYY年MM月DD日收盘价"）
   - market_cap（市值）
   - shares_in_issue（发行股数/流通股）
   - one_year_high / one_year_low（52周高低点）
   - source（资料来源）
3. **封面底部或末页的分析师嵌套表格** → 提取：
   - a1_cn（中文名）、a1_en（英文名）、a1_sfc（SFC执照号）、a1_email
   - 同样检查 a2-a8

**⚠️ 禁止行为**：
- ❌ 在主表格找到部分字段后就停止搜索
- ❌ 看到字段为空就直接返回空值
- ❌ 假设某些字段不存在

**✅ 必须行为**：
- ✅ 遍历所有表格的所有单元格
- ✅ 对每个单元格，检查其内部是否还有嵌套表格
- ✅ 递归搜索直到最深层
- ✅ 如果某字段确实不存在，在返回结果中说明"未找到"

## 第二部分：摘要提取

**摘要特征**：
- 位置：首页表格或嵌套表格内，通常位于封面右侧或底部区域
- 内容：包含多个完整段落（通常3-6段），每段有独立的语义内容
- 格式：与单行简短数据不同，摘要是大段文本，可能跨多个单元格

**⚠️ 识别陷阱**：
- ❌ 不要把单行数据（如"目标价：40元"）误认为摘要
- ❌ 不要把表格中的单个单元格内容当作摘要
- ✅ 摘要必须是多段落、有完整语义的内容块

## 第三部分：正文提取

**body 起始特征**：
- **body 不从第一页开始**：第一页是封面
- **起始标记通常是"目录"或"第一章标题"**

**⚠️ body 的结束边界规则**：
- **如果有 english_summary**：body_end_marker 应该是 english_summary 标题之前的最后一段内容
- **如果没有 english_summary**：body_end_marker 应该是附录/法律披露之前的最后一段内容
- body_end_marker 必须是正文内容本身，不能是 english_summary 或附录的标题

## 第四部分：英文摘要提取

**⚠️ 关键提醒：英文摘要可能在段落中，不仅仅是表格！**
- 英文摘要的 "Summary" 标题通常在**段落**中
- 预处理提供了段落索引 `[P{idx}]`
- 英文摘要在最后 50 个段落内，即 `[P{total-50}]` 到 `[P{total}]` 之间

**常见标题形式**：
- `Summary`
- `APPENDIX 1`
- `APPENDIX 1 Summary`
- `Executive Summary`

**⚠️ 注意区分**：
- ❌ 法律附录的 "附录APPENDIX" 不是英文摘要
- ✅ 正文后、法律附录前的 "Summary" 才是英文摘要

**⚠️ 英文摘要内容起始必须是正文第一句，不是标题**：
- ❌ 错误：`english_summary_content_start: "Summary"` （这是标题）
- ✅ 正确：`english_summary_content_start: "Initial Coverage on Wasion Holdings"` （正文第一句）
```

---

## 附录 B：技术参考

> 本部分说明渲染实现的技术细节，用于问题排查和功能扩展。

### B.1 法律附录识别规则

**识别条件**（满足任一即可）：
1. 开头必定是：`附录APPENDIX`
2. 前面有分页符（单独一页）

**附录范围**：从"附录APPENDIX"开始到整个文档末尾

### B.2 文档合并流程

1. **查找附录**：在 template 中搜索包含"附录APPENDIX"的段落
2. **提取附录**：从附录起始位置到文档末尾的所有元素
3. **删除附录**：从 template 中移除附录部分
4. **替换占位符**：通过 XML 替换所有字段占位符
5. **插入 abstract**：将 abstract 内容插入到表格单元格
6. **合并 body**：使用 docxcompose.append() 插入 body
7. **追加附录**：将提取的附录直接追加到文档末尾

### B.3 空白页问题处理

**原因**：
1. sectPr 分节符：每个 sectPr type=nextPage 会强制换页
2. 连续空段落：body.docx 开头可能有多个空段落

**解决方案**：
1. 追加前删除 body.docx 所有 sectPr（除了末尾的）
2. 删除 body.docx 开头的空段落（保留目录控件 sdt）

---

## 附录 C：模板依赖关系

| 文件 | 作用 |
|------|------|
| `schema.yaml` | **字段清单**（提取什么） |
| `template.docx` | **位置地图**（在哪里提取） |
| `elements.yaml` | **提取结果**（必须严格按照 schema） |

---

## 注意事项（速查）

| # | 规则 |
|---|------|
| 1 | 第一阶段必须用 LLM 提取，禁止硬编码 |
| 2 | 第二阶段无 LLM，纯 Python 脚本 |
| 3 | body 是拼接不是填充，模板无需 `{{body}}` |
| 4 | 禁止访问项目外路径 |
| 5 | 必须保留空字段，值为 `""` |
| 6 | 交互确认不能跳过 |
| 7 | 只读 templates/，不修改模板 |
| 8 | 只读 templates/，不修改模板资产 |
