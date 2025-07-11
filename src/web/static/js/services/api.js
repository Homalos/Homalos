// API服务模块
class ApiService {
    static baseUrl = window.location.origin
    
    // 通用请求方法
    static async request(url, options = {}) {
        try {
            const defaultOptions = {
                headers: {
                    'Content-Type': 'application/json'
                }
            }
            
            const finalOptions = { ...defaultOptions, ...options }
            
            const response = await fetch(`${this.baseUrl}${url}`, finalOptions)
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`)
            }
            
            const data = await response.json()
            return data
        } catch (error) {
            console.error(`API请求失败 [${url}]:`, error)
            throw error
        }
    }
    
    // 系统状态API
    static async getSystemStatus() {
        return await this.request('/api/v1/system/status')
    }
    
    // 策略管理API
    static async discoverStrategies() {
        return await this.request('/api/v1/strategies/discover')
    }
    
    static async getStrategies() {
        return await this.request('/api/v1/strategies')
    }
    
    static async loadStrategy(strategyData) {
        return await this.request('/api/v1/strategies', {
            method: 'POST',
            body: JSON.stringify(strategyData)
        })
    }
    
    static async startStrategy(strategyUuid) {
        return await this.request(`/api/v1/strategies/${strategyUuid}/start`, {
            method: 'POST'
        })
    }
    
    static async stopStrategy(strategyUuid) {
        return await this.request(`/api/v1/strategies/${strategyUuid}/stop`, {
            method: 'POST'
        })
    }
    
    static async getStrategyStatus(strategyUuid) {
        return await this.request(`/api/v1/strategies/${strategyUuid}`)
    }
    
    static async getStrategyOrders(strategyUuid) {
        return await this.request(`/api/v1/strategies/${strategyUuid}/orders`)
    }
    
    // 账户信息API
    static async getAccountInfo() {
        return await this.request('/api/v1/account')
    }
    
    // 行情订阅API
    static async subscribeMarketData(symbols, strategyId) {
        return await this.request('/api/v1/market/subscribe', {
            method: 'POST',
            body: JSON.stringify({
                symbols: symbols,
                strategy_id: strategyId
            })
        })
    }
    
    // 监控统计API
    static async getMonitoringStats() {
        return await this.request('/api/v1/monitoring/stats')
    }
}

// API响应处理工具类
class ApiResponse {
    static success(message, data = null) {
        return {
            success: true,
            message: message,
            data: data,
            timestamp: Date.now()
        }
    }
    
    static error(message, code = 500) {
        return {
            success: false,
            message: message,
            code: code,
            timestamp: Date.now()
        }
    }
    
    static isSuccess(response) {
        return response && response.success === true
    }
    
    static getData(response) {
        return this.isSuccess(response) ? response.data : null
    }
    
    static getMessage(response) {
        return response ? response.message : '未知错误'
    }
}

// API错误处理工具
class ApiError extends Error {
    constructor(message, code = 500, data = null) {
        super(message)
        this.name = 'ApiError'
        this.code = code
        this.data = data
    }
    
    static fromResponse(response) {
        const message = response.message || '请求失败'
        const code = response.code || response.status || 500
        return new ApiError(message, code, response)
    }
}

// 批量API操作工具
class ApiBatch {
    constructor() {
        this.requests = []
    }
    
    add(name, apiCall) {
        this.requests.push({ name, apiCall })
        return this
    }
    
    async execute() {
        const results = {}
        
        for (const { name, apiCall } of this.requests) {
            try {
                results[name] = await apiCall()
            } catch (error) {
                results[name] = { error: error.message }
            }
        }
        
        return results
    }
    
    async executeParallel() {
        const promises = this.requests.map(async ({ name, apiCall }) => {
            try {
                const result = await apiCall()
                return { name, result }
            } catch (error) {
                return { name, error: error.message }
            }
        })
        
        const results = await Promise.all(promises)
        const resultMap = {}
        
        results.forEach(({ name, result, error }) => {
            resultMap[name] = error ? { error } : result
        })
        
        return resultMap
    }
}

// 全局导出
window.ApiService = ApiService
window.ApiResponse = ApiResponse
window.ApiError = ApiError
window.ApiBatch = ApiBatch
