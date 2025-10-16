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

export const useStrategyStore = defineStore('strategy', () => {
  // ========== 状态 ==========
  const strategies = ref({})
  const strategyStatus = ref({})
  const wsConnection = ref(null)
  const messages = ref([])
  const isLoading = ref(false)
  
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
          displayTime: new Date().toLocaleTimeString('zh-CN')
        }
        
        messages.value.push(enrichedMessage)
        
        // 限制消息历史长度（保留最近1000条）
        if (messages.value.length > 1000) {
          messages.value = messages.value.slice(-1000)
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
        ElMessage.error('WebSocket连接错误，实时消息可能无法接收')
      },
      // onClose
      (event) => {
        console.log('WebSocket连接已关闭，尝试重连...')
        wsConnection.value = null
        
        // 非正常关闭（非1000状态码），尝试重连
        if (event.code !== 1000) {
          setTimeout(() => {
            console.log('尝试重新连接WebSocket...')
            connectWebSocket()
          }, 3000)
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
  
  function clearMessages() {
    messages.value = []
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
    clearMessages
  }
})

