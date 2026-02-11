# 认证和权限系统设计文档

## Context

Neolyst 项目需要建立用户认证和权限控制基础设施，为后续的报告管理功能提供安全基础。当前项目已初始化基础架构（backend + frontend），Supabase 项目已创建，但数据库为空，需要从零开始构建认证系统。

**约束条件:**
- 必须使用 Supabase Auth 进行用户认证
- 权限控制使用 Supabase RLS (Row Level Security)
- 后端使用 FastAPI + Python 3.11+
- 前端使用 Vue 3 + Vite + Tailwind CSS
- 所有开发文档和注释使用中文

**相关文档:**
- Supabase URL: https://slxeorayantrboopghej.supabase.co

## Goals / Non-Goals

**Goals:**
- 实现基于 Supabase Auth 的用户认证（登录/登出，JWT Token 验证）
- 建立数据库层的权限控制（RLS policies）
- 提供登录界面（含粒子背景效果）
- 提供桌面主页（功能卡片占位）
- 创建第一个 Admin 用户的初始化机制

**Non-Goals:**
- 不包含其他基础数据管理（Sector, Coverage, Template）
- 不包含报告相关功能
- 不实现 token 刷新机制

---

## Decisions

### 一、架构层

#### Decision 1: 角色存储在 app_metadata

**选择:** 将用户角色（Admin/SA/Analyst）存储在 Supabase Auth 的 `app_metadata` 中（仅服务端可修改）。

**理由:**
- ✅ JWT token 自动包含 role 信息，无需每次查询数据库
- ✅ RLS policies 可以直接从 JWT 读取角色，性能更好
- ✅ **app_metadata 只有服务端可以修改**，防止用户自行提升权限（安全性关键）

**metadata 结构:**
```json
{
  "user_metadata": {
    "full_name": "John Doe",
    "avatar_url": "..."
  },
  "app_metadata": {
    "role": "admin",
    "provider": "email"
  }
}
```

**注意:** 由于用户账号与 Analyst 信息解耦，`app_metadata` 中不需要 `analyst_id` 字段。

| metadata 类型 | 谁可以修改 | 适用场景 | 示例 |
|-------------|-----------|---------|------|
| user_metadata | 用户 + 服务端 | 个人信息 | full_name, avatar_url |
| **app_metadata** | **仅服务端** | **安全相关** | **role** |

---

#### Decision 2: 使用 RLS 实现数据库层权限控制

**选择:** 在数据库表上启用 Row Level Security (RLS)，通过 policies 控制访问。

**理由:**
- ✅ 数据库层面的安全控制，即使应用层有漏洞也能保护数据
- ✅ 自动过滤数据，减少后端代码
- ✅ 性能更好（数据库直接过滤）
- ✅ 审计友好（所有权限逻辑集中在数据库）

**RLS 辅助函数:**
```sql
CREATE OR REPLACE FUNCTION get_current_role()
RETURNS VARCHAR AS $$
  SELECT (auth.jwt()->>'app_metadata'->>'role')::VARCHAR;
$$ LANGUAGE sql SECURITY DEFINER;
```

**analyst 表 RLS policies 示例:**
```sql
ALTER TABLE analyst ENABLE ROW LEVEL SECURITY;

-- 所有认证用户可读
CREATE POLICY "All users can view analysts"
ON analyst FOR SELECT TO authenticated USING (true);

-- 只有 Admin 可写
CREATE POLICY "Only Admin can modify analysts"
ON analyst FOR ALL TO authenticated
USING (get_current_role() = 'admin')
WITH CHECK (get_current_role() = 'admin');
```

---

#### Decision 3: 用户账号与 Analyst 信息解耦

**选择:** 用户账号管理系统（Auth users）与 Analyst 信息系统（analyst 表）完全解耦。

**理由:**
- ✅ 职责清晰：用户账号用于认证，Analyst 信息用于数据记录
- ✅ 灵活性高，可以有不登录系统的 Analyst 信息记录
- ✅ 避免数据同步问题

**隐式关联规则（为未来报告功能预留）：**
- 当 User Auth 的 email 与 Analyst 的 email **一致时**，系统认为是**同一人**
- **当前阶段：** 只有 Admin 可以访问 Analyst 信息管理，SA/Analyst 不需要
- **未来报告功能：** Analyst 登录后可以查看/编辑自己的报告（报告表的 `contact_person` 字段关联到 analyst.email）
- **不使用外键关联**，通过 email 字符串匹配实现逻辑关联
- 示例：Analyst `john.doe@example.com` 登录后，只能看到 `contact_person = 'john.doe@example.com'` 的报告

**两个系统的关系:**

| 系统 | 用途 | 数据存储 | API |
|------|------|--------|------|
| **用户管理** | 认证和权限 | Supabase Auth users | `/api/users` |
| **Analyst 信息** | Analyst 数据记录 | analyst 表 | `/api/analyst-info` |

---

### 二、数据库层

#### Decision 4: 数据表设计

**选择:** 使用 Supabase PostgreSQL 原生表和 RLS，不使用 ORM。

**Region 表:**
```sql
CREATE TABLE region (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR UNIQUE NOT NULL,
  code VARCHAR UNIQUE NOT NULL,
  created_at TIMESTAMP DEFAULT now(),
  updated_at TIMESTAMP DEFAULT now()
);

ALTER TABLE region ENABLE ROW LEVEL SECURITY;

CREATE POLICY "All users can view regions"
ON region FOR SELECT TO authenticated USING (true);

CREATE POLICY "Only Admin can modify regions"
ON region FOR ALL TO authenticated
USING (get_current_role() = 'admin')
WITH CHECK (get_current_role() = 'admin');
```

**Analyst 表:**
```sql
CREATE TABLE analyst (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  full_name VARCHAR NOT NULL,
  chinese_name VARCHAR,
  email VARCHAR UNIQUE NOT NULL,
  suffix VARCHAR,
  region_id UUID REFERENCES region(id) ON DELETE SET NULL,
  sfc VARCHAR,
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMP DEFAULT now(),
  updated_at TIMESTAMP DEFAULT now()
);

ALTER TABLE analyst ENABLE ROW LEVEL SECURITY;

CREATE POLICY "All users can view analysts"
ON analyst FOR SELECT TO authenticated USING (true);

CREATE POLICY "Only Admin can manage analysts"
ON analyst FOR ALL TO authenticated
USING (get_current_role() = 'admin')
WITH CHECK (get_current_role() = 'admin');
```

---

### 三、后端架构

#### Decision 5: 项目结构组织

**选择:** 使用功能分层结构（api/models/core）。

**目录结构:**
```
backend/
├── src/
│   ├── main.py                 # FastAPI 应用入口
│   ├── api/                    # API 路由
│   │   ├── auth.py
│   │   ├── users.py
│   │   ├── regions.py
│   │   └── analyst_info.py
│   ├── core/                   # 核心配置
│   │   ├── config.py
│   │   ├── security.py
│   │   └── supabase.py
│   └── models/                 # Pydantic 数据模型
│       ├── auth.py
│       ├── user.py
│       ├── region.py
│       └── analyst.py
├── scripts/
│   └── init_admin.py
└── .env.example
```

**理由:** 不使用 ORM（如 SQLAlchemy）
- Supabase Python Client 已经提供良好的数据库操作 API
- RLS 在数据库层自动处理，无需复杂的 ORM 关系

---

#### Decision 6: 数据验证策略

**选择:** 使用 Pydantic 自动验证。

**理由:**
- ✅ 代码简洁（定义一次模型，到处复用）
- ✅ 类型安全（IDE 自动提示）
- ✅ 自动生成 API 文档（OpenAPI schema）

**示例:**
```python
from pydantic import BaseModel, EmailStr, Field

class AnalystCreate(BaseModel):
    full_name: str = Field(..., min_length=1)
    email: EmailStr
    region_id: UUID | None = None
    chinese_name: str | None = None
    suffix: str | None = None
    sfc: str | None = None
```

---

#### Decision 7: API 错误响应格式统一

**选择:** 实现统一的错误响应格式。

**实现:**
```python
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": "Request failed",
            "error": exc.detail,
            "data": None
        }
    )
```

---

#### Decision 8: JWT Token 配置

**选择:** Token 有效期 24 小时，过期后要求重新登录。

**配置:**
- 在 Supabase Dashboard 设置 `JWT expiry limit = 86400`（24 小时）

**理由:**
- ✅ 简化第一版实现，无需 refresh token 逻辑
- ✅ 24 小时满足一天的使用需求
- ✅ 平衡安全性和用户体验

---

#### Decision 9: 初始化 Admin 用户

**选择:** 使用独立脚本 `backend/scripts/init_admin.py` 自动创建 Admin 用户并配置 JWT 有效期。

**脚本功能:**
1. 创建默认 Admin 用户（email: `admin@neolyst.com`, password: `Admin123`）
2. 自动配置 JWT 有效期为 24 小时（通过 Supabase Management API）
3. 如果 API 失败，输出手动配置指导

**完整实现见附录。**

---

### 四、前端架构

#### Decision 10: Token 存储方式

**选择:** 将 JWT token 存储在 localStorage 中。

**理由:**
- ✅ 实现简单，无需复杂的 Cookie 配置
- ✅ 跨请求自动携带（通过 Axios 拦截器）
- ✅ 持久化存储，刷新页面后仍保持登录

**权衡:**
- ⚠️ XSS 风险：如果网站有 XSS 漏洞，攻击者可以窃取 token
- 缓解：确保输入验证和输出编码，防止 XSS；后续可迁移到 HttpOnly Cookie

**Axios 拦截器配置:**
```typescript
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

apiClient.interceptors.response.use(
  response => response,
  error => {
    if (error.response?.status === 401) {
      localStorage.removeItem('auth_token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)
```

---

#### Decision 11: 状态管理方案

**选择:** 使用 Vue 3 的 `provide/inject` 模式配合 `reactive()`。

**理由:**
- ✅ Vue 3 原生支持，无需额外依赖
- ✅ 确保状态是单例，避免多实例不同步
- ✅ 对于当前需求（只有认证状态），完全够用

**实现框架:**
```typescript
// stores/auth.ts
export function provideAuthStore() {
  const userState = reactive({
    token: localStorage.getItem('auth_token') || null,
    user: JSON.parse(localStorage.getItem('user_info') || 'null'),
    isAuthenticated: !!localStorage.getItem('auth_token')
  })

  const login = (token: string, user: any) => { /* ... */ }
  const logout = () => { /* ... */ }

  provide(AUTH_STORE_KEY, { userState, login, logout })
}

export function useAuth() {
  return inject(AUTH_STORE_KEY)
}
```

**权衡:** 如果后续状态变复杂，可以迁移到 Pinia（成本不高）

---

#### Decision 12: 桌面和导航设计

**选择:**
1. 桌面功能卡片点击后在新标签页打开
2. 功能页面不显示返回按钮，用户直接关闭标签页返回桌面

**理由:**
- ✅ 方便用户同时打开多个管理页面
- ✅ 符合传统桌面应用的交互习惯
- ✅ 共享 localStorage（同域名部署），认证状态保持
- ✅ 减少页面冗余元素

**实现:**
```vue
<template>
  <a :href="pageUrl" target="_blank" rel="noopener">
    <div class="icon">{{ icon }}</div>
    <div class="title">{{ title }}</div>
    <div class="description">{{ description }}</div>
    <div v-if="isComingSoon" class="badge">Coming Soon</div>
  </a>
</template>
```

---

#### Decision 13: 粒子背景实现

**选择:** 使用原生 Canvas 2D API 手写粒子效果，不依赖第三方库。

**粒子配置:**
```typescript
const particleConfig = {
  count: 120,
  speed: 2,
  size: { min: 1, max: 3 },
  opacity: { min: 0.3, max: 0.7 },
  color: 'blue-cyan gradient',  // hue: 200-260
  connectionDistance: 140,
  mouseInteraction: false,
  pulseSpeed: 0.15
}
```

**理由:**
- ✅ 零依赖，不增加包大小（~5KB vs tsparticles ~40KB）
- ✅ 轻量级，代码量 < 200 行
- ✅ 高性能，Canvas 2D 支持 60fps

---

#### Decision 14: 表格组件选择

**选择:** 使用简单的表格布局，不使用第三方表格库（如 AG Grid）。

**理由:**
- ✅ 第一版需求简单，无需复杂功能
- ✅ 减少依赖和包大小
- ✅ 使用 Tailwind CSS 实现表格样式

---

### 五、部署

#### Decision 15: 部署策略

**选择:** 使用同域名部署（Vercel 一体化）。

**理由:**
- ✅ Vercel 一体化部署（一个项目，前后端都在里面）
- ✅ 零配置 `vercel.json` 处理路由
- ✅ 不需要 CORS 代码（减少维护）
- ✅ git push 自动部署
- ✅ 自动 HTTPS、CDN

**vercel.json:**
```json
{
  "rewrites": [
    { "source": "/api/(.*)", "destination": "/api/$1" },
    { "source": "/(.*)", "destination": "/" }
  ]
}
```

---

## API 接口设计

### 认证相关 API

| 方法 | 端点 | 说明 | 权限 |
|------|--------|------|------|
| POST | `/api/auth/login` | 用户登录，返回 JWT Token | 公开 |
| POST | `/api/auth/logout` | 用户登出 | 认证用户 |
| GET | `/api/auth/me` | 获取当前用户信息 | 认证用户 |
| POST | `/api/auth/forgot-password` | 请求重置密码，发送邮件 | 公开 |
| POST | `/api/auth/reset-password` | 通过邮件链接重置密码 | 公开（带 token） |
| PUT | `/api/auth/change-password` | 登录状态下修改密码 | 认证用户 |

### 用户管理 API

| 方法 | 端点 | 说明 | 权限 |
|------|--------|------|------|
| GET | `/api/users` | 获取用户列表（支持搜索） | 仅 Admin |
| POST | `/api/users` | 创建用户 | 仅 Admin |
| PUT | `/api/users/{id}` | 更新用户信息 | 仅 Admin |
| PUT | `/api/users/{id}/password` | 修改密码 | 仅 Admin |
| PUT | `/api/users/{id}/role` | 修改角色 | 仅 Admin |
| DELETE | `/api/users/{id}` | 删除用户 | 仅 Admin |
| POST | `/api/users/check-email` | 检查邮箱唯一性 | 仅 Admin |
| PUT | `/api/users/{id}/toggle-status` | 启用/禁用账号 | 仅 Admin |

### Region 管理 API

| 方法 | 端点 | 说明 | 权限 |
|------|--------|------|------|
| GET | `/api/regions` | 获取地区列表 | 所有认证用户 |
| POST | `/api/regions` | 创建地区 | 仅 Admin |
| PUT | `/api/regions/{id}` | 更新地区 | 仅 Admin |
| DELETE | `/api/regions/{id}` | 删除地区 | 仅 Admin |

### Analyst 信息管理 API

| 方法 | 端点 | 说明 | 权限 |
|------|--------|------|------|
| GET | `/api/analyst-info` | 获取 Analyst 信息列表（支持搜索） | 所有认证用户 |
| POST | `/api/analyst-info` | 创建 Analyst 信息 | 仅 Admin |
| PUT | `/api/analyst-info/{id}` | 更新 Analyst 信息 | 仅 Admin |
| DELETE | `/api/analyst-info/{id}` | 删除 Analyst 信息 | 仅 Admin |

**注意:** 此 API 只管理 Analyst 信息，不创建或修改用户账号。`email` 字段仅用于业务记录。

---

## Risks / Trade-offs

| Risk | 缓解措施 |
|-------|----------|
| **Supabase Auth Admin API 权限问题** | service_role_key 存储在后端环境变量中，不提交到 git |
| **RLS Policies 调试困难** | 在 Supabase Dashboard 的 SQL Editor 中测试 policies |
| **前端 Token 存在 localStorage 的 XSS 风险** | 输入验证和输出编码，防止 XSS；后续可迁移到 HttpOnly Cookie |
| **粒子效果性能影响低端设备** | 使用 `requestAnimationFrame` 确保流畅；登录成功后立即停止动画 |
| **Analyst 和 Region 的外键约束** | 使用 `ON DELETE SET NULL` 确保级联删除不报错 |

---

## Migration Plan

不适用（这是新功能，无现有数据迁移）

**部署步骤:**
1. 在 Supabase 中创建 region 表和 RLS policies
2. 在 Supabase 中创建 analyst 表和 RLS policies
3. 创建 RLS 辅助函数 `get_current_role()`
4. 配置后端环境变量（`SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`）
5. 运行 `backend/scripts/init_admin.py` 创建 Admin 用户并配置 JWT 有效期
6. 使用 Admin 账号登录验证
7. 部署到 Vercel

---

## 附录：初始化脚本完整实现

```python
# backend/scripts/init_admin.py
import sys
import os
import requests
sys.path.insert(0, '..')

from supabase import create_client

def init_admin():
    """初始化默认 Admin 用户并配置系统"""

    supabase_url = os.getenv('SUPABASE_URL')
    service_role_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

    if not supabase_url or not service_role_key:
        print("❌ Missing environment variables: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY")
        sys.exit(1)

    client = create_client(supabase_url, service_role_key)

    admin_email = "admin@neolyst.com"
    admin_password = "Admin123"

    # 1. 创建 Admin 用户
    print("📝 Creating admin user...")
    try:
        user = client.auth.admin.create_user({
            'email': admin_email,
            'password': admin_password,
            'email_confirm': True,
            'user_metadata': { 'full_name': 'System Administrator' },
            'app_metadata': { 'role': 'admin', 'provider': 'email' }
        })
        print(f"✅ Admin user created: {admin_email}")
        print(f"   Password: {admin_password}")
    except Exception as e:
        if "already" in str(e).lower():
            print("ℹ️  Admin user already exists")
        else:
            print(f"❌ Failed to create admin: {e}")

    # 2. 配置 JWT 有效期为 24 小时
    print("\n⏰ Configuring JWT token expiry...")
    configure_jwt_expiry(supabase_url, service_role_key)

    print("\n✅ Initialization complete!")
    print("🔐 Please change the default password after first login")

def configure_jwt_expiry(supabase_url, service_role_key):
    """配置 JWT Token 有效期为 24 小时"""

    project_ref = supabase_url.replace('https://', '').replace('.supabase.co', '').split('//')[1]
    management_url = f"https://supabase.com/management/v1/projects/{project_ref}/config/jwt"

    headers = {
        'Authorization': f'Bearer {service_role_key}',
        'Content-Type': 'application/json'
    }

    data = { 'jwt_expiry_limit': 86400 }

    try:
        response = requests.patch(management_url, json=data, headers=headers)
        if response.status_code == 200:
            print("✅ JWT expiry set to 24 hours (86400 seconds)")
        else:
            print("⚠️  Could not configure JWT expiry via API")
            print("   Please manually configure in Supabase Dashboard:")
            print("   Settings → Auth → JWT Settings → JWT expiry limit = 86400")
    except Exception as e:
        print(f"⚠️  Failed to configure JWT expiry: {e}")
        print("   Please manually configure in Supabase Dashboard:")
        print("   Settings → Auth → JWT Settings → JWT expiry limit = 86400")

if __name__ == "__main__":
    init_admin()
```
