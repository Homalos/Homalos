/**
 * 常量定义
 */

// 日志级别映射
export const logLevelMap = {
  info: { name: '信息', color: 'info' },
  success: { name: '成功', color: 'success' },
  warning: { name: '警告', color: 'warning' },
  error: { name: '错误', color: 'danger' }
}

// 任务类型映射
export const taskTypeMap = {
  daily: { name: '每日任务', color: '#409EFF' },
  once: { name: '一次性任务', color: '#67C23A' },
  minute: { name: '每分钟任务', color: '#E6A23C' },
  weekday: { name: '每周任务', color: '#F56C6C' },
  monthly: { name: '每月任务', color: '#909399' }
}

// 星期映射
export const weekDayMap = {
  '周一': 'Mon', '周二': 'Tue', '周三': 'Wed', 
  '周四': 'Thu', '周五': 'Fri', '周六': 'Sat', '周日': 'Sun'
}

// 委托状态映射
export const orderStatusMap = {
  submitted: { name: '已报', color: 'info' },
  partiallyFilled: { name: '部分成交', color: 'warning' },
  filled: { name: '全部成交', color: 'success' },
  cancelled: { name: '已撤单', color: '' },
  rejected: { name: '废单', color: 'danger' }
}

// 委托类型映射
export const orderTypeMap = {
  limit: { name: '限价', color: 'primary' },
  market: { name: '市价', color: 'success' },
  conditional: { name: '条件单', color: 'warning' }
}

