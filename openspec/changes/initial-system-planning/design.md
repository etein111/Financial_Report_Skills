# 系统设计文档

## Context

这是投资研究报告管理系统的第一个版本(MVP)。系统主要服务于券商内部使用,由系统管理员统一操作,负责管理研究报告的创建、编辑、版本控制和发布流程。

第二个版本将开发独立的报告查看网站,因此第一个版本需要为未来集成预留接口。

## Goals / Non-Goals

**Goals:**
- 实现完整的基础数据管理(Analyst、Coverage、Sector、Region、报告模板 Word/Excel)
- 实现报告的创建、编辑、版本管理功能
- 实现报告发布和拒绝流程
- 确保所有修改都有完整的审计追踪(修改人、修改时间)
- 为未来版本预留扩展接口(发布后的报告复制到独立网站)

**Non-Goals:**
- 多角色权限系统(第一个版本只有系统管理员)
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

**选择:** Vue 3 + Composition API + Pinia + Tailwind CSS + Headless UI

**理由:**
- **Vue 3 Composition API**: 更好的类型推断,代码组织更灵活
- **Pinia**: 官方推荐的状态管理库,比 Vuex 更简洁
- **Tailwind CSS**: 实用优先的 CSS 框架,完美实现深色主题和定制化设计
- **Headless UI (Vue)**: 无样式的可访问组件,与 Tailwind 完美配合
- **不使用 Element Plus**: 为了完全控制视觉设计,使用 Headless UI + 自定义组件

**界面设计模式: 桌面式界面 + 窗口化操作**

与传统 Web 应用不同,本系统采用仿操作系统的桌面式界面:

1. **无全局导航条**: 没有传统的侧边栏或顶部导航栏
2. **仿系统桌面**: 登录后进入类似 Windows/macOS 的桌面环境
3. **功能卡片平铺**: 各功能模块以带图标的卡片形式展示在桌面上
4. **窗口化操作**: 点击功能卡片打开可拖动、可调整大小的窗口
5. **无返回按钮**: 窗口直接关闭,不需要返回按钮

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

**3. 窗口 (Windows):**
```css
/* 背景: zinc-900 */
/* 边框: 1px white/10 */
/* 标题栏: zinc-800, 48px height */
/* 内容区: zinc-950 background */
/* 圆角: 8px (rounded-lg) */
box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5)
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

**窗口内容布局规范:**

**1. 报告列表窗口 (Report List Window):**
```
┌─────────────────────────────────────────┐
│ 📝 Reports                  [_][□][×] │  ← 标题栏 (zinc-800)
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

**2. 基础数据管理窗口 (Data Management Windows):**
```
┌─────────────────────────────────────────┐
│ 👤 Analysts                 [_][□][×] │
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
│ ➕ New Report                [_][□][×] │
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
在报告编辑窗口右侧或底部显示:

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

**响应式断点 (Responsive Breakpoints):**
```css
/* 窗口最小尺寸 */
min-width: 800px
min-height: 600px

/* 窗口默认尺寸 */
- 报告列表: 1200px × 800px
- 基础数据管理: 1000px × 700px
- 报告创建/编辑: 1000px × 800px
```
```

**交互设计:**
```
登录页
  ↓
桌面 (Desktop.vue)
  ├── 功能卡片 (图标 + 名称) - 分组显示,所有文本使用英文
  │
  │   【报告功能组 - 上方】
  │   ├── 📝 Reports          - View all reports
  │   ├── ➕ New Report       - Create new report
  │   └── 📄 Templates        - Report template management (Word/Excel)
  │
  │   【基础数据管理组 - 下方】
  │   ├── 👤 Analysts         - Analyst information management
  │   ├── 🏢 Coverage         - Company coverage management
  │   ├── 🏗️ Sectors          - Industry classification management
  │   └── 🌍 Regions          - Region management
  │
  └── 任务栏 (Taskbar.vue)
      ├── 开始菜单 (可选)
      ├── 已打开窗口列表
      └── 系统托盘 (时间、通知等)
```

**桌面布局设计:**
- 功能卡片分为两个组,使用视觉分隔(卡片组标题、间距或背景色区分)
- 报告功能组放在上方,因为这是最常用的核心功能
- 基础数据管理组放在下方,作为配置类功能
- 每个卡片包含: 图标 + 英文功能名称 + 简短描述(可选)
- 卡片支持悬停效果,点击打开对应窗口
- **界面语言**: 所有 UI 文本使用英文(按钮、标签、菜单等)

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
│   ├── Login.vue              # 登录页 (带粒子效果背景)
│   │   # - 使用 ParticleBackground 组件
│   │   # - 标语"The Future is Here"
│   │   # - 登录表单(英文界面)
│   ├── Desktop.vue            # 桌面主界面
│   └── windows/               # 窗口化功能页
│       ├──报告管理/
│       │   ├── ReportListWindow.vue       # 报告列表
│       │   ├── ReportCreateWindow.vue     # 创建报告
│       │   ├── ReportEditWindow.vue       # 编辑报告
│       │   └── TemplateWindow.vue         # 报告模板管理 (Word/Excel)
│       └──基础数据管理/
│           ├── AnalystWindow.vue          # Analyst 管理
│           ├── CoverageWindow.vue         # Coverage 管理
│           ├── SectorWindow.vue           # Sector 管理
│           └── RegionWindow.vue           # Region 管理
├── components/
│   ├── window/                # 窗口系统组件
│   │   ├── WindowContainer.vue     # 窗口容器(支持拖动、调整大小)
│   │   ├── WindowHeader.vue        # 窗口标题栏
│   │   └── WindowManager.vue       # 窗口管理器
│   ├── desktop/               # 桌面组件
│   │   ├── DesktopIcon.vue         # 桌面图标卡片
│   │   ├── DesktopCardGroup.vue    # 卡片组容器(带标题和分隔)
│   │   └── Taskbar.vue             # 任务栏
│   └── common/                 # 通用组件
│       ├── ParticleBackground.vue  # 粒子背景组件
│       └── Icon.vue                # 图标组件
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
- 窗口组件懒加载
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
- 单个窗口组件: < 50KB gzipped

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

### Decision 9: 认证和授权

**选择:** 使用 Supabase Auth

**实现:**
- 第一个版本只有系统管理员角色
- 使用 Email + Password 登录
- JWT Token 存储在 localStorage
- API 请求携带 Authorization header

**未来扩展:**
- 第二个版本将添加 Analyst、研究主管、SA 等角色
- 使用 Supabase RLS(Row Level Security)实现数据权限控制

### Decision 11: 已发布报告的对外接口

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
