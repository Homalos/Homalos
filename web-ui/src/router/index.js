import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { useTradingAccountStore } from '@/stores/tradingAccount'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/',
    name: 'Home',
    component: () => import('@/views/Home.vue'),
    meta: { requiresAuth: true },
    redirect: '/about',
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/components/Dashboard.vue'),
        meta: { requiresAuth: true, requiresTradingAuth: true }
      },
      {
        path: 'console',
        name: 'Console',
        component: () => import('@/components/Console.vue'),
        meta: { requiresAuth: true, requiresTradingAuth: true }
      },
      {
        path: 'strategy',
        name: 'Strategy',
        component: () => import('@/components/StrategyManagement.vue'),
        meta: { requiresAuth: true, requiresTradingAuth: true }
      },
      {
        path: 'task-scheduler',
        name: 'TaskScheduler',
        component: () => import('@/components/TaskScheduler.vue'),
        meta: { requiresAuth: true, requiresTradingAuth: true }
      },
      {
        path: 'alarms',
        name: 'Alarms',
        component: () => import('@/views/AlarmManagement.vue'),
        meta: { requiresAuth: true },
        children: [
          {
            path: 'settings',
            name: 'AlarmSettings',
            component: () => import('@/views/AlarmSettings.vue'),
            meta: { requiresAuth: true }
          }
        ]
      },
      {
        path: 'notifications',
        name: 'Notifications',
        component: () => import('@/components/Notifications.vue'),
        meta: { requiresAuth: true, requiresTradingAuth: true }
      },
      {
        path: 'settings',
        name: 'Settings',
        component: () => import('@/components/Settings.vue'),
        meta: { requiresAuth: true }
      },
      {
        path: 'about',
        name: 'About',
        component: () => import('@/components/About.vue'),
        meta: { requiresAuth: true }
      }
    ]
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/about'
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫
router.beforeEach(async (to, from, next) => {
  const userStore = useUserStore()
  const tradingAccountStore = useTradingAccountStore()
  const requiresAuth = to.meta.requiresAuth

  if (requiresAuth && !userStore.isLoggedIn) {
    // 需要登录但未登录，跳转到登录页
    next('/login')
  } else if (to.path === '/login' && userStore.isLoggedIn) {
    // 已登录但访问登录页，跳转到首页（保持当前路由或默认到 about）
    next('/')
  } else {
    // 已通过系统登录，初始化资金账户Store
    if (userStore.isLoggedIn && to.path !== '/login') {
      await tradingAccountStore.initialize()
    }
    // 不再强制跳转，交给 PageMask 组件处理资金账户登录提示
    next()
  }
})

export default router

