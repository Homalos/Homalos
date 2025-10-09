/**
 * 任务调度相关工具函数
 */

/**
 * 计算下次执行时间
 * @param {Object} task - 任务对象
 * @returns {Date|null} 下次执行时间
 */
export const calculateNextRunTime = (task) => {
  if (task.status === 'disabled') return null
  
  const now = new Date()
  
  switch (task.type) {
    case 'minute': {
      const nextMinute = new Date(now)
      nextMinute.setMinutes(now.getMinutes() + 1)
      nextMinute.setSeconds(0, 0)
      return nextMinute
    }
    
    case 'daily': {
      const [hour, minute] = task.config.time.split(':')
      const todayTime = new Date(now)
      todayTime.setHours(parseInt(hour), parseInt(minute), 0, 0)
      if (todayTime > now) {
        return todayTime
      } else {
        const tomorrowTime = new Date(todayTime)
        tomorrowTime.setDate(todayTime.getDate() + 1)
        return tomorrowTime
      }
    }
    
    case 'once': {
      return new Date(task.config.dateTime)
    }
    
    case 'weekday': {
      const [hour, minute] = task.config.time.split(':')
      const currentDay = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'][now.getDay()]
      
      for (let i = 0; i <= 7; i++) {
        const checkDate = new Date(now)
        checkDate.setDate(now.getDate() + i)
        const checkDay = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'][checkDate.getDay()]
        
        if (task.config.dayOfWeek.includes(checkDay)) {
          checkDate.setHours(parseInt(hour), parseInt(minute), 0, 0)
          if (checkDate > now) {
            return checkDate
          }
        }
      }
      return null
    }
    
    case 'monthly': {
      const [hour, minute] = task.config.time.split(':')
      const currentDay = String(now.getDate()).padStart(2, '0')
      
      for (let i = 0; i < 62; i++) {
        const checkDate = new Date(now)
        checkDate.setDate(now.getDate() + i)
        const checkDay = String(checkDate.getDate()).padStart(2, '0')
        
        if (task.config.monthDay.includes(checkDay)) {
          checkDate.setHours(parseInt(hour), parseInt(minute), 0, 0)
          if (checkDate > now) {
            return checkDate
          }
        }
      }
      return null
    }
    
    default:
      return null
  }
}

/**
 * 格式化任务配置显示
 * @param {Object} task - 任务对象
 * @returns {string} 格式化后的配置描述
 */
export const formatTaskConfig = (task) => {
  switch (task.type) {
    case 'daily':
      return `每天 ${task.config.time}`
    case 'once':
      return task.config.dateTime
    case 'minute':
      return '每分钟执行'
    case 'weekday':
      return `每${task.config.dayOfWeek.join('、')} ${task.config.time}`
    case 'monthly':
      return `每月${task.config.monthDay.join('、')}号 ${task.config.time}`
    default:
      return '-'
  }
}

/**
 * 生成任务ID
 * @param {Array} tasks - 任务列表
 * @returns {number} 新的任务ID
 */
export const generateTaskId = (tasks) => {
  const maxId = tasks.reduce((max, t) => {
    return t.id > max ? t.id : max
  }, 0)
  return maxId + 1
}

