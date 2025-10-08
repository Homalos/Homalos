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
            <el-col :span="8">
              <el-statistic title="系统状态" value="运行中">
                <template #prefix>
                  <el-icon color="#67C23A"><SuccessFilled /></el-icon>
                </template>
              </el-statistic>
            </el-col>
            <el-col :span="8">
              <el-statistic title="CPU使用率" :value="systemInfo.cpu" suffix="%">
                <template #prefix>
                  <el-icon><Cpu /></el-icon>
                </template>
              </el-statistic>
            </el-col>
            <el-col :span="8">
              <el-statistic title="内存使用率" :value="systemInfo.memory" suffix="%">
                <template #prefix>
                  <el-icon><Memo /></el-icon>
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
          <!-- 策略统计 -->
          <el-row :gutter="20" style="margin-bottom: 20px;">
            <el-col :span="8">
              <el-statistic title="活跃策略" :value="systemInfo.activeStrategies">
                <template #prefix>
                  <el-icon color="#409eff"><DataAnalysis /></el-icon>
                </template>
              </el-statistic>
            </el-col>
            <el-col :span="8">
              <el-statistic title="运行中" :value="runningStrategiesCount">
                <template #prefix>
                  <el-icon color="#67C23A"><SuccessFilled /></el-icon>
                </template>
              </el-statistic>
            </el-col>
            <el-col :span="8">
              <el-statistic title="已停止" :value="stoppedStrategiesCount">
                <template #prefix>
                  <el-icon color="#909399"><Setting /></el-icon>
                </template>
              </el-statistic>
            </el-col>
          </el-row>
          <el-table :data="strategies" style="width: 100%">
            <el-table-column prop="id" label="策略ID" width="100" />
            <el-table-column prop="name" label="策略名称" />
            <el-table-column prop="status" label="状态" width="100">
              <template #default="scope">
                <el-tag :type="scope.row.status === '运行中' ? 'success' : 'info'">
                  {{ scope.row.status }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="startTime" label="启动时间" width="180" />
            <el-table-column prop="runningTime" label="运行时长" width="120" />
            <el-table-column label="操作" width="220">
              <template #default="scope">
                <el-button
                  size="small"
                  :type="scope.row.status === '运行中' ? 'warning' : 'success'"
                >
                  {{ scope.row.status === '运行中' ? '停止' : '启动' }}
                </el-button>
                <el-button size="small" type="primary" @click="handleShowDetail(scope.row)">详情</el-button>
                <el-button size="small" type="danger" @click="handleDeleteStrategy(scope.row)">删除</el-button>
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

        <!-- 策略详情面板 -->
        <el-drawer
          v-model="detailDrawerVisible"
          :title="`策略详情 - ${currentStrategy?.name || ''}`"
          size="70%"
          direction="rtl"
        >
          <div v-if="currentStrategy" class="strategy-detail">
            <!-- 1. 基础信息 -->
            <el-card shadow="never" class="detail-section">
              <template #header>
                <span class="section-title">基础信息</span>
              </template>
              <el-descriptions :column="2" border>
                <el-descriptions-item label="策略名称">{{ currentStrategy.name }}</el-descriptions-item>
                <el-descriptions-item label="策略ID">{{ currentStrategy.id }}</el-descriptions-item>
                <el-descriptions-item label="作者">{{ currentStrategy.author }}</el-descriptions-item>
                <el-descriptions-item label="创建时间">{{ currentStrategy.createTime }}</el-descriptions-item>
                <el-descriptions-item label="最后修改时间" :span="2">{{ currentStrategy.lastModifyTime }}</el-descriptions-item>
                <el-descriptions-item label="策略描述" :span="2">{{ currentStrategy.description }}</el-descriptions-item>
              </el-descriptions>
            </el-card>

            <!-- 2. 持仓信息 -->
            <el-card shadow="never" class="detail-section">
              <template #header>
                <span class="section-title">持仓信息</span>
              </template>
              <el-table :data="currentStrategy.positions" border stripe>
                <el-table-column prop="contract" label="合约代码" width="100" />
                <el-table-column prop="volume" label="持仓量" width="80" />
                <el-table-column prop="direction" label="方向" width="60">
                  <template #default="scope">
                    <el-tag :type="scope.row.direction === '多' ? 'success' : 'danger'">
                      {{ scope.row.direction }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="holdPrice" label="持仓价" width="100" />
                <el-table-column prop="takeProfitPrice" label="止盈价" width="100" />
                <el-table-column prop="stopLossPrice" label="止损价" width="100" />
                <el-table-column prop="margin" label="保证金" width="120">
                  <template #default="scope">
                    {{ scope.row.margin.toFixed(2) }}
                  </template>
                </el-table-column>
                <el-table-column prop="profitLoss" label="盈亏额" width="100">
                  <template #default="scope">
                    <span :style="{ color: scope.row.profitLoss >= 0 ? '#67C23A' : '#F56C6C' }">
                      {{ scope.row.profitLoss >= 0 ? '+' : '' }}{{ scope.row.profitLoss.toFixed(2) }}
                    </span>
                  </template>
                </el-table-column>
                <el-table-column prop="profitLossRatio" label="盈亏比" width="80">
                  <template #default="scope">
                    <span :style="{ color: scope.row.profitLossRatio >= 0 ? '#67C23A' : '#F56C6C' }">
                      {{ scope.row.profitLossRatio >= 0 ? '+' : '' }}{{ scope.row.profitLossRatio.toFixed(2) }}
                    </span>
                  </template>
                </el-table-column>
                <el-table-column prop="returnRate" label="收益率" width="100">
                  <template #default="scope">
                    <span :style="{ color: scope.row.returnRate >= 0 ? '#67C23A' : '#F56C6C' }">
                      {{ scope.row.returnRate >= 0 ? '+' : '' }}{{ scope.row.returnRate.toFixed(2) }}%
                    </span>
                  </template>
                </el-table-column>
              </el-table>
            </el-card>

            <!-- 3. 参数配置 -->
            <el-card shadow="never" class="detail-section">
              <template #header>
                <div class="section-header">
                  <span class="section-title">参数配置</span>
                  <div>
                    <el-button size="small" @click="handleCancelEdit">取消</el-button>
                    <el-button size="small" type="primary" @click="handleSaveParameters">保存</el-button>
                  </div>
                </div>
              </template>
              
              <el-form :model="editableParameters" label-width="140px">
                <!-- 交易参数 -->
                <el-divider content-position="left">交易参数</el-divider>
                <el-form-item label="最大订单数">
                  <el-input-number v-model="editableParameters.trading.maxOrders" :min="1" :max="20" />
                </el-form-item>

                <!-- 风险参数 -->
                <el-divider content-position="left">风险参数</el-divider>
                <el-form-item label="止损百分比（%）">
                  <el-input-number v-model="editableParameters.risk.stopLossPercent" :min="0.1" :max="10" :step="0.1" :precision="1" />
                </el-form-item>
                <el-form-item label="止盈百分比（%）">
                  <el-input-number v-model="editableParameters.risk.takeProfitPercent" :min="0.1" :max="20" :step="0.1" :precision="1" />
                </el-form-item>
                <el-form-item label="最大回撤（%）">
                  <el-input-number v-model="editableParameters.risk.maxDrawdown" :min="1" :max="50" :step="1" :precision="1" />
                </el-form-item>
              </el-form>
            </el-card>

            <!-- 4. 风险控制 -->
            <el-card shadow="never" class="detail-section">
              <template #header>
                <span class="section-title">风险控制</span>
              </template>
              <el-descriptions :column="2" border>
                <el-descriptions-item label="最大仓位">{{ currentStrategy.riskControl.maxPosition }} 手</el-descriptions-item>
                <el-descriptions-item label="止损比例">{{ currentStrategy.riskControl.stopLossRatio }}%</el-descriptions-item>
              </el-descriptions>
            </el-card>
          </div>
        </el-drawer>
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
  SuccessFilled,
  Cpu,
  Memo
} from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useUserStore } from '@/stores/user'
import { getSystemStats } from '@/api/monitor'

const router = useRouter()
const userStore = useUserStore()

const activeMenu = ref('dashboard')

// 定时器引用
let monitorTimer = null

// 系统监控信息
const systemInfo = reactive({
  cpu: 0,
  memory: 0,
  activeStrategies: 3,  // 硬编码值
  lastUpdate: null,
  loading: false,
  error: null
})

const strategies = ref([
  { 
    // === 基础字段 ===
    id: 'STR001', 
    name: '趋势跟踪策略', 
    status: '运行中', 
    startTime: '2025-10-08 09:30:00',
    runningTime: '12h15m',
    
    // === 基础信息 ===
    description: '基于趋势线和移动平均线的跟踪策略，适用于趋势明显的市场环境，通过识别市场趋势方向进行交易',
    author: '张三',
    createTime: '2025-10-01 14:20:00',
    lastModifyTime: '2025-10-07 16:45:00',
    
    // === 持仓信息 ===
    positions: [
      {
        contract: 'AU2406',
        volume: 10,
        direction: '多',
        holdPrice: 450.5,
        takeProfitPrice: 460.0,
        stopLossPrice: 445.0,
        margin: 45050.0,
        profitLoss: 1200.5,
        profitLossRatio: 2.67,
        returnRate: 2.67
      },
      {
        contract: 'AG2406',
        volume: 20,
        direction: '空',
        holdPrice: 5200.0,
        takeProfitPrice: 5100.0,
        stopLossPrice: 5250.0,
        margin: 104000.0,
        profitLoss: -500.0,
        profitLossRatio: -0.48,
        returnRate: -0.48
      }
    ],
    
    // === 参数配置 ===
    parameters: {
      trading: {
        lotSize: 1,
        maxOrders: 5,
        orderInterval: 60,
        enableCompound: true
      },
      risk: {
        stopLossPercent: 2.0,
        takeProfitPercent: 3.0,
        maxDrawdown: 10.0,
        riskRewardRatio: 1.5
      },
      indicator: {
        maPeriod: 20,
        maType: 'SMA',
        rsiPeriod: 14,
        enableMACD: true
      }
    },
    
    // === 风险控制 ===
    riskControl: {
      maxPosition: 50,
      stopLossRatio: 2.0,
      maxLeverage: 3.0,
      riskLevel: '中'
    }
  },
  { 
    // === 基础字段 ===
    id: 'STR002', 
    name: '均值回归策略', 
    status: '已停止', 
    startTime: '2025-10-07 14:20:00',
    runningTime: '-',
    
    // === 基础信息 ===
    description: '当价格偏离均值时进行反向交易，预期价格会回归均值，适用于震荡市场',
    author: '李四',
    createTime: '2025-09-25 10:30:00',
    lastModifyTime: '2025-10-06 09:15:00',
    
    // === 持仓信息 ===
    positions: [
      {
        contract: 'CU2406',
        volume: 15,
        direction: '多',
        holdPrice: 68500.0,
        takeProfitPrice: 70000.0,
        stopLossPrice: 67500.0,
        margin: 102750.0,
        profitLoss: 850.0,
        profitLossRatio: 0.83,
        returnRate: 0.83
      }
    ],
    
    // === 参数配置 ===
    parameters: {
      trading: {
        lotSize: 2,
        maxOrders: 3,
        orderInterval: 120,
        enableCompound: false
      },
      risk: {
        stopLossPercent: 1.5,
        takeProfitPercent: 2.5,
        maxDrawdown: 8.0,
        riskRewardRatio: 1.8
      },
      indicator: {
        maPeriod: 30,
        maType: 'EMA',
        rsiPeriod: 10,
        enableMACD: false
      }
    },
    
    // === 风险控制 ===
    riskControl: {
      maxPosition: 30,
      stopLossRatio: 1.5,
      maxLeverage: 2.0,
      riskLevel: '低'
    }
  },
  { 
    // === 基础字段 ===
    id: 'STR003', 
    name: '套利策略', 
    status: '运行中', 
    startTime: '2025-10-08 10:45:00',
    runningTime: '10h50m',
    
    // === 基础信息 ===
    description: '利用不同合约或市场间的价差进行套利交易，风险相对较低，收益稳定',
    author: '王五',
    createTime: '2025-10-03 11:00:00',
    lastModifyTime: '2025-10-08 08:30:00',
    
    // === 持仓信息 ===
    positions: [
      {
        contract: 'RB2406',
        volume: 25,
        direction: '多',
        holdPrice: 3850.0,
        takeProfitPrice: 3900.0,
        stopLossPrice: 3820.0,
        margin: 96250.0,
        profitLoss: 625.0,
        profitLossRatio: 0.65,
        returnRate: 0.65
      },
      {
        contract: 'RB2409',
        volume: 25,
        direction: '空',
        holdPrice: 3880.0,
        takeProfitPrice: 3830.0,
        stopLossPrice: 3910.0,
        margin: 97000.0,
        profitLoss: 750.0,
        profitLossRatio: 0.77,
        returnRate: 0.77
      }
    ],
    
    // === 参数配置 ===
    parameters: {
      trading: {
        lotSize: 3,
        maxOrders: 10,
        orderInterval: 30,
        enableCompound: true
      },
      risk: {
        stopLossPercent: 0.8,
        takeProfitPercent: 1.5,
        maxDrawdown: 5.0,
        riskRewardRatio: 2.0
      },
      indicator: {
        maPeriod: 15,
        maType: 'WMA',
        rsiPeriod: 12,
        enableMACD: true
      }
    },
    
    // === 风险控制 ===
    riskControl: {
      maxPosition: 100,
      stopLossRatio: 0.8,
      maxLeverage: 5.0,
      riskLevel: '高'
    }
  }
])

// 计算运行中的策略数量
const runningStrategiesCount = computed(() => {
  return strategies.value.filter(s => s.status === '运行中').length
})

// 计算已停止的策略数量
const stoppedStrategiesCount = computed(() => {
  return strategies.value.filter(s => s.status === '已停止').length
})

// 详情面板状态
const detailDrawerVisible = ref(false)
const currentStrategy = ref(null)
const editableParameters = reactive({
  trading: {},
  risk: {},
  indicator: {}
})

const settings = reactive({
  systemName: 'Homalos',
  autoStart: true,
  logLevel: 'info'
})

/**
 * 获取系统监控数据
 */
const fetchSystemStats = async () => {
  try {
    systemInfo.loading = true
    const data = await getSystemStats()
    
    systemInfo.cpu = data.cpu_percent
    systemInfo.memory = data.memory_percent
    systemInfo.lastUpdate = data.timestamp
    systemInfo.error = null
  } catch (error) {
    console.error('获取监控数据失败:', error)
    systemInfo.error = '获取监控数据失败'
    // 保留上次的数据，不清空
  } finally {
    systemInfo.loading = false
  }
}

/**
 * 启动监控数据轮询
 */
const startMonitoring = () => {
  fetchSystemStats()  // 立即获取一次
  monitorTimer = setInterval(fetchSystemStats, 3000)  // 每3秒刷新
}

/**
 * 停止监控数据轮询
 */
const stopMonitoring = () => {
  if (monitorTimer) {
    clearInterval(monitorTimer)
    monitorTimer = null
  }
}

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
 * 显示策略详情
 */
const handleShowDetail = (strategy) => {
  currentStrategy.value = strategy
  // 深拷贝参数到可编辑对象
  editableParameters.trading = { ...strategy.parameters.trading }
  editableParameters.risk = { ...strategy.parameters.risk }
  editableParameters.indicator = { ...strategy.parameters.indicator }
  detailDrawerVisible.value = true
}

/**
 * 保存参数配置
 */
const handleSaveParameters = () => {
  if (!currentStrategy.value) return
  
  // 更新策略参数
  currentStrategy.value.parameters.trading = { ...editableParameters.trading }
  currentStrategy.value.parameters.risk = { ...editableParameters.risk }
  currentStrategy.value.parameters.indicator = { ...editableParameters.indicator }
  
  // 更新最后修改时间
  const now = new Date()
  currentStrategy.value.lastModifyTime = now.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false
  }).replace(/\//g, '-')
  
  ElMessage.success('参数保存成功')
}

/**
 * 取消编辑
 */
const handleCancelEdit = () => {
  if (!currentStrategy.value) return
  
  // 恢复原始参数
  editableParameters.trading = { ...currentStrategy.value.parameters.trading }
  editableParameters.risk = { ...currentStrategy.value.parameters.risk }
  editableParameters.indicator = { ...currentStrategy.value.parameters.indicator }
  
  ElMessage.info('已取消编辑')
}

/**
 * 获取风险等级标签类型
 */
const getRiskLevelType = (level) => {
  const typeMap = {
    '低': 'success',
    '中': 'warning',
    '高': 'danger'
  }
  return typeMap[level] || 'info'
}

/**
 * 删除策略
 */
const handleDeleteStrategy = (strategy) => {
  ElMessageBox.confirm(
    `确定要删除策略 "${strategy.name}" (ID: ${strategy.id}) 吗？`,
    '删除确认',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    }
  ).then(() => {
    // 从策略列表中移除
    const index = strategies.value.findIndex(s => s.id === strategy.id)
    if (index !== -1) {
      strategies.value.splice(index, 1)
      ElMessage.success(`策略 "${strategy.name}" 已删除`)
    }
  }).catch(() => {
    // 用户取消删除
  })
}

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
  
  // 启动监控
  startMonitoring()
})

onUnmounted(() => {
  // 组件卸载时停止监控
  stopMonitoring()
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

/* 策略详情面板样式 */
.strategy-detail {
  padding: 0 20px 20px;
}

.detail-section {
  margin-bottom: 20px;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

/* 持仓表格紧凑布局 */
.detail-section :deep(.el-table) {
  font-size: 13px;
}

/* 表单项间距 */
.detail-section :deep(.el-form-item) {
  margin-bottom: 18px;
}

/* 分割线样式 */
.detail-section :deep(.el-divider__text) {
  font-weight: 600;
  color: #606266;
}
</style>

