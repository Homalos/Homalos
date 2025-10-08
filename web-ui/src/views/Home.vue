<template>
  <el-container class="home-container">
    <!-- 顶部导航栏 -->
    <el-header class="header">
      <div class="header-left">
        <h2>Homalos 量化交易系统</h2>
      </div>
      <div class="header-right">
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
            <span>系统监控</span>
          </el-menu-item>
          <el-menu-item index="strategy">
            <el-icon><DataAnalysis /></el-icon>
            <span>策略管理</span>
          </el-menu-item>
          <el-menu-item index="settings">
            <el-icon><Setting /></el-icon>
            <span>系统设置</span>
          </el-menu-item>
        </el-menu>
      </el-aside>

      <!-- 主内容区 -->
      <el-main class="main-content">
        <el-card v-if="activeMenu === 'dashboard'" shadow="hover">
          <template #header>
            <div class="card-header">
              <span>系统监控</span>
            </div>
          </template>
          <el-row :gutter="20">
            <el-col :span="6">
              <el-statistic title="系统状态" value="运行中">
                <template #prefix>
                  <el-icon color="#67C23A"><SuccessFilled /></el-icon>
                </template>
              </el-statistic>
            </el-col>
            <el-col :span="6">
              <el-statistic title="CPU使用率" :value="systemInfo.cpu" suffix="%">
                <template #prefix>
                  <el-icon><Cpu /></el-icon>
                </template>
              </el-statistic>
            </el-col>
            <el-col :span="6">
              <el-statistic title="内存使用率" :value="systemInfo.memory" suffix="%">
                <template #prefix>
                  <el-icon><Memo /></el-icon>
                </template>
              </el-statistic>
            </el-col>
            <el-col :span="6">
              <el-statistic title="活跃策略" :value="systemInfo.activeStrategies">
                <template #prefix>
                  <el-icon><DataAnalysis /></el-icon>
                </template>
              </el-statistic>
            </el-col>
          </el-row>
        </el-card>

        <el-card v-if="activeMenu === 'strategy'" shadow="hover">
          <template #header>
            <div class="card-header">
              <span>策略管理</span>
              <el-button type="primary" size="small">添加策略</el-button>
            </div>
          </template>
          <el-table :data="strategies" style="width: 100%">
            <el-table-column prop="name" label="策略名称" />
            <el-table-column prop="status" label="状态">
              <template #default="scope">
                <el-tag :type="scope.row.status === '运行中' ? 'success' : 'info'">
                  {{ scope.row.status }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="profit" label="收益率" />
            <el-table-column label="操作">
              <template #default="scope">
                <el-button
                  size="small"
                  :type="scope.row.status === '运行中' ? 'warning' : 'success'"
                >
                  {{ scope.row.status === '运行中' ? '停止' : '启动' }}
                </el-button>
                <el-button size="small" type="primary">配置</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>

        <el-card v-if="activeMenu === 'settings'" shadow="hover">
          <template #header>
            <div class="card-header">
              <span>系统设置</span>
            </div>
          </template>
          <el-form label-width="120px">
            <el-form-item label="系统名称">
              <el-input v-model="settings.systemName" />
            </el-form-item>
            <el-form-item label="自动启动">
              <el-switch v-model="settings.autoStart" />
            </el-form-item>
            <el-form-item label="日志级别">
              <el-select v-model="settings.logLevel">
                <el-option label="DEBUG" value="debug" />
                <el-option label="INFO" value="info" />
                <el-option label="WARNING" value="warning" />
                <el-option label="ERROR" value="error" />
              </el-select>
            </el-form-item>
            <el-form-item>
              <el-button type="primary">保存设置</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  User,
  ArrowDown,
  Monitor,
  DataAnalysis,
  Setting,
  SuccessFilled,
  Cpu,
  Memo
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()

const activeMenu = ref('dashboard')

const systemInfo = reactive({
  cpu: 25,
  memory: 45,
  activeStrategies: 3
})

const strategies = ref([
  { name: '趋势跟踪策略', status: '运行中', profit: '+12.5%' },
  { name: '均值回归策略', status: '已停止', profit: '+8.3%' },
  { name: '套利策略', status: '运行中', profit: '+15.7%' }
])

const settings = reactive({
  systemName: 'Homalos',
  autoStart: true,
  logLevel: 'info'
})

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

onMounted(async () => {
  // 获取用户信息
  await userStore.fetchUserInfo()
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

