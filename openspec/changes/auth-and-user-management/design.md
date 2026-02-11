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
- 设计文档: `openspec/changes/archive/2026-02-10-initial-system-planning/design.md` (Decision 9 详细说明了 RLS 设计)

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
- 不实现 token 刷新机制（短期 token 即可，后期增强）

**注意:** 本变更包含 Region 和 Analyst 表的完整 CRUD 管理功能。

## Decisions

### Decision 1: 角色信息存储在 Supabase Auth app_metadata 中

**选择:** 将用户角色（Admin/SA/Analyst）存储在 Supabase Auth 的 **app_metadata** 中（仅服务端可修改），而非 user_metadata 或 analyst 表。

**理由:**
- ✅ JWT token 自动包含 role 信息，无需每次查询数据库
- ✅ RLS policies 可以直接从 JWT 读取角色，性能更好
- ✅ **app_metadata 只有服务端可以修改**，防止用户自行提升权限（安全性关键）
- ✅ 角色信息集中管理，避免数据库同步问题

**metadata 结构:**
```json
{
  "user_metadata": {
    "full_name": "John Doe",  // 用户可修改的个人信息
    "avatar_url": "..."          // 可选：用户头像
  },
  "app_metadata": {
    "role": "admin",            // ← 关键安全信息，仅服务端可修改
    "provider": "email"
  }
}
```

**注意:** `app_metadata` 中不再需要 `analyst_id` 字段，因为 analyst 表和 Auth 用户是解耦的。

**关键区别:**
| metadata 类型 | 谁可以修改 | 适用场景 | 示例 |
|-------------|-----------|---------|------|
| user_metadata | 用户 + 服务端 | 个人信息 | full_name, avatar_url |
| **app_metadata** | **仅服务端** | **安全相关** | **role, analyst_id** |

**权衡:**
- 如果需要修改角色，需要使用 Supabase Admin API（service_role_key）
- 解决方案: 后期提供 Admin API 统一管理角色修改

### Decision 2: 使用 Supabase RLS 实现数据库层权限控制

**选择:** 在数据库表上启用 Row Level Security (RLS)，通过 policies 控制访问。

**理由:**
- ✅ 数据库层面的安全控制，即使应用层有漏洞也能保护数据
- ✅ 自动过滤数据，减少后端代码
- ✅ 性能更好（数据库直接过滤，不传输到应用层）
- ✅ 审计友好（所有权限逻辑集中在数据库）

**RLS 辅助函数:**
```sql
-- 从 JWT 提取当前用户角色
CREATE OR REPLACE FUNCTION get_current_role()
RETURNS VARCHAR AS $$
  SELECT (auth.jwt()->>'app_metadata'->>'role')::VARCHAR;
$$ LANGUAGE sql SECURITY DEFINER;
```

**注意:** 不再需要 `get_current_analyst_id()` 函数，因为所有 `*_by` 字段（created_by, submitted_by 等）都存储的是 `user_id`（auth.uid()），而不是 analyst_id。

**analyst 表 RLS policies:**
```sql
-- 启用 RLS
ALTER TABLE analyst ENABLE ROW LEVEL SECURITY;

-- 所有认证用户可读
CREATE POLICY "All users can view analysts"
ON analyst FOR SELECT
TO authenticated
USING (true);

-- 只有 Admin 可写
CREATE POLICY "Only Admin can modify analysts"
ON analyst FOR ALL
TO authenticated
USING (get_current_role() = 'admin')
WITH CHECK (get_current_role() = 'admin');
```

**替代方案对比:**
- ❌ 应用层权限检查: 代码复杂，容易遗漏，安全性低
- ❌ 数据库触发器: 无法实现灵活的角色策略
- ✅ RLS: 集中管理，安全可靠，性能优秀

### Decision 3: 初始化 Admin 用户使用独立脚本

**选择:** 创建 `backend/scripts/init_admin.py` 脚本，自动创建 Admin 用户并配置 JWT 有效期，而非手动操作。

**理由:**
- ✅ 更安全（不需要暴露临时的不安全的 API）
- ✅ 简单直接，运行一次即可完成所有初始化
- ✅ 适合开发和生产环境部署
- ✅ 自动配置 JWT 有效期，减少手动操作错误
- ✅ 可以硬编码默认值，无需额外配置

**脚本实现:**
```python
# backend/scripts/init_admin.py
import sys
import os
import requests
sys.path.insert(0, '..')

from supabase import create_client

def init_admin():
    """初始化默认 Admin 用户并配置系统"""

    # 从环境变量获取配置
    supabase_url = os.getenv('SUPABASE_URL')
    service_role_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

    if not supabase_url or not service_role_key:
        print("❌ Missing environment variables: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY")
        sys.exit(1)

    # 1. 创建 Admin 用户
    print("📝 Creating admin user...")
    client = create_client(supabase_url, service_role_key)

    admin_email = "admin@neolyst.com"
    admin_password = "Admin123"

    try:
        user = client.auth.admin.create_user({
            'email': admin_email,
            'password': admin_password,
            'email_confirm': True,
            'user_metadata': {
                'full_name': 'System Administrator'
            },
            'app_metadata': {
                'role': 'admin',
                'provider': 'email'
            }
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

    # Supabase Management API endpoint
    project_ref = supabase_url.replace('https://', '').replace('.supabase.co', '').split('//')[1]
    management_url = f"https://supabase.com/management/v1/projects/{project_ref}/config/jwt"

    headers = {
        'Authorization': f'Bearer {service_role_key}',
        'Content-Type': 'application/json'
    }

    data = {
        'jwt_expiry_limit': 86400  # 24 小时（秒）
    }

    try:
        response = requests.patch(management_url, json=data, headers=headers)
        if response.status_code == 200:
            print("✅ JWT expiry set to 24 hours (86400 seconds)")
        else:
            print(f"⚠️  Could not configure JWT expiry via API")
            print(f"   Please manually configure in Supabase Dashboard:")
            print(f"   Settings → Auth → JWT Settings → JWT expiry limit = 86400")
    except Exception as e:
        print(f"⚠️  Failed to configure JWT expiry: {e}")
        print(f"   Please manually configure in Supabase Dashboard:")
        print(f"   Settings → Auth → JWT Settings → JWT expiry limit = 86400")

if __name__ == "__main__":
    init_admin()
```

**脚本功能：**
1. 创建默认 Admin 用户（email: `admin@neolyst.com`, password: `Admin123`）
2. 自动配置 JWT Token 有效期为 24 小时（86400 秒）
   - 通过 Supabase Management API 自动配置
   - 如果 API 失败，输出手动配置指导

**关键点：**
- `role` 只在 `app_metadata` 中（安全）
- `full_name` 在 `user_metadata` 中（用户可修改）
- **只创建 Auth 用户，不创建 analyst 记录**（两者解耦，Admin 不需要业务信息）

**权衡:**
- ✅ 一键完成所有初始化配置
- ✅ 减少 Docker/手动配置错误
- ⚠️ 默认密码需要首次登录后手动修改
- ⚠️ JWT 配置需要 `service_role_key` 权限
- 缓解: 在部署文档中明确说明
- 缓解: 在部署文档中明确说明步骤

### Decision 4: 前端使用 localStorage 存储 Token

**选择:** 将 JWT token 存储在浏览器的 localStorage 中。

**理由:**
- ✅ 实现简单，无需复杂的 Cookie 配置
- ✅ 跨请求自动携带（通过 Axios 拦截器）
- ✅ 持久化存储，刷新页面后仍保持登录

**权衡:**
- ⚠️ XSS 风险：如果网站有 XSS 漏洞，攻击者可以窃取 token
- 缓解:
  - 使用 HttpOnly Cookie 是更安全的替代方案，但实现复杂
  - 对于第一版，localStorage 可接受（后续可优化）
  - 确保输入验证和输出编码，防止 XSS

**Axios 拦截器配置:**
```typescript
// frontend/src/api/client.ts
import axios from 'axios'

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000'
})

// 请求拦截器：自动添加 Token
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 响应拦截器：处理 401
apiClient.interceptors.response.use(
  response => response,
  error => {
    if (error.response?.status === 401) {
      // Token 无效或过期，清除并跳转登录
      localStorage.removeItem('auth_token')
      localStorage.removeItem('user_info')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export default apiClient
```

### Decision 5: 粒子背景效果使用 Canvas 2D

**选择:** 使用原生 Canvas 2D API 手写粒子效果，不依赖第三方库。

**理由:**
- ✅ 零依赖，不增加包大小
- ✅ 轻量级，代码量 < 200 行
- ✅ 高性能，Canvas 2D 支持 60fps
- ✅ 完全可控，自定义所有行为

**粒子配置:**
```typescript
const particleConfig = {
  count: 120,                    // 粒子数量
  speed: 2,                      // 移动速度
  size: { min: 1, max: 3 },     // 粒子大小
  opacity: { min: 0.3, max: 0.7 }, // 透明度范围
  color: 'blue-cyan gradient',     // 蓝色-青色渐变 (hue: 200-260)
  connectionDistance: 140,         // 连线距离阈值
  mouseInteraction: false,         // 禁用鼠标交互
  pulseSpeed: 0.15               // 脉冲速度
}
```

**替代方案对比:**
| 方案 | 包大小 | 性能 | 依赖 |
|------|--------|------|------|
| Canvas 2D 手写 | ~5KB | ⭐⭐⭐⭐⭐ | 无 |
| tsparticles | ~40KB | ⭐⭐⭐⭐ | 有 |
| three.js | ~600KB | ⭐⭐⭐ | 有 |

### Decision 7: JWT Token 过期处理策略

**选择:** Token 有效期设置为 24 小时，过期后要求用户重新登录，暂不实现 refresh token 机制。

**配置:**
- 在 Supabase Dashboard 中设置 `JWT expiry limit` 为 **24 小时**（86400 秒）
- 位置：Settings → Auth → JWT Settings

**理由:**
- ✅ 简化第一版实现，无需 refresh token 逻辑
- ✅ 24 小时满足一天的使用需求，用户大部分时间免登录
- ✅ 对于内部系统，每天重新登录一次的 UX 可接受
- ✅ 平衡安全性和用户体验

**权衡:**
- ⚠️ 用户体验：24 小时后需要重新登录
- ⚠️ 安全性：Token 有效期较长，被盗后可使用 24 小时
- 缓解：
  - 内部系统使用，风险可控
  - 后期可实现 refresh token 机制（第二版）
  - 可实现"在其他设备登出"功能强制 Token 失效

**Token 过期检测:**
```typescript
// Axios 响应拦截器
apiClient.interceptors.response.use(
  response => response,
  error => {
    if (error.response?.status === 401) {
      // 清除本地状态并跳转登录
      logout()
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)
```

### Decision 8: 功能卡片全部显示占位状态

**选择:** 桌面主页显示所有规划的功能卡片，但都标记为 "Coming Soon"，点击后显示占位页面。

**理由:**
- ✅ 让用户了解完整的功能规划
- ✅ 避免后期频繁修改主页添加卡片
- ✅ 清晰传达当前开发进度

**实现:**
```vue
<!-- DesktopCard.vue -->
<template>
  <a :href="pageUrl" target="_blank" class="card">
    <div class="icon">{{ icon }}</div>
    <div class="title">{{ title }}</div>
    <div class="description">{{ description }}</div>
    <div v-if="isComingSoon" class="badge">Coming Soon</div>
  </a>
</template>

<script setup lang="ts">
const props = defineProps<{
  icon: string
  title: string
  description: string
  pageUrl: string
  isComingSoon?: boolean
}>()
</script>
```

### Decision 9: 后端项目结构组织

**选择:** 使用功能分层结构（api/models/core），而非 MVC 结构。

**理由:**
- ✅ FastAPI 推荐 API-first 结构
- ✅ 清晰的关注点分离
- ✅ 便于小团队协作

**目录结构:**
```
backend/
├── src/
│   ├── main.py                 # FastAPI 应用入口
│   ├── api/                    # API 路由
│   │   ├── __init__.py
│   │   ├── auth.py              # 认证相关 API
│   │   └── analysts.py          # 用户管理 API (后续变更)
│   ├── core/                   # 核心配置
│   │   ├── __init__.py
│   │   ├── config.py            # 配置（环境变量等）
│   │   ├── security.py          # JWT 验证等安全相关
│   │   └── supabase.py         # Supabase 客户端初始化
│   ├── models/                 # Pydantic 数据模型
│   │   ├── __init__.py
│   │   ├── analyst.py
│   │   └── auth.py
│   └── db/                    # 数据库操作（直接使用 Supabase Client，无需 ORM）
│       └── __init__.py
├── scripts/
│   └── init_admin.py         # 初始化 Admin 脚本
└── .env.example
```

**为什么不使用 ORM（如 SQLAlchemy）:**
- Supabase Python Client 已经提供良好的数据库操作 API
- RLS 在数据库层自动处理，应用层无需复杂的 ORM 关系
- 减少一层抽象，代码更直接

### Decision 10: Region 和 Analyst 数据表设计

**选择:** 使用 Supabase PostgreSQL 原生表和 RLS，不使用 ORM。

**理由:**
- ✅ Supabase Python Client 提供直接操作数据库的能力
- ✅ RLS 在数据库层自动应用
- ✅ 简化代码，无需额外的 ORM 层

**Region 表结构:**
```sql
CREATE TABLE region (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR UNIQUE NOT NULL,  -- 地区名称（如 "China"）
  code VARCHAR UNIQUE NOT NULL,  -- 地区代码（如 "CN"）
  created_at TIMESTAMP DEFAULT now(),
  updated_at TIMESTAMP DEFAULT now()
);

-- 启用 RLS
ALTER TABLE region ENABLE ROW LEVEL SECURITY;

-- 所有认证用户可读
CREATE POLICY "All users can view regions"
ON region FOR SELECT
TO authenticated
USING (true);

-- 只有 Admin 可写
CREATE POLICY "Only Admin can modify regions"
ON region FOR ALL
TO authenticated
USING (get_current_role() = 'admin')
WITH CHECK (get_current_role() = 'admin');
```

**Analyst 表结构:**
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

-- 启用 RLS
ALTER TABLE analyst ENABLE ROW LEVEL SECURITY;

-- 所有认证用户可读
CREATE POLICY "All users can view analysts"
ON analyst FOR SELECT
TO authenticated
USING (true);

-- 只有 Admin 可写
CREATE POLICY "Only Admin can manage analysts"
ON analyst FOR ALL
TO authenticated
USING (get_current_role() = 'admin')
WITH CHECK (get_current_role() = 'admin');
```

**外键关系:**
- `analyst.region_id` → `region.id` (ON DELETE SET NULL)
- 删除 Region 时，关联的 Analyst 的 region_id 设为 NULL

### Decision 11: 用户账号与业务信息解耦

**选择:** 用户账号管理系统（Auth users）与业务信息系统（analyst 表）完全解耦，分为两个独立功能。

**理由:**
- ✅ 用户账号：用于认证和权限控制，存储邮箱、密码、角色
- ✅ 业务信息：用于业务数据记录，存储分析师姓名、地区、SFC 编号等
- ✅ 解耦设计更灵活，可以有不登录系统的业务信息记录
- ✅ 可以独立管理用户账号和业务信息
- ✅ 避免数据同步问题

**两个系统的关系：**

| 系统 | 用途 | 数据表 | 功能 |
|------|------|--------|------|
| **用户管理** | 认证和权限 | Supabase Auth users | 创建/编辑/删除用户，修改密码，修改角色 |
| **业务信息** | 业务数据记录 | analyst 表 | 创建/编辑/删除业务信息，关联地区 |

**用户管理功能（Feature 4）：**
- 管理所有 Auth 用户（Admin、SA、Analyst）
- 创建用户时直接设置邮箱、密码、角色
- 修改用户信息（姓名、邮箱）
- 修改用户密码
- 修改用户角色（在 Admin/SA/Analyst 之间切换）
- 启用/禁用用户账号
- 删除用户账号

**业务信息管理功能（Feature 6）：**
- 管理分析师的业务信息
- 创建业务信息（无需创建用户账号）
- 编辑业务信息信息
- 删除业务信息
- 邮箱字段仅用于业务记录，不与认证系统关联

**API 设计：**
- 用户管理：`/api/users` (CRUD, 修改密码, 修改角色, 启用/禁用)
- 业务信息：`/api/analyst-profiles` (CRUD)

**前端页面：**
- 用户管理页面（仅 Admin 可见）
- 业务信息管理页面（仅 Admin 可见）

**权衡:**
- ✅ 灵活性高，可以独立管理两个系统
- ✅ 数据结构清晰，职责分离
- ⚠️ 需要明确告知用户两个功能的区别
- ⚠️ 同一个人可能同时有用户账号和业务信息（但系统不强制关联）
- ✅ 后续版本可添加邮件发送功能（可选）

### Decision 12: 前端状态管理使用 provide/inject 确保单例

**选择:** 使用 Vue 3 的 `provide/inject` 模式配合 `reactive()` 确保状态单例，而非简单的 composable 函数。

**理由:**
- ✅ Vue 3 原生支持，无需额外依赖
- ✅ 确保状态是单例，避免多实例不同步
- ✅ 对于当前需求（只有认证状态），完全够用

**状态管理实现:**
```typescript
// frontend/src/stores/auth.ts
import { reactive, provide, inject } from 'vue'

const AUTH_STORE_KEY = Symbol('authStore')

// 创建响应式状态（模块级别单例）
const userState = reactive({
  token: localStorage.getItem('auth_token') || null,
  user: JSON.parse(localStorage.getItem('user_info') || 'null'),
  isAuthenticated: !!localStorage.getItem('auth_token')
})

export function provideAuthStore() {
  const login = (token: string, user: any) => {
    localStorage.setItem('auth_token', token)
    localStorage.setItem('user_info', JSON.stringify(user))
    userState.token = token
    userState.user = user
    userState.isAuthenticated = true
  }

  const logout = () => {
    localStorage.removeItem('auth_token')
    localStorage.removeItem('user_info')
    userState.token = null
    userState.user = null
    userState.isAuthenticated = false
  }

  const store = {
    userState,
    login,
    logout
  }

  provide(AUTH_STORE_KEY, store)
  return store
}

export function useAuth() {
  const store = inject<ReturnType<typeof provideAuthStore>>(AUTH_STORE_KEY)
  if (!store) {
    throw new Error('useAuth() must be called after provideAuthStore()')
  }
  return store
}
```

**在 App.vue 中 provide:**
```vue
<!-- App.vue -->
<script setup lang="ts">
import { provideAuthStore } from '@/stores/auth'

provideAuthStore()
</script>

<template>
  <router-view />
</template>
```

**在子组件中使用:**
```vue
<!-- Login.vue -->
<script setup lang="ts">
import { useAuth } from '@/stores/auth'

const { userState, login } = useAuth()
</script>
```

**权衡:**
- 如果后续状态变复杂，可以迁移到 Pinia（成本不高）
- 对于当前需求（只有认证状态），provide/inject 足够用

**选择:** 使用简单的表格布局，不使用第三方表格库（如 AG Grid）。

**理由:**
- ✅ 第一版需求简单，无需复杂功能
- ✅ 减少依赖和包大小
- ✅ 使用 Tailwind CSS 实现表格样式

**表格样式:**
```vue
<!-- 使用 Tailwind CSS 实现表格 -->
<table class="min-w-full divide-y divide-white/10">
  <thead class="bg-zinc-900">
    <tr>
      <th class="px-4 py-3 text-left text-sm font-medium text-zinc-400">Name</th>
      <th class="px-4 py-3 text-left text-sm font-medium text-zinc-400">Email</th>
      <!-- ... -->
    </tr>
  </thead>
  <tbody class="bg-zinc-950/50">
    <tr v-for="item in items" :key="item.id" class="hover:bg-zinc-800/50">
      <td class="px-4 py-3 text-sm">{{ item.full_name }}</td>
      <!-- ... -->
    </tr>
  </tbody>
</table>
```

### Decision 13: 数据验证策略

**选择:** 使用 Pydantic 自动验证，不手动验证。

**理由:**
- ✅ 代码简洁（定义一次模型，到处复用）
- ✅ 类型安全（IDE 自动提示）
- ✅ 自动生成 API 文档（OpenAPI schema）

**实现:**
```python
from pydantic import BaseModel, EmailStr, Field

class AnalystCreate(BaseModel):
    full_name: str = Field(..., min_length=1)
    email: EmailStr
    region_id: UUID | None = None
    chinese_name: str | None = None
    suffix: str | None = None
    sfc: str | None = None
    is_active: bool = True
    # 注意：不包含 role 字段
```

### Decision 14: API 错误响应格式统一

**选择:** 实现统一的错误响应格式，而非依赖 FastAPI 默认行为。

**理由:**
- ✅ 前端只需处理一种错误格式
- ✅ 用户体验一致
- ✅ 便于国际化

**实现:**
```python
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

app = FastAPI()

# 统一错误响应格式
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

### Decision 15: 部署策略

**选择:** 使用同域名部署（Vercel 一体化），简化部署流程。

**理由:**
- ✅ Vercel 一体化部署（一个项目，前后端都在里面）
- ✅ 零配置 `vercel.json` 处理路由
- ✅ 不需要 CORS 代码（减少维护）
- ✅ git push 自动部署
- ✅ 自动 HTTPS、CDN

**实现:**
```json
{
  "rewrites": [
    { "source": "/api/(.*)", "destination": "/api/$1" },
    { "source": "/(.*)", "destination": "/" }
  ]
}
```

**部署命令:**
```bash
git push
# 自动部署，无需手动操作
```

**注意:** 不需要 CORS 中间件配置（同域名部署）。

### Decision 16: 前端页面打开方式

**选择:** 保持新标签页设计（符合原型，方便多任务工作）。

**理由:**
- ✅ 符合原始设计（Decision 7.1）
- ✅ 方便用户同时打开多个管理页面
- ✅ 共享 localStorage（同域名部署）
- ✅ 实现简单：`<a target="_blank">`

**实现:**
```vue
<!-- DesktopCard.vue -->
<template>
  <a :href="pageUrl" target="_blank" rel="noopener">
    <div class="icon">{{ icon }}</div>
    <div class="title">{{ title }}</div>
    <div class="description">{{ description }}</div>
  </a>
</template>
```

## API 接口设计

### 认证相关 API

| 方法 | 端点 | 说明 | 权限 |
|------|--------|------|------|
| POST | `/api/auth/login` | 用户登录，返回 JWT Token | 公开 |
| POST | `/api/auth/logout` | 用户登出（可选，前端清除 token） | 认证用户 |
| GET | `/api/auth/me` | 获取当前用户信息 | 认证用户 |
| POST | `/api/auth/forgot-password` | 请求重置密码，发送邮件 | 公开 |
| POST | `/api/auth/reset-password` | 通过邮件链接重置密码 | 公开（带 token） |
| PUT | `/api/auth/change-password` | 登录状态下修改密码 | 认证用户 |

**登录请求：**
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

**登录响应：**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "role": "analyst",
    "full_name": "John Doe"
  }
}
```

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

**创建用户请求：**
```json
{
  "full_name": "John Doe",
  "email": "john.doe@example.com",
  "role": "analyst",
  "password": "InitialPassword123"
}
```

**修改角色请求：**
```json
{
  "role": "admin"
}
```

### Region 管理 API

| 方法 | 端点 | 说明 | 权限 |
|------|--------|------|------|
| GET | `/api/regions` | 获取地区列表 | 仅 Admin |
| POST | `/api/regions` | 创建地区 | 仅 Admin |
| PUT | `/api/regions/{id}` | 更新地区 | 仅 Admin |
| DELETE | `/api/regions/{id}` | 删除地区 | 仅 Admin |

**创建/更新 Region 请求：**
```json
{
  "name": "China",
  "code": "CN"
}
```

### Analyst 业务信息管理 API

| 方法 | 端点 | 说明 | 权限 |
|------|--------|------|------|
| GET | `/api/analyst-info` | 获取 Analyst 业务信息列表（支持搜索） | 仅 Admin |
| POST | `/api/analyst-info` | 创建 Analyst 业务信息 | 仅 Admin |
| PUT | `/api/analyst-info/{id}` | 更新 Analyst 业务信息 | 仅 Admin |
| DELETE | `/api/analyst-info/{id}` | 删除 Analyst 业务信息 | 仅 Admin |

**创建业务信息请求：**
```json
{
  "full_name": "John Doe",
  "chinese_name": "张三",
  "email": "john.doe@example.com",
  "suffix": "CFA",
  "region_id": "uuid",
  "sfc": "ABC123"
}
```

**注意：**
- 此 API 只管理业务信息，不创建或修改用户账号
- `email` 字段仅用于业务记录，不与认证系统关联
- 如需为分析师创建登录账号，请使用用户管理功能

## Risks / Trade-offs

**Risk 1: Supabase Auth Admin API 权限问题**

**描述:** 初始化脚本需要使用 Supabase Admin API，需要 service_role_key（具有完全权限）。

**缓解:**
- service_role_key 存储在后端环境变量中，不提交到 git
- 脚本只在部署时运行一次，风险可控
- 生产环境使用独立的 Supabase 项目（隔离）

**Risk 2: RLS Policies 调试困难**

**描述:** RLS policies 在数据库层，调试时看不到详细的错误信息。

**缓解:**
- 在 Supabase Dashboard 的 SQL Editor 中测试 policies
- 使用不同角色的 JWT token 验证权限
- 添加详细的日志记录（记录 RLS 拒绝的查询）

**Risk 3: 前端 Token 存在 localStorage 的 XSS 风险**

**描述:** 如果网站存在 XSS 漏洞，攻击者可以窃取 token。

**缓解:**
- 输入验证和输出编码，防止 XSS
- Content Security Policy (CSP) 限制外部脚本
- 后续版本可迁移到 HttpOnly Cookie（如果需要更高安全性）

**Risk 4: 粒子效果性能影响低端设备**

**描述:** 120 个粒子 + 连线可能在低端设备上掉帧。

**缓解:**
- 使用 `requestAnimationFrame` 确保流畅
- Canvas 使用 `will-change: transform` 优化渲染
- 登录成功后立即停止动画
- 后期可添加性能检测（如检测到掉帧，减少粒子数）

**Risk 5: 设计文档与 initial-system-planning 的重复**

**描述:** 本 change 提取了部分设计决策，可能导致文档分散。

**缓解:**
- 在 proposal 中明确说明是"从 initial-system-planning 挑选"
- 关联原始设计文档的路径
- 后续可以将 initial-system-planning 归档后删除

**Risk 6: Analyst 和 Region 的外键约束**

**描述:** 如果删除 Region，关联的 Analyst 的 region_id 设为 NULL，可能影响数据完整性。

**缓解:**
- 使用 `ON DELETE SET NULL` 确保级联删除不报错
- 在删除 Region 前检查是否有关联的 Analyst
- 可选：禁止删除有 Analyst 关联的 Region

## Migration Plan

不适用（这是新功能，无现有数据迁移）

**部署步骤:**
1. 在 Supabase 中创建 region 表和 RLS policies（使用 SQL migrations）
2. 在 Supabase 中创建 analyst 表和 RLS policies（使用 SQL migrations）
3. 创建 RLS 辅助函数 `get_current_role()`（不需要 `get_current_analyst_id()`）
4. 配置后端环境变量（`SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`）
5. 运行 `backend/scripts/init_admin.py`：
   - 自动创建默认 Admin 用户
   - 自动配置 JWT 有效期为 24 小时
   - 如果自动配置失败，脚本会输出手动配置指导
6. 使用 Admin 账号登录验证
7. 部署前端到静态托管服务（如 Vercel, Netlify）

**回滚策略:**
- 如果 Supabase 配置错误，可以在 Dashboard 中手动删除 policies
- 如果初始化脚本失败，可以手动在 Supabase Auth 创建 Admin

## Open Questions

无（所有技术决策已明确）
