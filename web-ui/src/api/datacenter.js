import request from './request'

/**
 * 启动数据中心
 * @returns {Promise} 启动结果
 */
export function startDataCenter() {
  return request({
    url: '/api/datacenter/start',
    method: 'post',
    data: {}
  })
}

/**
 * 停止数据中心
 * @param {Boolean} force - 是否强制停止
 * @param {Number} timeout - 超时时间（秒）
 * @returns {Promise} 停止结果
 */
export function stopDataCenter(force = false, timeout = 30) {
  return request({
    url: '/api/datacenter/stop',
    method: 'post',
    data: { force, timeout }
  })
}

/**
 * 重启数据中心
 * @returns {Promise} 重启结果
 */
export function restartDataCenter() {
  return request({
    url: '/api/datacenter/restart',
    method: 'post'
  })
}

/**
 * 获取数据中心状态
 * @returns {Promise} 状态信息
 */
export function getDataCenterStatus() {
  return request({
    url: '/api/datacenter/status',
    method: 'get'
  })
}

/**
 * 获取数据中心日志
 * @param {Number} lines - 返回最后N行
 * @param {String} level - 日志级别 (all/INFO/WARNING/ERROR/DEBUG)
 * @param {Number} sinceLine - 从第N行之后开始读取（用于增量更新）
 * @returns {Promise} 日志信息
 */
export function getDataCenterLogs(lines = 100, level = 'all', sinceLine = null) {
  const params = { lines, level }
  if (sinceLine !== null) {
    params.since_line = sinceLine
  }
  return request({
    url: '/api/datacenter/logs',
    method: 'get',
    params
  })
}

/**
 * 获取数据中心配置
 * @returns {Promise} 配置信息
 */
export function getDataCenterConfig() {
  return request({
    url: '/api/datacenter/config',
    method: 'get'
  })
}

/**
 * 更新数据中心配置
 * @param {Object} config - 配置对象
 * @returns {Promise} 更新结果
 */
export function updateDataCenterConfig(config) {
  return request({
    url: '/api/datacenter/config',
    method: 'put',
    data: { config }
  })
}

