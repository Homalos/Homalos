import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { 
  getStrategies, 
  getStrategyStatus, 
  startStrategy, 
  stopStrategy,
  reloadStrategy,
  enableStrategy,
  disableStrategy,
  createStrategyWebSocket
} from '@/api/strategy'
import { ElMessage } from 'element-plus'

// 日志持久化常量
const STORAGE_KEY = 'homalos_strategy_logs'
const MAX_STORED_LOGS = 500
const LOG_RETENTION_DAYS = 7

// 日志持久化工具函数
function saveLogsToStorage(logs) {
  try {
    const dataToStore = {
      logs: logs,
      timestamp: Date.now()
    }
    localStorage.setItem(STORAGE_KEY, JSON.stringify(dataToStore))
  } catch (error) {
    console.warn('保存日志到localStorage失败:', error)
  }
}

function loadLogsFromStorage() {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (!stored) return []
    
    const data = JSON.parse(stored)
    if (!data.logs || !Array.isArray(data.logs)) return []
    
    // 清理过期日志
    return cleanupExpiredLogs(data.logs)
  } catch (error) {
    console.warn('从localStorage加载日志失败:', error)
    return []
  }
}

function shouldPersistMessage(message) {
  // 重要的消息类型
  const importantTypes = ['status', 'error', 'stopped']
  
  // 重要的关键词
  const importantKeywords = [
    '已启动', '已停止', '启动成功', '停止成功',
    '重载成功', '重载失败', '启动失败', '停止失败',
    'started', 'stopped', 'load_state done', 'save_state result'
  ]
  
  // 检查消息类型
  if (importantTypes.includes(message.type)) {
    return true
  }
  
  // 检查消息内容
  if (message.payload && typeof message.payload === 'string') {
    return importantKeywords.some(keyword => 
      message.payload.includes(keyword)
    )
  }
  
  return false
}

function cleanupExpiredLogs(logs) {
  const now = Date.now()
  const retentionTime = LOG_RETENTION_DAYS * 24 * 60 * 60 * 1000
  
  return logs
    .filter(log => {
      // 保留最近指定天数的日志
      const logTime = new Date(log.timestamp).getTime()
      return (now - logTime) <= retentionTime
    })
    .slice(-MAX_STORED_LOGS) // 保留最近的指定条数
}

export const useStrategyStore = defineStore('strategy', () => {
  // ========== 状态 ==========
  const strategies = ref({})
  const strategyStatus = ref({})
  const wsConnection = ref(null)
  const messages = ref([])
  const isLoading = ref(false)
  const historyLogsLoaded = ref(false) // 标记历史日志是否已加载
  
  // ========== 计算属性 ==========
  const enabledStrategies = computed(() => {
    return Object.entries(strategies.value)
      .filter(([_, config]) => config.enabled)
      .reduce((acc, [sid, config]) => {
        acc[sid] = config
        return acc
      }, {})
  })
  
  const disabledStrategies = computed(() => {
    return Object.entries(strategies.value)
      .filter(([_, config]) => !config.enabled)
      .reduce((acc, [sid, config]) => {
        acc[sid] = config
        return acc
      }, {})
  })
  
  const runningStrategies = computed(() => {
    return Object.entries(strategyStatus.value)
      .filter(([_, status]) => status.alive)
      .reduce((acc, [sid, status]) => {
        acc[sid] = status
        return acc
      }, {})
  })
  
  const stoppedStrategies = computed(() => {
    return Object.entries(strategies.value)
      .filter(([sid, _]) => !strategyStatus.value[sid] || !strategyStatus.value[sid].alive)
      .reduce((acc, [sid, config]) => {
        acc[sid] = config
        return acc
      }, {})
  })
  
  const enabledCount = computed(() => Object.keys(enabledStrategies.value).length)
  const runningCount = computed(() => Object.keys(runningStrategies.value).length)
  const stoppedCount = computed(() => Object.keys(stoppedStrategies.value).length)
  
  // ========== 方法：数据获取 ==========
  async function fetchStrategies() {
    isLoading.value = true
    try {
      const response = await getStrategies()
      // 后端返回 { strategies: {...} }
      strategies.value = response.strategies || response
      console.log('策略列表已更新:', strategies.value)
    } catch (error) {
      console.error('获取策略列表失败:', error)
      ElMessage.error('获取策略列表失败')
    } finally {
      isLoading.value = false
    }
  }
  
  async function fetchStatus() {
    try {
      const response = await getStrategyStatus()
      // 后端返回 { running: {...} }
      strategyStatus.value = response.running
      console.log('策略状态已更新:', strategyStatus.value)
    } catch (error) {
      console.error('获取策略状态失败:', error)
      // 状态获取失败不弹窗，避免频繁打扰用户
    }
  }
  
  // ========== 方法：策略操作 ==========
  async function start(sid) {
    try {
      await startStrategy(sid)
      ElMessage.success(`策略 ${sid} 启动成功`)
      // 延迟刷新状态，给进程启动一点时间
      setTimeout(() => fetchStatus(), 500)
    } catch (error) {
      console.error(`启动策略 ${sid} 失败:`, error)
      ElMessage.error(`启动策略失败: ${error.response?.data?.detail || error.message}`)
    }
  }
  
  async function stop(sid) {
    try {
      await stopStrategy(sid)
      ElMessage.success(`策略 ${sid} 已停止`)
      await fetchStatus()
    } catch (error) {
      console.error(`停止策略 ${sid} 失败:`, error)
      ElMessage.error(`停止策略失败: ${error.response?.data?.detail || error.message}`)
    }
  }
  
  async function reload(sid) {
    try {
      await reloadStrategy(sid)
      ElMessage.success(`策略 ${sid} 重载成功`)
      setTimeout(() => fetchStatus(), 500)
    } catch (error) {
      console.error(`重载策略 ${sid} 失败:`, error)
      ElMessage.error(`重载策略失败: ${error.response?.data?.detail || error.message}`)
    }
  }
  
  async function enable(sid) {
    try {
      await enableStrategy(sid)
      // 立即更新本地状态
      if (strategies.value[sid]) {
        strategies.value[sid].enabled = true
      }
      ElMessage.success(`策略 ${sid} 已启用`)
    } catch (error) {
      console.error(`启用策略 ${sid} 失败:`, error)
      ElMessage.error(`启用策略失败: ${error.response?.data?.detail || error.message}`)
    }
  }
  
  async function disable(sid) {
    try {
      await disableStrategy(sid)
      // 立即更新本地状态
      if (strategies.value[sid]) {
        strategies.value[sid].enabled = false
      }
      ElMessage.success(`策略 ${sid} 已禁用`)
    } catch (error) {
      console.error(`禁用策略 ${sid} 失败:`, error)
      ElMessage.error(`禁用策略失败: ${error.response?.data?.detail || error.message}`)
    }
  }
  
  // ========== 方法：日志管理 ==========
  function loadHistoryLogs() {
    try {
      // 检查是否已经加载过历史日志，避免重复加载
      if (historyLogsLoaded.value) {
        console.log('历史日志已加载，跳过重复加载')
        return
      }
      
      const historyLogs = loadLogsFromStorage()
      if (historyLogs.length > 0) {
        // 标记为历史日志
        const markedLogs = historyLogs.map(log => ({
          ...log,
          isPersisted: true
        }))
        
        // 合并到当前消息列表，按时间排序
        const allLogs = [...markedLogs, ...messages.value]
        messages.value = allLogs.sort((a, b) => 
          new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
        )
        
        console.log(`已加载 ${historyLogs.length} 条历史日志`)
      }
      
      // 标记历史日志已加载
      historyLogsLoaded.value = true
    } catch (error) {
      console.error('加载历史日志失败:', error)
    }
  }
  
  function persistImportantLogs() {
    try {
      // 获取需要持久化的日志（排除已持久化的）
      const logsToSave = messages.value
        .filter(msg => !msg.isPersisted && shouldPersistMessage(msg))
        .map(msg => ({
          ...msg,
          isPersisted: true
        }))
      
      if (logsToSave.length > 0) {
        // 合并现有的持久化日志
        const existingLogs = loadLogsFromStorage()
        const allLogs = [...existingLogs, ...logsToSave]
        const cleanedLogs = cleanupExpiredLogs(allLogs)
        
        saveLogsToStorage(cleanedLogs)
        console.log(`已持久化 ${logsToSave.length} 条重要日志`)
      }
    } catch (error) {
      console.error('持久化日志失败:', error)
    }
  }

  // ========== 方法：WebSocket管理 ==========
  function connectWebSocket() {
    if (wsConnection.value) {
      console.warn('WebSocket已连接，无需重复连接')
      return
    }
    
    wsConnection.value = createStrategyWebSocket(
      // onMessage
      (message) => {
        // 添加时间戳
        const enrichedMessage = {
          ...message,
          timestamp: new Date().toISOString(),
          displayTime: new Date().toLocaleTimeString('zh-CN'),
          isPersisted: false // 标记为实时消息
        }
        
        messages.value.push(enrichedMessage)
        
        // 限制消息历史长度（保留最近1000条）
        if (messages.value.length > 1000) {
          messages.value = messages.value.slice(-1000)
        }
        
        // 异步持久化重要消息
        if (shouldPersistMessage(enrichedMessage)) {
          setTimeout(() => {
            persistImportantLogs()
          }, 100) // 延迟100ms执行，避免频繁写入
        }
        
        // 根据消息类型处理
        switch (message.type) {
          case 'log':
            console.log(`[${message.sid}] ${message.payload}`)
            break
          case 'error':
            console.error(`[${message.sid}] ERROR: ${message.payload}`)
            ElMessage.error(`策略 ${message.sid} 错误: ${message.payload}`)
            break
          case 'status':
            // 状态更新，刷新状态
            console.log(`[${message.sid}] 状态: ${message.payload}`)
            fetchStatus()
            break
          case 'stopped':
            console.log(`[${message.sid}] 已停止`)
            fetchStatus()
            break
          default:
            console.log(`[${message.sid}] ${message.type}:`, message.payload)
        }
      },
      // onError
      (error) => {
        console.error('WebSocket连接错误:', error)
        // 只在第一次错误时提示，避免重连时频繁提示
        if (!wsConnection.value || wsConnection.value.reconnectAttempts === 0) {
          ElMessage.warning('WebSocket连接错误，正在尝试重连...')
        }
      },
      // onClose
      (event) => {
        console.log('WebSocket连接已关闭', event.code, event.reason)
        
        // 非正常关闭且不是手动关闭，显示提示
        if (event.code !== 1000 && event.code !== 1001) {
          // 自动重连会由API层处理
          if (wsConnection.value && wsConnection.value.reconnectAttempts === 1) {
            ElMessage.info('连接已断开，正在自动重连...')
          }
        }
      }
    )
  }
  
  function disconnectWebSocket() {
    if (wsConnection.value) {
      wsConnection.value.close(1000, 'Client disconnect')
      wsConnection.value = null
      console.log('WebSocket已手动断开')
    }
  }
  
  // 获取WebSocket连接状态
  function getWebSocketStatus() {
    if (!wsConnection.value) {
      return { connected: false, status: '未连接', attempts: 0 }
    }
    return {
      connected: wsConnection.value.isConnected,
      status: wsConnection.value.getReadyStateText(),
      attempts: wsConnection.value.reconnectAttempts
    }
  }
  
  function clearMessages() {
    messages.value = []
    historyLogsLoaded.value = false // 重置加载标记
  }
  
  function clearHistoryLogs() {
    try {
      localStorage.removeItem(STORAGE_KEY)
      // 只保留实时消息
      messages.value = messages.value.filter(msg => !msg.isPersisted)
      historyLogsLoaded.value = false // 重置加载标记，允许重新加载
      console.log('历史日志已清空')
    } catch (error) {
      console.error('清空历史日志失败:', error)
    }
  }
  
  // ========== 返回 ==========
  return {
    // 状态
    strategies,
    strategyStatus,
    messages,
    isLoading,
    
    // 计算属性
    enabledStrategies,
    disabledStrategies,
    runningStrategies,
    stoppedStrategies,
    enabledCount,
    runningCount,
    stoppedCount,
    
    // 方法
    fetchStrategies,
    fetchStatus,
    start,
    stop,
    reload,
    enable,
    disable,
    connectWebSocket,
    disconnectWebSocket,
    getWebSocketStatus,
    clearMessages,
    loadHistoryLogs,
    clearHistoryLogs
  }
})

