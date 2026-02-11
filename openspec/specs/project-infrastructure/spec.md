# 项目基础设施规范

本文档定义 Neolyst 项目的基础技术架构和目录结构规范。

## 变更历史

**注意：** 本规范已根据 `auth-and-user-management` 变更进行更新，与设计文档保持一致。

---

## 后端架构

### Requirement: 后端项目结构

系统 SHALL 创建符合 FastAPI 标准的后端项目结构。

#### Scenario: 后端目录结构

- **WHEN** 开发者查看项目根目录
- **THEN** `backend/` 目录必须存在
- **AND** `backend/pyproject.toml` 文件必须存在
- **AND** `backend/src/` 目录必须存在
- **AND** `backend/src/main.py` 文件必须存在

**目录结构：**
```
backend/
├── src/
│   ├── main.py                 # FastAPI 应用入口
│   ├── api/                    # API 路由
│   │   ├── __init__.py
│   │   ├── auth.py              # 认证相关 API
│   │   ├── users.py            # 用户管理 API
│   │   ├── regions.py          # Region 管理 API
│   │   └── analyst_info.py    # Analyst 信息管理 API
│   ├── core/                   # 核心配置
│   │   ├── __init__.py
│   │   ├── config.py            # 配置（环境变量等）
│   │   ├── security.py          # JWT 验证等安全相关
│   │   └── supabase.py         # Supabase 客户端初始化
│   ├── models/                 # Pydantic 数据模型
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── user.py
│   │   ├── region.py
│   │   └── analyst.py
│   └── db/                    # 数据库操作（直接使用 Supabase Client）
│       └── __init__.py
├── scripts/
│   └── init_admin.py         # 初始化 Admin 脚本
├── .env.example
└── pyproject.toml
```

#### Scenario: 后端虚拟环境可创建

- **WHEN** 开发者在 `backend/` 目录运行 `uv sync`
- **THEN** `.venv/` 目录必须在 `backend/` 内创建
- **AND** FastAPI 和相关依赖必须安装成功
- **AND** 运行 `uv run python -c "import fastapi"` 必须成功

**理由：** 使用 uv 进行依赖管理，比传统 pip + virtualenv 更现代和高效。

---

## 前端架构

### Requirement: 前端项目结构

系统 SHALL 创建符合 Vue 3 和 Vite 标准的前端项目结构。

#### Scenario: 前端目录结构

- **WHEN** 开发者查看项目根目录
- **THEN** `frontend/` 目录必须存在
- **AND** `frontend/package.json` 文件必须存在
- **AND** `frontend/src/` 目录必须存在
- **AND** `frontend/src/main.ts` 文件必须存在

**目录结构：**
```
frontend/
├── src/
│   ├── main.ts               # 应用入口
│   ├── App.vue              # 根组件
│   ├── assets/              # 静态资源
│   │   └── styles/
│   │       └── main.css
│   ├── api/                 # API 调用
│   │   └── client.ts
│   ├── components/           # 可复用组件
│   │   ├── common/
│   │   │   └── ParticleBackground.vue
│   │   └── desktop/
│   │       └── DesktopCard.vue
│   ├── composables/         # 组合式函数
│   │   └── usePermission.ts
│   ├── views/               # 页面组件
│   │   ├── Login.vue
│   │   ├── Desktop.vue
│   │   ├── ComingSoon.vue
│   │   ├── RegionsPage.vue
│   │   └── AnalystInfoPage.vue
│   ├── stores/              # 状态管理
│   │   └── auth.ts
│   └── router/             # 路由配置
│       └── index.ts
├── .env.example
├── index.html
├── package.json
├── tailwind.config.js
└── vite.config.ts
```

#### Scenario: 前端开发服务器可启动

- **WHEN** 开发者在 `frontend/` 目录运行 `npm install`
- **THEN** `node_modules/` 目录必须创建
- **AND** 运行 `npm run dev` 必须成功启动开发服务器

---

## 环境配置

### Requirement: 环境配置模板

系统 SHALL 提供环境变量模板文件以指导开发者配置。

#### Scenario: 环境变量模板存在

- **WHEN** 开发者查看项目根目录
- **THEN** 后端 `.env.example` 文件必须存在
- **AND** 前端 `.env.example` 文件必须存在
- **AND** 文件必须包含 Supabase URL 和 key 的占位符
- **AND** 文件必须包含必要的注释说明

**后端 `.env.example` 模板：**
```bash
# Supabase 配置
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# 应用配置
APP_ENV=development
DEBUG=false
```

**前端 `.env.example` 模板：**
```bash
# API 地址
VITE_API_URL=http://localhost:8000
```

---

## 样式配置

### Requirement: Tailwind CSS 配置

前端项目 SHALL 配置 Tailwind CSS 以匹配原型设计。

#### Scenario: Tailwind 依赖已安装

- **WHEN** 开发者查看 `frontend/package.json`
- **THEN** `tailwindcss` 必须在依赖列表中
- **AND** `autoprefixer` 和 `postcss` 必须在依赖列表中

#### Scenario: Tailwind 配置文件存在

- **WHEN** 开发者查看 `frontend/` 目录
- **THEN** `tailwind.config.js` 文件必须存在
- **AND** 配置必须匹配原型的颜色和字体设置

**参考配置：**
```javascript
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // 根据原型设计定义颜色
      },
      fontFamily: {
        // 根据原型设计定义字体
      }
    }
  },
  plugins: [],
}
```

---

## API 设计规范

### Requirement: RESTful API 设计

所有 API 端点 SHALL 遵循 RESTful 设计原则。

**命名规范：**
- 资源使用复数名词：`/api/users`, `/api/regions`, `/api/analyst-info`
- HTTP 方法语义化：GET（查询）、POST（创建）、PUT（更新）、DELETE（删除）

**响应格式：**
```json
{
  "success": true/false,
  "message": "操作描述",
  "data": { ... },
  "error": "错误详情（如果失败）"
}
```

---

## 安全规范

### Requirement: 认证和授权

系统 SHALL 实现基于 JWT Token 的认证和基于角色的权限控制（RBAC）。

**认证流程：**
1. 用户调用 `POST /api/auth/login` 获取 Token
2. 前端在后续请求的 Authorization header 中携带 Token
3. Token 有效期为 24 小时
4. Token 过期后前端自动跳转登录页

**角色定义：**
- `admin` - 系统管理员，完全权限
- `sa` - 高级分析师，预留用于报告审核
- `analyst` - 普通分析师，只读权限

**权限控制层级：**
- 数据库层：Supabase RLS policies
- API 层：中间件验证角色
- 前端层：路由守卫和权限检查函数

---

## 版本控制规范

### Requirement: Git 提交规范

提交信息 SHOULD 遵循 Conventional Commits 规范。

**提交格式：**
```
<type>(<scope>): <subject>

<body>

<footer>
```

**类型（type）：**
- `feat`: 新功能
- `fix`: Bug 修复
- `docs`: 文档更新
- `refactor`: 代码重构
- `test`: 测试相关
- `chore`: 构建/工具链更新

**示例：**
```
feat(auth): implement user login and JWT authentication
feat(users): add user management API with CRUD operations
fix(auth): resolve token expiration handling issue
docs(readme): update setup instructions
```

---

## 变更管理

### Requirement: OpenSpec 工作流

开发工作 SHALL 使用 OpenSpec 进行变更管理。

**工作流程：**
1. 使用 `/opsx:new` 创建新变更
2. 在变更中生成 proposal、design、tasks 等 artifact
3. 实施完成后使用 `/opsx:verify` 验证实现
4. 使用 `/opsx:archive` 归档完成的变更

**变更状态：**
- `proposed` - 提案阶段
- `in-progress` - 实施中
- `completed` - 已完成
- `archived` - 已归档

---

## 依赖管理

### Requirement: 后端依赖管理

后端使用 **uv** 进行 Python 依赖管理和虚拟环境管理。

**常用命令：**
```bash
# 安装依赖
uv sync

# 运行应用
uv run python -m uvicorn src.main:app --reload

# 安装新依赖
uv add <package-name>

# 更新依赖
uv sync
```

**核心依赖（pyproject.toml）：**
```toml
[project]
name = "neolyst-backend"
version = "0.1.0"
requires-python = ">=3.11"

dependencies = [
    "fastapi>=0.104.0",
    "uvicorn[standard]>=0.24.0",
    "supabase>=2.0.0",
    "pydantic>=2.0.0",
    "python-dotenv>=1.0.0",
    "python-jose[cryptography]>=3.3.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

### Requirement: 前端依赖管理

前端使用 **npm** 进行 Node.js 依赖管理。

**核心依赖（package.json）：**
```json
{
  "name": "neolyst-frontend",
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "vue": "^3.4.0",
    "vue-router": "^4.2.0",
    "axios": "^1.6.0",
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^5.0.0",
    "vite": "^5.0.0",
    "tailwindcss": "^3.4.0",
    "autoprefixer": "^10.4.0",
    "postcss": "^8.4.0"
  }
}
```
