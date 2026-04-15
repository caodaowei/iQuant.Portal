import { createRouter, createWebHistory, RouteRecordRaw } from 'vue-router'
import { useUserStore } from '@/stores/user'

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { requiresAuth: false },
  },
  {
    path: '/',
    component: () => import('@/layouts/MainLayout.vue'),
    redirect: '/dashboard',
    meta: { requiresAuth: true },
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/Dashboard.vue'),
        meta: { title: '仪表盘', icon: 'DataAnalysis' },
      },
      {
        path: 'strategies',
        name: 'Strategies',
        component: () => import('@/views/Strategies.vue'),
        meta: { title: '策略管理', icon: 'Cpu' },
      },
      {
        path: 'backtest',
        name: 'Backtest',
        component: () => import('@/views/Backtest.vue'),
        meta: { title: '回测中心', icon: 'TrendCharts' },
      },
      {
        path: 'trading',
        name: 'Trading',
        component: () => import('@/views/Trading.vue'),
        meta: { title: '模拟交易', icon: 'ShoppingCart', requiresRole: 'trader' },
      },
      {
        path: 'positions',
        name: 'Positions',
        component: () => import('@/views/Positions.vue'),
        meta: { title: '持仓管理', icon: 'Wallet', requiresRole: 'trader' },
      },
      {
        path: 'diagnosis',
        name: 'Diagnosis',
        component: () => import('@/views/Diagnosis.vue'),
        meta: { title: 'AI 诊断', icon: 'Search' },
      },
      {
        path: 'data',
        name: 'Data',
        component: () => import('@/views/Data.vue'),
        meta: { title: '数据管理', icon: 'Database' },
      },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// 路由守卫
router.beforeEach(async (to, from, next) => {
  const userStore = useUserStore()

  // 如果需要认证但未登录
  if (to.meta.requiresAuth && !userStore.isLoggedIn) {
    next('/login')
  } 
  // 如果访问登录页但已登录
  else if (to.path === '/login' && userStore.isLoggedIn) {
    next('/')
  } 
  else {
    // 检查角色权限（如果后端提供了角色信息）
    const requiresRole = to.meta.requiresRole as string | undefined
    if (requiresRole && userStore.user) {
      const roleHierarchy: Record<string, number> = {
        viewer: 0,
        analyst: 1,
        trader: 2,
        admin: 3,
        user: 0, // Supabase 默认用户角色
      }

      const userRole = userStore.user.role || 'user'
      const userLevel = roleHierarchy[userRole] || 0
      const requiredLevel = roleHierarchy[requiresRole] || 0

      if (userLevel < requiredLevel) {
        next('/dashboard')
        return
      }
    }
    next()
  }
})

export default router
