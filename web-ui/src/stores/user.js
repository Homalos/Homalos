import { defineStore } from 'pinia'
import { ref } from 'vue'
import { login as loginApi, getCurrentUser } from '@/api/auth'

export const useUserStore = defineStore('user', () => {
  const token = ref(localStorage.getItem('token') || '')
  const userInfo = ref(null)
  const isLoggedIn = ref(!!token.value)

  /**
   * 登录
   */
  async function login(loginForm) {
    try {
      const response = await loginApi(loginForm)
      token.value = response.access_token
      localStorage.setItem('token', response.access_token)
      isLoggedIn.value = true
      return true
    } catch (error) {
      return false
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
    logout,
    fetchUserInfo
  }
})

