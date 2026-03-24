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

3. **第三轮**：确认配置并执行
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

**汇总配置**：
- 模板名称：common
- 报告类型：macro, strategy, quantitative, bond
- Word 文件：samples/macro_sample.docx
- elements.yaml：samples/macro_sample elements.yaml

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

### 示例 3: 命令行调用

```bash
python3 skills/template_maker/scripts/invoke.py \
  --name "common" \
  --report-types "macro,strategy,quantitative,bond" \
  --word "samples/macro_sample.docx"
```

## 技术细节

### schema.yaml 结构

生成的 schema.yaml 包含三部分：

```yaml
name: 模板名称
display_name: 模板显示名称
version: 1.0.0
fields:
  company:
    description: 公司名称
    format: 西锐飞机
  ticker:
    description: 股票代码
    format: 2507.HK

extraction_rules:
  abstract:
    description: 报告摘要部分
    scope: 从报告开头到第一个一级标题之前
    hints:
      - 通常包含投资亮点、核心观点
      - 长度约 200-500 字
  body:
    description: 报告正文部分
    scope: 从第一个一级标题之后到报告结尾
    hints:
      - 包含各章节详细内容
      - 可能包含表格、图表引用
```

注意：`extraction_rules` 供 report_maker skill 使用，定义如何从草稿中抽取摘要和正文。

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
name: 模板名称
display_name: 模板显示名称
version: 1.0.0
fields:
  company:
    type: string
    format: 西锐飞机
    description: 公司名称
  ticker:
    type: string
    format: 2507.HK
    description: 股票代码
```
