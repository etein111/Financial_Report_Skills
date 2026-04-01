---
name: template_maker
description: "当用户说「制作模板」、「创建模板」、「分析模板结构」或上传 Word 文档要求提取模板时使用此技能。支持创建新模板、维护现有模板、验证模板结构。"
---

# template_maker

模板制作与维护 skill。

## 何时使用

当您需要：
- 创建新的报告模板
- 修改现有模板的字段定义
- 从样本文档中提取 schema
- 验证模板的正确性

## 标准占位符定义

**重要**：必须使用以下标准占位符名称，不要自行创造其他名称。

### 内容片段占位符

| 占位符 | 用途 | 必选 | 说明 |
|--------|------|------|------|
| `{{ abstract }}` | 摘要 | 可选 | 报告摘要/投资亮点区域，通常在首页 |
| `{{ body }}` | 正文 | 可选 | 报告主体内容，从首页之后到附录之前 |
| `{{ summary }}` | 英文 Summary | 可选 | 英文摘要，通常在 APPENDIX 1 中 |

**注意**：
- 法律披露附录（APPENDIX/IMPORTANT DISCLOSURES）**保留原样，不替换为占位符**
- 快讯报告通常没有 `body` 和 `summary`
- 公司报告通常有 `abstract` 和 `body`

### 元数据占位符

| 占位符 | 用途 | 示例值 |
|--------|------|--------|
| `{{ company }}` | 公司名称 | 西锐飞机 |
| `{{ ticker }}` | 股票代码 | CIRR.O |
| `{{ rating }}` | 评级 | Buy |
| `{{ target_price }}` | 目标价 | $45.00 |
| `{{ title }}` | 报告标题 | 首次覆盖：优质飞机制造商 |
| `{{ report_date }}` | 报告日期 | 2026-03-20 |

### 分析师占位符

| 占位符 | 用途 |
|--------|------|
| `{{ a1_cn }}` | 分析师1中文名 |
| `{{ a1_en }}` | 分析师1英文名 |
| `{{ a1_sfc }}` | 分析师1 SFC 牌照号 |
| `{{ a1_email }}` | 分析师1邮箱 |
| `{{ a2_cn }}` ~ `{{ a8_cn }}` | 分析师2-8（同上格式） |

### 占位符格式规范

- 使用双花括号包裹：`{{ field_name }}`
- 花括号内部有空格：`{{` + 空格 + 字段名 + 空格 + `}}`
- 字段名使用小写字母和下划线：`target_price`（不是 `targetPrice`）

## 支持的报告类型

| 报告类型            | 说明                 |
|-----------------|--------------------|
| `company`       | 公司覆盖报告             |
| `sector`        | 行业研究报告             |
| `flash`         | 快讯                 |
| `company_flash` | 公司快讯               |
| `sector_flash`  | 行业快讯               |
| `macro`         | 宏观报告（使用 common 模板） |
| `strategy`      | 策略报告（使用 common 模板） |
| `quantitative`  | 量化报告（使用 common 模板） |
| `bond`          | 债券报告（使用 common 模板） |

**注意**：
- 报告类型通过 `router.yaml` 映射到模板名
- 多个报告类型可以共用一个模板
- `macro`、`strategy`、`quantitative`、`bond` 共用 `common` 模板
- 报告类型可以扩展

## 使用流程

### 创建新模板

#### 步骤 1：选择模板类型并自动扫描素材

**系统自动扫描对应目录的样本文档**：

```
【扫描样本文档】
请选择要使用的模板类型：
  1. company - 公司覆盖报告
  2. sector - 行业研究报告
  3.flash - 快讯  
  4. company_flash - 公司快讯
  5. sector_flash - 行业快讯
  6. macro - 宏观报告
  ...

您的选择: flash

正在扫描 inbox/samples/flash/ 目录...
找到以下样本文档：
  1. 全球消费及互联网周报_3_16-3_19_AutoRefresh.docx
  2. 全球消费及互联网周报_3_16-3_19-草稿.docx

请选择要使用的样本文档（输入编号）:
```

**自动扫描规则**：
| 模板类型 | 扫描目录 |
|---------|---------|
| company | inbox/samples/company/ |
| sector | inbox/samples/sector/ |
| flash | inbox/samples/flash/ |
| company_flash | inbox/samples/flash/ |
| sector_flash | inbox/samples/flash/ |
| macro | inbox/samples/macro/ |
| strategy | inbox/samples/macro/ |
| quantitative | inbox/samples/macro/ |
| bond | inbox/samples/macro/ |

**自动查找 elements.yaml**：
选择样本文档后，系统自动在同目录下查找匹配的 elements.yaml：
- `{文件名} elements.yaml`
- `{文件名}_elements.yaml`
- `elements.yaml`（通用配置）

#### 步骤 2：自动查找 elements.yaml

**系统自动在样本文档同目录下查找 elements.yaml**：

```
【查找 elements.yaml】
在 inbox/samples/flash/ 目录下查找...
✓ 找到: inbox/samples/flash/全球消费及互联网周报_3_16-3_19_AutoRefresh elements.yaml
```

如果找到多个 elements.yaml，显示列表供用户选择。

#### 步骤 3：LLM 分析文档结构

**必须通过 LLM 询问判断摘要和正文**：

```
【LLM 分析】正在分析文档结构...
请分析这篇研究报告：
1. 是否有摘要部分？（摘要通常是首页的投资亮点、核心观点区域）
2. 摘要的位置在哪里？
3. 是否有正文部分？（正文是报告的主要分析内容）
4. 正文从哪里开始？

请以 JSON 格式返回：
{
  "has_abstract": true/false,
  "abstract_scope": "位置描述",
  "has_body": true/false,
  "body_scope": "位置描述"
}
```

#### 步骤 4：交互确认位置

**流程原则**：先自动检测并展示结果，让用户确认是否正确。如果用户说不正确，再询问是否有该部分、具体位置在哪里。**不要根据报告类型先入为主地假设有没有某个部分。**

**确认摘要位置**：
```
【步骤 1/4】确认摘要位置

自动检测到摘要：
  位置：表格 0 行 2 列 1
  内容预览：公司是全球领先的通用航空飞机制造商...

请确认检测是否正确：
  - 回车或 y：正确，使用此位置
  - n：不正确，我来指定

检测是否正确？(y/n):
```

如果用户选择 n（不正确）：
```
这份报告是否有摘要部分？
是否有摘要？(y/n):

请指定摘要位置：
  示例：首页右侧、第二页表格中、首页左侧表格
摘要位置:
```

**确认正文位置**：
```
【步骤 2/4】确认正文位置

自动检测到正文：
  范围：正文范围: 段落 0 到 45（分节符之前）

请确认检测是否正确：
  - 回车或 y：正确，使用此范围
  - n：不正确，我来指定

检测是否正确？(y/n):
```

**确认英文 Summary 位置**：
```
【步骤 3/4】确认英文 Summary 位置

未自动检测到英文 Summary（未找到 Summary 标记）
这份报告是否有英文 Summary 部分？
  （通常在 APPENDIX 1 中，或 Executive Summary）

是否有 Summary？(y/n):
```

**法律披露附录**：
- 系统自动检测，不需要用户确认
- 保留原样，不替换为占位符
- 在最终配置中显示位置信息

#### 步骤 5：系统自动构建与验证

- 解析 Word 模板，将动态内容替换为占位符
- **验证占位符**：确保所有 elements.yaml 字段 + abstract + body 都正确提取
- 显示已提取的占位符列表
- 如有缺失占位符，显示警告信息
- 验证通过后，提示模板创建成功

#### 步骤 6：修改字段定义（可选）

- 告诉系统："以后提取宏观报告时，增加一个'风险提示'字段"
- 系统会展示变更计划
- 确认后自动更新 schema.yaml 和模板

#### 步骤 7：模板验证

- 系统自动验证模板结构
- 测试占位符替换
- 确保模板可以正常使用

## 核心功能

- **schema 生成**：从样本文档自动提取字段定义
- **模板创建**：生成带 Jinja2 占位符的 Word 模板
- **字段管理**：添加、删除、修改字段
- **模板验证**：检查模板结构和占位符
- **路由维护**：更新 router.yaml 映射

## 写权限边界

| 可写 | 不可写 |
|------|--------|
| `templates/*` | `reports/*` |
| schema.yaml | 报告处理结果 |
| template.docx | draft.docx |
| router.yaml | elements.yaml |
| meta.yaml | abstract.docx |
| | body.docx |
| | output.docx |
| | output.pdf |

## 注意事项

1. **只写 templates/**：template_maker 只修改模板资产
2. **不处理报告**：单篇报告处理由 report_maker 负责
3. **交互式确认**：重要变更前会展示预览
4. **自动验证**：每次修改后自动验证模板