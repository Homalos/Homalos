/**
 * 控制台逻辑 Composable - 简化版（仅交易核心）
 * 数据中心功能已移除
 */
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
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
    }
  })
  
  // 交易核心日志
  const tradingCoreLogs = ref([])
  const selectedTradingCoreLogLevel = ref('all')
  
  let statusTimer = null  // 状态轮询定时器
  let logsTimer = null    // 日志轮询定时器（暂未实现）

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

  // ===== 方法 =====
  
  /**
   * 添加控制台日志
   */
  const addConsoleLog = (level, category, message, details = {}) => {
    addLog(tradingCoreLogs, level, category, message, details, getCurrentTime)
  }

  /**
   * 启动交易核心
   */
  const handleStartTradingCore = async () => {
    try {
      // 检查是否已登录券商账户
      if (!tradingAccountStore.isLoggedIn) {
        ElMessage.warning('请先登录券商账户')
        return
      }

      // 检查是否有完整的账户配置
      if (!tradingAccountStore.hasBrokerConfig) {
        ElMessage.warning('缺少完整的账户配置，请重新登录并输入密码')
        return
      }

      consoleData.tradingCore.status = 'initializing'
      
      const result = await startTradingCore(null, false)  // 不自动连接网关
      
      consoleData.tradingCore.status = result.status || 'running'
      consoleData.tradingCore.startupTime = new Date()
      consoleData.tradingCore.message = result.message || '交易核心已启动'
      
      addConsoleLog(
        'success',
        '系统启动',
        '交易核心启动成功',
        { message: result.message }
      )
      
      ElMessage.success('交易核心已启动')
      
      // 启动状态轮询
      startStatusPolling()
      
    } catch (error) {
      const errorMsg = extractErrorMessage(error)
      consoleData.tradingCore.status = 'error'
      consoleData.tradingCore.message = errorMsg
      
      addConsoleLog(
        'error',
        '系统启动',
        `交易核心启动失败: ${errorMsg}`,
        {}
      )
      ElMessage.error(`交易核心启动失败: ${errorMsg}`)
    }
  }

  /**
   * 停止交易核心
   */
  const handleStopTradingCore = async (force = false) => {
    // 如果第一个参数是事件对象，则使用默认值 false
    if (typeof force !== 'boolean') {
      force = false
    }

    try {
      // 如果是强制停止，需要二次确认
      if (force) {
        await ElMessageBox.confirm(
          '强制停止可能导致数据丢失，确定要强制停止吗？',
          '强制停止确认',
          {
            confirmButtonText: '确定',
            cancelButtonText: '取消',
            type: 'warning'
          }
        )
      }
      
      consoleData.tradingCore.status = 'stopping'
      
      await stopTradingCore(force)
      
      consoleData.tradingCore.status = 'stopped'
      consoleData.tradingCore.runningTime = '-'
      consoleData.tradingCore.startupTime = null
      consoleData.tradingCore.gateway = {
        md_login: false,
        td_login: false,
        td_confirm: false,
        instruments_loaded: false
      }
      consoleData.tradingCore.message = ''
      
      addConsoleLog(
        'warning',
        '系统停止',
        force ? '交易核心已强制停止' : '交易核心已停止',
        {}
      )
      
      ElMessage.warning('交易核心已停止')
      
      // 停止状态轮询
      stopStatusPolling()
      
    } catch (error) {
      if (error === 'cancel') return  // 用户取消
      
      const errorMsg = extractErrorMessage(error)
      addConsoleLog(
        'error',
        '系统停止',
        `交易核心停止失败: ${errorMsg}`,
        {}
      )
      ElMessage.error(`交易核心停止失败: ${errorMsg}`)
    }
  }

  /**
   * 连接CTP网关
   */
  const handleConnectGateway = async () => {
    try {
      // 检查是否已登录券商账户
      if (!tradingAccountStore.isLoggedIn) {
        ElMessage.warning('请先登录券商账户')
        return
      }

      // 检查是否有完整的账户配置
      if (!tradingAccountStore.hasBrokerConfig) {
        ElMessage.warning('缺少完整的账户配置，请重新登录并输入密码')
        return
      }

      consoleData.tradingCore.status = 'connecting'
      
      const result = await connectGateway()
      
      // 更新网关状态
      if (result.gateway_status) {
        consoleData.tradingCore.gateway = result.gateway_status
      }
      
      consoleData.tradingCore.status = 'running'
      
      addConsoleLog(
        'success',
        '网关连接',
        'CTP网关连接成功',
        { gateway: result.gateway_status }
      )
      
      ElMessage.success('CTP网关已连接')
      
    } catch (error) {
      const errorMsg = extractErrorMessage(error)
      consoleData.tradingCore.status = 'running'  // 连接失败但核心仍在运行
      
      addConsoleLog(
        'error',
        '网关连接',
        `CTP网关连接失败: ${errorMsg}`,
        {}
      )
      ElMessage.error(`CTP网关连接失败: ${errorMsg}`)
    }
  }

  /**
   * 断开CTP网关
   */
  const handleDisconnectGateway = async () => {
    try {
      await ElMessageBox.confirm(
        '确定要断开CTP网关吗？',
        '断开确认',
        {
          confirmButtonText: '确定',
          cancelButtonText: '取消',
          type: 'warning'
        }
      )
      
      const result = await disconnectGateway()
      
      // 更新网关状态
      consoleData.tradingCore.gateway = {
        md_login: false,
        td_login: false,
        td_confirm: false,
        instruments_loaded: false
      }
      
      addConsoleLog(
        'warning',
        '网关断开',
        'CTP网关已断开',
        {}
      )
      
      ElMessage.warning('CTP网关已断开')
      
    } catch (error) {
      if (error === 'cancel') return  // 用户取消
      
      const errorMsg = extractErrorMessage(error)
      addConsoleLog(
        'error',
        '网关断开',
        `CTP网关断开失败: ${errorMsg}`,
        {}
      )
      ElMessage.error(`CTP网关断开失败: ${errorMsg}`)
    }
  }

  /**
   * 获取交易核心状态
   */
  const fetchTradingCoreStatus = async () => {
    try {
      const status = await getTradingCoreStatus()
      
      // 更新核心状态
      consoleData.tradingCore.status = status.status || 'stopped'
      consoleData.tradingCore.message = status.message || ''
      
      // 更新网关状态
      if (status.gateway_status) {
        consoleData.tradingCore.gateway = status.gateway_status
      }
      
      // 更新模块状态
      if (status.modules) {
        consoleData.tradingCore.modules = status.modules
      }
      
      // 计算运行时长
      if (status.status === 'running' && consoleData.tradingCore.startupTime) {
        const now = new Date()
        const diffMinutes = Math.floor((now - consoleData.tradingCore.startupTime) / 60000)
        if (diffMinutes < 60) {
          consoleData.tradingCore.runningTime = `${diffMinutes}m`
        } else {
          const hours = Math.floor(diffMinutes / 60)
          const minutes = diffMinutes % 60
          consoleData.tradingCore.runningTime = `${hours}h${minutes}m`
        }
      } else if (status.status !== 'running') {
        consoleData.tradingCore.runningTime = '-'
        consoleData.tradingCore.startupTime = null
        
        // 如果轮询中发现已停止，停止轮询
        if (statusTimer) {
          stopStatusPolling()
        }
      }
      
    } catch (error) {
      console.error('获取交易核心状态失败:', error)
    }
  }

  /**
   * 启动状态轮询
   */
  const startStatusPolling = () => {
    if (statusTimer) return
    
    fetchTradingCoreStatus()  // 立即获取一次
    statusTimer = setInterval(fetchTradingCoreStatus, 5000)  // 每5秒刷新
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

  // ===== 生命周期 =====
  
  onMounted(() => {
    // 组件挂载时获取一次状态
    fetchTradingCoreStatus()
  })

  onUnmounted(() => {
    // 组件卸载时停止轮询
    stopStatusPolling()
  })

  // ===== 返回 =====
  
  return {
    // 状态
    consoleData,
    tradingCoreLogs,
    selectedTradingCoreLogLevel,
    filteredTradingCoreLogs,
    tradingAccountStore,
    
    // 方法
    handleStartTradingCore,
    handleStopTradingCore,
    handleConnectGateway,
    handleDisconnectGateway,
    fetchTradingCoreStatus,
    startStatusPolling,
    stopStatusPolling
  }
}
