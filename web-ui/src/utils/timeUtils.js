/**
 * 时间处理工具函数
 */

/**
 * 获取格式化的当前时间
 * @returns {string} 格式化后的时间字符串 (YYYY-MM-DD HH:mm:ss)
 */
export const getCurrentTime = () => {
  return new Date().toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false
  }).replace(/\//g, '-')
}

/**
 * 获取相对时间显示
 * @param {Date} targetTime - 目标时间
 * @returns {string} 相对时间描述
 */
export const getRelativeTime = (targetTime) => {
  if (!targetTime) return '-'
  
  const now = new Date()
  const diff = targetTime - now
  const minutes = Math.floor(diff / 60000)
  const hours = Math.floor(diff / 3600000)
  const days = Math.floor(diff / 86400000)
  
  if (minutes < 0) return '已过期'
  if (minutes < 1) return '即将执行'
  if (minutes < 60) return `${minutes}分钟后`
  if (hours < 24) {
    if (hours < 1) return `${minutes}分钟后`
    return `${hours}小时后`
  }
  if (days === 0) {
    return `今天 ${targetTime.toLocaleTimeString('zh-CN', {hour: '2-digit', minute: '2-digit'})}`
  }
  if (days === 1) {
    return `明天 ${targetTime.toLocaleTimeString('zh-CN', {hour: '2-digit', minute: '2-digit'})}`
  }
  
  return targetTime.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

