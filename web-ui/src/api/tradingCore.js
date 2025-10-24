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
    },
    timeout: 30000  // 30秒超时（启动核心+连接网关需要较长时间）
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
    data: { force, timeout },
    timeout: 60000  // 60秒超时（后端停止操作可能需要30秒+缓冲时间）
  })
}

/**
 * 重启交易核心
 * @returns {Promise} 重启结果
 */
export function restartTradingCore() {
  return request({
    url: '/api/trading-core/restart',
    method: 'post',
    timeout: 90000  // 90秒超时（重启 = 停止 + 启动，需要更长时间）
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
    data: { broker_config: brokerConfig },
    timeout: 60000  // 60秒超时（CTP网关连接+登录可能需要较长时间）
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

/**
 * 获取运行中的策略数量
 * @returns {Promise} 策略数量
 */
export function getRunningStrategiesCount() {
  return request({
    url: '/api/trading-core/running-strategies-count',
    method: 'get'
  })
}

