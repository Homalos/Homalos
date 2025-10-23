import request from './request'

/**
 * 启动交易核心
 * @param {Object} config - 核心配置（可选）
 * @param {Boolean} autoConnectGateway - 是否自动连接网关
 * @returns {Promise} 启动结果
 */
export function startTradingCore(config = null, autoConnectGateway = false) {
  return request({
    url: '/api/trading-core/start',
    method: 'post',
    data: { 
      config, 
      auto_connect_gateway: autoConnectGateway 
    }
  })
}

/**
 * 停止交易核心
 * @param {Boolean} force - 是否强制停止
 * @param {Number} timeout - 超时时间（秒）
 * @returns {Promise} 停止结果
 */
export function stopTradingCore(force = false, timeout = 30) {
  return request({
    url: '/api/trading-core/stop',
    method: 'post',
    data: { force, timeout }
  })
}

/**
 * 重启交易核心
 * @returns {Promise} 重启结果
 */
export function restartTradingCore() {
  return request({
    url: '/api/trading-core/restart',
    method: 'post'
  })
}

/**
 * 获取交易核心状态
 * @returns {Promise} 状态信息
 */
export function getTradingCoreStatus() {
  return request({
    url: '/api/trading-core/status',
    method: 'get'
  })
}

/**
 * 连接CTP网关
 * @param {Object} brokerConfig - 经纪商配置（可选）
 * @returns {Promise} 连接结果
 */
export function connectGateway(brokerConfig = null) {
  return request({
    url: '/api/trading-core/gateway/connect',
    method: 'post',
    data: { broker_config: brokerConfig }
  })
}

/**
 * 断开CTP网关
 * @returns {Promise} 断开结果
 */
export function disconnectGateway() {
  return request({
    url: '/api/trading-core/gateway/disconnect',
    method: 'post'
  })
}

/**
 * 获取核心模块列表
 * @returns {Promise} 模块列表
 */
export function getCoreModules() {
  return request({
    url: '/api/trading-core/modules',
    method: 'get'
  })
}

