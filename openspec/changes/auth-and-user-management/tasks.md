# 实施任务清单

本文档按照实施阶段组织任务，每个阶段包含一组相关的工作项。

## 阶段 1：环境准备

**目标：** 完成开发环境的基础配置，为后续开发做好准备。

### 1.1 Supabase 项目配置
- [ ] 1.1.1 登录 Supabase Dashboard，确认项目 URL
- [ ] 1.1.2 获取 API keys：`SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`
- [ ] 1.1.3 创建 RLS 辅助函数 `get_current_role()`（不需要 `get_current_analyst_id()`）
- [ ] 1.1.4 在 SQL Editor 中测试辅助函数是否正常工作

### 1.2 数据库迁移脚本
- [ ] 1.2.1 编写 `backend/migrations/001_create_region_table.sql`（region 表结构 + RLS policies）
- [ ] 1.2.2 编写 `backend/migrations/002_create_analyst_table.sql`（analyst 表结构 + RLS policies）
- [ ] 1.2.3 在 Supabase SQL Editor 中执行迁移脚本
- [ ] 1.2.4 验证表结构和 RLS policies 已正确创建

### 1.3 初始化 Admin 用户
- [ ] 1.3.1 创建 `backend/scripts/init_admin.py` 脚本
- [ ] 1.3.2 实现硬编码 Admin 创建逻辑（email: admin@neolyst.com, password: Admin123）
- [ ] 1.3.3 集成 Supabase Admin API（使用 service_role_key）
- [ ] 1.3.4 添加错误处理（用户已存在、创建失败等情况）
- [ ] 1.3.5 运行脚本验证 Admin 用户创建成功

### 1.4 后端环境配置
- [ ] 1.4.1 创建 `backend/.env.example` 文件（包含所有必需环境变量）
- [ ] 1.4.2 创建 `backend/.env` 文件（本地开发配置，不提交到 git）
- [ ] 1.4.3 更新 `backend/pyproject.toml`，添加依赖（fastapi, supabase, pydantic, python-dotenv 等）
- [ ] 1.4.4 验证环境变量加载正常（运行 Python 测试脚本）

### 1.5 前端环境配置
- [ ] 1.5.1 创建 `frontend/.env.example` 文件（VITE_API_URL）
- [ ] 1.5.2 创建 `frontend/.env` 文件（本地开发配置）
- [ ] 1.5.3 配置 Tailwind CSS（颜色系统、字体，遵循设计规范）
- [ ] 1.5.4 创建全局样式文件 `assets/styles/main.css`

---

## 阶段 2：后端 API 开发

**目标：** 实现所有后端 API 接口，包括认证、用户管理、Region 管理、Analyst 信息管理。

### 2.1 后端项目结构
- [ ] 2.1.1 创建后端目录结构（`api/`, `core/`, `models/`）
- [ ] 2.1.2 配置 Supabase Client（`core/supabase.py`）
- [ ] 2.1.3 创建配置管理模块（`core/config.py`，读取环境变量）
- [ ] 2.1.4 创建 Pydantic 数据模型（`models/auth.py`, `models/user.py`, `models/region.py`, `models/analyst.py`）

### 2.2 认证 API
- [ ] 2.2.1 实现 JWT 验证中间件（`core/security.py`，从 Authorization header 提取并验证 token）
- [ ] 2.2.2 实现登录 API（`POST /api/auth/login`，调用 Supabase Auth）
- [ ] 2.2.3 实现获取当前用户 API（`GET /api/auth/me`，从 JWT 提取用户信息）
- [ ] 2.2.4 实现登出 API（`POST /api/auth/logout`，可选，前端清除 token 即可）
- [ ] 2.2.5 集成认证路由到 `main.py`

### 2.3 用户管理 API
- [ ] 2.3.1 实现用户管理 API（`api/users.py`）
- [ ] 2.3.2 实现 `GET /api/users`（获取列表，支持搜索，仅 Admin）
- [ ] 2.3.3 实现 `POST /api/users`（创建用户，仅 Admin）
- [ ] 2.3.4 实现 `PUT /api/users/{id}`（更新用户信息，仅 Admin）
- [ ] 2.3.5 实现 `PUT /api/users/{id}/password`（修改密码，仅 Admin）
- [ ] 2.3.6 实现 `PUT /api/users/{id}/role`（修改角色，仅 Admin）
- [ ] 2.3.7 实现 `DELETE /api/users/{id}`（删除用户，仅 Admin）
- [ ] 2.3.8 实现 `POST /api/users/check-email`（检查邮箱唯一性，仅 Admin）
- [ ] 2.3.9 实现 `PUT /api/users/{id}/toggle-status`（启用/禁用账号，仅 Admin）
- [ ] 2.3.10 集成用户管理路由到 `main.py`

### 2.4 Region 管理 API
- [ ] 2.4.1 实现 Region CRUD API（`api/regions.py`）
- [ ] 2.4.2 实现 `GET /api/regions`（获取列表，所有认证用户可读）
- [ ] 2.4.3 实现 `POST /api/regions`（创建，仅 Admin）
- [ ] 2.4.4 实现 `PUT /api/regions/{id}`（更新，仅 Admin）
- [ ] 2.4.5 实现 `DELETE /api/regions/{id}`（删除，仅 Admin）
- [ ] 2.4.6 集成 Region 路由到 `main.py`
- [ ] 2.4.7 测试 RLS policies（使用不同角色的 token 验证权限）

### 2.5 Analyst 信息管理 API
- [ ] 2.5.1 实现 Analyst 信息管理 API（`api/analyst_info.py`）
- [ ] 2.5.2 实现 `GET /api/analyst-info`（获取列表，支持搜索，所有认证用户可读）
- [ ] 2.5.3 实现 `POST /api/analyst-info/check-email`（邮箱唯一性检查）
- [ ] 2.5.4 实现 `POST /api/analyst-info`（创建 Analyst 信息，仅 Admin）
- [ ] 2.5.5 实现 `PUT /api/analyst-info/{id}`（更新 Analyst 信息，仅 Admin）
- [ ] 2.5.6 实现 `DELETE /api/analyst-info/{id}`（删除 Analyst 信息，仅 Admin）
- [ ] 2.5.7 集成 Analyst 信息路由到 `main.py`
- [ ] 2.5.8 测试 RLS policies（确保 Admin/SA/Analyst 权限正确）

### 2.6 后端启动验证
- [ ] 2.6.1 运行 `uv run uvicorn src.main:app --reload` 启动开发服务器
- [ ] 2.6.2 访问 Auto API 文档（`http://localhost:8000/docs`）验证所有接口已注册
- [ ] 2.6.3 测试健康检查接口（如果实现）

---

## 阶段 3：前端开发

**目标：** 实现所有前端页面和组件，包括登录、桌面主页、Region 和 Analyst 信息管理页面。

### 3.1 前端项目配置
- [ ] 3.1.1 配置 Vue Router（路由结构：`/login`, `/desktop`, `/regions`, `/analyst-info`）
- [ ] 3.1.2 创建 Axios 实例（`api/client.ts`，配置 baseURL）
- [ ] 3.1.3 实现请求拦截器（自动添加 JWT Token 到 Authorization header）
- [ ] 3.1.4 实现响应拦截器（处理 401 错误，清除 token 并跳转登录）

### 3.2 前端状态管理
- [ ] 3.2.1 创建认证状态管理（`stores/auth.ts`，使用 provide/inject 模式）
- [ ] 3.2.2 实现 `provideAuthStore()` 函数（在 App.vue 中调用）
- [ ] 3.2.3 实现 `useAuth()` composable（在子组件中使用）
- [ ] 3.2.4 实现 login/logout 方法（同步 localStorage 和响应式状态）
- [ ] 3.2.5 创建登录 API 调用函数（`api/auth.ts`）

### 3.3 粒子背景组件
- [ ] 3.3.1 创建 `components/common/ParticleBackground.vue` 组件
- [ ] 3.3.2 实现 Canvas 2D 粒子效果（120 个粒子，蓝色-青色渐变）
- [ ] 3.3.3 实现粒子间连线效果（距离 < 140px）
- [ ] 3.3.4 实现粒子脉冲闪烁效果
- [ ] 3.3.5 添加性能优化（requestAnimationFrame, will-change CSS 属性）
- [ ] 3.3.6 确保无鼠标交互（按照设计文档）

### 3.4 登录页面
- [ ] 3.4.1 创建 `views/Login.vue` 页面组件
- [ ] 3.4.2 实现登录表单布局（Email + Password + Login 按钮）
- [ ] 3.4.3 集成 ParticleBackground 组件作为背景
- [ ] 3.4.4 实现表单验证（Email 格式、必填项）
- [ ] 3.4.5 集成登录 API 调用和错误处理
- [ ] 3.4.6 实现登录成功后跳转到桌面主页

### 3.5 桌面主页
- [ ] 3.5.1 创建 `views/Desktop.vue` 页面组件
- [ ] 3.5.2 实现顶部导航栏（Logo + Welcome, {name} + Logout 按钮）
- [ ] 3.5.3 创建功能卡片组件 `components/desktop/DesktopCard.vue`
- [ ] 3.5.4 实现 Reports 功能卡片组（4 个卡片：Reports, New Report, Report Review, Templates）
- [ ] 3.5.5 实现 Data Management 功能卡片组（4 个卡片：Analyst Info, Coverage, Sectors, Regions）
- [ ] 3.5.6 实现卡片悬停效果和样式

### 3.6 占位页面
- [ ] 3.6.1 创建占位页面模板 `views/ComingSoon.vue`
- [ ] 3.6.2 所有未实现功能卡片链接到占位页面
- [ ] 3.6.3 占位页面显示 "This feature is coming soon" 提示
- [ ] 3.6.4 添加 "Back to Desktop" 返回链接

### 3.7 路由守卫
- [ ] 3.7.1 在 `router/index.ts` 实现路由守卫
- [ ] 3.7.2 未登录用户访问受保护路由时重定向到 `/login`
- [ ] 3.7.3 已登录用户访问 `/login` 时重定向到 `/desktop`
- [ ] 3.7.4 创建权限检查函数 `composables/usePermission.ts`
- [ ] 3.7.5 集成权限检查到功能卡片（Analyst Info 卡片仅 Admin 可见）

### 3.8 Region 管理页面
- [ ] 3.8.1 创建 `views/RegionsPage.vue` 页面组件
- [ ] 3.8.2 实现页面头部（标题 + "Back to Desktop" 链接）
- [ ] 3.8.3 实现 Region 列表（表格形式，所有用户可见）
- [ ] 3.8.4 实现创建 Region 表单对话框（Modal）
- [ ] 3.8.5 实现编辑 Region 功能
- [ ] 3.8.6 实现删除 Region 功能（含确认对话框）
- [ ] 3.8.7 权限控制（Admin only 可见创建/编辑/删除按钮）
- [ ] 3.8.8 创建/编辑/删除 API 调用和错误处理

### 3.9 Analyst 信息管理页面
- [ ] 3.9.1 创建 `views/AnalystInfoPage.vue` 页面组件
- [ ] 3.9.2 实现页面头部（标题 + "Back to Desktop" 链接）
- [ ] 3.9.3 实现搜索功能（按 full_name 或 email）
- [ ] 3.9.4 实现 Analyst 信息列表（表格形式）
- [ ] 3.9.5 实现创建 Analyst 信息表单（字段: full_name, chinese_name, email, suffix, region_id, sfc）
- [ ] 3.9.6 实现邮箱唯一性检查（调用 `POST /api/analyst-info/check-email`）
- [ ] 3.9.7 实现创建成功提示（创建成功后显示提示）
- [ ] 3.9.8 实现编辑 Analyst 信息功能
- [ ] 3.9.9 实现删除 Analyst 信息功能（含确认对话框）
- [ ] 3.9.10 权限控制（仅 Admin 可见整个页面）
- [ ] 3.9.11 创建/编辑/删除 API 调用和错误处理

### 3.10 登出功能
- [ ] 3.10.1 在 Desktop.vue 实现 Logout 按钮点击事件
- [ ] 3.10.2 清除 localStorage 中的 `auth_token` 和 `user_info`
- [ ] 3.10.3 重置前端用户状态（调用 `useAuth().logout()`）
- [ ] 3.10.4 跳转到登录页并显示成功提示

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
- [ ] 4.2.5 测试 RLS policies（使用不同角色的 token）

### 4.3 Analyst 信息管理测试
- [ ] 4.3.1 测试 Analyst 信息列表加载（所有角色可见）
- [ ] 4.3.2 测试搜索功能（按 full_name 或 email 过滤）
- [ ] 4.3.3 测试邮箱唯一性检查（重复邮箱返回错误）
- [ ] 4.3.4 测试创建 Analyst 信息（Admin 成功）
- [ ] 4.3.5 测试编辑 Analyst 信息（Admin 成功）
- [ ] 4.3.6 测试删除 Analyst 信息（Admin 成功）
- [ ] 4.3.7 测试页面权限控制（SA 和 Analyst 访问返回 403 或 404）

### 4.4 UI/UX 测试
- [ ] 4.4.1 验证粒子背景效果和性能（60fps）
- [ ] 4.4.2 测试桌面卡片悬停效果
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
- [ ] 5.1.1 更新根目录 `README.md`（项目说明、技术栈、启动命令）
- [ ] 5.1.2 创建开发环境搭建文档（`docs/SETUP.md`，.env 配置说明）
- [ ] 5.1.3 更新 `openspec/changes/auth-and-user-management/proposal.md`（记录实施完成情况）

### 5.2 代码质量
- [ ] 5.2.1 运行后端代码格式化（`uv run black backend/`）
- [ ] 5.2.2 运行后端代码检查（`uv run ruff check backend/`）
- [ ] 5.2.3 运行前端代码格式化（`npm run format`）
- [ ] 5.2.4 运行前端代码检查（`npm run lint`）
- [ ] 5.2.5 运行前端类型检查（`npm run type-check`）

### 5.3 清理工作
- [ ] 5.3.1 删除临时文件和测试脚本
- [ ] 5.3.2 删除注释代码和调试日志
- [ ] 5.3.3 确认 `.gitignore` 包含所有敏感文件（`.env`, `__pycache__`, `node_modules`）
- [ ] 5.3.4 提交代码到 git（创建清晰的 commit message）

---

## 任务统计

- **总任务数**: 124（已重构和优化）
- **已完成**: 0
- **待完成**: 124

## 实施建议

1. **按顺序执行**: 强烈建议按照阶段 1 → 阶段 2 → 阶段 3 → 阶段 4 → 阶段 5 的顺序执行
2. **每个阶段完成后测试**: 完成一个阶段后，进行基本功能测试再进入下一阶段
3. **优先环境准备**: 阶段 1 是所有后续工作的基础，必须首先完成
4. **后端优先**: 阶段 2 完成后，前端开发时可以立即联调
5. **持续集成**: 阶段 3 和 4 可以部分重叠，开发完一个模块就测试
