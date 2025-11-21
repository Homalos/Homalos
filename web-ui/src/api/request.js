import axios from 'axios'
import { ElMessage } from 'element-plus'

/**
 * 检查是否为资金账户相关API
 * @param {string} url - 请求URL
 * @returns {boolean} 是否为资金账户API
 */
function isTradingAccountAPI(url) {
  return url && url.includes('/api/trading-account')
}

/**
 * 检查是否为登录相关API
 * @param {string} url - 请求URL
 * @returns {boolean} 是否为登录API
 */
function isLoginAPI(url) {
  return url && (url.includes('/api/auth/login') || url.includes('/api/admin/auth/login'))
}

// 创建axios实例
const request = axios.create({
  baseURL: 'http://localhost:8000',
  timeout: 10000
  // 不设置默认Content-Type，让每个请求自己指定
})

// 请求拦截器
request.interceptors.request.use(
  config => {
    // 从localStorage获取token并添加到请求头
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    
    // 打印请求日志
    console.log('发送请求:', config.method?.toUpperCase(), config.url)
    
    // 优化请求头日志输出
    const headersToLog = {
      Accept: config.headers.Accept,
      Authorization: config.headers.Authorization ? '***' : undefined
    }
    // 只在有Content-Type时才显示
    if (config.headers['Content-Type']) {
      headersToLog['Content-Type'] = config.headers['Content-Type']
    }
    console.log('请求头:', headersToLog)
    
    // 如果没有设置Content-Type，axios会自动设置
    // 对于URLSearchParams，会自动设置为application/x-www-form-urlencoded
    // 对于普通对象，会自动设置为application/json
    
    return config
  },
  error => {
    console.error('请求错误:', error)
    return Promise.reject(error)
  }
)

// 响应拦截器
request.interceptors.response.use(
  response => {
    console.log('收到响应:', response.status, response.config.url)
    console.log('响应数据:', response.data)
    return response.data
  },
  error => {
    console.error('API请求错误:', error)
    
    if (error.response) {
      const { status, data } = error.response
      console.error('错误状态:', status, '错误数据:', data)
      
      switch (status) {
        case 401:
          console.error('❌ 401错误 - URL:', error.config.url)
          console.error('❌ 401错误 - 详情:', data.detail)
          
          // 检查是否是登录API
          const isLoginRequest = isLoginAPI(error.config.url)
          
          // 检查是否是资金账户或券商账户相关API
          const isBrokerageAPI = error.config.url && (
            error.config.url.includes('/api/trading-account') ||
            error.config.url.includes('/api/user-brokerages')
          )
          
          if (isLoginRequest) {
            // 登录API的401错误：不显示错误信息，让userStore统一处理
            // 避免智能登录机制的重复提示
          } else if (isBrokerageAPI) {
            // 资金账户/券商账户相关API的401错误：不显示提示，让组件自己处理
            // 不调用 ElMessage.error，避免重复提示
          } else {
            // 其他API的401错误：跳转登录页面
            ElMessage.error('登录已过期，请重新登录')
            localStorage.removeItem('token')
            window.location.href = '/login'
          }
          break
        case 403:
          // 检查是否是券商账户相关API
          const isBrokerageAPI403 = error.config.url && (
            error.config.url.includes('/api/trading-account') ||
            error.config.url.includes('/api/user-brokerages')
          )
          
          if (isBrokerageAPI403) {
            // 券商账户相关API的403错误：不显示通用提示，让组件自己处理具体错误
            // 例如"账户未激活"等业务错误
          } else {
            // 其他API的403错误：显示权限不足
            ElMessage.error('权限不足')
          }
          break
        case 409:
          // 409 Conflict - 业务冲突错误（如账户已存在）
          // 不在这里显示错误，让组件自己处理
          break
        case 422:
          // FastAPI验证错误
          const errorMsg = data.detail?.[0]?.msg || data.detail || '请求参数错误'
          ElMessage.error(errorMsg)
          break
        case 500:
          ElMessage.error('服务器错误')
          break
        default:
          ElMessage.error(data.detail || '请求失败')
      }
    } else if (error.request) {
      // 请求已发出，但没有收到响应
      console.error('无响应:', error.request)
      ElMessage.error('网络错误，请检查连接')
    } else {
      // 设置请求时发生错误
      console.error('请求配置错误:', error.message)
      ElMessage.error('请求配置错误: ' + error.message)
    }
    return Promise.reject(error)
  }
)

export default request

