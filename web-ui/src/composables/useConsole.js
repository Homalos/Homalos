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
import {
  startTradingCore,
  stopTradingCore,
  getTradingCoreStatus,
  connectGateway,
  disconnectGateway
} from '@/api/tradingCore'
import { getCurrentTime, addLog } from '@/utils'

export function useConsole() {
  // ===== 状态管理 =====
  const consoleData = reactive({
    tradingCore: {
      status: 'stopped',  // stopped | initializing | connecting | running | stopping | error
      runningTime: '-',
      startupTime: null,
      gateway: {
        md_login: false,
        td_login: false,
        td_confirm: false,
        instruments_loaded: false
      },
      modules: {},  // 核心模块状态
      message: ''
    },
    dataCenter: {
      status: 'stopped',
      runningTime: '-',
      pid: null,
      cpu: 0,
      memory: 0
    }
  })
  
  // 分离日志：交易核心和数据中心各自的日志（初始都为空）
  const tradingCoreLogs = ref([])
  const dataCenterLogs = ref([])
  
  const selectedTradingCoreLogLevel = ref('all')
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
  
  // 交易核心日志过滤
  const filteredTradingCoreLogs = computed(() => {
    if (selectedTradingCoreLogLevel.value === 'all') {
      return tradingCoreLogs.value
    }
    return tradingCoreLogs.value.filter(log => log.level === selectedTradingCoreLogLevel.value)
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
    const component = details.component || 'tradingCore'  // 默认为交易核心
    
    if (component === 'dataCenter') {
      addLog(dataCenterLogs, level, category, message, details, getCurrentTime)
    } else {
      addLog(tradingCoreLogs, level, category, message, details, getCurrentTime)
    }
  }

  /**
   * 启动交易核心（真实API调用）
   * @param {Boolean} autoConnectGateway - 是否自动连接网关
   */
  const handleStartTradingCore = async (autoConnectGateway = true) => {
    try {
      consoleData.tradingCore.status = 'initializing'
      consoleData.tradingCore.message = '正在启动...'
      
      const result = await startTradingCore(null, autoConnectGateway)
      
      if (result.success) {
        consoleData.tradingCore.status = result.status || 'running'
        consoleData.tradingCore.startupTime = result.startup_time
        consoleData.tradingCore.message = result.message
        
        addConsoleLog(
          'success',
          '核心启动',
          `交易核心启动成功: ${result.message}`,
          { startup_time: result.startup_time, component: 'tradingCore' }
        )
        
        ElMessage.success(result.message || '交易核心已启动')
        
        // 立即刷新一次状态
        await fetchTradingCoreStatus()
        
        // 启动状态轮询
        startTradingCoreStatusPolling()
      } else {
        throw new Error(result.message || '启动失败')
      }
      
    } catch (error) {
      const errorMsg = extractErrorMessage(error)
      consoleData.tradingCore.status = 'error'
      consoleData.tradingCore.message = errorMsg
      
      addConsoleLog(
        'error',
        '核心启动',
        `交易核心启动失败: ${errorMsg}`,
        { component: 'tradingCore' }
      )
      ElMessage.error(`交易核心启动失败: ${errorMsg}`)
    }
  }

  /**
   * 停止量化交易系统（真实API调用）
   */
  const handleStopTradingSystem = async (force = false) => {
    if (typeof force !== 'boolean') {
      force = false
    }
    
    try {
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
      
      await stopTradingSystem(force)
      
      consoleData.tradingSystem.status = 'stopped'
      consoleData.tradingSystem.runningTime = '-'
      consoleData.tradingSystem.pid = null
      consoleData.tradingSystem.cpu = 0
      consoleData.tradingSystem.memory = 0
      
      addConsoleLog(
        'warning',
        '系统停止',
        force ? '量化交易系统已强制停止' : '量化交易系统已停止',
        { component: 'tradingSystem' }
      )
      
      ElMessage.warning('量化交易系统已停止')
      
      // 停止状态轮询和日志流
      stopTradingSystemStatusPolling()
      stopTradingSystemLogs()
      
    } catch (error) {
      if (error === 'cancel') return
      
      const errorMsg = extractErrorMessage(error)
      addConsoleLog(
        'error',
        '系统停止',
        `量化交易系统停止失败: ${errorMsg}`,
        { component: 'tradingSystem' }
      )
      ElMessage.error(`量化交易系统停止失败: ${errorMsg}`)
    }
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

  // ===== 量化交易系统状态和日志管理 =====

  let tradingSystemStatusTimer = null
  let tradingSystemLogsTimer = null
  let tradingSystemEventSource = null
  let tradingSystemLastLogLine = 0
  let useTradingSystemSSE = true

  /**
   * 获取交易系统状态
   */
  const fetchTradingSystemStatus = async () => {
    try {
      const status = await getTradingSystemStatus()
      
      if (status.running) {
        consoleData.tradingSystem.status = 'running'
        consoleData.tradingSystem.pid = status.pid
        consoleData.tradingSystem.cpu = status.cpu_percent || 0
        consoleData.tradingSystem.memory = status.memory_mb || 0
        
        // 计算运行时长
        if (status.create_time) {
          const createTime = new Date(status.create_time)
          const now = new Date()
          const diffMinutes = Math.floor((now - createTime) / 60000)
          if (diffMinutes < 60) {
            consoleData.tradingSystem.runningTime = `${diffMinutes}m`
          } else {
            const hours = Math.floor(diffMinutes / 60)
            const minutes = diffMinutes % 60
            consoleData.tradingSystem.runningTime = `${hours}h${minutes}m`
          }
        }
      } else {
        consoleData.tradingSystem.status = 'stopped'
        consoleData.tradingSystem.runningTime = '-'
        consoleData.tradingSystem.pid = null
        consoleData.tradingSystem.cpu = 0
        consoleData.tradingSystem.memory = 0
        
        if (tradingSystemStatusTimer) {
          stopTradingSystemStatusPolling()
        }
      }
    } catch (error) {
      console.error('获取交易系统状态失败:', error)
    }
  }

  /**
   * 启动交易系统状态轮询
   */
  const startTradingSystemStatusPolling = () => {
    if (tradingSystemStatusTimer) return
    
    fetchTradingSystemStatus()
    tradingSystemStatusTimer = setInterval(fetchTradingSystemStatus, 10000)
  }

  /**
   * 停止交易系统状态轮询
   */
  const stopTradingSystemStatusPolling = () => {
    if (tradingSystemStatusTimer) {
      clearInterval(tradingSystemStatusTimer)
      tradingSystemStatusTimer = null
    }
  }

  /**
   * 获取交易系统日志
   */
  const fetchTradingSystemLogs = async (incremental = false) => {
    try {
      const params = {
        lines: 100,
        level: 'all'
      }
      
      if (incremental && tradingSystemLastLogLine > 0) {
        params.sinceLine = tradingSystemLastLogLine
      }
      
      const response = await getTradingSystemLogs(params.lines, params.level, params.sinceLine)
      
      if (response.success && response.logs && response.logs.length > 0) {
        const newLogs = response.logs
          .map((line, index) => parseLogLine(line, index))
          .filter(log => log.message)
        
        if (incremental) {
          tradingSystemLogs.value.push(...newLogs)
          
          if (tradingSystemLogs.value.length > 500) {
            tradingSystemLogs.value = tradingSystemLogs.value.slice(-500)
          }
        } else {
          tradingSystemLogs.value = newLogs
        }
        
        if (response.total_lines) {
          tradingSystemLastLogLine = response.total_lines
        }
      }
    } catch (error) {
      console.error('获取交易系统日志失败:', error)
    }
  }

  /**
   * 启动交易系统日志轮询
   */
  const startTradingSystemLogsPolling = () => {
    if (tradingSystemLogsTimer) return
    
    fetchTradingSystemLogs(false)
    tradingSystemLogsTimer = setInterval(() => {
      fetchTradingSystemLogs(true)
    }, 5000)
  }

  /**
   * 停止交易系统日志轮询
   */
  const stopTradingSystemLogsPolling = () => {
    if (tradingSystemLogsTimer) {
      clearInterval(tradingSystemLogsTimer)
      tradingSystemLogsTimer = null
    }
  }

  /**
   * 添加交易系统日志
   */
  const addTradingSystemLog = (log) => {
    const logEntry = {
      id: `log_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      timestamp: log.timestamp,
      level: log.level.toLowerCase(),
      category: log.context || 'System',
      message: log.message
    }
    
    tradingSystemLogs.value.push(logEntry)
    
    if (tradingSystemLogs.value.length > 500) {
      tradingSystemLogs.value = tradingSystemLogs.value.slice(-500)
    }
  }

  /**
   * 启动交易系统SSE日志流
   */
  const startTradingSystemSSELogs = () => {
    if (tradingSystemEventSource) return
    
    console.log('[SSE] 启动交易系统SSE日志流...')
    
    try {
      tradingSystemEventSource = new EventSource('/api/trading-system/logs/stream', {
        withCredentials: true
      })
      
      tradingSystemEventSource.onmessage = (event) => {
        try {
          const log = JSON.parse(event.data)
          addTradingSystemLog(log)
        } catch (error) {
          console.error('[SSE] 解析日志失败:', error, event.data)
        }
      }
      
      tradingSystemEventSource.onopen = () => {
        console.log('[SSE] 交易系统日志连接已建立')
        useTradingSystemSSE = true
      }
      
      tradingSystemEventSource.onerror = (error) => {
        console.error('[SSE] 交易系统日志连接错误:', error)
        
        if (tradingSystemEventSource.readyState === EventSource.CLOSED) {
          console.warn('[SSE] 连接已关闭，降级到轮询模式')
          stopTradingSystemSSELogs()
          useTradingSystemSSE = false
          startTradingSystemLogsPolling()
        } else if (tradingSystemEventSource.readyState === EventSource.CONNECTING) {
          console.log('[SSE] 正在重连...')
        }
      }
      
    } catch (error) {
      console.error('[SSE] 创建SSE连接失败:', error)
      useTradingSystemSSE = false
      startTradingSystemLogsPolling()
    }
  }

  /**
   * 停止交易系统SSE日志流
   */
  const stopTradingSystemSSELogs = () => {
    if (tradingSystemEventSource) {
      console.log('[SSE] 关闭交易系统SSE连接')
      tradingSystemEventSource.close()
      tradingSystemEventSource = null
    }
  }

  /**
   * 启动交易系统日志（使用轮询模式）
   * 注意：暂时禁用SSE，因为EventSource不支持携带认证token
   */
  const startTradingSystemLogs = () => {
    console.log('[交易系统] 使用轮询模式获取日志')
    startTradingSystemLogsPolling()
  }

  /**
   * 停止交易系统日志
   */
  const stopTradingSystemLogs = () => {
    stopTradingSystemSSELogs()
    stopTradingSystemLogsPolling()
    tradingSystemLastLogLine = 0
  }

  // 组件挂载时检查状态
  onMounted(() => {
    fetchDataCenterStatus()
    fetchTradingSystemStatus()
    // 如果数据中心在运行，启动轮询
    setTimeout(() => {
      if (consoleData.dataCenter.status === 'running') {
        startStatusPolling()
        startDataCenterLogs()  // 使用智能选择（SSE或轮询）
      }
      if (consoleData.tradingSystem.status === 'running') {
        startTradingSystemStatusPolling()
        startTradingSystemLogs()
      }
    }, 1000)
  })

  // 组件卸载时清理
  onUnmounted(() => {
    stopStatusPolling()
    stopDataCenterLogs()  // 同时清理SSE和轮询
    stopTradingSystemStatusPolling()
    stopTradingSystemLogs()
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
    fetchDataCenterStatus,
    fetchTradingSystemStatus
  }
}

