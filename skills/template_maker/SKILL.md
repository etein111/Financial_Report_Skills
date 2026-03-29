---
name: template_maker
description: "当用户说「制作模板」、「创建模板」、「分析模板结构」或上传 Word 文档要求提取模板时使用此技能。支持创建新模板、维护现有模板、验证模板结构。"
---

# template_maker

模板制作与维护 skill。

**用户隔离**：
- **重要**：每个用户在服务器上有独立的目录 `/data/{用户名}/`
- **首次使用**：必须先询问用户"请告诉我您的用户名"
- **文件路径**：
  - 样本文档：`/data/{用户名}/input/*.docx`
  - 提取的模板：`/data/{用户名}/output/*.docx`
- **禁止跨用户访问**：不允许访问其他用户的目录

## 何时使用

当您需要：
- 创建新的报告模板
- 修改现有模板的字段定义
- 从样本文档中提取 schema
- 验证模板的正确性

## 支持的报告类型

| 报告类型 | 说明 |
|---------|------|
| `company` | 公司覆盖报告 |
| `sector` | 行业研究报告 |
| `company_flash` | 公司快讯 |
| `sector_flash` | 行业快讯 |
| `macro` | 宏观报告（使用 common 模板） |
| `strategy` | 策略报告（使用 common 模板） |
| `quantitative` | 量化报告（使用 common 模板） |
| `bond` | 债券报告（使用 common 模板） |

**注意**：
- 报告类型通过 `router.yaml` 映射到模板名
- 多个报告类型可以共用一个模板
- `macro`、`strategy`、`quantitative`、`bond` 共用 `common` 模板
- 报告类型可以扩展

## 使用流程

### 创建新模板

1. **提供样本文档**
   - 上传一份排版标准的历史报告（Word）
   - 提供对应的要素清单（elements.yaml）
   - 指定模板名称（如："将其设为 common 模板"）

2. **系统自动构建与验证**
   - 解析 Word 模板，将动态内容替换为占位符
   - 基于原要素执行一次闭环验证
   - 验证通过后，提示模板创建成功

3. **修改字段定义**
   - 告诉系统："以后提取宏观报告时，增加一个'风险提示'字段"
   - 系统会展示变更计划
   - 确认后自动更新 schema.yaml 和模板

4. **模板验证**
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
