# Neolyst

投资研究报告管理系统 - 基于 Web 的报告创建、审核和发布平台。

## 项目概述

Neolyst 是一个集中化的系统,用于管理投资研究报告的创建、编辑、版本控制、审核和发布流程。系统支持多角色权限管理(Analyst、SA、Admin)和工作流审批。

### 技术栈

**后端:**
- Python + FastAPI
- uv (包管理和虚拟环境)
- Supabase (认证、数据库、存储)

**前端:**
- Vue 3 + TypeScript
- Vite (构建工具)
- Tailwind CSS (样式框架)
- Axios (HTTP 客户端)

## 快速开始

### 前置要求

- Python 3.11+
- Node.js 18+
- uv (Python 包管理器)
- Supabase 账号

### 1. 环境配置

复制环境变量模板并填入你的 Supabase 配置:

```bash
cp .env.example .env
```

编辑 `.env` 文件,填入以下信息:
- `SUPABASE_URL`: 你的 Supabase 项目 URL
- `SUPABASE_ANON_KEY`: Supabase 公开密钥
- `SUPABASE_SERVICE_ROLE_KEY`: Supabase 服务端密钥

### 2. 后端启动

```bash
# 进入后端目录
cd backend

# 安装依赖(首次运行)
uv sync

# 启动开发服务器
uv run uvicorn app.main:app --reload --port 8000
```

后端 API 将运行在 `http://localhost:8000`

查看 API 文档: `http://localhost:8000/docs`

### 3. 前端启动

```bash
# 进入前端目录
cd frontend

# 安装依赖(首次运行)
npm install

# 启动开发服务器
npm run dev
```

前端将运行在 `http://localhost:5173`

## 项目结构

```
neolyst/
├── backend/           # 后端 FastAPI 应用
│   ├── app/          # 应用代码
│   ├── pyproject.toml # 项目配置
│   └── .venv/        # Python 虚拟环境(本地)
├── frontend/         # 前端 Vue 应用
│   ├── src/         # 源代码
│   └── package.json # 项目配置
├── prototype/       # HTML 原型设计
├── openspec/        # OpenSpec 规划文档
└── .env.example     # 环境变量模板
```

## 开发工具

### 后端常用命令

```bash
cd backend

# 安装依赖
uv sync

# 运行开发服务器
uv run uvicorn app.main:app --reload

# 添加新依赖
uv add <package-name>

# 运行脚本
uv run <command>
```

### 前端常用命令

```bash
cd frontend

# 安装依赖
npm install

# 运行开发服务器
npm run dev

# 构建生产版本
npm run build

# 预览生产构建
npm run preview
```

## 开发指南

### 代码风格

- 所有代码注释使用中文
- 遵循 PEP 8 (Python) 和官方风格指南 (Vue/TypeScript)
- 使用有意义的变量和函数名

### 提交规范

使用清晰的提交信息描述你的更改:

```
feat: 添加报告创建功能
fix: 修复权限检查问题
docs: 更新 README
```

## 许可证

Copyright © 2025 Neolyst
