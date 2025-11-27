/**
 * @ProjectName: Homalos
 * @FileName   : websocket.js
 * @Date       : 2025/11/27
 * @Author     : Lumosylva
 * @Email      : donnymoving@gmail.com
 * @Software   : WebStorm
 * @Description: WebSocket 客户端工具
 */

class WebSocketClient {
  constructor(url) {
    this.url = url
    this.ws = null
    this.reconnectAttempts = 0
    this.maxReconnectAttempts = 5
    this.reconnectDelay = 3000
    this.messageHandlers = new Map()
    this.isConnected = false
  }

  /**
   * 连接到 WebSocket 服务器
   */
  connect() {
    return new Promise((resolve, reject) => {
      try {
        this.ws = new WebSocket(this.url)

        this.ws.onopen = () => {
          console.log('[WebSocket] 已连接到服务器:', this.url)
          this.isConnected = true
          this.reconnectAttempts = 0
          resolve()
        }

        this.ws.onmessage = (event) => {
          try {
            const message = JSON.parse(event.data)
            this.handleMessage(message)
          } catch (error) {
            console.error('[WebSocket] 消息解析失败:', error)
          }
        }

        this.ws.onerror = (error) => {
          console.error('[WebSocket] 连接错误:', error)
          this.isConnected = false
          reject(error)
        }

        this.ws.onclose = () => {
          console.log('[WebSocket] 连接已关闭')
          this.isConnected = false
          this.attemptReconnect()
        }
      } catch (error) {
        reject(error)
      }
    })
  }

  /**
   * 尝试重新连接
   */
  attemptReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++
      const delay = this.reconnectDelay * this.reconnectAttempts
      console.log(`[WebSocket] 将在 ${delay}ms 后尝试重新连接 (${this.reconnectAttempts}/${this.maxReconnectAttempts})`)
      
      setTimeout(() => {
        this.connect().catch((error) => {
          console.error('[WebSocket] 重新连接失败:', error)
        })
      }, delay)
    } else {
      console.error('[WebSocket] 达到最大重连次数，放弃重连')
    }
  }

  /**
   * 处理服务器消息
   */
  handleMessage(message) {
    const { type, strategy_id, data } = message

    // 调用对应类型的处理器
    if (this.messageHandlers.has(type)) {
      const handlers = this.messageHandlers.get(type)
      handlers.forEach((handler) => {
        try {
          handler({ strategy_id, data })
        } catch (error) {
          console.error(`[WebSocket] 消息处理器执行失败 (${type}):`, error)
        }
      })
    }
  }

  /**
   * 订阅消息类型
   */
  on(type, handler) {
    if (!this.messageHandlers.has(type)) {
      this.messageHandlers.set(type, [])
    }
    this.messageHandlers.get(type).push(handler)
  }

  /**
   * 取消订阅消息类型
   */
  off(type, handler) {
    if (this.messageHandlers.has(type)) {
      const handlers = this.messageHandlers.get(type)
      const index = handlers.indexOf(handler)
      if (index > -1) {
        handlers.splice(index, 1)
      }
    }
  }

  /**
   * 发送消息
   */
  send(message) {
    if (!this.isConnected) {
      console.error('[WebSocket] 未连接，无法发送消息')
      return false
    }

    try {
      this.ws.send(JSON.stringify(message))
      return true
    } catch (error) {
      console.error('[WebSocket] 发送消息失败:', error)
      return false
    }
  }

  /**
   * 订阅策略持仓更新
   */
  subscribeStrategy(strategyId) {
    return this.send({
      type: 'subscribe',
      strategy_id: strategyId
    })
  }

  /**
   * 取消订阅策略持仓更新
   */
  unsubscribeStrategy(strategyId) {
    return this.send({
      type: 'unsubscribe',
      strategy_id: strategyId
    })
  }

  /**
   * 心跳检测
   */
  ping() {
    return this.send({
      type: 'ping'
    })
  }

  /**
   * 断开连接
   */
  disconnect() {
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
    this.isConnected = false
  }
}

export default WebSocketClient
