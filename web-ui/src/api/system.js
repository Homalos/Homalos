import request from './request'

/**
 * 获取系统基础信息
 * @returns {Promise} 系统基础信息
 */
export function getSystemInfo() {
  return request({
    url: '/api/system-config/info',
    method: 'get'
  })
}

/**
 * 获取系统配置
 * @returns {Promise} 系统配置数据
 */
export function getSystemConfig() {
  return request({
    url: '/api/system-config',
    method: 'get'
  })
}

/**
 * 更新系统配置
 * @param {Object} config - 配置对象
 * @param {boolean} config.dev_mode - 开发模式
 * @param {boolean} config.dev_trading_hours_check - 交易时间检查
 * @returns {Promise} 更新结果
 */
export function updateSystemConfig(config) {
  return request({
    url: '/api/system-config',
    method: 'put',
    data: config
  })
}

/**
 * 获取通知配置
 * @returns {Promise} 通知配置数据
 */
export function getNotificationConfig() {
  return request({
    url: '/api/system-config/notification',
    method: 'get'
  })
}

/**
 * 更新通知配置
 * @param {Object} config - 通知配置对象
 * @param {Object} config.dingtalk - 钉钉配置
 * @param {Object} config.wecom - 企业微信配置
 * @param {Object} config.email - 邮件配置
 * @returns {Promise} 更新结果
 */
export function updateNotificationConfig(config) {
  return request({
    url: '/api/system-config/notification',
    method: 'put',
    data: config
  })
}

/**
 * 获取日志配置
 * @returns {Promise} 日志配置数据
 */
export function getLoggingConfig() {
  return request({
    url: '/api/system-config/logging',
    method: 'get'
  })
}

/**
 * 更新日志配置
 * @param {Object} config - 日志配置对象
 * @param {boolean} config.is_debug - 是否开启debug模式
 * @param {string} config.level - 日志级别
 * @param {string} config.rotation - 单个日志文件大小上限
 * @param {string} config.retention - 日志保留时间
 * @param {string} config.compression - 日志文件压缩格式
 * @returns {Promise} 更新结果
 */
export function updateLoggingConfig(config) {
  return request({
    url: '/api/system-config/logging',
    method: 'put',
    data: config
  })
}

