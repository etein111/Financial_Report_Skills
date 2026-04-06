# NeoSpace 工作台插件系统架构与技术实现文档

## 文档概述

本文档全面阐述 NeoSpace 工作台插件系统的架构设计、技术实现方案、完整业务流程以及数据模型定义。NeoSpace 是 Neolyst 研究报告管理平台的 AI 智能工作台，通过独立可编排的 Agent Skills 实现报告的自动化编辑、审核与发布流程。本文档面向架构师、开发工程师、产品经理以及业务分析师，旨在提供从系统概览到实现细节的完整技术参考。

---

## 第一部分：项目概述与定位

### 1.1 项目背景

NeoSpace 是 Neolyst 研究报告管理系统的 AI 工作台插件系统。Neolyst 本身是一个成熟的研究报告管理平台，提供用户认证、分析师信息管理、公司覆盖（Coverage）管理、报告模板管理以及完整的报告审批工作流。然而，在日常使用过程中，分析师和运营人员面临大量重复性工作，包括报告格式排版、字段提取、合规检查、审批流转等，这些工作占据了分析师大量精力，影响了报告生产的效率。

NeoSpace 的核心价值在于通过 AI 自动化技术将这些重复性工作智能化，将分析师从繁琐的格式排版和数据录入工作中解放出来，使其能够专注于报告内容的创作和质量把控。系统设计遵循“独立 Skills 可编排”的核心理念，每个自动化能力都被封装为独立的 Agent Skill，彼此解耦，通过可视化的工作流编排进行触发和串联，使得业务人员可以根据实际需求灵活调整自动化流程。

### 1.2 系统定位

NeoSpace 在整个技术生态中处于 Neolyst 核心系统的上层，作为插件系统存在。它不替代 Neolyst 的核心功能，而是增强和扩展 Neolyst 的能力边界。具体而言，NeoSpace 负责处理报告的智能化生成、自动化审核和合规检查，而数据持久化、权限管理和最终的业务状态流转仍然由 Neolyst 核心系统完成。这种分层设计确保了系统的稳定性和可维护性，同时充分发挥了 AI 自动化带来的效率提升。

从技术架构角度看，NeoSpace 是一个基于大语言模型（LLM）的智能自动化平台，它通过 Agent Skills 的形式调用各种 AI 能力来处理报告相关的任务。每个 Skill 都是一个相对独立的 AI Agent，拥有特定的职责和能力范围，通过标准化的接口进行通信和协作。这种架构设计既保证了系统的灵活性，又便于单独测试和维护每个 Skill。

### 1.3 核心设计原则

NeoSpace 的设计遵循以下核心原则，这些原则贯穿于系统的各个层面，指导着技术决策和实现方式。

第一个原则是**独立 Skills 架构**。系统将各种自动化逻辑拆分为独立的 Agent Skills，每个 Skill 保持单一职责，彼此相对独立。这种设计使得单个 Skill 的修改和升级不会影响其他 Skills 的正常运行，同时也便于针对特定问题进行排查和修复。Skills 之间通过事件和消息进行解耦，而不是直接的函数调用，这大大降低了系统各部分之间的耦合度。

第二个原则是**流程可编排**。通过工作流引擎将各个 Skills 进行灵活编排，实现复杂的自动化流程。编排配置可以被修改和定制，以适应不同业务场景的需求。工作流引擎支持串行、并行、条件分支等多种执行模式，能够满足大多数业务流程的需求。

第三个原则是**审核后更新**。NeoSpace 作为智能处理层，负责报告的自动化处理和审核检查，但在数据最终写入时，通过调用 Supabase Skills 来更新 Neolyst 系统的数据库。这种设计确保了数据一致性，所有业务数据仍然由 Neolyst 核心系统管理，NeoSpace 只负责处理逻辑。

第四个原则是**业务人员可配置**。系统的设计目标是让业务人员（如分析师和排版助理）能够自行修改提取规则和维护排版模板，而无需研发人员介入。通过自然语言交互或修改 YAML 配置文件，业务人员即可新增报告模板或提取字段，实现业务主导的自动化流程。

---

## 第二部分：系统架构设计

### 2.1 整体架构图

NeoSpace 系统采用分层架构设计，从上到下分为四个主要层次：Agent Skills 层、Supabase Skills 层、Neolyst 核心应用层以及基础设施层。每个层次都有明确的职责边界和接口定义，下面将详细说明各层的功能和交互关系。

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           NeoSpace 工作台插件系统                             │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                      Agent Skills 智能处理层                              ││
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐    ││
│  │  │ Analyst  │ │  Report  │ │  Audit   │ │ Approve  │ │  File   │    ││
│  │  │ Manager  │ │  Checker │ │ Workflow │ │ Handler  │ │Handler  │    ││
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘    ││
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐    ││
│  │  │ Translate│ │ Generate │ │ Publish  │ │   RQC    │ │  Stock  │    ││
│  │  │  Skill   │ │  Report  │ │ Handler  │ │ Handler  │ │  List   │    ││
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘    ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                    │                                         │
│                                    ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                   Supabase Skills 数据操作层                             ││
│  │              （审核通过后调用，更新 Neolyst 数据库）                     ││
│  └─────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          Neolyst 核心系统                                    │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                    Next.js 应用层                                        ││
│  │              Server Components / Server Actions / Route Handlers         ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                    │                                         │
│                                    ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                    Supabase 后端服务层                                   ││
│  │     Auth 认证 │ Postgres 数据库 │ RLS 行级安全 │ PostgREST │ Storage   ││
│  └─────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 技术栈详解

NeoSpace 工作台插件系统的技术栈分为两个主要部分：Neolyst 核心系统技术栈和 NeoSpace 智能处理层技术栈。

**Neolyst 核心系统技术栈**是整个平台的基础，采用了业界成熟的技术方案。前端方面使用 Next.js App Router 架构，结合 React 和 TypeScript 构建了现代化的 Web 应用。Next.js 的 Server Components 和 Server Actions 提供了优秀的服务端渲染能力和便捷的服务器端数据处理能力。认证方面采用 Supabase Auth 进行用户身份管理，数据库使用 Supabase Postgres，并通过 RLS（Row Level Security）实现细粒度的数据访问控制。文件存储使用 Supabase Storage，API 层通过 PostgREST 提供便捷的 RESTful 接口。

**NeoSpace 智能处理层技术栈**专注于 AI 自动化能力的实现。模板引擎采用 python-docx-template（基于 Jinja2），负责将短文本数据渲染并填入 Word 模板。文档格式解析采用 Pandoc 引擎，实现 Word 与 Markdown 之间的双向转换。结构化抽取引擎基于大语言模型（LLM）的逻辑推理能力，结合 schema.yaml 的约束进行精准的数据抽取。复杂资产提取采用“隐藏转 PDF + 高清裁图”方案，利用 PyMuPDF 库进行坐标识别和高清截图。最终发布格式转换采用 libreoffice 的 headless 模式进行 Word 到 PDF 的转换。

### 2.3 分层架构详解

**Agent Skills 智能处理层**是 NeoSpace 的核心，负责实现各种自动化 AI 能力。该层包含多个独立的 Skills，每个 Skill 针对特定的业务功能。Analyst Manager 负责从 Excel 提取分析师信息并与 Neolyst 数据进行比对。Report Checker 负责检查报告字段完整性和文件齐全性。Audit Workflow 处理报告的自动化审核流程。Approve Handler 处理各种审批场景，包括 Coverage 审批、首席审批和 RQC 审批。File Handler 管理文件上传、下载和格式转换。Translate Skill 提供报告翻译能力。Generate Report Skill 负责自动生成标准格式的报告。Publish Handler 处理报告的发布流程，包括 Word 转 PDF 和通知邮件发送。

**Supabase Skills 数据操作层**是 NeoSpace 与 Neolyst 核心系统交互的桥梁。所有对 Neolyst 数据库的修改都通过该层进行，确保数据操作的一致性和安全性。该层封装了常见的数据操作，包括报告状态更新、分析师信息同步、Coverage 创建与更新、审批日志记录以及文件存储上传等。

**Next.js 应用层**是用户交互的前端入口，提供 Web 界面供用户操作。该层使用 Server Components 进行服务端渲染，优化首屏加载性能。Server Actions 用于处理表单提交和数据更新，Route Handlers 用于处理 API 请求。

**Supabase 后端服务层**提供底层的数据库和存储服务。Auth 模块管理用户认证和会话。Postgres 存储所有业务数据，并提供强大的查询能力。RLS 实现数据级别的安全控制，确保用户只能访问授权的数据。PostgREST 自动生成 RESTful API，简化数据访问。Storage 管理文件上传和下载。

---

## 第三部分：核心数据模型

### 3.1 数据实体总览

NeoSpace 和 Neolyst 系统涉及多个核心数据实体，这些实体之间通过外键关系相互关联，形成完整的数据模型。以下是各主要数据表的状态和说明。

| 模块 | 表名 | 状态 | 说明 |
|------|------|------|------|
| 认证用户 | auth.users | 已上线 | Supabase 托管的认证用户表 |
| 区域 | region | 已上线 | 地理区域信息 |
| 分析师信息 | analyst | 已上线 | 分析师的详细业务信息 |
| 行业分类 | sector | 已实现 | 两级行业分类结构 |
| 公司覆盖 | coverage | 已实现 | 公司覆盖信息和元数据 |
| 覆盖分析师关系 | coverage_analyst | 已实现 | Coverage 与分析师的多对多关系 |
| 报告模板 | template | 已实现 | Word 模板管理 |
| 报告主表 | report | 已实现 | 报告的核心数据 |
| 报告版本 | report_version | 已实现 | 报告内容的版本历史 |
| 报告作者关系 | report_analyst | 已实现 | 报告与作者的关系 |
| 报告状态历史 | report_status_log | 已实现 | 报告状态流转日志 |

### 3.2 核心表结构详解

**region 表**存储地理区域信息，是报告类型为 sector、sector_flash、flash、macro、strategy、quantitative、bond 的必填字段。表结构包含 uuid 类型的主键 id、唯一且非空的 name 和 code 字段，以及审计字段 created_at 和 updated_at。初始基线数据应包含 China、Hong Kong、Japan、Taiwan、Korea、India、Macau、US 等主要市场区域，并预留扩展空间。

**analyst 表**存储分析师的详细业务信息，与 auth.users 表解耦。关键字段包括 uuid 类型主键 id、full_name（非空文本）、chinese_name（中文名，可空）、citext 类型的唯一邮箱 email、关联 region 的外键 region_id、SFC 执照编号 sfc、是否活跃标志 is_active，以及审计字段。分析师信息与认证账号保持分离，不自动创建或删除账号，这种设计允许灵活的人员管理。

**sector 表**实现两级行业分类结构。关键字段包括 uuid 主键 id、level 字段标识层级（1 或 2）、parent_id 外键实现自关联、name_en/name_cn/wind_name 多语言名称、is_active 活跃标志以及审计字段。约束规则确保只允许两级结构，一级节点无父节点，二级节点必须挂载在一级节点下，并禁止循环层级。

**coverage 表**存储公司覆盖信息，是 company 和 company_flash 类型报告的核心关联表。关键字段包括 uuid 主键 id、ticker（股票代码，唯一）、english_full_name（公司英文全称，非空）、chinese_short_name（中文简称）、sector_id 外键关联行业、isin（国际证券识别码，唯一）、country_of_domicile（注册国家）、reporting_currency（报告货币）、ads_conversion_factor（ADS 转换因子）、is_duplicate/is_active 状态标志、approved_by/approved_at 审批信息以及审计字段。ticker 和 isin 都要求唯一性，并采用标准化比较。

**coverage_analyst 表**实现 Coverage 与分析师的多对多关系，支持每个 Coverage 最多 8 位分析师。关键字段包括 uuid 主键 id、coverage_id 外键、analyst_id 外键、role 角色字段（1 到 8）、sort_order 排序字段以及审计字段。约束条件确保同一 Coverage 中同一分析师只出现一次，同一 Coverage 中每个排序位置唯一。新建 Coverage 时，初始 `coverage_analyst` 与当前报告分析师列表保持一致；对已有 Coverage，单篇报告提交不自动改写其既有 `coverage_analyst`，报告作者关系独立记录在 `report_analyst` 中。

**template 表**管理生成报告所使用的模板资产。关键字段包括 uuid 主键 id、name 模板名称、report_type 模板类型、language 模板语言、template_file_path Word 模板存储路径、schema_file_path 对应 `schema.yaml` 存储路径、uploaded_by 上传者外键以及审计字段。`report_type` 字段保存模板类型，也就是 `template_type`，与 draft 和提交阶段使用的研报类型 `report_type` 分离。`template_file_path` 与 `schema_file_path` 共同定义一套完整模板资产，其中 `schema.yaml` 用于描述需要抽取的字段，以及这些字段在分析师原始报告中的大致位置和特征。系统初始化应至少包含 company、sector、company_flash、sector_flash、common 五种模板类型在中英文维度上的模板资产。

**report 表**是报告管理的核心表，存储报告的主要信息。关键字段包括 uuid 主键 id、owner_user_id 所有者外键（非空且不可转移）、title 标题（非空）、report_type 报告类型（非空）、ticker 股票代码、rating 评级、target_price 目标价、region_id/sector_id 关联外键、report_language 报告语言（zh 或 en）、contact_person_id 联系人外键、investment_thesis 投资观点、certificate_confirmed 证书确认（布尔值，默认 false）、status 状态（draft/submitted/published/rejected）、current_version_no 当前版本号、published_by/published_at 发布快照以及审计字段。约束规则规定报告不做物理删除，submitted 状态下所有者仍可编辑，仅在 submitted 转换为 published 时更新发布快照。

**report_version 表**记录报告内容的版本历史，采用追加写入模式。关键字段包括 uuid 主键 id、report_id 报告外键、version_no 版本号（按报告递增）、snapshot_json JSON 格式的字段快照、word_file_path/model_file_path 文件路径、changed_by 修改人外键以及 changed_at 修改时间。约束条件确保报告和版本号的组合唯一，且采用追加模式禁止更新和删除。

**report_analyst 表**维护报告与分析师的作者关系。关键字段包括 uuid 主键 id、report_id 报告外键、analyst_id 分析师外键、role 角色、sort_order 排序以及审计字段。该表记录单篇报告的作者列表，与 `coverage_analyst` 的长期 Coverage 团队关系分离。所有者可维护自己报告的作者关系，管理员可全局维护。

**report_status_log 表**记录报告状态流转历史，采用追加写入模式。关键字段包括 uuid 主键 id、report_id 报告外键、from_status 源状态、to_status 目标状态、action_by 操作人外键、action_by_name 操作人名称、action_at 操作时间、reason 拒绝原因（reject 时必填）以及 version_no 操作发生时的版本号。约束条件确保记录完整的状态流转链，禁止更新和删除。

### 3.3 报告状态机

报告的状态流转遵循严格的状态机规则，确保业务流程的规范性。允许的流转路径包括：从 draft 可以流转到 submitted，表示报告提交审核；从 submitted 可以流转到 published，表示审批通过发布；从 submitted 可以流转到 rejected，表示审批拒绝；从 rejected 可以流转到 draft，表示被拒绝后重新修改。

禁止的流转包括任意跨级跳转和逆向非法回写，例如 published 状态不能直接回到 draft 状态。这种设计确保了报告状态流转的可追溯性和业务合规性。

---

## 第四部分：Agent Skills 能力详解

### 4.1 Skills 分类概览

NeoSpace 系统将自动化能力划分为五大类别，每个类别包含多个具体的 Agent Skills。这些 Skills 协同工作，覆盖了从数据维护到报告发布的完整业务流程。

**数据维护类 Skills** 负责处理分析师信息的管理和同步。Analyst Manager 是该类别的核心 Skill，功能是从 Excel 文件提取分析师信息，与 Neolyst 系统中的数据进行智能比对，在确认差异后自动更新数据库。这个 Skill 大大简化了分析师信息维护的工作量，避免了手动录入的错误。

**报告检查类 Skills** 负责验证报告的完整性和合规性。Report Field Checker 检查研报类型所需的字段是否完整，根据研报类型（company、sector、flash、company_flash、sector_flash、macro、strategy、quantitative、bond）验证必填字段。File Completeness Checker 检查 Word 文件、Model 文件、审批截图等必要文件是否齐全。File Similarity Checker 使用莱文斯坦距离算法计算文件相似度，与上一版本的最新文件进行比对，相似度低于 60% 时发出警告，防止提交错误版本。SFC Signature Validator 核对分析师与 SFC 署名，从 SFC 官方网站查询牌照信息并自动填充到报告中。

**审批流程类 Skills** 负责处理各种审批场景。Coverage Approval Handler 检查 Coverage 是否存在，处理首次覆盖的审批邮件。Chief Approval Handler 处理报告提交前的首席审批流程。RQC Approval Handler 判断是否触发 RQC（研究质量委员会）审批，触发条件包括首次覆盖、评级调整、目标价变动超过 30%，并处理主管确认邮件。

**内容生成类 Skills** 负责自动生成报告内容和元素。Report Title Generator 根据报告类型和评级变动自动生成标准格式的标题，支持首次覆盖、评级变动、目标价变动等多种场景。Report Extractor 从 Word 文档中智能提取报告摘要和正文内容。Stock Chart Generator 从市场数据库获取股票代码数据，生成股价走势图和成交量柱状图。Report Generator 自动填充报告模板内容，整合各种数据生成完整的报告文档。

**发布流程类 Skills** 负责报告的最终发布和分发。Report Submission Handler 执行提交前的各项检查，包括 RQC 是否通过、Coverage 是否存在等，检查通过后自动更新报告状态。Translation Handler 支持报告翻译版本的管理和生成。Auto Auditor 使用 AI 技术自动审核报告的合规性。Publish Handler 负责将 Word 转换为 PDF，发送发布通知邮件，并同步到 Wind 平台。

### 4.2 报告字段矩阵

不同类型的报告在提交时有不同的必填字段要求，以下矩阵详细说明了各类报告的字段要求。

| 字段名称 | company | sector | flash | company_flash | sector_flash | macro | strategy | quantitative | bond |
|----------|:-------:|:------:|:-----:|:-------------:|:------------:|:-----:|:--------:|:------------:|:----:|
| Ticker | ✅ | | | ✅ | | | | | |
| Rating | ✅ | | | | | | | | |
| Target price | ✅ | | | | | | | | |
| Region | | ✅ | ✅ | | ✅ | ✅ | ✅ | ✅ | ✅ |
| Sector | | ✅ | | | ✅ | | | | |
| Report language | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Report title | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Analyst | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Contact Person | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Investment thesis | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Certificate | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

对于 company 和 company_flash 类型，必须提供合法的 ticker；其中 company 类型额外需要提供 rating 和 target_price。对于 sector 和 sector_flash 类型，必须提供合法的 region 和 sector。对于 flash、macro、strategy、quantitative、bond 类型，必须提供合法的 region。

### 4.3 报告标题生成规则

报告标题的生成遵循严格的格式规则，确保标题清晰表达报告的核心内容。以下是各类场景的标题生成规则。

首次覆盖场景的标题格式为：公司中文全称（股票代码）：首次覆盖：报告标题。例如：Vertiv (VRT US)：首次覆盖：报告标题xxxx。

评级调整但目标价未变动的场景，标题格式为：公司全称（股票代码）：报告标题——上调至优于大市。例如：Vertiv (VRT US)：报告标题xxxx——上调至优于大市。

评级和目标价同时调整的场景，标题格式为：公司全称（股票代码）：报告标题——上调至优于大市；上调目标价24%。例如：Vertiv (VRT US)：报告标题xxxx——上调至优于大市；上调目标价24%。

仅目标价调整而评级不变的场景，标题格式为：公司全称（股票代码）：报告标题——维持优于大市；上调目标价24%。例如：Vertiv (VRT US)：报告标题xxxx——维持优于大市；上调目标价24%。

评级和目标价都未调整的场景，标题格式为：公司全称（股票代码）：报告标题——维持优于大市。

对于同时有中英文版本的报告，标题格式需要同时包含中文和英文：公司中文简称（股票代码）：报告中文标题——上调至优于大市；上调目标价24%（Vertiv：英文标题——Maintain OP & Raise TP by 24%）。

---

## 第五部分：业务流程与工作流

### 5.1 报告创建完整流程

报告创建是 NeoSpace 系统的核心业务流程，涉及多个 Skills 的协同工作。以下是完整的流程描述。

**第一步：文件上传**。分析师上传报告的 Word 草稿文件。系统接收文件后，进行初步的文件格式验证，确保上传的是有效的 Word 文档。

**第二步：字段检查**。Report Field Checker 自动从 Word 文档中提取各项字段，包括 Ticker、Rating、Target price、Region、Sector、Report language、Report title、Analyst、Contact Person、Investment thesis 等。系统根据报告类型检查必填字段是否完整，如果有缺失字段，系统会提示分析师补充。

**第三步：文件检查**。File Completeness Checker 验证必要文件是否齐全。所有类型的报告都必须有 Word 文件，company 类型的报告还必须提供 Model 文件。如果文件不齐全，系统会阻止后续流程并提示补充。

**第四步：相似度检查**。File Similarity Checker 将当前文件与上一版本的最新文件进行相似度比对。使用莱文斯坦距离算法计算相似度，如果相似度低于 60%，系统会发出警告，提示可能是提交了错误版本。

**第五步：内容提取**。Report Extractor 从 Word 文档中提取报告摘要和正文内容，将提取的内容进行结构化处理，存储到系统中。

**第六步：SFC 检查**。SFC Signature Validator 核对分析师与 SFC 署名，从 SFC 官方网站查询分析师的 SFC 执照信息。如果分析师没有有效的 SFC 执照，系统会阻止提交，确保提交的报告符合监管要求。

**第七步：Coverage 检查**。Coverage Approval Handler 检查报告的 Coverage 是否已经在系统中存在。如果不存在，系统会提示在 Neolyst 中添加 Coverage 信息。

**第八步：标题生成**。Report Title Generator 根据报告类型和评级变动自动生成标准格式的标题。如果分析师不满意自动生成的标题，也可以手动输入自定义标题。

**第九步：提交报告**。Report Submission Handler 执行提交前的最终检查，包括 RQC 是否已经通过、首席是否已经审批、Coverage 是否存在等。所有检查通过后，系统自动在 Neolyst 中将报告状态设置为 submitted。

**第十步：审批流程**。报告进入审批流程后，根据不同情况触发不同的审批路径。RQC Approval Handler 判断是否需要 RQC 审批，Chief Approval Handler 处理首席审批，审批通过后进入发布阶段。

**第十一步：审核发布**。Auto Auditor 进行 AI 自动审核，验证报告的合规性。审核通过后，Publish Handler 将 Word 转换为 PDF，发送发布通知邮件，并同步到 Wind 平台。

### 5.2 工作流编排架构

NeoSpace 系统的工作流编排采用可视化配置的方式，允许业务人员灵活定义自动化流程的执行顺序和条件分支。

```
报告创建流程图:

┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  上传    │───▶│ 字段检查 │───▶│ 文件检查 │───▶│ 相似度   │
│  文件    │    │          │    │          │    │  检查    │
└──────────┘    └──────────┘    └──────────┘    └──────────┘
                                                      │
                                                      ▼
                 ┌──────────┐    ┌──────────┐    ┌──────────┐
                 │  生成    │◀───│ Coverage │◀───│  SFC     │◀──┐
                 │  标题    │    │  检查    │    │  检查    │   │
                 └──────────┘    └──────────┘    └──────────┘   │
                      │                                         │
                      ▼                                         │
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐   │
│  发布    │◀───│  首席    │◀───│  RQC     │◀───│  提交    │───┘
│  报告    │    │  审批    │    │  审批    │    │  报告    │
└──────────┘    └──────────┘    └──────────┘    └──────────┘
```

工作流引擎支持多种执行模式。串行执行是最基本的模式，Skills 按照配置的顺序依次执行，一个完成后才触发下一个。并行执行允许多个 Skills 同时运行，提高处理效率，适用于彼此独立的 Skills。条件分支根据特定条件选择不同的执行路径，例如根据报告类型选择不同的处理流程。循环执行支持对批量数据进行重复处理，适用于需要处理多个文件的场景。

### 5.3 模板制作与维护流程

NeoSpace 系统提供了便捷的模板制作和维护功能，允许业务人员独立完成模板的创建和更新，无需研发人员介入。

**步骤一：上传标准样本**。用户提供一份排版标准的历史报告 Word 文件以及对应的要素清单（elements.yaml），上传至系统并输入指令，例如“将其设为宏观报告模板”。

**步骤二：系统自动构建与验证**。系统自动解析 Word 文档，识别文档结构和占位符位置，将动态内容替换为占位符。验证阶段会基于原要素重新生成报告并与原文件进行比对，验证无差异后提示创建成功。

**步骤三：对话式修改提取规则**。当业务需要新增字段时，业务人员无需手动修改代码，直接在对话框中告诉 AI，例如“以后提取宏观报告时，增加一个‘风险提示’字段”。系统收到指令后会执行两步：自动更新提取规则文件（schema.yaml），然后提示用户下载当前的排版模板，在希望显示风险提示的位置输入占位符 {{risk_warning}}，将修改后的 Word 传回系统。

**步骤四：模板排版生效**。业务人员将带有新占位符或调整过格式的模板 Word 重新上传，系统自动更新覆盖。

---

## 第六部分：存储架构与文件规范

### 6.1 存储模型

NeoSpace 系统使用 Supabase Storage 进行文件存储，主要分为两个存储桶：模板文件存储桶和报告文件存储桶。

**模板文件存储**采用独立的模板专用 bucket。存储路径遵循规范：`templates/{template_type}/{language}/template.docx` 与 `templates/{template_type}/{language}/schema.yaml`。读取权限方面，所有已认证用户都可以读取模板文件（受路径约束）。写入权限方面，仅管理员可以上传、替换和删除模板文件。

**报告文件存储**采用报告专用 bucket。存储路径遵循规范：`reports/{report_id}/`，其中 report_id 是报告的唯一标识。文件名遵循固定格式：`{report_id}_{version_no3}_{label}_{ts}.{ext}`。其中 version_no3 是三位版本号（如 001、002），label 是文件标签（report 表示报告文件，model 表示模型文件），ts 是 UTC 秒级时间戳（格式为 YYYYMMDDTHHMMSSZ），ext 是文件扩展名。

文件权限控制方面，读取权限归报告所有者、管理员和审批人员（SA）所有，但 SA 只能访问 submitted/published/rejected 状态范围的报告。写入权限归报告所有者和管理员所有。

### 6.2 数据同步规范

NeoSpace 作为智能处理层，在完成自动化处理后需要将结果同步回 Neolyst 核心系统。数据同步遵循以下规范。

**同步触发时机**：所有数据修改操作都在审核通过后执行。NeoSpace 不直接修改 Neolyst 数据库，而是通过 Supabase Skills 调用进行数据更新。

**同步数据范围**：报告状态更新（draft → submitted → published/rejected）、分析师信息同步（Analyst Manager 处理后）、Coverage 创建与更新（首次覆盖审批通过后）、审批日志记录（状态流转时）、文件存储上传（报告文件上传到 Storage）。

**同步失败处理**：如果同步失败，系统会保留处理结果并记录错误日志，便于后续重试和问题排查。

---

## 第七部分：权限与安全

### 7.1 角色体系

Neolyst 和 NeoSpace 系统采用基于角色的访问控制（RBAC），定义三种核心角色。

**admin（管理员）**拥有系统最高权限，可以执行所有操作，包括用户管理、区域管理、分析师信息管理、Coverage 管理、Sector 管理、模板管理、报告管理以及审批操作。

**sa（审批角色）**主要负责审批工作，可以查看和审批 submitted 状态的报告，执行审批通过、拒绝和退回操作。SA 角色的可见范围限于 submitted/published/rejected 状态的报告，不可访问他人的 draft 报告。

**analyst（分析师）**是报告的主要创建者和使用者，可以创建和编辑自己的报告、提交报告供审批、查看自己报告的状态历史。Analyst 可以新增 Coverage，但编辑和删除 Coverage 需要管理员权限。

### 7.2 RLS 矩阵

Row Level Security（RLS）提供了数据库级别的数据访问控制，确保用户只能访问授权的数据。以下是各表的 RLS 权限矩阵。

| 表名 | Admin | SA | Analyst |
|------|-------|----|--------|
| region | 读/写 | 读 | 读 |
| analyst | 读/写 | 读 | 读 |
| sector | 读/写 | 读 | 读 |
| coverage | 读/写 | 读 | 读 + 插入 |
| coverage_analyst | 读/写 | 读 | 读 + 插入 |
| template | 读/写 | 读 | 读 |
| report | 全量读/写（无删除） | 读（仅 submitted/published/rejected） | 读/写（仅 owner；状态限 draft/submitted） |
| report_version | 读 + 插入 | 读（仅 submitted/published/rejected） | 读 + 插入（仅 owner） |
| report_analyst | 全量读/写 | 读（仅 submitted/published/rejected） | 读/写（仅 owner） |
| report_status_log | 读 + 插入 | 读 + 插入（审批与退回） | 读 + 插入（仅 owner 执行 submit） |

### 7.3 认证与会话

系统使用 Supabase Auth 进行用户认证，认证后的会话信息通过 SSR cookies 存储在客户端。服务端鉴权的事实来源是 getUser() 函数返回的用户信息。角色信息遵循统一的数据决策规则，来源于 JWT 角色字段。

路由门禁通过 proxy.ts 实现，未登录用户会被拦截并跳转到登录页面，无权限访问管理页面的用户会跳转到 403 错误页面。

---

## 第八部分：目录结构与文件规范

### 8.1 项目目录结构

```
neoskills/
├── docs/                                    # 文档目录
│   ├── README.md                            # 项目概述和系统架构
│   ├── agent-req.md                         # AI 代理需求和功能规格
│   ├── report-skills.md                     # 报告技能需求与设计文档
│   └── neolyst/                             # Neolyst 系统文档
│       ├── ARCHITECTURE.md                  # 系统架构设计
│       ├── DATA_MODEL.md                    # 数据模型定义
│       └── REQUIREMENTS.md                  # 业务需求规格
├── samples/                                 # 研究报告示例
│   ├── Bloom Energy Corporation 1231.docx  # 示例报告
│   ├── Bloom Energy Corporation 1231_AutoRefresh.pdf
│   ├── VRT 20260221.docx
│   ├── VRT+20260221_AutoRefresh.pdf
│   ├── EN-Vistra Corp20260104.docx
│   ├── EN-Vistra Corp20260104_params.json
│   ├── EN-Vistra+Corp20260104_AutoRefresh.pdf
│   ├── 西锐飞机首次覆盖报告（中文）提交版.docx
│   ├── 西锐飞机首次覆盖报告（中文）提交版 param.json
│   └── 西锐飞机首次覆盖报告（中文）提交版_AutoRefresh.pdf
└── CLAUDE.md                                # AI 辅助开发指南
```

### 8.2 报告文件命名规范

报告文件遵循统一的命名规范，便于管理和识别。

中文报告命名格式：公司全称 日期.docx，例如：西锐飞机首次覆盖报告（中文）提交版.docx。

英文报告命名格式：Ticker 日期.docx，例如：VRT 20260221.docx。

自动刷新生成的 PDF 文件在原文件名后添加 _AutoRefresh.pdf 后缀，例如：VRT+20260221_AutoRefresh.pdf。

参数提取文件使用 _params.json 后缀，例如：EN-Vistra Corp20260104_params.json。

---

## 第九部分：关键技术实现

### 9.1 模板引擎实现

NeoSpace 系统采用 python-docx-template（基于 Jinja2）作为模板引擎，实现将业务数据填入 Word 模板的功能。短文本数据（如标题、日期、评级等）通过 Jinja2 的变量替换机制直接填入模板中的占位符。占位符使用双花括号语法，例如 {{company_name}}、{{rating}}、{{target_price}} 等。

对于报告中重复出现的部分（如分析师信息），可以使用 Jin2 的循环语法批量渲染。例如：

```
{% for analyst in analysts %}
{{ analyst.name }} - {{ analyst.sfc_code }}
{% endfor %}
```

### 9.2 文档格式转换

Word 到 Markdown 的转换采用 Pandoc 引擎，通过 Python 的 pypandoc 库调用。转换过程中，Pandoc 会剥离 Word 文档中的格式样式，生成纯净的 Markdown 文本，便于后续的数据提取和处理。

Markdown 到 Word 的转换同样使用 Pandoc。为了保持主模板的版式不被破坏，系统采用 Subdoc（子文档）机制：先将 Markdown 转换为一个临时的标准 Word 文档，然后利用 python-docx-template 的 Subdoc 功能将该临时文档整体替换主模板中的正文占位符。这种方式能够 100% 继承 Markdown 的层级结构，同时不破坏主模板的设计。

### 9.3 复杂图表提取

对于 Word 草稿中的复杂图表和财务模型表格（如含有特定底色、跨行跨列合并的表格），系统采用“隐藏转 PDF + 高清裁图”方案进行处理。

第一步，后台静默调用 LibreOffice 将原始 Word 草稿转换为高质量的 PDF 文件。第二步，利用 Python 的 PyMuPDF（fitz）库解析 PDF 文件，识别出表格或图表所在的精确页面与物理坐标。第三步，直接从 PDF 文件对应坐标处进行高清截图裁剪，存入资源目录。这种方案从根本上避免了 Word 表格转 HTML 或 Markdown 时常见的格式崩坏问题，确保格式、边框与底色 100% 视觉保真。

### 9.4 文件相似度检测

文件相似度检测使用莱文斯坦距离（Levenshtein Distance）算法。算法公式为：相似度 = 1 - (莱文斯坦距离 / 最大字符串长度)。当相似度低于 60% 时，系统会发出警告，提示可能是提交了错误的文件版本。

### 9.5 SFC 牌照验证

SFC 牌照验证通过访问香港证监会（SFC）的公开查询网站（https://apps.sfc.hk/publicregWeb/searchByName）获取分析师的 SFC 执照信息。系统自动填充查询结果到报告的分析师信息中。如果遇到重名等特殊情况，系统会与相关人员沟通确认。

---

## 第十部分：附录

### 10.1 Certificate 英文条款原文

在报告提交前，Certificate 确认页面必须展示以下英文条款原文：

1. members of my household and I have not traded any financial interest in the subject company since I started the coverage nor currently hold any financial interest in the subject company (including, without limitation, any securities, option, right, warrant, future, long or short position)

2. I did not receive any compensation from the subject company in the previous 12 months

3. I have not served as an officer, director or employee of the subject company

4. none of my household serve as an officer of the subject company

5. I comply with the Group Compliance Policy with regards to gifts and entertainment in dealing with subject companies and investors

6. this research report contains no material non-public information

用户必须勾选确认上述所有条款，才能提交报告。

### 10.2 RQC 触发条件

RQC（研究质量委员会）审批在以下三种情况下自动触发：首次覆盖报告、评级发生变动、目标价变动幅度达到或超过 30%。系统会自动判断是否需要触发 RQC 审批，并将报告分配给相应的审批人。

### 10.3 数据库规范

主键默认使用 uuid 类型。时间字段统一使用 timestamptz 类型，字段名为 created_at 和 updated_at。外键必须显式声明 ON DELETE 语义，包括 set null、cascade、restrict 等。唯一性通过唯一约束或唯一索引在数据库层保证。审计采用 append-only 日志表，不允许 UPDATE 和 DELETE 操作。删除策略优先使用逻辑删除或状态驱动。

### 10.4 待完善功能

根据当前规划，以下功能需要进一步细化需求和实现：StockList 检查规则的详细说明、文件相似度阈值与比对规则的细化、自动翻译的语言策略、自动审核的 AI 判断规则、发布邮件的文案模板。

---

## 文档版本

| 版本 | 日期 | 修改内容 | 作者 |
|------|------|----------|------|
| 1.0 | 2026-03-16 | 初始版本 | NeoSpace Team |

---

*本文档为 NeoSpace 工作台插件系统的完整架构和技术实现文档，包含系统设计、数据模型、业务流程、权限控制等各个方面的详细说明。*
