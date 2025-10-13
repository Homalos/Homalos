import request from './request'

/**
 * 登录资金账户
 * @param {Object} data - 登录数据
 * @param {number} data.account_id - 账户ID（已有账户）
 * @param {string} data.broker_id - 券商ID（新账户）
 * @param {string} data.account_number - 资金账号（新账户）
 * @param {string} data.password - 密码
 * @param {boolean} data.remember - 记住账户
 */
export function loginTradingAccount(data) {
  return request({
    url: '/api/trading-account/login',
    method: 'post',
    data
  })
}

/**
 * 登出资金账户
 */
export function logoutTradingAccount() {
  return request({
    url: '/api/trading-account/logout',
    method: 'post'
  })
}

/**
 * 获取资金账户登录状态
 */
export function getTradingAccountStatus() {
  return request({
    url: '/api/trading-account/status',
    method: 'get'
  })
}

/**
 * 获取账户列表
 */
export function getTradingAccountList() {
  return request({
    url: '/api/trading-account/list',
    method: 'get'
  })
}

/**
 * 添加资金账户
 * @param {Object} data - 账户数据
 */
export function addTradingAccount(data) {
  return request({
    url: '/api/trading-account',
    method: 'post',
    data
  })
}

/**
 * 更新资金账户
 * @param {number} id - 账户ID
 * @param {Object} data - 更新数据
 */
export function updateTradingAccount(id, data) {
  return request({
    url: `/api/trading-account/${id}`,
    method: 'put',
    data
  })
}

/**
 * 删除资金账户
 * @param {number} id - 账户ID
 */
export function deleteTradingAccount(id) {
  return request({
    url: `/api/trading-account/${id}`,
    method: 'delete'
  })
}

/**
 * 切换账户
 * @param {number} id - 账户ID
 */
export function switchTradingAccount(id) {
  return request({
    url: `/api/trading-account/${id}/switch`,
    method: 'post'
  })
}

/**
 * 修改密码
 * @param {number} id - 账户ID
 * @param {Object} data - 密码数据
 */
export function changeTradingAccountPassword(id, data) {
  return request({
    url: `/api/trading-account/${id}/password`,
    method: 'put',
    data
  })
}

/**
 * 获取券商列表
 */
export function getBrokers() {
  return request({
    url: '/api/trading-account/brokers',
    method: 'get'
  })
}

