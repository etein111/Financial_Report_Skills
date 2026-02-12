/**
 * 权限检查 Composable
 *
 * 提供便捷的权限检查方法
 */
import { computed } from 'vue'
import { useAuth } from '@/stores/auth'

export function usePermission() {
  const { userState } = useAuth()

  const isAdmin = computed(() => userState.user?.role === 'admin')
  const isSA = computed(() => userState.user?.role === 'sa')
  const isAnalyst = computed(() => userState.user?.role === 'analyst')

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

  const canManageUsers = isAdmin
  const canManageRegions = isAdmin
  const canManageAnalystInfo = isAdmin

  return {
    isAdmin,
    isSA,
    isAnalyst,
    hasRole,
    hasAnyRole,
    hasAllRoles,
    canManageUsers,
    canManageRegions,
    canManageAnalystInfo
  }
}
