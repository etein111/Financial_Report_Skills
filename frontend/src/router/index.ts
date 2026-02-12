import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'

// 路由配置
const routes: RouteRecordRaw[] = [
  {
    path: '/',
    redirect: '/login'
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/desktop',
    name: 'Desktop',
    component: () => import('../views/Desktop.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/regions',
    name: 'Regions',
    component: () => import('../views/RegionsPage.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/analyst-info',
    name: 'AnalystInfo',
    component: () => import('../views/AnalystInfoPage.vue'),
    meta: { requiresAuth: true, adminOnly: true }
  },
  {
    path: '/users',
    name: 'Users',
    component: () => import('../views/UsersPage.vue'),
    meta: { requiresAuth: true, adminOnly: true }
  },
  {
    path: '/coming-soon',
    name: 'ComingSoon',
    component: () => import('../views/ComingSoon.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/desktop'
  }
]

// 创建路由实例
const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes
})

// 路由守卫
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('auth_token')

  // 检查是否需要认证
  if (to.meta.requiresAuth && !token) {
    next('/login')
    return
  }

  // 已登录用户访问登录页，跳转到桌面
  if (to.path === '/login' && token) {
    next('/desktop')
    return
  }

  // 检查 Admin 权限
  if (to.meta.adminOnly) {
    try {
      const userInfo = JSON.parse(localStorage.getItem('user_info') || '{}')
      if (userInfo.role !== 'admin') {
        next('/desktop')
        return
      }
    } catch {
      next('/login')
      return
    }
  }

  next()
})

export default router
