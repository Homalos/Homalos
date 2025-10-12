<template>
  <el-container class="home-container">
    <!-- 顶部导航栏 -->
    <el-header class="header">
      <div class="header-left">
        <h2>Homalos 量化交易系统</h2>
      </div>
      <div class="header-right">
        <!-- 通知图标 -->
        <el-badge :value="unreadCount" :hidden="unreadCount === 0" class="header-icon">
          <el-icon :size="20" @click="handleNotificationClick">
            <Bell />
          </el-icon>
        </el-badge>
        
        <!-- 控制台图标 -->
        <el-icon :size="20" class="header-icon" @click="handleConsoleClick">
          <Operation />
        </el-icon>
        
        <!-- 设置图标 -->
        <el-icon :size="20" class="header-icon" @click="handleSettingsClick">
          <Setting />
        </el-icon>
        
        <!-- 用户信息 -->
        <el-dropdown @command="handleCommand">
          <span class="user-info">
            <el-icon><User /></el-icon>
            <span>{{ userStore.userInfo?.username || '用户' }}</span>
            <el-icon class="el-icon--right"><ArrowDown /></el-icon>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="logout">退出登录</el-dropdown-item>
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
        <Dashboard v-if="activeMenu === 'dashboard'" />

        <!-- 控制台 -->
        <Console v-if="activeMenu === 'console'" />

        <!-- 策略管理 -->
        <StrategyManagement v-if="activeMenu === 'strategy'" />

        <!-- 通知中心 -->
        <Notifications v-if="activeMenu === 'notifications'" />

        <!-- 任务调度器 -->
        <TaskScheduler v-if="activeMenu === 'task-scheduler'" />

        <!-- 系统设置 -->
        <Settings v-if="activeMenu === 'settings'" />

        <!-- 关于 -->
        <About v-if="activeMenu === 'about'" />

      </el-main>
    </el-container>
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
  Operation
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'
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

const router = useRouter()
const userStore = useUserStore()

const activeMenu = ref('dashboard')

// ===== 使用 Composables =====
const {
  notifications,
  unreadCount,
  markAsRead,
  markAllAsRead
} = useNotifications()

const handleMenuSelect = (index) => {
  activeMenu.value = index
}

const handleCommand = (command) => {
  if (command === 'logout') {
    userStore.logout()
    ElMessage.success('已退出登录')
    router.push('/login')
  }
}

/**
 * 处理通知图标点击，跳转到通知中心
 */
const handleNotificationClick = () => {
  activeMenu.value = 'notifications'
}

/**
 * 处理设置图标点击，跳转到系统设置页面
 */
const handleSettingsClick = () => {
  activeMenu.value = 'settings'
}

/**
 * 控制台图标点击
 */
const handleConsoleClick = () => {
  activeMenu.value = 'console'
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
</style>

