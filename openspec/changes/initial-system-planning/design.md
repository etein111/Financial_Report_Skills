# 系统设计文档

## Context

这是投资研究报告管理系统的第一个版本(MVP)。系统主要服务于券商内部使用,由系统管理员统一操作,负责管理研究报告的创建、编辑、版本控制和发布流程。

第二个版本将开发独立的报告查看网站,因此第一个版本需要为未来集成预留接口。

## Goals / Non-Goals

**Goals:**
- 实现完整的基础数据管理(Analyst、Coverage、Sector、Region、Word 模板)
- 实现报告的创建、编辑、版本管理功能
- 实现报告发布和拒绝流程
- 确保所有修改都有完整的审计追踪(修改人、修改时间)
- 为未来版本预留扩展接口(发布后的报告复制到独立网站)

**Non-Goals:**
- 前台展示网站(第二个版本)
- 多角色权限系统(第一个版本只有系统管理员)
- 独立网站的用户管理和权限(第二个版本)
- 报告审批工作流(第一个版本由管理员直接操作)

## Decisions

### Decision 1: 技术栈选择

**选择:** FastAPI + Vue + Supabase + uv

**理由:**
- **FastAPI**: 现代、高性能的 Python Web 框架,自动生成 API 文档,类型安全
- **Vue**: 渐进式前端框架,易于上手,组件化开发
- **Supabase**: 提供 PostgreSQL 数据库、身份认证、文件存储等开箱即用的功能,减少基础设施搭建工作
- **uv**: 极速的 Python 包管理器,比 pip 快很多,提升开发体验

**权衡:**
- 考虑过 Django,但 FastAPI 更轻量且性能更好
- 考虑过 React,但 Vue 学习曲线更平缓
- Supabase 相比自建数据库节省了运维成本

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

word_template (Word 模板)
- id: UUID (PK)
- name: VARCHAR
- report_type: VARCHAR (Company, Sector, Company Flash, Sector Flash, Common)
- file_path: VARCHAR (Supabase Storage path)
- version: INTEGER
- created_at: TIMESTAMP
- updated_at: TIMESTAMP

report (报告)
- id: UUID (PK)
- report_type: VARCHAR
- title: VARCHAR
- status: VARCHAR (draft: 未发布, published: 已发布, rejected: 已拒绝)
- language: VARCHAR (zh/en)
- investment_thesis: TEXT
- ticker: VARCHAR (nullable, Company 类型)
- rating: VARCHAR (nullable, Company 类型)
- target_price: DECIMAL (nullable, Company 类型)
- region_id: UUID (nullable, FK, Sector 类型)
- sector_id: UUID (nullable, FK, Sector 类型)
- current_version: INTEGER
- created_by: UUID (FK -> analyst)
- published_at: TIMESTAMP (nullable)
- published_by: UUID (nullable, FK -> analyst)
- rejected_at: TIMESTAMP (nullable)
- rejected_by: UUID (nullable, FK -> analyst)
- created_at: TIMESTAMP
- updated_at: TIMESTAMP

report_version (报告版本历史)
- id: UUID (PK)
- report_id: UUID (FK)
- version: INTEGER
- basic_info_snapshot: JSONB (基本信息快照)
- word_file_path: VARCHAR (nullable)
- model_file_path: VARCHAR (nullable)
- change_type: VARCHAR (basic_info/word/model)
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
├── word-templates/
│   └── {template_id}/{version}/template.docx
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
- 使用 `change_type` 字段标识修改类型
- 基本信息 snapshot 以 JSONB 格式存储,方便恢复和对比

**理由:**
- 完整保留所有修改历史,满足合规要求
- 可以追溯到任何时间点的报告状态
- 支持版本对比和恢复

### Decision 5: API 设计原则

**RESTful API 设计:**
- 使用标准 HTTP 方法(GET/POST/PUT/DELETE)
- 使用语义化的 URL 路径
- 统一的响应格式
- 使用 JWT 认证(通过 Supabase Auth)

**API 示例:**
```
GET    /api/analysts          # 获取分析师列表
POST   /api/analysts          # 创建分析师
GET    /api/analysts/{id}     # 获取单个分析师
PUT    /api/analysts/{id}     # 更新分析师

GET    /api/coverage          # 获取公司覆盖列表
POST   /api/coverage          # 创建公司覆盖
POST   /api/coverage/check-duplicate  # 检查 ticker 是否已被覆盖
GET    /api/coverage/{id}     # 获取单个覆盖详情
PUT    /api/coverage/{id}     # 更新覆盖信息

GET    /api/reports           # 获取报告列表
POST   /api/reports           # 创建报告
GET    /api/reports/{id}      # 获取单个报告
PUT    /api/reports/{id}      # 更新报告
POST   /api/reports/{id}/publish   # 发布报告
POST   /api/reports/{id}/reject    # 拒绝报告
GET    /api/reports/{id}/versions  # 获取版本历史
```

**Coverage 重复检查 API:**
```python
POST /api/coverage/check-duplicate
Request: { "ticker": "AAPL" }
Response:
{
  "is_duplicate": true,
  "existing_coverages": [
    {
      "analyst_name": "John Doe",
      "analyst_email": "john@example.com",
      "created_at": "2024-01-01T00:00:00Z"
    }
  ]
}
```

前端在用户输入 ticker 后,调用此 API 检查是否重复。如果重复,显示警告对话框,要求用户确认后才能创建。

### Decision 6: 前端架构

**选择:** Vue 3 + Composition API + Pinia + Element Plus

**理由:**
- **Vue 3 Composition API**: 更好的类型推断,代码组织更灵活
- **Pinia**: 官方推荐的状态管理库,比 Vuex 更简洁
- **Element Plus**: 成熟的 UI 组件库,减少开发工作量

**界面设计模式: 桌面式界面 + 窗口化操作**

与传统 Web 应用不同,本系统采用仿操作系统的桌面式界面:

1. **无全局导航条**: 没有传统的侧边栏或顶部导航栏
2. **仿系统桌面**: 登录后进入类似 Windows/macOS 的桌面环境
3. **功能卡片平铺**: 各功能模块以带图标的卡片形式展示在桌面上
4. **窗口化操作**: 点击功能卡片打开可拖动、可调整大小的窗口
5. **无返回按钮**: 窗口直接关闭,不需要返回按钮

**交互设计:**
```
登录页
  ↓
桌面 (Desktop.vue)
  ├── 功能卡片 (图标 + 名称)
  │   ├── 📊 Analyst 管理
  │   ├── 🏢 Coverage 管理
  │   ├── 🏗️ Sector 管理
  │   ├── 🌍 Region 管理
  │   ├── 📄 Word 模板
  │   ├── 📝 报告列表
  │   ├── ➕ 创建报告
  │   └── 📋 版本历史
  │
  └── 任务栏 (Taskbar.vue)
      ├── 开始菜单 (可选)
      ├── 已打开窗口列表
      └── 系统托盘 (时间、通知等)
```

**窗口系统:**
- 支持多个窗口同时打开
- 窗口可拖动、调整大小、最小化、最大化、关闭
- 窗口层级管理 (点击置顶)
- 窗口状态保存在 Pinia store
- 支持窗口快捷键 (Alt+Tab 切换)

**页面结构:**
```
/src
├── views/
│   ├── Login.vue              # 登录页
│   ├── Desktop.vue            # 桌面主界面
│   └── windows/               # 窗口化功能页
│       ├──基础数据/
│       │   ├── AnalystWindow.vue
│       │   ├── CoverageWindow.vue
│       │   ├── SectorWindow.vue
│       │   ├── RegionWindow.vue
│       │   └── TemplateWindow.vue
│       └──报告管理/
│           ├── ReportListWindow.vue
│           ├── ReportCreateWindow.vue
│           ├── ReportEditWindow.vue
│           └── ReportVersionsWindow.vue
├── components/
│   ├── window/                # 窗口系统组件
│   │   ├── WindowContainer.vue     # 窗口容器(支持拖动、调整大小)
│   │   ├── WindowHeader.vue        # 窗口标题栏
│   │   └── WindowManager.vue       # 窗口管理器
│   ├── desktop/               # 桌面组件
│   │   ├── DesktopIcon.vue         # 桌面图标卡片
│   │   └── Taskbar.vue             # 任务栏
│   └── common/                 # 通用组件
└── stores/
    ├── window.ts              # 窗口状态管理
    ├── desktop.ts             # 桌面状态
    └── user.ts                # 用户状态
```

**Window Store 结构:**
```typescript
interface WindowState {
  windows: Array<{
    id: string
    title: string
    component: Component
    position: { x: number; y: number }
    size: { width: number; height: number }
    isMinimized: boolean
    isMaximized: boolean
    zIndex: number
  }>
  activeWindowId: string | null
}
```

### Decision 7: 认证和授权

**选择:** 使用 Supabase Auth

**实现:**
- 第一个版本只有系统管理员角色
- 使用 Email + Password 登录
- JWT Token 存储在 localStorage
- API 请求携带 Authorization header

**未来扩展:**
- 第二个版本将添加 Analyst、研究主管、SA 等角色
- 使用 Supabase RLS(Row Level Security)实现数据权限控制

### Decision 8: 已发布报告的对外接口

**设计:** 为外部系统提供已发布报告的查询接口

**实现:**
- 发布报告时,在 `published_at` 和 `published_by` 字段记录发布信息
- 提供公开 API 供外部系统(如独立的报告查看网站)查询已发布报告
- API 支持按时间戳增量查询,方便外部系统同步数据

**API 设计:**
```python
# 获取已发布的报告列表(支持按时间戳增量查询)
GET /api/public/published-reports?since={timestamp}

Response:
{
  "reports": [
    {
      "id": "uuid",
      "report_type": "Company",
      "title": "报告标题",
      "published_at": "2024-01-01T00:00:00Z",
      "basic_info": { ... },  # 报告基本信息
      "word_file_url": "https://...",  # Word 文件下载链接
      "model_file_url": "https://..."  # Excel 文件下载链接(如有)
    }
  ],
  "last_updated": "2024-01-01T00:00:00Z"
}
```

**注意:** 独立的报告查看网站由另一个项目负责,本项目仅提供数据接口。
