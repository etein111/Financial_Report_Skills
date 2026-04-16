# NeoSpace 工作台插件系统架构与技术实现

第 1~2 节供业务人员与项目经理阅读；第 3~5 节供研发落地参考。

## 1. 项目概述与定位

NeoSpace 是 Neolyst 研究报告管理平台的 AI 智能工作台插件系统，通过独立可编排的 Agent Skills 实现报告的自动化编辑、审核与发布。

NeoSpace 处于 Neolyst 核心系统上层，负责报告的智能生成、自动化审核和合规检查。数据持久化、权限管理和业务状态流转由 Neolyst 核心系统完成。

### 1.1 核心设计原则

1. **独立 Skills 架构**：每个 Skill 保持单一职责，通过事件和消息解耦
2. **流程可编排**：工作流引擎支持串行、并行、条件分支等执行模式
3. **一致性逻辑下沉到 Supabase**：业务数据一致性、状态流转、关系维护通过 Supabase Skills 接口执行
4. **业务人员可配置**：通过自然语言或 YAML 配置即可新增模板或提取字段

## 2. 系统架构

### 2.1 整体架构图

```
┌──────────────────────────────────────────────────────────────┐
│                      NeoSpace 工作台插件系统                   │
│  ┌──────────────────────────────────────────────────────────┐│
│  │                Agent Skills 智能处理层                     ││
│  │  AnalystMgr │ ReportChecker │ AuditWorkflow │ Approve     ││
│  │  FileHandler │ Translate │ GenerateReport │ Publish │ RQC ││
│  └──────────────────────────────────────────────────────────┘│
│                            │                                  │
│                            ▼                                  │
│  ┌──────────────────────────────────────────────────────────┐│
│  │            Supabase Skills 数据操作层                      ││
│  │   （承载一致性逻辑，服务 draft 保存、校验与提交等操作）      ││
│  └──────────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────┐
│                     Neolyst 核心系统                           │
│  Next.js 应用层（Server Components / Actions / Route Handlers）│
│                            │                                  │
│                            ▼                                  │
│  Supabase 后端（Auth │ Postgres │ RLS │ PostgREST │ Storage） │
└──────────────────────────────────────────────────────────────┘
```

### 2.2 技术栈

| 层面 | 技术 |
|------|------|
| 前端 | Next.js App Router + React + TypeScript |
| 后端 | Supabase（Auth / Postgres / RLS / PostgREST / Storage） |
| 模板引擎 | python-docx-template (Jinja2) |
| 文档解析 | Pandoc (Word ↔ Markdown) |
| 结构化抽取 | LLM + schema.yaml |
| 复杂资产提取 | LibreOffice → PDF → PyMuPDF 高清截图 |
| 发布格式 | libreoffice --headless |

### 2.3 分层职责

| 层 | 职责 |
|----|------|
| Agent Skills | AI 自动化能力（字段检查、文件检查、审批、生成、发布等） |
| Supabase Skills | 与 Neolyst 数据交互的桥梁（模板发布、draft 保存、提交校验、状态更新、文件上传等） |
| Next.js 应用 | 用户交互入口（Server Components / Server Actions / Route Handlers） |
| Supabase 后端 | 底层数据库、认证、RLS、存储 |

## 3. 核心数据模型

完整数据模型见 `docs/DATA_MODEL.md`。以下为概要。

### 3.1 数据实体

| 模块 | 表 | 状态 |
|------|----|------|
| 认证用户 | auth.users | 已上线 |
| 区域 | region | 已上线 |
| 分析师信息 | analyst | 已上线 |
| 行业分类 | sector | 已实现 |
| 公司覆盖 | coverage | 已实现 |
| 覆盖-分析师 | coverage_analyst | 已实现 |
| 报告模板 | template | 已实现 |
| 报告主表 | report | 已实现 |
| 报告版本 | report_version | 已实现 |
| 报告作者 | report_analyst | 已实现 |
| 报告状态历史 | report_status_log | 已实现 |

### 3.2 报告状态机

允许流转：`draft → submitted → published`、`submitted → rejected → draft`

禁止：跨级跳转和逆向回写（如 `published → draft`）

### 3.3 报告字段矩阵

| 字段 | company | sector | company_flash | sector_flash | common |
|------|:-------:|:------:|:-------------:|:------------:|:------:|
| Ticker | ✅ | | ✅ | | |
| Rating | ✅ | | | | |
| Target price | ✅ | | | | |
| Region | | ✅ | | ✅ | ✅ |
| Sector | | ✅ | | ✅ | |
| Report language | ✅ | ✅ | ✅ | ✅ | ✅ |
| Report title | ✅ | ✅ | ✅ | ✅ | ✅ |
| Analyst | ✅ | ✅ | ✅ | ✅ | ✅ |
| Contact Person | ✅ | ✅ | ✅ | ✅ | ✅ |
| Investment thesis | ✅ | ✅ | ✅ | ✅ | ✅ |
| Certificate | ✅ | ✅ | ✅ | ✅ | ✅ |

### 3.4 RLS 矩阵

| 表 | Admin | SA | Analyst |
|----|-------|----|---------|
| region / analyst / sector | R/W | R | R |
| coverage | R/W | R | R + INSERT |
| coverage_analyst | R/W | R | R + INSERT |
| template | R/W | R | R |
| report | 全量 R/W（无 DELETE） | R（submitted/published/rejected） | R/W（仅 owner，draft/submitted） |
| report_version | R + INSERT | R（submitted/published/rejected） | R + INSERT（仅 owner） |
| report_analyst | 全量 R/W | R（submitted/published/rejected） | R/W（仅 owner） |
| report_status_log | R + INSERT | R + INSERT（审批与退回） | R + INSERT（仅 owner submit） |

## 4. Agent Skills 能力详解

### 4.1 Skills 分类

**数据维护**：Analyst Manager — 从 Excel 提取分析师信息，与 Neolyst 比对，确认差异后自动更新

**报告检查**：

| Skill | 功能 |
|-------|------|
| Report Field Checker | 按报告类型验证必填字段完整性 |
| File Completeness Checker | 验证 Word、Model 等文件齐全 |
| File Similarity Checker | 莱文斯坦距离比对文件名，相似度 < 60% 警告 |
| SFC Signature Validator | 从 SFC 官网查询牌照信息，自动填充 |

**审批流程**：

| Skill | 功能 |
|-------|------|
| Coverage Approval | 检查 Coverage 存在性，处理首次覆盖审批 |
| Chief Approval | 处理首席审批 |
| RQC Approval | 判断 RQC 触发（首次覆盖/评级调整/TP 变动 ≥ 30%） |

**内容生成**：

| Skill | 功能 |
|-------|------|
| Report Title Generator | 按规则自动生成标准标题 |
| Report Extractor | 从 Word 提取摘要和正文 |
| Stock Chart Generator | 从市场数据生成股价走势图和 Volume 柱状图 |
| Report Generator | 填充模板生成完整报告 |

**发布流程**：

| Skill | 功能 |
|-------|------|
| Report Submission | 提交前检查（RQC/Coverage/字段），通过后更新状态 |
| Translation | 报告翻译 |
| Auto Auditor | AI 自动审核合规性 |
| Publish Handler | Word → PDF，发送通知邮件，同步 Wind |

### 4.2 报告标题生成规则

| 场景 | 格式 |
|------|------|
| 首次覆盖 | `{公司名} ({Ticker}): 首次覆盖: {标题}` |
| 评级变动，目标价不变 | `{公司名} ({Ticker}): {标题}—{动作}{评级}` |
| 评级+目标价变动 | `{公司名} ({Ticker}): {标题}—{动作}{评级}; {TP动作}{TP变动}%` |
| 仅目标价变动 | `{公司名} ({Ticker}): {标题}—维持{评级}; {TP动作}{TP变动}%` |
| 评级和目标价都不变 | `{公司名} ({Ticker}): {标题}—维持{评级}` |
| 中英文版 | `公司中文简称 ({Ticker}): 中文标题—动作 (English Title — Action)` |

## 5. 业务流程

### 5.1 报告创建流程

```
上传文件 → 字段检查 → 文件检查 → 相似度检查 → SFC 检查
→ Coverage 检查 → 标题生成 → 提交报告 → RQC/首席审批 → 发布
```

### 5.2 模板制作流程

1. 上传标准样本 + schema.yaml
2. 系统自动构建模板并验证
3. 对话式修改提取规则和模板
4. 确认后生效

## 6. 存储架构

### 6.1 模板文件

- Bucket：模板专用
- 路径：以 `template.template_file_path` 和 `template.schema_file_path` 为准（非 report_type 推导）
- 读取：所有已认证用户
- 写入：仅 Admin
- 多个 report_type 可引用同一路径共用模板资产

### 6.2 报告文件

- Bucket：reports 专用
- 目录：`{report_id}/`
- 命名：`{report_id}_{version_no3}_{label}_{ts}.{ext}`
  - version_no3：三位版本号（001、002…）
  - label：report / pdf / model
  - ts：UTC `YYYYMMDDTHHMMSSZ`

### 6.3 报告文件权限

- 读取：owner / Admin / SA（SA 仅 submitted|published|rejected）
- 写入：owner / Admin

## 7. 权限与安全

### 7.1 角色

| 角色 | 权限范围 |
|------|----------|
| Admin | 全部操作（用户/区域/分析师/Coverage/Sector/模板/报告/审批） |
| SA | 审批 submitted 报告；可见 submitted/published/rejected |
| Analyst | 创建/编辑/提交自己的报告；新增 Coverage |

### 7.2 认证

- 会话：SSR cookies（`@supabase/ssr`）
- 鉴权事实源：`getUser()`
- 角色事实源：JWT 角色字段（遵循 DECISIONS.md D-003）
- 路由门禁：proxy.ts（未登录 → /login，无权限 → /403）

## 8. 目录结构

```
neoskills/
├── docs/
│   ├── README.md
│   ├── agent-req.md
│   ├── report-skills.md
│   └── neolyst/
│       ├── ARCHITECTURE.md
│       ├── DATA_MODEL.md
│       └── REQUIREMENTS.md
├── samples/                   # 研究报告示例
└── CLAUDE.md
```

报告文件命名：
- 中文：`公司全称 日期.docx`
- 英文：`Ticker 日期.docx`
- 自动刷新 PDF：`原名_AutoRefresh.pdf`
- 参数提取：`原名_params.json`

## 9. 关键技术实现

### 9.1 模板引擎

python-docx-template (Jinja2) 渲染短文本到 Word 占位符。`{{company_name}}`、`{{rating}}` 等。

重复部分用循环：`{% for analyst in analysts %}{{ analyst.name }}{% endfor %}`

### 9.2 文档格式转换

- Word → Markdown：Pandoc (pypandoc)，剥离格式生成纯净文本
- Markdown → Word：Pandoc + Subdoc 机制，保留层级结构不破坏主模板版式

### 9.3 复杂图表提取

LibreOffice 静默转 PDF → PyMuPDF 解析坐标 → 高清截图裁剪 → 存入 assets/

避免 Word 表格转 HTML/Markdown 的格式崩坏，保证 100% 视觉保真。

### 9.4 文件相似度检测

相似度 = `1 - 莱文斯坦距离 / 最大字符串长度`。阈值 60%。

### 9.5 SFC 牌照验证

从 https://apps.sfc.hk/publicregWeb/searchByName 查询，自动填充。重名时人工确认。

## 10. 附录

### 10.1 Certificate 英文条款

报告提交前必须展示并勾选确认：

1. members of my household and I have not traded any financial interest in the subject company since I started the coverage nor currently hold any financial interest in the subject company (including, without limitation, any securities, option, right, warrant, future, long or short position)
2. I did not receive any compensation from the subject company in the previous 12 months
3. I have not served as an officer, director or employee of the subject company
4. none of my household serve as an officer of the subject company
5. I comply with the Group Compliance Policy with regards to gifts and entertainment in dealing with subject companies and investors
6. this research report contains no material non-public information

### 10.2 RQC 触发条件

- 首次覆盖
- 评级变动
- 目标价变动 ≥ 30%

### 10.3 数据库规范

- 主键：uuid
- 时间：timestamptz，字段名 created_at / updated_at
- 外键：显式声明 ON DELETE
- 唯一性：约束或唯一索引
- 审计：append-only 日志表
- 删除：优先逻辑删除或状态驱动
