/**
 * 控制台逻辑 Composable
 */
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  startDataCenter,
  stopDataCenter,
  restartDataCenter,
  getDataCenterStatus,
  getDataCenterLogs
} from '@/api/datacenter'
import { getCurrentTime, addLog } from '@/utils'

export function useConsole() {
  // ===== 状态管理 =====
  const consoleData = reactive({
    tradingSystem: {
      status: 'stopped',  // running | stopped
      runningTime: '-',
      pid: null,
      cpu: 0,
      memory: 0
    },
    dataCenter: {
      status: 'stopped',
      runningTime: '-',
      pid: null,
      cpu: 0,
      memory: 0
    }
  })
  
  // 分离日志：量化交易系统和数据中心各自的日志（初始都为空）
  const tradingSystemLogs = ref([])
  const dataCenterLogs = ref([])
  
  const selectedTradingLogLevel = ref('all')
  const selectedDataCenterLogLevel = ref('all')
  
  let statusTimer = null  // 状态轮询定时器
  let logsTimer = null    // 日志轮询定时器
  let lastLogLine = 0     // 记录最后读取的日志行号
  let eventSource = null  // SSE连接对象
  let useSSE = true       // 是否使用SSE（降级标志）

  // ===== 工具函数 =====
  
  /**
   * 从错误对象中提取错误信息
   */
  const extractErrorMessage = (error) => {
    if (error.response?.data) {
      if (typeof error.response.data.detail === 'string') {
        return error.response.data.detail
      } else if (error.response.data.detail) {
        return JSON.stringify(error.response.data.detail)
      } else if (error.response.data.message) {
        return error.response.data.message
      }
    } else if (error.message) {
      return error.message
    }
    return '未知错误'
  }

  // ===== 计算属性 =====
  
  // 量化交易系统日志过滤
  const filteredTradingLogs = computed(() => {
    if (selectedTradingLogLevel.value === 'all') {
      return tradingSystemLogs.value
    }
    return tradingSystemLogs.value.filter(log => log.level === selectedTradingLogLevel.value)
  })
  
  // 数据中心日志过滤
  const filteredDataCenterLogs = computed(() => {
    if (selectedDataCenterLogLevel.value === 'all') {
      return dataCenterLogs.value
    }
    return dataCenterLogs.value.filter(log => log.level === selectedDataCenterLogLevel.value)
  })

  // ===== 方法 =====
  
  /**
   * 添加控制台日志（根据组件类型分配到不同的日志数组）
   */
  const addConsoleLog = (level, category, message, details = {}) => {
    const component = details.component || 'tradingSystem'  // 默认为交易系统
    
    if (component === 'dataCenter') {
      addLog(dataCenterLogs, level, category, message, details, getCurrentTime)
    } else {
      addLog(tradingSystemLogs, level, category, message, details, getCurrentTime)
    }
  }

  /**
   * 启动量化交易系统（暂时保留硬编码）
   */
  const handleStartTradingSystem = () => {
    consoleData.tradingSystem.status = 'running'
    consoleData.tradingSystem.runningTime = '0m'
    
    addConsoleLog(
      'success',
      '系统启动',
      '量化交易系统启动成功',
      { component: 'tradingSystem' }
    )
    
    ElMessage.success('量化交易系统已启动')
  }

  /**
   * 停止量化交易系统（暂时保留硬编码）
   */
  const handleStopTradingSystem = () => {
    consoleData.tradingSystem.status = 'stopped'
    consoleData.tradingSystem.runningTime = '-'
    
    addConsoleLog(
      'warning',
      '系统停止',
      '量化交易系统已停止',
      { component: 'tradingSystem' }
    )
    
    ElMessage.warning('量化交易系统已停止')
  }

  /**
   * 启动数据中心（调用真实API）
   */
  const handleStartDataCenter = async () => {
    try {
      const result = await startDataCenter()
      
      // 确保状态设置为字符串
      consoleData.dataCenter.status = 'running'
      consoleData.dataCenter.pid = result.pid || null
      
      addConsoleLog(
        'success',
        '系统启动',
        '数据中心启动成功',
        { pid: result.pid, component: 'dataCenter' }
      )
      
      ElMessage.success('数据中心已启动')
      
      // 立即刷新一次状态
      await fetchDataCenterStatus()
      
      // 启动状态轮询和日志流（SSE或轮询）
      startStatusPolling()
      startDataCenterLogs()
      
    } catch (error) {
      const errorMsg = extractErrorMessage(error)
      addConsoleLog(
        'error',
        '系统启动',
        `数据中心启动失败: ${errorMsg}`,
        { component: 'dataCenter' }
      )
      ElMessage.error(`数据中心启动失败: ${errorMsg}`)
    }
  }

  /**
   * 停止数据中心（调用真实API）
   */
  const handleStopDataCenter = async (force = false) => {
    // 如果第一个参数是事件对象，则使用默认值 false
    if (typeof force !== 'boolean') {
      force = false
    }
    
    try {
      // 如果是强制停止，先确认
      if (force) {
        await ElMessageBox.confirm(
          '强制停止可能导致数据丢失，确定要强制停止吗？',
          '确认强制停止',
          {
            confirmButtonText: '确定',
            cancelButtonText: '取消',
            type: 'warning'
          }
        )
      }
      
      await stopDataCenter(force)
      
      consoleData.dataCenter.status = 'stopped'
      consoleData.dataCenter.runningTime = '-'
      consoleData.dataCenter.pid = null
      consoleData.dataCenter.cpu = 0
      consoleData.dataCenter.memory = 0
      
      addConsoleLog(
        'warning',
        '系统停止',
        force ? '数据中心已强制停止' : '数据中心已停止',
        { component: 'dataCenter' }
      )
      
      ElMessage.warning('数据中心已停止')
      
      // 停止状态轮询和日志流
      stopStatusPolling()
      stopDataCenterLogs()
      
    } catch (error) {
      if (error === 'cancel') return  // 用户取消
      
      const errorMsg = extractErrorMessage(error)
      addConsoleLog(
        'error',
        '系统停止',
        `数据中心停止失败: ${errorMsg}`,
        { component: 'dataCenter' }
      )
      ElMessage.error(`数据中心停止失败: ${errorMsg}`)
    }
  }

  /**
   * 重启数据中心（调用真实API）
   */
  const handleRestartDataCenter = async () => {
    try {
      await ElMessageBox.confirm(
        '确定要重启数据中心吗？',
        '确认重启',
        {
          confirmButtonText: '确定',
          cancelButtonText: '取消',
          type: 'warning'
        }
      )
      
      await restartDataCenter()
      
      addConsoleLog(
        'success',
        '系统重启',
        '数据中心重启成功',
        { component: 'dataCenter' }
      )
      
      ElMessage.success('数据中心已重启')
      
      // 立即刷新一次状态
      await fetchDataCenterStatus()
      
      // 重启状态轮询和日志轮询
      startStatusPolling()
      startLogsPolling()
      
    } catch (error) {
      if (error === 'cancel') return  // 用户取消
      
      const errorMsg = extractErrorMessage(error)
      addConsoleLog(
        'error',
        '系统重启',
        `数据中心重启失败: ${errorMsg}`,
        { component: 'dataCenter' }
      )
      ElMessage.error(`数据中心重启失败: ${errorMsg}`)
    }
  }

  /**
   * 获取数据中心状态
   */
  const fetchDataCenterStatus = async () => {
    try {
      const status = await getDataCenterStatus()
      
      if (status.running) {
        consoleData.dataCenter.status = 'running'
        consoleData.dataCenter.pid = status.pid
        consoleData.dataCenter.cpu = status.cpu_percent || 0
        consoleData.dataCenter.memory = status.memory_mb || 0
        
        // 计算运行时长
        if (status.create_time) {
          const createTime = new Date(status.create_time)
          const now = new Date()
          const diffMinutes = Math.floor((now - createTime) / 60000)
          if (diffMinutes < 60) {
            consoleData.dataCenter.runningTime = `${diffMinutes}m`
          } else {
            const hours = Math.floor(diffMinutes / 60)
            const minutes = diffMinutes % 60
            consoleData.dataCenter.runningTime = `${hours}h${minutes}m`
          }
        }
      } else {
        consoleData.dataCenter.status = 'stopped'
        consoleData.dataCenter.runningTime = '-'
        consoleData.dataCenter.pid = null
        consoleData.dataCenter.cpu = 0
        consoleData.dataCenter.memory = 0
        
        // 如果轮询中发现已停止，停止轮询
        if (statusTimer) {
          stopStatusPolling()
        }
      }
    } catch (error) {
      console.error('获取数据中心状态失败:', error)
    }
  }

  /**
   * 启动状态轮询
   */
  const startStatusPolling = () => {
    if (statusTimer) return
    
    fetchDataCenterStatus()  // 立即获取一次
    statusTimer = setInterval(fetchDataCenterStatus, 10000)  // 每10秒刷新（优化：降低轮询频率）
  }

  /**
   * 停止状态轮询
   */
  const stopStatusPolling = () => {
    if (statusTimer) {
      clearInterval(statusTimer)
      statusTimer = null
    }
  }

  /**
   * 解析日志行并转换为日志对象
   */
  const parseLogLine = (line, index) => {
    // 日志格式: 2025-10-10 12:34:56.789 | INFO     | [DataCenter] trace_id DataCenter:init_gateway:123 - Message
    const logPatterns = [
      // 匹配格式1: YYYY-MM-DD HH:mm:ss.SSS | LEVEL | [Context] ...
      /^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}[.,]\d{3})\s*\|\s*(\w+)\s*\|\s*\[([^\]]+)\]/,
      // 匹配格式2: YYYY-MM-DD HH:mm:ss | LEVEL | [Context] ...
      /^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s*\|\s*(\w+)\s*\|\s*\[([^\]]+)\]/,
      // 匹配格式3: YYYY-MM-DD HH:mm:ss.SSS - LEVEL - ...
      /^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}[.,]\d{3})\s*-\s*(\w+)\s*-/
    ]
    
    for (const pattern of logPatterns) {
      const match = line.match(pattern)
      if (match) {
        const timestamp = match[1]
        const level = match[2].trim().toLowerCase()
        const category = match[3] ? match[3].trim() : 'System'
        const message = line.substring(match[0].length).trim()
        
        return {
          id: `log_${Date.now()}_${index}`,
          timestamp,
          level,
          category,
          message: message.replace(/^-\s*/, '')  // 移除开头的 -
        }
      }
    }
    
    // 如果没有匹配到格式，返回原始日志行
    return {
      id: `log_${Date.now()}_${index}`,
      timestamp: getCurrentTime(),
      level: 'info',
      category: 'System',
      message: line
    }
  }

  /**
   * 获取数据中心日志
   */
  const fetchDataCenterLogs = async (incremental = false) => {
    try {
      const params = {
        lines: 100,
        level: 'all'
      }
      
      // 如果是增量更新，使用 since_line
      if (incremental && lastLogLine > 0) {
        params.sinceLine = lastLogLine
      }
      
      const response = await getDataCenterLogs(params.lines, params.level, params.sinceLine)
      
      if (response.success && response.logs && response.logs.length > 0) {
        const newLogs = response.logs
          .map((line, index) => parseLogLine(line, index))
          .filter(log => log.message)  // 过滤空消息
        
        if (incremental) {
          // 增量添加到现有日志
          dataCenterLogs.value.push(...newLogs)
          
          // 限制日志数量，最多保留500条
          if (dataCenterLogs.value.length > 500) {
            dataCenterLogs.value = dataCenterLogs.value.slice(-500)
          }
        } else {
          // 首次加载，直接替换
          dataCenterLogs.value = newLogs
        }
        
        // 更新最后读取的行号
        if (response.total_lines) {
          lastLogLine = response.total_lines
        }
      }
    } catch (error) {
      console.error('获取数据中心日志失败:', error)
    }
  }

  /**
   * 启动日志轮询
   */
  const startLogsPolling = () => {
    if (logsTimer) return
    
    // 首次加载完整日志
    fetchDataCenterLogs(false)
    
    // 之后每5秒增量获取新日志（优化：降低轮询频率，减少CPU占用）
    logsTimer = setInterval(() => {
      fetchDataCenterLogs(true)
    }, 5000)
  }

  /**
   * 停止日志轮询
   */
  const stopLogsPolling = () => {
    if (logsTimer) {
      clearInterval(logsTimer)
      logsTimer = null
    }
  }

  /**
   * 添加数据中心日志到显示列表
   */
  const addDataCenterLog = (log) => {
    const logEntry = {
      id: `log_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      timestamp: log.timestamp,
      level: log.level.toLowerCase(),
      category: log.context || 'System',
      message: log.message
    }
    
    dataCenterLogs.value.push(logEntry)
    
    // 限制日志数量，最多保留500条
    if (dataCenterLogs.value.length > 500) {
      dataCenterLogs.value = dataCenterLogs.value.slice(-500)
    }
  }

  /**
   * 启动SSE日志流
   */
  const startSSELogs = () => {
    if (eventSource) return
    
    console.log('[SSE] 启动SSE日志流...')
    
    try {
      // 创建EventSource连接
      eventSource = new EventSource('/api/datacenter/logs/stream', {
        withCredentials: true  // 携带认证信息
      })
      
      // 接收日志消息
      eventSource.onmessage = (event) => {
        try {
          const log = JSON.parse(event.data)
          addDataCenterLog(log)
        } catch (error) {
          console.error('[SSE] 解析日志失败:', error, event.data)
        }
      }
      
      // 连接打开
      eventSource.onopen = () => {
        console.log('[SSE] 连接已建立')
        useSSE = true
      }
      
      // 错误处理
      eventSource.onerror = (error) => {
        console.error('[SSE] 连接错误:', error)
        
        // 检查连接状态
        if (eventSource.readyState === EventSource.CLOSED) {
          console.warn('[SSE] 连接已关闭，降级到轮询模式')
          stopSSELogs()
          useSSE = false
          
          // 降级到轮询
          startLogsPolling()
        } else if (eventSource.readyState === EventSource.CONNECTING) {
          console.log('[SSE] 正在重连...')
        }
      }
      
    } catch (error) {
      console.error('[SSE] 创建SSE连接失败:', error)
      useSSE = false
      // 降级到轮询
      startLogsPolling()
    }
  }

  /**
   * 停止SSE日志流
   */
  const stopSSELogs = () => {
    if (eventSource) {
      console.log('[SSE] 关闭SSE连接')
      eventSource.close()
      eventSource = null
    }
  }

  /**
   * 启动数据中心日志（智能选择SSE或轮询）
   */
  const startDataCenterLogs = () => {
    // 检查浏览器是否支持SSE
    if (typeof EventSource === 'undefined') {
      console.warn('[SSE] 浏览器不支持EventSource，使用轮询模式')
      useSSE = false
      startLogsPolling()
      return
    }
    
    // 优先使用SSE
    if (useSSE) {
      startSSELogs()
    } else {
      startLogsPolling()
    }
  }

  /**
   * 停止数据中心日志
   */
  const stopDataCenterLogs = () => {
    stopSSELogs()
    stopLogsPolling()
    lastLogLine = 0
  }

  // 组件挂载时检查状态
  onMounted(() => {
    fetchDataCenterStatus()
    // 如果数据中心在运行，启动轮询
    setTimeout(() => {
      if (consoleData.dataCenter.status === 'running') {
        startStatusPolling()
        startDataCenterLogs()  // 使用智能选择（SSE或轮询）
      }
    }, 1000)
  })

  // 组件卸载时清理
  onUnmounted(() => {
    stopStatusPolling()
    stopDataCenterLogs()  // 同时清理SSE和轮询
  })

  return {
    // 状态
    consoleData,
    tradingSystemLogs,
    dataCenterLogs,
    selectedTradingLogLevel,
    selectedDataCenterLogLevel,
    
    // 计算属性
    filteredTradingLogs,
    filteredDataCenterLogs,
    
    // 方法
    addConsoleLog,
    handleStartTradingSystem,
    handleStopTradingSystem,
    handleStartDataCenter,
    handleStopDataCenter,
    handleRestartDataCenter,
    fetchDataCenterStatus
  }
}

