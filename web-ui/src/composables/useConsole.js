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
  disconnectGateway,
  getRunningStrategiesCount
} from '@/api/tradingCore'
import { getCurrentTime, addLog } from '@/utils'
import { useTradingAccountStore } from '@/stores/tradingAccount'

export function useConsole() {
  // ===== 获取Store =====
  const tradingAccountStore = useTradingAccountStore()
  
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
      // 检查是否已登录资金账户
      if (!tradingAccountStore.isLoggedIn && autoConnectGateway) {
        const result = await ElMessageBox.confirm(
          '启动交易核心并连接网关需要先登录资金账户（输入密码）。\n\n' +
          '您可以选择：\n' +
          '• 先登录资金账户，然后启动\n' +
          '• 只启动核心，稍后手动连接网关',
          '未登录资金账户',
          {
            confirmButtonText: '仅启动核心',
            cancelButtonText: '取消',
            type: 'warning',
            distinguishCancelAndClose: true,
            closeOnClickModal: false
          }
        ).catch(() => 'cancel')
        
        if (result === 'cancel') {
          return
        }
        
        // 用户选择仅启动核心，不自动连接网关
        autoConnectGateway = false
        ElMessage.info('将启动交易核心，但不连接网关。请登录账户后手动连接。')
      }
      
      // 检查是否有完整的broker配置（免密登录时缺少密码）
      if (tradingAccountStore.isLoggedIn && !tradingAccountStore.hasBrokerConfig && autoConnectGateway) {
        const result = await ElMessageBox.confirm(
          '您当前是通过免密登录，系统未获取到完整的账户配置（包括密码）。\n\n' +
          '连接网关需要这些敏感信息。您可以选择：\n' +
          '• 退出后重新登录并输入密码\n' +
          '• 只启动核心，暂不连接网关',
          '缺少完整账户配置',
          {
            confirmButtonText: '仅启动核心',
            cancelButtonText: '取消',
            type: 'warning',
            distinguishCancelAndClose: true,
            closeOnClickModal: false
          }
        ).catch(() => 'cancel')
        
        if (result === 'cancel') {
          return
        }
        
        // 用户选择仅启动核心，不自动连接网关
        autoConnectGateway = false
        ElMessage.info('将启动交易核心，但不连接网关。请重新登录（输入密码）后手动连接。')
      }
      
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
   * 停止交易核心（真实API调用）
   */
  const handleStopTradingCore = async (force = false) => {
    if (typeof force !== 'boolean') {
      force = false
    }
    
    try {
      // 1. 检查运行中的策略数量
      let runningStrategiesCount = 0
      try {
        const countResult = await getRunningStrategiesCount()
        if (countResult.success) {
          runningStrategiesCount = countResult.count || 0
        }
      } catch (error) {
        console.error('获取运行中策略数量失败:', error)
      }
      
      // 2. 如果有运行中的策略，显示警告提示
      if (runningStrategiesCount > 0) {
        await ElMessageBox.confirm(
          `当前有 ${runningStrategiesCount} 个策略正在运行。停止交易核心将自动停止所有运行中的策略，可能导致未平仓位风险。\n\n确定要停止交易核心吗？`,
          '高风险操作警告',
          {
            confirmButtonText: '确定停止',
            cancelButtonText: '取消',
            type: 'warning',
            dangerouslyUseHTMLString: false
          }
        )
      }
      
      // 3. 如果是强制停止，再次确认
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
      
      consoleData.tradingCore.status = 'stopping'
      consoleData.tradingCore.message = '正在停止...'
      
      const result = await stopTradingCore(force)
      
      if (result.success) {
        consoleData.tradingCore.status = 'stopped'
        consoleData.tradingCore.runningTime = '-'
        consoleData.tradingCore.startupTime = null
        consoleData.tradingCore.gateway = {
          md_login: false,
          td_login: false,
          td_confirm: false,
          instruments_loaded: false
        }
        consoleData.tradingCore.modules = {}
        consoleData.tradingCore.message = result.message
    
        const stoppedCount = result.stopped_strategies_count || 0
        const logMessage = stoppedCount > 0 
          ? `交易核心已停止，同时停止了 ${stoppedCount} 个策略` 
          : (force ? '交易核心已强制停止' : result.message)
    
        addConsoleLog(
          'warning',
          '核心停止',
          logMessage,
          { component: 'tradingCore', stopped_strategies_count: stoppedCount }
        )
        
        ElMessage.warning(logMessage)
        
        // 停止状态轮询
        stopTradingCoreStatusPolling()
      } else {
        throw new Error(result.message || '停止失败')
      }
      
    } catch (error) {
      if (error === 'cancel') return
      
      const errorMsg = extractErrorMessage(error)
      consoleData.tradingCore.status = 'error'
      consoleData.tradingCore.message = errorMsg
      
      addConsoleLog(
        'error',
        '核心停止',
        `交易核心停止失败: ${errorMsg}`,
        { component: 'tradingCore' }
      )
      ElMessage.error(`交易核心停止失败: ${errorMsg}`)
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

  // ===== 交易核心状态管理 =====

  let tradingCoreStatusTimer = null

  /**
   * 连接CTP网关
   */
  const handleConnectGateway = async () => {
    try {
      // 检查是否已登录资金账户
      if (!tradingAccountStore.isLoggedIn) {
        ElMessageBox.alert(
          '连接网关需要先登录资金账户（输入密码）。\n\n' +
          '新的安全架构下，敏感的账户信息（用户名、密码等）存储在数据库中，\n' +
          '只有登录资金账户时才会构建完整的broker配置。\n\n' +
          '请前往"资金账户"面板登录后再尝试连接网关。',
          '需要登录资金账户',
          {
            confirmButtonText: '知道了',
            type: 'warning'
          }
        )
        return
      }
      
      // 检查是否有完整的broker配置（免密登录时缺少密码）
      if (!tradingAccountStore.hasBrokerConfig) {
        ElMessageBox.alert(
          '您当前是通过免密登录，系统未获取到完整的账户配置（包括密码）。\n\n' +
          '连接网关需要这些敏感信息。\n\n' +
          '请退出资金账户后，重新登录并输入密码，然后再尝试连接网关。',
          '缺少完整账户配置',
          {
            confirmButtonText: '知道了',
            type: 'warning'
          }
        )
        return
      }
      
      consoleData.tradingCore.status = 'connecting'
      consoleData.tradingCore.message = '正在连接网关...'
      
      const result = await connectGateway()
      
      if (result.success) {
        addConsoleLog(
          'success',
          '网关连接',
          result.message || '网关连接成功',
          { component: 'tradingCore' }
        )
        
        ElMessage.success(result.message || '网关连接成功')
        
        // 刷新状态
        await fetchTradingCoreStatus()
      } else {
        throw new Error(result.message || '网关连接失败')
      }
    } catch (error) {
      const errorMsg = extractErrorMessage(error)
      addConsoleLog(
        'error',
        '网关连接',
        `网关连接失败: ${errorMsg}`,
        { component: 'tradingCore' }
      )
      ElMessage.error(`网关连接失败: ${errorMsg}`)
    }
  }

  /**
   * 断开CTP网关
   */
  const handleDisconnectGateway = async () => {
    try {
      await ElMessageBox.confirm(
        '确定要断开网关连接吗？',
        '确认断开',
        {
          confirmButtonText: '确定',
          cancelButtonText: '取消',
          type: 'warning'
        }
      )
      
      const result = await disconnectGateway()
      
      if (result.success) {
        addConsoleLog(
          'warning',
          '网关断开',
          result.message || '网关已断开',
          { component: 'tradingCore' }
        )
        
        ElMessage.warning(result.message || '网关已断开')
        
        // 刷新状态
        await fetchTradingCoreStatus()
      } else {
        throw new Error(result.message || '网关断开失败')
      }
    } catch (error) {
      if (error === 'cancel') return
      
      const errorMsg = extractErrorMessage(error)
      addConsoleLog(
        'error',
        '网关断开',
        `网关断开失败: ${errorMsg}`,
        { component: 'tradingCore' }
      )
      ElMessage.error(`网关断开失败: ${errorMsg}`)
    }
  }

  /**
   * 获取交易核心状态
   */
  const fetchTradingCoreStatus = async () => {
    try {
      const status = await getTradingCoreStatus()
      
      // 更新核心状态（确保是字符串）
      consoleData.tradingCore.status = status.status || 'stopped'
      consoleData.tradingCore.message = status.message || ''
      
      // 更新网关状态（字段名：gateway，不是 gateway_status）
      if (status.gateway) {
        consoleData.tradingCore.gateway = {
          md_login: status.gateway.md_login || false,
          td_login: status.gateway.td_login || false,
          td_confirm: status.gateway.td_confirm || false,
          instruments_loaded: status.gateway.instruments_loaded || false
        }
      } else {
        // 如果没有网关数据，重置为默认值
        consoleData.tradingCore.gateway = {
          md_login: false,
          td_login: false,
          td_confirm: false,
          instruments_loaded: false
        }
      }
      
      // 更新模块状态（字段名：modules，是对象不是数组）
      if (status.modules && typeof status.modules === 'object') {
        consoleData.tradingCore.modules = status.modules
      } else {
        consoleData.tradingCore.modules = {}
      }
      
      // 计算运行时长（字段名：running_time，不是 running_duration）
      if (status.running_time) {
        consoleData.tradingCore.runningTime = status.running_time
      } else if (status.status === 'running' && status.startup_time) {
        const startTime = new Date(status.startup_time)
        const now = new Date()
        const diffMinutes = Math.floor((now - startTime) / 60000)
        if (diffMinutes < 60) {
          consoleData.tradingCore.runningTime = `${diffMinutes}分钟`
        } else {
          const hours = Math.floor(diffMinutes / 60)
          const minutes = diffMinutes % 60
          consoleData.tradingCore.runningTime = `${hours}小时${minutes}分钟`
        }
      } else {
        consoleData.tradingCore.runningTime = '-'
      }
      
      // 如果核心已停止，停止轮询
      if (status.status === 'stopped' && tradingCoreStatusTimer) {
        stopTradingCoreStatusPolling()
      }
      
    } catch (error) {
      console.error('获取交易核心状态失败:', error)
      // 网络错误时，重置为默认状态
      consoleData.tradingCore.status = 'stopped'
      consoleData.tradingCore.message = '无法连接到服务器'
      consoleData.tradingCore.gateway = {
        md_login: false,
        td_login: false,
        td_confirm: false,
        instruments_loaded: false
      }
    }
  }

  /**
   * 启动交易核心状态轮询
   */
  const startTradingCoreStatusPolling = () => {
    if (tradingCoreStatusTimer) return
    
    fetchTradingCoreStatus()
    tradingCoreStatusTimer = setInterval(fetchTradingCoreStatus, 5000)  // 每5秒刷新
  }

  /**
   * 停止交易核心状态轮询
   */
  const stopTradingCoreStatusPolling = () => {
    if (tradingCoreStatusTimer) {
      clearInterval(tradingCoreStatusTimer)
      tradingCoreStatusTimer = null
    }
  }


  // 组件挂载时检查状态
  onMounted(() => {
    fetchDataCenterStatus()
    fetchTradingCoreStatus()
    // 如果数据中心或交易核心在运行，启动轮询
    setTimeout(() => {
      if (consoleData.dataCenter.status === 'running') {
        startStatusPolling()
        startDataCenterLogs()  // 使用智能选择（SSE或轮询）
      }
      if (consoleData.tradingCore.status === 'running') {
        startTradingCoreStatusPolling()
      }
    }, 1000)
  })

  // 组件卸载时清理
  onUnmounted(() => {
    stopStatusPolling()
    stopDataCenterLogs()  // 同时清理SSE和轮询
    stopTradingCoreStatusPolling()
  })

  return {
    // 状态
    consoleData,
    tradingCoreLogs,
    dataCenterLogs,
    selectedTradingCoreLogLevel,
    selectedDataCenterLogLevel,
    tradingAccountStore,  // 暴露给组件使用
    
    // 计算属性
    filteredTradingCoreLogs,
    filteredDataCenterLogs,
    
    // 交易核心方法
    handleStartTradingCore,
    handleStopTradingCore,
    handleConnectGateway,
    handleDisconnectGateway,
    fetchTradingCoreStatus,
    
    // 数据中心方法
    handleStartDataCenter,
    handleStopDataCenter,
    handleRestartDataCenter,
    fetchDataCenterStatus,
    
    // 工具方法
    addConsoleLog
  }
}

