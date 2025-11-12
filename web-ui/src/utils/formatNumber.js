/**
 * 数字格式化工具函数
 */

/**
 * 格式化大数字，自动选择合适的单位
 * @param {number} num - 要格式化的数字
 * @param {number} precision - 小数位数，默认2位
 * @returns {string} 格式化后的字符串
 * 
 * 示例：
 * formatLargeNumber(1234) => "1,234"
 * formatLargeNumber(12345) => "1.23万"
 * formatLargeNumber(1234567) => "123.46万"
 * formatLargeNumber(12345678) => "1,234.57万"
 * formatLargeNumber(123456789) => "1.23亿"
 */
export function formatLargeNumber(num, precision = 2) {
  if (num === null || num === undefined || isNaN(num)) {
    return '0'
  }

  const absNum = Math.abs(num)
  const sign = num < 0 ? '-' : ''

  // 小于1万，直接显示并添加千分位分隔符
  if (absNum < 10000) {
    return sign + absNum.toLocaleString('zh-CN', {
      minimumFractionDigits: 0,
      maximumFractionDigits: precision
    })
  }
  
  // 1万到1亿之间，显示为"万"
  if (absNum < 100000000) {
    const wanValue = absNum / 10000
    return sign + wanValue.toFixed(precision) + '万'
  }
  
  // 1亿以上，显示为"亿"
  const yiValue = absNum / 100000000
  return sign + yiValue.toFixed(precision) + '亿'
}

/**
 * 格式化金额，带货币符号
 * @param {number} amount - 金额
 * @param {string} currency - 货币符号，默认'¥'
 * @param {number} precision - 小数位数，默认2位
 * @returns {string} 格式化后的金额字符串
 */
export function formatCurrency(amount, currency = '¥', precision = 2) {
  const formattedNumber = formatLargeNumber(amount, precision)
  return currency + formattedNumber
}

/**
 * 格式化百分比
 * @param {number} value - 数值
 * @param {number} precision - 小数位数，默认2位
 * @returns {string} 格式化后的百分比字符串
 */
export function formatPercentage(value, precision = 2) {
  if (value === null || value === undefined || isNaN(value)) {
    return '0.00%'
  }
  return value.toFixed(precision) + '%'
}

/**
 * 智能格式化数字（根据数字大小自动选择最佳显示方式）
 * @param {number} num - 要格式化的数字
 * @param {object} options - 选项
 * @param {number} options.precision - 小数位数
 * @param {boolean} options.showSign - 是否显示正负号
 * @param {string} options.currency - 货币符号
 * @returns {string} 格式化后的字符串
 */
export function smartFormatNumber(num, options = {}) {
  const {
    precision = 2,
    showSign = false,
    currency = ''
  } = options

  if (num === null || num === undefined || isNaN(num)) {
    return currency + '0'
  }

  let result = formatLargeNumber(num, precision)
  
  // 添加正号（如果需要且为正数）
  if (showSign && num > 0) {
    result = '+' + result
  }
  
  // 添加货币符号
  if (currency) {
    result = currency + result
  }
  
  return result
}
