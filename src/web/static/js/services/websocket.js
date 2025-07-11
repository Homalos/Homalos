// WebSocket服务模块
// 使用全局变量替代ES6 import

class WebSocketService {
    constructor() {
        this.ws = null
        this.connected = false
        this.reconnectAttempts = 0
        this.maxReconnectAttempts = 5
        this.reconnectInterval = 5000
        this.heartbeatInterval = 30000
        this.heartbeatTimer = null
        this.messageHandlers = new Map()
        this.reconnectTimer = null
    }
    
    // 连接WebSocket
    connect() {
        try {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
            const wsUrl = `${protocol}//${window.location.host}/ws/realtime`
            
            console.log('正在连接WebSocket:', wsUrl)
            this.ws = new WebSocket(wsUrl)
            
            this.ws.onopen = this.onOpen.bind(this)
            this.ws.onmessage = this.onMessage.bind(this)
            this.ws.onclose = this.onClose.bind(this)
            this.ws.onerror = this.onError.bind(this)
            
        } catch (error) {
            console.error('WebSocket连接创建失败:', error)
            this.onConnectionChange(false)
        }
    }
    
    // 连接成功处理
    onOpen() {
        console.log('WebSocket连接已建立')
        this.connected = true
        this.reconnectAttempts = 0
        this.onConnectionChange(true)
        this.startHeartbeat()
        
        // 添加连接成功日志
        window.stateActions.addLog('success', 'WebSocket连接已建立')
        
        // 发送测试日志，确保日志功能正常
        setTimeout(() => {
            window.stateActions.addLog('info', '实时日志功能已激活')
        }, 1000)
    }
    
    // 接收消息处理
    onMessage(event) {
        try {
            const data = JSON.parse(event.data)
            this.handleMessage(data)
        } catch (error) {
            console.error('WebSocket消息解析失败:', error, event.data)
        }
    }
    
    // 连接关闭处理
    onClose(event) {
        console.log('WebSocket连接关闭:', event.code, event.reason)
        this.connected = false
        this.onConnectionChange(false)
        this.stopHeartbeat()
        
        // 添加连接关闭日志
        window.stateActions.addLog('warning', 'WebSocket连接断开')
        
        // 尝试重连
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.scheduleReconnect()
        } else {
            console.warn('WebSocket重连次数已达上限')
            window.stateActions.addLog('error', 'WebSocket重连失败，已达最大重试次数')
        }
    }
    
    // 连接错误处理
    onError(error) {
        console.error('WebSocket连接错误:', error)
        window.stateActions.addLog('error', 'WebSocket连接错误')
    }
    
    // 处理收到的消息
    handleMessage(data) {
        const { type } = data
        
        switch (type) {
            case 'event':
                this.handleEventMessage(data)
                break
            case 'pong':
                // 心跳响应，无需处理
                break
            default:
                console.log('收到未知类型消息:', data)
                break
        }
        
        // 调用注册的消息处理器
        if (this.messageHandlers.has(type)) {
            const handler = this.messageHandlers.get(type)
            try {
                handler(data)
            } catch (error) {
                console.error(`消息处理器执行失败 [${type}]:`, error)
            }
        }
    }
    
    // 处理事件消息
    handleEventMessage(data) {
        const { event_type, data: eventData, source, timestamp } = data
        
        console.log('收到WebSocket事件:', {
            event_type,
            source,
            eventData,
            timestamp
        })
        
        // 格式化事件消息
        let message = ''
        if (typeof eventData === 'object' && eventData !== null) {
            // 如果是对象，尝试提取有意义的信息
            if (eventData.message) {
                message = eventData.message
            } else if (eventData.strategy_id) {
                message = `策略 ${eventData.strategy_id} 状态变化`
            } else {
                message = JSON.stringify(eventData)
            }
        } else {
            message = String(eventData || '系统事件')
        }
        
        // 确定日志级别
        let logLevel = 'info'
        if (event_type.includes('error')) {
            logLevel = 'error'
        } else if (event_type.includes('warning')) {
            logLevel = 'warning'
        } else if (event_type.includes('success') || event_type.includes('started')) {
            logLevel = 'success'
        }
        
        // 添加日志到全局状态
        const fullMessage = source ? `[${source}] ${message}` : message
        window.stateActions.addLog(logLevel, fullMessage)
        
        // 根据事件类型进行特殊处理
        switch (event_type) {
            case 'strategy.started':
            case 'strategy.stopped':
            case 'strategy.error':
                // 策略状态变化，可以触发策略列表刷新
                this.emit('strategy_status_changed', eventData)
                break
            case 'order.submitted':
            case 'order.filled':
            case 'order.cancelled':
                // 订单状态变化
                this.emit('order_status_changed', eventData)
                break
            case 'system.error':
                // 系统错误
                this.emit('system_error', eventData)
                break
        }
    }
    
    // 发送消息
    send(message) {
        if (this.connected && this.ws) {
            try {
                const messageStr = typeof message === 'string' 
                    ? message 
                    : JSON.stringify(message)
                this.ws.send(messageStr)
                return true
            } catch (error) {
                console.error('发送WebSocket消息失败:', error)
                return false
            }
        } else {
            console.warn('WebSocket未连接，无法发送消息')
            return false
        }
    }
    
    // 发送心跳
    sendHeartbeat() {
        this.send({ type: 'ping', timestamp: Date.now() })
    }
    
    // 开始心跳
    startHeartbeat() {
        this.stopHeartbeat() // 清除之前的心跳
        this.heartbeatTimer = setInterval(() => {
            this.sendHeartbeat()
        }, this.heartbeatInterval)
    }
    
    // 停止心跳
    stopHeartbeat() {
        if (this.heartbeatTimer) {
            clearInterval(this.heartbeatTimer)
            this.heartbeatTimer = null
        }
    }
    
    // 安排重连
    scheduleReconnect() {
        if (this.reconnectTimer) {
            clearTimeout(this.reconnectTimer)
        }
        
        this.reconnectAttempts++
        const delay = this.reconnectInterval * this.reconnectAttempts
        
        console.log(`WebSocket将在${delay/1000}秒后尝试第${this.reconnectAttempts}次重连`)
        window.stateActions.addLog('info', `WebSocket将在${delay/1000}秒后尝试重连`)
        
        this.reconnectTimer = setTimeout(() => {
            this.connect()
        }, delay)
    }
    
    // 连接状态变化处理
    onConnectionChange(connected) {
        this.connected = connected
        
        // 更新全局状态
        window.stateActions.updateWSConnection(connected, this.ws)
    }
    
    // 注册消息处理器
    onMessage(type, handler) {
        this.messageHandlers.set(type, handler)
    }
    
    // 移除消息处理器
    offMessage(type) {
        this.messageHandlers.delete(type)
    }
    
    // 事件发射器（简单实现）
    emit(event, data) {
        // 这里可以实现一个简单的事件系统
        // 目前直接通过console输出
        console.log(`WebSocket事件 [${event}]:`, data)
    }
    
    // 断开连接
    disconnect() {
        this.stopHeartbeat()
        
        if (this.reconnectTimer) {
            clearTimeout(this.reconnectTimer)
            this.reconnectTimer = null
        }
        
        if (this.ws) {
            this.ws.close(1000, '手动断开')
            this.ws = null
        }
        
        this.connected = false
        this.reconnectAttempts = 0
        this.onConnectionChange(false)
    }
    
    // 获取连接状态
    isConnected() {
        return this.connected && this.ws && this.ws.readyState === WebSocket.OPEN
    }
}

// 全局WebSocket实例
window.WebSocketService = WebSocketService
window.wsService = new WebSocketService() 