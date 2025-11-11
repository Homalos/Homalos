<template>
  <!-- 策略管理主面板 -->
  <el-card shadow="hover">
    <template #header>
      <div class="card-header">
        <div class="header-left">
          <span class="header-title">策略管理</span>
          <WebSocketStatus />
        </div>
        <div class="header-right">
          <el-button type="success" size="small" @click="handleScanStrategies">
            <el-icon><FolderOpened /></el-icon>
            加载全部
          </el-button>
          <el-button type="primary" size="small" @click="handleShowFileSelectDialog">
            <el-icon><DocumentAdd /></el-icon>
            加载单个
          </el-button>
          <el-button type="primary" size="small" @click="handleRefresh">
            <el-icon><Refresh /></el-icon>
            刷新
          </el-button>
        </div>
      </div>
    </template>
    
    <!-- 核心状态横幅 -->
    <el-alert
      v-if="coreStatus.status !== 'running'"
      title="交易核心未运行"
      type="warning"
      :closable="false"
      style="margin-bottom: 20px;"
    >
      <template #default>
        <div style="display: flex; align-items: center; justify-content: space-between;">
          <span>策略将无法接收行情数据和执行交易，请先启动交易核心。</span>
          <el-button type="primary" size="small" @click="gotoConsole">
            前往控制台
          </el-button>
        </div>
      </template>
    </el-alert>

    <el-alert
      v-else
      title="交易核心运行中"
      type="success"
      :closable="false"
      style="margin-bottom: 20px;"
    >
      <template #default>
        <el-space>
          <el-tag :type="coreStatus.gateway.md_login ? 'success' : 'warning'" size="small">
            行情: {{ coreStatus.gateway.md_login ? '✓' : '✗' }}
          </el-tag>
          <el-tag :type="coreStatus.gateway.td_login ? 'success' : 'warning'" size="small">
            交易: {{ coreStatus.gateway.td_login ? '✓' : '✗' }}
          </el-tag>
          <el-tag :type="coreStatus.gateway.td_confirm ? 'success' : 'warning'" size="small">
            结算: {{ coreStatus.gateway.td_confirm ? '✓' : '✗' }}
          </el-tag>
          <el-tag :type="coreStatus.gateway.instruments_loaded ? 'success' : 'warning'" size="small">
            合约: {{ coreStatus.gateway.instruments_loaded ? '✓' : '✗' }}
          </el-tag>
          <span style="color: #67C23A;">运行时长: {{ coreStatus.runningTime }}</span>
        </el-space>
      </template>
    </el-alert>
    
    <!-- 策略统计 -->
    <el-row :gutter="20" style="margin-bottom: 20px;">
      <el-col :span="8">
        <el-statistic title="已注册策略" :value="Object.keys(strategyStore.strategies).length">
          <template #prefix>
            <el-icon color="#409eff"><DataAnalysis /></el-icon>
          </template>
        </el-statistic>
      </el-col>
      <el-col :span="8">
        <el-statistic title="运行中" :value="strategyStore.runningCount">
          <template #prefix>
            <el-icon color="#67C23A"><SuccessFilled /></el-icon>
          </template>
        </el-statistic>
      </el-col>
      <el-col :span="8">
        <el-statistic title="已停止" :value="strategyStore.stoppedCount">
          <template #prefix>
            <el-icon color="#909399"><Setting /></el-icon>
          </template>
        </el-statistic>
      </el-col>
    </el-row>
    
    <!-- 策略列表 -->
    <el-table 
      :data="strategyList" 
      style="width: 100%"
      v-loading="strategyStore.isLoading"
    >
      <el-table-column label="策略ID" width="200">
        <template #default="scope">
          {{ getShortStrategyId(scope.row.sid) }}
        </template>
      </el-table-column>
      <el-table-column label="策略名称" width="150">
        <template #default="scope">
          {{ scope.row.name || getStrategyName(scope.row.sid) || scope.row.class }}
        </template>
      </el-table-column>
      <el-table-column label="浮动盈亏" width="120" align="right">
        <template #default="scope">
          <span :style="getPnlStyle(getStrategyPnl(scope.row.sid))">
            {{ formatPnl(getStrategyPnl(scope.row.sid)) }}
          </span>
        </template>
      </el-table-column>
      <el-table-column label="交易次数" width="100" align="center">
        <template #default="scope">
          {{ getStrategyTradeCount(scope.row.sid) || 0 }}
        </template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="scope">
          <el-tag :type="getStrategyStatus(scope.row.sid) === '运行中' ? 'success' : 'info'">
            {{ getStrategyStatus(scope.row.sid) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="启动时间" width="180">
        <template #default="scope">
          {{ formatStartTime(getStrategyStartTime(scope.row.sid)) }}
        </template>
      </el-table-column>
      <el-table-column label="启用" width="80">
        <template #default="scope">
          <el-switch
            :model-value="scope.row.enabled"
            @change="handleToggleEnabled(scope.row.sid, $event)"
          />
        </template>
      </el-table-column>
      <el-table-column label="操作" width="280" fixed="right">
        <template #default="scope">
          <!-- 已停止策略的操作：启动、卸载、详情 -->
          <template v-if="getStrategyStatus(scope.row.sid) === '已停止'">
            <el-button
              size="small"
              type="success"
              :disabled="!scope.row.enabled"
              @click="handleStartStrategy(scope.row.sid)"
            >
              启动
            </el-button>
            <el-button
              size="small"
              type="danger"
              @click="handleUnloadStrategy(scope.row.sid)"
            >
              卸载
            </el-button>
          </template>
          
          <!-- 运行中策略的操作：停止、重载、详情 -->
          <template v-if="getStrategyStatus(scope.row.sid) === '运行中'">
            <el-button
              size="small"
              type="warning"
              @click="handleStopStrategy(scope.row.sid)"
            >
              停止
            </el-button>
            <!-- 热重载按钮已移除（功能已禁用） -->
          </template>
          
          <!-- 通用操作：详情 -->
          <el-button 
            size="small" 
            @click="handleShowDetail(scope.row)"
          >
            详情
          </el-button>
        </template>
      </el-table-column>
    </el-table>
  </el-card>

  <!-- 实时日志 -->
  <el-card shadow="hover" style="margin-top: 20px;">
    <template #header>
      <div class="card-header">
        <span>实时日志</span>
          <div>
          <el-select 
            v-model="selectedLogType" 
            placeholder="筛选日志类型" 
            size="small" 
            style="width: 150px; margin-right: 10px;"
            clearable
          >
            <el-option label="全部" value="" />
            <el-option label="日志(log)" value="log" />
            <el-option label="错误(error)" value="error" />
            <el-option label="状态(status)" value="status" />
          </el-select>
          <el-button size="small" @click="strategyStore.clearMessages">清空全部</el-button>
          <el-button size="small" type="warning" @click="handleClearHistory">清空历史</el-button>
        </div>
      </div>
    </template>
    <div class="log-container">
      <el-timeline v-if="filteredMessages.length > 0">
        <el-timeline-item 
          v-for="(msg, index) in filteredMessages.slice(-50)" 
          :key="index"
          :timestamp="msg.displayTime || msg.timestamp"
          placement="top"
        >
          <div class="log-item">
            <el-tag 
              :type="getLogTypeColor(msg.type)" 
              size="small" 
              style="margin-right: 8px;"
            >
              [{{ msg.sid }}]
            </el-tag>
            <el-tag 
              :type="getLogTypeColor(msg.type)" 
              size="small" 
              style="margin-right: 8px;"
            >
              {{ msg.type }}
            </el-tag>
            <el-tag 
              :type="msg.isPersisted ? 'info' : 'success'"
              size="small" 
              style="margin-right: 8px;"
              effect="plain"
            >
              {{ msg.isPersisted ? '历史' : '实时' }}
            </el-tag>
            <span class="log-message">{{ msg.payload }}</span>
            <div v-if="msg.trace" class="log-trace">
              <pre>{{ msg.trace }}</pre>
            </div>
          </div>
        </el-timeline-item>
      </el-timeline>
      <el-empty v-else description="暂无日志记录" />
    </div>
  </el-card>

  <!-- 策略详情抽屉 -->
  <el-drawer
    v-model="detailDrawerVisible"
    :title="`策略详情 - ${currentStrategy?.sid || ''}`"
    size="60%"
    direction="rtl"
  >
    <div v-if="currentStrategy" class="strategy-detail">
      <!-- 基础信息 -->
      <el-card shadow="never" class="detail-section">
        <template #header>
          <span class="section-title">基础信息</span>
        </template>
        <el-descriptions :column="2" border>
          <el-descriptions-item label="策略ID" :span="2">
            <el-tag size="small" type="info">{{ getShortStrategyId(currentStrategy.sid) }}</el-tag>
            <span style="margin-left: 10px; font-size: 12px; color: #909399;">
              完整ID: {{ currentStrategy.sid }}
            </span>
          </el-descriptions-item>
          <el-descriptions-item label="策略名称">{{ currentStrategy.name || '-' }}</el-descriptions-item>
          <el-descriptions-item label="作者">{{ currentStrategy.author || '-' }}</el-descriptions-item>
          <el-descriptions-item label="类名">{{ currentStrategy.class }}</el-descriptions-item>
          <el-descriptions-item label="模块路径" :span="2">{{ currentStrategy.module }}</el-descriptions-item>
          <el-descriptions-item label="文件路径" :span="2">{{ currentStrategy.file }}</el-descriptions-item>
          <el-descriptions-item label="策略描述" :span="2">
            {{ currentStrategy.description || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="订阅合约" :span="2">
            <el-tag 
              v-for="instrument in currentStrategy.instruments" 
              :key="instrument" 
              size="small" 
              style="margin-right: 8px;"
            >
              {{ instrument }}
            </el-tag>
            <span v-if="!currentStrategy.instruments || currentStrategy.instruments.length === 0">-</span>
          </el-descriptions-item>
          <el-descriptions-item label="是否启用" :span="2">
            <el-tag :type="currentStrategy.enabled ? 'success' : 'info'">
              {{ currentStrategy.enabled ? '已启用' : '已禁用' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="参数配置" :span="2">
            <pre>{{ JSON.stringify(currentStrategy.params, null, 2) }}</pre>
          </el-descriptions-item>
        </el-descriptions>
      </el-card>

      <!-- 运行状态 -->
      <el-card shadow="never" class="detail-section" v-if="currentStrategyStatus">
        <template #header>
          <span class="section-title">运行状态</span>
        </template>
        <el-descriptions :column="2" border>
          <el-descriptions-item label="进程ID">{{ currentStrategyStatus.pid || '-' }}</el-descriptions-item>
          <el-descriptions-item label="运行状态">
            <el-tag :type="currentStrategyStatus.alive ? 'success' : 'info'">
              {{ currentStrategyStatus.alive ? '运行中' : '已停止' }}
            </el-tag>
          </el-descriptions-item>
        </el-descriptions>
      </el-card>

      <!-- 占位：持仓/委托/成交信息（待对接交易网关） -->
      <el-card shadow="never" class="detail-section">
        <template #header>
          <span class="section-title">交易信息</span>
        </template>
        <el-alert
          title="提示"
          type="info"
          description="持仓、委托、成交数据需要对接交易网关后才能显示"
          :closable="false"
        />
      </el-card>
    </div>
  </el-drawer>

  <!-- 文件选择对话框 -->
  <el-dialog
    v-model="fileSelectDialogVisible"
    title="选择要加载的策略文件"
    width="600px"
    :close-on-click-modal="false"
  >
    <el-table 
      :data="availableFiles" 
      highlight-current-row
      @current-change="handleFileSelectionChange"
      style="width: 100%"
    >
      <el-table-column type="index" width="50" />
      <el-table-column label="文件名" prop="filename" width="150" />
      <el-table-column label="策略名称" prop="strategy_name" width="150" />
      <el-table-column label="类名" prop="class_name" width="120" />
      <el-table-column label="状态" width="100">
        <template #default="scope">
          <el-tag v-if="scope.row.loaded" type="success" size="small">
            已加载
          </el-tag>
          <el-tag v-else type="info" size="small">
            未加载
          </el-tag>
        </template>
      </el-table-column>
    </el-table>
    
    <template #footer>
      <span class="dialog-footer">
        <el-button @click="fileSelectDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleConfirmLoadSingle">
          确定
        </el-button>
      </span>
    </template>
  </el-dialog>
</template>

<script setup>
import {
  DataAnalysis, SuccessFilled, Setting, Refresh, FolderOpened, DocumentAdd
} from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ref, computed, onMounted, onUnmounted, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useStrategyStore } from '@/stores/strategy'
import { getTradingCoreStatus } from '@/api/tradingCore'
import WebSocketStatus from './WebSocketStatus.vue'

// ========== 初始化 ==========
const strategyStore = useStrategyStore()
const router = useRouter()

// ========== 状态 ==========
const detailDrawerVisible = ref(false)
const currentStrategy = ref(null)
const selectedLogType = ref('')
const fileSelectDialogVisible = ref(false)
const availableFiles = ref([])
const selectedFile = ref('')

// 核心状态
const coreStatus = reactive({
  status: 'stopped',  // stopped | initializing | connecting | running | stopping | error
  runningTime: '-',
  gateway: {
    md_login: false,
    td_login: false,
    td_confirm: false,
    instruments_loaded: false
  }
})

let coreStatusTimer = null

// ========== 计算属性 ==========
const strategyList = computed(() => {
  return Object.entries(strategyStore.strategies).map(([sid, config]) => ({
    sid,
    ...config
  }))
})

const currentStrategyStatus = computed(() => {
  if (!currentStrategy.value) return null
  return strategyStore.strategyStatus[currentStrategy.value.sid]
})

const filteredMessages = computed(() => {
  if (!selectedLogType.value) {
    return strategyStore.messages
  }
  return strategyStore.messages.filter(msg => msg.type === selectedLogType.value)
})

// ========== 工具方法 ==========
function getStrategyStatus(sid) {
  const status = strategyStore.strategyStatus[sid]
  return status && status.alive ? '运行中' : '已停止'
}

function getStrategyPID(sid) {
  const status = strategyStore.strategyStatus[sid]
  return status ? status.pid : null
}

function getShortStrategyId(sid) {
  // 将长ID转换为短ID
  // 例如: src.strategy.strategies.strategy1.Strategy1 -> strategy1.Strategy1
  if (!sid) return '-'
  const parts = sid.split('.')
  if (parts.length >= 2) {
    return parts.slice(-2).join('.')  // 取最后两部分
  }
  return sid
}

function getStrategyName(sid) {
  // 优先从策略注册信息中获取name（扫描时从策略文件中提取）
  const strategyInfo = strategyStore.strategies[sid]
  if (strategyInfo && strategyInfo.name) {
    return strategyInfo.name
  }
  
  // 如果注册信息中没有，则从运行状态中获取
  const status = strategyStore.strategyStatus[sid]
  return status ? status.strategy_name : null
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

function getLogTypeColor(type) {
  const colorMap = {
    log: 'info',
    error: 'danger',
    status: 'warning',
    stopped: 'info'
  }
  return colorMap[type] || 'info'
}

// ========== 事件处理 ==========
async function handleRefresh() {
  await Promise.all([
    strategyStore.fetchStrategies(),
    strategyStore.fetchStatus()
  ])
  ElMessage.success('刷新成功')
}

async function handleScanStrategies() {
  try {
    await strategyStore.scanAndLoadStrategies()
  } catch (error) {
    console.error('扫描策略失败:', error)
  }
}

async function handleShowFileSelectDialog() {
  try {
    availableFiles.value = await strategyStore.fetchAvailableFiles()
    if (availableFiles.value.length === 0) {
      ElMessage.warning('没有可用的策略文件')
      return
    }
    selectedFile.value = ''
    fileSelectDialogVisible.value = true
  } catch (error) {
    console.error('获取策略文件列表失败:', error)
  }
}

async function handleConfirmLoadSingle() {
  if (!selectedFile.value) {
    ElMessage.warning('请选择要加载的策略文件')
    return
  }
  
  const success = await strategyStore.loadSingleStrategy(selectedFile.value)
  if (success) {
    fileSelectDialogVisible.value = false
  }
}

function handleFileSelectionChange(currentRow) {
  if (currentRow) {
    selectedFile.value = currentRow.filename
  }
}

// ========== 核心状态管理 ==========
/**
 * 获取交易核心状态
 */
async function fetchCoreStatus() {
  try {
    const status = await getTradingCoreStatus()
    
    coreStatus.status = status.status || 'stopped'
    coreStatus.runningTime = status.running_time || '-'
    
    if (status.gateway) {
      coreStatus.gateway = {
        md_login: status.gateway.md_login || false,
        td_login: status.gateway.td_login || false,
        td_confirm: status.gateway.td_confirm || false,
        instruments_loaded: status.gateway.instruments_loaded || false
      }
    } else {
      coreStatus.gateway = {
        md_login: false,
        td_login: false,
        td_confirm: false,
        instruments_loaded: false
      }
    }
    
    // 如果核心已停止，停止轮询
    if (status.status === 'stopped' && coreStatusTimer) {
      stopCoreStatusPolling()
    }
  } catch (error) {
    console.error('获取交易核心状态失败:', error)
    coreStatus.status = 'stopped'
    coreStatus.runningTime = '-'
    coreStatus.gateway = {
      md_login: false,
      td_login: false,
      td_confirm: false,
      instruments_loaded: false
    }
  }
}

/**
 * 启动核心状态轮询
 */
function startCoreStatusPolling() {
  if (coreStatusTimer) return
  
  fetchCoreStatus()
  coreStatusTimer = setInterval(fetchCoreStatus, 10000)  // 每10秒刷新
}

/**
 * 停止核心状态轮询
 */
function stopCoreStatusPolling() {
  if (coreStatusTimer) {
    clearInterval(coreStatusTimer)
    coreStatusTimer = null
  }
}

/**
 * 跳转到控制台
 */
function gotoConsole() {
  router.push('/console')
}

/**
 * 启动策略（带核心状态检查）
 */
async function handleStartStrategy(sid) {
  // 1. 检查核心状态
  await fetchCoreStatus()
  
  if (coreStatus.status !== 'running') {
    // 弹窗确认：只提供"前往控制台"选项
    try {
      await ElMessageBox.confirm(
        '交易核心未运行，策略无法启动。请先前往控制台启动交易核心。',
        '无法启动策略',
        {
          confirmButtonText: '前往控制台',
          cancelButtonText: '取消',
          type: 'error',
          distinguishCancelAndClose: true
        }
      )
      // 用户选择前往控制台
      router.push('/console')
      return
    } catch (action) {
      // 用户取消或关闭对话框
      ElMessage.info('已取消启动')
      return
    }
  }
  
  // 2. 检查网关状态
  if (!coreStatus.gateway.md_login || !coreStatus.gateway.td_login) {
    ElMessage.warning('CTP网关未完全连接，策略可能无法正常工作')
  }
  
  // 3. 启动策略
  await strategyStore.start(sid)
}

async function handleStopStrategy(sid) {
  try {
    await ElMessageBox.confirm(
      `确认停止策略 ${sid}？`,
      '停止确认',
      {
        confirmButtonText: '确认',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    await strategyStore.stop(sid)
  } catch {
    ElMessage.info('已取消')
  }
}

// 热重载功能已禁用（出于安全考虑）
// async function handleReloadStrategy(sid) { ... }
// 请使用"停止-修改-启动"流程

async function handleToggleEnabled(sid, enabled) {
  if (enabled) {
    await strategyStore.enable(sid)
  } else {
    await strategyStore.disable(sid)
  }
}

async function handleUnloadStrategy(sid) {
  try {
    await ElMessageBox.confirm(
      `确认卸载策略 ${sid}？\n卸载后策略将从管理表格中移除，需要重新加载才可展示`,
      '卸载确认',
      {
        confirmButtonText: '确认',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    await strategyStore.unload(sid)
  } catch {
    ElMessage.info('已取消')
  }
}

function handleShowDetail(row) {
  currentStrategy.value = row
  detailDrawerVisible.value = true
}

function handleClearHistory() {
  strategyStore.clearHistoryLogs()
  ElMessage.success('历史日志已清空')
}

// ========== 生命周期 ==========
// 定义清理资源（在 setup 同步阶段定义）
let intervalId = null
const handleBeforeUnload = () => {
  strategyStore.forcePersistAllLogs()
}

// 在 setup 同步阶段注册 onUnmounted（必须在任何 await 之前）
onUnmounted(() => {
  if (intervalId) {
    clearInterval(intervalId)
  }
  strategyStore.disconnectWebSocket()
  window.removeEventListener('beforeunload', handleBeforeUnload)
  stopCoreStatusPolling()  // 停止核心状态轮询
})

// 组件挂载时初始化
onMounted(async () => {
  // 初始化系统时区（从后端配置获取）
  await strategyStore.initializeSystemTimezone()
  
  // 加载历史日志
  strategyStore.loadHistoryLogs()
  
  // 加载策略列表和状态
  await Promise.all([
    strategyStore.fetchStrategies(),
    strategyStore.fetchStatus()
  ])
  
  // 连接WebSocket
  strategyStore.connectWebSocket()
  
  // 定时刷新状态（每5秒）
  intervalId = setInterval(() => {
    strategyStore.fetchStatus()
  }, 5000)
  
  // 添加页面卸载监听器
  window.addEventListener('beforeunload', handleBeforeUnload)
  
  // 启动核心状态轮询
  startCoreStatusPolling()
})
</script>

<style scoped>
/* 全局卡片优化 - 与Dashboard/Console风格一致 */
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

/* 卡片header优化 */
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  position: relative;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.header-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  position: relative;
  padding-left: 12px;
}

/* header左侧渐变装饰条 */
.header-title::before {
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

/* 按钮渐变优化 - 与Console一致 */
:deep(.el-button--primary) {
  background: linear-gradient(135deg, #409eff 0%, #2d7bdb 100%) !important;
  border: none !important;
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.35) !important;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
}

:deep(.el-button--primary:hover) {
  background: linear-gradient(135deg, #53a8ff 0%, #409eff 100%) !important;
  transform: translateY(-2px) !important;
  box-shadow: 0 6px 16px rgba(64, 158, 255, 0.45) !important;
}

:deep(.el-button--success) {
  background: linear-gradient(135deg, #67c23a 0%, #4a9e2b 100%) !important;
  border: none !important;
  box-shadow: 0 4px 12px rgba(103, 194, 58, 0.35) !important;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
}

:deep(.el-button--success:hover) {
  background: linear-gradient(135deg, #85ce61 0%, #67c23a 100%) !important;
  transform: translateY(-2px) !important;
  box-shadow: 0 6px 16px rgba(103, 194, 58, 0.45) !important;
}

:deep(.el-button--danger) {
  background: linear-gradient(135deg, #f56c6c 0%, #e13f3f 100%) !important;
  border: none !important;
  box-shadow: 0 4px 12px rgba(245, 108, 108, 0.35) !important;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
}

:deep(.el-button--danger:hover) {
  background: linear-gradient(135deg, #f78989 0%, #f56c6c 100%) !important;
  transform: translateY(-2px) !important;
  box-shadow: 0 6px 16px rgba(245, 108, 108, 0.45) !important;
}

:deep(.el-button--warning) {
  background: linear-gradient(135deg, #e6a23c 0%, #d18b2a 100%) !important;
  border: none !important;
  box-shadow: 0 4px 12px rgba(230, 162, 60, 0.35) !important;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
}

:deep(.el-button--warning:hover) {
  background: linear-gradient(135deg, #ebb563 0%, #e6a23c 100%) !important;
  transform: translateY(-2px) !important;
  box-shadow: 0 6px 16px rgba(230, 162, 60, 0.45) !important;
}

/* Tag美化 */
:deep(.el-tag) {
  border-radius: 6px;
  padding: 6px 12px;
  font-weight: 500;
  border: none;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.08);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

:deep(.el-tag:hover) {
  transform: translateY(-1px);
  box-shadow: 0 3px 6px rgba(0, 0, 0, 0.12);
}

:deep(.el-tag--success) {
  background: linear-gradient(135deg, #67c23a 0%, #5daf34 100%);
  color: #ffffff;
}

:deep(.el-tag--warning) {
  background: linear-gradient(135deg, #e6a23c 0%, #cf9236 100%);
  color: #ffffff;
}

:deep(.el-tag--danger) {
  background: linear-gradient(135deg, #f56c6c 0%, #dd5a5a 100%);
  color: #ffffff;
}

:deep(.el-tag--info) {
  background: linear-gradient(135deg, rgba(144, 147, 153, 0.9) 0%, rgba(144, 147, 153, 0.8) 100%);
  color: #ffffff;
}

/* Alert美化 */
:deep(.el-alert) {
  border-radius: 8px;
  border-left: 4px solid;
}

:deep(.el-alert--warning) {
  border-left-color: #e6a23c;
  background: linear-gradient(135deg, rgba(230, 162, 60, 0.05) 0%, rgba(230, 162, 60, 0.02) 100%);
}

:deep(.el-alert--success) {
  border-left-color: #67c23a;
  background: linear-gradient(135deg, rgba(103, 194, 58, 0.05) 0%, rgba(103, 194, 58, 0.02) 100%);
}

/* 统计组件优化 */
:deep(.el-statistic) {
  text-align: center;
  padding: 16px;
  background: linear-gradient(135deg, rgba(64, 158, 255, 0.03) 0%, rgba(103, 194, 58, 0.03) 100%);
  border-radius: 12px;
  border: 1px solid rgba(64, 158, 255, 0.08);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

:deep(.el-statistic:hover) {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.1);
  border-color: rgba(64, 158, 255, 0.15);
}

:deep(.el-statistic__head) {
  color: #909399;
  font-size: 14px;
  font-weight: 500;
  margin-bottom: 8px;
}

:deep(.el-statistic__content) {
  font-size: 32px;
  font-weight: 700;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

/* 表格优化 */
:deep(.el-table) {
  border-radius: 8px;
  overflow: hidden;
}

:deep(.el-table th.el-table__cell) {
  background: linear-gradient(135deg, #f5f7fa 0%, #f9f9f9 100%);
  color: #303133;
  font-weight: 600;
  border-bottom: 2px solid rgba(64, 158, 255, 0.1);
}

:deep(.el-table tbody tr:hover > td) {
  background: rgba(64, 158, 255, 0.03) !important;
}

/* Switch开关美化 */
:deep(.el-switch.is-checked .el-switch__core) {
  background: linear-gradient(135deg, #67c23a 0%, #5daf34 100%) !important;
  border-color: transparent !important;
}

/* 日志容器优化 */
.log-container {
  max-height: 500px;
  overflow-y: auto;
  padding: 10px;
  background: linear-gradient(135deg, #f5f7fa 0%, #f9f9f9 100%);
  border-radius: 8px;
  border: 1px solid rgba(64, 158, 255, 0.05);
}

/* 自定义滚动条 */
.log-container::-webkit-scrollbar {
  width: 8px;
}

.log-container::-webkit-scrollbar-track {
  background: rgba(0, 0, 0, 0.02);
  border-radius: 4px;
}

.log-container::-webkit-scrollbar-thumb {
  background: linear-gradient(135deg, #409eff 0%, #67c23a 100%);
  border-radius: 4px;
}

.log-container::-webkit-scrollbar-thumb:hover {
  background: linear-gradient(135deg, #53a8ff 0%, #85ce61 100%);
}

.log-item {
  display: flex;
  align-items: flex-start;
  flex-wrap: wrap;
  padding: 4px 0;
}

.log-message {
  color: #606266;
  font-size: 14px;
  flex: 1;
  line-height: 1.6;
}

.log-trace {
  width: 100%;
  margin-top: 8px;
  padding: 12px;
  background: linear-gradient(135deg, #fff5f5 0%, #ffe8e8 100%);
  border-radius: 6px;
  overflow-x: auto;
  border-left: 3px solid #f56c6c;
}

.log-trace pre {
  margin: 0;
  font-size: 12px;
  color: #e74c3c;
  line-height: 1.5;
}

/* Timeline优化 */
:deep(.el-timeline-item__timestamp) {
  color: #909399;
  font-size: 12px;
  font-weight: 500;
}

/* 策略详情抽屉优化 */
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
  position: relative;
  padding-left: 12px;
}

/* section标题左侧装饰条 */
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

/* Drawer内的卡片优化 */
:deep(.el-drawer .el-card) {
  border-radius: 12px;
  border: 1px solid rgba(64, 158, 255, 0.08);
}

:deep(.el-drawer .el-card.is-never-shadow) {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
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

/* Dialog中的按钮 */
:deep(.el-dialog .el-button--primary) {
  background: linear-gradient(135deg, #409eff 0%, #2d7bdb 100%) !important;
  border: none !important;
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.35) !important;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
}

:deep(.el-dialog .el-button--primary:hover) {
  background: linear-gradient(135deg, #53a8ff 0%, #409eff 100%) !important;
  transform: translateY(-2px) !important;
  box-shadow: 0 6px 16px rgba(64, 158, 255, 0.45) !important;
}

:deep(.el-dialog .el-button--default) {
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.08) 0%, rgba(255, 255, 255, 0.05) 100%);
  border: 1px solid rgba(0, 0, 0, 0.1);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

:deep(.el-dialog .el-button--default:hover) {
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.12) 0%, rgba(255, 255, 255, 0.08) 100%);
  border-color: rgba(64, 158, 255, 0.2);
  transform: translateY(-2px);
}
</style>
