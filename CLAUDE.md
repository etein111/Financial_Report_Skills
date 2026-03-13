# CLAUDE.md

本文件为 Claude Code (claude.ai/code) 在此代码库中工作时提供指导。

## 项目概述

NeoSpace 是 Neolyst 研究报告管理平台的 **AI 工作台插件系统**。本代码库包含自动化报告编辑、审核和合规工作流的设计文档、需求和 AI 提示词。

**注意：** 这主要是一个文档/设计代码库，没有可执行的代码库——它包含 AI 驱动自动化任务的规格说明、提示词和示例文件。

## 代码库结构

```text
neoskills/
├── docs/
│   ├── README.md                    # 项目概述和系统架构
│   ├── agent-req.md                 # AI 代理需求和功能
│   └── neolyst/
│       ├── ARCHITECTURE.md          # Neolyst 系统架构 (Next.js + Supabase)
│       ├── DATA_MODEL.md            # 逻辑数据模型和 RLS 矩阵
│       └── REQUIREMENTS.md          # 业务需求和功能规格
└── samples/                          # 研究报告示例 (Word/PDF)
```

## 核心概念

### Neolyst 系统（现有平台）

- **技术栈**：Next.js App Router + React + TypeScript（前端），Supabase（后端）
- **角色**：`admin`（管理员）、`sa`（审批）、`analyst`（分析师）
- **核心实体**：Region（区域）、Analyst（分析师）、Sector（行业）、Coverage（覆盖）、Template（模板）、Report（报告）
- **报告状态流转**：`draft → submitted → published/rejected`

### NeoSpace 工作台插件（本项目）

AI 自动化能力按独立技能组织：

1. **数据维护**：Analyst Manager（Excel → 数据库同步）
2. **报告检查**：字段完整性、文件验证、相似度检查、SFC 署名验证
3. **审批流程**：Coverage 审批、首席审批、RQC（评级变动）触发
4. **内容生成**：标题生成、内容提取、股票图表、报告自动填充
5. **发布流程**：提交处理、翻译、自动审核、PDF 转换、Wind 同步

### 报告类型

- `company` - 公司完整报告（需要 Word + Model 文件）
- `sector` - 行业报告
- `company_flash` / `sector_flash` - 快讯报告
- `common` - 宏观、策略、量化、债券报告

### 各报告类型的必填字段

| 字段 | company | sector | company_flash | sector_flash | common |
|------|:-------:|:------:|:-------------:|:------------:|:------:|
| Ticker | ✓ | | ✓ | | |
| Rating | ✓ | | | | |
| 目标价 | ✓ | | | | |
| Region | | ✓ | | ✓ | ✓ |
| Sector | | ✓ | | ✓ | |
| 报告语言 | ✓ | ✓ | ✓ | ✓ | ✓ |
| 标题 | ✓ | ✓ | ✓ | ✓ | ✓ |
| 分析师 | ✓ | ✓ | ✓ | ✓ | ✓ |
| 联系人 | ✓ | ✓ | ✓ | ✓ | ✓ |
| 投资观点 | ✓ | ✓ | ✓ | ✓ | ✓ |
| Certificate | ✓ | ✓ | ✓ | ✓ | ✓ |

## 使用示例文件

`samples/` 目录包含研究报告示例（Word 和 PDF 格式），用于：

- 模板提取和参数化
- 测试 AI 自动化工作流
- 验证解析和生成逻辑

**示例文件包括：**

- `Bloom Energy Corporation 1231.docx` + 自动刷新的 PDF
- `EN-Vistra Corp20260104.docx` + 自动刷新的 PDF
- `VRT 20260221.docx` + 自动刷新的 PDF
- `西锐飞机首次覆盖报告（中文）提交版.docx` + 自动刷新的 PDF

## PDF 模板提取

PDF 模板提取将成品研究报告转换为可复用模板，包含三个输出：

1. `template.pdf` - 带 `{{占位符}}` 的 PDF
2. `params.json` - 当前报告的参数值
3. `render_rules.md` - 渲染规则（布局、图表、多分析师处理）

**关键占位符：**

- 公司信息：`{{TICKER}}`、`{{COMPANY_NAME}}`、`{{REPORT_DATE}}`
- 评级：`{{RATING_CHANGE}}`、`{{RATING}}`、`{{TARGET_PRICE}}`
- 市场数据：`{{CURRENT_PRICE}}`、`{{MARKET_CAP}}`、`{{SHARES_OUTSTANDING}}`
- 图表：`{{PRICE_CHART}}`、`{{VOLUME_CHART}}`、`{{RECOMMENDATION_CHART}}`
- 分析师：`{{ANALYST_1_NAME}}`、`{{ANALYST_1_SFC}}`、`{{ANALYST_1_EMAIL}}`（最多 8 位）
- 内容：`{{SUMMARY_1}}` 到 `{{SUMMARY_4}}`、`{{BODY}}`

## 数据库架构要点

### 主要数据表

- `region` - 地理区域
- `analyst` - 分析师信息（姓名、邮箱、SFC 执照、区域）
- `sector` - 两级行业分类
- `coverage` - 公司覆盖（股票代码、ISIN、行业归属）
- `coverage_analyst` - 多对多关系（每个 coverage 最多 4 位分析师）
- `template` - Word/Excel 模板（带版本管理）
- `report` - 报告主表（所有者、状态、版本追踪）
- `report_version` - 仅追加的版本历史
- `report_analyst` - 报告作者关系
- `report_status_log` - 仅追加的状态流转日志

### 存储（Supabase Storage）

- 模板：`templates/{template_id}/{version}/...`
- 报告：`reports/{report_id}/{report_id}_{version}_{label}_{timestamp}.{ext}`

### RLS（行级安全）矩阵

关键访问模式：

- **Admin**：大多数表完全读写
- **SA（审批）**：对已提交/已发布/已拒绝的报告只读，可审批/拒绝
- **Analyst**：仅对自己报告（草稿/已提交）读写，对 coverage 可读 + 插入

## 重要业务规则

### 报告标题生成

- **首次覆盖**：`{公司名} ({Ticker}): 首次覆盖: {标题}`
- **评级变动，目标价不变**：`{公司名} ({Ticker}): {标题}—{行动}{评级}`
- **评级 + 目标价变动**：`{公司名} ({Ticker}): {标题}—{行动}{评级}; {TP_行动}{TP_变动}%`
- **仅目标价变动**：`{公司名} ({Ticker}): {标题}—维持{评级}; {TP_行动}{TP_变动}%`

### 文件相似度检查

- 算法：`1 - (莱文斯坦距离 / 最大字符串长度)`
- 阈值：与上一版相比相似度 < 60% 时警告

### SFC 验证

- 分析师在提交报告前必须持有有效的 SFC 执照
- 查询来源：https://apps.sfc.hk/publicregWeb/searchByName

### RQC（研究质量委员会）触发条件

- 首次覆盖
- 评级变动
- 目标价变动 ≥ 30%

## 理解项目的文档阅读顺序

1. `docs/README.md` - 系统架构概述
2. `docs/neolyst/REQUIREMENTS.md` - 业务需求和角色权限
3. `docs/neolyst/DATA_MODEL.md` - 数据模型和 RLS 矩阵
4. `docs/agent-req.md` - AI 自动化需求

## 文件命名规范

- 报告文件遵循模式：`{公司名} {日期}.docx` 或 `{Ticker} {日期}.docx`
- 自动刷新的 PDF：`{原文件名}_AutoRefresh.pdf`

## 在此代码库中工作时

- **了解需求**：先阅读 `docs/neolyst/REQUIREMENTS.md`
- **数据库查询**：参考 `docs/neolyst/DATA_MODEL.md` 了解表结构
- **添加 AI 功能**：查看 `docs/agent-req.md` 了解技能分解
- **示例测试**：使用 `samples/` 目录中的文件进行验证
