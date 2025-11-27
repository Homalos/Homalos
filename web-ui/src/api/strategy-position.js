#!/usr/bin/env node
/**
 * @ProjectName: Homalos
 * @FileName   : strategy-position.js
 * @Date       : 2025/11/27
 * @Author     : Lumosylva
 * @Email      : donnymoving@gmail.com
 * @Software   : WebStorm
 * @Description: 策略持仓 API 调用方法
 */

import request from './request'

/**
 * 获取策略当前持仓
 * @param {number} strategyId - 策略ID
 * @returns {Promise}
 */
export function getStrategyPositions(strategyId) {
  return request({
    url: `/api/strategies-db/${strategyId}/positions`,
    method: 'get'
  })
}

/**
 * 获取策略历史持仓
 * @param {number} strategyId - 策略ID
 * @param {number} limit - 返回的最大记录数（默认100）
 * @returns {Promise}
 */
export function getStrategyPositionHistory(strategyId, limit = 100) {
  return request({
    url: `/api/strategies-db/${strategyId}/positions/history`,
    method: 'get',
    params: {
      limit
    }
  })
}

/**
 * 获取持仓同步统计信息
 * @returns {Promise}
 */
export function getPositionSyncStats() {
  return request({
    url: '/api/position-sync/stats',
    method: 'get'
  })
}

export default {
  getStrategyPositions,
  getStrategyPositionHistory,
  getPositionSyncStats
}
