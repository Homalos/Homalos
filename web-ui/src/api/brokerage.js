/**
 * 用户券商账户API
 * @module api/brokerage
 */
import request from './request'

/**
 * 创建用户券商账户
 * @param {Object} data - 券商账户数据
 * @param {string} data.account_name - 账户别名
 * @param {string} data.broker_code - 券商代码
 * @param {string} data.broker_name - 券商名称
 * @param {string} data.account_id - 资金账号
 * @param {string} data.investor_id - 投资者ID
 * @param {string} data.broker_id - 券商ID
 * @param {string} data.password - 交易密码（明文，后端会加密）
 * @param {string} [data.auth_code] - 授权码
 * @param {string} [data.app_id] - 应用ID
 * @param {string} [data.account_type='production'] - 账户类型：simulation/production
 * @param {string} [data.status='inactive'] - 账户状态：active/inactive/error
 * @param {boolean} [data.is_default=false] - 是否为默认账户
 * @returns {Promise<Object>} 创建的券商账户信息
 */
export function createBrokerage(data) {
  // 将password字段转换为password_encrypted（后端Service会处理加密）
  const requestData = {
    ...data,
    password_encrypted: data.password
  }
  delete requestData.password
  
  return request({
    url: '/user-brokerages',
    method: 'post',
    data: requestData
  })
}

/**
 * 获取用户券商账户列表
 * @param {Object} params - 查询参数
 * @param {boolean} [params.include_inactive=false] - 是否包含未激活账户
 * @returns {Promise<Object>} 券商账户列表
 */
export function getBrokerageList(params = {}) {
  return request({
    url: '/user-brokerages',
    method: 'get',
    params
  })
}

/**
 * 获取单个券商账户详情
 * @param {number} brokerageId - 券商账户ID
 * @returns {Promise<Object>} 券商账户详情
 */
export function getBrokerageDetail(brokerageId) {
  return request({
    url: `/user-brokerages/${brokerageId}`,
    method: 'get'
  })
}

/**
 * 更新券商账户
 * @param {number} brokerageId - 券商账户ID
 * @param {Object} data - 更新数据
 * @param {string} [data.account_name] - 账户别名
 * @param {string} [data.status] - 账户状态
 * @param {boolean} [data.is_default] - 是否为默认账户
 * @returns {Promise<Object>} 更新后的券商账户信息
 */
export function updateBrokerage(brokerageId, data) {
  return request({
    url: `/user-brokerages/${brokerageId}`,
    method: 'put',
    data
  })
}

/**
 * 删除券商账户
 * @param {number} brokerageId - 券商账户ID
 * @returns {Promise<Object>} 删除结果
 */
export function deleteBrokerage(brokerageId) {
  return request({
    url: `/user-brokerages/${brokerageId}`,
    method: 'delete'
  })
}

/**
 * 设置默认券商账户
 * @param {number} brokerageId - 券商账户ID
 * @returns {Promise<Object>} 更新结果
 */
export function setDefaultBrokerage(brokerageId) {
  return updateBrokerage(brokerageId, { is_default: true })
}

/**
 * 激活券商账户
 * @param {number} brokerageId - 券商账户ID
 * @returns {Promise<Object>} 更新结果
 */
export function activateBrokerage(brokerageId) {
  return updateBrokerage(brokerageId, { status: 'active' })
}

/**
 * 停用券商账户
 * @param {number} brokerageId - 券商账户ID
 * @returns {Promise<Object>} 更新结果
 */
export function deactivateBrokerage(brokerageId) {
  return updateBrokerage(brokerageId, { status: 'inactive' })
}
