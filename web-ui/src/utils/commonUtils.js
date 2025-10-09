/**
 * 通用工具函数
 */

/**
 * 添加日志到日志列表
 * @param {Object} logsRef - 日志列表的 ref 对象
 * @param {string} level - 日志级别
 * @param {string} category - 日志分类
 * @param {string} message - 日志消息
 * @param {Object} details - 日志详情
 * @param {Function} getCurrentTime - 获取当前时间的函数
 */
export const addLog = (logsRef, level, category, message, details = {}, getCurrentTime) => {
  const newLog = {
    id: logsRef.value.length > 0 
      ? Math.max(...logsRef.value.map(l => l.id)) + 1 
      : 1,
    timestamp: getCurrentTime(),
    level,
    category,
    message,
    details
  }
  logsRef.value.unshift(newLog) // 添加到开头
  
  // 限制日志数量（最多保留100条）
  if (logsRef.value.length > 100) {
    logsRef.value = logsRef.value.slice(0, 100)
  }
}

