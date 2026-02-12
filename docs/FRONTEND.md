# Neolyst 前端配置文档

## 概述

Neolyst 前端基于 Vue 3 + TypeScript + Vite 构建，使用 Tailwind CSS 进行样式设计。

**开发服务器:** `http://localhost:5173`

**API 服务器:** `http://localhost:5173`

---

## 路由结构

| 路径 | 组件 | 说明 | 权限要求 |
|------|------|------|----------|
| `/` | - | 重定向到 `/login` | - |
| `/login` | `Login.vue` | 登录页面 | 公开 |
| `/desktop` | `Desktop.vue` | 桌面主页 | 需要认证 |
| `/regions` | `RegionsPage.vue` | Region 管理 | 需要认证 |
| `/analyst-info` | `AnalystInfoPage.vue` | Analyst 信息管理 | 需要认证 + Admin |
| `/coming-soon` | `ComingSoon.vue` | 占位页面 | 需要认证 |

### 路由守卫

路由守卫在 `src/router/index.ts` 中实现：

1. **未登录保护**: 访问需要认证的页面时，未登录用户自动跳转到登录页
2. **已登录保护**: 已登录用户访问登录页时，自动跳转到桌面
3. **Admin 权限**: 访问 Admin 专用页面时，非 Admin 用户被拒绝

---

## API 调用方式

### Axios 客户端

使用 `src/api/client.ts` 中配置的 Axios 实例：

```typescript
import apiClient from '@/api/client'

// GET 请求
const response = await apiClient.get('/api/regions')

// POST 请求
const response = await apiClient.post('/api/regions', {
  name: 'Hong Kong',
  code: 'HK'
})

// PUT 请求
const response = await apiClient.put(`/api/regions/${id}`, {
  name: 'Singapore',
  code: 'SG'
})

// DELETE 请求
const response = await apiClient.delete(`/api/regions/${id}`)
```

### 请求拦截器

请求拦截器会自动从 `localStorage` 读取 `auth_token` 并添加到请求头：

```typescript
Authorization: Bearer <token>
```

### 响应拦截器

响应拦截器处理 401 错误，自动：
1. 清除本地存储的认证信息
2. 跳转到登录页

---

## 状态管理

### 认证状态

使用 Vue 3 的 `provide/inject` 模式进行状态管理：

```typescript
// stores/auth.ts
export function provideAuthStore() {
  const userState = reactive({
    token: localStorage.getItem('auth_token') || null,
    user: JSON.parse(localStorage.getItem('user_info') || 'null'),
    isAuthenticated: !!localStorage.getItem('auth_token')
  })

  const login = (token: string, user: any) => {
    userState.token = token
    userState.user = user
    userState.isAuthenticated = true
    localStorage.setItem('auth_token', token)
    localStorage.setItem('user_info', JSON.stringify(user))
  }

  const logout = () => {
    userState.token = null
    userState.user = null
    userState.isAuthenticated = false
    localStorage.removeItem('auth_token')
    localStorage.removeItem('user_info')
  }

  provide(AUTH_STORE_KEY, { userState, login, logout })
}

export function useAuth() {
  return inject(AUTH_STORE_KEY)
}
```

### 使用示例

```vue
<script setup lang="ts">
import { useAuth } from '@/composables/useAuth'

const { userState, login, logout } = useAuth()
</script>

<template>
  <div v-if="userState.isAuthenticated">
    Welcome, {{ userState.user?.full_name }}
  </div>
</template>
```

---

## 环境配置

### 环境变量

在 `.env` 文件中定义：

```env
VITE_API_BASE_URL=http://localhost:5173
VITE_SUPABASE_URL=https://slxeorayantrboopghej.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-key
```

### 访问环境变量

```typescript
const apiUrl = import.meta.env.VITE_API_BASE_URL
```

---

## 组件结构

```
src/
├── api/              # API 调用
│   └── client.ts     # Axios 客户端
├── assets/           # 静态资源
│   └── styles/       # 全局样式
├── components/       # 组件
│   ├── common/       # 通用组件
│   └── desktop/      # 桌面组件
├── composables/      # Composables
├── router/           # 路由配置
├── stores/           # 状态管理
├── views/            # 页面组件
├── App.vue           # 根组件
└── main.ts           # 入口文件
```

---

## 桌面功能卡片

桌面主页显示功能卡片，按功能分组展示。点击卡片会在新浏览器标签页打开对应功能页面。

### 功能卡片分组

**Reports 组：**
- Reports（报告列表）
- New Report（创建新报告）
- Templates（模板管理）
- Sectors（行业分类）

**Data Management 组：**
- Regions（地区管理）
- Analyst Info（分析师信息）
- Users（用户管理，仅 Admin）

### 卡片行为

- **点击方式**: 在新标签页打开（使用 `window.open(url, '_blank')`）
- **桌面保持**: 桌面主页保持在原标签页
- **Coming Soon**: 未实现功能显示 "Coming Soon" 标签，点击后显示占位页面
- **权限控制**: Admin 专用卡片仅对 Admin 用户可见
- **悬停效果**: 鼠标悬停时边框变亮、轻微上移

### 组件文件

- `views/Desktop.vue` - 桌面主页
- `components/desktop/DesktopCard.vue` - 功能卡片组件

---

## 样式指南

### Tailwind CSS

使用 Tailwind 的工具类进行样式设计：

```vue
<div class="flex items-center gap-4 p-4 bg-white/5 rounded-lg">
  <span class="text-lg font-semibold text-white">Content</span>
</div>
```

### 自定义样式

全局样式在 `src/style.css` 中定义，包括：
- 玻璃拟态效果 (`.glass`)
- 文本渐变 (`.text-gradient`)
- 自定义滚动条

---

## 开发命令

```bash
# 安装依赖
npm install

# 启动开发服务器
npm run dev

# 构建生产版本
npm run build

# 预览生产构建
npm run preview
```

---

## 类型定义

使用 TypeScript 进行类型检查。类型定义应与后端 API 响应保持一致。

```typescript
interface User {
  id: string
  email: string
  full_name?: string
  role: 'admin' | 'sa' | 'analyst'
}

interface LoginResponse {
  success: boolean
  message: string
  data: {
    token: string
    user: User
  }
}
```

---

## 权限控制

### 检查用户权限

使用 `usePermission` composable：

```typescript
import { usePermission } from '@/composables/usePermission'

const { isAdmin, hasRole } = usePermission()

if (isAdmin) {
  // Admin only logic
}
```

### 页面级权限

在路由配置中使用 `meta` 字段：

```typescript
{
  path: '/analyst-info',
  meta: { requiresAuth: true, adminOnly: true }
}
```

---

## 错误处理

### API 错误

API 错误由 Axios 响应拦截器统一处理。组件中可以添加额外处理：

```typescript
try {
  const response = await apiClient.get('/api/data')
} catch (error) {
  if (axios.isAxiosError(error)) {
    // 处理特定错误
  }
}
```

### 表单验证

使用浏览器原生验证或自定义验证逻辑：

```vue
<input
  type="email"
  v-model="email"
  required
  minlength="6"
  class="input"
/>
```

---

## 构建和部署

### 生产构建

```bash
npm run build
```

构建输出在 `dist/` 目录。

### 部署

`dist/` 目录可以部署到任何静态文件服务器：
- Vercel
- Netlify
- Nginx
- Apache
