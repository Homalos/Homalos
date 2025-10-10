/**
 * 控制台逻辑 Composable
 */
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  startDataCenter,
  stopDataCenter,
  restartDataCenter,
  getDataCenterStatus
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
      
      // 启动状态轮询
      startStatusPolling()
      
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
      
      // 停止状态轮询
      stopStatusPolling()
      
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
      
      // 重启状态轮询
      startStatusPolling()
      
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
    statusTimer = setInterval(fetchDataCenterStatus, 5000)  // 每5秒刷新
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

  // 组件挂载时检查状态
  onMounted(() => {
    fetchDataCenterStatus()
    // 如果数据中心在运行，启动轮询
    setTimeout(() => {
      if (consoleData.dataCenter.status === 'running') {
        startStatusPolling()
      }
    }, 1000)
  })

  // 组件卸载时清理
  onUnmounted(() => {
    stopStatusPolling()
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

