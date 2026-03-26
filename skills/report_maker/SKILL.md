---
name: report_maker
description: 当用户上传报告草稿或要求生成/解析研究报告时使用此技能。负责草稿解析、使用 LLM 提取要素、交互式确认以及使用两阶段工作流生成标准报告。此技能处理分析师研究报告（公司、行业、宏观、策略、量化、债券报告），从 Word 草稿文档转换为基于模板的格式化输出。**必须使用中文与用户沟通**。
---

# Report Maker - 研究报告生成与验证

负责 `reports/` 目录的所有写操作。采用两阶段流程：**抽取确认 → 渲染输出**。

核心原则：**只写 reports/，不写 templates/**

## 使用时机

**使用场景**：
- 用户上传报告草稿（.docx），说"生成标准排版报告"
- 用户说"处理这篇草稿"、"解析报告"、"提取报告要素"
- Editor 修正提取的要素
- Editor 确认后继续生成标准报告

**报告类型**（需用户指定）：
- `company` - 公司覆盖报告
- `sector` - 行业研究报告
- `macro` - 宏观报告
- `strategy` - 策略报告
- `quantitative` - 量化报告
- `bond` - 债券报告

**不适用的场景**：
- 创建/修改模板（使用 template_maker）
- 修改 schema.yaml（使用 template_maker）
- 修改 router.yaml（使用 template_maker）

## 语言要求

**必须使用中文与用户沟通** - 所有对话、提示、确认和说明都必须使用中文。

## 两阶段流程

### 第一阶段：抽取与确认（交互式）

**目标**：从草稿中提取要素，与用户确认后保存

**⚠️ 交互原则：一个问题一个问题地问，不要一次性列出多个问题**

1. **接收输入** - 逐个问题询问
   ```
   问题 1/3：这是什么类型的报告？
   - 等待用户回答（company/sector/macro/strategy/quantitative/bond）

   问题 2/3：草稿文件在哪里？
   - 等待用户提供 .docx 文件路径

   问题 3/3：报告名称是什么？（用于创建 reports/<名称>/ 目录）
   - 等待用户回答，提供单一的缺省建议值
   - 命名规则（日期统一放在最后，前缀从标题提取关键词）：
     * 从报告标题中提取 2-4 个关键词作为前缀
     * 格式：{关键词1}_{关键词2}_{日期}
     * company 示例：从"西锐飞机首次覆盖报告.docx"提取 → "首次覆盖_20251021" 或 "西锐飞机_20251021"
     * sector 示例：从"新能源汽车行业深度分析.docx"提取 → "新能源_深度分析_20251021"
     * 其他类型同理，优先提取标题中的核心主题词
   - 优先使用英文或拼音，避免中文特殊字符
   ```

2. **路由到模板**
   - 从 `templates/router.yaml` 获取模板名
   - 加载 `templates/{template_name}/schema.yaml`

3. **LLM 提取要素**
   - 将草稿内容和 schema.yaml 发送给 LLM
   - LLM 根据 schema 中的字段定义提取数据

4. **交互式确认** ⚠️ 关键步骤 - 逐个字段确认
   ```
   对每个字段（除了 abstract 和 body），一次只问一个：
   - 展示当前字段的 LLM 提取值
   - 如果未提取到：询问用户"是否留空或补充？"
   - 如果提取到了：询问用户"正确吗？(y=确认/n=修改/输入新值)"
   - 等待用户响应后再处理下一个字段
   ```

5. **确保所有字段存在**
   - elements.yaml 必须与 schema.yaml 严格对应
   - 空字段使用空字符串 `""`，不要省略

6. **拆分摘要和正文**
   - 根据 schema 中 `abstract.scope` 提取摘要
   - 根据 schema 中 `body.scope` 提取正文
   - 保存为 `abstract.docx` 和 `body.docx`

7. **保存结果**
   - 保存 `elements.yaml`
   - 保存 `abstract.docx`
   - 保存 `body.docx`
   - 复制 `draft.docx`

8. **展示摘要并暂停**
   - 展示提取结果摘要
   - 等待用户确认或修正

### 第二阶段：渲染与输出

**目标**：基于确认后的要素生成标准报告

1. **更新修正数据**
   - 加载 `elements.yaml`
   - 应用用户修正
   - 保存更新后的 `elements.yaml`

2. **渲染短字段**
   - 使用 python-docx-template（Jinja2）
   - 加载 `templates/{template_name}/template.docx`
   - 用 elements.yaml 中的值替换占位符

3. **插入长文本片段**
   - 用 python-docx 插入 `abstract.docx` 内容
   - 用 python-docx 插入 `body.docx` 内容

4. **保存并转换**
   - 保存 `output.docx`
   - 调用 LibreOffice 转换为 `output.pdf`

## 报告目录结构

```
reports/<report_name>/
├── draft.docx           # 原始草稿
├── elements.yaml        # 提取的要素（与 schema 一致）
├── abstract.docx        # 摘要片段
├── body.docx            # 正文片段
├── output.docx          # 最终 Word
└── output.pdf           # 最终 PDF
```

## elements.yaml 格式

**必须与 schema.yaml 严格保持一致**：

```yaml
# 所有字段都存在，空字段用空字符串
a1_cn: "杨斌"
a1_email: "harryyang@hfisec.com.hk"
a1_en: "Bin Yang"
a1_sfc: "BSQ313"
abstract: "abstract.docx"      # 文件路径引用
body: "body.docx"              # 文件路径引用
company: "西锐飞机"
current_price: ""              # 空字段
current_price_date: ""
market_cap: ""
one_year_high: ""
one_year_low: ""
rating: "OUTPERFORM"
report_date: "21 Oct 2025"
shares_in_issue: ""
target_price: "86.72"
ticker: "2507.HK"
title: "首次覆盖：..."
```

## 写权限边界

| 可写 | 不可写 |
|------|--------|
| `reports/{report_name}/*` | `templates/*` |
| 报告的 draft.docx | schema.yaml |
| 报告的 elements.yaml | router.yaml |
| 报告的 abstract.docx | 任何模板文件 |
| 报告的 body.docx | |
| 报告的 output.docx | |
| 报告的 output.pdf | |

## 常见用户指令

| 用户指令 | 阶段 | 触发动作 |
|---------|------|----------|
| "生成标准排版报告" | 第一阶段 | extract_and_confirm |
| "ticker 应该是 700 HK" | 第一阶段 | update_elements |
| "确认，继续生成" | 第二阶段 | render_output |
| "重新提取摘要" | 第一阶段 | re_extract |

## 关键注意事项

1. **交互式确认是必须的** - 不能跳过第一阶段直接生成
2. **空字段处理** - 必须保留空字段，值为 `""`
3. **字段名一致性** - elements.yaml 的键名必须与 schema.yaml 完全一致
4. **模板切换限制** - 只能在第一阶段切换模板，第二阶段不支持切换
5. **只读 templates/** - report_maker 永远不修改模板资产
