// 全局状态管理模块
// 使用Vue全局变量

// 全局响应式状态
const globalState = Vue.reactive({
    // 系统状态
    system: {
        isRunning: false,
        connectionStatus: 'disconnected',
        lastUpdate: null
    },
    
    // 策略相关数据
    strategies: {},
    availableStrategies: [],
    selectedStrategy: null,
    
    // 账户信息
    accountInfo: {
        totalBalance: 0,
        availableBalance: 0,
        margin: 0
    },
    
    // UI状态
    ui: {
        strategyDialogVisible: false,
        loading: false,
        loadingText: '加载中...'
    },
    
    // 实时数据
    realtimeLogs: [],
    wsConnection: {
        connected: false,
        ws: null
    }
})

// 状态操作方法
const stateActions = {
    // 更新系统状态
    updateSystemStatus(status) {
        // 字段映射：将后端snake_case转换为前端camelCase
        const mappedStatus = {
            isRunning: status.is_running,
            startTime: status.start_time,
            connectionStatus: status.connectionStatus || 'connected',
            ...status
        }
        
        Object.assign(globalState.system, mappedStatus)
        globalState.system.lastUpdate = new Date()
        
        console.log('系统状态已更新:', {
            isRunning: globalState.system.isRunning,
            mappedFrom: status.is_running
        })
    },
    
    // 更新策略列表
    updateStrategies(strategies) {
        // 处理策略数据，确保格式正确
        if (Array.isArray(strategies)) {
            // 如果是数组，转换为对象
            const strategiesObj = {}
            strategies.forEach(strategy => {
                strategiesObj[strategy.strategy_id] = strategy
            })
            globalState.strategies = strategiesObj
        } else if (typeof strategies === 'object') {
            // 如果已经是对象，直接使用
            globalState.strategies = { ...strategies }
        }
        
        console.log('策略列表已更新:', Object.keys(globalState.strategies).length, '个策略')
    },
    
    // 更新可用策略列表
    updateAvailableStrategies(strategies) {
        globalState.availableStrategies = [...strategies]
    },
    
    // 选择策略
    selectStrategy(strategy) {
        globalState.selectedStrategy = strategy
    },
    
    // 更新账户信息
    updateAccountInfo(accountInfo) {
        // 字段映射处理
        const mappedAccountInfo = {
            totalBalance: accountInfo.total_balance || accountInfo.totalBalance || 0,
            availableBalance: accountInfo.available_balance || accountInfo.availableBalance || 0,
            margin: accountInfo.margin || 0,
            ...accountInfo
        }
        
        Object.assign(globalState.accountInfo, mappedAccountInfo)
    },
    
    // 显示/隐藏策略对话框
    toggleStrategyDialog(visible = null) {
        if (visible !== null) {
            globalState.ui.strategyDialogVisible = visible
        } else {
            globalState.ui.strategyDialogVisible = !globalState.ui.strategyDialogVisible
        }
    },
    
    // 设置加载状态
    setLoading(loading, text = '加载中...') {
        globalState.ui.loading = loading
        globalState.ui.loadingText = text
    },
    
    // 添加日志
    addLog(type, message) {
        const log = {
            id: Date.now() + Math.random(),
            timestamp: new Date().toLocaleTimeString(),
            type: type,
            message: message
        }
        
        globalState.realtimeLogs.unshift(log)
        
        // 限制日志数量
        if (globalState.realtimeLogs.length > 100) {
            globalState.realtimeLogs = globalState.realtimeLogs.slice(0, 100)
        }
        
        // 调试日志
        console.log(`新日志: [${type}] ${message}`)
    },
    
    // 清空日志
    clearLogs() {
        globalState.realtimeLogs.length = 0
    },
    
    // 更新WebSocket连接状态
    updateWSConnection(connected, ws = null) {
        globalState.wsConnection.connected = connected
        if (ws) {
            globalState.wsConnection.ws = ws
        }
        
        // 添加连接状态变化日志
        const statusText = connected ? '已连接' : '已断开'
        this.addLog('info', `WebSocket ${statusText}`)
    }
}

// 计算属性（getter）
const stateGetters = {
    // 策略列表
    get strategyList() {
        return Object.values(globalState.strategies)
    },
    
    // 运行中的策略数量
    get runningStrategiesCount() {
        return this.strategyList.filter(s => s.status === 'running').length
    },
    
    // 系统是否健康
    get isSystemHealthy() {
        return globalState.system.isRunning && globalState.wsConnection.connected
    },
    
    // 格式化的账户余额
    get formattedBalance() {
        return globalState.accountInfo.totalBalance?.toFixed(2) || '0.00'
    }
}

// 用于组合式API的工具函数
function useGlobalState() {
    return {
        state: globalState,
        actions: stateActions,
        getters: stateGetters
    }
}

// 全局导出
window.globalState = globalState
window.stateActions = stateActions
window.stateGetters = stateGetters
window.useGlobalState = useGlobalState 