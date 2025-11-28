<template>
  <div class="strategy-detail-page">
    <!-- 页面头部 -->
    <el-card shadow="never" class="page-header">
      <div class="header-content">
        <div class="header-left">
          <div class="page-title">
            <h2>策略详情</h2>
            <span class="strategy-id">{{ getShortStrategyId(strategyId) }}</span>
          </div>
        </div>
        <div class="header-right">
          <el-button 
            type="success" 
            size="default"
            :disabled="!strategy?.enabled || getStrategyStatus(strategyId) === '运行中'"
            @click="handleStartStrategy"
            v-if="getStrategyStatus(strategyId) === '已停止'"
          >
            <el-icon><VideoPlay /></el-icon>
            启动策略
          </el-button>
          <el-button 
            type="warning" 
            size="default"
            @click="handleStopStrategy"
            v-if="getStrategyStatus(strategyId) === '运行中'"
          >
            <el-icon><VideoPause /></el-icon>
            停止策略
          </el-button>
          <el-button 
            type="danger" 
            size="default"
            @click="handleUnloadStrategy"
            v-if="getStrategyStatus(strategyId) === '已停止'"
          >
            <el-icon><Delete /></el-icon>
            卸载策略
          </el-button>
          <el-button 
            type="primary" 
            size="default"
            @click="handleRefresh"
          >
            <el-icon><Refresh /></el-icon>
            刷新
          </el-button>
          <el-button 
            type="primary" 
            :icon="ArrowLeft" 
            @click="goBack"
            class="back-button"
          >
            返回策略管理
          </el-button>
        </div>
      </div>
    </el-card>

    <!-- 策略状态概览 -->
    <el-row :gutter="20" style="margin: 20px 0;">
      <el-col :span="6">
        <el-card shadow="hover" class="status-card">
          <el-statistic title="运行状态">
            <template #prefix>
              <el-icon :color="getStrategyStatus(strategyId) === '运行中' ? '#67C23A' : '#909399'">
                <CircleCheck v-if="getStrategyStatus(strategyId) === '运行中'" />
                <CircleClose v-else />
              </el-icon>
            </template>
            <template #default>
              <el-tag :type="getStrategyStatus(strategyId) === '运行中' ? 'success' : 'info'">
                {{ getStrategyStatus(strategyId) }}
              </el-tag>
            </template>
          </el-statistic>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="status-card">
          <el-statistic title="浮动盈亏" :value="getStrategyPnl(strategyId)" :precision="2">
            <template #prefix>
              <el-icon :color="getStrategyPnl(strategyId) > 0 ? '#F56C6C' : getStrategyPnl(strategyId) < 0 ? '#67C23A' : '#909399'">
                <TrendCharts />
              </el-icon>
            </template>
            <template #formatter="{ value }">
              <span :style="getPnlStyle(value)">
                {{ formatPnl(value) }}
              </span>
            </template>
          </el-statistic>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="status-card">
          <el-statistic title="交易次数" :value="getStrategyTradeCount(strategyId)">
            <template #prefix>
              <el-icon color="#409EFF"><DataAnalysis /></el-icon>
            </template>
          </el-statistic>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="status-card">
          <el-statistic title="启动时间">
            <template #prefix>
              <el-icon color="#E6A23C"><Clock /></el-icon>
            </template>
            <template #default>
              <span>{{ formatStartTime(getStrategyStartTime(strategyId)) }}</span>
            </template>
          </el-statistic>
        </el-card>
      </el-col>
    </el-row>

    <!-- 详细信息 -->
    <el-card shadow="hover" class="detail-section">
      <template #header>
        <span class="section-title">基础信息</span>
      </template>
      <el-descriptions :column="1" border v-if="strategy">
        <el-descriptions-item label="策略UUID" :span="1">
          <el-tag size="small" type="success">{{ strategy.uuid || '-' }}</el-tag>
          <el-button 
            v-if="strategy.uuid"
            type="text" 
            size="small" 
            @click="copyUuid"
            style="margin-left: 8px;"
          >
            复制
          </el-button>
        </el-descriptions-item>
        <el-descriptions-item label="策略名称">{{ strategy.name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="作者">{{ strategy.author || '-' }}</el-descriptions-item>
        <el-descriptions-item label="文件路径">{{ strategy.file }}</el-descriptions-item>
        <el-descriptions-item label="策略描述">
          {{ strategy.description || '-' }}
        </el-descriptions-item>
      </el-descriptions>
      <el-skeleton v-else :rows="8" animated />
    </el-card>

    <!-- 持仓卡片 -->
    <el-card shadow="hover" class="detail-section" style="margin-top: 20px;">
      <template #header>
        <span class="section-title">持仓</span>
      </template>
      <el-table :data="displayPositions" stripe border>
        <el-table-column prop="instrument" label="合约" width="80" />
        <el-table-column prop="direction" label="多空" width="80" align="center">
          <template #default="{ row }">
            <span 
              v-if="row.direction === '多'"
              class="direction-tag direction-long"
            >
              {{ row.direction }}
            </span>
            <span 
              v-else
              class="direction-tag direction-short"
            >
              {{ row.direction }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="可用/总仓" width="120" align="center">
          <template #default="{ row }">
            {{ row.available }}/{{ row.total }}
          </template>
        </el-table-column>
        <el-table-column prop="open_price" label="开仓均价" width="100" align="right" />
        <el-table-column prop="last_price" label="最新价" width="100" align="right" />
        <el-table-column prop="pnl_per_lot" label="逐笔盈亏" width="100" align="right">
          <template #default="{ row }">
            <span :style="row.pnl_per_lot > 0 ? { color: '#f56c6c' } : row.pnl_per_lot < 0 ? { color: '#67c23a' } : {}">
              {{ row.pnl_per_lot }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="profit_price" label="盈利价差" width="100" align="right" />
        <el-table-column prop="pnl_ratio" label="浮盈比例" width="100" align="right">
          <template #default="{ row }">
            {{ (row.pnl_ratio * 100).toFixed(2) }}%
          </template>
        </el-table-column>
        <el-table-column prop="margin" label="保证金" width="100" align="right" />
        <el-table-column prop="market_value" label="市值" width="100" align="right" />
        <el-table-column prop="pnl_mark" label="盯市盈亏" width="100" align="right">
          <template #default="{ row }">
            <span :style="row.pnl_mark > 0 ? { color: '#f56c6c' } : row.pnl_mark < 0 ? { color: '#67c23a' } : {}">
              {{ row.pnl_mark }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="stop_profit" label="止盈价" width="100" align="right" />
        <el-table-column prop="stop_loss" label="止损价" width="100" align="right" />
        <el-table-column label="操作" width="280" fixed="right" align="center">
          <template #default="{ row }">
            <div style="display: flex; gap: 6px; justify-content: center; flex-wrap: wrap;">
              <el-button 
                type="danger" 
                size="small"
                @click="handleClosePosition(row)"
              >
                一键平仓
              </el-button>
              <el-button 
                type="warning" 
                size="small"
                @click="handlePartialClose(row)"
              >
                部分平仓
              </el-button>
              <el-button 
                type="primary" 
                size="small"
                @click="handleReversePosition(row)"
              >
                反手开仓
              </el-button>
            </div>
          </template>
        </el-table-column>
        <template #empty>
          <div class="table-empty-container">
            <el-empty description="暂无持仓" />
          </div>
        </template>
      </el-table>
    </el-card>

    <!-- 成交卡片 -->
    <el-card shadow="hover" class="detail-section" style="margin-top: 20px;">
      <template #header>
        <span class="section-title">成交</span>
      </template>
      <el-table :data="trades" stripe border :default-sort="{ prop: 'trade_time', order: 'descending' }">
        <el-table-column prop="symbol" label="合约" width="80" />
        <el-table-column prop="direction" label="多空" width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="row.direction === 'LONG' ? 'danger' : 'success'">
              {{ row.direction === 'LONG' ? '多' : '空' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="offset_type" label="开平" width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="row.offset_type === 'OPEN' ? 'primary' : 'warning'">
              {{ row.offset_type === 'OPEN' ? '开' : '平' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="trade_price" label="成交价" width="100" align="right" />
        <el-table-column prop="trade_volume" label="成交量" width="100" align="center" />
        <el-table-column prop="pnl" label="平仓盈亏" width="100" align="right">
          <template #default="{ row }">
            <span :style="row.pnl > 0 ? { color: '#f56c6c' } : row.pnl < 0 ? { color: '#67c23a' } : {}">
              {{ row.pnl }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="commission" label="手续费" width="100" align="right" />
        <el-table-column prop="order_id" label="订单编号" width="150" />
        <el-table-column prop="trade_time" label="时间" width="180" sortable align="center">
          <template #default="{ row }">
            {{ formatTradeTime(row.trade_time) }}
          </template>
        </el-table-column>
        <template #empty>
          <div class="table-empty-container">
            <el-empty description="暂无成交记录" />
          </div>
        </template>
      </el-table>
    </el-card>

    <!-- 策略日志 -->
    <el-card shadow="hover" class="detail-section" style="margin-top: 20px;">
      <template #header>
        <div class="log-header">
          <span class="section-title">策略日志</span>
          <div class="log-controls">
            <!-- Trace ID 过滤 -->
            <el-select 
              v-if="availableTraceIds.length > 0"
              v-model="selectedTraceId"
              placeholder="按 Trace ID 过滤"
              size="small"
              clearable
              style="width: 200px; margin-right: 8px;"
              @change="loadLogs"
            >
              <el-option 
                v-for="id in availableTraceIds" 
                :key="id"
                :label="id.substring(0, 8) + '...'"
                :value="id"
              />
            </el-select>
            
            <!-- Context 过滤 -->
            <el-select 
              v-if="availableContexts.length > 0"
              v-model="selectedContext"
              placeholder="按 Context 过滤"
              size="small"
              clearable
              style="width: 150px; margin-right: 8px;"
              @change="loadLogs"
            >
              <el-option 
                v-for="ctx in availableContexts" 
                :key="ctx"
                :label="ctx"
                :value="ctx"
              />
            </el-select>
            
            <!-- 刷新按钮 -->
            <el-button 
              type="primary" 
              size="small"
              @click="loadLogs"
              :loading="logsLoading"
            >
              <el-icon><Refresh /></el-icon>
              刷新日志
            </el-button>
          </div>
        </div>
      </template>
      
      <div v-if="strategyLogs.length > 0" class="logs-container">
        <div class="logs-info">
          <span>共 {{ strategyLogs.length }} 条日志</span>
          <el-button 
            type="text" 
            size="small"
            @click="clearLogs"
          >
            清空
          </el-button>
        </div>
        <div class="logs-list">
          <div 
            v-for="(log, index) in strategyLogs" 
            :key="index"
            class="log-item"
            :class="getLogClass(log)"
          >
            <div class="log-header-info" v-if="log.timestamp || log.level || log.trace_id">
              <span v-if="log.timestamp" class="log-timestamp">{{ log.timestamp }}</span>
              <span v-if="log.level" class="log-level" :class="`level-${log.level.toLowerCase()}`">{{ log.level }}</span>
              <span v-if="log.trace_id" class="log-trace-id" :title="log.trace_id">{{ log.trace_id.substring(0, 8) }}</span>
              <span v-if="log.context" class="log-context">[{{ log.context }}]</span>
            </div>
            <div class="log-content">{{ log.content || log.message }}</div>
          </div>
        </div>
      </div>
      <el-empty v-else description="暂无日志" />
    </el-card>
  </div>
</template>

<script setup>
import {
  ArrowLeft, VideoPlay, VideoPause, Delete, Refresh,
  CircleCheck, CircleClose, TrendCharts, DataAnalysis, Clock
} from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useStrategyStore } from '@/stores/strategy'
import { useTradingAccountStore } from '@/stores/tradingAccount'
import { getStrategyLogs } from '@/api/strategy'
import { getStrategyPositions, getStrategyPositionHistory, getStrategyTrades } from '@/api/strategy-position'
import WebSocketClient from '@/utils/websocket'

// ========== 初始化 ==========
const route = useRoute()
const router = useRouter()
const strategyStore = useStrategyStore()
const tradingAccountStore = useTradingAccountStore()

// ========== 状态 ==========
const strategyId = ref(null)
const strategyUuid = ref(null)
const strategy = ref(null)
const strategyLogs = ref([])
const logsLoading = ref(false)
const availableTraceIds = ref([])
const availableContexts = ref([])
const selectedTraceId = ref(null)
const selectedContext = ref(null)

// 数据库持仓数据
const dbPositions = ref([])
const positionsLoading = ref(false)
const useDbPositions = ref(true)  // 是否使用数据库持仓（默认使用）

// 成交记录数据
const trades = ref([])
const tradesLoading = ref(false)

// WebSocket 实时推送
const wsClient = ref(null)
const wsConnected = ref(false)

// 持仓数据 - 支持从数据库或内存获取
const displayPositions = computed(() => {
  const colors = ['#409EFF', '#67C23A', '#E6A23C', '#F56C6C', '#909399']
  
  // 如果使用数据库持仓，优先显示数据库数据
  if (useDbPositions.value && dbPositions.value && dbPositions.value.length > 0) {
    return dbPositions.value.map((pos, index) => {
      return {
        position_id: pos.position_id,
        instrument: pos.symbol,
        direction: pos.direction === 'LONG' ? '多' : '空',
        available: pos.volume || 0,
        total: pos.volume || 0,
        open_price: pos.avg_price || 0,
        last_price: pos.last_price || 0,
        pnl_per_lot: pos.position_pnl || 0,
        profit_price: 0,
        pnl_ratio: 0,
        margin: 0,
        market_value: (pos.volume || 0) * (pos.last_price || 0),
        pnl_mark: pos.position_pnl || 0,
        stop_profit: 0,
        stop_loss: 0,
        is_closed: pos.is_closed,
        color: colors[index % colors.length]
      }
    })
  }
  
  // 否则显示策略维护的内存持仓
  if (!strategy.value || !strategy.value.positions) {
    return []
  }
  
  const strategyPositions = strategy.value.positions || []
  
  return strategyPositions.map((pos, index) => {
    const direction = typeof pos.direction === 'string' ? pos.direction : 
                     (pos.direction === 1 ? '多' : pos.direction === -1 ? '空' : '多')
    
    return {
      instrument: pos.instrument_id,
      direction: direction,
      available: pos.volume || 0,
      total: pos.volume || 0,
      open_price: pos.avg_price || pos.price || 0,
      last_price: pos.last_price || pos.price || 0,
      pnl_per_lot: pos.pnl || 0,
      profit_price: 0,
      pnl_ratio: pos.pnl_ratio || 0,
      margin: 0,
      market_value: (pos.volume || 0) * (pos.last_price || pos.price || 0),
      pnl_mark: pos.pnl || 0,
      stop_profit: pos.stop_profit || 0,
      stop_loss: pos.stop_loss || 0,
      color: colors[index % colors.length]
    }
  })
})

// UUID格式正则表达式
const UUID_REGEX = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i

// 自动识别id参数是UUID还是sid
function identifyIdType(id) {
  if (!id) return { type: null, value: null }
  
  // 检查是否为UUID格式
  if (UUID_REGEX.test(id)) {
    return { type: 'uuid', value: id }
  }
  
  // 否则视为sid
  return { type: 'sid', value: id }
}

// 初始化时识别路由参数
const idInfo = identifyIdType(route.params.id)
if (idInfo.type === 'uuid') {
  strategyUuid.value = idInfo.value
} else if (idInfo.type === 'sid') {
  strategyId.value = idInfo.value
}

// ========== 计算属性 ==========
const currentStrategyStatus = computed(() => {
  if (!strategyId.value) return null
  return strategyStore.strategyStatus[strategyId.value]
})

// ========== 工具方法 ==========
function getStrategyStatus(sid) {
  const status = strategyStore.strategyStatus[sid]
  return status && status.alive ? '运行中' : '已停止'
}

function getShortStrategyId(sid) {
  if (!sid) return '-'
  const parts = sid.split('.')
  if (parts.length >= 2) {
    return parts.slice(-2).join('.')
  }
  return sid
}

function getStrategyPnl(sid) {
  const status = strategyStore.strategyStatus[sid]
  return status ? status.pnl : 0
}

function getStrategyTradeCount(sid) {
  const status = strategyStore.strategyStatus[sid]
  return status ? status.trade_count : 0
}

function getStrategyStartTime(sid) {
  const status = strategyStore.strategyStatus[sid]
  return status ? status.start_time : null
}

function formatPnl(pnl) {
  if (pnl === 0) return '0.00'
  return pnl > 0 ? `+${pnl.toFixed(2)}` : pnl.toFixed(2)
}

function getPnlStyle(pnl) {
  if (pnl > 0) return { color: '#f56c6c', fontWeight: 'bold' }  // 红色表示盈利
  if (pnl < 0) return { color: '#67c23a', fontWeight: 'bold' }  // 绿色表示亏损
  return { color: '#303133' }  // 黑色表示不亏不赚
}

function formatStartTime(timestamp) {
  if (!timestamp) return '-'
  const date = new Date(timestamp * 1000)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

function getRunningDuration(startTime) {
  if (!startTime) return '-'
  const start = new Date(startTime * 1000)
  const now = new Date()
  const duration = now - start
  
  const hours = Math.floor(duration / (1000 * 60 * 60))
  const minutes = Math.floor((duration % (1000 * 60 * 60)) / (1000 * 60))
  const seconds = Math.floor((duration % (1000 * 60)) / 1000)
  
  return `${hours}时${minutes}分${seconds}秒`
}

// ========== 持仓相关方法 ==========
async function loadDbPositions() {
  if (!strategyId.value) return
  
  positionsLoading.value = true
  try {
    const response = await getStrategyPositions(strategyId.value)
    // 后端返回 StrategyPositionListResponse 格式：{ total, positions }
    if (response && response.positions !== undefined) {
      dbPositions.value = response.positions || []
      useDbPositions.value = true
      if (dbPositions.value.length > 0) {
        ElMessage.success(`持仓数据已加载，共 ${dbPositions.value.length} 个持仓`)
      }
    } else {
      console.warn('持仓数据格式错误:', response)
      ElMessage.warning('加载持仓数据失败')
      useDbPositions.value = false
    }
  } catch (error) {
    console.error('加载持仓数据失败:', error)
    ElMessage.error('加载持仓数据失败: ' + (error.message || '未知错误'))
    useDbPositions.value = false
  } finally {
    positionsLoading.value = false
  }
}

// ========== 成交相关方法 ==========
async function loadTrades() {
  if (!strategyId.value) return
  
  tradesLoading.value = true
  try {
    const response = await getStrategyTrades(strategyId.value)
    // 后端返回 StrategyTradeListResponse 格式：{ total, trades }
    if (response && response.trades !== undefined) {
      trades.value = response.trades || []
      if (trades.value.length > 0) {
        ElMessage.success(`成交记录已加载，共 ${trades.value.length} 条`)
      }
    } else {
      console.warn('成交数据格式错误:', response)
      ElMessage.warning('加载成交数据失败')
    }
  } catch (error) {
    console.error('加载成交数据失败:', error)
    ElMessage.error('加载成交数据失败: ' + (error.message || '未知错误'))
  } finally {
    tradesLoading.value = false
  }
}

function formatTradeTime(timestamp) {
  if (!timestamp) return '-'
  
  try {
    // 处理 ISO 格式的时间戳
    const date = new Date(timestamp)
    if (isNaN(date.getTime())) {
      return timestamp
    }
    
    // 格式化为 YYYY-MM-DD HH:mm:ss
    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')
    const hours = String(date.getHours()).padStart(2, '0')
    const minutes = String(date.getMinutes()).padStart(2, '0')
    const seconds = String(date.getSeconds()).padStart(2, '0')
    
    return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`
  } catch (error) {
    console.error('格式化时间失败:', error)
    return timestamp
  }
}

// ========== WebSocket 相关方法 ==========
async function initWebSocket() {
  if (!strategyId.value) return
  
  try {
    // 构建 WebSocket URL
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    const wsUrl = `${protocol}//${host}/ws/positions?strategy_id=${strategyId.value}`
    
    // 创建 WebSocket 客户端
    wsClient.value = new WebSocketClient(wsUrl)
    
    // 监听持仓更新
    wsClient.value.on('position_update', ({ strategy_id, data }) => {
      console.log('[WebSocket] 收到持仓更新:', data)
      
      // 更新本地持仓数据
      if (data && data.symbol) {
        const existingIndex = dbPositions.value.findIndex(
          (pos) => pos.symbol === data.symbol && pos.direction === data.direction
        )
        
        if (existingIndex > -1) {
          // 更新现有持仓
          dbPositions.value[existingIndex] = {
            ...dbPositions.value[existingIndex],
            ...data
          }
        } else {
          // 添加新持仓
          dbPositions.value.push(data)
        }
      }
    })
    
    // 监听心跳响应
    wsClient.value.on('pong', () => {
      console.log('[WebSocket] 心跳响应')
    })
    
    // 连接到服务器
    await wsClient.value.connect()
    wsConnected.value = true
    console.log('[WebSocket] 已连接到持仓推送服务')
  } catch (error) {
    console.error('[WebSocket] 连接失败:', error)
    wsConnected.value = false
  }
}

function closeWebSocket() {
  if (wsClient.value) {
    wsClient.value.disconnect()
    wsClient.value = null
  }
  wsConnected.value = false
}

// ========== 日志相关方法 ==========
function getLogClass(log) {
  if (!log || !log.level) return 'log-default'
  
  // 根据日志级别判断样式
  const level = log.level.toUpperCase()
  if (level === 'ERROR') {
    return 'log-error'
  } else if (level === 'WARNING') {
    return 'log-warning'
  } else if (level === 'INFO') {
    return 'log-info'
  } else if (level === 'DEBUG') {
    return 'log-debug'
  }
  return 'log-default'
}

async function loadLogs() {
  if (!strategyId.value) return
  
  logsLoading.value = true
  try {
    const response = await getStrategyLogs(
      strategyId.value, 
      100, 
      selectedTraceId.value, 
      selectedContext.value
    )
    if (response.code === 200 && response.data) {
      strategyLogs.value = response.data.logs || []
      availableTraceIds.value = response.data.available_trace_ids || []
      availableContexts.value = response.data.available_contexts || []
    } else {
      ElMessage.warning('获取日志失败')
    }
  } catch (error) {
    console.error('获取日志失败:', error)
    ElMessage.error('获取日志失败')
  } finally {
    logsLoading.value = false
  }
}

function clearLogs() {
  strategyLogs.value = []
  selectedTraceId.value = null
  selectedContext.value = null
  ElMessage.success('日志已清空')
}

// ========== 持仓操作 ==========
function handleClosePosition(row) {
  ElMessageBox.confirm(
    `确认平仓 ${row.instrument} ${row.direction}仓 ${row.total}手？`,
    '平仓确认',
    {
      confirmButtonText: '确认',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(() => {
    ElMessage.success('平仓请求已提交')
    // TODO: 调用后端API执行平仓操作
  }).catch(() => {
    ElMessage.info('已取消')
  })
}

function handlePartialClose(row) {
  ElMessageBox.prompt(
    `请输入要平仓的手数（最多 ${row.available} 手）`,
    '部分平仓',
    {
      confirmButtonText: '确认',
      cancelButtonText: '取消',
      inputPattern: /^[0-9]+$/,
      inputErrorMessage: '请输入正整数'
    }
  ).then(({ value }) => {
    const closeAmount = parseInt(value)
    if (closeAmount > row.available) {
      ElMessage.error(`平仓手数不能超过可用手数 ${row.available}`)
      return
    }
    ElMessage.success(`部分平仓请求已提交，平仓 ${closeAmount} 手`)
    // TODO: 调用后端API执行部分平仓操作
  }).catch(() => {
    ElMessage.info('已取消')
  })
}

function handleReversePosition(row) {
  ElMessageBox.prompt(
    `请输入反手开仓的手数`,
    '反手开仓',
    {
      confirmButtonText: '确认',
      cancelButtonText: '取消',
      inputPattern: /^[0-9]+$/,
      inputErrorMessage: '请输入正整数'
    }
  ).then(({ value }) => {
    const reverseAmount = parseInt(value)
    ElMessage.success(`反手开仓请求已提交，开仓 ${reverseAmount} 手`)
    // TODO: 调用后端API执行反手开仓操作
  }).catch(() => {
    ElMessage.info('已取消')
  })
}

// ========== 事件处理 ==========
function goBack() {
  router.push('/strategy')
}

function copyUuid() {
  if (!strategy.value?.uuid) return
  
  navigator.clipboard.writeText(strategy.value.uuid).then(() => {
    ElMessage.success('UUID已复制到剪贴板')
  }).catch(() => {
    ElMessage.error('复制失败')
  })
}

async function handleRefresh() {
  await Promise.all([
    strategyStore.fetchStrategies(),
    strategyStore.fetchStatus()
  ])
  loadStrategyData()
  // 同时刷新持仓和成交数据
  await Promise.all([
    loadDbPositions(),
    loadTrades()
  ])
  ElMessage.success('刷新成功')
}

async function handleStartStrategy() {
  try {
    await strategyStore.start(strategyId.value)
  } catch (error) {
    console.error('启动策略失败:', error)
  }
}

async function handleStopStrategy() {
  try {
    await ElMessageBox.confirm(
      `确认停止策略 ${strategyId.value}？`,
      '停止确认',
      {
        confirmButtonText: '确认',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    await strategyStore.stop(strategyId.value)
  } catch (error) {
    if (error !== 'cancel') {
      console.error('停止策略失败:', error)
    } else {
      ElMessage.info('已取消')
    }
  }
}

async function handleUnloadStrategy() {
  try {
    await ElMessageBox.confirm(
      `确认卸载策略 ${strategyId.value}？\n卸载后策略将从管理表格中移除，需要重新加载才可展示`,
      '卸载确认',
      {
        confirmButtonText: '确认',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    await strategyStore.unload(strategyId.value)
    // 卸载成功后返回策略管理页面
    router.push('/strategy')
  } catch (error) {
    if (error !== 'cancel') {
      console.error('卸载策略失败:', error)
    } else {
      ElMessage.info('已取消')
    }
  }
}

async function handleToggleEnabled(enabled) {
  try {
    if (enabled) {
      await strategyStore.enable(strategyId.value)
    } else {
      await strategyStore.disable(strategyId.value)
    }
    // 重新加载策略数据
    loadStrategyData()
  } catch (error) {
    console.error('切换策略启用状态失败:', error)
  }
}

// ========== 数据加载 ==========
function loadStrategyData() {
  // 如果是通过UUID访问，需要先找到对应的sid
  if (strategyUuid.value && !strategyId.value) {
    // 遍历所有策略找到匹配的UUID
    for (const [sid, config] of Object.entries(strategyStore.strategies)) {
      if (config.uuid === strategyUuid.value) {
        strategyId.value = sid
        break
      }
    }
    
    if (!strategyId.value) {
      ElMessage.error('策略UUID不存在或未加载')
      router.push('/strategy')
      return
    }
  }
  
  if (!strategyId.value) return
  
  // 从store中获取策略信息
  const strategyConfig = strategyStore.strategies[strategyId.value]
  
  if (!strategyConfig) {
    ElMessage.error('策略不存在或未加载')
    router.push('/strategy')
    return
  }
  
  // 构建完整的策略对象，包含sid
  strategy.value = {
    sid: strategyId.value,
    ...strategyConfig
  }
}

// ========== 生命周期 ==========
onMounted(async () => {
  // 确保策略数据已加载
  if (Object.keys(strategyStore.strategies).length === 0) {
    await Promise.all([
      strategyStore.fetchStrategies(),
      strategyStore.fetchStatus()
    ])
  }
  
  loadStrategyData()
  
  // 自动加载持仓、成交、日志和 WebSocket
  if (strategyId.value) {
    await Promise.all([
      loadDbPositions(),
      loadTrades(),
      loadLogs(),
      initWebSocket()
    ])
  }
})

// 页面卸载时关闭 WebSocket
watch(() => route.params.id, () => {
  closeWebSocket()
}, { immediate: false })

// 组件卸载时关闭 WebSocket
onBeforeUnmount(() => {
  closeWebSocket()
})

// 监听路由参数变化
watch(() => route.params.id, async (newId) => {
  const idInfo = identifyIdType(newId)
  
  if (idInfo.type === 'uuid') {
    strategyUuid.value = idInfo.value
    strategyId.value = null  // 清除SID，让loadStrategyData重新查找
  } else if (idInfo.type === 'sid') {
    strategyId.value = idInfo.value
    strategyUuid.value = null  // 清除UUID
  }
  
  loadStrategyData()
  
  // 加载日志
  if (strategyId.value) {
    await loadLogs()
  }
})
</script>

<style scoped>
/* 页面容器 */
.strategy-detail-page {
  padding: 0;
}

/* 页面头部 */
.page-header {
  margin-bottom: 0;
  border-radius: 12px;
  border: 1px solid rgba(64, 158, 255, 0.08);
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 20px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.back-button {
  background: linear-gradient(135deg, #409eff 0%, #2d7bdb 100%);
  border: none;
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.35);
}

.back-button:hover {
  background: linear-gradient(135deg, #53a8ff 0%, #409eff 100%);
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(64, 158, 255, 0.45);
}

.page-title h2 {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
  color: #303133;
}

.strategy-id {
  font-size: 14px;
  color: #909399;
  font-weight: normal;
}

/* 状态卡片 */
.status-card {
  border-radius: 12px;
  border: 1px solid rgba(64, 158, 255, 0.08);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.status-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 20px rgba(64, 158, 255, 0.12);
}

/* 详情区域 */
.detail-section {
  border-radius: 12px;
  border: 1px solid rgba(64, 158, 255, 0.08);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.detail-section:hover {
  box-shadow: 0 4px 20px rgba(64, 158, 255, 0.12);
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  position: relative;
  padding-left: 12px;
}

.section-title::before {
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

/* 按钮样式优化 */
:deep(.el-button--success) {
  background: linear-gradient(135deg, #67c23a 0%, #4a9e2b 100%);
  border: none;
  box-shadow: 0 4px 12px rgba(103, 194, 58, 0.35);
}

:deep(.el-button--success:hover) {
  background: linear-gradient(135deg, #85ce61 0%, #67c23a 100%);
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(103, 194, 58, 0.45);
}

:deep(.el-button--warning) {
  background: linear-gradient(135deg, #e6a23c 0%, #d18b2a 100%);
  border: none;
  box-shadow: 0 4px 12px rgba(230, 162, 60, 0.35);
}

:deep(.el-button--warning:hover) {
  background: linear-gradient(135deg, #ebb563 0%, #e6a23c 100%);
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(230, 162, 60, 0.45);
}

:deep(.el-button--danger) {
  background: linear-gradient(135deg, #f56c6c 0%, #e13f3f 100%);
  border: none;
  box-shadow: 0 4px 12px rgba(245, 108, 108, 0.35);
}

:deep(.el-button--danger:hover) {
  background: linear-gradient(135deg, #f78989 0%, #f56c6c 100%);
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(245, 108, 108, 0.45);
}

:deep(.el-button--primary) {
  background: linear-gradient(135deg, #409eff 0%, #2d7bdb 100%);
  border: none;
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.35);
}

:deep(.el-button--primary:hover) {
  background: linear-gradient(135deg, #53a8ff 0%, #409eff 100%);
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(64, 158, 255, 0.45);
}

/* Tag样式 */
:deep(.el-tag) {
  border-radius: 6px;
  padding: 6px 12px;
  font-weight: 500;
  border: none;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.08);
}

:deep(.el-tag--success) {
  background: linear-gradient(135deg, #67c23a 0%, #5daf34 100%);
  color: #ffffff;
}

:deep(.el-tag--info) {
  background: linear-gradient(135deg, rgba(144, 147, 153, 0.9) 0%, rgba(144, 147, 153, 0.8) 100%);
  color: #ffffff;
}

/* 方向标签样式 */
.direction-tag {
  display: inline-block;
  padding: 6px 12px;
  border-radius: 6px;
  font-weight: 500;
  font-size: 14px;
}

.direction-long {
  background-color: #fef0f0;
  color: #f56c6c;
  border: 1px solid rgba(245, 108, 108, 0.2);
}

.direction-short {
  background-color: #f0f9f0;
  color: #67c23a;
  border: 1px solid rgba(103, 194, 58, 0.2);
}

/* 表格空状态容器 */
.table-empty-container {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 20px 20px;
  min-height: 100px;
}

/* 统计组件优化 */
:deep(.el-statistic) {
  text-align: center;
  padding: 16px;
}

:deep(.el-statistic__head) {
  color: #909399;
  font-size: 14px;
  font-weight: 500;
  margin-bottom: 8px;
}

:deep(.el-statistic__content) {
  font-size: 28px;
  font-weight: 700;
}

/* Descriptions优化 */
:deep(.el-descriptions__label) {
  font-weight: 600;
  color: #606266;
  background: linear-gradient(135deg, #f5f7fa 0%, #f9f9f9 100%);
}

:deep(.el-descriptions__content) {
  color: #303133;
}

/* Switch开关美化 */
:deep(.el-switch.is-checked .el-switch__core) {
  background: linear-gradient(135deg, #67c23a 0%, #5daf34 100%);
  border-color: transparent;
}

/* 代码样式 */
code {
  background: #f5f7fa;
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 12px;
  color: #e6a23c;
}

/* 日志相关样式 */
.log-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.log-controls {
  display: flex;
  gap: 8px;
  align-items: center;
}

.logs-container {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.logs-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 0;
  border-bottom: 1px solid #ebeef5;
  margin-bottom: 12px;
  font-size: 12px;
  color: #909399;
}

.logs-list {
  flex: 1;
  overflow-y: auto;
  max-height: 400px;
  border: 1px solid #ebeef5;
  border-radius: 4px;
  background: #fafafa;
}

.log-item {
  padding: 8px 12px;
  border-bottom: 1px solid #f0f0f0;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 12px;
  line-height: 1.6;
  word-break: break-all;
  white-space: pre-wrap;
}

.log-item:last-child {
  border-bottom: none;
}

.log-header-info {
  display: flex;
  gap: 8px;
  margin-bottom: 4px;
  font-size: 11px;
  opacity: 0.8;
}

.log-timestamp {
  color: #909399;
  font-weight: 500;
}

.log-level {
  padding: 1px 4px;
  border-radius: 2px;
  font-weight: 600;
  text-transform: uppercase;
}

.log-level.level-error {
  background: #f56c6c;
  color: white;
}

.log-level.level-warning {
  background: #e6a23c;
  color: white;
}

.log-level.level-info {
  background: #409eff;
  color: white;
}

.log-level.level-debug {
  background: #909399;
  color: white;
}

.log-trace-id {
  background: #f5f7fa;
  padding: 1px 4px;
  border-radius: 2px;
  color: #606266;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  cursor: pointer;
}

.log-trace-id:hover {
  background: #e6f7ff;
  color: #409eff;
}

.log-context {
  color: #67c23a;
  font-weight: 600;
}

.log-content {
  display: block;
  color: #303133;
}

/* 日志级别颜色 */
.log-error {
  background: #fef0f0;
  color: #f56c6c;
  border-left: 3px solid #f56c6c;
  padding-left: 9px;
}

.log-warning {
  background: #fdf6ec;
  color: #e6a23c;
  border-left: 3px solid #e6a23c;
  padding-left: 9px;
}

.log-info {
  background: #f0f9ff;
  color: #409eff;
  border-left: 3px solid #409eff;
  padding-left: 9px;
}

.log-debug {
  background: #f5f7fa;
  color: #909399;
  border-left: 3px solid #909399;
  padding-left: 9px;
}

.log-default {
  background: #ffffff;
  color: #606266;
}

/* 日志列表滚动条美化 */
.logs-list::-webkit-scrollbar {
  width: 6px;
}

.logs-list::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 3px;
}

.logs-list::-webkit-scrollbar-thumb {
  background: #c0c4cc;
  border-radius: 3px;
}

.logs-list::-webkit-scrollbar-thumb:hover {
  background: #a8abb2;
}
</style>
