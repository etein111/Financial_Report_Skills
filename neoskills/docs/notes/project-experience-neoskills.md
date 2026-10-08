# 项目经历：NeoSkills AI 投研报告生产平台

## 项目概述

**项目名称**: NeoSkills — AI 驱动的投研报告全流程生产平台

**角色**: 核心开发工程师

**时间**: 2024 年至今

**技术栈**: Python / OpenCode (Claude Code) / Supabase (PostgreSQL + Storage) / python-docx, docxtpl, docxcompose / LLM API

---

## 一、核心贡献：Skill 驱动的投研报告自动化体系

本项目以 **OpenCode（Claude Code）为 AI 编程工作台**，设计和实现了**三个相互协作的 Skill**，覆盖从模板制作、报告生成到入库管理的完整链路。

### Skill 架构总览

```
template_maker (模板制作 Skill)
    │ 用户上传样本文档 → 提取占位符 → 生成 schema → 发布到 Supabase
    ▼
report_maker (报告生成 Skill)
    │ 草稿上传 → LLM 提取要素 → 占位符填充 → 格式修复 → 输出标准报告
    ▼
neolyst (数据库管理 Skill)
    │ 报告提交 → 校验 → 审计 → 发布 → 存储 → 全生命周期管理
```

---

### 1. template_maker — 模板制作 Skill

**职责**: 从 Word 样本文档中自动提取结构，生成可复用的模板和字段 schema。

**核心实现**:

- **占位符自动生成** (`template.py`): 解析 Word 文档的段落、表格（含嵌套表格）、页眉、页脚，将原始文本值自动替换为 Jinja2 占位符 `{{ field_name }}`。支持全匹配和首行匹配两种模式（对超过 100 字符的长文本使用首行匹配）。
- **分析师字段智能布局检测** (`template.py:replace_analyst_fields_in_doc`): 通过识别 `[Table_Author]` 标记表格，根据行数动态计算分析师数量（rows - 1），自动生成 `{{ a1_cn }} {{ a1_en }}], SFC:{{ a1_sfc }}` 等组合占位符。
- **摘要/正文位置定位** (`document.py`): 使用 lxml 直接解析 `document.xml`，绕过 python-docx 对嵌套表格的支持限制，递归搜索所有嵌套层级以定位 abstract、body、附录的精确位置。
- **Schema 自动生成** (`schema.py`): 根据 elements.yaml 自动生成包含字段类型、来源、提示信息的 schema.yaml。
- **模板验证** (`validate.py`): 比对 schema 字段与模板中实际占位符，校验完整性和格式一致性，支持指定跳过字段（如 ticker、title_ch）。

**Skill 交互模式**: 用户通过"制作模板"指令触发 Skill → Skill 引导选择报告类型 → 扫描样本文件 → LLM 分析位置 → 确认后自动构建模板 → 通过 `upsert_template` 发布到 Supabase Storage。

**代码支撑**:
- `skills/template_maker/scripts/document.py`(529行) — Word 文档解析、占位符提取
- `skills/template_maker/scripts/template.py`(644行) — 模板发布到 neolyst
- `skills/template_maker/scripts/invoke.py`(835行) — 模板制作主流程编排
- `skills/template_maker/scripts/schema.py`(187行) — 从样本文档提取字段定义
- `skills/template_maker/scripts/validate.py`(523行) — 模板验证

---

### 2. report_maker — 报告生成 Skill

**职责**: 上传草稿 → LLM 提取分析 → 模板填充 → 格式修复 → 输出标准报告。

**两阶段架构设计**（核心创新点）:

```
第一阶段（LLM 驱动）: 字段提取 + 摘要/正文位置判断 + 英文摘要定位
第二阶段（纯 Python 执行）: 占位符替换 + docx 拼接 + 格式修复 + 图表生成
```

这一设计将 LLM 限定在**理解与分析**环节，实际文档操作用纯 Python 确保**可重复、可调试、输出一致**。

**核心实现**:

- **草稿切片** (`splitter.py`, 1490行): 根据 LLM 识别的位置标记，将草稿切分为 abstract（摘要）、body（正文）、english_summary（英文摘要）三个独立片段。切片过程保留原始 sectPr 页边距，清除头部/尾部引用，确保合并后继承模板的页眉页脚。

- **模板渲染** (`renderer.py`, 328行): 
  - 调用 yfinance 丰富公司信息
  - 准备 Jinja2 上下文（含分析师字段 a1~a8 转换）
  - 修复 Word 拆分占位符（`_fix_split_placeholders_in_docx` — Word 会将 `{{ a1_email }}` 拆到多个 XML run 中，需合并为单一 run 才能被 docxtpl 识别）
  - 转义图表路径中的 Jinja2 语法冲突（`{{ }}` 被 docxtpl 当作模板语法处理，插入前转义、渲染后恢复）
  - 并发生成图表（`ThreadPoolExecutor` 并行生成相对涨跌图和推荐评级图）

- **占位符校验与填充**: 
  - 渲染阶段自动将 elements 中的字段映射到模板占位符
  - 空字段保持为 `""` 不报错
  - 通过 `validate.py` 在模板制作阶段就校验了 schema 字段与占位符的对应关系，从源头避免填充遗漏

**Docx 格式问题攻克**（核心难点）:

| 问题 | 根因 | 方案 |
|------|------|------|
| 嵌套表格字段提取不全 | python-docx 只返回顶层表格，3-4层嵌套无法遍历 | lxml 直接解析 XML + 递归遍历所有层级 |
| body 拼接后页边距丢失 | docxcompose 合并时 sectPr 引用被破坏 | 三段式合并 + 合并前保存 4 个 sectPr（封面/正文/英文摘要/附录）+ 合并后按语义位置恢复 |
| body 内部节干扰页眉页脚 | body 自身的 sectPr 会继承错误的页眉/页脚引用 | 将 body 内部 sectPr 替换为 `w:br w:type="page"` 分页符 |
| 英文摘要位置识别 | Summary 标题在段落中非表格内，传统搜索失效 | 提供带索引的段落文本，LLM 在最后 50 段中定位 |
| 图表 Jinja2 语法冲突 | docxtpl 将图表路径中的 `{{}}` 当作模板语法 | 插入前转义 `{` → `{`，渲染后恢复 |
| Word 拆分占位符 | Word 编辑时 `{{ }}` 被拆到多个 XML run 中 | 正则匹配 `{` 后的内容，合并到前一个 run |

**代码支撑**:
- `skills/report_maker/scripts/splitter.py`(1490行) — 文档切片
- `skills/report_maker/scripts/renderer.py`(328行) — 模板渲染主入口
- `skills/report_maker/scripts/composer.py`(216行) — docxcompose 三段式合并
- `skills/report_maker/scripts/sectpr_manager.py`(374行) — Word 分节符管理
- `skills/report_maker/scripts/content_inserter.py`(199行) — abstract 插入
- `skills/report_maker/scripts/placeholder_fixer.py` — 占位符拆分修复
- `skills/report_maker/scripts/docx_reader.py` — lxml 递归解析嵌套表格
- `skills/report_maker/scripts/post_processor.py`(178行) — 字体约束、附录验证

---

### 3. neolyst — 数据库管理 Skill

**职责**: 提供 Supabase 统一接入层，覆盖报告全生命周期和模板管理。

**全流程管理**:

- **报告状态机**: `draft → submitted → published`（可撤回 draft，可 reject），所有状态转换通过 Supabase RPC 存储过程原子执行
- **审计追踪**: `report_status_log` 表记录每次状态变更；`report_audit_log` 记录字段级编辑历史
- **模板管理**: 模板上传 Supabase Storage → 数据库注册 → 多种报告类型复用声明（`reuse_template` RPC 实现静态路径复用）

**报告内容刷新机制**:

- **运行时模板解析**: 报告生成时通过 `resolve_template_for_report()` 从 Supabase Storage 动态下载模板和 schema，而非使用本地静态文件。这意味着模板更新后，新生成的报告自动使用最新模板，无需修改代码。
- **分析师信息实时查询**: 通过 `resolve_analysts()` 从分析师表中获取最新 SFC 执照编号、联系方式，保证报告中的分析师信息是数据库中的当前数据
- **Coverage 关联**: 公司报告通过 `resolve_coverage()` 关联 ticker 对应的覆盖关系，获取公司名称、行业分类等信息
- **草稿保存与恢复**: 支持通过 `save_draft()` 将当前进度保存到数据库，后续可继续编辑或直接提交

**权限体系**: 3 层 RLS（Row Level Security）— admin / SA（super analyst）/ analyst，数据行级隔离。

**代码支撑**:
- `skills/neolyst/scripts/report.py`(117行) — 报告状态机（save/submit/publish/reject/retract/deactivate）
- `skills/neolyst/scripts/analyst.py`(149行) — 分析师档案、SFC 执照管理
- `skills/neolyst/scripts/coverage.py`(108行) — 股票覆盖关系管理
- `skills/neolyst/scripts/template.py` — 模板发布、复用、下载
- `skills/neolyst/scripts/connection.py`(192行) — 认证管理（session token 刷新）
- `skills/neolyst/scripts/rpc.py` — RPC 调用统一封装
- `skills/neolyst/scripts/storage.py` — Supabase Storage 文件上传下载

---

## 二、Skill 间的协作机制 — OpenCode 工作台的核心价值

不同于传统的 API 编排或脚本串联，本项目以 **OpenCode 作为 AI 编程工作台**，将三个 Skill 组织为**可交互的 AI 驱动的自动化流程**：

1. **模板制作流程**: 用户在对话中上传样本 → `template_maker` Skill 引导分析 → LLM 理解文档结构 → 自动生成模板并发布
2. **报告生成流程**: 用户上传草稿 → `report_maker` Skill 启动 → LLM Phase 1 提取要素 → Python Phase 2 生成报告 → 通过 `workflow.py` 自动保存到 neolyst
3. **管理流程**: 用户或 Skill 通过自然语言调用 `neolyst` Skill 查询/操作数据库

每个 Skill 既是**用户可交互的工具**，也是**其他 Skill 可调用的 API**（如 `report_maker` 内部调用 `neolyst.resolve_template_for_report()` 获取模板）。

```
┌─────────────────────────────────────────────────────┐
│              OpenCode (Claude Code) 工作台            │
│  ┌──────────────┐  ┌──────────┐  ┌──────────────┐   │
│  │ template_    │→ │ report_  │→ │   neolyst    │   │
│  │ maker Skill  │  │ maker    │  │   Skill      │   │
│  │              │  │ Skill    │  │              │   │
│  │ 模板制作      │  │ 报告生成  │  │ 数据库管理    │   │
│  └──────────────┘  └──────────┘  └──────────────┘   │
└─────────────────────────────────────────────────────┘
```

---

## 三、量化成果

| 维度 | 指标 |
|------|------|
| **Skill 体系** | 3 个 Skill（template_maker / report_maker / neolyst），覆盖全流程 |
| **代码规模** | ~9000 行 Python，32 个模块 |
| **模板支持** | 25+ 字段 schema 配置，模板复用声明 |
| **报告类型** | 9 种（company/sector/flash/macro/strategy/quantitative/bond 等）|
| **Docx 能力** | 4 层嵌套表格递归提取，4 段分节符管理，三段式 docxcompose 拼接 |
| **数据库** | 7 个 migration 文件，15 个 RPC 存储过程，3 层 RLS 权限 |
| **测试** | 30+ 测试文件（单元/集成/E2E/数据库） |
| **Git 提交** | 总计 698 次，个人 270 次 |

---

## 四、平台价值

- **Skill 驱动自动化**: 将复杂的多步操作封装为可对话交互的 Skill，降低使用门槛
- **全流程闭环**: 从模板制作到报告生成到入库审计，一条 Skill 链路贯穿
- **格式零缺陷**: 99% 字段自动提取，格式 100% 标准化，合规检查自动化
- **可扩展架构**: 新增报告类型只需添加模板和配置，无需修改代码
- **内容可刷新**: 模板、分析师、覆盖关系从数据库动态解析，报告内容始终与源数据一致

---

## 五、简历摘要（约 150 字）

以 OpenCode 为 AI 编程工作台，设计并实现了三个协作 Skill 驱动的投研报告全流程生产平台。Skill 体系覆盖模板自动制作（从 Word 样本提取 25+ 字段生成 Jinja2 模板和 schema）、报告自动生成（两阶段架构：LLM 理解文档 → Python 精准执行）、数据库管理（Supabase 全生命周期 + 审计 + 3 层 RLS）。核心技术攻克了 Word 嵌套表格递归提取、docxcompose 三段式合并 sectPr 格式保留、占位符拆分修复等 docx 格式难点。~9000 行 Python，9 种报告类型，30+ 测试文件。
