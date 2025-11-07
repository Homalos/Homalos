import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  loginTradingAccount,
  logoutTradingAccount,
  getTradingAccountStatus,
  getTradingAccountList
} from '@/api/tradingAccount'
import { connectAccountWebSocket, getLatestAccountData } from '@/api/account'

export const useTradingAccountStore = defineStore('tradingAccount', () => {
  // 状态
  const accountId = ref(localStorage.getItem('trading_account_id') || null)
  const isLoggedIn = ref(localStorage.getItem('trading_account_logged_in') === 'true')
  const accountInfo = ref(null)
  const accountList = ref([])
  const hasBrokerConfig = ref(false) // 是否有完整的broker配置（用于连接网关）
  
  // 实时账户数据（从交易网关获取）
  const accountData = ref({
    account_id: '',
    balance: 0,
    frozen: 0,
    available: 0
  })
  const positions = ref([])
  
  // WebSocket连接状态
  let accountWs = null
  const isWsConnected = ref(false)

  // 计算属性
  const hasAccount = computed(() => accountList.value.length > 0)
  const defaultAccount = computed(() => accountList.value.find(acc => acc.is_default))
  
  // 计算总盈亏
  const totalPnl = computed(() => {
    return positions.value.reduce((sum, position) => sum + (position.pnl || 0), 0)
  })

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
      hasBrokerConfig.value = response.has_broker_config || false
      
      if (response.is_logged_in) {
        accountId.value = String(response.account_id)
        accountInfo.value = {
          id: response.account_id,
          broker_id: response.broker_id,
          account_id: String(response.account_number),
          display_name: response.display_name
        }
        
        // 更新localStorage
        localStorage.setItem('trading_account_id', String(response.account_id))
        localStorage.setItem('trading_account_logged_in', 'true')
      } else {
        // 清理状态
        clearLoginState()
      }
      
      return response.is_logged_in
    } catch (error) {
      console.error('获取资金账户状态失败:', error)
      
      // 如果是认证错误（401），清理状态
      if (error.response?.status === 401) {
        clearLoginState()
        return false
      }
      
      // 其他错误保持现有状态，避免网络问题导致误清理
      return isLoggedIn.value
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
   * 清理登录状态
   */
  function clearLoginState() {
    accountId.value = null
    accountInfo.value = null
    isLoggedIn.value = false
    hasBrokerConfig.value = false
    localStorage.removeItem('trading_account_id')
    localStorage.removeItem('trading_account_logged_in')
  }

  /**
   * 初始化（页面加载时调用）
   */
  async function initialize() {
    // 检查localStorage中的登录状态
    if (isLoggedIn.value && accountId.value) {
      try {
        // 调用后端验证状态
        const isValid = await fetchStatus()
        if (!isValid) {
          console.log('资金账户状态验证失败，已清理本地状态')
        }
      } catch (error) {
        console.error('初始化资金账户状态失败:', error)
        // fetchStatus内部已处理错误情况
      }
    }
    
    // 获取账户列表
    await fetchAccountList()
  }
  
  /**
   * 连接账户数据WebSocket
   */
  function connectAccountWs() {
    if (accountWs) {
      console.log('[AccountWS] 已存在连接，先断开旧连接')
      disconnectAccountWs()
    }
    
    try {
      accountWs = connectAccountWebSocket(handleAccountMessage, handleAccountError)
      isWsConnected.value = true
      console.log('[AccountWS] 连接已建立')
    } catch (error) {
      console.error('[AccountWS] 连接失败:', error)
      isWsConnected.value = false
    }
  }
  
  /**
   * 断开账户数据WebSocket
   */
  function disconnectAccountWs() {
    if (accountWs) {
      try {
        accountWs.close()
        accountWs = null
        isWsConnected.value = false
        console.log('[AccountWS] 连接已断开')
      } catch (error) {
        console.error('[AccountWS] 断开连接失败:', error)
      }
    }
  }
  
  /**
   * 处理账户数据WebSocket消息
   */
  function handleAccountMessage(message) {
    try {
      if (message.type === 'account') {
        // 更新账户数据
        accountData.value = message.data
        console.log('[AccountWS] 账户数据更新:', message.data)
      } else if (message.type === 'positions') {
        // 更新持仓数据
        positions.value = message.data || []
        console.log('[AccountWS] 持仓数据更新:', message.data.length)
      }
    } catch (error) {
      console.error('[AccountWS] 处理消息失败:', error)
    }
  }
  
  /**
   * 处理WebSocket错误
   */
  function handleAccountError(error) {
    console.error('[AccountWS] 错误:', error)
    isWsConnected.value = false
    
    // 5秒后尝试重连
    setTimeout(() => {
      if (!accountWs) {
        console.log('[AccountWS] 尝试重新连接...')
        connectAccountWs()
      }
    }, 5000)
  }

  return {
    // 状态
    accountId,
    isLoggedIn,
    accountInfo,
    accountList,
    hasBrokerConfig,
    
    // 实时账户数据
    accountData,
    positions,
    isWsConnected,
    
    // 计算属性
    hasAccount,
    defaultAccount,
    totalPnl,
    
    // 方法
    login,
    logout,
    fetchStatus,
    fetchAccountList,
    switchAccount,
    clearLoginState,
    initialize,
    
    // WebSocket方法
    connectAccountWs,
    disconnectAccountWs
  }
})

