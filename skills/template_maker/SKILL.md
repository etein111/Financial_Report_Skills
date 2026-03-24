---
name: template_maker
description: 创建和维护分析师报告模板。当用户需要创建新模板、分析 Word 文档结构生成 schema、维护现有模板字段或验证模板时使用此 skill。支持交互式参数收集和自动化模式（invoke.py 脚本）。
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

### 交互步骤

1. **确定模板名称和报告类型**
   - 示例回复："好的，创建 `common` 模板，用于 macro、strategy 等报告类型。请提供 Word 样本文件路径"

2. **获取 Word 文件路径**
   - 验证文件存在
   - 自动检测 elements.yaml
   - 如果检测到多个候选文件，让用户选择

3. **询问摘要和正文配置**
   - 摘要位置询问（必须）
   - 正文位置询问（可选，flash 报告可能没有正文）
   - 告知用户关键结构特征：
     - **摘要后面一定有换页符**（在 Word 中体现为分节）
     - **如果有正文，至少一页，正文结束后也有换页符**
     - **附录（信息披露）一定从新的一页开始**

4. **确认并执行**
   - 展示汇总信息
   - 询问："确认创建吗？"

### 执行流程

确认后，按以下步骤创建模板：

1. 加载 Word 文档和 elements.yaml
2. 生成扁平化的 schema.yaml
3. 替换模板中的字段值为占位符
4. 替换摘要和正文区域
5. 更新 router.yaml 路由配置
6. 保存模板文件

成功后创建以下文件结构：

```
templates/
├── router.yaml           # 自动更新路由配置
└── <模板名>/
    ├── meta.yaml         # 模板元数据
    ├── schema.yaml       # 字段 schema（扁平化结构）
    └── template.docx     # Word 模板文件
```

## schema.yaml 结构

生成的 schema.yaml 采用**扁平化结构**：

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

**重要说明：**
- `abstract`（摘要）是必须的，所有报告类型都有
- `body`（正文）是可选的，例如 flash 报告通常没有正文

## 自动化模式

对于批量操作或自动化场景，可以直接使用 `scripts/invoke.py` 脚本：

```bash
# 交互式创建（会确认）
python skills/template_maker/scripts/invoke.py \
  --name common \
  --word fixtures/macro_sample.docx \
  --elements "fixtures/macro_sample elements.yaml"

# 自动化模式（跳过确认）
python skills/template_maker/scripts/invoke.py \
  --name company \
  --word fixtures/company_sample.docx \
  --elements "fixtures/company_sample elements.yaml" \
  --auto-confirm

# 快讯报告（无正文）
python skills/template_maker/scripts/invoke.py \
  --name company_flash \
  --word fixtures/flash_sample.docx \
  --elements "fixtures/flash_sample elements.yaml" \
  --no-body \
  --auto-confirm

# 自定义摘要/正文位置
python skills/template_maker/scripts/invoke.py \
  --name custom \
  --word fixtures/custom.docx \
  --elements fixtures/custom_elements.yaml \
  --abstract-scope "首页第二栏" \
  --body-scope "从第三章开始" \
  --auto-confirm
```

**参数说明：**
- `--name`: 模板名称（必需）
- `--word`: Word 样本文件路径（必需）
- `--elements`: elements.yaml 配置文件路径（必需）
- `--abstract-scope`: 摘要位置描述（默认: "首页右侧"）
- `--body-scope`: 正文位置描述（默认: "从首页之后到报告结尾"）
- `--no-body`: 快讯报告，没有正文部分
- `--output-dir`: 输出目录（默认: templates）
- `--auto-confirm, -y`: 跳过确认，直接创建

## elements.yaml 自动检测

系统按以下顺序查找 `elements.yaml`：

1. `<word_name> elements.yaml`
2. `<word_name>_elements.yaml`
3. `elements.yaml`（同目录）

## 代码模块

函数式编程设计，按职责分为 6 个模块：

| 模块 | 函数数 | 职责 |
|------|--------|------|
| `router.py` | 6 | 路由配置管理（读写分离）|
| `schema.py` | 6 | Schema 生成和更新（读写分离）|
| `validate.py` | 1 | 模板验证 |
| `document.py` | 9 | 文档结构分析 |
| `template.py` | 10 | 模板内容操作 |

**关键特性：**
- 纯函数设计（逻辑和 I/O 分离）
- 支持批量操作（减少文件 I/O）
- Document 对象传递（避免重复加载 Word 文档）

## 模板目录结构

```
templates/
├── router.yaml           # 路由配置
└── <模板名>/
    ├── meta.yaml         # 模板元数据
    ├── schema.yaml       # 字段 schema（扁平化）
    └── template.docx     # Word 模板文件
```

## elements.yaml 格式

```yaml
company: 西锐飞机
ticker: 2507.HK
target_price: 15.0
rating: 买入
```

## 使用示例

### 示例 1: 创建通用模板

**用户**：`创建一个通用模板`

**AI**：请问您想创建什么类型的模板？（例如：common 通用模板、company 公司报告）

**用户**：`common`

**AI**：好的，创建 `common` 模板，用于 macro、strategy 等报告类型。请提供 Word 样本文件路径：
（例如：fixtures/macro_sample.docx）

**用户**：`fixtures/macro_sample.docx`

**AI**：检测到 `fixtures/macro_sample elements.yaml`，将使用该配置文件。

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
- Word 文件：fixtures/macro_sample.docx
- elements.yaml：fixtures/macro_sample elements.yaml
- 摘要位置：首页右侧（长的话可能到第二页）
- 正文位置：从首页之后开始

确认创建吗？

### 示例 2: Flash 报告（无正文）

**用户**：`创建一个 flash 报告模板`

**AI**：请问您想创建什么类型的模板？

**用户**：`company_flash`

**AI**：好的，创建 `company_flash` 模板。请提供 Word 样本文件路径：

**用户**：`fixtures/company_flash_sample.docx`

**AI**：检测到 `fixtures/company_flash_sample elements.yaml`，将使用该配置文件。

摘要在文档的哪个位置？

**用户**：`首页右侧`

**AI**：好的。这份报告是否有正文部分？

**用户**：`没有正文，这是 flash 报告`

**AI**：明白了。

**汇总配置**：
- 模板名称：company_flash
- Word 文件：fixtures/company_flash_sample.docx
- elements.yaml：fixtures/company_flash_sample elements.yaml
- 摘要位置：首页右侧
- 正文：无

确认创建吗？
