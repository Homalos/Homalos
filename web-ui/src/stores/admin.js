import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useAdminStore = defineStore('admin', () => {
  // 状态
  const adminInfo = ref(null)
  const isLoggedIn = ref(false)
  const token = ref(localStorage.getItem('admin_token') || null)

  // 管理员注册
  const register = async (registerData) => {
    try {
      const response = await fetch('/api/admin/auth/register', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(registerData)
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || '注册失败')
      }

      return {
        success: true,
        data: data,
        message: '管理员注册成功'
      }
    } catch (error) {
      console.error('管理员注册失败:', error)
      return {
        success: false,
        message: error.message || '注册失败，请稍后重试'
      }
    }
  }

  // 管理员登录
  const login = async (loginData) => {
    try {
      const formData = new FormData()
      formData.append('username', loginData.username)
      formData.append('password', loginData.password)

      const response = await fetch('/api/admin/auth/login', {
        method: 'POST',
        body: formData
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || '登录失败')
      }

      // 保存token和管理员信息
      token.value = data.access_token
      adminInfo.value = data.admin_info
      isLoggedIn.value = true

      // 存储到localStorage
      localStorage.setItem('admin_token', data.access_token)
      localStorage.setItem('admin_info', JSON.stringify(data.admin_info))

      return {
        success: true,
        data: data
      }
    } catch (error) {
      console.error('管理员登录失败:', error)
      return {
        success: false,
        message: error.message || '登录失败，请稍后重试'
      }
    }
  }

  // 管理员登出
  const logout = async () => {
    try {
      if (token.value) {
        await fetch('/api/admin/auth/logout', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token.value}`
          }
        })
      }
    } catch (error) {
      console.error('管理员登出失败:', error)
    } finally {
      // 清除状态
      token.value = null
      adminInfo.value = null
      isLoggedIn.value = false

      // 清除localStorage
      localStorage.removeItem('admin_token')
      localStorage.removeItem('admin_info')
    }
  }

  // 获取当前管理员信息
  const getCurrentAdmin = async () => {
    if (!token.value) return false

    try {
      const response = await fetch('/api/admin/auth/me', {
        headers: {
          'Authorization': `Bearer ${token.value}`
        }
      })

      if (!response.ok) {
        throw new Error('获取管理员信息失败')
      }

      const data = await response.json()
      adminInfo.value = data
      isLoggedIn.value = true

      return true
    } catch (error) {
      console.error('获取管理员信息失败:', error)
      // 清除无效token
      await logout()
      return false
    }
  }

  // 初始化（从localStorage恢复状态）
  const initialize = async () => {
    const savedToken = localStorage.getItem('admin_token')
    const savedAdminInfo = localStorage.getItem('admin_info')

    if (savedToken && savedAdminInfo) {
      token.value = savedToken
      try {
        adminInfo.value = JSON.parse(savedAdminInfo)
        isLoggedIn.value = true
        
        // 验证token是否仍然有效
        await getCurrentAdmin()
      } catch (error) {
        console.error('初始化管理员状态失败:', error)
        await logout()
      }
    }
  }

  return {
    // 状态
    adminInfo,
    isLoggedIn,
    token,
    
    // 方法
    register,
    login,
    logout,
    getCurrentAdmin,
    initialize
  }
})
