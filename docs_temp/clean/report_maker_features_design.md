# Report Maker 功能设计文档

本文档描述 report_maker 三个核心功能的设计实现。

## 1. 拆草稿 (Draft Splitting)

### 1.1 功能概述

将原始研究报告（草稿）拆分为三个独立片段：
- **摘要 (abstract)**: 首页右侧或正文开头的摘要区域
- **正文 (body)**: 正文内容（从目录/第一章到最后附录之前）
- **法律附录 (appendix)**: 保留在最终输出中

### 1.2 嵌套表格读取

python-docx 的 `doc.tables` 会漏读嵌套表格。改用 lxml 直接解析 `document.xml`：

```python
from lxml import etree
with zipfile.ZipFile(doc_path, 'r') as z:
    with z.open('word/document.xml') as f:
        tree = etree.parse(f)
# 访问所有 <w:tbl> 元素，包括嵌套在单元格中的
```

### 1.3 提取策略

#### 摘要提取 (`extract_abstract`)

**策略1**: 从首页表格中查找
- 遍历第一个表格的所有单元格
- 匹配摘要特征：公司名关键词、长度 > 200 字符
- 使用 `deepcopy` 复制段落，保留格式

**策略2**: 从段落中按标记查找
- 起始标记：`摘要`、`投资亮点`、`核心观点`
- 结束标记：`目录`、`1 `、`1.`

#### 正文提取 (`extract_body`)

**核心策略**: "复制整个文档 → 删除范围外元素"

```
shutil.copy(draft_path, body.docx)   # 复制整个文档（保留图片引用和格式）
doc = Document(output_path)
# 找到正文范围，删除范围外元素
doc.save(output_path)
```

复制而非重建，保留图片引用关系（`word/_rels/document.xml.rels`）和全部格式。

**正文范围判定**:
- **起始位置**: 目录位置 或 第一章标题
- **结束位置**: `重要信息披露`、`[Table_disclaimer]`、`APPENDIX`、`附录`

### 1.4 其他提取方式

| 函数 | 方式 | 适用场景 |
|------|------|----------|
| `extract_fragment_by_table_range` | 按表格索引范围 | 指定表格区域 |
| `extract_fragment_by_paragraph_range` | 按段落索引范围 | 指定段落区域 |
| `extract_fragment_by_keywords` | 按关键词定位 | 已知内容特征 |

### 1.5 关键代码片段

```python
# 使用 lxml 获取所有表格（包括嵌套）
def _get_all_tables_lxml(doc_path):
    with zipfile.ZipFile(doc_path, 'r') as z:
        with z.open('word/document.xml') as f:
            tree = etree.parse(f).getroot()
    return list(tree.iter(f'{W}tbl'))

# 复制整个文档，删除范围外元素
def extract_body(draft_path, output_path):
    shutil.copy(draft_path, output_path)  # 复制全部
    doc = Document(output_path)
    body = doc.element.body
    elements = list(body)

    # 找到正文范围...
    # 删除 start_idx 之前和 end_idx 之后的元素

    doc.save(output_path)
```

---

## 2. 合成报告 (Report Composition)

### 2.1 功能概述

将渲染后的模板（已填充短字段）与摘要片段、正文片段合并，生成最终报告。

### 2.2 核心挑战

| 挑战 | 解决方案 |
|------|----------|
| docxtpl 破坏嵌套表格 | MARKER 机制分步处理 |
| docxcompose 丢失图片/破坏页边距 | `_copy_media_between_docx` + `_remove_docxcompose_extra_sectPr` |

### 2.3 渲染流程

```
┌─────────────────┐
│   模板 (Jinja2)  │  ← 包含 {{ abstract }} 和 {{ body }} 占位符
└────────┬────────┘
         │ docxtpl 渲染
         ▼
┌─────────────────┐
│  渲染后模板      │  ← {{ abstract }} → ABSTRACT_MARKER
│  (temp_path)    │  ← {{ body }} → BODY_MARKER
└────────┬────────┘
         │
         ├──────────────────────────────┐
         │                              │
         ▼                              ▼
┌─────────────────┐          ┌─────────────────┐
│  插入 abstract   │          │  插入 body       │
│  (ABSTRACT_MARKER)│          │  (BODY_MARKER)  │
└────────┬────────┘          └────────┬────────┘
         │                              │
         └──────────────┬───────────────┘
                        ▼
              ┌─────────────────┐
              │   最终报告       │
              │  (output.docx)  │
              └─────────────────┘
```

### 2.4 MARKER 机制

用文本标记替代 Jinja2 占位符，避免 docxtpl 破坏嵌套表格：

```python
ABSTRACT_MARKER = '###ABSTRACT_MARKER###'
BODY_MARKER = '###BODY_MARKER###'

# 在渲染上下文中
context['abstract'] = ABSTRACT_MARKER
context['body'] = BODY_MARKER

# docxtpl 渲染后，占位符被替换为 MARKER 文本
# 然后在 MARKER 位置插入实际的 fragment 内容
```

### 2.5 三段式合并

docxcompose 将文档分为三部分合并：Part1（marker 前）+ Body（draft）+ Part3（marker 后）。

代码位置：`insert_body_at_marker_compose()` (renderer.py:844-950)

### 2.6 图表 Jinja2 语法处理

**问题**: Flash 模板中的图表 XML 包含 `{{ Chart }}` 等文本，被 docxtpl 误解析。

**解决**: 转义 → 渲染 → 恢复

```python
# 1. 渲染前：转义图表中的 {{ 为 &#123;&#123;
escaped_chart_files = _escape_jinja_in_charts(template_path)

# 2. docxtpl 渲染（不会误解析图表内容）
template.render(context)

# 3. 渲染后：恢复原始内容
_restore_jinja_in_charts(output_path, escaped_chart_files)
```

### 2.7 docxcompose 副作用补救

| 问题 | 原因 | 补救措施 |
|------|------|----------|
| **图片丢失** | docxcompose 未正确复制 media 关系 | `_copy_media_between_docx()` |
| **多余分节符** | docxcompose 自动插入默认页边距的 sectPr | `_remove_docxcompose_extra_sectPr()` |

**多余 sectPr 特征**: `top=1440, bottom=1440`（Word 默认 1 英寸）

---

## 3. 多分析师 (Multi-Analyst Support)

### 3.1 功能概述

报告支持最多 8 位分析师，需在模板中渲染每位分析师信息并扩展认证声明。

### 3.2 分析师数据结构

```python
# elements.yaml 中的字段
a1_cn: "杨斌"       # 第一位分析师 - 中文名
a1_en: "Bin Yang"   # 第一位分析师 - 英文名
a1_sfc: "BSQ313"    # 第一位分析师 - SFC 执照
a1_email: "..."      # 第一位分析师 - 邮箱

a2_cn: "..."        # 第二位分析师
a2_en: "..."
# ... 最多 8 位
```

### 3.3 模板中的条件渲染

使用 Jinja2 条件判断控制多分析师显示：

```html
{% if a2_cn %}
<tr>
    <td>{{ a2_cn }}</td>
    <td>{{ a2_en }}</td>
    ...
</tr>
{% endif %}
```

这种方式无需后端清理，空分析师自然不显示。

### 3.4 上下文准备

`prepare_context_with_analysts` 展平字段并收集分析师列表：

```python
context['analyst_chinese_name'] = elements.get('a1_cn', '')
context['analyst_english_name'] = elements.get('a1_en', '')
context['analyst_sfc_code'] = elements.get('a1_sfc', '')
context['analyst_email'] = elements.get('a1_email', '')

# 收集所有分析师用于循环渲染
analysts = []
for i in range(1, 9):
    cn = elements.get(f'a{i}_cn', '')
    if cn:
        analysts.append({
            'chinese_name': cn,
            'english_name': elements.get(f'a{i}_en', ''),
            'sfc_code': elements.get(f'a{i}_sfc', ''),
            'email': elements.get(f'a{i}_email', '')
        })
context['analysts'] = analysts
```

### 3.5 认证声明扩展

模板中只有一份声明（`a1_cn`, `a1_en`），多分析师时需扩展。声明格式：`我，{{ a1_cn }}，在此保证... I, {{ a1_en }}, certify that...`

扩展策略：
1. 解压 docx 到临时目录
2. 在 XML 中找到分析师声明单元格（包含"在此保证"和"a1_cn"）
3. 选择文本长度较短的单元格（独立声明 vs 大附录）
4. 复制声明段落，替换占位符为 `a2_cn`, `a2_en` 等
5. 重新打包为 docx

```python
# 为额外分析师创建声明段落
for analyst in analysts[1:]:  # 跳过第一个
    new_para_xml = template_para_xml
    # 替换 a1_cn -> 实际中文名
    new_para_xml = re.sub(r'\{\{\s*a1_cn\s*\}\}', analyst['cn'], new_para_xml)
    # 替换 a1_en -> 实际英文名
    new_para_xml = re.sub(r'\{\{\s*a1_en\s*\}\}', analyst['en'], new_para_xml)

    # 插入到单元格
    certification_cell.insert(insert_position, new_para)
```

---

## 4. 关键文件对应

| 功能 | 主要文件 | 核心函数 |
|------|----------|----------|
| 拆草稿 | `splitter.py` | `extract_abstract()`, `extract_body()` |
| 合成报告 | `renderer.py` | `render_report()` |
| 多分析师 | `renderer.py` | `prepare_context_with_analysts()`, `expand_analyst_certification()` |

## 5. 依赖关系图

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   draft    │ ──► │   splitter   │ ──► │  abstract   │
│  .docx    │     │              │     │   .docx     │
└─────────────┘     │              │     └─────────────┘
                    │              │     ┌─────────────┐
                    │              │ ──► │   body      │
                    │              │     │   .docx     │
                    └──────────────┘     └─────────────┘
                                                │
                                                ▼
                    ┌──────────────┐     ┌─────────────┐
                    │   renderer   │ ◄── │  elements   │
                    │              │     │   .yaml     │
                    │  ┌─────────┐ │     └─────────────┘
                    │  │ template│ │
                    │  │ .docx   │ │
                    │  └─────────┘ │
                    └──────────────┘
                            │
                            ▼
                    ┌─────────────┐
                    │   output    │
                    │   .docx     │
                    └─────────────┘
```
