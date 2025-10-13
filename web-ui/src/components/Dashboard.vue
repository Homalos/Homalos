<template>
  <div>
    <!-- 1. 账户总览 -->
    <el-card shadow="hover" style="margin-bottom: 20px;">
      <template #header>
        <div class="card-header">
          <span>{{ accountOverviewTitle }}</span>
        </div>
      </template>
      <el-row :gutter="20">
        <el-col :span="6">
          <el-statistic title="总资产" :value="dashboardData.account.totalAssets" precision="2" prefix="¥">
            <template #prefix>
              <el-icon color="#409EFF"><Wallet /></el-icon>
            </template>
          </el-statistic>
        </el-col>
        <el-col :span="6">
          <el-statistic title="可用资金" :value="dashboardData.account.availableFunds" precision="2" prefix="¥">
            <template #prefix>
              <el-icon color="#67C23A"><Money /></el-icon>
            </template>
          </el-statistic>
        </el-col>
        <el-col :span="6">
          <el-statistic title="保证金占用" :value="dashboardData.account.marginUsed" precision="2" prefix="¥">
            <template #prefix>
              <el-icon color="#E6A23C"><Lock /></el-icon>
            </template>
          </el-statistic>
        </el-col>
        <el-col :span="6">
          <el-statistic 
            title="浮动盈亏" 
            :value="dashboardData.account.floatingProfitLoss" 
            precision="2" 
            prefix="¥"
            :value-style="{ color: dashboardData.account.floatingProfitLoss > 0 ? '#F56C6C' : dashboardData.account.floatingProfitLoss < 0 ? '#67C23A' : '#000000' }"
          >
            <template #prefix>
              <el-icon :color="dashboardData.account.floatingProfitLoss > 0 ? '#F56C6C' : dashboardData.account.floatingProfitLoss < 0 ? '#67C23A' : '#000000'">
                <TrendCharts />
              </el-icon>
            </template>
          </el-statistic>
        </el-col>
      </el-row>
    </el-card>

    <!-- 2. 今日表现 & 策略运行状态 -->
    <el-row :gutter="20" style="margin-bottom: 20px;">
      <el-col :span="12">
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
                precision="2" 
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
                precision="2" 
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
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span>策略运行状态</span>
            </div>
          </template>
          <el-row :gutter="20">
            <el-col :span="8">
              <el-statistic title="运行中" :value="dashboardData.strategyStatus.running">
                <template #prefix>
                  <el-icon color="#67C23A"><VideoPlay /></el-icon>
                </template>
              </el-statistic>
            </el-col>
            <el-col :span="8">
              <el-statistic title="已停止" :value="dashboardData.strategyStatus.stopped">
                <template #prefix>
                  <el-icon color="#909399"><VideoPause /></el-icon>
                </template>
              </el-statistic>
            </el-col>
            <el-col :span="8">
              <el-statistic title="异常" :value="dashboardData.strategyStatus.error">
                <template #prefix>
                  <el-icon color="#F56C6C"><Warning /></el-icon>
                </template>
              </el-statistic>
            </el-col>
          </el-row>
        </el-card>
      </el-col>
    </el-row>

    <!-- 3. 系统监控 & 持仓概览 -->
    <el-row :gutter="20" style="margin-bottom: 20px;">
      <el-col :span="12">
        <el-card shadow="hover">
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
      </el-col>
      <el-col :span="12">
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

    <!-- 4. 关键指标图表 -->
    <el-card shadow="hover">
      <template #header>
        <div class="card-header">
          <span>关键指标图表</span>
        </div>
      </template>
      <el-row :gutter="20">
        <el-col :span="8">
          <div class="chart-placeholder">
            <el-icon size="60" color="#909399"><DataLine /></el-icon>
            <div style="margin-top: 10px; color: #909399;">资产曲线图表（待开发）</div>
          </div>
        </el-col>
        <el-col :span="8">
          <div class="chart-placeholder">
            <el-icon size="60" color="#909399"><DataAnalysis /></el-icon>
            <div style="margin-top: 10px; color: #909399;">每日盈亏图表（待开发）</div>
          </div>
        </el-col>
        <el-col :span="8">
          <div class="chart-placeholder">
            <el-icon size="60" color="#909399"><TrendCharts /></el-icon>
            <div style="margin-top: 10px; color: #909399;">夏普比率图表（待开发）</div>
          </div>
        </el-col>
      </el-row>
    </el-card>
  </div>
</template>

<script setup>
import { reactive, computed, onMounted, onUnmounted } from 'vue'
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
  DataAnalysis
} from '@element-plus/icons-vue'
import { dashboardData as dashboardDataImport } from '@/mock'
import { useSystemMonitor } from '@/composables'
import { useTradingAccountStore } from '@/stores/tradingAccount'

// 使用导入的仪表盘数据初始化
const dashboardData = reactive(dashboardDataImport)

// 系统监控数据
const {
  systemInfo,
  startMonitoring,
  stopMonitoring
} = useSystemMonitor()

// 资金账户Store
const tradingAccountStore = useTradingAccountStore()

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

// 组件挂载时启动监控
onMounted(() => {
  startMonitoring()
})

// 组件卸载时停止监控
onUnmounted(() => {
  stopMonitoring()
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.chart-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 200px;
  background-color: #f5f7fa;
  border-radius: 4px;
  text-align: center;
}
</style>

