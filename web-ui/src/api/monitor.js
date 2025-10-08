import request from './request'

/**
 * 获取系统监控数据
 * @returns {Promise} 系统监控数据
 */
export function getSystemStats() {
  return request({
    url: '/api/monitor/system',
    method: 'get'
  })
}

