/**
 * 用户管理API
 */
import request from './request'

/**
 * 获取用户列表
 * @param {Object} params - 查询参数
 * @param {Number} params.page - 页码
 * @param {Number} params.page_size - 每页数量
 * @param {String} params.search - 搜索关键词
 * @param {String} params.status - 状态筛选
 * @param {String} params.role - 角色筛选
 * @returns {Promise}
 */
export function getUsersList(params) {
  return request({
    url: '/api/users',
    method: 'get',
    params
  })
}

/**
 * 获取用户详情
 * @param {Number} userId - 用户ID
 * @returns {Promise}
 */
export function getUserDetail(userId) {
  return request({
    url: `/api/users/${userId}`,
    method: 'get'
  })
}

/**
 * 创建用户
 * @param {Object} data - 用户数据
 * @returns {Promise}
 */
export function createUser(data) {
  return request({
    url: '/api/users',
    method: 'post',
    data
  })
}

/**
 * 更新用户信息
 * @param {Number} userId - 用户ID
 * @param {Object} data - 更新数据
 * @returns {Promise}
 */
export function updateUser(userId, data) {
  return request({
    url: `/api/users/${userId}`,
    method: 'put',
    data
  })
}

/**
 * 更新用户状态
 * @param {Number} userId - 用户ID
 * @param {String} status - 新状态
 * @returns {Promise}
 */
export function updateUserStatus(userId, status) {
  return request({
    url: `/api/users/${userId}/status`,
    method: 'put',
    data: { status }
  })
}

/**
 * 更新用户角色
 * @param {Number} userId - 用户ID
 * @param {String} role - 新角色
 * @returns {Promise}
 */
export function updateUserRole(userId, role) {
  return request({
    url: `/api/users/${userId}/role`,
    method: 'put',
    data: { role }
  })
}

/**
 * 重置用户密码
 * @param {Number} userId - 用户ID
 * @param {String} newPassword - 新密码
 * @returns {Promise}
 */
export function resetUserPassword(userId, newPassword) {
  return request({
    url: `/api/users/${userId}/password`,
    method: 'put',
    data: { new_password: newPassword }
  })
}

/**
 * 删除用户
 * @param {Number} userId - 用户ID
 * @returns {Promise}
 */
export function deleteUser(userId) {
  return request({
    url: `/api/users/${userId}`,
    method: 'delete'
  })
}
