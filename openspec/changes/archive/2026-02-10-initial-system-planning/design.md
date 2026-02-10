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

### Decision 6: 开发工具链

**选择:** 尽可能使用 uv 作为包管理和项目工具

**uv 的应用范围:**

**后端 (Python):**
- **包管理**: 使用 `uv pip` 替代 `pip`,速度提升 10-100 倍
- **虚拟环境**: 使用 `uv venv` 创建虚拟环境
- **依赖锁定**: 使用 `uv lock` 生成依赖锁定文件
- **脚本运行**: 使用 `uv run` 运行 Python 脚本和工具

**前端 (Node.js/JavaScript):**
- 虽然前端不直接使用 Python,但可以在项目根目录使用 uv 管理开发工具
- 通过 `uv` 运行基于 Python 的前端构建工具(如果有)

**项目管理:**
- 使用 `uv` 统一管理整个项目的工具脚本
- 示例: `uv run lint`, `uv run test`, `uv run dev`

**安装和使用:**
```bash
# 安装 uv
pip install uv
# 或使用官方安装脚本
curl -LsSf https://astral.sh/uv/install.sh | sh

# 初始化项目
uv init

# 添加依赖
uv add fastapi uvicorn[standard] sqlalchemy supabase

# 运行开发服务器
uv run uvicorn backend.main:app --reload
```

**理由:**
- **极致速度**: uv 用 Rust 编写,比 pip 快 10-100 倍
- **统一体验**: 前后端使用统一的工具链管理
- **依赖锁定**: 内置依赖锁定,确保可重现构建
- **现代设计**: 解决了 pip 的许多历史问题

**替代方案对比:**
- ❌ pip: 速度慢,没有内置依赖锁定
- ❌ Poetry: 功能完善但速度较慢
- ❌ PDM: 较新的项目,生态不够成熟
- ✅ uv: 最快、最现代的选择

### Decision 7: 前端架构

**选择:** Vue 3 + TypeScript + Vite + Tailwind CSS

**理由:**
- **Vue 3**: 现代化前端框架，提供响应式数据和组件化开发
- **TypeScript**: 类型安全，提升代码质量和可维护性
- **Vite**: 极速的开发体验和热更新
- **Tailwind CSS**: 实用优先的CSS框架，与prototype保持一致，快速实现定制化设计
- **自定义组件**: 直接使用Tailwind构建简单组件，不使用Headless UI或Element Plus
- **状态管理**: 使用Vue 3的reactive()和provide/inject，不需要Pinia（项目规模适中）
- **与prototype一致**: 设计风格、CSS类名、颜色系统完全沿用已验证的prototype

**界面设计模式: 桌面式界面 + 多页面应用**

与传统 Web 应用不同，本系统采用仿桌面的多页面应用界面：

1. **桌面主页**: 登录后进入桌面主页，显示功能卡片
2. **功能卡片**: 各功能模块以带图标的卡片形式展示
3. **独立页面**: 点击功能卡片在新标签页打开独立功能页面
4. **简单操作**: 功能页面用完直接关闭，无需返回按钮

**视觉设计规范:**

**主题方向:**
- **主题模式**: "精致的深色模式" (Sophisticated Dark Mode)
- **背景色**: 使用 Tailwind CSS `zinc-950` 作为主背景色,避免纯黑色
- **文字主色**: `#ffffff` (白色)
- **设计风格**: "Linear 风格的专业感"
  - 使用细边框 (1px border-white/10) 代替阴影效果
  - 简洁、现代、科技感

**字体系统:**
- **UI 字体**: Inter (Sans-serif) - 用于界面文本、按钮、标签
- **元数据字体**: JetBrains Mono (Monospace) - 用于所有元数据、版本号、时间戳、ID 等

**颜色系统 (Tailwind CSS):**
```css
/* 背景色 */
--bg-primary: zinc-950       #09090b  /* 主背景 */
--bg-secondary: zinc-900     #18181b  /* 次级背景、卡片背景 */
--bg-tertiary: zinc-800/50   #27272a80 /* 悬停状态 */

/* 边框色 */
--border-default: white/10   /* 默认边框 */
--border-hover: white/20     /* 悬停边框 */

/* 文字色 */
--text-primary: white        #ffffff  /* 主文字 */
--text-secondary: zinc-400   #a1a1aa  /* 次要文字 */
--text-muted: zinc-500       #71717a  /* 弱化文字 */

/* 状态色 */
--status-draft: zinc-500     #71717a  /* 草稿 - 灰色 */
--status-reviewing: amber-500 #f59e0b /* 审核中 - 琥珀色 */
--status-approved: emerald-500 #10b981 /* 已批准 - 绿色 */
--status-rejected: red-500   #ef4444  /* 已拒绝 - 红色 */
```

**组件设计规范:**

**1. 按钮 (Buttons):**
```css
/* 圆角: 6px (rounded-md) */
/* 微妙的渐变背景 */
--btn-bg-default: zinc-800 → zinc-700
--btn-bg-hover: zinc-700 → zinc-600
--btn-text: white
--btn-border: white/10
```

**2. 桌面卡片 (Desktop Cards):**
```css
/* 尺寸: 160px x 120px */
/* 背景: zinc-900 with 1px white/10 border */
/* 悬停效果: 微妙的发光 (white/5) + 轻微提升 */
padding: 16px
gap: 12px
transition: all 200ms ease
```

**3. 页面头部 (Page Headers):**
```css
/* 背景: zinc-900 */
/* 边框: 1px white/10 底部 */
/* 标题: 20px, font-weight 600 */
/* 内边距: 16px 24px */
```

**4. 状态指示器 (Status Indicators):**
```css
/* 使用弱化的颜色,避免过于鲜艳 */
--draft: zinc-500 background + zinc-400 text
--reviewing: amber-500/20 background + amber-400 text
--approved: emerald-500/20 background + emerald-400 text
--rejected: red-500/20 background + red-400 text
```

**5. 高密度布局 (High Density):**
```css
/* 列表项 */
padding: 8px 12px
font-size: 13px (列表项) / 14px (标题)
line-height: 1.4
gap: 4px (紧凑间距)

/* 表单 */
input padding: 8px 12px
label font-size: 13px
form gap: 16px
```

**悬停效果 (Hover Effects):**
```css
/* 卡片悬停 */
.card:hover {
  border-color: white/20;
  box-shadow: 0 0 0 1px white/5;
  transform: translateY(-2px);
}

/* 按钮悬停 */
.button:hover {
  background: linear-gradient(to bottom, zinc-700, zinc-600);
  border-color: white/20;
}

/* 列表行悬停 */
.list-item:hover {
  background: zinc-800/50;
  border-color: white/15;
}
```

**功能页面布局规范:**

**1. 报告列表页面 (Reports Page):**
```
┌─────────────────────────────────────────┐
│ 📝 Reports                               │  ← 页面标题
├─────────────────────────────────────────┤
│ [Filters]                               │
│ Status: [All▼] Type: [All▼] Search: [___] │  ← 筛选工具栏
├─────────────────────────────────────────┤
│ ┌─────────────────────────────────────┐ │
│ │ 📄 AAPL Stock Analysis [Draft]  2h ago │ │  ← 紧凑列表行
│ │    Company | John Doe                │ │
│ ├─────────────────────────────────────┤ │
│ │ 📄 TSLA Investment Rating [Review] Yesterday │ │
│ │    Company | Jane Smith              │ │
│ └─────────────────────────────────────┘ │
│ [High density list, scrollable]         │
└─────────────────────────────────────────┘

布局:
- 左侧: 报告列表 (70% 宽度)
  - 紧凑列表行,每个项目 48px 高度
  - 显示: 标题、类型、状态、时间、Analyst
- 右侧: 报告预览 (30% 宽度) - 可选
  - 显示选中报告的详细信息
  - 包含版本历史时间线
```

**2. 基础数据管理页面 (Data Management Pages):**
```
┌─────────────────────────────────────────┐
│ 👤 Analysts                               │  ← 页面标题
├─────────────────────────────────────────┤
│ [Search]                [+ New] [Export]│  ← 工具栏
├─────────────────────────────────────────┤
│ Name              Email         Region  │  ← 表头
├─────────────────────────────────────────┤
│ John Doe          john@...      CN      │  ← 数据行 (高密度)
│ Jane Smith        jane@...      US      │
│ ...                                       │
└─────────────────────────────────────────┘

表格样式:
- 行高: 40px (紧凑但不拥挤)
- 字体大小: 13px
- 边框: 1px white/5 (底部边框分隔)
- 悬停: zinc-800/50 背景
- 选中: zinc-700 背景 + zinc-500 左边框 (2px)
```

**3. 表单布局 (Forms):**
```
┌─────────────────────────────────────────┐
│ ➕ New Report                            │  ← 页面标题
├─────────────────────────────────────────┤
│                                         │
│ Report Type *                           │  ← 标签 (13px, zinc-400)
│ [Company ▼]                            │  ← 选择器
│                                         │
│ Report Title *                          │
│ [________________________________]      │  ← 输入框
│                                         │
│ Analysts * (Select multiple)            │
│ [+ John Doe] [+ Jane Smith] [+]         │  ← 标签选择器
│                                         │
│ Report File (Word) *                    │
│ ┌───────────────────────────────────┐  │
│ │ 📄 Drag & drop or click to upload │  │  ← 上传区域
│ │    Supports .docx, .doc           │  │
│ └───────────────────────────────────┘  │
│                                         │
│        [Cancel]  [Save Draft]  [Publish] │  ← 操作按钮组
└─────────────────────────────────────────┘

表单样式:
- 标签字体: 13px, zinc-400
- 输入框: zinc-900 背景, 1px white/10 边框
- 输入框聚焦: zinc-800 背景, white/20 边框
- 上传区域: 虚线边框 (white/10), zinc-900/50 背景
- 按钮组间距: 8px
```

**4. 版本历史时间线 (Version History Timeline):**
```
在报告编辑页面右侧或底部显示:

📋 Version History
┌─────────────────────────────────────┐
│ ● v3 (Current)  [2h ago]          │  ← 最新版本
│ │  - Updated investment rating     │
│ │  - Author: John Doe              │
│ │                                  │
│ │ ○ v2  [Yesterday]               │
│ │ │  - Updated Excel Model         │
│ │ │  - Author: Jane Smith          │
│ │ │                                │
│ │ └ ○ v1  [3 days ago]            │
│ │    - Initial version             │
│ │    - Author: John Doe            │
│ └───────────────────────────────────┘

样式:
- 连接线: zinc-700
- 版本号: JetBrains Mono, 14px, zinc-300
- 时间戳: JetBrains Mono, 12px, zinc-500
- 描述: Inter, 13px, zinc-400
- 作者: Inter, 12px, zinc-500
```

**交互设计:**
```
登录页
  ↓
桌面 (Desktop.vue)
  ├── 功能卡片 (图标 + 名称) - 分组显示,所有文本使用英文
  │
  │   【报告功能组 - 上方】
  │   ├── 📝 Reports          - View my reports (Analyst) / View all reports (SA/Admin)
  │   ├── ➕ New Report       - Create new report
  │   ├── ✅ Report Review    - Review submitted reports (SA/Admin only)
  │   └── 📄 Templates        - Report template management (Word/Excel)
  │
  │   【基础数据管理组 - 下方】
  │   ├── 👤 Analysts         - Analyst information management
  │   ├── 🏢 Coverage         - Company coverage management
  │   ├── 🏗️ Sectors          - Industry classification management
  │   └── 🌍 Regions          - Region management
  │
```

**桌面布局设计:**
- 功能卡片分为两个组,使用视觉分隔(卡片组标题、间距或背景色区分)
- 报告功能组放在上方,因为这是最常用的核心功能
- 基础数据管理组放在下方,作为配置类功能
- 每个卡片包含: 图标 + 英文功能名称 + 简短描述(可选)
- 卡片支持悬停效果,点击在新标签页打开独立功能页面
- 功能页面直接关闭,无需返回按钮
- **界面语言**: 所有 UI 文本使用英文(按钮、标签、菜单等)

**页面结构:**
```
/src
├── views/
│   ├── Login.vue              # 登录页 (带粒子效果背景)
│   │   # - 使用 ParticleBackground 组件
│   │   # - 标语"The Future is Now"
│   │   # - 登录表单(英文界面)
│   ├── Desktop.vue            # 桌面主页
│   ├── reports/              # 报告管理页面 (独立页面,新标签页打开)
│   │   ├── ReportsPage.vue           # 报告列表页
│   │   ├── NewReportPage.vue          # 创建报告页
│   │   ├── ReportEditPage.vue         # 编辑报告页
│   │   ├── ReportVersionsPage.vue     # 版本历史页
│   │   └── TemplatesPage.vue          # 模板管理页
│   ├── review/               # 报告审核页面 (SA/Admin only, 新标签页打开)
│   │   ├── ReportReviewPage.vue        # 审核列表页
│   │   └── ReportReviewDetailPage.vue  # 审核详情页
│   └── data-management/       # 基础数据管理页面 (新标签页打开)
│       ├── AnalystsPage.vue           # Analyst 管理页
│       ├── CoveragePage.vue           # Coverage 管理页
│       ├── SectorsPage.vue            # Sector 管理页
│       └── RegionsPage.vue            # Region 管理页
├── components/
│   ├── desktop/               # 桌面组件
│   │   ├── DesktopCard.vue             # 桌面功能卡片
│   │   ├── DesktopCardGroup.vue        # 卡片组容器
│   │   └── DesktopHeader.vue           # 桌面顶部导航
│   └── common/                 # 通用组件
│       ├── ParticleBackground.vue      # 粒子背景组件
│       └── StatusBadge.vue             # 状态标签组件
└── stores/
    ├── user.ts                # 用户状态
    └── desktop.ts             # 桌面状态
```

**交互设计:**
- 桌面卡片点击后在新标签页打开独立功能页面
- 功能页面直接关闭，无需返回按钮
- 页面间通过浏览器标签页切换

**登录页设计 (Login Page):**

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│   [粒子效果背景 - Canvas 2D]                           │
│                                                         │
│                 ┌─────────────────────────┐            │
│                 │                         │            │
│                 │  The Future is Here     │            │  ← 标语
│                 │    <Inter font>         │            │
│                 │    48px, white/90       │            │
│                 │                         │            │
│                 ├─────────────────────────┤            │
│                 │                         │            │
│                 │  Email          __      │            │
│                 │  ──────────────┴────    │            │
│                 │                         │            │
│                 │  Password       __      │            │
│                 │  ──────────────┴────    │            │
│                 │                         │            │
│                 │     [    Login    ]     │            │  ← 按钮
│                 │                         │            │
│                 └─────────────────────────┘            │
│                                                         │
└─────────────────────────────────────────────────────────┘

布局:
- 登录框居中显示
- 尺寸: 400px × 420px
- 背景: zinc-900 with 1px white/10 border
- 圆角: 12px
- 标语和登录框之间: 60px 间距
```

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
  无法编辑                        批准/拒绝
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

**粒子效果技术实现:**

**选择:** 使用原生 Canvas 2D API 手写粒子效果

**理由:**
- ✅ 零依赖:不需要引入任何外部库
- ✅ 轻量级:代码量小(< 200 行)
- ✅ 高性能:Canvas 2D 性能优秀,支持 60fps
- ✅ 可控:完全自定义粒子行为和视觉效果

**粒子效果规范:**
```typescript
// 粒子配置
const particleConfig = {
  count: 80,              // 粒子数量 (不太多,保证性能)
  size: { min: 1, max: 3 }, // 粒子大小
  speed: { min: 0.2, max: 0.8 }, // 移动速度
  opacity: { min: 0.1, max: 0.6 }, // 透明度
  color: '255, 255, 255',  // 白色粒子
  connectionDistance: 120, // 连线距离
  mouseInteraction: true   // 鼠标互动
}

// 粒子行为
- 缓慢漂浮的粒子
- 粒子之间距离<120px时绘制连线
- 连线透明度根据距离渐变
- 鼠标靠近时粒子微微加速远离
```

**性能优化措施:**
```typescript
// 1. 使用 requestAnimationFrame
// 2. 限制粒子数量
// 3. 使用离屏 Canvas (如果需要)
// 4. 登录成功后立即停止动画
// 5. 使用 will-change CSS 属性
```

**代码结构:**
```typescript
// components/common/ParticleBackground.vue
<template>
  <canvas ref="canvas" class="particle-bg" />
</template>

<script setup lang="ts">
// ~150 行代码
// - Particle 类
// - Animation loop
// - Mouse interaction
// - Resize handler
</script>

<style scoped>
.particle-bg {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: zinc-950;
  will-change: transform;
}
</style>
```

**性能对比:**
| 方案 | 包大小 | 性能 | 依赖 |
|------|--------|------|------|
| Canvas 2D 手写 | ~5KB | ⭐⭐⭐⭐⭐ | 无 |
| tsparticles | ~40KB | ⭐⭐⭐⭐ | 有 |
| three.js | ~600KB | ⭐⭐⭐ | 有 |
| particles.js | ~15KB | ⭐⭐⭐ | 有 |

**结论:** 使用原生 Canvas 2D 手写,零依赖、最小体积、最佳性能。

### Decision 7.1: 界面原型验证后的架构调整

**背景:** 在创建 HTML 静态原型并经过用户确认后,对原设计进行了重要调整。

**调整 1: 从窗口化改为多页面应用**

**原设计:** 窗口化操作模式
- 点击桌面功能卡片打开可拖动、可调整大小的窗口
- 支持多窗口同时打开

**调整后:** 多页面应用模式
- 点击桌面功能卡片在**新标签页**打开独立功能页面
- 每个功能有独立 URL，方便分享和直接访问
- 用户通过关闭标签页来关闭功能页，无需返回按钮

**理由:**
1. **可分享性**: 独立 URL 可以直接发送给他人
2. **简化交互**: 用户熟悉浏览器标签页操作，降低学习成本
3. **开发简化**: 不需要实现复杂的窗口管理系统
4. **性能优化**: 每个页面独立加载，不占用主页面资源

**页面结构:**
```
/login.html          - 登录页 (独立 URL)
/index.html          - 桌面/主页
/reports.html        - 报告列表 (新标签页打开)
/new-report.html     - 创建报告 (新标签页打开)
/templates.html      - 模板管理 (新标签页打开)
/analysts.html       - Analyst 管理 (新标签页打开)
/coverage.html       - Coverage 管理 (新标签页打开)
/sectors.html        - Sector 管理 (新标签页打开)
/regions.html        - Region 管理 (新标签页打开)
```

**实现细节:**
- 桌面卡片使用 `<a>` 标签 + `target="_blank"` 打开新标签页
- 每个功能页顶部有 "← Back to Desktop" 链接返回桌面
- 登录页和桌面页完全分离,不同 URL

**调整 2: 视觉设计优化**

**背景色调整:**
- **原设计**: 纯色背景 `#09090b` (zinc-950)
- **调整后**: 渐变背景 `linear-gradient(to bottom, #0c1221 0%, #09090b 50%, #020617 100%)`
- **理由**: 深蓝色到黑色的渐变更有层次感和科技感,避免过于单调

**登录页标题调整:**
- **原设计**: "The Future is Here" (48px, 可能折行)
- **调整后**: "The Future is Now" (32px, `white-space: nowrap`)
- **理由**: 更简洁有力,防止标题溢出登录框

**粒子效果优化:**
- **粒子数量**: 80 → 120 (适中密度)
- **粒子速度**: 基础速度 2 (适中,不快不慢)
- **交互方式**: 移除所有鼠标交互效果
  - 不再响应鼠标位置
  - 粒子自由移动,保持原始速度
  - 保留粒子间连线效果(距离 < 140px)
  - 保留脉冲闪烁效果

**最终粒子配置:**
```typescript
const particleConfig = {
  count: 120,                    // 粒子数量
  speed: 2,                      // 移动速度 (vx, vy = (Math.random() - 0.5) * 2)
  size: { min: 1, max: 3 },      // 粒子大小
  opacity: { min: 0.3, max: 0.7 }, // 透明度范围
  color: 'blue-cyan gradient',   // 蓝色-青色渐变 (hue: 200-260)
  connectionDistance: 140,       // 连线距离阈值
  mouseInteraction: false,       // 禁用鼠标交互
  pulseSpeed: 0.15               // 脉冲速度
}
```

**设计规范更新:**

**1. 背景色系统:**
```css
/* 主背景 - 渐变 */
--bg-primary: linear-gradient(to bottom, #0c1221 0%, #09090b 50%, #020617 100%);

/* 备用纯色 (用于卡片等) */
--bg-secondary: zinc-900       #18181b
--bg-tertiary: zinc-950        #09090b
```

**2. 登录页布局:**
```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│   [粒子效果背景 - Canvas 2D - 渐变背景]                  │
│                                                         │
│                 ┌─────────────────────────┐            │
│                 │                         │            │
│                 │  The Future is Now      │            │  ← 32px, 不折行
│                 │    <Inter font>         │            │
│                 │    white-space: nowrap  │            │
│                 │                         │            │
│                 │  Research Report        │            │
│                 │  Management System      │            │
│                 ├─────────────────────────┤            │
│                 │  Email                  │            │
│                 │  [______________]       │            │
│                 │                         │            │
│                 │  Password               │            │
│                 │  [______________]       │            │
│                 │                         │            │
│                 │     [    Login    ]     │            │
│                 │                         │            │
│                 └─────────────────────────┘            │
│                                                         │
└─────────────────────────────────────────────────────────┘

尺寸: 400px × 420px
登录框背景: zinc-900 (#18181b)
边框: 1px white/10
圆角: 12px
```

**3. 桌面布局:**
```
┌─────────────────────────────────────────────────────────────┐
│ Neolyst                              Welcome, Admin  Logout │  ← 顶部导航栏
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Reports                                                    │  ← 卡片组标题
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                 │
│  │   📝     │  │   ➕     │  │   📄     │                 │
│  │ Reports  │  │New Report│  │Templates │                 │
│  │View all  │  │Create new│  │Word/Excel│                 │
│  └──────────┘  └──────────┘  └──────────┘                 │
│                                                             │
│  Data Management                                           │  ← 卡片组标题
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │   👤     │  │   🏢     │  │   🏗️    │  │   🌍     │  │
│  │ Analysts │  │ Coverage │  │ Sectors  │  │ Regions  │  │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘  │
└─────────────────────────────────────────────────────────────┘

卡片:
- 尺寸: 自适应,保持 4:3 宽高比
- 背景: zinc-900
- 边框: 1px white/10
- 悬停: 边框变亮 white/20,轻微上移 2px
- 图标: 40px emoji
- 标题: 14px, font-weight 500
- 描述: 12px, zinc-500
```

**4. 功能页布局:**
```
┌─────────────────────────────────────────────────────────────┐
│ 📝 Reports                        ← Back to Desktop          │  ← 页面头部
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  [功能内容区]                                               │
│                                                             │
└─────────────────────────────────────────────────────────────┘

页面头部:
- 背景: zinc-900
- 边框底部: 1px white/10
- 标题: 20px, font-weight 600
- 返回链接: 14px, zinc-500 → hover zinc-400
```

**影响范围:**
1. **前端架构**: 简化为多页面应用，无需窗口管理系统
2. **路由设计**: 使用 Vue Router，每个功能页独立路由
3. **组件设计**: 页面级组件，功能页面独立
4. **状态管理**: 使用 Vue 3 的 reactive() 和 provide/inject，管理用户状态

**原型文件位置:**
- `prototype/login.html` - 登录页原型
- `prototype/index.html` - 桌面主页原型
- `prototype/reports.html` - 报告列表原型
- `prototype/new-report.html` - 创建报告原型
- `prototype/templates.html` - 模板管理原型
- `prototype/analysts.html` - Analyst 管理原型
- `prototype/coverage.html` - Coverage 管理原型(占位)
- `prototype/sectors.html` - Sector 管理原型(占位)
- `prototype/regions.html` - Region 管理原型(占位)

---

### Decision 7.5: 前端性能优化原则

**原则:** 轻量、快速、零重型依赖

**具体要求:**

**1. 避免大型视觉库**
- ❌ 不使用 Three.js (600KB+)
- ❌ 不使用 PixiJS (400KB+)
- ❌ 不使用 Babylon.js (3MB+)
- ✅ 使用原生 Canvas API
- ✅ 使用 CSS 动画
- ✅ 使用 Vue 内置的 Transition 组件

**2. 代码分割**
- 按路由分割代码
- 页面组件懒加载
- 非首屏资源延迟加载

**3. 图片优化**
- 使用 WebP 格式
- 响应式图片
- 懒加载

**4. CSS 优化**
- 使用 Tailwind CSS 的 purge 功能
- 避免内联样式
- 使用 CSS containment

**5. 打包优化**
- Tree shaking
- 代码压缩
- Gzip/Brotli 压缩

**6. 运行时优化**
- 虚拟滚动 (长列表)
- 防抖/节流
- 使用 computed 缓存
- 避免不必要的响应式数据

**包大小目标:**
- 首屏 JS: < 200KB gzipped
- 完整应用: < 500KB gzipped

### Decision 8.5: 代码质量工具

**选择:** 使用现代化的 Python 和前端代码质量工具

**后端 (Python) 代码质量工具:**

**1. 代码格式化: Black**
```bash
# 安装
uv add black --group dev

# 配置 (pyproject.toml)
[tool.black]
line-length = 100
target-version = ['py311']
include = '\.pyi?$'

# 运行
uv run black backend/
uv run black --check backend/  # 仅检查,不修改
```

**2. 代码检查: Ruff (替代 flake8, pylint, isort)**
```bash
# 安装
uv add ruff --group dev

# 配置 (pyproject.toml)
[tool.ruff]
line-length = 100
target-version = "py311"
select = ["E", "F", "I", "N", "W", "UP"]
ignore = ["E501"]  # 行长度由 Black 处理

# 运行
uv run ruff check backend/
uv run ruff check --fix backend/  # 自动修复
```

**3. 类型检查: mypy**
```bash
# 安装
uv add mypy --group dev

# 配置 (pyproject.toml)
[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true

# 运行
uv run mypy backend/
```

**4. 测试: pytest + pytest-cov**
```bash
# 安装
uv add pytest pytest-cov --group dev

# 配置 (pyproject.toml)
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = "--cov=backend --cov-report=html --cov-report=term"

# 运行
uv run pytest
uv run pytest --cov=backend --cov-report=html
```

**5. Pre-commit Hooks**
```bash
# 安装
uv add pre-commit --group dev

# 配置 (.pre-commit-config.yaml)
repos:
  - repo: https://github.com/psf/black
    rev: 24.1.1
    hooks:
      - id: black
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.14
    hooks:
      - id: ruff
        args: [--fix]
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.8.0
    hooks:
      - id: mypy
        additional_dependencies: [types-all]

# 安装 hooks
pre-commit install

# 手动运行
pre-commit run --all-files
```

**前端 (Vue/TypeScript) 代码质量工具:**

**1. 代码格式化: Prettier**
```bash
# 安装
npm install -D prettier

# 配置 (.prettierrc)
{
  "semi": false,
  "singleQuote": true,
  "printWidth": 100,
  "trailingComma": "es5",
  "arrowParens": "avoid"
}

# 运行
npx prettier --write src/
npx prettier --check src/  # 仅检查
```

**2. 代码检查: ESLint**
```bash
# 安装
npm install -D eslint @typescript-eslint/parser @typescript-eslint/eslint-plugin eslint-plugin-vue

# 配置 (.eslintrc.cjs)
module.exports = {
  root: true,
  env: { browser: true, es2020: true },
  extends: [
    'eslint:recommended',
    'plugin:@typescript-eslint/recommended',
    'plugin:vue/vue3-recommended'
  ],
  parser: 'vue-eslint-parser',
  parserOptions: {
    ecmaVersion: 'latest',
    parser: '@typescript-eslint/parser'
  },
  rules: {
    'vue/multi-word-component-names': 'off',
    '@typescript-eslint/no-explicit-any': 'warn'
  }
}

# 运行
npx eslint src/
npx eslint --fix src/  # 自动修复
```

**3. 类型检查: TypeScript**
```bash
# 运行
npx vue-tsc --noEmit
```

**4. 组件测试: Vitest**
```bash
# 安装
npm install -D vitest @vue/test-utils

# 配置 (vitest.config.ts)
export default defineConfig({
  test: {
    environment: 'jsdom',
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html']
    }
  }
})

# 运行
npx vitest
npx vitest --coverage
```

**统一工具脚本:**

```json
// package.json (前端)
{
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview",
    "lint": "eslint src/",
    "lint:fix": "eslint --fix src/",
    "format": "prettier --write src/",
    "format:check": "prettier --check src/",
    "type-check": "vue-tsc --noEmit",
    "test": "vitest",
    "test:coverage": "vitest --coverage"
  }
}
```

```toml
# pyproject.toml (后端)
[project.scripts]
dev = "uvicorn backend.main:app --reload"
lint = "ruff check backend/"
lint:fix = "ruff check --fix backend/"
format = "black backend/"
format:check = "black --check backend/"
type-check = "mypy backend/"
test = "pytest"
test:cov = "pytest --cov=backend --cov-report=html"
```

**代码质量标准:**
- ✅ 所有代码必须通过 Black/Prettier 格式化
- ✅ 所有代码必须通过 Ruff/ESLint 检查
- ✅ 后端代码必须有类型注解 (通过 mypy 检查)
- ✅ 新功能必须有单元测试 (覆盖率目标 > 80%)
- ✅ Pre-commit hooks 必须安装并启用

### Decision 8.6: 开发规范和项目组织

**目的:** 建立统一的开发规范，确保代码质量和团队协作效率。

#### 界面和语言规范

**多语言使用原则:**
- **系统界面**: 英文（所有 UI 文本、按钮、菜单、标签）
- **API 响应消息**: 英文（成功、错误、验证提示）
- **数据库字段名**: 英文（所有表名、字段名、枚举值）
- **代码注释和文档**: 中文（便于团队理解和维护）
- **项目文档**: 中文（README、设计文档、API 文档）
- **报告内容**: 支持中英文双语（报告标题、摘要、正文）

**前端界面格式:**
```javascript
// 日期格式
const formatDate = (date) => 'YYYY-MM-DD'  // 2024-01-15

// 数字格式
const formatNumber = (num) => num.toLocaleString()  // 1,234.56

// 货币格式
const formatCurrency = (amount, currency) =>
  new Intl.NumberFormat('en-US', { style: 'currency', currency }).format(amount)
  // $1,234.56, ¥1,234.56
```

**后端 API 响应格式:**
```python
# 成功响应
{
    "success": true,
    "data": {...},
    "message": "Report created successfully",
    "error": null
}

# 错误响应
{
    "success": false,
    "data": null,
    "message": "Validation failed",
    "error": "Email already exists"
}
```

**数据库枚举值:**
```sql
-- 报告状态
'draft', 'submitted', 'published', 'rejected'

-- 用户角色
'analyst', 'sa', 'admin'

-- 报告类型
'Company', 'Sector', 'Company Flash', 'Sector Flash', 'Common'
```

#### 代码风格

**Python (后端) 代码规范:**
```bash
# 使用 UTF-8 编码
# -*- coding: utf-8 -*-

# 遵循 PEP 8 规范
# 最大行长度: 100 字符
# 使用类型注解
from typing import List, Optional
from datetime import datetime

def create_report(
    title: str,
    report_type: str,
    analyst_id: str,
    investment_thesis: Optional[str] = None
) -> Report:
    """
    创建新的研究报告

    Args:
        title: 报告标题
        report_type: 报告类型
        analyst_id: 分析师 ID
        investment_thesis: 投资论点（可选）

    Returns:
        创建的报告对象

    Raises:
        ValueError: 参数验证失败
    """
    pass
```

**TypeScript (前端) 代码规范:**
```typescript
// 使用 TypeScript 类型注解
interface Report {
  id: string
  title: string
  type: ReportType
  status: ReportStatus
  createdBy: string
  createdAt: Date
}

// 使用明确的返回类型
async function fetchReports(status?: ReportStatus): Promise<Report[]> {
  const params = status ? { status } : {};
  const response = await api.get('/reports', { params });
  return response.data;
}

// 使用可选链和空值合并
const analystName = report.analyst?.name ?? 'Unknown';
```

#### 文件组织原则

**项目目录结构:**
```
neolyst/
├── backend/                 # 后端代码
│   ├── api/                # API 路由
│   ├── models/             # 数据模型
│   ├── services/           # 业务逻辑
│   ├── core/               # 核心配置
│   │   ├── config.py       # 配置文件
│   │   ├── security.py     # 安全相关
│   │   └── database.py     # 数据库连接
│   └── main.py             # 应用入口
│
├── frontend/               # 前端代码
│   ├── src/
│   │   ├── views/          # 页面组件
│   │   ├── components/     # 可复用组件
│   │   ├── composables/    # Vue 组合式函数(状态管理)
│   │   ├── api/            # API 客户端
│   │   ├── types/          # TypeScript 类型
│   │   └── main.ts         # 应用入口
│   └── package.json
│
├── tests/                  # 测试代码
│   ├── test_api.py        # API 测试
│   ├── test_models.py     # 模型测试
│   └── test_services.py   # 服务测试
│
├── scripts/                # 工具脚本
│   ├── init_db.py         # 数据库初始化
│   ├── seed_data.py       # 种子数据
│   └── migrate.py         # 数据迁移
│
├── docs/                   # 文档
│   ├── api.md             # API 文档
│   └── deployment.md      # 部署文档
│
├── openspec/              # OpenSpec 文档
│   └── changes/
│
├── .env                   # 环境变量（不纳入版本控制）
├── .env.example          # 环境变量示例
├── .gitignore
├── README.md             # 项目说明（中文）
└── pyproject.toml        # Python 项目配置
```

**命名约定:**
```python
# 测试文件
test_report.py
test_analyst_service.py

# 工具脚本
init_db.py
seed_data.py
create_admin.py

# 文档
api.md
deployment.md
architecture.md
```

**❌ 避免在根目录:**
- ❌ test.py（临时测试文件）
- ❌ tmp.py（临时脚本）
- ❌ random_file.json（散乱文件）

#### 技术栈和依赖

**后端技术:**
```toml
# pyproject.toml
[project]
name = "neolyst"
requires-python = ">=3.14"  # 使用最新 Python 特性

dependencies = [
    "fastapi>=0.115.0",           # Web 框架
    "uvicorn[standard]>=0.32.0",  # ASGI 服务器
    "supabase>=2.27.3",           # Supabase Python 客户端
    "python-dotenv>=1.2.1",       # 环境变量管理
    "pydantic>=2.10.0",            # 数据验证
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.24.0",
    "pytest-cov>=6.0.0",
    "ruff>=0.8.0",
    "black>=24.0.0",
    "mypy>=1.14.0",
]
```

**前端技术:**
```json
// package.json
{
  "name": "neolyst-frontend",
  "type": "module",
  "dependencies": {
    "vue": "^3.5.0",
    "typescript": "^5.7.0",
    "@supabase/supabase-js": "^2.39.0",
    "vue-router": "^4.5.0",
    "pinia": "^2.2.0"
  },
  "devDependencies": {
    "vite": "^6.0.0",
    "eslint": "^9.0.0",
    "prettier": "^3.4.0"
  }
}
```

**后端服务:**
- **Supabase**: https://slxeorayantrboopghej.supabase.co
  - PostgreSQL 数据库
  - Supabase Auth（认证和授权）
  - Row Level Security (RLS)
  - 实时订阅和数据同步

#### 环境配置

**必需的环境变量:**
```bash
# .env 文件（不纳入版本控制）
SUPABASE_URL=https://slxeorayantrboopghej.supabase.co
SUPABASE_ANON_KEY=your_anon_key_here
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key_here  # 仅后端使用
DATABASE_URL=postgresql://...  # 可选，用于直接数据库访问

# 应用配置
APP_ENV=development  # development | production
LOG_LEVEL=INFO       # DEBUG | INFO | WARNING | ERROR
```

**环境变量示例:**
```bash
# .env.example
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_supabase_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
DATABASE_URL=your_database_url

APP_ENV=development
LOG_LEVEL=INFO
```

#### API 设计规范

**RESTful API 原则:**
```python
# 使用语义化的 URL 路径
GET    /api/v1/reports              # 获取报告列表
GET    /api/v1/reports/{id}         # 获取单个报告
POST   /api/v1/reports              # 创建报告
PUT    /api/v1/reports/{id}         # 更新报告
DELETE /api/v1/reports/{id}         # 删除报告

# 使用嵌套资源
GET    /api/v1/reports/{id}/versions      # 获取报告版本列表
POST   /api/v1/reports/{id}/submit       # 提交报告审核
POST   /api/v1/reports/{id}/approve      # 批准报告
POST   /api/v1/reports/{id}/reject       # 拒绝报告
```

**统一的响应格式:**
```python
# Pydantic 模型
from pydantic import BaseModel, Generic, TypeVar, Optional

T = TypeVar('T')

class ApiResponse(BaseModel, Generic[T]):
    success: bool
    data: Optional[T] = None
    message: str = ""
    error: Optional[str] = None

# 使用示例
@app.get("/api/v1/reports/{id}")
async def get_report(id: str) -> ApiResponse[ReportResponse]:
    report = await report_service.get_report(id)
    return ApiResponse(
        success=True,
        data=report,
        message="Report retrieved successfully"
    )
```

**错误处理:**
```python
from fastapi import HTTPException

# 使用 HTTPException
@app.post("/api/v1/reports")
async def create_report(report: ReportCreate):
    if not validate_ticker(report.ticker):
        raise HTTPException(
            status_code=400,
            detail="Invalid ticker symbol"
        )

    if await report_exists(report.title):
        raise HTTPException(
            status_code=409,
            detail="Report with this title already exists"
        )
```

#### 代码质量工具总结

**类型检查:**
- `mypy`: 静态类型检查，捕获类型错误

**单元测试:**
- `pytest`: 测试框架
- `pytest-asyncio`: 异步测试支持
- `pytest-cov`: 代码覆盖率
- 目标: 80%+ 覆盖率

**代码检查:**
- `ruff`: 快速的 Python linter（替代 flake8, pylint）
- `black`: 代码格式化
- 遵循 PEP 8 规范

**Pre-commit Hooks:**
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    rev: 24.1.1
    hooks:
      - id: black

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.14
    hooks:
      - id: ruff
        args: [--fix]

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.8.0
    hooks:
      - id: mypy
        additional_dependencies: [types-all]
```

#### 认证与授权

**Supabase Auth:**
- JWT Token 认证机制
- 用户角色存储在 `user_metadata` 和 `app_metadata` 中
- Row Level Security (RLS) 在数据库层面保护数据

**基于角色的访问控制 (RBAC):**
- **Analyst**: 只能访问自己创建的数据
- **SA**: 可以查看所有数据，可以审核
- **Admin**: 拥有所有权限，可以管理用户

#### 总结

**开发规范的核心原则:**
1. **代码质量**: 使用类型注解、单元测试、代码检查
2. **文件组织**: 清晰的目录结构，命名约定
3. **多语言策略**: 界面和 API 使用英文，文档和注释使用中文
4. **环境管理**: 使用 `.env` 文件，不纳入版本控制
5. **API 设计**: RESTful 原则，统一的响应格式
6. **权限控制**: Supabase Auth + RLS，数据库层面保护

---

### Decision 9: 用户角色和权限系统

**选择:** 使用 Supabase Auth + RLS (Row Level Security) 实现权限控制

**为什么选择 Supabase RLS:**
- ✅ 数据库层面的权限控制，更安全
- ✅ 自动过滤数据，无需应用层手动过滤
- ✅ 减少后端代码，权限控制逻辑在数据库中
- ✅ 性能更好，数据库直接过滤
- ✅ 防止应用层权限绕过

**三种角色定义:**

1. **Analyst(分析师)**
   - 创建和编辑自己的报告（包括已提交状态的报告）
   - 提交报告审核
   - 查看自己的所有报告(草稿/已提交/已发布/已拒绝)
   - 查看被拒绝报告的拒绝理由
   - 重新编辑被拒绝的报告

2. **SA(合规人员/Supervisor Analyst)**
   - 查看所有 Analyst 的报告
   - 审核已提交的报告
   - 批准或拒绝报告发布
   - 填写拒绝理由
   - 查看审核历史和统计
   - 不能创建或编辑报告

3. **Admin(系统管理员)**
   - 拥有所有权限
   - 管理基础数据(Analyst、Coverage、Sector、Region、Templates)
   - 查看和编辑所有报告
   - 替 Analyst 创建报告
   - 管理 Analyst 账号(创建、禁用、重置密码)
   - 充当 SA 角色，可以审核报告

**Supabase Auth 集成:**

1. **用户创建流程（带邮箱重复验证）:**
```python
# Admin 创建 Analyst 时
async def create_analyst(analyst_data: AnalystCreate):
    email = analyst_data.email

    # 1. 检查 analyst 表中是否已存在该邮箱
    existing_analyst = db.query(
        "SELECT * FROM analyst WHERE email = $1",
        email
    )

    if existing_analyst:
        raise HTTPException(
            status_code=400,
            detail=f"Email already exists for analyst: {existing_analyst['full_name']}"
        )

    # 2. 检查 Supabase Auth 中是否已存在该邮箱
    try:
        existing_users = supabase.auth.admin.list_users()
        auth_user_exists = any(
            user.email == email
            for user in existing_users.users
        )

        if auth_user_exists:
            # 数据不一致：Auth 有用户但 analyst 表没有
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Email exists in authentication system but no corresponding analyst record. "
                    f"Please contact system administrator to resolve data inconsistency."
                )
            )
    except Exception as e:
        # 如果无法查询 Auth 用户，继续创建（可能会失败，但让 Auth 返回错误）
        logger.warning(f"Failed to check Auth users: {e}")

    # 3. 在 analyst 表中创建记录
    analyst = db.insert(analyst_data)

    # 4. 在 Supabase Auth 中创建用户
    try:
        created_user = supabase.auth.admin.create_user({
            'email': analyst_data.email,
            'password': generate_default_password(),  # 如: analyst123
            'email_confirm': True,
            'user_metadata': {
                'role': analyst_data.role,  # 'analyst', 'sa', 'admin'
            },
            'app_metadata': {
                'provider': 'email',
                'role': analyst_data.role,
                'analyst_id': str(analyst.id)
            }
        })
    except Exception as auth_error:
        # 如果 Auth 创建失败，删除 analyst 记录（回滚）
        db.delete("analyst", analyst.id)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create authentication user: {str(auth_error)}"
        )

    # 5. 发送欢迎邮件(包含默认密码)
    try:
        password = generate_default_password()
        send_welcome_email(analyst_data.email, password)
    except Exception as email_error:
        # 邮件发送失败不影响创建，只记录警告
        logger.warning(f"Failed to send welcome email: {email_error}")

    return analyst
```

2. **角色信息存储:**
   - Supabase Auth 的 `user_metadata` 和 `app_metadata` 存储 `role` 和 `analyst_id`
   - 登录后 JWT token 包含角色信息
   - RLS policies 使用 `auth.jwt()->>'app_metadata'->>'role'` 获取当前用户角色

**数据库设计 (启用 RLS):**

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

-- 启用 RLS
ALTER TABLE analyst ENABLE ROW LEVEL SECURITY;
ALTER TABLE report ENABLE ROW LEVEL SECURITY;
ALTER TABLE coverage ENABLE ROW LEVEL SECURITY;
ALTER TABLE sector ENABLE ROW LEVEL SECURITY;
ALTER TABLE region ENABLE ROW LEVEL SECURITY;
ALTER TABLE template ENABLE ROW LEVEL SECURITY;
```

**RLS Policies (报告权限控制):**

```sql
-- 辅助函数：获取当前用户 ID 和角色
CREATE OR REPLACE FUNCTION get_current_analyst_id()
RETURNS UUID AS $$
  SELECT (auth.jwt()->>'analyst_id')::UUID;
$$ LANGUAGE sql SECURITY DEFINER;

CREATE OR REPLACE FUNCTION get_current_role()
RETURNS VARCHAR AS $$
  SELECT (auth.jwt()->>'app_metadata'->>'role')::VARCHAR;
$$ LANGUAGE sql SECURITY DEFINER;

-- Report 表的 RLS Policies

-- 1. 所有认证用户都可以查看报告（根据角色过滤）
CREATE POLICY "Reports can be viewed by authenticated users"
ON report FOR SELECT
USING (true);  -- 具体过滤在下面

-- 2. Analyst 只能查看自己创建的报告
CREATE POLICY "Analysts can view own reports"
ON report FOR SELECT
TO authenticated
USING (
  get_current_role() = 'analyst'
  AND created_by = get_current_analyst_id()
);

-- 3. SA 和 Admin 可以查看所有报告
CREATE POLICY "SA and Admin can view all reports"
ON report FOR SELECT
TO authenticated
USING (
  get_current_role() IN ('sa', 'admin')
);

-- 4. Analyst 只能插入自己的报告 (created_by 自动设置)
CREATE POLICY "Analysts can insert own reports"
ON report FOR INSERT
TO authenticated
WITH CHECK (
  get_current_role() = 'analyst'
  AND created_by = get_current_analyst_id()
);

-- 5. Admin 可以为任何 Analyst 插入报告
CREATE POLICY "Admin can insert reports for any analyst"
ON report FOR INSERT
TO authenticated
WITH CHECK (get_current_role() = 'admin');

-- 6. Analyst 只能更新自己的报告（草稿和已提交状态）
CREATE POLICY "Analysts can update own reports"
ON report FOR UPDATE
TO authenticated
USING (
  get_current_role() = 'analyst'
  AND created_by = get_current_analyst_id()
  AND status IN ('draft', 'submitted')  -- 允许编辑草稿和已提交的报告
)
WITH CHECK (
  status IN ('draft', 'submitted')  -- 保持状态不变
  OR (status = 'draft' AND created_by = get_current_analyst_id())  -- 允许从草稿提交
);

-- 7. Admin 可以更新任何报告
CREATE POLICY "Admin can update any report"
ON report FOR UPDATE
TO authenticated
USING (get_current_role() = 'admin')
WITH CHECK (true);

-- 8. SA 不能更新任何报告
-- (没有 policy = 不能更新)

-- 9. SA 和 Admin 可以审核报告（更新 status 为 published/rejected）
CREATE POLICY "SA and Admin can review reports"
ON report FOR UPDATE
TO authenticated
USING (
  get_current_role() IN ('sa', 'admin')
  AND status = 'submitted'
)
WITH CHECK (
  status IN ('published', 'rejected')
  AND (
    (status = 'published' AND published_by = get_current_analyst_id())
    OR (status = 'rejected' AND rejected_by = get_current_analyst_id())
  )
);
```

**RLS Policies (基础数据权限):**

```sql
-- Analyst 表 (Admin only)
CREATE POLICY "Only Admin can manage analysts"
ON analyst FOR ALL
TO authenticated
USING (get_current_role() = 'admin')
WITH CHECK (get_current_role() = 'admin');

-- 但所有用户都可以查看 Analyst 信息（用于下拉选择等）
CREATE POLICY "All users can view analysts"
ON analyst FOR SELECT
TO authenticated
USING (true);

-- Coverage, Sector, Region 表 (所有认证用户可读，Admin 可写)
CREATE POLICY "All users can view base data"
ON coverage FOR SELECT
TO authenticated
USING (true);

CREATE POLICY "Only Admin can modify base data"
ON coverage FOR ALL
TO authenticated
USING (get_current_role() = 'admin')
WITH CHECK (get_current_role() = 'admin');

-- 对 Sector, Region 应用相同的策略

-- Template 表 (所有认证用户可读可下载，Admin 可写可删除)
CREATE POLICY "All users can view templates"
ON template FOR SELECT
TO authenticated
USING (true);

CREATE POLICY "Only Admin can manage templates"
ON template FOR ALL
TO authenticated
USING (get_current_role() = 'admin')
WITH CHECK (get_current_role() = 'admin');
```

**后端 API 简化 (使用 RLS):**

```python
# 邮箱检查 API (Admin only，在创建 Analyst 前验证)
@router.get("/api/analysts/check-email")
async def check_analyst_email(
    email: str,
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    检查邮箱是否可用于创建 Analyst

    Returns:
        {
            "available": bool,      # 邮箱是否可用
            "exists_in_db": bool,    # 是否在 analyst 表中存在
            "exists_in_auth": bool,  # 是否在 Supabase Auth 中存在
            "message": str           # 提示信息
        }
    """
    # 检查 analyst 表
    existing_analyst = db.query(
        "SELECT id, full_name FROM analyst WHERE email = $1",
        email
    )
    exists_in_db = len(existing_analyst) > 0

    # 检查 Supabase Auth
    exists_in_auth = False
    try:
        users = supabase.auth.admin.list_users()
        exists_in_auth = any(user.email == email for user in users.users)
    except Exception as e:
        logger.warning(f"Failed to check Auth: {e}")

    # 判断并返回结果
    if exists_in_db:
        return {
            "available": False,
            "exists_in_db": True,
            "exists_in_auth": False,
            "message": f"Email already exists for analyst: {existing_analyst[0]['full_name']}"
        }
    elif exists_in_auth:
        return {
            "available": False,
            "exists_in_db": False,
            "exists_in_auth": True,
            "message": "Email exists in authentication system but no corresponding analyst record. Please recover or use different email."
        }
    else:
        return {
            "available": True,
            "exists_in_db": False,
            "exists_in_auth": False,
            "message": "Email is available"
        }

# 无需手动过滤数据，RLS 自动处理
@router.get("/api/reports")
async def list_reports():
    # RLS 自动根据角色过滤：
    # - Analyst: 只能看到 created_by = 自己的报告
    # - SA/Admin: 可以看到所有报告
    reports = db.query("SELECT * FROM report")  # 简单查询即可
    return reports

@router.post("/api/reports")
async def create_report(
    report_data: ReportCreate,
    current_user: CurrentUser = Depends(get_current_user)
):
    # Admin 创建时可以指定 created_for_analyst_id
    # RLS 会检查权限
    if current_user.role == 'admin' and report_data.created_for_analyst_id:
        created_by = report_data.created_for_analyst_id
    else:
        created_by = current_user.id

    report = db.create_report(
        **report_data.dict(exclude={'created_for_analyst_id'}),
        created_by=created_by,
        status='draft'
    )
    return report

@router.put("/api/reports/{id}")
async def update_report(
    id: str,
    report_data: ReportUpdate,
):
    # RLS 自动检查：
    # - Analyst: 只能更新 status IN ('draft', 'submitted') 且 created_by=自己的报告
    # - SA: 不能更新（没有 policy）
    # - Admin: 可以更新任何报告
    report = db.update_report(id, report_data)
    return report

@router.post("/api/reports/{id}/submit")
async def submit_report(id: str, current_user: CurrentUser = Depends(get_current_user)):
    # RLS 会检查 Analyst 是否拥有该报告
    report = db.update_report_status(
        id,
        status='submitted',
        submitted_at=datetime.now(),
        submitted_by=current_user.id
    )
    return report
```

**报告审核 API (使用 RLS):**

```python
@router.get("/api/reports/submitted")
async def list_submitted_reports():
    # RLS 自动限制只有 SA/Admin 可以访问
    # 通过查询过滤待审核报告
    reports = db.query(
        "SELECT * FROM report WHERE status = 'submitted'"
    )
    return reports

@router.post("/api/reports/{id}/approve")
async def approve_report(
    id: str,
    current_user: CurrentUser = Depends(get_current_user)
):
    # RLS 检查：只有 SA/Admin 可以更新 status='submitted' 的报告
    updated = db.update_report_status(
        id,
        status='published',
        published_at=datetime.now(),
        published_by=current_user.id
    )

    # 发送邮件通知 Analyst
    send_approval_email(...)

    return updated

@router.post("/api/reports/{id}/reject")
async def reject_report(
    id: str,
    reason: str,
    current_user: CurrentUser = Depends(get_current_user)
):
    # RLS 检查：只有 SA/Admin 可以更新 status='submitted' 的报告
    updated = db.update_report_status(
        id,
        status='rejected',
        rejected_at=datetime.now(),
        rejected_by=current_user.id,
        rejection_reason=reason
    )

    # 发送邮件通知 Analyst
    send_rejection_email(...)

    return updated
```

**前端权限控制 (简化):**

```typescript
// stores/user.ts
interface UserState {
  id: string
  role: 'analyst' | 'sa' | 'admin'
  email: string
  name: string
}

// 权限检查函数 (主要用于 UI 控制，实际权限由 RLS 保证)
const can = {
  editReport: (user: User, report: Report) => {
    if (user.role === 'sa') return false
    if (user.role === 'admin') return true
    return user.role === 'analyst' && report.created_by === user.id && report.status === 'draft'
  },

  accessReviewPage: (user: User) => {
    return user.role === 'sa' || user.role === 'admin'
  },

  createForAnalyst: (user: User) => {
    return user.role === 'admin'
  },

  manageAnalysts: (user: User) => {
    return user.role === 'admin'
  }
}

// 路由守卫
router.beforeEach((to, from, next) => {
  const user = useUserStore()
  if (to.meta.requiresRole && !can[to.meta.permission](user)) {
    next('/desktop')
  } else {
    next()
  }
})
```

**RLS 安全优势:**

1. **数据库层面控制**：即使应用层代码有漏洞，RLS 也能保护数据
2. **自动过滤**：无需手动编写过滤逻辑
3. **性能优化**：数据库直接过滤，减少网络传输
4. **简化代码**：后端 API 代码更简洁
5. **审计友好**：所有权限控制逻辑集中在数据库中

**注意事项:**

1. **RLS 不能完全替代应用层检查**：
   - UI 层仍需要权限检查来显示/隐藏按钮
   - 业务逻辑层需要检查权限来提供友好的错误提示

2. **使用 SECURITY DEFINER 函数**：
   - 某些操作需要提升权限（如发送邮件）
   - 使用 `SECURITY DEFINER` 函数绕过 RLS

3. **测试 RLS Policies**：
   - 需要针对每种角色测试 RLS policies
   - 确保 policies 正确且没有漏洞

4. **性能监控**：
   - 复杂的 RLS policies 可能影响查询性能
   - 需要在生产环境监控和优化

**前端界面设计:**

**桌面功能卡片调整:**
```
【报告功能组 - 上方】
├── 📝 Reports          - View my reports (Analyst) / View all reports (SA/Admin)
├── ➕ New Report       - Create new report
├── ✅ Report Review    - Review submitted reports (SA/Admin only)
└── 📄 Templates        - View and download templates (All users) / Manage templates (Admin only)

【基础数据管理组 - 下方】
├── 👤 Analysts         - Analyst management (Admin only)
├── 🏢 Coverage         - Company coverage management
├── 🏗️ Sectors          - Industry classification management
└── 🌍 Regions          - Region management
```

**新建报告页面 (Admin 特有功能):**
```html
<!-- Admin 创建报告时显示 Analyst 选择器 -->
<div class="form-group" v-if="user.role === 'admin'">
  <label class="form-label">Create for Analyst *</label>
  <select class="form-select" v-model="formData.created_for_analyst_id" required>
    <option value="">Select an analyst...</option>
    <option v-for="analyst in analysts" :value="analyst.id">
      {{ analyst.full_name }} ({{ analyst.email }})
    </option>
  </select>
</div>
```

**报告审核页面设计:**
```
┌─────────────────────────────────────────────────────────────┐
│ ✅ Report Review                            ← Back to Desktop │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  📊 Review Statistics                                      │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Pending Review: 12  |  Reviewed Today: 8          │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  [Filters]                                                  │
│  Type: [All▼]  Analyst: [All▼]  Search: [_______]          │
│                                                             │
│  📋 Pending Reports (12)                                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 📄 AAPL Stock Analysis                  [Review]    │   │
│  │    Company | John Doe | Submitted 2h ago           │   │
│  ├─────────────────────────────────────────────────────┤   │
│  │ 📄 TSLA Investment Rating               [Review]    │   │
│  │    Company | Jane Smith | Submitted 5h ago         │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**报告审核详情页:**
```
┌─────────────────────────────────────────────────────────────┐
│ ✅ Review Report: AAPL Stock Analysis                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Report Information:                                        │
│  - Type: Company                                           │
│  - Analyst: John Doe                                       │
│  - Submitted: 2 hours ago                                  │
│  - Ticker: AAPL                                            │
│  - Rating: Buy                                             │
│  - Target Price: $250                                      │
│                                                             │
│  📄 Word Document: [Preview] [Download]                     │
│  📊 Excel Model: [Download]                                │
│                                                             │
│  [Approve & Publish]  [Reject with Reason]                 │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

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

**邮件通知模板:**

1. **账号创建通知:**
```
Subject: Your Neolyst Account Has Been Created

Dear {{ analyst_name }},

Your Neolyst account has been created successfully.

Login URL: https://neolyst.example.com/login
Email: {{ email }}
Temporary Password: {{ temporary_password }}

Please change your password after first login.

Best regards,
Neolyst Admin
```

2. **报告批准通知:**
```
Subject: Your Report Has Been Published

Dear {{ analyst_name }},

Your report "{{ report_title }}" has been approved and published.

Approved by: {{ sa_name }}
Approved at: {{ approved_at }}

You can view the published report at:
{{ report_url }}

Congratulations!
```

3. **报告拒绝通知:**
```
Subject: Your Report Has Been Rejected

Dear {{ analyst_name }},

Your report "{{ report_title }}" has been rejected.

Rejected by: {{ sa_name }}
Rejected at: {{ rejected_at }}
Reason: {{ rejection_reason }}

You can view the rejection reason and make changes at:
{{ report_url }}

Please re-edit the report and submit it again when ready.
```

---
- 使用 Email + Password 登录
- JWT Token 存储在 localStorage
- API 请求携带 Authorization header

**注意:** 报告查看网站是独立系统,由其他项目负责,本系统仅提供已发布报告的数据接口。

### Decision 10: 已发布报告的对外接口

**设计:** 为外部系统提供已发布报告的查询接口

**实现:**
- SA 批准发布报告时,报告状态变为 `published`
- 记录 `published_at` 和 `published_by`(SA)
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
      "published_by": "sa_name",
      "basic_info": { ... },  # 报告基本信息
      "word_file_url": "https://...",  # Word 文件下载链接
      "model_file_url": "https://..."  # Excel 文件下载链接(如有)
    }
  ],
  "last_updated": "2024-01-01T00:00:00Z"
}
```

**注意:** 独立的报告查看网站由另一个项目负责,本项目仅提供数据接口。
