import request from './request'

/**
 * 管理员登录
 * @param {Object} data - 登录数据
 * @param {string} data.username - 用户名/邮箱/手机号
 * @param {string} data.password - 密码
 * @param {string} data.mfa_code - MFA验证码（可选）
 */
export function adminLogin(data) {
  return request({
    url: '/api/admin/auth/login',
    method: 'post',
    data: {
      username_or_email_or_phone: data.username,
      password: data.password,
      mfa_code: data.mfa_code || null
    },
    headers: {
      'Content-Type': 'application/json'
    }
  })
}

/**
 * 管理员注册
 * @param {Object} data - 注册数据
 */
export function adminRegister(data) {
  return request({
    url: '/api/admin/auth/register',
    method: 'post',
    data,
    headers: {
      'Content-Type': 'application/json'
    }
  })
}

/**
 * 检查用户名是否为管理员
 * 这是一个简单的检测方法，可以根据实际需求调整
 * @param {string} username - 用户名
 * @returns {boolean} - 是否为管理员账户
 */
export function isAdminUsername(username) {
  // 管理员用户名通常包含admin、超级管理员等特征
  const adminPatterns = [
    /admin/i,           // 包含admin的用户名
    /超级/,              // 包含"超级"的用户名
    /管理员/,            // 包含"管理员"的用户名
    /root/i,            // 系统管理员
    /supervisor/i,      // 监管员
    /manager/i          // 管理者
  ]
  
  return adminPatterns.some(pattern => pattern.test(username))
}
