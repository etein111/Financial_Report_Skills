# Neolyst - 投资研究报告管理系统

> "The Future is Now"

一个基于 Supabase 和 FastAPI 构建的现代化投资研究报告管理系统，支持多种用户角色和细粒度权限控制。

## 技术栈

### 后端
- **FastAPI** - 现代 Python Web 框架
- **Supabase** - 后端服务（Auth、Database、Storage）
- **PostgreSQL** - 数据库（带 RLS 支持）
- **Python 3.14+** - 运行环境

### 前端
- **Vue 3** - 渐进式 JavaScript 框架
- **Vite** - 下一代前端构建工具
- **Tailwind CSS v4** - 原子化 CSS 框架
- **TypeScript** - 类型安全的 JavaScript

### 开发工具
- **OpenSpec** - 变更管理和规范驱动开发
- **Supabase CLI** - 本地开发和部署

## 功能特性

### 用户认证
- ✅ Supabase Auth 集成（ES256 JWT）
- ✅ 基于角色的访问控制（RBAC）
- ✅ 多角色支持：Admin、SA、Analyst
- ✅ Row Level Security（RLS）策略

### 权限控制
| 功能 | Admin | SA | Analyst |
|------|-------|----|---------|
| 用户管理 | ✅ | ❌ | ❌ |
| 查看 Region | ✅ | ✅ | ✅ |
| 修改 Region | ✅ | ❌ | ❌ |
| 查看 Analyst 信息 | ✅ | ✅ | ✅ |
| 修改 Analyst 信息 | ✅ | ❌ | ❌ |

## 快速开始

### 前置要求
- Python 3.14+
- Node.js 20+
- Supabase 账号

### 1. 克隆仓库
```bash
git clone https://github.com/wanli15nian/neolyst.git
cd neolyst
```

### 2. 配置后端
```bash
cd backend

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入 Supabase 凭证
```

### 3. 配置前端
```bash
cd frontend

# 安装依赖
npm install

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入 API 地址
```

### 4. 启动开发服务器

**后端（端口 8001）：**
```bash
cd backend
python -m uvicorn src.main:app --host 127.0.0.1 --port 8001 --reload
```

**前端（端口 5173）：**
```bash
cd frontend
npm run dev
```

### 5. 访问应用
打开浏览器访问 [http://localhost:5173](http://localhost:5173)

## 测试账号

默认测试账号（需在 Supabase 中创建）：
- **Admin**: admin@test.com / admin123
- **SA**: sa2@test.com / sa123456
- **Analyst**: analyst2@test.com / analyst123

## 项目结构

```
neolyst/
├── backend/                 # FastAPI 后端
│   ├── src/
│   │   ├── api/            # API 路由
│   │   ├── core/           # 核心功能（配置、安全、Supabase）
│   │   ├── models/         # 数据模型
│   │   └── main.py         # 应用入口
│   └── tests/              # 测试文件
├── frontend/               # Vue 3 前端
│   ├── src/
│   │   ├── api/            # API 客户端
│   │   ├── components/     # Vue 组件
│   │   ├── stores/         # Pinia 状态管理
│   │   ├── views/          # 页面视图
│   │   └── main.ts         # 应用入口
│   └── public/             # 静态资源
├── docs/                   # 项目文档
│   └── RLS_ARCHITECTURE.md # RLS 架构说明
└── openspec/               # OpenSpec 变更管理
    └── changes/            # 变更记录
```

## 核心设计

### 认证架构

```
用户登录
  ↓
Supabase Auth (sign_in_with_password)
  ↓
返回 Supabase 原生 JWT Token (ES256)
  ↓
前端存储 Token
  ↓
后续请求携带 Bearer Token
  ↓
FastAPI 验证 (supabase_client.auth.get_user)
  ↓
返回用户信息（含 role）
  ↓
权限检查 (require_admin 依赖)
```

### RLS 策略

```sql
-- 所有认证用户可读
CREATE POLICY "Authenticated users can view analysts"
ON analyst FOR SELECT TO authenticated
USING (true);

-- 只有 Admin 可写
CREATE POLICY "Only Admin can modify analysts"
ON analyst FOR ALL TO authenticated
USING ((auth.jwt()->'app_metadata'->>'role')::text = 'admin')
WITH CHECK ((auth.jwt()->'app_metadata'->>'role')::text = 'admin');
```

### API 权限控制

```python
# 所有认证用户可访问
@router.get("/api/regions")
async def list_regions(
    current_user: Annotated[dict, Depends(get_current_user)]
):
    ...

# 仅 Admin 可访问
@router.post("/api/regions")
async def create_region(
    current_user: Annotated[dict, Depends(require_admin)]
):
    ...
```

## 开发指南

### 添加新的 API 端点

**只读端点**（所有认证用户可访问）：
```python
@router.get("")
async def list_items(
    current_user: Annotated[dict, Depends(get_current_user)]
):
    ...
```

**写操作端点**（仅 Admin 可访问）：
```python
@router.post("")
async def create_item(
    current_user: Annotated[dict, Depends(require_admin)]
):
    ...
```

### 添加新的数据库表

1. 在 Supabase 中创建表
2. 启用 RLS
3. 创建 RLS 策略
4. 创建对应的 API 端点

## 文档

- [RLS 架构说明](docs/RLS_ARCHITECTURE.md) - Row Level Security 设计
- [OpenSpec 变更](openspec/changes/) - 规范驱动的变更管理

## 贡献

欢迎提交 Issue 和 Pull Request！

## 许可证

MIT License
