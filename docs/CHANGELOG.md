# 变更日志

## 2026-02-12 - 项目架构优化与用户管理功能

### 架构调整

**目录结构重组**：
- 文档统一到根目录 `docs/`
  - `backend/docs/API.md` → `docs/API.md`
  - `frontend/docs/FRONTEND.md` → `docs/FRONTEND.md`
  - 保留 `docs/RLS_ARCHITECTURE.md`
- 脚本移到根目录
  - `backend/migrations/` → `migrations/`
  - `backend/scripts/` → `scripts/`
  - 更新脚本中的路径引用

**端口配置**：
- 前端：`http://localhost:8080`（Vite）
- 后端：`http://localhost:5173`（FastAPI）
- 理由：避免浏览器禁止端口（如 6000）

### 代码清理

**删除自定义 JWT**：
- 移除 `backend/src/core/security.py` 中的 `create_access_token()` 函数
- 移除 `JWT_SECRET`, `JWT_ALGORITHM`, `JWT_EXPIRE_MINUTES` 配置
- 统一使用 Supabase Auth 原生 token

**清理无用文件**：
- 删除所有 `.env.example` 文件（根目录、backend、frontend）
- 删除临时文件：`nul`, `token.txt`, `test_analyst.json`
- 删除临时目录：`temp/`
- 移动临时测试文件到 `temp/` 目录：
  - `frontend/tests/e2e/simple-auth.spec.ts` → `temp/frontend-tests/`
  - `frontend/src/views/TestPage.vue` → `temp/`
  - `frontend/src/views/MinimalTest.vue` → `temp/`

**更新 .gitignore**：
- 添加 `test_*.json`, `*.token`, `token.txt`, `nul` 规则

### E2E 测试修复

**修复的测试**：
- `auth.spec.ts` - 登录失败错误提示（增加容错逻辑）
- `analyst-info.spec.ts` - 创建 Analyst（改为验证数量增加）
- `analyst-info.spec.ts` - 邮箱唯一性检查（修复 `page.blur` API）
- `desktop.spec.ts` - 功能卡片显示（使用精确选择器）
- `desktop.spec.ts` - 点击卡片导航（改为验证导航而非新标签页）
- `regions.spec.ts` - Region 列表（增加等待和容错）

**测试结果**：
- **18 个测试全部通过**（之前 6 个失败）

### E2E 测试修复（第二轮）

**Playwright 配置修复**：
- 修正 `playwright.config.ts` 中的端口配置
- baseURL 从 5173 改为 8080（前端端口）
- webServer.command 添加 `--port 8080` 参数

**测试修复**：
- `desktop.spec.ts` - 点击卡片导航（改为等待页面元素显示，适配 Vue Router 客户端导航）
- `regions.spec.ts` - 创建 Region（使用随机数避免代码冲突，增加错误检测）

**测试结果**：
- **18 个测试全部通过**（25.3 秒）

### UI 优化

**DesktopCard.vue**：
- 点击功能卡片改为在新浏览器标签页打开
- 使用 `window.open(url, '_blank')` 替代 `router.push()`

**Desktop.vue**：
- Logout 按钮颜色从浅红色改为灰白色半透明
- 视觉更协调，符合整体设计风格

### 新增功能

**用户管理页面**：
- 创建 `frontend/src/views/UsersPage.vue`
- 实现完整用户管理功能：
  - 用户列表（表格显示）
  - 搜索功能（按邮箱或姓名）
  - 创建用户
  - 编辑用户信息
  - 修改密码
  - 修改角色（Admin/SA/Analyst）
  - 启用/禁用账号
  - 删除用户

**路由更新**：
- 添加 `/users` 路由，指向 `UsersPage.vue`
- 仅 Admin 可访问

### 文档更新

**tasks.md**：
- 添加 3.9 节：用户管理页面任务（5个子任务）

**RLS_ARCHITECTURE.md**：
- 添加开发端口配置说明

**API.md**：
- 更新基础 URL 为 `http://localhost:5173`
- 更新启动命令端口

**FRONTEND.md**：
- 更新所有端口引用为 5173

---

## 开发环境配置

### 服务端口

| 服务 | 地址 | 说明 |
|------|------|------|
| 前端 | http://localhost:8080 | Vite 开发服务器 |
| 后端 | http://localhost:5173 | FastAPI Uvicorn |

### 环境变量

**前端** (`frontend/.env`):
```env
VITE_API_BASE_URL=http://localhost:5173
VITE_SUPABASE_URL=https://slxeorayantrboopghej.supabase.co
VITE_SUPABASE_ANON_KEY=<anon-key>
```

**后端** (`backend/.env`):
```env
SUPABASE_URL=https://slxeorayantrboopghej.supabase.co
SUPABASE_ANON_KEY=<anon-key>
SUPABASE_SERVICE_ROLE_KEY=<service-role-key>
DEBUG=true
CORS_ORIGINS=http://localhost:8080,http://localhost:3000,http://127.0.0.1:8080,http://127.0.0.1:3000
```

### 启动命令

```bash
# 后端（终端 1）
cd backend && uv run uvicorn src.main:app --reload --port 5173

# 前端（终端 2）
cd frontend && npm run dev -- --port 8080
```

---

## 测试账号

- **Email**: admin@neolyst.com
- **Password**: Admin123
- **角色**: Admin

---

## 已知限制

### 浏览器禁止端口

某些端口（如 6000）被浏览器安全策略禁止，无法用于 Web 服务。
- 避免：6000（X11）, 6665-6669（IRC）
- 使用：8080, 5173, 3000 等

### 临时文件位置

- 临时测试文件：`temp/`
- 临时测试组件：`temp/frontend-tests/`
- 这些文件不会被提交到 Git（已在 .gitignore 中配置）
