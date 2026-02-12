# Neolyst API 使用文档

## 概述

Neolyst API 是投资研究报告管理系统的后端服务，基于 FastAPI 框架构建。

**基础 URL:** `http://localhost:8000`

**API 文档:** `http://localhost:8000/docs` (Swagger UI)

---

## 认证方式

API 使用 JWT (JSON Web Token) 进行身份验证。

### 登录

```http
POST /api/auth/login
Content-Type: application/json

{
  "email": "admin@neolyst.com",
  "password": "Admin123"
}
```

**响应:**

```json
{
  "success": true,
  "message": "登录成功",
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "user": {
      "id": "uuid",
      "email": "admin@neolyst.com",
      "full_name": "System Administrator",
      "role": "admin"
    }
  }
}
```

### 使用 Token

在需要认证的请求中，添加 Authorization header:

```http
Authorization: Bearer <token>
```

---

## API 端点

### 认证相关

| 方法 | 端点 | 说明 | 权限 |
|------|------|------|------|
| POST | `/api/auth/login` | 用户登录 | 公开 |
| POST | `/api/auth/logout` | 用户登出 | 认证用户 |
| GET | `/api/auth/me` | 获取当前用户信息 | 认证用户 |

### 用户管理 (仅 Admin)

| 方法 | 端点 | 说明 | 权限 |
|------|------|------|------|
| GET | `/api/users` | 获取用户列表（支持搜索） | Admin |
| POST | `/api/users` | 创建用户 | Admin |
| PUT | `/api/users/{id}` | 更新用户信息 | Admin |
| DELETE | `/api/users/{id}` | 删除用户 | Admin |
| PUT | `/api/users/{id}/password` | 修改用户密码 | Admin |
| PUT | `/api/users/{id}/role` | 修改用户角色 | Admin |
| PUT | `/api/users/{id}/toggle-status` | 启用/禁用账号 | Admin |
| POST | `/api/users/check-email` | 检查邮箱唯一性 | Admin |

### Region 管理

| 方法 | 端点 | 说明 | 权限 |
|------|------|------|------|
| GET | `/api/regions` | 获取地区列表 | 所有认证用户 |
| POST | `/api/regions` | 创建地区 | Admin |
| PUT | `/api/regions/{id}` | 更新地区 | Admin |
| DELETE | `/api/regions/{id}` | 删除地区 | Admin |

### Analyst 信息管理 (仅 Admin)

| 方法 | 端点 | 说明 | 权限 |
|------|------|------|------|
| GET | `/api/analyst-info` | 获取 Analyst 信息列表（支持搜索） | 所有认证用户 |
| POST | `/api/analyst-info` | 创建 Analyst 信息 | Admin |
| PUT | `/api/analyst-info/{id}` | 更新 Analyst 信息 | Admin |
| DELETE | `/api/analyst-info/{id}` | 删除 Analyst 信息 | Admin |
| POST | `/api/analyst-info/check-email` | 检查邮箱唯一性 | Admin |

---

## 请求/响应示例

### 创建用户

```http
POST /api/users
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "email": "john.doe@example.com",
  "password": "password123",
  "full_name": "John Doe",
  "role": "analyst"
}
```

### 创建 Region

```http
POST /api/regions
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "name": "Hong Kong",
  "code": "HK"
}
```

### 创建 Analyst 信息

```http
POST /api/analyst-info
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "full_name": "John Smith",
  "chinese_name": "张三",
  "email": "john.smith@example.com",
  "suffix": "CFA",
  "region_id": "uuid",
  "sfc": "ABC123"
}
```

### 搜索用户

```http
GET /api/users?search=john
Authorization: Bearer <admin_token>
```

### 搜索 Analyst 信息

```http
GET /api/analyst-info?search=john&is_active=true
Authorization: Bearer <token>
```

---

## 错误响应格式

所有错误响应遵循统一格式：

```json
{
  "detail": "错误描述信息"
}
```

常见 HTTP 状态码：
- `200` - 成功
- `201` - 创建成功
- `400` - 请求参数错误
- `401` - 未认证
- `403` - 权限不足
- `404` - 资源不存在
- `409` - 资源冲突（如邮箱已存在）
- `500` - 服务器错误

---

## 启动开发服务器

```bash
cd backend
uv run uvicorn src.main:app --reload
```

服务器将在 `http://localhost:8000` 启动。

访问 `http://localhost:8000/docs` 查看 Swagger API 文档。
