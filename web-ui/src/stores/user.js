import { defineStore } from 'pinia'
import { ref } from 'vue'
import { login as loginApi, getCurrentUser, register as registerApi } from '@/api/auth'
import { adminLogin, isAdminUsername } from '@/api/admin'

export const useUserStore = defineStore('user', () => {
  const token = ref(localStorage.getItem('token') || '')
  const userInfo = ref(null)
  const isLoggedIn = ref(!!token.value)

  /**
   * 登录 - 智能选择普通用户或管理员登录
   */
  async function login(loginForm) {
    try {
      let response
      
      // 检测是否为管理员用户名，优先尝试管理员登录
      if (isAdminUsername(loginForm.username)) {
        try {
          // 尝试管理员登录
          response = await adminLogin(loginForm)
          console.log('管理员登录成功')
        } catch (adminError) {
          console.log('管理员登录失败，尝试普通用户登录:', adminError.message)
          // 管理员登录失败，尝试普通用户登录
          response = await loginApi(loginForm)
          console.log('普通用户登录成功')
        }
      } else {
        try {
          // 尝试普通用户登录
          response = await loginApi(loginForm)
          console.log('普通用户登录成功')
        } catch (userError) {
          console.log('普通用户登录失败，尝试管理员登录:', userError.message)
          // 普通用户登录失败，尝试管理员登录
          response = await adminLogin(loginForm)
          console.log('管理员登录成功')
        }
      }
      
      token.value = response.access_token
      localStorage.setItem('token', response.access_token)
      isLoggedIn.value = true
      return true
    } catch (error) {
      console.error('登录失败:', error.message)
      return false
    }
  }

  /**
   * 注册
   */
  async function register(registerForm) {
    try {
      const response = await registerApi({
        username: registerForm.username,
        password: registerForm.password,
        email: registerForm.email || null,
        full_name: registerForm.full_name || null,
        role: 'admin'  // 默认注册管理员角色
      })
      return { success: true, user: response }
    } catch (error) {
      return { 
        success: false, 
        message: error.response?.data?.detail || '注册失败' 
      }
    }
  }

  /**
   * 登出
   */
  function logout() {
    token.value = ''
    userInfo.value = null
    isLoggedIn.value = false
    localStorage.removeItem('token')
  }

  /**
   * 获取用户信息
   */
  async function fetchUserInfo() {
    try {
      const response = await getCurrentUser()
      userInfo.value = response
      return true
    } catch (error) {
      return false
    }
  }

  return {
    token,
    userInfo,
    isLoggedIn,
    login,
    register,
    logout,
    fetchUserInfo
  }
})

