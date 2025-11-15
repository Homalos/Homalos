<template>
  <el-container class="home-container">
    <!-- 顶部导航栏 -->
    <el-header class="header">
      <div class="header-left">
        <h2>Homalos 量化交易系统</h2>
      </div>
      <div class="header-right">
        <!-- 资金账户登录按钮（未登录时显示） -->
        <el-button
          v-if="!tradingAccountStore.isLoggedIn"
          class="login-account-transparent-btn"
          type="primary"
          size="small"
          @click="showTradingLogin = true"
          plain
        >
          <el-icon><Unlock /></el-icon>
          登录资金账户
        </el-button>
        
        <!-- 告警通知中心 -->
        <NotificationCenter 
          @switchToAlarms="handleSwitchToAlarms"
          @switchToAlarmSettings="handleSwitchToAlarmSettings"
        />
        
        <!-- 控制台图标 -->
        <el-icon :size="20" class="header-icon" @click="handleConsoleClick">
          <Operation />
        </el-icon>
        
        <!-- 设置图标 -->
        <el-icon :size="20" class="header-icon" @click="handleSettingsClick">
          <Setting />
        </el-icon>
        
        <!-- 用户信息 -->
        <el-dropdown @command="handleUserCommand">
          <span class="user-info">
            <el-icon><User /></el-icon>
            <span>{{ userStore.userInfo?.username || '用户' }}</span>
            <el-icon class="el-icon--right"><ArrowDown /></el-icon>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <!-- 资金账户状态 -->
              <el-dropdown-item disabled divided>
                <div class="account-status">
                  <el-icon v-if="tradingAccountStore.isLoggedIn" color="#67C23A">
                    <CircleCheckFilled />
                  </el-icon>
                  <el-icon v-else color="#909399">
                    <Lock />
                  </el-icon>
                  <span>
                    {{ tradingAccountStore.isLoggedIn ? 
                      tradingAccountStore.accountInfo?.display_name || '资金账户已登录' : 
                      '未登录资金账户' 
                    }}
                  </span>
                </div>
              </el-dropdown-item>
              
              <!-- 管理资金账户 -->
              <el-dropdown-item command="manage-accounts">
                <el-icon><SwitchButton /></el-icon>
                管理资金账户
              </el-dropdown-item>
              
              <!-- 退出资金账户（仅在已登录时显示） -->
              <el-dropdown-item 
                v-if="tradingAccountStore.isLoggedIn" 
                command="logout-trading"
                divided
              >
                <el-icon><Close /></el-icon>
                退出资金账户
              </el-dropdown-item>
              
              <!-- 退出系统登录 -->
              <el-dropdown-item command="logout" divided>
                <el-icon><SwitchButton /></el-icon>
                退出系统登录
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </el-header>

    <el-container>
      <!-- 侧边栏 -->
      <el-aside width="200px" class="sidebar">
        <el-menu
          :default-active="currentMenuIndex"
          class="sidebar-menu"
          @select="handleMenuSelect"
        >
          <el-menu-item index="/dashboard">
            <el-icon><Monitor /></el-icon>
            <span>仪表盘</span>
          </el-menu-item>
          <el-menu-item index="/console">
            <el-icon><Operation /></el-icon>
            <span>控制台</span>
          </el-menu-item>
          <el-menu-item index="/strategy">
            <el-icon><DataAnalysis /></el-icon>
            <span>策略管理</span>
          </el-menu-item>
          <el-menu-item index="/task-scheduler">
            <el-icon><Timer /></el-icon>
            <span>任务调度器</span>
          </el-menu-item>
          <el-menu-item index="/alarms">
            <el-icon><Bell /></el-icon>
            <span>告警管理</span>
          </el-menu-item>
          <el-menu-item index="/notifications">
            <el-icon><Bell /></el-icon>
            <span>通知中心</span>
          </el-menu-item>
          <el-menu-item index="/brokerages">
            <el-icon><Wallet /></el-icon>
            <span>券商账户</span>
          </el-menu-item>
          <el-menu-item index="/settings">
            <el-icon><Setting /></el-icon>
            <span>系统设置</span>
          </el-menu-item>
          <el-menu-item index="/about">
            <el-icon><InfoFilled /></el-icon>
            <span>关于</span>
          </el-menu-item>
        </el-menu>
      </el-aside>

      <!-- 主内容区 -->
      <el-main class="main-content">
        <!-- 使用路由视图渲染子页面 -->
        <router-view v-slot="{ Component, route }">
          <div style="position: relative;">
            <component :is="Component" />
            <!-- 需要资金账户登录的页面显示遮罩 -->
            <PageMask 
              v-if="route.meta.requiresTradingAuth && !tradingAccountStore.isLoggedIn"
              :show="true" 
              @login="showTradingLogin = true"
            />
          </div>
        </router-view>
      </el-main>
    </el-container>
    
    <!-- 资金账户登录对话框 -->
    <TradingAccountLogin 
      v-model="showTradingLogin" 
      @success="handleTradingLoginSuccess"
      @goToManage="handleGoToManageAccounts"
    />
    
    <!-- 账户管理对话框 -->
    <AccountManager 
      v-model="showAccountManager"
      @requestLogin="handleRequestLogin"
    />
    
    <!-- 首次引导对话框 -->
    <FirstTimeGuide 
      v-model="showFirstTimeGuide" 
      @finish="handleGuideFinish"
    />
  </el-container>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import {
  User,
  ArrowDown,
  Monitor,
  DataAnalysis,
  Setting,
  InfoFilled,
  Bell,
  Timer,
  Operation,
  Unlock,
  Lock,
  CircleCheckFilled,
  SwitchButton,
  Close,
  Wallet
} from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useUserStore } from '@/stores/user'
import { useTradingAccountStore } from '@/stores/tradingAccount'
import { getSystemStats } from '@/api/monitor'
import { getTradingCoreStatus } from '@/api/tradingCore'
// Mock 数据导入
// （控制台、任务调度器、通知中心、仪表盘的数据已在各自组件中导入）
// 常量导入
// （大部分常量已在各自组件中导入）
// 工具函数导入
// （大部分工具函数已在各自组件中导入）
// Composables 导入
import {
  useNotifications
} from '@/composables'
// 组件导入（页面组件由路由懒加载，这里只导入对话框和公共组件）
import TradingAccountLogin from '@/components/TradingAccountLogin.vue'
import AccountManager from '@/components/AccountManager.vue'
import FirstTimeGuide from '@/components/FirstTimeGuide.vue'
import PageMask from '@/components/PageMask.vue'
import NotificationCenter from '@/components/NotificationCenter.vue'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()
const tradingAccountStore = useTradingAccountStore()

// 根据当前路由计算侧边栏高亮项
const currentMenuIndex = computed(() => {
  const path = route.path
  // 特殊处理告警管理子路由，统一高亮告警管理菜单
  if (path.startsWith('/alarms')) return '/alarms'
  return path
})

// 对话框状态
const showTradingLogin = ref(false)
const showAccountManager = ref(false)
const showFirstTimeGuide = ref(false)

// ===== 使用 Composables =====
const {
  notifications,
  unreadCount,
  markAsRead,
  markAllAsRead
} = useNotifications()

const handleMenuSelect = (path) => {
  router.push(path)
}

/**
 * 处理控制台图标点击
 */
const handleConsoleClick = () => {
  router.push('/console')
}

/**
 * 处理设置图标点击
 */
const handleSettingsClick = () => {
  router.push('/settings')
}

/**
 * 处理切换到告警管理
 */
const handleSwitchToAlarms = () => {
  router.push('/alarms')
}

/**
 * 处理切换到告警设置
 */
const handleSwitchToAlarmSettings = () => {
  router.push('/alarms/settings')
}

/**
 * 处理前往管理账户
 */
function handleGoToManageAccounts() {
  showAccountManager.value = true
}

/**
 * 处理请求登录（从账户管理器触发）
 */
function handleRequestLogin() {
  showTradingLogin.value = true
}

/**
 * 处理用户下拉菜单命令
 */
const handleUserCommand = async (command) => {
  switch (command) {
    case 'manage-accounts':
      showAccountManager.value = true
      break
    case 'logout-trading':
      await handleLogoutTrading()
      break
    case 'logout':
      await handleLogout()
      break
  }
}

/**
 * 退出资金账户
 */
async function handleLogoutTrading() {
  try {
    // 检查交易核心状态
    let coreStatus = null
    try {
      coreStatus = await getTradingCoreStatus()
    } catch (error) {
      console.warn('获取交易核心状态失败:', error)
    }
    
    // 根据交易核心状态显示不同的提示
    let message = '确定要退出资金账户吗？'
    let type = 'info'
    let confirmButtonText = '确定'
    
    if (coreStatus && coreStatus.status === 'RUNNING') {
      message = '注意：交易核心正在运行！\n\n' +
                '退出资金账户后：\n' +
                '• 交易核心将继续运行\n' +
                '• 运行中的策略将继续执行\n' +
                '• 交易信号将继续发送\n\n' +
                '建议：如需停止交易，请先在控制台面板停止交易核心。'
      type = 'warning'
      confirmButtonText = '仍要退出'
    } else if (coreStatus && coreStatus.status !== 'STOPPED') {
      // 交易核心在其他状态（INITIALIZING, CONNECTING等）
      message = '退出资金账户后，交易核心将继续运行。\n' +
                '如需停止交易，请在控制台面板手动停止交易核心。'
      type = 'warning'
    }
    
    await ElMessageBox.confirm(
      message,
      '确认退出资金账户',
      {
        confirmButtonText: confirmButtonText,
        cancelButtonText: '取消',
        type: type,
        distinguishCancelAndClose: true
      }
    )
    
    await tradingAccountStore.logout()
    ElMessage.success('已退出资金账户')
    router.push('/about')
  } catch (error) {
    // 取消操作
  }
}

/**
 * 退出系统登录（同时退出资金账户）
 */
async function handleLogout() {
  try {
    // 检查交易核心状态
    let coreStatus = null
    try {
      coreStatus = await getTradingCoreStatus()
    } catch (error) {
      console.warn('获取交易核心状态失败:', error)
    }
    
    // 根据交易核心状态显示不同的提示
    let message = '确定要退出系统登录吗？'
    let type = 'info'
    let confirmButtonText = '确定'
    
    if (coreStatus && coreStatus.status === 'RUNNING') {
      message = '警告：交易核心正在运行！\n\n' +
                '退出系统登录后：\n' +
                '• 交易核心将继续运行\n' +
                '• 运行中的策略将继续执行\n' +
                '• 交易信号将继续发送\n' +
                '• 您将无法通过Web界面管理系统\n\n' +
                '强烈建议：退出前先在控制台面板停止交易核心。'
      type = 'error'  // 使用error类型更醒目
      confirmButtonText = '仍要退出'
    } else if (coreStatus && coreStatus.status !== 'STOPPED') {
      // 交易核心在其他状态（INITIALIZING, CONNECTING等）
      message = '退出系统登录后，交易核心将继续运行。\n' +
                '如需停止交易，请在控制台面板手动停止交易核心。'
      type = 'warning'
    }
    
    await ElMessageBox.confirm(
      message,
      '确认退出系统登录',
      {
        confirmButtonText: confirmButtonText,
        cancelButtonText: '取消',
        type: type,
        distinguishCancelAndClose: true
      }
    )
    
    // 先退出资金账户
    if (tradingAccountStore.isLoggedIn) {
      await tradingAccountStore.logout()
    }
    
    // 再退出系统
    userStore.logout()
    ElMessage.success('已退出登录')
    router.push('/login')
  } catch (error) {
    // 取消操作
  }
}

/**
 * 处理通知图标点击，跳转到通知中心
 */
const handleNotificationClick = () => {
  router.push('/notifications')
}

/**
 * 资金账户登录成功
 */
function handleTradingLoginSuccess(account) {
  ElMessage.success('资金账户登录成功')
  // 只在 about 页面或根路径时才跳转到 dashboard，否则保持当前页面
  if (route.path === '/about' || route.path === '/') {
    router.push('/dashboard')
  }
}

/**
 * 首次引导完成
 */
function handleGuideFinish(completed) {
  if (completed) {
    ElMessage.success('欢迎使用 Homalos 量化交易系统！')
    router.push('/dashboard')
  }
}

/**
 * 检查是否首次使用
 */
function checkFirstTime() {
  const guideCompleted = localStorage.getItem('homalos_guide_completed')
  const hasAccounts = tradingAccountStore.accountList.length > 0
  
  // 如果没有完成引导且没有账户，显示引导
  if (!guideCompleted && !hasAccounts) {
    console.log('🎯 首次使用检测：显示引导界面', {
      guideCompleted,
      hasAccounts,
      accountListLength: tradingAccountStore.accountList.length
    })
    showFirstTimeGuide.value = true
  } else {
    console.log('🎯 首次使用检测：不显示引导', {
      guideCompleted,
      hasAccounts,
      accountListLength: tradingAccountStore.accountList.length
    })
  }
}

// ===== 所有业务逻辑已提取到 Composables =====
// 策略管理逻辑 -> useStrategyManagement.js
// 任务调度逻辑 -> useTaskScheduler.js
// 通知管理逻辑 -> useNotifications.js
// 控制台逻辑 -> useConsole.js
// 系统监控逻辑 -> useSystemMonitor.js


onMounted(async () => {
  // 获取用户信息
  if (!userStore.userInfo) {
    const success = await userStore.fetchUserInfo()
    if (!success) {
      ElMessage.error('获取用户信息失败，请重新登录')
      router.push('/login')
      return
    }
  }
  
  // 初始化资金账户Store
  await tradingAccountStore.initialize()
  
  // 检查是否首次使用
  checkFirstTime()
  
  // 不再强制跳转到仪表盘，保持用户当前页面
})
</script>

<style scoped>
.home-container {
  height: 100vh;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: linear-gradient(135deg, #223d80df 0%, #2a53a0df 55%, #3062badf 100%);
  color: white;
  padding: 0 20px;
  backdrop-filter: blur(18px);
  -webkit-backdrop-filter: blur(18px);
}

.header-left h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 500;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 20px;
}

.header-icon {
  cursor: pointer;
  transition: opacity 0.3s;
  color: white;
}

.header-icon:hover {
  opacity: 0.8;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  color: white;
}

.sidebar {
  background-color: #f5f7fa;
}

.sidebar-menu {
  border-right: none;
  height: 100%;
}

.main-content {
  background-color: #f0f2f5;
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

:deep(.el-statistic) {
  text-align: center;
}

.account-status {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 0;
}

.login-account-transparent-btn {
  background: transparent !important;
  border: none !important;
  color: #fff !important;
  box-shadow: none !important;
  transition: background 0.2s, border 0.2s, box-shadow 0.2s;
}
.login-account-transparent-btn:hover {
  border: 1.3px solid #409EFF !important;
  background: rgba(64,158,255,0.09) !important;
  color: #409EFF !important;
  box-shadow: 0 0 8px #409eff33;
}
</style>

