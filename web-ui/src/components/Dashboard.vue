<template>
  <div>
    <!-- 1. 账户总览 -->
    <el-card shadow="hover" style="margin-bottom: 20px;">
      <template #header>
        <div class="card-header">
          <span>{{ accountOverviewTitle }}</span>
        </div>
      </template>
      <div class="account-overview-container">
        <div class="account-item">
          <el-statistic title="总权益" :value="dashboardData.account.totalEquity" :precision="2" prefix="¥">
            <template #prefix>
              <el-icon color="#409EFF"><Wallet /></el-icon>
            </template>
          </el-statistic>
        </div>
        <div class="account-item">
          <el-statistic title="可用资金" :value="dashboardData.account.availableFunds" :precision="2" prefix="¥">
            <template #prefix>
              <el-icon color="#67C23A"><Money /></el-icon>
            </template>
          </el-statistic>
        </div>
        <div class="account-item">
          <el-statistic title="保证金占用" :value="dashboardData.account.marginUsed" :precision="2" prefix="¥">
            <template #prefix>
              <el-icon color="#E6A23C"><Lock /></el-icon>
            </template>
          </el-statistic>
        </div>
        <div class="account-item">
          <el-statistic 
            title="浮动盈亏" 
            :value="dashboardData.account.floatingProfitLoss" 
            :precision="2" 
            prefix="¥"
            :value-style="{ color: dashboardData.account.floatingProfitLoss > 0 ? '#F56C6C' : dashboardData.account.floatingProfitLoss < 0 ? '#67C23A' : '#000000' }"
          >
            <template #prefix>
              <el-icon :color="dashboardData.account.floatingProfitLoss > 0 ? '#F56C6C' : dashboardData.account.floatingProfitLoss < 0 ? '#67C23A' : '#000000'">
                <TrendCharts />
              </el-icon>
            </template>
          </el-statistic>
        </div>
        <div class="account-item">
          <el-statistic 
            title="资金使用率" 
            :value="dashboardData.account.fundUtilizationRate" 
            :precision="2" 
            suffix="%"
          >
            <template #prefix>
              <el-icon color="#909399">
                <DataAnalysis />
              </el-icon>
            </template>
          </el-statistic>
        </div>
      </div>
    </el-card>

    <!-- 2. 今日表现（独占一行） -->
    <el-row style="margin-bottom: 20px;">
      <el-col :span="24">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span>今日表现（{{ todayDate }}）</span>
            </div>
          </template>
          <el-row :gutter="20">
            <el-col :span="8">
              <el-statistic 
                title="当日收益率" 
                :value="dashboardData.todayPerformance.returnRate" 
                :precision="2" 
                suffix="%"
                :value-style="{ color: dashboardData.todayPerformance.returnRate > 0 ? '#F56C6C' : dashboardData.todayPerformance.returnRate < 0 ? '#67C23A' : '#000000' }"
              >
                <template #prefix>
                  <el-icon :color="dashboardData.todayPerformance.returnRate > 0 ? '#F56C6C' : dashboardData.todayPerformance.returnRate < 0 ? '#67C23A' : '#000000'">
                    <DataLine />
                  </el-icon>
                </template>
              </el-statistic>
            </el-col>
            <el-col :span="8">
              <el-statistic 
                title="盈亏金额" 
                :value="dashboardData.todayPerformance.profitLoss" 
                :precision="2" 
                prefix="¥"
                :value-style="{ color: dashboardData.todayPerformance.profitLoss > 0 ? '#F56C6C' : dashboardData.todayPerformance.profitLoss < 0 ? '#67C23A' : '#000000' }"
              >
                <template #prefix>
                  <el-icon :color="dashboardData.todayPerformance.profitLoss > 0 ? '#F56C6C' : dashboardData.todayPerformance.profitLoss < 0 ? '#67C23A' : '#000000'">
                    <Coin />
                  </el-icon>
                </template>
              </el-statistic>
            </el-col>
            <el-col :span="8">
              <el-statistic title="交易次数" :value="dashboardData.todayPerformance.tradeCount">
                <template #prefix>
                  <el-icon color="#409EFF"><Operation /></el-icon>
                </template>
              </el-statistic>
            </el-col>
          </el-row>
        </el-card>
      </el-col>
    </el-row>

    <!-- 3. 系统监控 & 策略运行状态 -->
    <el-row :gutter="20" style="margin-bottom: 20px;">
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span>系统监控</span>
            </div>
          </template>
          <el-row :gutter="16">
            <el-col :span="6">
              <div class="custom-statistic">
                <div class="statistic-title">交易系统状态</div>
                <div class="statistic-content">
                  <el-icon :color="tradingCoreStatusInfo.color" class="statistic-icon">
                    <component :is="tradingCoreStatusInfo.icon" />
                  </el-icon>
                  <span class="statistic-value" :style="{ color: tradingCoreStatusInfo.color }">
                    {{ tradingCoreStatusInfo.text }}
                  </span>
                </div>
              </div>
            </el-col>
            <el-col :span="6">
              <div class="custom-statistic">
                <div class="statistic-title">数据中心状态</div>
                <div class="statistic-content">
                  <el-icon :color="dataCenterStatusInfo.color" class="statistic-icon">
                    <component :is="dataCenterStatusInfo.icon" />
                  </el-icon>
                  <span class="statistic-value" :style="{ color: dataCenterStatusInfo.color }">
                    {{ dataCenterStatusInfo.text }}
                  </span>
                </div>
              </div>
            </el-col>
            <el-col :span="6">
              <div class="custom-statistic">
                <div class="statistic-title">CPU使用率</div>
                <div class="statistic-content">
                  <el-icon color="#409EFF" class="statistic-icon">
                    <Cpu />
                  </el-icon>
                  <span class="statistic-value" style="color: #409EFF;">
                    {{ systemInfo.cpu }}%
                  </span>
                </div>
              </div>
            </el-col>
            <el-col :span="6">
              <div class="custom-statistic">
                <div class="statistic-title">内存使用率</div>
                <div class="statistic-content">
                  <el-icon color="#409EFF" class="statistic-icon">
                    <Memo />
                  </el-icon>
                  <span class="statistic-value" style="color: #409EFF;">
                    {{ systemInfo.memory }}%
                  </span>
                </div>
              </div>
            </el-col>
          </el-row>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span>策略状态</span>
            </div>
          </template>
          <el-row :gutter="20">
            <el-col :span="8">
              <div class="custom-statistic">
                <div class="statistic-title">活跃策略</div>
                <div class="statistic-content">
                  <el-icon color="#409EFF" class="statistic-icon">
                    <TrendCharts />
                  </el-icon>
                  <span class="statistic-value" style="color: #409EFF;">
                    {{ strategyStatusData.active }}
                  </span>
                </div>
              </div>
            </el-col>
            <el-col :span="8">
              <div class="custom-statistic">
                <div class="statistic-title">运行中</div>
                <div class="statistic-content">
                  <el-icon color="#67C23A" class="statistic-icon">
                    <VideoPlay />
                  </el-icon>
                  <span class="statistic-value" style="color: #67C23A;">
                    {{ strategyStatusData.running }}
                  </span>
                </div>
              </div>
            </el-col>
            <el-col :span="8">
              <div class="custom-statistic">
                <div class="statistic-title">已停止</div>
                <div class="statistic-content">
                  <el-icon color="#909399" class="statistic-icon">
                    <VideoPause />
                  </el-icon>
                  <span class="statistic-value" style="color: #909399;">
                    {{ strategyStatusData.stopped }}
                  </span>
                </div>
              </div>
            </el-col>
          </el-row>
        </el-card>
      </el-col>
    </el-row>

    <!-- 4. 持仓概览（独占一行） -->
    <el-row style="margin-bottom: 20px;">
      <el-col :span="24">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span>持仓概览</span>
            </div>
          </template>
          <div style="padding: 10px 0;">
            <div v-for="(item, index) in dashboardData.positions" :key="index" style="margin-bottom: 10px;">
              <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                <span>{{ item.name }}</span>
                <span>{{ item.ratio }}%</span>
              </div>
              <el-progress :percentage="item.ratio" :color="item.color" :show-text="false" />
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 5. 关键指标图表 -->
    <el-card shadow="hover">
      <template #header>
        <div class="card-header">
          <span>关键指标图表</span>
        </div>
      </template>
      <el-row :gutter="20">
        <el-col :span="8">
          <div class="chart-container">
            <div class="chart-header">
              <div class="chart-title">权益曲线</div>
              <el-select 
                v-model="chartPeriods.equity" 
                size="small" 
                style="width: 100px;"
                @change="handlePeriodChange('equity')"
              >
                <el-option label="近1周" value="1week" />
                <el-option label="近1月" value="1month" />
                <el-option label="近3月" value="3months" />
                <el-option label="近6月" value="6months" />
                <el-option label="全部" value="all" />
              </el-select>
            </div>
            <EquityCurveChart :data="filteredChartData.equityCurve" />
          </div>
        </el-col>
        <el-col :span="8">
          <div class="chart-container">
            <div class="chart-header">
              <div class="chart-title">盈亏图表</div>
              <el-select 
                v-model="chartPeriods.profitLoss" 
                size="small" 
                style="width: 100px;"
                @change="handlePeriodChange('profitLoss')"
              >
                <el-option label="近1周" value="1week" />
                <el-option label="近1月" value="1month" />
                <el-option label="近3月" value="3months" />
                <el-option label="近6月" value="6months" />
                <el-option label="全部" value="all" />
              </el-select>
            </div>
            <ProfitLossChart :data="filteredChartData.profitLoss" />
          </div>
        </el-col>
        <el-col :span="8">
          <div class="chart-container">
            <div class="chart-header">
              <div class="chart-title">收益率曲线</div>
              <el-select 
                v-model="chartPeriods.returnRate" 
                size="small" 
                style="width: 100px;"
                @change="handlePeriodChange('returnRate')"
              >
                <el-option label="近1周" value="1week" />
                <el-option label="近1月" value="1month" />
                <el-option label="近3月" value="3months" />
                <el-option label="近6月" value="6months" />
                <el-option label="全部" value="all" />
              </el-select>
            </div>
            <ReturnRateChart :data="filteredChartData.returnRate" />
          </div>
        </el-col>
      </el-row>
    </el-card>
  </div>
</template>

<script setup>
import { reactive, computed, watch, onMounted, onUnmounted } from 'vue'
import {
  Wallet,
  Money,
  Lock,
  TrendCharts,
  DataLine,
  Coin,
  Operation,
  VideoPlay,
  VideoPause,
  Warning,
  SuccessFilled,
  Cpu,
  Memo,
  DataAnalysis,
  Connection,
  Loading,
  CircleCloseFilled
} from '@element-plus/icons-vue'
import { emptyDashboardData, dashboardData as dashboardDataImport } from '@/mock'
import { useSystemMonitor } from '@/composables'
import { useTradingAccountStore } from '@/stores/tradingAccount'
import { getTradingCoreStatus } from '@/api/tradingCore'
import { getDataCenterStatus } from '@/api/datacenter'
import { getStrategyStatus } from '@/api/strategy'
import EquityCurveChart from './charts/EquityCurveChart.vue'
import ProfitLossChart from './charts/ProfitLossChart.vue'
import ReturnRateChart from './charts/ReturnRateChart.vue'

// 初始化交易账户 Store
const tradingAccountStore = useTradingAccountStore()

// 系统状态（交易核心和数据中心）
const systemStatus = reactive({
  tradingCore: 'stopped',  // stopped | initializing | connecting | running | stopping | error
  dataCenter: false        // running: true/false
})

// 策略状态（真实数据）
const strategyStatusData = reactive({
  active: 0,    // 活跃策略数
  running: 0,   // 运行中策略数
  stopped: 0    // 已停止策略数
})

// 使用归零数据初始化（系统未启动时）
const dashboardData = reactive(emptyDashboardData)

// 监听 WebSocket 连接状态，决定显示归零数据还是实时数据
watch(
  () => tradingAccountStore.isWsConnected,
  (isConnected) => {
    if (!isConnected) {
      // 未连接时，重置为归零数据
      Object.assign(dashboardData, emptyDashboardData)
    }
  },
  { immediate: true }
)

// 监听实时账户数据，动态更新仪表盘
watch(
  () => tradingAccountStore.accountData,
  (newAccountData) => {
    if (newAccountData && newAccountData.balance > 0) {
      dashboardData.account.totalEquity = newAccountData.balance
      dashboardData.account.availableFunds = newAccountData.available
      dashboardData.account.marginUsed = newAccountData.frozen
      dashboardData.account.fundUtilizationRate = newAccountData.balance > 0
        ? (newAccountData.frozen / newAccountData.balance) * 100
        : 0
    }
  },
  { deep: true, immediate: true }
)

// 监听实时持仓数据，更新浮动盈亏
watch(
  () => tradingAccountStore.totalPnl,
  (newPnl) => {
    dashboardData.account.floatingProfitLoss = newPnl
  },
  { immediate: true }
)

// 图表周期选择状态
const chartPeriods = reactive({
  equity: 'all',      // 权益曲线周期
  profitLoss: 'all',  // 盈亏图表周期
  returnRate: 'all'   // 收益率曲线周期
})

// 系统监控数据
const {
  systemInfo,
  startMonitoring,
  stopMonitoring
} = useSystemMonitor()

// 今日日期显示
const todayDate = computed(() => {
  const date = new Date()
  return date.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  })
})

/**
 * 数据过滤函数 - 根据选择的周期过滤图表数据
 * @param {Array} data - 原始数据数组
 * @param {string} period - 周期选项 ('1week'|'1month'|'3months'|'6months'|'all')
 * @returns {Array} 过滤后的数据数组
 * 
 * 数据限制策略：
 * - 近1周：最近7天
 * - 近1月：最近1个月
 * - 近3月：最近3个月
 * - 近6月：最近6个月
 * - 全部：最多3年数据（防止数据过大影响性能）
 */
function filterDataByPeriod(data, period) {
  const now = new Date()
  let startDate = new Date()
  
  switch (period) {
    case '1week':
      startDate.setDate(now.getDate() - 7)
      break
    case '1month':
      startDate.setMonth(now.getMonth() - 1)
      break
    case '3months':
      startDate.setMonth(now.getMonth() - 3)
      break
    case '6months':
      startDate.setMonth(now.getMonth() - 6)
      break
    case 'all':
      // 全部数据限制为最多3年
      startDate.setFullYear(now.getFullYear() - 3)
      break
    default:
      // 默认也限制为3年
      startDate.setFullYear(now.getFullYear() - 3)
      break
  }
  
  return data.filter(item => {
    const itemDate = new Date(item.date)
    return itemDate >= startDate
  })
}

// 过滤后的图表数据
const filteredChartData = computed(() => ({
  equityCurve: filterDataByPeriod(dashboardData.chartData.equityCurve, chartPeriods.equity),
  profitLoss: filterDataByPeriod(dashboardData.chartData.profitLoss, chartPeriods.profitLoss),
  returnRate: filterDataByPeriod(dashboardData.chartData.returnRate, chartPeriods.returnRate)
}))

// 周期变更处理函数
function handlePeriodChange(chartType) {
  console.log(`${chartType} 图表周期已更改为: ${chartPeriods[chartType]}`)
}

/**
 * 加密账号 - 只显示后4位，前面用*替代
 * @param {string|number} accountId - 原始账号（支持字符串和数字）
 * @returns {string} 加密后的账号
 * @example
 * maskAccountId('123456789') // '*****6789'
 * maskAccountId(160219)      // '**0219'
 * maskAccountId('1234')      // '1234'
 */
function maskAccountId(accountId) {
  // 防御性编程：确保是字符串
  const accountStr = String(accountId || '')
  
  if (!accountStr || accountStr.length <= 4) {
    return accountStr
  }
  
  const visiblePart = accountStr.slice(-4)  // 后4位
  const maskedPart = '*'.repeat(accountStr.length - 4)  // 前面用*替代
  return maskedPart + visiblePart
}

// 账户总览标题
const accountOverviewTitle = computed(() => {
  // 如果未登录资金账户，只显示"账户总览"
  if (!tradingAccountStore.isLoggedIn) {
    return '账户总览'
  }
  
  // 获取账户信息
  const accountName = tradingAccountStore.accountInfo?.display_name || '未命名账户'
  const accountId = tradingAccountStore.accountInfo?.account_id || ''
  
  // 加密账号
  const maskedAccount = maskAccountId(accountId)
  
  // 显示格式：账户总览 - 账户名称 (加密账号)
  return `账户总览 - ${accountName} (${maskedAccount})`
})

/**
 * 获取交易核心状态
 */
async function fetchTradingCoreStatus() {
  try {
    const status = await getTradingCoreStatus()
    systemStatus.tradingCore = status.status || 'stopped'
  } catch (error) {
    console.error('获取交易核心状态失败:', error)
    systemStatus.tradingCore = 'stopped'
  }
}

/**
 * 获取数据中心状态
 */
async function fetchDataCenterStatus() {
  try {
    const status = await getDataCenterStatus()
    systemStatus.dataCenter = status.running || false
  } catch (error) {
    console.error('获取数据中心状态失败:', error)
    systemStatus.dataCenter = false
  }
}

/**
 * 获取策略状态
 */
async function fetchStrategyStatus() {
  try {
    const status = await getStrategyStatus()
    strategyStatusData.active = status.total || 0
    strategyStatusData.running = status.running || 0
    strategyStatusData.stopped = status.stopped || 0
  } catch (error) {
    console.error('获取策略状态失败:', error)
    strategyStatusData.active = 0
    strategyStatusData.running = 0
    strategyStatusData.stopped = 0
  }
}

/**
 * 获取所有系统状态
 */
async function fetchSystemStatus() {
  await Promise.all([
    fetchTradingCoreStatus(),
    fetchDataCenterStatus(),
    fetchStrategyStatus()
  ])
}

/**
 * 交易核心状态显示信息
 */
const tradingCoreStatusInfo = computed(() => {
  const statusMap = {
    stopped: { text: '已停止', color: '#909399', icon: 'VideoPause' },
    initializing: { text: '初始化中', color: '#E6A23C', icon: 'Loading' },
    connecting: { text: '连接中', color: '#E6A23C', icon: 'Loading' },
    running: { text: '运行中', color: '#67C23A', icon: 'SuccessFilled' },
    stopping: { text: '停止中', color: '#E6A23C', icon: 'Loading' },
    error: { text: '错误', color: '#F56C6C', icon: 'CircleCloseFilled' }
  }
  return statusMap[systemStatus.tradingCore] || statusMap.stopped
})

/**
 * 数据中心状态显示信息
 */
const dataCenterStatusInfo = computed(() => {
  if (systemStatus.dataCenter) {
    return { text: '运行中', color: '#67C23A', icon: 'SuccessFilled' }
  } else {
    return { text: '已停止', color: '#909399', icon: 'VideoPause' }
  }
})

let systemStatusTimer = null

/**
 * 启动系统状态轮询
 */
function startSystemStatusPolling() {
  if (systemStatusTimer) return
  
  fetchSystemStatus()  // 立即获取一次
  systemStatusTimer = setInterval(fetchSystemStatus, 5000)  // 每5秒刷新
}

/**
 * 停止系统状态轮询
 */
function stopSystemStatusPolling() {
  if (systemStatusTimer) {
    clearInterval(systemStatusTimer)
    systemStatusTimer = null
  }
}

// 组件挂载时启动监控
onMounted(() => {
  startMonitoring()
  startSystemStatusPolling()
  // 连接账户数据WebSocket
  tradingAccountStore.connectAccountWs()
})

// 组件卸载时停止监控
onUnmounted(() => {
  stopMonitoring()
  stopSystemStatusPolling()
  // 断开账户数据WebSocket
  tradingAccountStore.disconnectAccountWs()
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

/* 账户总览容器 - flexbox布局 */
.account-overview-container {
  display: flex;
  justify-content: space-between;
  align-items: stretch;
  gap: 16px;
  flex-wrap: wrap;
}

/* 账户统计项 */
.account-item {
  flex: 1;
  min-width: 180px;
  max-width: 240px;
  text-align: center;
}

/* 响应式设计 */
@media (max-width: 1200px) {
  .account-item {
    min-width: 160px;
    max-width: 200px;
  }
}

@media (max-width: 992px) {
  .account-overview-container {
    gap: 12px;
  }
  
  .account-item {
    min-width: 140px;
    max-width: 180px;
  }
}

@media (max-width: 768px) {
  .account-overview-container {
    flex-direction: column;
    gap: 16px;
  }
  
  .account-item {
    max-width: none;
    min-width: auto;
  }
}

@media (max-width: 576px) {
  .account-overview-container {
    gap: 12px;
  }
}

/* 图表容器样式 */
.chart-container {
  background-color: #f9f9f9;
  border-radius: 8px;
  padding: 16px;
  height: 240px;
  display: flex;
  flex-direction: column;
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.chart-title {
  font-size: 14px;
  font-weight: 500;
  color: #303133;
}

/* 响应式图表设计 */
@media (max-width: 1200px) {
  .chart-container {
    height: 220px;
    padding: 12px;
  }
  
  .chart-title {
    font-size: 13px;
    margin-bottom: 8px;
  }
}

@media (max-width: 768px) {
  .chart-container {
    height: 200px;
    padding: 10px;
    margin-bottom: 16px;
  }
  
  .chart-title {
    font-size: 12px;
    margin-bottom: 6px;
  }
}

/* 自定义统计组件样式 */
.custom-statistic {
  text-align: center;
  padding: 10px 0;
}

.statistic-title {
  color: #909399;
  font-size: 14px;
  margin-bottom: 10px;
  line-height: 22px;
}

.statistic-content {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.statistic-icon {
  font-size: 20px;
}

.statistic-value {
  font-size: 24px;
  font-weight: 600;
  line-height: 32px;
}
</style>

