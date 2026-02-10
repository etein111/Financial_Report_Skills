## Why

需要建立标准化的开发环境来支持 Neolyst 投资研究报告管理系统的实施,为后续功能开发提供统一的项目结构和工具链。

## What Changes

**项目结构:**
- 初始化 monorepo 结构,包含 `backend/` 和 `frontend/` 目录
- 建立统一的环境配置文件

**后端初始化:**
- 使用 `uv` 初始化 Python FastAPI 项目
- 配置项目依赖和虚拟环境管理
- 准备 Supabase 集成的基础配置
- 虚拟环境位于 `backend/.venv/` (本地,不提交到 git)

**前端初始化:**
- 使用 Vite 初始化 Vue 3 项目
- 配置 Tailwind CSS(与 prototype 保持一致)
- 配置 Axios 用于 API 通信
- 依赖位于 `frontend/node_modules/` (本地,不提交到 git)

**开发工具:**
- 创建 `.env.example` 作为环境变量模板
- 配置开发环境的文档和说明

## Capabilities

### New Capabilities
- `项目基础架构`: 提供开发和运行 Neolyst 系统所需的基础项目结构、配置和工具链

### Modified Capabilities
<!-- 无现有功能修改 -->

## Impact

**新增文件:**
- `backend/pyproject.toml` - 后端项目配置和依赖
- `backend/uv.lock` - 依赖锁定文件(提交到 git)
- `backend/.venv/` - Python 虚拟环境(本地,不提交)
- `backend/app/` - FastAPI 应用代码目录
- `frontend/package.json` - 前端项目配置
- `frontend/package-lock.json` - 依赖锁定文件
- `frontend/node_modules/` - npm 依赖(本地,不提交)
- `frontend/src/` - Vue 应用代码目录
- `.env.example` - 环境变量模板(提交到 git)

**开发工具:**
- 后端使用 `uv` 进行包管理和脚本执行
- 前端使用 `npm` 和 `vite` 进行开发和构建
