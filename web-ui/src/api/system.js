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

