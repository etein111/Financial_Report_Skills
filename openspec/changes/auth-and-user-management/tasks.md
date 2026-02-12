# 实施任务清单

本文档按照实施阶段组织任务，每个阶段包含一组相关的工作项。

## 阶段 1：环境准备

**目标：** 完成开发环境的基础配置，为后续开发做好准备。

### 1.1 Supabase 项目配置
- [ ] 1.1.1 配置 Supabase 项目并获取 API keys（`SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`）
- [ ] 1.1.2 创建并测试 RLS 辅助函数 `get_current_role()`（在 SQL Editor 中执行并验证）

### 1.2 数据库迁移脚本
- [ ] 1.2.1 编写数据库迁移脚本（`backend/migrations/001_create_region_table.sql` 和 `002_create_analyst_table.sql`，包含表结构和 RLS policies）
- [ ] 1.2.2 执行迁移脚本并验证表结构和 RLS policies 已正确创建

### 1.3 初始化 Admin 用户
- [ ] 1.3.1 创建 `backend/scripts/init_admin.py` 脚本（实现 Admin 创建逻辑 + Supabase Admin API 集成 + 错误处理）
- [ ] 1.3.2 运行脚本验证 Admin 用户创建成功（email: admin@neolyst.com, password: Admin123）

### 1.4 后端环境配置
- [ ] 1.4.1 创建环境配置文件和更新依赖（`.env.example` + `.env` + `pyproject.toml`，验证环境变量加载正常）

### 1.5 前端环境配置
- [ ] 1.5.1 创建前端环境配置和全局样式（`.env.example` + `.env` + Tailwind CSS 配置 + `assets/styles/main.css`）

---

## 阶段 2：后端 API 开发

**目标：** 实现所有后端 API 接口，包括认证、用户管理、Region 管理、Analyst 信息管理。

### 2.1 后端项目结构
- [ ] 2.1.1 搭建后端项目结构（创建 `api/`, `core/`, `models/` 目录，配置 Supabase Client，创建 `config.py`，创建所有 Pydantic 模型）

### 2.2 认证 API
- [ ] 2.2.1 实现 JWT 验证中间件和登录/登出 API（`core/security.py` + `POST /api/auth/login` + `POST /api/auth/logout`）
- [ ] 2.2.2 实现 `GET /api/auth/me`（从 JWT 提取用户信息）并集成路由到 `main.py`

### 2.3 用户管理 API
- [ ] 2.3.1 实现用户 CRUD API（`api/users.py`，包含 `GET /api/users` 支持搜索、`POST /api/users` 创建、`PUT /api/users/{id}` 更新、`DELETE /api/users/{id}` 删除）
- [ ] 2.3.2 实现密码和角色管理 API（`PUT /password` 修改密码、`PUT /role` 修改角色、`PUT /toggle-status` 启用/禁用）
- [ ] 2.3.3 实现邮箱唯一性检查（`POST /check-email`）并集成路由，测试权限控制（仅 Admin）

### 2.4 Region 管理 API
- [ ] 2.4.1 实现 Region CRUD API（`api/regions.py`，包含 `GET/POST/PUT/DELETE /api/regions`）
- [ ] 2.4.2 集成路由到 `main.py` 并测试 RLS policies（使用不同角色的 token 验证 Admin vs 其他角色权限）

### 2.5 Analyst 信息管理 API
- [ ] 2.5.1 实现 Analyst 信息 CRUD API（`api/analyst_info.py`，包含 `GET /api/analyst-info` 支持搜索、`POST/PUT/DELETE` 实现增删改）
- [ ] 2.5.2 实现邮箱唯一性检查 API（`POST /check-email`）并集成路由
- [ ] 2.5.3 测试 RLS policies 和权限控制（确保所有认证用户可读，仅 Admin 可写）

### 2.6 后端启动验证
- [ ] 2.6.1 启动开发服务器并验证 API 文档（`uv run uvicorn src.main:app --reload`，访问 `http://localhost:8000/docs`）
- [ ] 2.6.2 编写后端 API 使用文档（`docs/API.md`，包含认证方式、端点列表、请求/响应示例）

---

## 阶段 3：前端开发

**目标：** 实现所有前端页面和组件，包括登录、桌面主页、Region 和 Analyst 信息管理页面。

### 3.1 前端项目配置
- [ ] 3.1.1 配置 Vue Router 和路由结构（`/login`, `/desktop`, `/regions`, `/analyst-info`, `/coming-soon`）
- [ ] 3.1.2 创建 Axios 实例并实现拦截器（`api/client.ts`，请求拦截器自动添加 Token，响应拦截器处理 401）
- [ ] 3.1.3 编写前端配置文档（`docs/FRONTEND.md`，包含路由结构、API 调用方式、状态管理说明）

### 3.2 认证状态管理
- [ ] 3.2.1 实现认证状态管理（`stores/auth.ts`，包含 `provideAuthStore()` 和 `useAuth()` composable，实现 login/logout 方法）
- [ ] 3.2.2 创建登录 API 调用函数（`api/auth.ts`）并编写状态管理文档

### 3.3 粒子背景组件
- [ ] 3.3.1 实现粒子背景组件（`components/common/ParticleBackground.vue`，Canvas 2D，120 粒子，蓝青渐变，粒子间连线 < 140px，脉冲闪烁，requestAnimationFrame 优化，无鼠标交互）

### 3.4 登录页面
- [ ] 3.4.1 创建登录页面（`views/Login.vue`，表单布局 + 粒子背景 + 表单验证）
- [ ] 3.4.2 集成登录 API 并实现错误处理和登录成功跳转

### 3.5 桌面主页
- [ ] 3.5.1 创建桌面主页和导航栏（`views/Desktop.vue`，Logo + Welcome, {name} + Logout 按钮）
- [ ] 3.5.2 实现功能卡片组件（`components/desktop/DesktopCard.vue`，Reports 组 + Data Management 组，悬停效果）
- [ ] 3.5.3 编写桌面功能文档（说明功能卡片、新标签页打开方式、导航栏设计）

### 3.6 路由守卫和权限
- [ ] 3.6.1 实现路由守卫（未登录重定向到 `/login`，已登录访问 `/login` 重定向到 `/desktop`）
- [ ] 3.6.2 创建权限检查函数并集成（`composables/usePermission.ts`，功能卡片权限控制）

### 3.7 Region 管理页面
- [ ] 3.7.1 创建 Region 列表页面（`views/RegionsPage.vue`，表格形式，所有用户可见，返回链接）
- [ ] 3.7.2 实现 CRUD 功能（创建/编辑/删除对话框，API 调用和错误处理，Admin only 权限控制）

### 3.8 Analyst 信息管理页面
- [ ] 3.8.1 创建 Analyst 信息列表页面（`views/AnalystInfoPage.vue`，表格 + 搜索 + 返回链接）
- [ ] 3.8.2 实现 CRUD 功能和表单验证（创建/编辑对话框，邮箱唯一性前端实时验证，API 调用，Admin only 权限）

### 3.9 其他功能
- [ ] 3.9.1 创建 Coming Soon 占位页面（`views/ComingSoon.vue`，"This feature is coming soon" 提示，返回链接）
- [ ] 3.9.2 实现登出功能（Desktop.vue 中 Logout 按钮，清除 localStorage，重置状态，跳转登录）

---

## 阶段 4：集成测试

**目标：** 端到端测试整个系统功能，确保所有流程正常工作。

### 4.1 认证流程测试
- [ ] 4.1.1 测试完整登录流程（输入有效凭据 → 登录成功 → 跳转桌面）
- [ ] 4.1.2 测试登录失败流程（无效凭据 → 显示错误提示）
- [ ] 4.1.3 测试登出功能（点击 Logout → 清除状态 → 跳转登录）
- [ ] 4.1.4 测试路由守卫（未登录访问 `/desktop` → 重定向登录）
- [ ] 4.1.5 测试 Token 过期处理（清除 token → 401 → 重定向登录）

### 4.2 Region 管理测试
- [ ] 4.2.1 测试 Region 列表加载（所有角色可见）
- [ ] 4.2.2 测试创建 Region（Admin 成功，其他角色 403）
- [ ] 4.2.3 测试编辑 Region（Admin 成功，其他角色 403）
- [ ] 4.2.4 测试删除 Region（Admin 成功，其他角色 403）
- [ ] 4.2.5 测试 RLS policies（使用不同角色的 token 验证数据库层权限）

### 4.3 Analyst 信息管理测试
- [ ] 4.3.1 测试 Analyst 信息列表加载（所有角色可见）
- [ ] 4.3.2 测试搜索功能（按 full_name 或 email 过滤）
- [ ] 4.3.3 测试邮箱唯一性检查（重复邮箱返回错误）
- [ ] 4.3.4 测试创建 Analyst 信息（Admin 成功）
- [ ] 4.3.5 测试编辑 Analyst 信息（Admin 成功）
- [ ] 4.3.6 测试删除 Analyst 信息（Admin 成功）
- [ ] 4.3.7 测试页面权限控制（SA 和 Analyst 访问返回 403 或 404）

### 4.4 UI/UX 测试
- [ ] 4.4.1 验证粒子背景效果和性能（60fps，无卡顿）
- [ ] 4.4.2 测试桌面卡片悬停效果和样式
- [ ] 4.4.3 测试表格样式和响应式布局
- [ ] 4.4.4 测试对话框交互（创建、编辑、删除确认）
- [ ] 4.4.5 测试错误提示显示（表单验证、API 错误）
- [ ] 4.4.6 测试不同浏览器兼容性（Chrome, Firefox, Safari）

### 4.5 角色权限测试
- [ ] 4.5.1 使用 Admin 账号验证所有功能可访问
- [ ] 4.5.2 使用 SA 账号验证可访问 Analyst 信息列表
- [ ] 4.5.3 使用 Analyst 账号验证无法访问管理页面
- [ ] 4.5.4 验证 RLS policies 在数据库层面正确过滤数据

---

## 阶段 5：文档和清理

**目标：** 完善项目文档，清理代码，准备交付。

### 5.1 文档更新
- [ ] 5.1.1 更新根目录 `README.md`（项目说明、技术栈、启动命令、环境配置）
- [ ] 5.1.2 更新 `openspec/changes/auth-and-user-management/proposal.md`（记录实施完成情况）

### 5.2 代码质量
- [ ] 5.2.1 运行代码格式化和检查（后端：`uv run black backend/` + `uv run ruff check backend/`，前端：`npm run format` + `npm run lint` + `npm run type-check`）
- [ ] 5.2.2 修复检查中发现的问题

### 5.3 清理和提交
- [ ] 5.3.1 清理临时文件和调试日志（删除测试脚本、注释代码）
- [ ] 5.3.2 确认 `.gitignore` 包含所有敏感文件（`.env`, `__pycache__`, `node_modules`）并提交代码到 git

---

## 任务统计

- **总任务数**: 68（已简化优化）
- **已完成**: 0
- **待完成**: 68

## 简化说明

相比原版本（124 任务），本版本进行了以下优化：

1. **API 开发任务聚合**：单个 API 端点不再拆分，改为"实现模块 CRUD"
2. **粒子背景简化**：6 个任务合并为 1 个任务
3. **环境配置合并**：相关配置任务合并为"一次性配置"
4. **测试保留**：根据需求保留详细测试，确保质量
5. **文档前置**：每个阶段结束时写相关文档，不是堆到最后

## 实施建议

1. **按顺序执行**: 强烈建议按照阶段 1 → 阶段 2 → 阶段 3 → 阶段 4 → 阶段 5 的顺序执行
2. **每个阶段完成后测试**: 完成一个阶段后，进行基本功能测试再进入下一阶段
3. **优先环境准备**: 阶段 1 是所有后续工作的基础，必须首先完成
4. **后端优先**: 阶段 2 完成后，前端开发时可以立即联调
5. **文档同步**: 每个阶段结束时会编写相关文档，避免最后集中写文档
