## ADDED Requirements

### Requirement: 后端项目结构初始化

系统 SHALL 创建符合 FastAPI 和 uv 标准的后端项目结构。

#### Scenario: 后端目录结构存在
- **WHEN** 开发者查看项目根目录
- **THEN** `backend/` 目录必须存在
- **AND** `backend/pyproject.toml` 文件必须存在
- **AND** `backend/app/` 目录必须存在
- **AND** `backend/app/__init__.py` 文件必须存在

#### Scenario: 后端虚拟环境可创建
- **WHEN** 开发者在 `backend/` 目录运行 `uv sync`
- **THEN** `.venv/` 目录必须在 `backend/` 内创建
- **AND** FastAPI 依赖必须安装成功
- **AND** 运行 `uv run python -c "import fastapi"` 必须成功

### Requirement: 前端项目结构初始化

系统 SHALL 创建符合 Vue 3 和 Vite 标准的前端项目结构。

#### Scenario: 前端目录结构存在
- **WHEN** 开发者查看项目根目录
- **THEN** `frontend/` 目录必须存在
- **AND** `frontend/package.json` 文件必须存在
- **AND** `frontend/src/` 目录必须存在
- **AND** `frontend/src/main.ts` 文件必须存在

#### Scenario: 前端开发服务器可启动
- **WHEN** 开发者在 `frontend/` 目录运行 `npm install`
- **THEN** `node_modules/` 目录必须创建
- **AND** 运行 `npm run dev` 必须成功启动开发服务器

### Requirement: 环境配置模板

系统 SHALL 提供环境变量模板文件以指导开发者配置。

#### Scenario: 环境变量模板存在
- **WHEN** 开发者查看项目根目录
- **THEN** `.env.example` 文件必须存在
- **AND** 文件必须包含 Supabase URL 和 key 的占位符
- **AND** 文件必须包含必要的注释说明

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
