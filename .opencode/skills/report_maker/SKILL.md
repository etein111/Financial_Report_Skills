---
name: report_maker
description: "当用户说「做研报」、「生成报告」、「写研报」、「处理研报」、「生成研究报告」或上传报告草稿（.docx）时使用此技能。负责解析 Word 草稿、提取要素、交互确认，生成标准格式的研究报告。**必须使用中文与用户沟通**。"
---

# Report Maker - 研究报告生成

**工作流程**：抽取确认 → 渲染输出 → 用户指定位置保存

**文件交互**：
- 询问用户输入文件（草稿 .docx）的路径
- 询问用户输出目录位置（可以选择已有目录，或新建目录）
- 最终输出文件保存在用户指定的输出目录下的 `output.docx`

---

## 使用条件

**触发场景**：
- 用户上传报告草稿（.docx），说"生成标准排版报告"
- 用户说"处理这篇草稿"、"解析报告"、"提取报告要素"
- Editor 需要修正已提取的要素或继续生成报告

**不适用**：创建/修改模板 → 使用 `template_maker`

**语言要求**：必须使用中文与用户沟通

**报告类型**：company, sector, macro, strategy, quantitative, bond

---

## 依赖检查

**必需的 Python 包**：
- `python-docx` - Word 文档操作
- `docxtpl` - Jinja2 模板渲染
- `docxcompose` - 文档合并
- `PyYAML` - YAML 配置文件

**检查命令**：
```bash
python3 -c "import docx, docxtpl, docxcompose, yaml; print('✓ 所有依赖已安装')"
```

**安装命令**（如需安装）：
```bash
# 优先使用 uv（项目规范）
uv pip install "docxtpl>=0.20.0" docxcompose

# 如果 uv 不可用，先安装 uv
# Linux/Mac:
curl -LsSf https://astral.sh/uv/install.sh | sh

# 或使用 pip:
pip install uv

# 回退方案：使用 pip3（不推荐）
pip3 install --break-system-packages "docxtpl>=0.20.0" docxcompose
```

---

## 第一阶段：抽取与确认

### 1. 选择报告类型并自动扫描草稿

**步骤 1/4：选择报告类型**

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

您的选择:
```

**步骤 2/4：自动扫描草稿文件**

**在当前工作目录下**扫描草稿文件和对应的 elements.yaml：

```
您的选择: company

正在扫描当前目录...
找到以下草稿文档：
  1. 西锐飞机首次覆盖报告（中文）提交版.docx
  2. Bloom Energy Corporation 1231.docx
  3. EN-Vistra Corp20260104.docx

请选择要处理的草稿文档（输入编号）:
```

**扫描规则**：
- 扫描**当前工作目录**下的 `.docx` 文件
- 排除以 `~$` 开头的临时文件
- 排除 `_AutoRefresh` 后缀的文件（这些是生成的 PDF 预览）

**自动查找 elements.yaml**：
选择草稿文档后，系统自动在同目录下查找匹配的 elements.yaml：
- `{文件名} elements.yaml`（如 `西锐飞机 elements.yaml`）
- `{文件名}_elements.yaml`
- `elements.yaml`（通用配置）

**报告类型与模板映射**：

| 报告类型 | 使用模板 |
|---------|---------|
| company | company |
| sector | sector |
| flash | flash |
| company_flash | company_flash |
| sector_flash | sector_flash |
| macro | macro |
| strategy | common |
| quantitative | common |
| bond | common |

### 2. 确认输出目录

**步骤 3/4：确认报告名称和输出目录**

根据选择的草稿文件，自动生成建议的报告名称：

```
【确认输出目录】
草稿文件: 西锐飞机首次覆盖报告（中文）提交版.docx
建议报告名称: cirrus(2507)_20260331

请确认报告名称（直接回车使用建议值，或输入新名称）:

输出目录将创建在: reports/cirrus(2507)_20260331/
确认？(y/n)
```

**命名规则**（日期统一放在最后）：

| 报告类型 | 格式 | 示例 |
|---------|------|------|
| company | `{公司简写}({ticker})_{日期}` | `cirrus(2507)_20251021` |
| 其他类型 | `{核心主题词}_{日期}` | `new_energy_20251021` |

**主题词提取原则**：
- 提取"讲了什么"（主题），跳过"怎么讲的"（描述）
- ✅ 主题词：新能源汽车、AI芯片、美联储、利率政策
- ❌ 描述性词汇：深度分析、研究、报告、解读、提交版

### 3. 自动加载对应模板

**步骤 4/4：自动加载模板**

根据步骤 1 选择的报告类型，自动确定并加载对应的模板：

```
【加载模板】
报告类型: company
使用模板: templates/company/
✓ 已加载 schema.yaml（25 个字段）
✓ 已加载 template.docx
```

**模板目录结构**：
```
templates/
├── company/          # 公司完整报告模板
├── sector/           # 行业报告模板
├── macro/            # 宏观报告模板
├── flash/            # 快讯模板
├── common/           # 通用模板（strategy/quantitative/bond 共用）
└── ...               # 其他模板
```

每个模板目录必须包含：
- `schema.yaml` - **定义要提取哪些字段**
- `template.docx` - **Word 模板文件**

### 4. 🔑 一次性提取 elements + 摘要 + 正文（核心步骤）

**⚠️ 核心原则：LLM 一次性完成所有提取工作**

将草稿内容和 schema.yaml 发送给 LLM，在**一次调用中**完成：
1. 提取所有 elements 字段
2. 判断并提取摘要内容
3. 判断并提取正文内容

**LLM 提取提示词**：

```
请分析这份研究报告草稿，一次性提取以下所有内容：

## 第一部分：字段提取
根据 schema.yaml 中定义的字段，从草稿中提取数据：
{schema_yaml_内容}

⚠️ 注意：很多字段嵌套在表格单元格中，请仔细检查所有表格内容。
常见嵌套位置：
- 封面表格：公司名、股票代码、评级、目标价
- 侧边栏表格（通常在封面右侧或底部）：
  - current_price（当前价格）
  - current_price_date（价格日期）
  - market_cap（市值）
  - shares_in_issue（流通股）
  - one_year_high / one_year_low（52周高低点）
  - source（数据来源）
- 分析师信息表格（通常在封面底部或末页）：
  - 分析师中文名、英文名
  - SFC 代码
  - 邮箱

## 第二部分：摘要提取
1. 是否有摘要部分？（摘要通常是首页右侧的投资亮点、核心观点区域）
2. 如果有摘要，请指出摘要的精确位置（如"首页右侧表格的第X行第Y列单元格"）
3. has_abstract: true/false
4. abstract_scope: "位置描述"

## 第三部分：正文提取
1. 是否有正文部分？（正文是报告的主要分析内容，从目录或第一章开始）
2. 如果有正文，请指出正文的起始位置（如"从目录开始"或"从第N页开始"）
3. has_body: true/false
4. body_scope: "位置描述"

## 输出格式
请返回 YAML 格式：
```yaml
# 字段数据
report_date: "..."
company: "..."
ticker: "..."
# ... 其他 schema 中定义的字段 ...

# 摘要信息
has_abstract: true/false
abstract_scope: "位置描述"

# 正文信息
has_body: true/false
body_scope: "位置描述"
```
```

**LLM 返回结果解析**：

```python
# LLM 返回的数据
llm_result = {
    # elements 字段
    "report_date": "21 Oct 2025",
    "company": "西锐飞机",
    "ticker": "2507.HK",
    "current_price": "60.40",
    # ... 其他字段 ...

    # 摘要/正文信息
    "has_abstract": True,
    "abstract_scope": "首页右侧表格",
    "has_body": True,
    "body_scope": "从目录开始，到附录之前"
}

# 分离 elements 和位置信息
elements = {k: v for k, v in llm_result.items()
            if k not in ['has_abstract', 'abstract_scope', 'has_body', 'body_scope']}
```

**关键优势**：
- ✅ 减少 LLM 调用次数（从多次降为一次）
- ✅ LLM 对整体报告结构有更完整的理解
- ✅ 避免字段提取和位置判断的信息不一致

### 5. 使用脚本提取摘要和正文（保留原始格式）

**⚠️ 重要：摘要和正文的实际提取必须使用 Python 脚本，不是 LLM**

LLM 只负责**判断位置**，实际的内容提取使用 `splitter.py` 中的函数，
确保**完整保留原始格式**（字体、加粗、图片、表格等）。

```python
from skills.report_maker.scripts import splitter

# 根据 LLM 返回的位置信息，使用脚本提取
if llm_result['has_abstract']:
    splitter.extract_abstract(
        draft_path,
        llm_result['abstract_scope'],
        output_path=f"{output_dir}/abstract.docx"
    )

if llm_result['has_body']:
    splitter.extract_body(
        draft_path,
        llm_result['body_scope'],
        output_path=f"{output_dir}/body.docx"
    )
```

**格式保留机制**：
- 使用 `deepcopy` 复制 XML 元素，保留所有格式信息
- 摘要：复制单元格内的完整段落（字体、颜色、加粗等）
- 正文：复制整个文档片段（包括图片、表格、目录控件）

### 6. 一次性确认所有字段

**展示所有提取的字段（表格形式）**：

```
| 字段 | 提取值 | 状态 |
|------|--------|------|
| report_date | `21 Oct 2025` | ✅ |
| company | `西锐飞机` | ✅ |
| ticker | `2507.HK` | ✅ |
| current_price | `60.40` | ✅ |
| ... | ... | ... |
| has_abstract | `True` | ✅ |
| abstract_scope | `首页右侧表格` | ✅ |
| has_body | `True` | ✅ |
| body_scope | `从目录开始` | ✅ |
```

用户可以一次性确认或修正多个字段。

### 7. 保存结果

将提取结果保存到用户指定的输出目录：

```
<输出目录>/
├── draft.docx           # 原始草稿（复制）
├── elements.yaml        # 提取的要素（含位置信息）
├── abstract.docx        # 摘要片段（仅当 has_abstract=True 时，完整保留格式）
└── body.docx            # 正文片段（仅当 has_body=True 时，完整保留格式）
```

### 8. 展示摘要并暂停

展示提取结果摘要，等待用户确认或修正

---

## 第二阶段：渲染与输出

**⚠️ 核心原则：渲染阶段完全不需要 LLM 介入**

第二阶段使用纯 Python 脚本（`renderer.py`）直接合成报告：
- ✅ 通过 XML 替换占位符填充字段
- ✅ 使用 `deepcopy` 插入摘要（完整保留格式）
- ✅ 使用 `docxcompose` 合并正文（完整保留格式、图片、表格）
- ✅ 自动处理法律附录

### 1. 更新修正数据

加载 `elements.yaml`，应用用户修正，保存更新后的 `elements.yaml`

### 2. 确认 abstract 和 body 文件位置

- 如果 `has_abstract=True` 且 `abstract.docx` 存在：确认文件位置
- 如果 `has_abstract=False`：跳过摘要步骤
- 如果 `has_body=True` 且 `body.docx` 存在：确认文件位置
- 如果 `has_body=False`：跳过正文步骤

**默认文件位置**：
```
abstract: <输出目录>/abstract.docx
body: <输出目录>/body.docx
```

### 3. 渲染报告（纯脚本，无 LLM）

**渲染行为由 elements.yaml 中的 has_abstract 和 has_body 决定**：

- 如果 `has_abstract=True`：插入摘要到模板（完整保留原始格式）
- 如果 `has_abstract=False`：跳过摘要插入
- 如果 `has_body=True`：合并正文到模板（完整保留原始格式、图片、表格）
- 如果 `has_body=False`：跳过正文合并

**⚠️ 内容处理方式（关键区别）**：

| 内容类型 | 处理方式 | 说明 |
|---------|---------|------|
| elements 字段 | **占位符替换** | `{{company}}` → `西锐飞机`，继承模板格式 |
| 摘要 (abstract) | **deepcopy 插入** | 复制到表格单元格内，继承模板单元格格式 |
| **正文 (body)** | **文档拼接** | 使用 `docxcompose.append()`，**保留 body 自己的页边距** |
| 法律附录 | 从模板直接复制 | 保持模板原样，不做任何修改 |

**⚠️ 重要：body 不是占位符填充！**
- body.docx 是独立文档，有自己完整的格式（页边距、页眉页脚等）
- 使用 `docxcompose` **拼接**到模板后面，而非填充到占位符
- **模板中不需要 `{{body}}` 占位符**
- 如果用占位符填充 body，会导致 body 丢失自己的页边距，继承模板格式

使用 `renderer.render_report()` 函数完成以下操作：
1. 通过 XML 级别替换所有占位符（不破坏嵌套表格结构）
2. 插入摘要到表格单元格（使用 deepcopy 保留格式）
3. 使用 docxcompose 合并正文（保留图片和表格）
4. 追加法律附录
5. 保存最终输出文件

**完整代码示例**：

```python
from skills.report_maker.scripts import common, renderer
from pathlib import Path

# 报告路径（根据实际情况调整）
report_dir = Path('reports/cirrus(2507)_20251021')
elements_path = report_dir / 'elements.yaml'
abstract_path = report_dir / 'abstract.docx'
body_path = report_dir / 'body.docx'
output_path = report_dir / 'output.docx'

# 模板路径（用户已确认选择的模板）
template_name = "company"  # 用户选择的模板
template_path = f'templates/{template_name}/template.docx'

# 加载 elements.yaml
elements = common.load_yaml(elements_path)

# 渲染报告
renderer.render_report(
    template_path=template_path,    # 模板文件完整路径
    elements=elements,               # 要素字典（从 elements.yaml 加载）
    abstract_path=str(abstract_path), # 摘要文件路径
    body_path=str(body_path),        # 正文文件路径
    output_path=str(output_path)     # 输出文件路径
)

print(f'✓ 报告已生成: {output_path}')
```

**函数签名**：

```python
def render_report(
    template_path: str,      # 模板文件完整路径（相对于项目根目录）
    elements: Dict[str, Any], # 要素字典（从 elements.yaml 加载）
    abstract_path: str,      # 摘要文件路径
    body_path: str,          # 正文文件路径
    output_path: str         # 输出文件路径
) -> bool:
    """渲染报告，正确处理分析师字段、abstract 和 body。

    Returns:
        bool: 是否成功
    """
```

**参数说明**：

| 参数 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `template_path` | `str` | 模板文件的完整相对路径 | `templates/company/template.docx` |
| `elements` | `Dict` | 从 `elements.yaml` 加载的要素字典 | `{'report_date': '21 Oct 2025', ...}` |
| `abstract_path` | `str` | 摘要片段文件路径 | `reports/cirrus(2507)_20251021/abstract.docx` |
| `body_path` | `str` | 正文片段文件路径 | `reports/cirrus(2507)_20251021/body.docx` |
| `output_path` | `str` | 输出文件路径 | `reports/cirrus(2507)_20251021/output.docx` |

### 4. 验证占位符填充

**必须验证**：渲染后的 output.docx 中不存在任何 `{{}}` 占位符。

```python
import re

def verify_no_placeholders(docx_path):
    """验证 Word 文档中没有遗留的占位符"""
    from docx import Document
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
- 报告中有未替换的占位符
- 必须排查 `elements.yaml` 中是否缺少对应字段
- 或检查模板中是否有额外占位符未在 schema 中定义

### 5. 转换为 PDF（可选）

使用 `word2pdf` 将 Word 文档转换为 PDF：

```bash
# 语法：word2pdf convert "<输入文件>" -o "<输出目录>"
word2pdf convert "C:\reports\report1.docx" -o "C:\reports"
```

### 6. 输出文件结构

渲染完成后的报告目录结构：

```
reports/<report_name>/
├── draft.docx           # 原始草稿
├── elements.yaml        # 提取的要素
├── abstract.docx        # 摘要片段
├── body.docx            # 正文片段
├── output.docx          # ✅ 最终 Word 文档
└── output.pdf           # ✅ 最终 PDF 文档（可选）
```

---

## 数据格式规范

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
```

---

## 注意事项

1. **交互式确认是必须的** - 不能跳过第一阶段直接生成
2. **LLM 只用于第一阶段** - 一次性提取 elements + 摘要位置 + 正文位置
3. **第二阶段无 LLM** - 渲染完全使用 Python 脚本，不需要 LLM 介入
4. **格式保留是关键** - 摘要和正文必须保留原始格式（字体、图片、表格等）
5. **工作目录要求** - 所有操作必须从项目根目录执行，否则找不到模板文件
6. **输出位置** - 报告保存在用户指定的输出目录下的 `output.docx`
7. **依赖检查** - 确保已安装 docxtpl 和 docxcompose
8. **空字段处理** - 必须保留空字段，值为 `""`
9. **字段严格一致性** - elements.yaml 必须与 schema.yaml 完全一致
   - 字段名称相同
   - 字段顺序相同
   - 字段数量相同
   - 空字段也必须存在（值为 `""`）
10. **模板依赖关系**：
    - **schema.yaml** 是"字段清单"（提取什么）
    - **template.docx** 是"位置地图"（在哪里提取）
    - **elements.yaml** 是"提取结果"（必须严格按照 schema）
11. **模板切换限制** - 只能在第一阶段切换模板，第二阶段不支持切换
12. **只读 templates/** - report_maker 永远不修改模板资产
13. **body 是拼接不是填充** - body.docx 使用 docxcompose 拼接，保留自己的页边距；模板中无需 `{{body}}` 占位符

---

## 技术参考（仅供开发参考）

> 本部分详细说明了渲染实现的技术细节，用于问题排查和功能扩展。

### 法律附录识别规则

**识别条件**（满足任一即可）：
1. 开头必定是：`附录APPENDIX`
2. 前面有分页符（单独一页）

**附录范围**：从"附录APPENDIX"开始到整个文档末尾的所有内容

### 文档合并流程

渲染使用 **docxcompose** 合并 body.docx，流程如下：

1. **查找附录**：在 template 中搜索包含"附录APPENDIX"的段落，确定附录起始位置
2. **提取附录**：从附录起始位置到文档末尾的所有元素（包括 sectPr）
3. **删除附录**：从 template 中移除附录部分
4. **替换占位符**：通过 XML 替换所有字段占位符
5. **插入 abstract**：将 abstract 内容插入到表格单元格
6. **合并 body**：使用 docxcompose.append() 插入 body
7. **追加附录**：将提取的附录直接追加到文档末尾
8. **恢复 sectPr**：确保文档末尾有正确的 sectPr

### 附录处理原则

**关键原则**：附录完全来自 template，不做任何修改

```
Output 结构：
- 封面（保持 template 原样）
- 正文（使用 body.docx 的页边距）
- 法律附录（直接追加，保持 template 原样）
```

### 空白页问题处理

**原因**：
1. sectPr 分节符：每个 sectPr type=nextPage 会强制换页
2. 连续空段落：大量空段落会占用页面空间
3. 文档开头空段落：body.docx 开头可能有多个空段落

**解决方案**：
1. 追加前删除 body.docx 所有 sectPr（除了末尾的）
2. 删除 body.docx 开头的空段落（保留目录控件 sdt）

### Abstract 插入

abstract 插入到表格单元格，使用 deepcopy 保留完整格式：
- 删除单元格内所有段落
- 逐段复制 abstract.docx 内容（保留字体、颜色等格式）