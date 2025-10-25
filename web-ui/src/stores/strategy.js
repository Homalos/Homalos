import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { 
  getStrategies, 
  getStrategyStatus, 
  startStrategy, 
  stopStrategy,
  // reloadStrategy, // 热重载功能已禁用
  enableStrategy,
  disableStrategy,
  unloadStrategy,
  createStrategyWebSocket,
  scanStrategies,
  getAvailableStrategyFiles,
  scanSingleStrategy
} from '@/api/strategy'
import { getSystemInfo } from '@/api/system'
import { ElMessage } from 'element-plus'

// 日志持久化常量
const STORAGE_KEY = 'homalos_strategy_logs'
const MAX_STORED_LOGS = 500
const LOG_RETENTION_DAYS = 7
const DEBUG_LOGS = true // 临时调试开关

// 生成消息唯一ID
function generateMessageId(message) {
  // 添加更多唯一性因素：时间戳、随机数、消息序号
  const timestamp = message.timestamp || new Date().toISOString()
  const random = Math.random().toString(36).substring(2, 8)
  const sequence = Date.now().toString(36) // 更精确的时间序列
  
  const content = `${message.sid}_${message.type}_${message.payload}_${timestamp}_${random}_${sequence}`
  
  // 使用更长的哈希避免冲突
  let hash = 0
  for (let i = 0; i < content.length; i++) {
    const char = content.charCodeAt(i)
    hash = ((hash << 5) - hash) + char
    hash = hash & hash // 转换为32位整数
  }
  
  return Math.abs(hash).toString(36) + random
}

// 日志持久化工具函数
function saveLogsToStorage(logs) {
  try {
    // 保存所有日志，不进行去重，确保日志完整性
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
  const systemTimezone = ref('Asia/Shanghai') // 系统时区，默认为上海时区
  
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
  
  // ========== 方法：系统配置 ==========
  async function initializeSystemTimezone() {
    try {
      const response = await getSystemInfo()
      if (response && response.timezone) {
        systemTimezone.value = response.timezone
        console.log('系统时区已加载:', systemTimezone.value)
      }
    } catch (error) {
      console.warn('获取系统时区失败，使用默认值 Asia/Shanghai:', error)
      // 保持默认值 'Asia/Shanghai'
    }
  }
  
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

  // 扫描并加载策略
  async function scanAndLoadStrategies() {
    isLoading.value = true
    try {
      const response = await scanStrategies()
      if (response.success) {
        const result = response.data
        ElMessage.success({
          message: `${response.message}`,
          duration: 5000,
          showClose: true
        })
        // 扫描成功后自动刷新策略列表
        await fetchStrategies()
      } else {
        ElMessage.warning(response.message || '扫描策略失败')
      }
    } catch (error) {
      console.error('扫描策略失败:', error)
      ElMessage.error(error.response?.data?.detail || '扫描策略失败')
    } finally {
      isLoading.value = false
    }
  }
  
  async function fetchAvailableFiles() {
    try {
      const response = await getAvailableStrategyFiles()
      if (response.success) {
        return response.files
      } else {
        ElMessage.error(response.message || '获取策略文件列表失败')
        return []
      }
    } catch (error) {
      console.error('获取策略文件列表失败:', error)
      ElMessage.error(error.response?.data?.detail || '获取策略文件列表失败')
      return []
    }
  }
  
  async function loadSingleStrategy(filename) {
    isLoading.value = true
    try {
      const response = await scanSingleStrategy(filename)
      if (response.success) {
        ElMessage.success({
          message: response.message,
          duration: 3000,
          showClose: true
        })
        // 加载成功后自动刷新策略列表
        await fetchStrategies()
        return true
      } else {
        ElMessage.error(response.message || '加载策略失败')
        return false
      }
    } catch (error) {
      console.error('加载策略失败:', error)
      ElMessage.error(error.response?.data?.detail || '加载策略失败')
      return false
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
  
  // 热重载功能已禁用（出于安全考虑）
  // async function reload(sid) { ... }
  // 请使用"停止-修改-启动"流程
  
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
  
  async function unload(sid) {
    try {
      await unloadStrategy(sid)
      // 从本地状态中移除
      delete strategies.value[sid]
      delete strategyStatus.value[sid]
      ElMessage.success(`策略 ${sid} 已卸载`)
      // 刷新状态
      await fetchStatus()
    } catch (error) {
      console.error(`卸载策略 ${sid} 失败:`, error)
      ElMessage.error(`卸载策略失败: ${error.response?.data?.detail || error.message}`)
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
        // 标记为历史日志并确保有ID
        const markedLogs = historyLogs.map(log => ({
          ...log,
          isPersisted: true,
          id: log.id || generateMessageId(log)
        }))
        
        // 合并到当前消息列表并去重
        const allLogs = [...markedLogs, ...messages.value]
        const deduplicatedLogs = deduplicateLogs(allLogs)
        
        // 按时间排序
        messages.value = deduplicatedLogs.sort((a, b) => 
          new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
        )
        
        console.log(`已加载 ${historyLogs.length} 条历史日志，去重后共 ${messages.value.length} 条`)
        console.log('历史日志详情:', historyLogs.map(log => {
          const payload = typeof log.payload === 'string' ? log.payload.substring(0, 30) : String(log.payload).substring(0, 30)
          return `${log.sid}-${log.type}-${payload}`
        }))
        console.log('当前所有日志:', messages.value.map(log => {
          const payload = typeof log.payload === 'string' ? log.payload.substring(0, 30) : String(log.payload).substring(0, 30)
          return `${log.sid}-${log.type}-${payload}`
        }))
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
          isPersisted: true,
          id: msg.id || generateMessageId(msg)
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
        // 过滤心跳消息（ping/pong），不显示在实时日志中
        if (message.type === 'ping' || message.type === 'pong') {
          return
        }
        
        // 添加时间戳和唯一ID
        const enrichedMessage = {
          ...message,
          timestamp: new Date().toISOString(),
          displayTime: new Date().toLocaleString('zh-CN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            hour12: false,
            timeZone: systemTimezone.value
          }),
          isPersisted: false // 标记为实时消息
        }
        
        // 生成唯一ID
        enrichedMessage.id = generateMessageId(enrichedMessage)
        
        // 不进行去重，保留所有日志完整性（用户需要看到所有事件）
        messages.value.push(enrichedMessage)
        
        // 限制消息历史长度（保留最近1000条）
        if (messages.value.length > 1000) {
          messages.value = messages.value.slice(-1000)
        }
        
        // 立即持久化重要消息，延迟持久化普通消息
        if (shouldPersistMessage(enrichedMessage)) {
          // 重要消息立即持久化
          setTimeout(() => {
            persistImportantLogs()
          }, 10) // 减少延迟到10ms
        } else {
          // 普通消息也进行延迟持久化，防止丢失
          setTimeout(() => {
            persistImportantLogs()
          }, 500) // 普通消息延迟500ms
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
  
  // 页面卸载时强制保存所有日志
  function forcePersistAllLogs() {
    try {
      // 获取所有未持久化的消息
      const unsavedLogs = messages.value
        .filter(msg => !msg.isPersisted)
        .map(msg => ({
          ...msg,
          isPersisted: true,
          id: msg.id || generateMessageId(msg)
        }))
      
      if (unsavedLogs.length > 0) {
        // 合并现有的持久化日志
        const existingLogs = loadLogsFromStorage()
        const allLogs = [...existingLogs, ...unsavedLogs]
        const cleanedLogs = cleanupExpiredLogs(allLogs)
        
        // 同步保存，确保在页面卸载前完成
        saveLogsToStorage(cleanedLogs)
        console.log(`页面卸载时强制保存了 ${unsavedLogs.length} 条日志`)
        console.log('保存的日志详情:', unsavedLogs.map(log => {
          const payload = typeof log.payload === 'string' ? log.payload.substring(0, 30) : String(log.payload).substring(0, 30)
          return `${log.sid}-${log.type}-${payload}`
        }))
      }
    } catch (error) {
      console.error('强制保存日志失败:', error)
    }
  }
  
  // ========== 返回 ==========
  return {
    // 状态
    strategies,
    strategyStatus,
    messages,
    isLoading,
    systemTimezone,
    
    // 计算属性
    enabledStrategies,
    disabledStrategies,
    runningStrategies,
    stoppedStrategies,
    enabledCount,
    runningCount,
    stoppedCount,
    
    // 方法
    initializeSystemTimezone,
    fetchStrategies,
    scanAndLoadStrategies,
    fetchAvailableFiles,
    loadSingleStrategy,
    fetchStatus,
    start,
    stop,
    // reload, // 热重载功能已禁用
    enable,
    disable,
    unload,
    connectWebSocket,
    disconnectWebSocket,
    getWebSocketStatus,
    clearMessages,
    loadHistoryLogs,
    clearHistoryLogs,
    forcePersistAllLogs
  }
})

