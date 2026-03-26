---
name: report_maker
description: 当用户上传报告草稿或要求生成/解析研究报告时使用此技能。负责草稿解析、使用 LLM 提取要素、交互式确认以及使用两阶段工作流生成标准报告。此技能处理分析师研究报告（公司、行业、宏观、策略、量化、债券报告），从 Word 草稿文档转换为基于模板的格式化输出。**必须使用中文与用户沟通**。
---

# Report Maker - 研究报告生成

**核心原则**：只写 `reports/`，不写 `templates/`

**工作流程**：抽取确认 → 渲染输出

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

## 第一阶段：抽取与确认

### 1. 询问基本信息（逐个询问）

```
问题 1/3：这是什么类型的报告？
- 等待用户回答（company/sector/macro/strategy/quantitative/bond）

问题 2/3：草稿文件在哪里？
- 等待用户提供 .docx 文件路径

问题 3/3：报告名称是什么？（用于创建 reports/<名称>/ 目录）
- 等待用户回答，提供单一的缺省建议值
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

### 2. 路由到模板

从 `templates/router.yaml` 获取模板名，加载 `templates/{template_name}/schema.yaml`

### 3. 提取字段

**使用自动化提取**（优先）：

```bash
python3 -c "
from skills.report_maker.scripts import extractor, common
schema = common.load_yaml('templates/company/schema.yaml')
elements = extractor.extract_elements(draft_path, schema)
"
```

**或使用 LLM 辅助提取**（自动化失败时）：

将草稿内容和 schema.yaml 发送给 LLM，LLM 根据 schema 中的字段定义提取数据。

**⚠️ 关键技术提示：嵌套表格处理**

- python-docx 的 `cell.text` 只返回直接段落文本，**不包括嵌套表格**
- 许多关键字段（如 current_price, market_cap 等）在首页表格的**嵌套表格**中
- 本 skill 已在 `docx_reader.py` 和 `field_extractor.py` 中实现自动化递归读取

### 4. 一次性确认所有字段

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

### 5. 确保所有字段存在

- elements.yaml 必须与 schema.yaml 严格对应
- 空字段使用空字符串 `""`，不要省略

### 6. 拆分摘要和正文

根据 schema 中 `abstract.scope` 和 `body.scope` 提取内容，保存为 `abstract.docx` 和 `body.docx`

### 7. 保存结果

```
reports/<report_name>/
├── draft.docx           # 原始草稿
├── elements.yaml        # 提取的要素
├── abstract.docx        # 摘要片段
└── body.docx            # 正文片段
```

### 8. 展示摘要并暂停

展示提取结果摘要，等待用户确认或修正

---

## 第二阶段：渲染与输出

### 1. 更新修正数据

加载 `elements.yaml`，应用用户修正，保存更新后的 `elements.yaml`

### 2. 渲染短字段

使用 python-docx-template（Jinja2）加载 `templates/{template_name}/template.docx`，用 elements.yaml 中的值替换占位符

### 3. 插入长文本片段

用 python-docx 插入 `abstract.docx` 和 `body.docx` 内容

### 4. 保存并转换

```
reports/<report_name>/
├── output.docx          # 最终 Word
└── output.pdf           # 最终 PDF（通过 LibreOffice 转换）
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

## 权限边界

### ✅ 可写
- `reports/{report_name}/*`（所有文件）

### ❌ 不可写
- `templates/*`（任何模板文件）
- schema.yaml
- router.yaml

---

## 注意事项

1. **交互式确认是必须的** - 不能跳过第一阶段直接生成
2. **空字段处理** - 必须保留空字段，值为 `""`
3. **字段名一致性** - elements.yaml 的键名必须与 schema.yaml 完全一致
4. **模板切换限制** - 只能在第一阶段切换模板，第二阶段不支持切换
5. **只读 templates/** - report_maker 永远不修改模板资产

---

## 技术参考（仅供开发参考）

> 本部分详细说明了渲染实现的技术细节，用于问题排查和功能扩展。

### 文档合并流程

渲染使用 **docxcompose** 合并 body.docx，流程如下：

1. **提取附录**：从 template 中提取 `{{body}}` 之后的内容（法律附录等）和末尾 sectPr
2. **预清理 body.docx**：
   - 删除所有段落内的 sectPr（防止强制换页导致空白页）
   - 删除独立的 sectPr 元素
   - 删除开头的空段落（保留目录控件 sdt）
3. **合并**：使用 docxcompose.append() 插入 body
4. **创建分节符**：在附录前添加 sectPr，隔离正文和附录
5. **恢复附录**：将提取的附录追加回文档末尾
6. **修正末尾 sectPr**：恢复 template 原始的 sectPr

### 附录隔离机制

**关键原则**：附录完全来自 template，不做任何修改

```
Output Section 结构：
- Section 0: 封面（保持 template 原样，left=1.00cm）
- Section 1: 正文（使用 body.docx 的页边距 left=6.35cm）
- Section 2: 附录（保持 template 原样，left=1.00cm）
```

**分节符 sectPr 必须包含完整属性**：

| 属性 | 说明 | 示例值 |
|------|------|--------|
| `pgSz` | 页面尺寸 | A4: w=11910, h=16840 twips |
| `pgMar` | 页边距 | 包括 header 和 footer 距离 |
| `cols` | 列设置 | - |
| `docGrid` | 文档网格 | - |

⚠️ 缺少这些属性会导致页面尺寸为 0，页眉页脚显示不全。

### 空白页问题处理

**原因**：
1. sectPr 分节符：每个 sectPr type=nextPage 会强制换页
2. 连续空段落：大量空段落会占用页面空间
3. 文档开头空段落：body.docx 开头可能有多个空段落

**解决方案**：
1. 追加前删除 body.docx 所有 sectPr
2. 追加后清理连续空段落（保留最多 1 个）
3. 删除 body.docx 开头的空段落

### Abstract 插入

abstract 插入到表格单元格，使用 deepcopy 保留完整格式：
- 删除单元格内所有段落
- 逐段复制 abstract.docx 内容（保留字体、颜色等格式）
