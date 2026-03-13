# NeoSpace 工作台插件系统

## 项目概述

NeoSpace 是 Neolyst 研究报告管理系统的 **AI 工作台插件**，通过一组符合标准的 Skills 实现报告的自动化编辑与审核流程。

## 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                     NeoSpace 工作台插件                          │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    Agent Skills 层                       │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │   │
│  │  │ Analyst  │ │  Report  │ │  Audit   │ │ Approve  │   │   │
│  │  │ Manager  │ │ Checker  │ │ Workflow │ │ Handler  │   │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘   │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │   │
│  │  │  File    │ │ Translate│ │ Generate │ │ Publish  │   │   │
│  │  │ Handler  │ │  Skill   │ │  Report  │ │ Handler  │   │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘   │   │
│  └─────────────────────────────────────────────────────────┘   │
│                            │                                    │
│                            ▼                                    │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                 Supabase Skills 层                       │   │
│  │         （审核通过后调用，更新 Neolyst 数据库）            │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Neolyst 核心系统                            │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    Next.js App Router                    │   │
│  │          Server Components / Server Actions              │   │
│  └─────────────────────────────────────────────────────────┘   │
│                            │                                    │
│                            ▼                                    │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                   Supabase 后端                          │   │
│  │        Auth │ Postgres │ RLS │ PostgREST │ Storage      │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## Neolyst 系统（已存在）

Neolyst 是一个研究报告管理系统，提供以下核心能力：

### 技术栈
- **前端**: Next.js App Router + React + TypeScript
- **后端**: Supabase（Auth / Postgres / RLS / PostgREST / Storage）

### 核心功能
| 模块 | 说明 |
|------|------|
| 认证系统 | 登录、登出、忘记密码、统一认证回调 |
| 用户管理 | 列表/搜索/分页、邀请创建、编辑信息、角色管理 |
| 区域管理 | Region 的 CRUD 操作 |
| 分析师信息 | Analyst Info 的完整管理 |
| 行业分类 | 两级 Sector 结构管理 |
| 公司覆盖 | Coverage 与分析师关联管理 |
| 报告模板 | Word/Excel 模板管理、版本控制 |
| 报告管理 | 报告创建、版本管理、状态流转、审批流程 |

### 角色体系
| 角色 | 权限范围 |
|------|----------|
| `admin` | 系统管理员，全量操作权限 |
| `sa` | 审批角色，可审批/拒绝报告 |
| `analyst` | 分析师角色，可创建/编辑自己的报告 |

### 相关文档
- [架构设计](./neolyst/ARCHITECTURE.md) - 系统架构与技术边界
- [数据模型](./neolyst/DATA_MODEL.md) - 逻辑数据模型与 RLS 矩阵
- [需求规格](./neolyst/REQUIREMENTS.md) - 项目级业务需求

## 工作台插件（本项目）

### 目标定位
工作台插件通过 AI Agent Skills 实现 Neolyst 报告的 **自动化编辑和审核** 工作，包括：
- 研报模板的自动刷新
- 自动翻译
- 评级变动需要主管审核
- 各种合规检查（StockList、SFC 署名等）

### 设计原则
1. **独立 Skills**：各种自动化逻辑拆分为独立的 Skill，彼此相对独立
2. **流程编排**：通过可定制的工作流编排触发各 Skill
3. **审核后更新**：审核通过后调用 Supabase Skill 更新 Neolyst 数据库

### 能力模块

#### 1. 数据维护类
| Skill | 功能 |
|-------|------|
| Analyst Manager | 从 Excel 提取分析师信息，与 Neolyst 数据比对，确认后自动更新数据库 |

#### 2. 报告检查类
| Skill | 功能 |
|-------|------|
| Report Field Checker | 检查报告类型所需的字段是否完整 |
| File Completeness Checker | 检查 Word/Model/审批截图等文件是否齐全 |
| File Similarity Checker | 检查文件相似度，防止提交错误版本 |
| SFC Signature Validator | 核对分析师与 SFC 署名 |

#### 3. 审批流程类
| Skill | 功能 |
|-------|------|
| Coverage Approval Handler | 检查 Coverage 是否存在，处理首次覆盖审批邮件 |
| Chief Approval Handler | 报告提交前首席审批邮件处理 |
| RQC Approval Handler | RQC 触发判断（首次覆盖/评级调整/目标价变动≥30%）及主管确认邮件处理 |

#### 4. 内容生成类
| Skill | 功能 |
|-------|------|
| Report Title Generator | 根据报告类型和评级变动自动生成标题 |
| Report Extractor | 从 Word 中提取报告摘要和正文 |
| Stock Chart Generator | 从市场数据库获取 ticker 数据生成股价图 |
| Report Generator | 自动填充报告模板内容 |

#### 5. 发布流程类
| Skill | 功能 |
|-------|------|
| Report Submission Handler | 提交前检查（RQC 通过等），自动更新报告状态 |
| Translation Handler | 支持报告翻译版本管理 |
| Auto Auditor | AI 自动审核报告合规性 |
| Publish Handler | Word 转 PDF，发布通知邮件，同步 Wind 平台 |

### 报告字段矩阵（提交态必填）

| 字段 | company | sector | company_flash | sector_flash | common |
|---|:---:|:---:|:---:|:---:|:---:|
| Ticker | ✅ |  | ✅ |  |  |
| Rating | ✅ |  |  |  |  |
| Target price | ✅ |  |  |  |  |
| Region |  | ✅ |  | ✅ | ✅ |
| Sector |  | ✅ |  | ✅ |  |
| Report language | ✅ | ✅ | ✅ | ✅ | ✅ |
| Report title | ✅ | ✅ | ✅ | ✅ | ✅ |
| Analyst | ✅ | ✅ | ✅ | ✅ | ✅ |
| Contact Person | ✅ | ✅ | ✅ | ✅ | ✅ |
| Investment thesis | ✅ | ✅ | ✅ | ✅ | ✅ |
| Certificate | ✅ | ✅ | ✅ | ✅ | ✅ |

### 工作流编排

```
报告创建流程:
┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐
│  上传    │──▶│ 字段检查 │──▶│ 文件检查 │──▶│ 相似度   │
│  文件    │   │          │   │          │   │  检查    │
└──────────┘   └──────────┘   └──────────┘   └──────────┘
                                                │
                                                ▼
┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐
│  生成    │◀──│ Coverage │◀──│  SFC     │◀──│  提取    │
│  标题    │   │  检查    │   │  检查    │   │  内容    │
└──────────┘   └──────────┘   └──────────┘   └──────────┘
     │
     ▼
┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐
│  提交    │──▶│  RQC     │──▶│  首席    │──▶│  审核    │
│  报告    │   │  审批    │   │  审批    │   │  发布    │
└──────────┘   └──────────┘   └──────────┘   └──────────┘
```

## Supabase Skill 调用

工作台插件在审核通过后，通过 Supabase Skill 更新 Neolyst 数据库：

```typescript
// 示例：审核通过后更新报告状态
await supabaseSkill.updateReport(reportId, {
  status: 'published',
  published_by: approverId,
  published_at: new Date().toISOString()
});
```

### 数据同步范围
- 报告状态更新（draft → submitted → published/rejected）
- 分析师信息同步
- Coverage 创建与更新
- 审批日志记录
- 文件存储上传

## 文档目录

```
docs/
├── README.md                    # 本文档
├── req.md                       # 工作台插件需求规格
└── neolyst/                     # Neolyst 系统文档
    ├── ARCHITECTURE.md          # 系统架构
    ├── DATA_MODEL.md            # 数据模型
    └── REQUIREMENTS.md          # 业务需求
```

## 开发指南

### Skill 开发规范
1. 每个 Skill 应保持单一职责
2. Skill 之间通过事件/消息解耦
3. 所有数据库操作通过 Supabase Skill 进行
4. 审核相关操作需要记录完整日志

### 调用 Neolyst API
```typescript
// 通过 Supabase Skill 调用
import { createSupabaseSkill } from './skills/supabase';

const supabase = createSupabaseSkill();

// 查询 Coverage
const coverage = await supabase.query('coverage', {
  ticker: 'VRT US'
});

// 更新报告状态
await supabase.update('report', reportId, {
  status: 'submitted'
});
```

## 待补充内容

以下功能需要进一步细化需求：
- [ ] StockList 检查规则详细说明
- [ ] 文件相似度阈值与比对规则细化
- [ ] 自动翻译的语言策略
- [ ] 自动审核的 AI 判断规则
- [ ] 发布邮件的文案模板

---

*最后更新: 2026-03-04*
