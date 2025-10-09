/**
 * 策略相关工具函数
 */

/**
 * 生成唯一的策略ID
 * @param {Array} strategies - 策略列表
 * @returns {string} 新的策略ID (格式: STR001)
 */
export const generateStrategyId = (strategies) => {
  const maxId = strategies.reduce((max, s) => {
    const num = parseInt(s.id.replace('STR', ''))
    return num > max ? num : max
  }, 0)
  return `STR${String(maxId + 1).padStart(3, '0')}`
}

/**
 * 计算策略的总浮动盈亏
 * @param {Object} strategy - 策略对象
 * @returns {number} 总浮动盈亏金额
 */
export const getTotalProfitLoss = (strategy) => {
  if (!strategy.positions || strategy.positions.length === 0) {
    return 0
  }
  return strategy.positions.reduce((total, position) => {
    return total + (position.profitLoss || 0)
  }, 0)
}

/**
 * 获取风险等级标签类型
 * @param {string} level - 风险等级 (低/中/高)
 * @returns {string} Element Plus Tag 类型
 */
export const getRiskLevelType = (level) => {
  const typeMap = {
    '低': 'success',
    '中': 'warning',
    '高': 'danger'
  }
  return typeMap[level] || 'info'
}

/**
 * 获取通知标签类型
 * @param {string} level - 通知级别 (紧急/重要/通知)
 * @returns {string} Element Plus Tag 类型
 */
export const getNotificationTagType = (level) => {
  const typeMap = {
    '紧急': 'danger',
    '重要': 'warning',
    '通知': 'info'
  }
  return typeMap[level] || 'info'
}

