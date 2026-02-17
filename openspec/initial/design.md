# 系统设计文档

## Context

这是投资研究报告管理系统,服务于券商内部使用,支持三种角色(Analyst、SA、Admin)协同工作,负责管理研究报告的创建、编辑、审核和发布流程。

## Goals / Non-Goals

**Goals:**
- 实现完整的基础数据管理(Analyst、Coverage、Sector、Region、报告模板 Word/Excel)
- 实现报告的创建、编辑、版本管理功能
- 实现报告发布和拒绝流程
- 确保所有修改都有完整的审计追踪(修改人、修改时间)
- 提供接口供独立的报告查看网站获取已发布报告

**Non-Goals:**
- 报告查看网站(独立系统,不包含在本项目范围内)
- 移动端支持(第一个版本仅桌面端)

## Decisions

### Decision 2: 数据库设计

**表结构设计:**

```
analyst (分析师)
- id: UUID (PK)
- full_name: VARCHAR
- chinese_name: VARCHAR
- email: VARCHAR (unique)
- suffix: VARCHAR
- region_id: UUID (FK)
- sfc: VARCHAR
- created_at: TIMESTAMP
- updated_at: TIMESTAMP

sector (行业分类)
- id: UUID (PK)
- level: INTEGER (1: 一级, 2: 二级)
- parent_id: UUID (FK, nullable, 二级行业关联一级)
- name_cn: VARCHAR
- name_en: VARCHAR
- wind_name: VARCHAR
- created_at: TIMESTAMP
- updated_at: TIMESTAMP

region (地区)
- id: UUID (PK)
- name: VARCHAR (unique)
- code: VARCHAR (e.g., 'CN', 'HK', 'US')
- created_at: TIMESTAMP
- updated_at: TIMESTAMP

coverage (公司覆盖)
- id: UUID (PK)
- ticker: VARCHAR
- country_of_domicile: VARCHAR
- english_full_name: VARCHAR
- chinese_short_name: VARCHAR
- traditional_chinese: VARCHAR
- sector_id: UUID (FK)
- isin: VARCHAR
- reporting_currency: VARCHAR
- ads_conversion_factor: DECIMAL
- is_duplicate: BOOLEAN (标记是否为重复 ticker 的覆盖)
- approved_by: UUID (nullable, FK -> analyst, 研究主管批准人)
- approved_at: TIMESTAMP (nullable, 批准时间)
- created_at: TIMESTAMP
- updated_at: TIMESTAMP

coverage_analyst (公司-分析师关联,支持团队)
- id: UUID (PK)
- coverage_id: UUID (FK)
- analyst_id: UUID (FK)
- role: INTEGER (1: 首席, 2/3/4: 其他作者)
- unique constraint: (coverage_id, analyst_id)

template (报告模板)
- id: UUID (PK)
- name: VARCHAR
- report_type: VARCHAR (Company, Sector, Company Flash, Sector Flash, Common)
- file_type: VARCHAR (word, excel)
- file_path: VARCHAR (Supabase Storage path)
- version: INTEGER
- created_at: TIMESTAMP
- updated_at: TIMESTAMP

report (报告)
- id: UUID (PK)
- report_type: VARCHAR
- title: VARCHAR
- status: VARCHAR (draft: 草稿, submitted: 已提交, published: 已发布, rejected: 已拒绝)
- language: VARCHAR (zh/en)
- investment_thesis: TEXT
- ticker: VARCHAR (nullable, Company 类型)
- rating: VARCHAR (nullable, Company 类型)
- target_price: DECIMAL (nullable, Company 类型)
- region_id: UUID (nullable, FK, Sector 类型)
- sector_id: UUID (nullable, FK, Sector 类型)
- current_version: INTEGER
- created_by: UUID (FK -> analyst)
- submitted_at: TIMESTAMP (nullable, 提交审核时间)
- submitted_by: UUID (nullable, FK -> analyst, 提交审核人)
- published_at: TIMESTAMP (nullable)
- published_by: UUID (nullable, FK -> analyst)
- rejected_at: TIMESTAMP (nullable)
- rejected_by: UUID (nullable, FK -> analyst)
- rejection_reason: TEXT (nullable, 拒绝理由)
- created_at: TIMESTAMP
- updated_at: TIMESTAMP

report_version (报告版本历史)
- id: UUID (PK)
- report_id: UUID (FK)
- version: INTEGER
- basic_info_snapshot: JSONB (基本信息快照)
- word_file_path: VARCHAR (nullable)
- model_file_path: VARCHAR (nullable)
- changed_by: UUID (FK -> analyst)
- changed_at: TIMESTAMP
- comment: VARCHAR (optional)

report_analyst (报告-分析师关联,支持多个分析师)
- id: UUID (PK)
- report_id: UUID (FK)
- analyst_id: UUID (FK)
- role: INTEGER (1: 首席, 2/3/4: 其他作者)
```

**理由:**
- 使用 UUID 作为主键,分布式系统友好
- 使用 JSONB 存储基本信息快照,方便查询历史版本
- 关联表支持多对多关系,如 coverage-analyst、report-analyst
- 软删除通过 status 字段实现,不物理删除数据

### Decision 3: 文件存储策略

**选择:** 使用 Supabase Storage

**理由:**
- Supabase Storage 提供开箱即用的文件存储
- 自动处理文件上传、下载、权限控制
- 支持文件版本管理
- 与数据库集成良好

**文件组织结构:**
```
storage/
├── templates/
│   ├── {template_id}/{version}/template.docx  (Word 模板)
│   └── {template_id}/{version}/template.xlsx  (Excel 模板)
├── reports/
│   └── {report_id}/
│       ├── word/
│       │   └── {version}/report.docx
│       └── model/
│           └── {version}/model.xlsx
```

### Decision 4: 版本管理策略

**选择:** 每次修改创建新版本记录

**实现:**
- 每次修改(基本信息/Word/Model)都在 `report_version` 表中创建新记录
- 使用 `version` 字段递增版本号
- 根据字段内容判断修改类型:
  - `basic_info_snapshot` 有值 → 修改了基本信息
  - `word_file_path` 有值 → 修改了Word文档
  - `model_file_path` 有值 → 修改了Excel模型
- 可以同时包含多个修改类型(如同时修改基本信息和Word)
- 基本信息 snapshot 以 JSONB 格式存储,方便恢复和对比

**理由:**
- 完整保留所有修改历史,满足合规要求
- 可以追溯到任何时间点的报告状态
- 支持版本对比和恢复

**报告功能页面设计原则:**

为了清晰区分报告管理和审核职责，系统将报告功能分为两个独立页面：

**1. Reports 页面（报告列表）**
- **功能定位**: 报告管理和协作页面
- **访问权限**: 所有角色都可以访问
  - **Analyst**: 查看和管理自己的报告（草稿、已提交、已发布、已拒绝）
  - **SA/Admin**: 查看所有报告，监控报告状态
- **主要操作**:
  - 查看报告列表（按状态筛选）
  - 创建新报告
  - 编辑报告（只能编辑草稿状态的报告）
  - 提交报告审核（Analyst 只能提交自己的草稿）
  - 查看报告详情
  - 查看版本历史
- **页面特点**:
  - 侧重于报告的 CRUD 操作
  - 显示报告的完整生命周期
  - 提供报告编辑和提交流程入口

**2. Report Review 页面（报告审核）**
- **功能定位**: SA/Admin 专属的报告审核工作台
- **访问权限**: 仅 SA 和 Admin 可以访问
- **主要操作**:
  - 查看待审核报告列表（仅显示状态为"已提交"的报告）
  - 查看报告完整信息（Word 预览、Excel 下载）
  - 批准报告发布
  - 拒绝报告（需填写拒绝理由）
  - 查看审核历史和统计
- **页面特点**:
  - 专注于审核工作流
  - 显示审核统计信息（待审核数量、今日已审核等）
  - 高亮显示等待时间较长的报告
  - 提供批量审核功能（可选）

**两个页面的关系:**
```
Reports (报告管理)             Report Review (报告审核)
       ↓                                ↓
  Analyst 创建报告                Analyst 提交报告
       ↓                                ↓
  提交审核 ─────────────────────→  出现在审核队列
       ↓                                ↓
  显示状态: 已提交              SA/Admin 审核
       ↓                                ↓
    可以编辑                        批准/拒绝
                                        ↓
                                  状态: 已发布/已拒绝
                                        ↓
              Analyst 查看状态 ──────────→ 更新 Reports 中的状态
```

**为什么分离两个页面:**
1. **职责分离**: 报告管理和审核是两个不同的业务流程
2. **权限控制**: 审核页面需要特殊权限限制
3. **用户体验**: SA/Admin 可以专注于审核工作，不被其他报告干扰
4. **开发简化**: 两个页面可以独立开发和优化




**代码质量标准:**
- ✅ 所有代码必须通过 Black/Prettier 格式化
- ✅ 所有代码必须通过 Ruff/ESLint 检查




**数据库设计 **

```sql
-- analyst 表
CREATE TABLE analyst (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  full_name VARCHAR NOT NULL,
  chinese_name VARCHAR,
  email VARCHAR UNIQUE NOT NULL,
  suffix VARCHAR,
  region_id UUID REFERENCES region(id),
  sfc VARCHAR,
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMP DEFAULT now(),
  updated_at TIMESTAMP DEFAULT now()
);

-- report 表
CREATE TABLE report (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  report_type VARCHAR NOT NULL,
  title VARCHAR NOT NULL,
  status VARCHAR NOT NULL DEFAULT 'draft', -- 'draft', 'submitted', 'published', 'rejected'
  language VARCHAR,
  investment_thesis TEXT,

  -- Company 类型字段
  ticker VARCHAR,
  rating VARCHAR,
  target_price DECIMAL,

  -- Sector 类型字段
  region_id UUID REFERENCES region(id),
  sector_id UUID REFERENCES sector(id),

  -- 工作流字段
  created_by UUID NOT NULL REFERENCES analyst(id),
  submitted_at TIMESTAMP,
  submitted_by UUID REFERENCES analyst(id),
  published_at TIMESTAMP,
  published_by UUID REFERENCES analyst(id),
  rejected_at TIMESTAMP,
  rejected_by UUID REFERENCES analyst(id),
  rejection_reason TEXT,

  created_at TIMESTAMP DEFAULT now(),
  updated_at TIMESTAMP DEFAULT now()
);



**报告状态流转图:**
```
Analyst          SA/Admin
  │                │
  │ 创建报告        │
  ├──────────────► │ (status: draft)
  │                │
  │ 提交审核        │
  ├──────────────► │ (status: submitted)
  │                │
  │                │ 审核批准
  │◄──────────────┤ (status: published)
  │                │
  │                │ 审核拒绝
  │◄──────────────┤ (status: rejected)
  │                │
  │ 重新编辑        │
  ├──────────────► │ (status: draft)
  │                │
  │ 提交审核        │
  ├──────────────► │ (status: submitted)
```
