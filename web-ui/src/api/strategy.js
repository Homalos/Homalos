import request from './request'

/**
 * 获取所有策略列表
 * @returns {Promise} 策略列表
 */
export function getStrategies() {
  return request({
    url: '/api/strategies',
    method: 'get'
  })
}

/**
 * 启动策略
 * @param {string} sid - 策略ID
 * @returns {Promise} 操作结果
 */
export function startStrategy(sid) {
  return request({
    url: `/api/strategies/${sid}/start`,
    method: 'post'
  })
}

/**
 * 停止策略
 * @param {string} sid - 策略ID
 * @returns {Promise} 操作结果
 */
export function stopStrategy(sid) {
  return request({
    url: `/api/strategies/${sid}/stop`,
    method: 'post'
  })
}

/**
 * 重载策略
 * @param {string} sid - 策略ID
 * @returns {Promise} 操作结果
 */
export function reloadStrategy(sid) {
  return request({
    url: `/api/strategies/${sid}/reload`,
    method: 'post'
  })
}

/**
 * 启用策略
 * @param {string} sid - 策略ID
 * @returns {Promise} 操作结果
 */
export function enableStrategy(sid) {
  return request({
    url: `/api/strategies/${sid}/enable`,
    method: 'post'
  })
}

/**
 * 禁用策略
 * @param {string} sid - 策略ID
 * @returns {Promise} 操作结果
 */
export function disableStrategy(sid) {
  return request({
    url: `/api/strategies/${sid}/disable`,
    method: 'post'
  })
}

/**
 * 获取策略运行状态
 * @returns {Promise} 运行状态
 */
export function getStrategyStatus() {
  return request({
    url: '/api/strategies/status',
    method: 'get'
  })
}

/**
 * 创建策略WebSocket连接
 * @param {Function} onMessage - 消息回调函数
 * @param {Function} onError - 错误回调函数
 * @param {Function} onClose - 关闭回调函数
 * @param {string} filter - 可选，过滤特定策略ID
 * @returns {WebSocket} WebSocket实例
 */
export function createStrategyWebSocket(onMessage, onError = null, onClose = null, filter = null) {
  const wsUrl = filter 
    ? `ws://localhost:8000/api/strategies/ws?filter=${filter}`
    : `ws://localhost:8000/api/strategies/ws`
  
  const ws = new WebSocket(wsUrl)
  
  ws.onopen = () => {
    console.log('策略WebSocket已连接')
  }
  
  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      if (onMessage) {
        onMessage(data)
      }
    } catch (error) {
      console.error('解析WebSocket消息失败:', error)
    }
  }
  
  ws.onerror = (error) => {
    console.error('WebSocket错误:', error)
    if (onError) {
      onError(error)
    }
  }
  
  ws.onclose = (event) => {
    console.log('策略WebSocket已断开', event.code, event.reason)
    if (onClose) {
      onClose(event)
    }
  }
  
  return ws
}

