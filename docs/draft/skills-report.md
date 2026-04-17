# 分析师报告自动化处理系统（需求与设计文档）

第 1~2 节描述业务目标与操作流程；第 3~4 节描述目录结构、核心文件与技术方案。

## 1. 系统概述与设计目标

面向分析师报告的自动化生产能力，提升模板维护、草稿解析和标准报告生成的效率。

核心设计目标：**业务人员自主配置与管理**。业务人员通过自然语言维护提取规则和排版模板。YAML 文件作为系统生成的可读资产保留在仓库中，便于查阅与审计，但第一版不要求业务人员手工修改。

## 2. 核心工作流

系统以对话框（Chat UI）为主要交互界面，包含两个场景。

### 场景一：报告模板的制作与维护

**业务痛点**：新增或修改模板依赖研发介入，响应慢、维护成本高。

1. **上传标准样本**：用户提供一份排版标准的历史报告（Word）及要素清单（elements.yaml），输入指令（如"设为 common 模板"）。
2. **系统自动构建与验证**：系统解析 Word 模板，替换动态内容为占位符，基于原要素执行闭环验证。
3. **对话式修改**：业务人员在对话框告诉 AI 新增字段需求（如"以后提取宏观报告时增加'风险提示'字段"）。系统生成变更计划并展示预览：更新 schema.yaml、修改模板 Word 插入占位符。用户确认后生效。
4. **模板排版生效**：用户确认后，系统更新模板并执行最小渲染验证。

### 场景二：分析师日常报告生成

**业务痛点**：分析师草稿格式不统一，后期人工排版耗时。

1. **提交草稿**：分析师上传报告草稿，输入指令（如"生成标准排版报告"）。
2. **智能解析**：系统识别报告类型，通过 `router.yaml` 路由到对应模板，提取文本、图表及核心要素，创建独立目录保存结果。
3. **核心数据确认**：系统展示提取的关键要素。遗漏或错误处可通过自然语言指令修改。第一版在此阶段暂停等待 Editor 确认。模板切换仅允许在确认阶段进行。
4. **标准报告生成**：确认后结合模板渲染输出标准 Word 和 PDF。摘要与正文分别保存为 Word 片段，再与模板合并。

## 3. 架构与目录拓扑

### 3.0 报告类型

| 报告类型 | 说明 |
|---------|------|
| `company` | 公司覆盖报告（首次覆盖、深度分析等） |
| `sector` | 行业研究报告 |
| `company_flash` | 公司快讯 |
| `sector_flash` | 行业快讯 |
| `macro` | 宏观报告（共用 common 模板） |
| `strategy` | 策略报告（共用 common 模板） |
| `quantitative` | 量化报告（共用 common 模板） |
| `bond` | 债券报告（共用 common 模板） |

模板映射规则：
- 报告类型通过 `router.yaml` 映射到模板名
- 多个报告类型可映射到同一模板
- 报告类型不限于上表，可按业务需要扩展

### 3.1 核心数据文件

| 文件 | 用途 |
|------|------|
| `elements.yaml` | 统一业务要素单。记录结构化业务数据，可作为模板样本输入或草稿解析结果 |
| `schema.yaml` | 提取规则说明书。字段定义、描述和提取要求。AI 通过对话自动维护 |
| `router.yaml` | 模板路由表。报告类型 → 模板名的静态映射 |
| `meta.yaml` | 轻量元数据。模板或报告的基础说明（名称、状态、更新时间） |
| `template.docx` / `abstract.docx` / `body.docx` | 正式排版模板 / 摘要片段 / 正文片段 |

### 3.2 目录拓扑

```
/agent_workspace/
├── /skills/                            <-- Agent Skills 插件区
│   ├── /template_maker/
│   │   └── SKILL.md
│   └── /report_maker/
│       └── SKILL.md
├── /templates/                         <-- 正式模板资产区
│   ├── router.yaml
│   └── /common/                        <-- 按模板名组织，非报告类型
│       ├── schema.yaml
│       ├── template.docx
│       └── meta.yaml
└── /reports/                           <-- 每篇报告的处理现场
    └── /西锐飞机首次覆盖报告/
        ├── draft.docx
        ├── elements.yaml
        ├── abstract.docx
        ├── body.docx
        ├── /assets/                    <-- 图表/截图
        ├── output.docx
        ├── output.pdf
        └── meta.yaml
```

约束：
- `skills/` 只存放符合 Agent Skills Open Standard 的技能插件
- `templates/` 只存放正式模板资产，按模板名组织（不与报告类型绑定）
- `reports/` 按报告名组织目录（非任务 ID），便于 Editor 定位
- 第一版不设模板工作目录和版本历史，候选文件在临时目录处理后覆盖正式模板

### 3.3 Skills 边界与职责

两个 skills 按写权限划分：

**template_maker**
- 只负责 `templates/` 目录
- 创建/维护 template.docx、schema.yaml、模板 meta.yaml、router.yaml
- 模板修改后执行最小渲染验证
- 不处理单篇报告，不写入 `reports/`

**report_maker**
- 只负责 `reports/` 目录
- 接收草稿、识别类型、选择模板、创建报告目录、抽取 elements.yaml
- 生成 abstract.docx、body.docx、assets/
- 确认后生成 output.docx 和 output.pdf
- 不修改正式模板，不写 schema.yaml、router.yaml

**report_maker 两阶段流程**
- 第一阶段：抽取与确认。抽取要素和文档片段，等待 Editor 检查
- 第二阶段：渲染与输出。确认后渲染标准报告
- 模板切换仅允许在第一阶段

## 4. 技术栈

| 组件 | 方案 | 说明 |
|------|------|------|
| 模板引擎 | python-docx-template (Jinja2) | 将 elements.yaml 短文本渲染到 Word 占位符 |
| 文档片段处理 | Word 直出 | 第一版不引入 Markdown 中间层，直接拆出 abstract.docx 和 body.docx |
| 结构化抽取 | LLM + schema.yaml | 大语言模型结合 schema 约束从 Word 草稿抽取数据 |
| 复杂资产提取 | PDF 坐标裁剪法 | LibreOffice 转 PDF + PyMuPDF 高清截图，保证视觉保真 |
| 最终发布格式 | libreoffice --headless | Linux/容器环境 Word 转 PDF |

## 5. 实现状态

### 5.1 report_maker Skill

- 两阶段工作流：抽取确认 → 渲染输出
- 要素提取：基于 schema.yaml 的 LLM 提取
- 模板路由：router.yaml
- 片段拆分：abstract + body
- 模板渲染：docxtpl (Jinja2)
- 片段插入：智能占位符定位
- PDF 转换：LibreOffice + 重试

### 5.2 测试覆盖

84 个测试全部通过：common.py (24)、extractor.py (6)、splitter.py (21)、renderer.py (18)。含端到端集成测试。

### 5.3 目录结构

```
neoskills/
├── skills/report_maker/
│   ├── SKILL.md
│   ├── scripts/  (common.py, extractor.py, splitter.py, renderer.py)
│   └── tests/    (unit + integration)
├── templates/
│   ├── router.yaml
│   └── company/  (schema.yaml, template.docx)
├── reports/<report_name>/  (draft, elements, abstract, body, output)
└── docs/
```

### 5.4 待实现

**template_maker Skill**：模板创建/修改、Schema 编辑、模板验证、路由维护

**高级功能**：PDF 坐标裁剪、多语言支持、版本控制、批量处理
