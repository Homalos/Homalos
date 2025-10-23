import request from './request'

/**
 * 启动交易系统
 * @returns {Promise} 启动结果
 */
export function startTradingSystem() {
  return request({
    url: '/api/trading-system/start',
    method: 'post',
    data: {}
  })
}

/**
 * 停止交易系统
 * @param {Boolean} force - 是否强制停止
 * @param {Number} timeout - 超时时间（秒）
 * @returns {Promise} 停止结果
 */
export function stopTradingSystem(force = false, timeout = 30) {
  return request({
    url: '/api/trading-system/stop',
    method: 'post',
    data: { force, timeout }
  })
}

/**
 * 重启交易系统
 * @returns {Promise} 重启结果
 */
export function restartTradingSystem() {
  return request({
    url: '/api/trading-system/restart',
    method: 'post'
  })
}

/**
 * 获取交易系统状态
 * @returns {Promise} 状态信息
 */
export function getTradingSystemStatus() {
  return request({
    url: '/api/trading-system/status',
    method: 'get'
  })
}

/**
 * 获取交易系统日志
 * @param {Number} lines - 返回最后N行
 * @param {String} level - 日志级别 (all/INFO/WARNING/ERROR/DEBUG)
 * @param {Number} sinceLine - 从第N行之后开始读取（用于增量更新）
 * @returns {Promise} 日志信息
 */
export function getTradingSystemLogs(lines = 100, level = 'all', sinceLine = null) {
  const params = { lines, level }
  if (sinceLine !== null) {
    params.since_line = sinceLine
  }
  return request({
    url: '/api/trading-system/logs',
    method: 'get',
    params
  })
}

