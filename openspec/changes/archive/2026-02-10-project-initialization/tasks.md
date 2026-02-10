# 项目初始化实施任务清单

## 1. 后端项目初始化

- [x] 1.1 创建 `backend/` 目录结构
- [x] 1.2 在 `backend/` 目录初始化 uv 项目(`uv init --no-readme`)
- [x] 1.3 创建 `backend/app/` 目录和 `__init__.py`
- [x] 1.4 添加 FastAPI 依赖到 `pyproject.toml`(fastapi, uvicorn)
- [x] 1.5 添加 Supabase Python 客户端依赖(supabase)
- [x] 1.6 创建 `backend/app/main.py` FastAPI 应用入口
- [x] 1.7 创建简单的健康检查端点 `GET /`
- [x] 1.8 运行 `uv sync` 验证依赖安装

## 2. 前端项目初始化

- [x] 2.1 使用 Vite 创建 Vue 3 项目(`npm create vite@latest frontend -- --template vue-ts`)
- [x] 2.2 安装 Tailwind CSS 及依赖(`npm install -D tailwindcss postcss autoprefixer`)
- [x] 2.3 运行 `npx tailwindcss init -p` 生成配置文件
- [x] 2.4 从 prototype 复制 Tailwind 配置(颜色、字体)
- [x] 2.5 安装 Axios(`npm install axios`)
- [x] 2.6 创建 `frontend/src/style.css` 并导入 Tailwind 指令
- [x] 2.7 在 `main.ts` 中导入样式文件
- [x] 2.8 运行 `npm install` 验证依赖安装

## 3. 环境配置

- [x] 3.1 创建项目根目录的 `.env.example` 文件
- [x] 3.2 添加 Supabase URL 和 key 模板
- [x] 3.3 添加后端端口配置模板
- [x] 3.4 添加前端 API 地址配置模板
- [x] 3.5 添加中文注释说明每个环境变量

## 4. 开发文档

- [x] 4.1 更新项目根目录 `README.md`
- [x] 4.2 添加项目概述说明
- [x] 4.3 添加后端启动步骤文档
- [x] 4.4 添加前端启动步骤文档
- [x] 4.5 添加环境配置步骤文档

## 5. 验证

- [x] 5.1 验证后端可启动(`cd backend && uv run uvicorn app.main:app --reload`)
- [x] 5.2 验证健康检查端点可访问(`curl http://localhost:8000/`)
- [x] 5.3 验证前端可启动(`cd frontend && npm run dev`)
- [x] 5.4 验证前端页面可访问(`http://localhost:5173`)
