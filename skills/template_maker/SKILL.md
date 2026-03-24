---
name: template_maker
description: 创建和维护分析师报告模板。当用户需要创建新模板、分析 Word 文档结构生成 schema、维护现有模板字段或验证模板时使用此 skill。支持对话式参数收集和自动检测 elements.yaml 配置文件
---

# template_maker

创建和维护分析师报告模板。

## 报告类型

系统支持的常见报告类型：

| 报告类型 | 说明 |
|---------|------|
| `company` | 公司覆盖报告（首次覆盖、深度分析等） |
| `sector` | 行业研究报告 |
| `company_flash` | 公司快讯报告 |
| `sector_flash` | 行业快讯报告 |
| `macro` | 宏观报告（通常共用 common 模板） |
| `strategy` | 策略报告（通常共用 common 模板） |
| `quantitative` | 量化报告（通常共用 common 模板） |
| `bond` | 债券报告（通常共用 common 模板） |

**注意**：
- 报告类型用于 `router.yaml` 配置，必须使用小写
- 多个报告类型可以映射到同一个模板
- 例如：`macro`、`strategy`、`quantitative`、`bond` 都可以映射到 `common` 模板
- 报告类型不限于上述列表，可根据业务需要扩展

## 工作流程

当用户请求创建或维护模板时，使用**渐进式交互**：

### 核心原则

- **一次只问一个问题**
- **提供推荐值或默认值**
- **多轮对话逐步收集信息**

### 步骤 1: 确定用户意图

首次回复只需要问一个简单问题：

```
请问您想创建什么类型的模板？
（例如：common 通用模板、company 公司报告）
```

- 如果用户不清楚选项，列出常见模板类型作为参考
- 根据用户回答，给出**推荐配置**
- 不要一次问多个问题

### 步骤 2: 渐进式收集信息

每轮只问一个下一步需要的信息：

1. **第一轮**：获取模板名称和报告类型
   - 示例回复："好的，创建 `common` 模板，用于 macro、strategy 等报告类型。
      请提供 Word 样本文件路径（例如：samples/macro_sample.docx）"

2. **第二轮**：获取 Word 文件路径
   - 验证文件存在
   - 自动检测 elements.yaml
   - 如果检测到多个候选文件，让用户选择

3. **第三轮**：询问摘要和正文配置
   - 询问："摘要在文档的哪个位置？"
     - 告知用户关键结构特征：
       - **摘要后面一定有换页符**（在 Word 中体现为分节）
       - 摘要通常在首页的表格中，右侧区域
     - 例如："首页右侧（长的话可能到第二页）"
     - 摘要是必须的
   - 询问："这份报告是否有正文部分？如果有，它从哪里开始？"
     - 告知用户关键结构特征：
       - **如果有正文，至少一页，正文结束后也有换页符**
       - **附录（信息披露）一定从新的一页开始**
     - 例如：flash 报告通常没有正文
     - 如果有正文："从首页之后的第一个一级标题之后到附录之前"
   - 如果用户回答"使用默认配置"，则使用自动检测

4. **第四轮**：确认配置并执行
   - 展示汇总信息
   - 询问："确认创建吗？"

### 步骤 3: 执行创建

### 步骤 2: 执行创建

使用 `scripts/invoke.py` 执行模板创建：

```bash
cd /mnt/c/_code/neoskills
python3 skills/template_maker/scripts/invoke.py \
  --name "模板名称" \
  --word "path/to/sample.docx" \
  --elements "path/to/elements.yaml"
```

或使用对话式模式：

```bash
python3 skills/template_maker/scripts/invoke.py
```

### 步骤 3: 验证结果

成功后会创建以下文件结构：

```
templates/
├── router.yaml           # 自动更新路由配置
└── <模板名>/
    ├── meta.yaml         # 模板元数据
    ├── schema.yaml       # 字段 schema
    └── template.docx     # Word 模板文件
```

## 使用示例

### 示例 1: 创建通用模板（多轮对话）

**用户**：`创建一个通用模板`

**AI**：请问您想创建什么类型的模板？（例如：common 通用模板、company 公司报告）

**用户**：`common`

**AI**：好的，创建 `common` 模板。这个模板用于哪些报告类型？
（例如：macro, strategy, quantitative, bond）

**用户**：`就用示例的`

**AI**：明白了。请提供 Word 样本文件路径：
（例如：samples/macro_sample.docx）

**用户**：`samples/macro_sample.docx`

**AI**：检测到 `samples/macro_sample elements.yaml`，将使用该配置文件。

现在需要配置摘要和正文的抽取规则。

**摘要配置：**
- 摘要后面一定有换页符
- 通常在首页的表格中，右侧区域

摘要在文档的哪个位置？

**用户**：`首页右侧，长的话可能到第二页`

**AI**：好的。现在配置正文部分。

**正文结构特征：**
- 如果有正文，至少一页，正文结束后也有换页符
- 附录（信息披露）一定从新的一页开始

这份报告是否有正文部分？如果有，它从哪里开始？

**用户**：`从首页之后开始`

**AI**：明白了。

**汇总配置**：
- 模板名称：common
- 报告类型：macro, strategy, quantitative, bond
- Word 文件：samples/macro_sample.docx
- elements.yaml：samples/macro_sample elements.yaml
- 摘要位置：首页右侧（长的话可能到第二页）
- 正文位置：从首页之后开始

确认创建吗？

### 示例 2: 用户在一条消息中提供所有信息

**用户**：`创建 common 模板，用于 macro 和 strategy，文件是 samples/macro_sample.docx`

**AI**：收到配置。检测到 `samples/macro_sample elements.yaml`。

**汇总配置**：
- 模板名称：common
- 报告类型：macro, strategy
- Word 文件：samples/macro_sample.docx
- elements.yaml：samples/macro_sample elements.yaml

确认创建吗？

### 示例 3: Flash 报告（无正文）

**用户**：`创建一个 flash 报告模板`

**AI**：请问您想创建什么类型的模板？（例如：common 通用模板、company 公司报告）

**用户**：`company_flash`

**AI**：好的，创建 `company_flash` 模板。这个模板用于哪些报告类型？

**用户**：`company_flash`

**AI**：明白了。请提供 Word 样本文件路径：

**用户**：`samples/company_flash_sample.docx`

**AI**：检测到 `samples/company_flash_sample elements.yaml`，将使用该配置文件。

**摘要配置：**
- 摘要后面一定有换页符
- 通常在首页的表格中，右侧区域

摘要在文档的哪个位置？

**用户**：`首页右侧`

**AI**：好的。现在配置正文部分。

**正文结构特征：**
- 如果有正文，至少一页，正文结束后也有换页符
- 附录（信息披露）一定从新的一页开始

这份报告是否有正文部分？

**用户**：`没有正文，这是 flash 报告`

**AI**：明白了。

**汇总配置**：
- 模板名称：company_flash
- 报告类型：company_flash
- Word 文件：samples/company_flash_sample.docx
- elements.yaml：samples/company_flash_sample elements.yaml
- 摘要位置：首页右侧
- 正文：无

确认创建吗？

### 示例 4: 命令行调用

```bash
python3 skills/template_maker/scripts/invoke.py \
  --name "common" \
  --report-types "macro,strategy,quantitative,bond" \
  --word "samples/macro_sample.docx"
```

## 技术细节

### schema.yaml 结构

生成的 schema.yaml 采用扁平化结构：

```yaml
# === 普通字段（从样本文档提取，用于填充模板）===
company:
  description: 公司名称
  format: 西锐飞机

ticker:
  description: 股票代码
  format: 2507.HK

rating:
  description: 评级
  format: 优于大市

# === Word 片段（从原始文档摘取，保存为独立 Word 文件）===
abstract:
  type: fragment
  description: 报告摘要部分
  scope: 首页右侧（长的话可能到第二页）
  hints:
    - 通常包含投资亮点、核心观点
    - 长度约 200-500 字
    - 位于首页右侧区域

body:
  type: fragment
  description: 报告正文部分
  scope: 从首页之后到报告结尾
  hints:
    - 包含各章节详细内容
    - 可能包含表格、图表引用
    - 按原文结构保留段落和标题层级
```

**字段类型说明：**
- **普通字段**（无 `type`）：从样本文档提取的字段值，在生成报告时填充到模板中
- **Word 片段**（`type: fragment`）：从原始文档摘取的 Word 片段文件，由 document_maker 使用

**重要说明**：
- `abstract`（摘要）是必须的，所有报告类型都有
- `body`（正文）是可选的，例如 flash 报告通常没有正文
- 如果用户指定某部分不存在，则该部分不会包含在 schema 中

### 自动检测逻辑

系统按以下顺序查找 `elements.yaml`：

1. `<word_name> elements.yaml`
2. `<word_name>_elements.yaml`
3. `elements.yaml`（同目录）

### 代码模块

- `scripts/core.py`: 核心编排器 TemplateMaker
- `scripts/invoke.py`: CLI 调用入口
- `scripts/parser.py`: Word 文档分析器
- `scripts/schema_gen.py`: Schema 生成器（包含 extraction_rules）
- `scripts/router_mgr.py`: 路由管理器
- `scripts/validator.py`: 模板验证器
- `scripts/utils.py`: 工具函数

### 依赖安装

```bash
pip install -r skills/template_maker/scripts/requirements.txt
```

## 模板目录结构

```
templates/
├── router.yaml           # 路由配置
└── <模板名>/
    ├── meta.yaml         # 模板元数据
    ├── schema.yaml       # 字段 schema
    └── template.docx     # Word 模板文件
```

## elements.yaml 格式

```yaml
company: 西锐飞机
ticker: 2507.HK
target_price: 15.0
rating: 买入
```

## 生成的 schema.yaml 格式

```yaml
# 扁平化结构，无顶层 fields 或 extraction_rules

# 普通字段（从样本文档提取）
company:
  description: 公司名称
  format: 西锐飞机

ticker:
  description: 股票代码
  format: 2507.HK

# Word 片段（从原始文档摘取）
abstract:
  type: fragment
  description: 报告摘要
  scope: 首页右侧
  hints:
    - 通常包含投资亮点
    - 长度约 200-500 字

body:
  type: fragment
  description: 报告正文
  scope: 从首页之后到报告结尾
  hints:
    - 包含各章节详细内容
    - 可能包含表格、图表引用
```
