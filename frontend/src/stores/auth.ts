/**
 * 认证状态管理
 *
 * 使用全局单例模式实现全局认证状态
 */
import { reactive, watch } from 'vue'

// 用户信息接口
export interface User {
  id: string
  email: string
  full_name?: string
  role: 'admin' | 'sa' | 'analyst'
}

// 用户状态接口
interface UserState {
  token: string | null
  user: User | null
  isAuthenticated: boolean
}

// Auth Store 接口
interface AuthStore {
  userState: UserState
  login: (token: string, user: User) => void
  logout: () => void
  updateUser: (user: User) => void
}

// 从 localStorage 初始化状态
const token = localStorage.getItem('auth_token')
const userJson = localStorage.getItem('user_info')

let user: User | null = null
if (userJson) {
  try {
    user = JSON.parse(userJson)
  } catch {
    localStorage.removeItem('user_info')
  }
}

// 创建响应式状态
const userState = reactive<UserState>({
  token,
  user,
  isAuthenticated: !!token
})

// 监听状态变化并持久化到 localStorage
watch(
  () => userState.token,
  (newToken) => {
    if (newToken) {
      localStorage.setItem('auth_token', newToken)
    } else {
      localStorage.removeItem('auth_token')
    }
  }
)

watch(
  () => userState.user,
  (newUser) => {
    if (newUser) {
      localStorage.setItem('user_info', JSON.stringify(newUser))
    } else {
      localStorage.removeItem('user_info')
    }
  },
  { deep: true }
)

// 登录方法
function login(token: string, user: User) {
  userState.token = token
  userState.user = user
  userState.isAuthenticated = true
}

// 登出方法
function logout() {
  userState.token = null
  userState.user = null
  userState.isAuthenticated = false

  // 清除 localStorage
  localStorage.removeItem('auth_token')
  localStorage.removeItem('user_info')
}

// 更新用户信息方法
function updateUser(user: User) {
  userState.user = user
}

// 创建全局 store 单例
export const authStore: AuthStore = {
  userState,
  login,
  logout,
  updateUser
}

/**
 * 使用 Auth Store
 * 在组件中调用此函数获取认证状态和方法
 */
export function useAuth(): AuthStore {
  return authStore
}

/**
 * 权限检查 Composable
 */
export function usePermission() {
  const isAdmin = userState.user?.role === 'admin'
  const isSA = userState.user?.role === 'sa'
  const isAnalyst = userState.user?.role === 'analyst'

  const hasRole = (roles: string | string[]) => {
    if (!userState.user) return false
    if (typeof roles === 'string') {
      return userState.user.role === roles
    }
    return roles.includes(userState.user.role)
  }

  const hasAnyRole = (roles: string[]) => {
    return hasRole(roles)
  }

  const hasAllRoles = (roles: string[]) => {
    return roles.every(role => hasRole(role))
  }

  return {
    isAdmin,
    isSA,
    isAnalyst,
    hasRole,
    hasAnyRole,
    hasAllRoles
  }
}
