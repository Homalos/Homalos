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
          <div class="custom-statistic">
            <div class="statistic-title">总权益</div>
            <div class="statistic-content">
              <el-icon color="#409EFF" class="statistic-icon">
                <Wallet />
              </el-icon>
              <el-tooltip 
                :content="`精确值: ¥${dashboardData.account.totalEquity.toFixed(2)}`" 
                placement="top"
              >
                <span class="statistic-value" style="color: #409EFF;">
                  {{ formatCurrency(dashboardData.account.totalEquity) }}
                </span>
              </el-tooltip>
            </div>
          </div>
        </div>
        <div class="account-item">
          <div class="custom-statistic">
            <div class="statistic-title">可用资金</div>
            <div class="statistic-content">
              <el-icon color="#67C23A" class="statistic-icon">
                <Money />
              </el-icon>
              <el-tooltip 
                :content="`精确值: ¥${dashboardData.account.availableFunds.toFixed(2)}`" 
                placement="top"
              >
                <span class="statistic-value" style="color: #67C23A;">
                  {{ formatCurrency(dashboardData.account.availableFunds) }}
                </span>
              </el-tooltip>
            </div>
          </div>
        </div>
        <div class="account-item">
          <div class="custom-statistic">
            <div class="statistic-title">保证金占用</div>
            <div class="statistic-content">
              <el-icon color="#E6A23C" class="statistic-icon">
                <Lock />
              </el-icon>
              <el-tooltip 
                :content="`精确值: ¥${dashboardData.account.marginUsed.toFixed(2)}`" 
                placement="top"
              >
                <span class="statistic-value" style="color: #E6A23C;">
                  {{ formatCurrency(dashboardData.account.marginUsed) }}
                </span>
              </el-tooltip>
            </div>
          </div>
        </div>
        <div class="account-item">
          <div class="custom-statistic">
            <div class="statistic-title">浮动盈亏</div>
            <div class="statistic-content">
              <el-icon 
                :color="dashboardData.account.floatingProfitLoss > 0 ? '#F56C6C' : dashboardData.account.floatingProfitLoss < 0 ? '#67C23A' : '#909399'" 
                class="statistic-icon"
              >
                <TrendCharts />
              </el-icon>
              <el-tooltip 
                :content="`精确值: ¥${dashboardData.account.floatingProfitLoss.toFixed(2)}`" 
                placement="top"
              >
                <span 
                  class="statistic-value" 
                  :style="{ color: dashboardData.account.floatingProfitLoss > 0 ? '#F56C6C' : dashboardData.account.floatingProfitLoss < 0 ? '#67C23A' : '#909399' }"
                >
                  {{ formatCurrency(dashboardData.account.floatingProfitLoss) }}
                </span>
              </el-tooltip>
            </div>
          </div>
        </div>
        <div class="account-item">
          <div class="custom-statistic">
            <div class="statistic-title">资金使用率</div>
            <div class="statistic-content">
              <el-icon color="#909399" class="statistic-icon">
                <DataAnalysis />
              </el-icon>
              <span class="statistic-value" style="color: #909399;">
                {{ formatPercentage(dashboardData.account.fundUtilizationRate) }}
              </span>
            </div>
          </div>
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
              <div class="custom-statistic">
                <div class="statistic-title">当日收益率</div>
                <div class="statistic-content">
                  <el-icon 
                    :color="dashboardData.todayPerformance.returnRate > 0 ? '#F56C6C' : dashboardData.todayPerformance.returnRate < 0 ? '#67C23A' : '#909399'" 
                    class="statistic-icon"
                  >
                    <DataLine />
                  </el-icon>
                  <span 
                    class="statistic-value" 
                    :style="{ color: dashboardData.todayPerformance.returnRate > 0 ? '#F56C6C' : dashboardData.todayPerformance.returnRate < 0 ? '#67C23A' : '#909399' }"
                  >
                    {{ formatPercentage(dashboardData.todayPerformance.returnRate) }}
                  </span>
                </div>
              </div>
            </el-col>
            <el-col :span="8">
              <div class="custom-statistic">
                <div class="statistic-title">盈亏金额</div>
                <div class="statistic-content">
                  <el-icon 
                    :color="dashboardData.todayPerformance.profitLoss > 0 ? '#F56C6C' : dashboardData.todayPerformance.profitLoss < 0 ? '#67C23A' : '#909399'" 
                    class="statistic-icon"
                  >
                    <Coin />
                  </el-icon>
                  <el-tooltip 
                    :content="`精确值: ¥${dashboardData.todayPerformance.profitLoss.toFixed(2)}`" 
                    placement="top"
                  >
                    <span 
                      class="statistic-value" 
                      :style="{ color: dashboardData.todayPerformance.profitLoss > 0 ? '#F56C6C' : dashboardData.todayPerformance.profitLoss < 0 ? '#67C23A' : '#909399' }"
                    >
                      {{ formatCurrency(dashboardData.todayPerformance.profitLoss) }}
                    </span>
                  </el-tooltip>
                </div>
              </div>
            </el-col>
            <el-col :span="8">
              <div class="custom-statistic">
                <div class="statistic-title">交易次数</div>
                <div class="statistic-content">
                  <el-icon color="#409EFF" class="statistic-icon">
                    <Operation />
                  </el-icon>
                  <span class="statistic-value" style="color: #409EFF;">
                    {{ dashboardData.todayPerformance.tradeCount }}
                  </span>
                </div>
              </div>
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
          <!-- 1x3网格布局 -->
          <el-row :gutter="20">
            <el-col :span="8">
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
            <el-col :span="8">
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
            <el-col :span="8">
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
            <div v-if="dashboardData.positions.length === 0" style="text-align: center; color: #909399; padding: 20px;">
              暂无持仓
            </div>
            <div v-else>
              <div v-for="(item, index) in dashboardData.positions" :key="index" style="margin-bottom: 15px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                  <div style="display: flex; align-items: center; gap: 8px;">
                    <span style="font-weight: 600; font-size: 14px;">{{ item.name }}</span>
                    <el-tag :type="item.direction === '多' ? 'danger' : 'success'" size="small">
                      {{ item.direction }}
                    </el-tag>
                  </div>
                  <span style="font-weight: 600; color: #409EFF;">{{ item.ratio }}%</span>
                </div>
                <div style="display: flex; justify-content: space-between; font-size: 12px; color: #606266; margin-bottom: 5px;">
                  <span>数量: {{ item.volume }}手 | 价格: {{ item.price.toFixed(2) }}</span>
                  <span :style="{ color: item.pnl >= 0 ? '#67C23A' : '#F56C6C', fontWeight: 600 }">
                    盈亏: {{ item.pnl >= 0 ? '+' : '' }}{{ item.pnl.toFixed(2) }}
                  </span>
                </div>
                <el-progress :percentage="item.ratio" :color="item.color" :show-text="false" />
              </div>
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
import { getStrategies, getStrategyStatus } from '@/api/strategy'
import { connectAccountWebSocket } from '@/api/account'
import EquityCurveChart from './charts/EquityCurveChart.vue'
import ProfitLossChart from './charts/ProfitLossChart.vue'
import ReturnRateChart from './charts/ReturnRateChart.vue'
import { formatCurrency, formatPercentage, formatLargeNumber } from '@/utils/formatNumber'

// 初始化交易账户 Store
const tradingAccountStore = useTradingAccountStore()

// 系统状态（交易核心）
const systemStatus = reactive({
  tradingCore: 'stopped'  // stopped | initializing | connecting | running | stopping | error
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

// 监听持仓数据，更新持仓概览
// 使用计算属性来确保数组长度变化被检测到
const positionCount = computed(() => tradingAccountStore.positions.length)

watch(
  positionCount,
  () => {
    const newPositions = tradingAccountStore.positions
    console.log('[Dashboard] 持仓数据更新，新持仓数量:', newPositions?.length || 0)
    if (newPositions && newPositions.length > 0) {
      // 去重：根据instrument_id和direction合并相同的持仓
      const positionMap = new Map()
      newPositions.forEach(pos => {
        const key = `${pos.instrument_id}_${pos.direction}`
        if (!positionMap.has(key)) {
          positionMap.set(key, pos)
        }
      })
      
      const uniquePositions = Array.from(positionMap.values())
      console.log('[Dashboard] 去重后持仓数量:', uniquePositions.length)
      
      // 计算总市值
      const totalValue = uniquePositions.reduce((sum, pos) => {
        return sum + (pos.volume * pos.price)
      }, 0)
      
      // 转换为仪表盘显示格式
      dashboardData.positions = uniquePositions.map((pos, index) => {
        const value = pos.volume * pos.price
        const ratio = totalValue > 0 ? (value / totalValue * 100).toFixed(2) : 0
        
        // 根据方向选择颜色
        const colors = ['#409EFF', '#67C23A', '#E6A23C', '#F56C6C', '#909399']
        const colorIndex = index % colors.length
        
        return {
          name: pos.instrument_id,
          direction: pos.direction,
          ratio: parseFloat(ratio),
          color: colors[colorIndex],
          volume: pos.volume,
          price: pos.price,
          pnl: pos.pnl
        }
      })
      console.log('[Dashboard] 持仓概览已更新:', dashboardData.positions.map(p => p.name))
    } else {
      console.log('[Dashboard] 持仓为空，清空持仓概览')
      dashboardData.positions = []
    }
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
  // 如果未登录券商账户，只显示"账户总览"
  if (!tradingAccountStore.isLoggedIn) {
    return '账户总览'
  }
  
  // 获取账户信息
  // 新的UserBrokerage模型使用account_name，旧的TradingAccount使用display_name
  const accountName = tradingAccountStore.accountInfo?.account_name || 
                      tradingAccountStore.accountInfo?.display_name || 
                      '未命名账户'
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
 * 获取策略状态
 */
async function fetchStrategyStatus() {
  try {
    // 同时获取策略列表和运行状态
    const [strategiesResponse, statusResponse] = await Promise.all([
      getStrategies(),
      getStrategyStatus()
    ])
    
    // 获取已加载的策略（对象格式）
    const loadedStrategies = strategiesResponse.strategies || {}
    const loadedCount = Object.keys(loadedStrategies).length
    
    // 获取运行状态（对象格式）
    const runningStrategies = statusResponse.running || {}
    
    // 计算运行中的策略数量（alive === true）
    const runningArray = Object.values(runningStrategies)
    const runningCount = runningArray.filter(s => s.alive === true).length
    
    // 已停止 = 已加载 - 运行中
    const stoppedCount = loadedCount - runningCount
    
    strategyStatusData.active = loadedCount
    strategyStatusData.running = runningCount
    strategyStatusData.stopped = stoppedCount
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
/* 全局卡片优化 - 增强视觉效果 */
:deep(.el-card),
.el-card {
  border-radius: 12px !important;
  border: 1px solid rgba(64, 158, 255, 0.08) !important;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
  overflow: hidden !important;
}

:deep(.el-card__header),
.el-card__header {
  border-radius: 12px 12px 0 0 !important;
}

:deep(.el-card__body),
.el-card__body {
  border-radius: 0 0 12px 12px !important;
}

:deep(.el-card.is-hover-shadow:hover),
:deep(.el-card.is-always-shadow),
.el-card.is-hover-shadow:hover,
.el-card.is-always-shadow {
  box-shadow: 0 4px 20px rgba(64, 158, 255, 0.12) !important;
}

/* 进度条美化 - 添加渐变和发光效果 */
:deep(.el-progress-bar__outer) {
  background-color: rgba(64, 158, 255, 0.08) !important;
  border-radius: 10px !important;
  overflow: hidden;
}

:deep(.el-progress-bar__inner) {
  border-radius: 10px !important;
  transition: all 0.6s cubic-bezier(0.4, 0, 0.2, 1) !important;
  position: relative;
  overflow: hidden;
}

/* 进度条发光效果 */
:deep(.el-progress-bar__inner)::after {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(90deg, 
    transparent 0%, 
    rgba(255, 255, 255, 0.3) 50%, 
    transparent 100%);
  animation: progressGlow 2s ease-in-out infinite;
}

@keyframes progressGlow {
  0% {
    transform: translateX(-100%);
  }
  100% {
    transform: translateX(100%);
  }
}

/* 卡片header优化 - 增加渐变边框和视觉层次 */
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  position: relative;
}

.card-header span {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  position: relative;
  padding-left: 12px;
}

/* header左侧渐变装饰条 */
.card-header span::before {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 4px;
  height: 18px;
  background: linear-gradient(135deg, #409eff 0%, #67c23a 100%);
  border-radius: 2px;
}

/* 账户总览容器 - flexbox布局优化 */
.account-overview-container {
  display: flex;
  justify-content: space-between;
  align-items: stretch;
  gap: 20px; /* 从16px增加到20px */
  flex-wrap: wrap;
}

/* 账户统计项 - 增加卡片内嵌套效果 */
.account-item {
  flex: 1;
  min-width: 200px; /* 从180px增加到200px，给数字更多空间 */
  max-width: 260px; /* 从240px增加到260px */
  text-align: center;
  background: linear-gradient(135deg, rgba(64, 158, 255, 0.03) 0%, rgba(103, 194, 58, 0.03) 100%);
  border-radius: 12px;
  padding: 12px 8px; /* 增加上下内边距 */
  border: 1px solid rgba(64, 158, 255, 0.08);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
  display: flex; /* 添加flex布局 */
  flex-direction: column; /* 垂直排列 */
  justify-content: center; /* 垂直居中 */
}

/* hover效果 - 微妙上浮 */
.account-item:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.1);
  border-color: rgba(64, 158, 255, 0.15);
}

/* 账户项背景装饰 */
.account-item::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: linear-gradient(90deg, #409eff 0%, #67c23a 50%, #e6a23c 100%);
  opacity: 0;
  transition: opacity 0.3s ease;
}

.account-item:hover::before {
  opacity: 1;
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

/* 图表容器样式 - 优化版 */
.chart-container {
  background: linear-gradient(135deg, #f5f7fa 0%, #f9f9f9 100%); /* 渐变背景 */
  border-radius: 12px; /* 从8px增加到12px */
  padding: 20px; /* 从16px增加到20px */
  height: 240px;
  display: flex;
  flex-direction: column;
  border: 1px solid rgba(64, 158, 255, 0.05);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.02); /* 添加轻微阴影 */
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.chart-container:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(64, 158, 255, 0.08);
  border-color: rgba(64, 158, 255, 0.1);
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px; /* 从12px增加到16px */
}

.chart-title {
  font-size: 15px; /* 从14px增加到15px */
  font-weight: 600; /* 从500增加到600 */
  color: #303133;
  position: relative;
  padding-left: 10px;
}

/* 图表标题左侧装饰条 */
.chart-title::before {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 14px;
  background: linear-gradient(135deg, #409eff 0%, #67c23a 100%);
  border-radius: 2px;
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

/* 自定义统计组件样式 - 优化版 */
.custom-statistic {
  text-align: center;
  padding: 16px 0; /* 从10px增加到16px，更透气 */
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.statistic-title {
  color: #909399;
  font-size: 14px;
  margin-bottom: 12px; /* 从10px增加到12px */
  line-height: 22px;
  font-weight: 500;
}

.statistic-content {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px; /* 从8px增加到12px，图标和数字间距更大 */
  flex-wrap: wrap; /* 允许换行 */
  min-height: 60px; /* 设置最小高度，保持一致性 */
}

/* 图标增强 - 更大更醒目 */
.statistic-icon {
  font-size: 28px; /* 从20px增加到28px，提升视觉冲击力 */
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.1));
}

/* 数字增强 - 更大更醒目，支持自动换行 */
.statistic-value {
  font-size: 28px; /* 从32px调整到28px，避免过大 */
  font-weight: 700; /* 从600增加到700，更粗 */
  line-height: 36px; /* 从40px调整到36px */
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.05); /* 添加文字阴影 */
  word-break: break-all; /* 允许在任意字符间换行 */
  hyphens: auto; /* 自动断字 */
  max-width: 100%; /* 确保不超出容器 */
  text-align: center; /* 居中对齐 */
}
</style>

