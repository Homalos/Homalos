import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  loginTradingAccount,
  logoutTradingAccount,
  getTradingAccountStatus,
  getTradingAccountList
} from '@/api/tradingAccount'

export const useTradingAccountStore = defineStore('tradingAccount', () => {
  // 状态
  const accountId = ref(localStorage.getItem('trading_account_id') || null)
  const isLoggedIn = ref(localStorage.getItem('trading_account_logged_in') === 'true')
  const accountInfo = ref(null)
  const accountList = ref([])

  // 计算属性
  const hasAccount = computed(() => accountList.value.length > 0)
  const defaultAccount = computed(() => accountList.value.find(acc => acc.is_default))

  /**
   * 登录资金账户
   */
  async function login(loginData) {
    try {
      const response = await loginTradingAccount(loginData)
      
      if (response.success) {
        accountId.value = String(response.account.id)
        accountInfo.value = response.account
        isLoggedIn.value = true
        
        // 更新Token
        if (response.token) {
          localStorage.setItem('token', response.token)
        }
        
        // 持久化
        localStorage.setItem('trading_account_id', String(response.account.id))
        localStorage.setItem('trading_account_logged_in', 'true')
        
        // 刷新账户列表（确保新创建的账户显示在列表中）
        await fetchAccountList()
        
        return { success: true, account: response.account }
      }
      return { success: false, message: response.message || '登录失败' }
    } catch (error) {
      console.error('资金账户登录失败:', error)
      return { success: false, message: error.response?.data?.detail || '登录失败' }
    }
  }

  /**
   * 登出资金账户
   */
  async function logout() {
    try {
      const response = await logoutTradingAccount()
      
      if (response.success) {
        // 更新Token
        if (response.token) {
          localStorage.setItem('token', response.token)
        }
      }
    } catch (error) {
      console.error('资金账户登出失败:', error)
    } finally {
      // 无论成功失败都清除状态
      accountId.value = null
      accountInfo.value = null
      isLoggedIn.value = false
      localStorage.removeItem('trading_account_id')
      localStorage.removeItem('trading_account_logged_in')
    }
  }

  /**
   * 获取登录状态
   */
  async function fetchStatus() {
    try {
      const response = await getTradingAccountStatus()
      isLoggedIn.value = response.is_logged_in
      
      if (response.is_logged_in) {
        accountId.value = String(response.account_id)
        accountInfo.value = {
          id: response.account_id,
          broker_id: response.broker_id,
          account_id: String(response.account_number),
          display_name: response.display_name
        }
      }
      
      return response.is_logged_in
    } catch (error) {
      console.error('获取资金账户状态失败:', error)
      return false
    }
  }

  /**
   * 获取账户列表
   */
  async function fetchAccountList() {
    try {
      const response = await getTradingAccountList()
      accountList.value = response.accounts || []
      return true
    } catch (error) {
      console.error('获取账户列表失败:', error)
      return false
    }
  }

  /**
   * 切换账户
   */
  async function switchAccount(accountId) {
    // 实现切换逻辑
    // 调用登录API并更新状态
  }

  /**
   * 初始化（页面加载时调用）
   */
  async function initialize() {
    if (isLoggedIn.value && accountId.value) {
      await fetchStatus()
    }
    await fetchAccountList()
  }

  return {
    // 状态
    accountId,
    isLoggedIn,
    accountInfo,
    accountList,
    
    // 计算属性
    hasAccount,
    defaultAccount,
    
    // 方法
    login,
    logout,
    fetchStatus,
    fetchAccountList,
    switchAccount,
    initialize
  }
})

