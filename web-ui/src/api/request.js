import axios from 'axios'
import { ElMessage } from 'element-plus'

// 创建axios实例
const request = axios.create({
  baseURL: 'http://localhost:8000',
  timeout: 10000
  // 不设置默认Content-Type，让每个请求自己指定
})

// 请求拦截器
request.interceptors.request.use(
  config => {
    console.log('发送请求:', config.method?.toUpperCase(), config.url)
    console.log('请求头:', config.headers)
    
    // 从localStorage获取token
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    
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
          ElMessage.error('未授权，请重新登录')
          localStorage.removeItem('token')
          window.location.href = '/login'
          break
        case 403:
          ElMessage.error('权限不足')
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

