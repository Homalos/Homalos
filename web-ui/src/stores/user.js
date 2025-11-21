import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { login as loginApi, getCurrentUser, register as registerApi } from '@/api/auth'
import { adminLogin, isAdminUsername } from '@/api/admin'
import { ElMessage } from 'element-plus'

export const useUserStore = defineStore('user', () => {
  const token = ref(localStorage.getItem('token') || '')
  const userInfo = ref(null)
  const isLoggedIn = ref(!!token.value)
  
  // 计算属性：是否为管理员
  const isAdmin = computed(() => {
    if (!userInfo.value) return false
    // 检查是否为Admin对象（有admin_id）或User对象且role为admin
    return userInfo.value.admin_id !== undefined || userInfo.value.role === 'admin'
  })

  /**
   * 登录 - 智能选择普通用户或管理员登录
   */
  async function login(loginForm) {
    try {
      let response
      let lastError = null
      
      // 检测是否为管理员用户名，优先尝试管理员登录
      if (isAdminUsername(loginForm.username)) {
        try {
          // 尝试管理员登录
          response = await adminLogin(loginForm)
          console.log('管理员登录成功')
        } catch (adminError) {
          console.log('管理员登录失败，尝试普通用户登录:', adminError.message)
          lastError = adminError
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
          lastError = userError
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
      
      // 显示错误信息
      const errorMessage = error.response?.data?.detail || '用户名或密码错误'
      ElMessage.error(`登录失败: ${errorMessage}`)
      
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
        confirm_password: registerForm.confirmPassword || registerForm.password,
        email: registerForm.email,
        phone: registerForm.phone || null,
        full_name: registerForm.fullName || registerForm.full_name || null,
        timezone: registerForm.timezone || 'Asia/Shanghai',
        locale: registerForm.locale || 'zh-CN',
        avatar_url: registerForm.avatar_url || null
      })
      return { success: true, user: response }
    } catch (error) {
      console.error('注册API错误:', error.response?.data)
      // 处理验证错误
      let message = '注册失败'
      if (error.response?.data?.detail) {
        if (Array.isArray(error.response.data.detail)) {
          // Pydantic验证错误
          message = error.response.data.detail.map(err => 
            `${err.loc.join('.')}: ${err.msg}`
          ).join('; ')
        } else {
          message = error.response.data.detail
        }
      }
      return { 
        success: false, 
        message
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
    isAdmin,
    login,
    register,
    logout,
    fetchUserInfo
  }
})

