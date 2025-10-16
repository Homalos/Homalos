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
          type="success"
          size="small"
          @click="showTradingLogin = true"
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
          :default-active="activeMenu"
          class="sidebar-menu"
          @select="handleMenuSelect"
        >
          <el-menu-item index="dashboard">
            <el-icon><Monitor /></el-icon>
            <span>仪表盘</span>
          </el-menu-item>
          <el-menu-item index="console">
            <el-icon><Operation /></el-icon>
            <span>控制台</span>
          </el-menu-item>
          <el-menu-item index="strategy">
            <el-icon><DataAnalysis /></el-icon>
            <span>策略管理</span>
          </el-menu-item>
          <el-menu-item index="task-scheduler">
            <el-icon><Timer /></el-icon>
            <span>任务调度器</span>
          </el-menu-item>
          <el-menu-item index="alarms">
            <el-icon><Bell /></el-icon>
            <span>告警管理</span>
          </el-menu-item>
          <el-menu-item index="notifications">
            <el-icon><Bell /></el-icon>
            <span>通知中心</span>
          </el-menu-item>
          <el-menu-item index="settings">
            <el-icon><Setting /></el-icon>
            <span>系统设置</span>
          </el-menu-item>
          <el-menu-item index="about">
            <el-icon><InfoFilled /></el-icon>
            <span>关于</span>
          </el-menu-item>
        </el-menu>
      </el-aside>

      <!-- 主内容区 -->
      <el-main class="main-content">
        <!-- 仪表盘 -->
        <div v-if="activeMenu === 'dashboard'" style="position: relative;">
          <Dashboard />
          <PageMask 
            :show="!tradingAccountStore.isLoggedIn" 
            @login="showTradingLogin = true"
          />
        </div>

        <!-- 控制台 -->
        <div v-if="activeMenu === 'console'" style="position: relative;">
          <Console />
          <PageMask 
            :show="!tradingAccountStore.isLoggedIn" 
            @login="showTradingLogin = true"
          />
                  </div>

        <!-- 策略管理 -->
        <div v-if="activeMenu === 'strategy'" style="position: relative;">
          <StrategyManagement />
          <PageMask 
            :show="!tradingAccountStore.isLoggedIn" 
            @login="showTradingLogin = true"
          />
                  </div>

        <!-- 通知中心 -->
        <div v-if="activeMenu === 'notifications'" style="position: relative;">
          <Notifications />
          <PageMask 
            :show="!tradingAccountStore.isLoggedIn" 
            @login="showTradingLogin = true"
          />
            </div>

        <!-- 任务调度器 -->
        <div v-if="activeMenu === 'task-scheduler'" style="position: relative;">
          <TaskScheduler />
          <PageMask 
            :show="!tradingAccountStore.isLoggedIn" 
            @login="showTradingLogin = true"
          />
            </div>

        <!-- 告警管理 -->
        <AlarmManagement v-if="activeMenu === 'alarms'" />

        <!-- 系统设置（完全可访问） -->
        <Settings v-if="activeMenu === 'settings'" />

        <!-- 关于（完全可访问） -->
        <About v-if="activeMenu === 'about'" />

      </el-main>
    </el-container>
    
    <!-- 资金账户登录对话框 -->
    <TradingAccountLogin 
      v-model="showTradingLogin" 
      @success="handleTradingLoginSuccess"
    />
    
    <!-- 账户管理对话框 -->
    <AccountManager 
      v-model="showAccountManager" 
      @add="showTradingLogin = true"
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
import { useRouter } from 'vue-router'
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
  Close
} from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useUserStore } from '@/stores/user'
import { useTradingAccountStore } from '@/stores/tradingAccount'
import { getSystemStats } from '@/api/monitor'
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
// 组件导入
import Console from '@/components/Console.vue'
import TaskScheduler from '@/components/TaskScheduler.vue'
import Notifications from '@/components/Notifications.vue'
import Settings from '@/components/Settings.vue'
import About from '@/components/About.vue'
import Dashboard from '@/components/Dashboard.vue'
import StrategyManagement from '@/components/StrategyManagement.vue'
import TradingAccountLogin from '@/components/TradingAccountLogin.vue'
import AccountManager from '@/components/AccountManager.vue'
import FirstTimeGuide from '@/components/FirstTimeGuide.vue'
import PageMask from '@/components/PageMask.vue'
import NotificationCenter from '@/components/NotificationCenter.vue'
import AlarmManagement from '@/views/AlarmManagement.vue'

const router = useRouter()
const userStore = useUserStore()
const tradingAccountStore = useTradingAccountStore()

// 默认显示"关于"页面，登录资金账户后切换到仪表盘
const activeMenu = ref('about')

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

const handleMenuSelect = (index) => {
  activeMenu.value = index
  
  // 如果切换到告警管理，重置到主页面
  if (index === 'alarms') {
    setTimeout(() => {
      const alarmManagementComponent = document.querySelector('.alarm-management')
      if (alarmManagementComponent) {
        const event = new CustomEvent('resetToMainPage')
        alarmManagementComponent.dispatchEvent(event)
      }
    }, 100)
  }
}

/**
 * 处理控制台图标点击
 */
const handleConsoleClick = () => {
  activeMenu.value = 'console'
}

/**
 * 处理设置图标点击
 */
const handleSettingsClick = () => {
  activeMenu.value = 'settings'
}

/**
 * 处理切换到告警管理
 */
const handleSwitchToAlarms = () => {
  activeMenu.value = 'alarms'
  // 等待组件渲染后重置到主页面
  setTimeout(() => {
    const alarmManagementComponent = document.querySelector('.alarm-management')
    if (alarmManagementComponent) {
      const event = new CustomEvent('resetToMainPage')
      alarmManagementComponent.dispatchEvent(event)
    }
  }, 100)
}

/**
 * 处理切换到告警设置
 */
const handleSwitchToAlarmSettings = () => {
  activeMenu.value = 'alarms'
  // 需要等待组件渲染后再切换到设置子页面
  setTimeout(() => {
    // 通过事件或状态通知AlarmManagement组件显示设置页面
    const alarmManagementComponent = document.querySelector('.alarm-management')
    if (alarmManagementComponent) {
      // 触发显示设置页面的逻辑
      const event = new CustomEvent('showAlarmSettings')
      alarmManagementComponent.dispatchEvent(event)
    }
  }, 100)
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
    await ElMessageBox.confirm(
      '确定要退出资金账户吗？',
      '确认退出',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    await tradingAccountStore.logout()
    ElMessage.success('已退出资金账户')
    activeMenu.value = 'about'
  } catch (error) {
    // 取消操作
  }
}

/**
 * 退出系统登录（同时退出资金账户）
 */
async function handleLogout() {
  try {
    await ElMessageBox.confirm(
      '确定要退出系统登录吗？',
      '确认退出',
      {
        confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
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
  activeMenu.value = 'notifications'
}

/**
 * 资金账户登录成功
 */
function handleTradingLoginSuccess(account) {
  ElMessage.success('资金账户登录成功')
  activeMenu.value = 'dashboard'
}

/**
 * 首次引导完成
 */
function handleGuideFinish(completed) {
  if (completed) {
    ElMessage.success('欢迎使用 Homalos 量化交易系统！')
    activeMenu.value = 'dashboard'
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
  
  // 如果已登录资金账户，切换到仪表盘
  if (tradingAccountStore.isLoggedIn) {
    activeMenu.value = 'dashboard'
  }
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
  background-color: #409eff;
  color: white;
  padding: 0 20px;
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
</style>

