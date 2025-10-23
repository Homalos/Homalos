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
 * 卸载策略
 * @param {string} sid - 策略ID
 * @returns {Promise} 操作结果
 */
export function unloadStrategy(sid) {
  return request({
    url: `/api/strategies/${sid}/unload`,
    method: 'delete'
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
 * 扫描并加载策略
 * 自动发现 src/strategy/strategies/ 目录下继承BaseStrategy的策略类
 * @returns {Promise} 扫描结果
 */
export function scanStrategies() {
  return request({
    url: '/api/strategies/scan',
    method: 'post'
  })
}

/**
 * 获取可用的策略文件列表
 * @returns {Promise} 策略文件列表
 */
export function getAvailableStrategyFiles() {
  return request({
    url: '/api/strategies/available-files',
    method: 'get'
  })
}

/**
 * 扫描并加载单个策略文件
 * @param {string} filename - 策略文件名
 * @returns {Promise} 加载结果
 */
export function scanSingleStrategy(filename) {
  return request({
    url: '/api/strategies/scan-single',
    method: 'post',
    data: { filename }
  })
}

/**
 * 创建增强的策略WebSocket连接（支持自动重连、心跳检测）
 * @param {Function} onMessage - 消息回调函数
 * @param {Function} onError - 错误回调函数
 * @param {Function} onClose - 关闭回调函数
 * @param {string} filter - 可选，过滤特定策略ID
 * @returns {Object} WebSocket管理对象
 */
export function createStrategyWebSocket(onMessage, onError = null, onClose = null, filter = null) {
  const wsUrl = filter 
    ? `ws://localhost:8000/api/strategies/ws?filter=${filter}`
    : `ws://localhost:8000/api/strategies/ws`
  
  let ws = null
  let reconnectAttempts = 0
  let maxReconnectAttempts = 10
  let reconnectDelay = 1000 // 初始重连延迟1秒
  let maxReconnectDelay = 30000 // 最大30秒
  let reconnectTimer = null
  let heartbeatTimer = null
  let heartbeatInterval = 30000 // 30秒心跳
  let isManualClose = false
  
  // 创建连接
  function connect() {
    try {
      ws = new WebSocket(wsUrl)
      
      ws.onopen = () => {
        console.log('✅ 策略WebSocket已连接')
        reconnectAttempts = 0 // 重置重连次数
        reconnectDelay = 1000 // 重置延迟
        startHeartbeat() // 启动心跳
      }
      
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          
          // 处理心跳响应
          if (data.type === 'pong') {
            console.log('💓 收到心跳响应')
            return
          }
          
          // 调用消息回调
          if (onMessage) {
            onMessage(data)
          }
        } catch (error) {
          console.error('❌ 解析WebSocket消息失败:', error)
        }
      }
      
      ws.onerror = (error) => {
        console.error('❌ WebSocket错误:', error)
        if (onError) {
          onError(error)
        }
      }
      
      ws.onclose = (event) => {
        console.log('🔌 WebSocket已断开', { code: event.code, reason: event.reason })
        stopHeartbeat()
        
        if (onClose) {
          onClose(event)
        }
        
        // 如果不是手动关闭，尝试重连
        if (!isManualClose && reconnectAttempts < maxReconnectAttempts) {
          scheduleReconnect()
        } else if (reconnectAttempts >= maxReconnectAttempts) {
          console.error('❌ 达到最大重连次数，停止重连')
        }
      }
    } catch (error) {
      console.error('❌ 创建WebSocket失败:', error)
      scheduleReconnect()
    }
  }
  
  // 计划重连
  function scheduleReconnect() {
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
    }
    
    reconnectAttempts++
    const delay = Math.min(reconnectDelay * Math.pow(1.5, reconnectAttempts - 1), maxReconnectDelay)
    
    console.log(`🔄 ${delay/1000}秒后尝试第${reconnectAttempts}次重连...`)
    
    reconnectTimer = setTimeout(() => {
      console.log(`🔄 正在进行第${reconnectAttempts}次重连...`)
      connect()
    }, delay)
  }
  
  // 启动心跳
  function startHeartbeat() {
    stopHeartbeat()
    heartbeatTimer = setInterval(() => {
      if (ws && ws.readyState === WebSocket.OPEN) {
        try {
          ws.send(JSON.stringify({ type: 'ping' }))
          console.log('💓 发送心跳')
        } catch (error) {
          console.error('❌ 发送心跳失败:', error)
        }
      }
    }, heartbeatInterval)
  }
  
  // 停止心跳
  function stopHeartbeat() {
    if (heartbeatTimer) {
      clearInterval(heartbeatTimer)
      heartbeatTimer = null
    }
  }
  
  // 手动关闭
  function close(code = 1000, reason = 'Client disconnect') {
    isManualClose = true
    stopHeartbeat()
    
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
    
    if (ws) {
      ws.close(code, reason)
      ws = null
    }
    
    console.log('🔌 WebSocket已手动关闭')
  }
  
  // 获取连接状态
  function getReadyState() {
    return ws ? ws.readyState : WebSocket.CLOSED
  }
  
  // 获取状态文本
  function getReadyStateText() {
    const state = getReadyState()
    const states = {
      [WebSocket.CONNECTING]: '连接中',
      [WebSocket.OPEN]: '已连接',
      [WebSocket.CLOSING]: '关闭中',
      [WebSocket.CLOSED]: '已关闭'
    }
    return states[state] || '未知'
  }
  
  // 立即连接
  connect()
  
  // 返回管理对象
  return {
    close,
    getReadyState,
    getReadyStateText,
    get reconnectAttempts() { return reconnectAttempts },
    get isConnected() { return ws && ws.readyState === WebSocket.OPEN }
  }
}

