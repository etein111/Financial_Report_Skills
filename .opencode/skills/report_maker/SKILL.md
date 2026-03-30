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

### 1. 询问基本信息（逐个询问）

```
问题 1/4：草稿文件在哪里？
- 等待用户提供 .docx 文件路径

问题 2/4：报告名称是什么？（用于命名输出目录）
- 等待用户回答，提供单一的缺省建议值

问题 3/4：请确认输出目录位置
- 等待用户选择（可以选已有目录，或新建目录）
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

### 2. 自动查找可用模板

在**当前工作目录**下的 `templates/` 目录中查找所有可用的模板。

**查找方法**：
```bash
# 列出 templates/ 下的所有子目录（每个子目录是一个模板）
ls -d templates/*/
```

**模板目录结构**：
```
templates/
├── company/          # 公司完整报告模板
├── sector/           # 行业报告模板
├── macro/            # 宏观报告模板
├── flash/            # 快讯模板
└── ...               # 其他模板
```

每个模板目录必须包含：
- `schema.yaml` - **定义要提取哪些字段**
- `template.docx` - **Word 模板文件**

### 3. 展示可用模板并让用户确认

**问题 4/4：请选择使用的模板**

展示找到的所有可用模板供用户选择：

```
可用模板列表：
1. company      - 公司完整报告
2. sector       - 行业报告
3. macro        - 宏观报告
4. flash        - 快讯

请选择模板编号或直接输入模板名称：
```

- 等待用户选择
- 用户可以直接输入模板名称（如 `company`）
- 如果只有一个模板，可以直接询问"是否使用 {模板名} 模板？"

### 4. 加载选定的模板

根据用户选择的模板名称，加载对应的模板文件：

```python
# 模板路径（在当前工作目录下）
template_name = "company"  # 用户选择的模板
template_path = f"templates/{template_name}/template.docx"
schema_path = f"templates/{template_name}/schema.yaml"

# 加载 schema
import yaml
with open(schema_path, 'r', encoding='utf-8') as f:
    schema = yaml.safe_load(f)
```

⚠️ **重要**：模板路径基于当前工作目录，确保 `templates/` 目录存在且包含用户选择的模板。

### 5. 提取字段

**⚠️ 核心原则**：
- **schema.yaml** 明确要提取哪些字段
- **template.docx** 明确字段在文档中的位置（占位符位置）
- **elements.yaml** 必须严格按照 schema.yaml 的字段（顺序、名称、类型）

**使用自动化提取**（默认，推荐）：

```bash
python3 -c "
from skills.report_maker.scripts import extractor, common

# 加载 schema
schema = common.load_yaml(f'templates/{template_name}/schema.yaml')

# 执行提取（从草稿中提取 schema 中定义的字段）
elements = extractor.extract_elements(draft_path, schema)

# 确保所有字段存在（与 schema 严格一致）
elements = common.ensure_all_fields(elements, schema)
"
```

自动化提取功能现已完善，可以正确处理：
- ✅ 嵌套表格中的财务数据（current_price, target_price, market_cap 等）
- ✅ 组合字段的拆分（one_year_high/low 从 "73.40-20.50" 拆分）
- ✅ 从注释中提取的数据（current_price_date）
- ✅ 特殊格式化字段（analysts）
- ✅ 保留单位（22.11bn, 365.99mn）

**或使用 LLM 辅助提取**（仅在自动化提取完全失败时）：

将草稿内容和 schema.yaml 发送给 LLM，LLM 根据 schema 中的字段定义提取数据。

**⚠️ 关键技术提示：嵌套表格处理**

- python-docx 的 `cell.text` 只返回直接段落文本，**不包括嵌套表格**
- 许多关键字段（如 current_price, market_cap 等）在首页表格的**嵌套表格**中
- 本 skill 已在 `docx_reader.py` 和 `field_extractor.py` 中实现自动化递归读取

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
```

用户可以一次性确认或修正多个字段。

### 7. 确保所有字段存在

- elements.yaml 必须与 schema.yaml 严格对应
- 空字段使用空字符串 `""`，不要省略

### 8. 拆分摘要和正文

根据 schema 中 `abstract.scope` 和 `body.scope` 提取内容，保存为 `abstract.docx` 和 `body.docx`

### 9. 保存结果

将提取结果保存到用户指定的输出目录：

```
<用户指定目录>/
├── draft.docx           # 原始草稿（可选）
├── elements.yaml        # 提取的要素
├── abstract.docx        # 摘要片段
└── body.docx            # 正文片段
```

### 10. 展示摘要并暂停

展示提取结果摘要，等待用户确认或修正

---

## 第二阶段：渲染与输出

### 1. 更新修正数据

加载 `elements.yaml`，应用用户修正，保存更新后的 `elements.yaml`

### 2. 确认 abstract 和 body 位置

**显式询问 abstract.docx 和 body.docx 的位置**：

```
问题：abstract.docx 在哪里？
- 等待用户提供文件路径
- 默认值：<输出目录>/abstract.docx

问题：body.docx 在哪里？
- 等待用户提供文件路径
- 默认值：<输出目录>/body.docx
```

### 3. 渲染报告

使用 `renderer.render_report()` 函数完成以下操作：
- 渲染短字段到模板（使用 Jinja2 替换占位符）
- 插入摘要和正文片段（使用 docxcompose 合并文档）
- 保存最终输出文件

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
2. **模板目录** - 模板在当前工作目录的 `templates/` 下
3. **输出位置** - 报告保存在用户指定的输出目录下的 `output.docx`
4. **依赖检查** - 确保已安装 docxtpl 和 docxcompose
5. **空字段处理** - 必须保留空字段，值为 `""`
6. **字段严格一致性** - elements.yaml 必须与 schema.yaml 完全一致
   - 字段名称相同
   - 字段顺序相同
   - 字段数量相同
   - 空字段也必须存在（值为 `""`）
7. **模板依赖关系**：
   - **schema.yaml** 是"字段清单"（提取什么）
   - **template.docx** 是"位置地图"（在哪里提取）
   - **elements.yaml** 是"提取结果"（必须严格按照 schema）
8. **模板切换限制** - 只能在第一阶段切换模板，第二阶段不支持切换
9. **只读 templates/** - report_maker 永远不修改模板资产
10. **自动化提取能力** - 现已支持一次性正确提取所有字段，包括嵌套表格、组合字段拆分、注释提取、特殊格式化等

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
