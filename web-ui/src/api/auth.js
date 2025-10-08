import request from './request'

/**
 * 用户登录
 * @param {Object} data - 登录数据
 * @param {string} data.username - 用户名
 * @param {string} data.password - 密码
 */
export function login(data) {
  // FastAPI的OAuth2PasswordRequestForm需要使用application/x-www-form-urlencoded格式
  const formData = new URLSearchParams()
  formData.append('username', data.username)
  formData.append('password', data.password)
  
  return request({
    url: '/api/auth/login',
    method: 'post',
    data: formData,
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded'
    }
  })
}

/**
 * 用户注册
 * @param {Object} data - 注册数据
 */
export function register(data) {
  return request({
    url: '/api/auth/register',
    method: 'post',
    data,
    headers: {
      'Content-Type': 'application/json'
    }
  })
}

/**
 * 获取当前用户信息
 */
export function getCurrentUser() {
  return request({
    url: '/api/auth/me',
    method: 'get'
  })
}

