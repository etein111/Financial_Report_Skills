# AI Agent 开发岗 · 投研报告平台项目面试备战

> 面向简历中的这段实习经历：以 OpenCode(Claude Code) 为工作台，Template Maker / Report Maker / Neolyst 三 Skill 协作，Supabase 支撑，9 类投研报告自动生成，Docx 复杂格式治理。
> 本文档基于目录内真实代码编写（`neoskills/` 为更新版，含 ThreadPoolExecutor 与项目经历文档）。

---

## 0. 开场 30 秒：你的"一句话故事"

面试官问"介绍一下这个项目"，别照着简历念，用这个结构：

> 这是一个以 **Agent(OpenCode/Claude Code)作为工作台** 的投研报告生产平台。核心是 **三个协作的 Skill**——template_maker 把样本文档自动变成带 Jinja2 占位符的模板和字段 schema；report_maker 采用**两阶段架构**——LLM 只负责"读懂"草稿（提取 25+ 字段、定位摘要/正文/英文摘要位置），真正的文档操作（占位符替换、docx 拼接、格式修复）全部用纯 Python 保证**确定性和可测试性**；neolyst 是 Supabase 数据层，管模板、报告状态机和审计。技术难点集中在 **OOXML 底层**——我用 lxml 直接解析 document.xml 解决了 python-docx 处理不了深层嵌套表格的问题，设计了 docxcompose 三段式合并 + sectPr 语义恢复，还写了一个占位符 run 修复算法解决 Word 编辑导致的占位符断裂。支持 9 类报告。

加一句价值定位："这个项目最有说服力的点是 **'不确定输入（分析师自由格式的草稿）→ 确定输出（合规标准报告）'的管线设计**，它把 LLM 的幻觉风险限制在'理解'环节，把必须 100% 正确的格式工作交给确定性代码。"

---

## 1. 完整项目陈述（详细介绍版）

> 被问到"请详细介绍一下这个项目"时的完整叙事。按结构记忆主干，每个点展开 1-2 句，整体 3-5 分钟讲完；面试官追问哪块，就跳到后文对应章节深挖（docx 攻坚见第 5 章 STAR，新方法对照见第 4 章应对手册）。

### 1.1 项目背景与目标

- **业务场景**：券商投研部门要批量产出 9 类投研报告（公司覆盖 company / 行业 sector / 快讯 flash / 公司快讯 company_flash / 行业快讯 sector_flash / 宏观 macro / 策略 strategy / 量化 quantitative / 债券 bond）。
- **硬约束**：报告必须满足合规要求（香港 SFC 监管）和统一母版格式——页边距、页眉页脚、分节、分析师执照信息（SFC 代码）、法律披露、英文摘要，全部有严格规范。
- **痛点**：分析师产出的是自由格式的 Word 草稿，过去靠人工套模板排版，一份报告要数小时且经常因格式不达标返工。
- **目标**：用 AI Agent 做工作台，把"模板制作 → 内容生成 → 审核入库"全流程自动化，把单份报告产出从小时级降到分钟级。

### 1.2 整体架构

- **工作台**：OpenCode（Claude Code）作为 AI 编程工作台，提供 agent loop——对话、模型路由、工具调用、权限、文件系统。我们的工程重心放在领域逻辑，而不是重复造 agent 轮子。
- **三个协作 Skill**：
  - `template_maker` 模板制作：Word 样本 → 自动提取结构 → Jinja2 模板 + 字段 schema → 发布到 Supabase
  - `report_maker` 报告生成：草稿 → LLM 提取要素 → 纯 Python 渲染 → 标准报告
  - `neolyst` 数据库管理：Supabase 统一接入，模板管理、报告生命周期、审计、权限
- **数据层**：Supabase（PostgreSQL + Storage）。模板和 schema 存 Storage，报告元数据、状态机、审计日志存 Postgres，RLS 做行级权限。
- **协作方式**：三个 Skill 既可被用户对话触发，也可互相调用（report_maker 内部通过 `neolyst_integration.py` 调 neolyst 的 RPC），形成一条完整链路。

### 1.3 template_maker —— 模板制作 Skill

- 解析 Word 样本的段落、表格（含嵌套）、页眉页脚，把文本值替换成 Jinja2 占位符 `{{ field_name }}`，支持全匹配和首行匹配（超长文本用首行匹配）。
- 分析师字段智能布局检测：识别 `[Table_Author]` 表格，按行数动态算出分析师数量，自动生成 `{{ a1_cn }} {{ a1_en }}, SFC:{{ a1_sfc }}` 组合占位符。
- 用 lxml 直接解析 `document.xml` 定位摘要/正文/附录位置（绕过 python-docx 嵌套表格限制）。
- 自动生成 schema.yaml（字段类型、来源、提示信息），`validate.py` 比对 schema 与模板占位符，从源头保证"提取什么"和"填到哪"一致。

### 1.4 report_maker —— 报告生成 Skill（核心）

**两阶段架构是核心设计**："LLM 理解，Python 执行，幻觉留在理解层"。

- **第一阶段（LLM 驱动，只做理解）**：
  1. 预处理：docx_reader 展平嵌套表格 + 段落带索引 `[P0]...[Pn]`，末尾 50 段重点标注（英文摘要位置）；
  2. 一次 LLM 调用完成：提取 25+ 字段 + 判断摘要/正文/英文摘要的位置（起止 marker）；
  3. 交互确认：展示摘要和字段表，等待用户确认（human-in-the-loop）。
- **第二阶段（纯 Python 执行，保证确定性与可测试性）**：
  1. `placeholder_fixer` 修复 Word 拆分的占位符 run；
  2. `docxtpl` 渲染占位符替换；
  3. `ThreadPoolExecutor(2)` 并发生成相对涨跌图与推荐评级图（yfinance + matplotlib）；
  4. `docxcompose` 三段式合并插入正文，`sectpr_manager` 恢复 4 个分节的页边距/页眉页脚；
  5. 字体约束（中文楷体、英文 Calibri）、图表 Jinja2 转义恢复、附录验证。
- 输出标准格式 docx（可选转 PDF），并走 `workflow.py` 保存/提交到 neolyst。

### 1.5 neolyst —— 数据库管理 Skill

- **报告状态机**：`draft → submitted → published`，可撤回 `draft`、可退回 `rejected`；所有流转由数据库 RPC + 触发器原子执行，非法流转直接抛异常。
- **审计追踪**：`report_write_status_log` 触发器在状态变化时自动写入 `report_status_log`（jsonb 关键字段快照 + from/to + 时间戳）。
- **动态模板**：`resolve_template_for_report()` 运行时从 Storage 下载模板和 schema，模板更新后新报告自动用新版，无需改代码；分析师信息、coverage 关系也是运行时查库。
- **权限体系**：3 层 RLS——admin / SA（super analyst）/ analyst，行级隔离（analyst 只看自己的草稿和已发布报告，SA 看 submitted/published/rejected，admin 全量）。

### 1.6 核心技术难点与攻克（4 个）

1. **嵌套表格提取**（见第 5 章 STAR-1）：python-docx 只返回顶层表格，用 lxml `tree.iter(W:tbl)` 全量抓取任意深度 + 递归重建层级。
2. **合并破坏 sectPr**（见第 5 章 STAR-2）：docxcompose 会破坏分节格式，设计"合并前保存 4 个 sectPr → 三段式切分合并 → 按语义位置恢复"。
3. **占位符 run 断裂**（见第 5 章 STAR-3）：Word 编辑把 `{{ a1_email }}` 拆到多个 run，写算法渲染前合并。
4. **图表 Jinja2 冲突**：图表 XML 里 `{{ }}` 会被 docxtpl 误当模板语法，插入前转义、渲染后恢复。

### 1.7 成果与量化指标

- 3 个 Skill 覆盖全流程；~9000 行 Python；9 种报告类型；25+ 字段 schema。
- 4 层嵌套表格递归提取、4 段分节符管理、三段式 docxcompose 拼接。
- 7 个 migration、15 个 RPC、3 层 RLS；30+ 测试（单测/集成/E2E/数据库）。
- 项目共 698 次提交，个人约 270 次。格式标准化后返工率大幅下降，单份报告从"小时级人工排版"到"分钟级自动生成"。

### 1.8 我的角色与收获

- 独立负责 docx 底层攻坚（嵌套表格、sectPr、占位符修复）和两阶段管线设计。
- 最大的方法论收获：**"不确定输入 → 确定输出"的管线设计**——把 LLM 放在"理解"环节、把确定性代码放在"执行"环节，既保质量又可测试。这个模式可以泛化到任何"自由格式输入 + 严格格式输出"的场景。
- 反思与演进方向：① 用结构化输出/function calling 替代 YAML 文本解析，配合 prompt caching 压成本；② 模板锚点数据化，去掉硬编码；③ 用 Word Content Controls 替代 Jinja 占位符作为长期方案；④ 引入 LLM-as-judge 做报告质量回归评估。（详见第 4 章应对手册）

---

## 2. 面试官会攻击的 6 个点（先自查，别被问懵）

### ① 简历硬伤：report_audit_log 不存在 ⚠️

简历和 `project-experience-neoskills.md` 都写了 "`report_audit_log` 记录字段级编辑历史"，但翻遍所有 migration，**只有 `report_status_log`（状态流转审计），没有 `report_audit_log` 这张表**。审计是真实存在的（`report_write_status_log` 触发器 + jsonb 快照，`squash_all.sql:233`），但"字段级编辑历史"是**没实现的夸大**。

**怎么办（三选一）**：
- 面试前补一张真的 `report_audit_log` 表（用 trigger 记录 OLD/NEW 的 diff）；
- 或改简历措辞为"**状态流转审计 + 关键字段快照**"（这是代码里真实做到的）；
- 至少预判这个问题："你简历说字段级审计，具体怎么做的？" → 诚实回答 + 补一句"目前审计的是状态流转和关键字段快照，字段级 diff 是我规划的下一步"。

面试官宁可听到你主动承认边界，也不想听你吹。

### ② 硬编码锚点："APPENDIX 1" / "附录APPENDIX"

`sectpr_manager.py:130-145` 靠**文本匹配 `APPENDIX 1` 和 `Table_disclaimer`** 来决定每个 sectPr 该分配哪个模板分节的页边距——这是脆弱的启发式。追问：**"如果模板里英文标题改了，代码就崩，你有考虑过？"**

**防御回答**：承认这是"模板契约"——`_save_all_template_sectPrs`（`sectpr_manager.py:32`）按**顺序**保存了 4 个 section（cover/body/english_summary/appendix），恢复时再按**语义位置**分配。改进方向：把这些锚点抽到 schema.yaml 里做成数据驱动，或者用 `w:type` + sectPr 的**顺序索引**而不是文本匹配。如果你实际遇到过（比如英文模板没英语摘要），可以讲这个真实的坑。

### ③ placeholder_fixer 只处理"同一父元素内"的 run 断裂

`fix_runs_in_parent`（`placeholder_fixer.py:15`）把所有收集的 run 合并到**第一个 run 的父元素**里，并 `parent.remove(run)`。如果占位符跨 `w:hyperlink`、跨表格等不同容器被拆分，第二个 run 根本不在第一个 run 的父元素里，`remove` 会抛异常（整个函数被外层 try/except 兜住，打印警告后继续）。

**防御回答**：说明你清楚这个边界——"Word 编辑造成的 run 拆分绝大多数发生在同一段落/同一父级内，这是我们覆盖的主场景；跨容器拆分我们用 try/except 兜底不阻塞流程。如果要更稳健，应该按每个 run 自己的 getparent() 分组合并。" **主动说出代码的边界，是加分项不是减分项。**

### ④ ThreadPoolExecutor(2) 的 GIL 问题

简历写"ThreadPoolExecutor 并发图表渲染"。内行会问：**"matplotlib 是 CPU 密集，Python 有 GIL，线程并行有效吗？"**

**正确回答（分两层）**：
1. 这里的两个图表（`_generate_relative_chart` / `_generate_recommendation_chart`）主要耗时是 **yfinance 的网络请求（I/O 密集）**，`max_workers=2` 是为了让两张图的数据抓取并行，线程在等待网络时能让出 GIL，所以有效；
2. matplotlib 的绘制部分确实受 GIL 限制，`ThreadPoolExecutor` 对 CPU 段没有加速——如果要扩展到"9 类报告 × 每份多图"，我会把渲染改成 **ProcessPoolExecutor** 或引入**市场数据缓存层**，避免重复抓 yfinance。

这题答好了直接体现你对并发的理解深度。

### ⑤ "为什么不直接用 python-docx 的 cell.tables？"

简历写"python-docx 深层嵌套表格支持不足"。实际上 python-docx 有 `cell.tables`，但它只返回**直接子表格**且不保留层级。你的 `docx_reader.py:41` 用 `tree.iter(W:tbl)` 拿到**文档顺序的扁平列表**，再用 `_extract_cell_data`（`docx_reader.py:97`）通过 `findall` 递归重建层级。**追问**："`iter` 返回的是文档顺序，你怎么知道哪个表嵌套在哪个表里？"

**答案**：提取时用 `tree.iter(W:tbl)` 保证**任何深度的表格都不会漏**（这是 python-docx 做不到的），而结构化重建靠 `_extract_cell_data` 里对直接子表格的递归 `findall`——每一层只找直接孩子，自然保持了父子关系。文本提取用 `.iter(W:t)` 全展平，所以 4 层嵌套的内容文本完整。

### ⑥ 两阶段架构被挑战："为什么不让 LLM 直接生成整个 docx？"

这是**最可能被问的哲学题**，答案在第 3 部分 A 组。核心：金融合规报告对格式是**硬约束**，LLM 生成 OOXML 不确定、不可测；你的设计是"**可变输入 → 固定输出**"的通用模式。

---

## 3. 核心问题 + 骨架答案（背主线，展开细节）

### A 组 · 整体架构与 Agent 体系（最像"AI agent 开发岗"会问的）

**A1. 为什么设计成三个 Skill，而不是一个大的 agent？**

> 职责正交、可组合。template_maker 产模板、report_maker 消费模板、neolyst 管数据。每个 Skill 既是**用户可对话的工具**，也是**其他 Skill 可调用的 API**（report_maker 通过 `neolyst_integration.py` 调 neolyst 的 RPC）。单一 agent 会变成巨型 prompt 和一堆 if-else，拆成 Skill 后每个 SKILL.md 是一个**可独立测试、可单独发布**的能力单元。

**A2. 两阶段架构（LLM 理解 + Python 执行）为什么这样拆？**

> 一句话：**"把幻觉留在理解层，把确定性留给执行层。"** 三点支撑：①金融报告格式是合规硬约束（恒利证券 SFC 监管），docx 结构必须精确，LLM 生成的 OOXML 不可测；②可测试性——renderer 是纯函数，15+ 单测直接跑；③成本——渲染阶段零 LLM 调用。升级点主动讲：**"抽取现在是把 LLM 结果写成 YAML 再 PyYAML 解析，更现代的做法是用 function calling / 结构化输出按 schema 强制，失败自动重试，还能配合 prompt caching 压成本。"** 这句是加分项。

**A3. Skill 和 MCP 的区别？你觉得这二者关系？**

> 2025-2026 AI agent 岗位的高频题。**Skills = 流程/能力定义（怎么做），MCP = 工具接入层（能做什么）。** 这套 Skill 是文件化的能力规格（SKILL.md + scripts + tests），挂在 Claude Code/OpenCode 的 agent loop 上；MCP 解决的是"agent 怎么调外部工具/API"。二者互补——完全可以把模板制作、报告生成的流程封装成 MCP server 暴露给任何支持 MCP 的 agent，Skill 里的提示词和规范原样迁移。**如果面试官问"为什么不直接上 LangGraph/Agent SDK"**，答：我们用现成 harness 的 agent loop（模型路由、工具调用、权限、文件系统），把工程精力投在领域逻辑；需要程序化编排多个 agent 时，我会用 Agent SDK/LangGraph 重写编排层，但 Skill 内沉淀的流程资产可复用。

**A4. LLM 抽取一次调用就处理整份 300 页草稿，token 和上下文问题怎么处理？**

> 预处理（docx_reader 展平表格 + 段落带索引）后只把**文本内容**喂给 LLM，不是整份二进制；正文主体 200-300 页会超上下文——实际上抽取是**锚点式**（LLM 只要返回"摘要从哪到哪、正文起止 marker、字段值"），不需要全量进上下文，而且 **prompt caching** 可以缓存固定的抽取提示词部分。追问空间：承认大报告需要分块+每块二次校验，这是可讲清的演进点。

### B 组 · Docx 底层攻坚（核心卖点，必考）

**B1. python-docx 处理不了嵌套表格，你具体怎么绕过的？**

> python-docx 的 `document.tables` 只返回顶层表格，`cell.tables` 只有直接子表。我用 `zipfile` 解包 docx → `lxml` 解析 `word/document.xml` → `tree.iter(W:tbl)` 拿到**所有层级**表格的扁平列表保证不漏，再递归 `findall` 重建表→行→单元格→嵌套表结构（`docx_reader.py`）。字段提取（`field_extractor.py`）在此基础上按 schema 别名匹配。

**B2. 讲讲三段式 docxcompose 合并和 sectPr 恢复，为什么需要它？**

> docxcompose 的 `append()` 在合并时会**破坏被追加文档的 sectPr**（body-level sectPr 被移除，分节页眉页脚 rId 引用损坏），导致合并后页边距、页眉页脚错乱。方案（`composer.py:34`）：
> 1. 合并前 `_save_all_template_sectPrs` 把模板 4 个 section（cover/body/english_summary/appendix）的 sectPr 深拷贝保存；
> 2. 把模板从 BODY_MARKER 处**切成三段**：part1（封面，marker 前）+ part3（英文摘要+法律披露，marker 后），中间插入 body.docx；
> 3. `docxcompose` 依次拼接，最后 `_restore_all_sectPrs` **按语义位置**把 4 个 sectPr 放回去（continuous→封面，APPENDIX 1 前→正文，法律附录前→英文摘要，body-level→附录）。
> 因为每个 section 自带 header/footer 引用，body 插入后自动继承对应 section 的页眉页脚，**不需要额外处理页眉页脚**——这是这个设计最优雅的地方。

**B3. 占位符 run 修复算法怎么工作的？为什么要修？**

> Word 编辑时会把 `{{ a1_email }}` 拆到多个 `<w:r>` 里（比如加粗/改字导致 run 边界变化），docxtpl 按 `{{ }}` 匹配就会失败。`placeholder_fixer.py` 在渲染前扫描：发现 `{{` 后持续累积后续 run 的文本，直到遇到 `}}`，把累积文本合并到第一个 run 并删除其余 run（`fix_runs_in_parent`），让占位符成为单一 run。**亮点**：还能顺带讲 `image_handler.py` 里的图表 Jinja2 转义——图表 XML 里如果路径含 `{{ }}` 会被 docxtpl 误当模板语法，插入前转义、渲染后恢复。

**B4. 简历说"lxml 递归解析底层 XML 突破 python-docx 限制"，现在的替代方案你了解吗？**

> 见第 4 部分对照表，直接背答案。

### C 组 · Supabase / 数据层

**C1. 报告状态机为什么用 RPC + 触发器，不在应用层做？**

> 状态流转是不可绕过的不变量，必须在**数据库层**原子保证。`report_status_is_valid`（`squash_all.sql:207`）是 IMMUTABLE 函数定义合法路径 `draft→submitted→published/rejected/draft`、`rejected→draft`；`report_enforce_status_transition` 是 BEFORE UPDATE 触发器，非法流转直接 `raise exception`。同时 `report_write_status_log` 触发器自动写审计日志（jsonb 快照 + from/to status + 时间）。这样**任何客户端**（Skill、Web、直接 SQL）都绕不过状态机和审计。

**C2. RLS 三层权限怎么设计的？current_app_role() 安全吗？**

> `current_app_role()`（`squash_all.sql:87`）从 JWT 的 `app_metadata.role` 读角色，策略示例：`report_select`（`squash_all.sql:1639`）— admin 全量、SA 看 submitted/published/rejected、analyst 只看自己 + 已发布。**要主动讲安全细节**：`SECURITY DEFINER` 函数会**绕过 RLS**，所以有一个专门 migration `remove_unnecessary_security_definer.sql` 把能改 `INVOKER` 的都改掉，保留的 DEFINER（如 `resolve_coverage` 只读）也限定了最小暴露。加分：提一句 Postgres 搜索路径注入——生产级做法是 `SET search_path = pg_catalog, public` 防止攻击者劫持函数解析。

**C3. 动态模板管理怎么实现的？**

> `resolve_template_for_report()` 运行时从 Supabase Storage 下载模板 + schema，而非本地静态文件；模板更新后新报告自动用新模板，不用改代码。分析师信息也是运行时 `resolve_analysts()` 查库，保证 SFC 执照号、邮箱是**当前数据**。`reuse_template` RPC 做多报告类型静态路径复用。

### D 组 · 测试、质量、评估

**D1. 怎么保证生成的报告没占位符残留？怎么保证质量？**

> 渲染后 `verify_no_placeholders` 正则扫全部段落和表格，发现 `{{}}` 直接抛错；`post_processor._verify_appendix_with_lxml` 验证法律附录完整性；输出统计段落/表格/图片数。模板制作阶段的 `validate.py` 把 schema 字段和模板占位符**在源头比对**，避免填充遗漏。测试：report_maker/tests 15+ 单测、neolyst/tests 12+、supabase/tests 有 SQL 测试；`evals/evals.json` 有端到端交互评估用例。**现代补充**：如果用 LLM-as-judge + golden 数据集做回归，会更有说服力（见第 4 部分）。

**D2. 你最自豪的 bug 修复是哪个？（行为题）**

> 推荐讲 **sectPr 恢复** 或 **占位符 run 修复**，STAR 素材在第 5 部分。

---

## 4. "你的方法过时了"应对手册 ⭐

面试官说"这方法过时了，现在有 XX，你用过吗"，**别慌也别硬辩**，按这个套路：**先承认 → 讲你方法为何在当时/在此场景成立 → 给出升级路径 → 表达开放性**。

| 简历方法 | 可能的"过时"挑战 | 应对要点 |
|---|---|---|
| **lxml 手写递归解析 docx 嵌套表格** | "现在有 MinerU / Nougat / 布局感知模型，直接把 PDF 转成结构化文本/JSON" | 承认这是 2024-2025 的热点方向（MinerU 对中文文档效果好）；**解释差异**：我们是**从 Word 源文件出发**且要保证确定性、离线、零 OCR 误差；升级路径：如果输入是 PDF 报告，我会用 MinerU/marker 做布局解析，或用**视觉 LLM 对渲染后的 PDF 页做零样本抽取**；甚至可讲"金融场景 OCR 会引入数字错误，合规上我们倾向源文件解析"。 |
| **Jinja2 占位符 + run 合并修复** | "现在用 Word Content Controls(SDT) 绑定，或用 docxtemplater 直接支持" | Content Controls 确实是**更稳健的长期方向**（不会被拆分、结构语义化），我会把它列为 v2；**但占位符方案**胜在模板制作简单（分析师用 Word 改模板即可）且继承模板格式；`docxtemplater`（JS）内部同样要处理 run 拆分，本质是一个问题。 |
| **docxcompose 三段式 + sectPr 手工恢复** | "为什么不用 LibreOffice headless(UNO) 合并/转换？" | LibreOffice 合并语义更可靠、兼容性更好，但**重依赖、难 CI 嵌入、不好精确控制分节格式**；4-section 模板场景，sectPr 级合并更轻且确定性更高。升级路径：把模板解析成**文档对象模型**（sections/headers/footers/styles），从模型重建输出，而不是在 XML 上做手术——这才是根治。 |
| **ThreadPoolExecutor(2) 并发图表** | "现在用 asyncio / 或把渲染丢到独立服务" | 见 ①④ 的 GIL 两层回答；补充：网络 I/O 用 asyncio+httpx 更省线程，yfinance 拉数 + matplotlib 渲染可加**数据缓存层**避免重复请求。 |
| **LLM 文本抽取 + YAML 解析** | "现在用 function calling / 结构化输出（strict schema）直接拿 JSON，还带重试" | 主动提（见 A2）：结构化输出按 schema 约束解码，天然校验、可自动重试、可用 **prompt caching** 缓存抽取提示词；当时解析 YAML 后也按 schema 校验，但结构化输出是明确升级方向。 |
| **三个 Skill 跑在 Claude Code 上** | "这算什么，现在有 MCP、有 Agent SDK、有 LangGraph" | 见 A3。核心观点：**Skills 与 MCP/Agent SDK 是不同层，不冲突**；把"流程规范"沉淀为 Skill 文件、把"工具接入"用 MCP 统一，是当前 agent 工程的最佳实践组合。 |
| **Supabase RLS/RPC 审计** | "不用 pgAudit？不用事件溯源？" | Supabase 是当前主流 BaaS，没问题；补充：审计日志若要求**不可篡改**，可加 pgAudit 或独立 append-only audit schema；上游数据流若要多写者并发，可加乐观锁/版本号。 |
| **手工 yfinance + matplotlib 画图** | "图表应该用 ECharts/Plotly，或 LLM 生成图表？" | 金融报告要求静态、可嵌 docx、风格统一（恒利品牌色），matplotlib 确定性强；若前端交互，再用 ECharts。 |
| **模板 = docx 文件** | "模板为什么不用 JSON Schema 驱动，直接程序化建 docx？" | 因为**业务方用 Word 维护模板样式**，模板 docx 是设计师/合规口的产物；程序化建 docx 适合从零生成，不适用于"复用既有母版格式"。 |

**必须能脱口而出的"新方法"关键词**（AI agent 岗面试加分）：MCP、Agent Skills、Structured Outputs / function calling、Agent SDK / LangGraph / CrewAI、prompt caching、LLM-as-judge + evals、RAG + pgvector、Agent 可观测性（Langfuse / OpenTelemetry GenAI）、MinerU / vision-LLM 文档解析、long-context 模型（Claude 5 家族等）让"上下文管理"成本下降。

---

## 5. 行为面试 STAR 素材包（3 个真实故事）

**STAR-1 · 嵌套表格字段提取不全**（根因/方案型）
- **S**：封面是 3-4 层嵌套大表格，关键数据在深层子表。
- **T**：python-docx 只返回顶层表，`cell.tables` 只给直接子表，字段提取一直缺。
- **A**：改用 `zipfile` 解包 + `lxml` 解析 `document.xml`，`tree.iter(W:tbl)` 全量抓取任意深度，再递归重建表-行-单元格-嵌套表结构；LLM 抽取提示词强制"深入每一层嵌套表搜索"。
- **R**：字段提取从"经常缺"到"25+ 字段全提取"，配套单测覆盖 4 层嵌套 fixture。

**STAR-2 · docxcompose 合并把页边距/页眉页脚弄丢**（最值得讲的硬核故事）
- **S/T**：合并后每个分节的页边距、页眉页脚引用被 docxcompose 破坏，报告格式不达标。
- **A**：先 `deepcopy` 保存模板 4 个 sectPr → 三段式切分合并 → 合并后**按语义位置**（continuous→封面、APPENDIX 1 前→正文、法律附录前→英文摘要、body-level→附录）恢复；body 内部 section 用 `w:br type=page` 分页符替代，避免它的 sectPr 污染模板页眉页脚。
- **R**：跨节页眉页脚与页边距 100% 还原，不再有"格式错乱返工"。

**STAR-3 · Word 编辑拆散占位符导致渲染残留**
- **S/T**：分析师在 Word 里改模板后，`{{ a1_email }}` 被拆到多个 run，docxtpl 替换失败，报告里残留占位符。
- **A**：写 `placeholder_fixer.py` 渲染前扫描：遇 `{{` 累积后续 run 文本直到 `}}`，合并到首 run、删除其余 run；同时处理图表 XML 里 `{{}}` 与 docxtpl 的语法冲突（转义+恢复）。
- **R**：占位符残留率归零，渲染后校验器（`verify_no_placeholders`）兜底。

---

## 6. 面试准备清单 & 临场小抄

**面试前 10 分钟过一遍**：
1. `docx_reader.py:41` — `tree.iter(W:tbl)` 解决嵌套表格
2. `composer.py:34` — 三段式合并；`sectpr_manager.py:32/84` — 4 sectPr 语义恢复
3. `placeholder_fixer.py:15` — run 合并算法
4. `renderer.py:151`（neoskills 版）— ThreadPoolExecutor(2) 图表并发
5. `squash_all.sql:207/186/233` — 状态机 + 触发器审计；`:87/1639` — RLS
6. 两阶段架构一句话："**LLM 理解，Python 执行，幻觉留在理解层**"
7. 三件套防御："**承认边界 → 解释当时选择 → 给出升级路径**"
8. ⚠️ 记得改掉简历里的 `report_audit_log` 措辞，或先补实现

**核心代码位置索引**：
- `neoskills/skills/report_maker/scripts/`：renderer / composer / sectpr_manager / placeholder_fixer / docx_reader / splitter / field_extractor / chart_generator / content_inserter / post_processor / image_handler
- `neoskills/skills/template_maker/scripts/`：document / template / invoke / schema / validate
- `neoskills/skills/neolyst/scripts/`：report / analyst / coverage / template / connection / rpc / storage
- `neoskills/supabase/migrations/`：squash_all.sql（schema + RLS + RPC + 触发器）
- `neoskills/skills/report_maker/evals/evals.json`：端到端评估用例
