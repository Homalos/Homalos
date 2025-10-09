/**
 * 策略管理逻辑 Composable
 */
import { ref, reactive, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { strategiesData, strategyLogsData } from '@/mock'
import { getCurrentTime, generateStrategyId, getTotalProfitLoss, addLog } from '@/utils'

export function useStrategyManagement() {
  // ===== 状态管理 =====
  const strategies = ref(strategiesData)
  const strategyLogs = ref(strategyLogsData)
  const selectedLogLevel = ref('all')
  
  // 详情面板状态
  const detailDrawerVisible = ref(false)
  const currentStrategy = ref(null)
  const addStrategyDialogVisible = ref(false)
  
  const editableParameters = reactive({
    trading: {},
    risk: {},
    indicator: {},
    riskControl: {}
  })

  // ===== 计算属性 =====
  const activeStrategiesCount = computed(() => strategies.value.length)
  
  const runningStrategiesCount = computed(() => 
    strategies.value.filter(s => s.status === '运行中').length
  )
  
  const stoppedStrategiesCount = computed(() => 
    strategies.value.filter(s => s.status === '已停止').length
  )
  
  const filteredStrategyLogs = computed(() => {
    if (selectedLogLevel.value === 'all') {
      return strategyLogs.value
    }
    return strategyLogs.value.filter(log => log.level === selectedLogLevel.value)
  })

  // ===== 方法 =====
  
  /**
   * 添加策略日志
   */
  const addStrategyLog = (level, category, message, details = {}) => {
    addLog(strategyLogs, level, category, message, details, getCurrentTime)
  }

  /**
   * 添加策略到列表
   */
  const handleAddStrategy = (template) => {
    const newStrategyId = generateStrategyId(strategies.value)
    const currentTime = getCurrentTime()
    
    const newStrategy = {
      id: newStrategyId,
      name: template.name,
      status: '已停止',
      startTime: '',
      runningTime: '-',
      description: template.description,
      author: template.author,
      createTime: currentTime,
      lastModifyTime: currentTime,
      positions: [],
      parameters: {
        trading: {},
        risk: {},
        indicator: {}
      },
      riskControl: {
        maxPosition: template.defaultRiskControl.maxPosition,
        stopLossRatio: template.defaultRiskControl.stopLossRatio,
        takeProfitRatio: template.defaultRiskControl.takeProfitRatio,
        maxDrawdown: template.defaultRiskControl.maxDrawdown
      }
    }
    
    strategies.value.push(newStrategy)
    
    addStrategyLog(
      'success',
      '添加策略',
      `成功添加策略 "${template.name}"`,
      { strategyId: newStrategyId, strategyName: template.name }
    )
    
    addStrategyDialogVisible.value = false
    ElMessage.success(`策略 "${template.name}" 已成功添加到列表`)
  }

  /**
   * 启动策略
   */
  const handleStartStrategy = (strategy) => {
    strategy.status = '运行中'
    strategy.startTime = getCurrentTime()
    
    addStrategyLog(
      'success',
      '启动策略',
      `策略 "${strategy.name}" 已启动`,
      { strategyId: strategy.id, strategyName: strategy.name }
    )
    
    ElMessage.success(`策略 "${strategy.name}" 已启动`)
  }

  /**
   * 停止策略
   */
  const handleStopStrategy = (strategy) => {
    strategy.status = '已停止'
    strategy.runningTime = '-'
    
    addStrategyLog(
      'warning',
      '停止策略',
      `策略 "${strategy.name}" 已停止`,
      { strategyId: strategy.id, strategyName: strategy.name }
    )
    
    ElMessage.success(`策略 "${strategy.name}" 已停止`)
  }

  /**
   * 删除策略
   */
  const handleDeleteStrategy = (strategyId) => {
    ElMessageBox.confirm(
      '确定要删除这个策略吗？',
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    ).then(() => {
      const index = strategies.value.findIndex(s => s.id === strategyId)
      if (index !== -1) {
        const strategy = strategies.value[index]
        strategies.value.splice(index, 1)
        
        addStrategyLog(
          'warning',
          '删除策略',
          `策略 "${strategy.name}" 已删除`,
          { strategyId: strategy.id, strategyName: strategy.name }
        )
        
        ElMessage.success(`策略 "${strategy.name}" 已删除`)
      }
    }).catch(() => {
      // 用户取消删除
    })
  }

  /**
   * 显示策略详情
   */
  const handleShowDetail = (strategy) => {
    currentStrategy.value = strategy
    editableParameters.trading = { ...strategy.parameters.trading }
    editableParameters.risk = { ...strategy.parameters.risk }
    editableParameters.indicator = { ...strategy.parameters.indicator }
    editableParameters.riskControl = { ...strategy.riskControl }
    detailDrawerVisible.value = true
  }

  /**
   * 保存参数配置
   */
  const handleSaveParameters = () => {
    if (!currentStrategy.value) return
    
    currentStrategy.value.parameters.trading = { ...editableParameters.trading }
    currentStrategy.value.parameters.risk = { ...editableParameters.risk }
    currentStrategy.value.parameters.indicator = { ...editableParameters.indicator }
    currentStrategy.value.riskControl = { ...editableParameters.riskControl }
    
    const now = new Date()
    currentStrategy.value.lastModifyTime = now.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false
    }).replace(/\//g, '-')
    
    addStrategyLog(
      'info',
      '参数配置',
      `策略 "${currentStrategy.value.name}" 风险控制参数已更新`,
      { 
        strategyId: currentStrategy.value.id, 
        strategyName: currentStrategy.value.name,
        maxPosition: editableParameters.riskControl.maxPosition,
        stopLossRatio: editableParameters.riskControl.stopLossRatio,
        takeProfitRatio: editableParameters.riskControl.takeProfitRatio,
        maxDrawdown: editableParameters.riskControl.maxDrawdown
      }
    )
    
    ElMessage.success('参数保存成功')
  }

  /**
   * 取消编辑
   */
  const handleCancelEdit = () => {
    if (!currentStrategy.value) return
    
    editableParameters.trading = { ...currentStrategy.value.parameters.trading }
    editableParameters.risk = { ...currentStrategy.value.parameters.risk }
    editableParameters.indicator = { ...currentStrategy.value.parameters.indicator }
    editableParameters.riskControl = { ...currentStrategy.value.riskControl }
    
    ElMessage.info('已取消编辑')
  }

  return {
    // 状态
    strategies,
    strategyLogs,
    selectedLogLevel,
    detailDrawerVisible,
    currentStrategy,
    addStrategyDialogVisible,
    editableParameters,
    
    // 计算属性
    activeStrategiesCount,
    runningStrategiesCount,
    stoppedStrategiesCount,
    filteredStrategyLogs,
    
    // 方法
    addStrategyLog,
    handleAddStrategy,
    handleStartStrategy,
    handleStopStrategy,
    handleDeleteStrategy,
    handleShowDetail,
    handleSaveParameters,
    handleCancelEdit,
    getTotalProfitLoss
  }
}

