/**
 * 控制台逻辑 Composable
 */
import { ref, reactive, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { consoleLogsData } from '@/mock'
import { getCurrentTime, addLog } from '@/utils'

export function useConsole() {
  // ===== 状态管理 =====
  const consoleData = reactive({
    tradingSystem: {
      status: 'stopped',  // running | stopped
      runningTime: '-'
    },
    dataCenter: {
      status: 'stopped',  // running | stopped
      runningTime: '-'
    }
  })
  
  const consoleLogs = ref(consoleLogsData)
  const selectedConsoleLogLevel = ref('all')

  // ===== 计算属性 =====
  const filteredConsoleLogs = computed(() => {
    if (selectedConsoleLogLevel.value === 'all') {
      return consoleLogs.value
    }
    return consoleLogs.value.filter(log => log.level === selectedConsoleLogLevel.value)
  })

  // ===== 方法 =====
  
  /**
   * 添加控制台日志
   */
  const addConsoleLog = (level, category, message, details = {}) => {
    addLog(consoleLogs, level, category, message, details, getCurrentTime)
  }

  /**
   * 启动量化交易系统
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
   * 停止量化交易系统
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
   * 启动数据中心
   */
  const handleStartDataCenter = () => {
    consoleData.dataCenter.status = 'running'
    consoleData.dataCenter.runningTime = '0m'
    
    addConsoleLog(
      'success',
      '系统启动',
      '数据中心启动成功',
      { component: 'dataCenter' }
    )
    
    ElMessage.success('数据中心已启动')
  }

  /**
   * 停止数据中心
   */
  const handleStopDataCenter = () => {
    consoleData.dataCenter.status = 'stopped'
    consoleData.dataCenter.runningTime = '-'
    
    addConsoleLog(
      'warning',
      '系统停止',
      '数据中心已停止',
      { component: 'dataCenter' }
    )
    
    ElMessage.warning('数据中心已停止')
  }

  return {
    // 状态
    consoleData,
    consoleLogs,
    selectedConsoleLogLevel,
    
    // 计算属性
    filteredConsoleLogs,
    
    // 方法
    addConsoleLog,
    handleStartTradingSystem,
    handleStopTradingSystem,
    handleStartDataCenter,
    handleStopDataCenter
  }
}

