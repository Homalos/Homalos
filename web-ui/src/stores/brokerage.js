/**
 * 用户券商账户Store
 * @module stores/brokerage
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  createBrokerage,
  getBrokerageList,
  getBrokerageDetail,
  updateBrokerage,
  deleteBrokerage,
  setDefaultBrokerage,
  activateBrokerage,
  deactivateBrokerage
} from '@/api/brokerage'

export const useBrokerageStore = defineStore('brokerage', () => {
  // 状态
  const brokerages = ref([])
  const currentBrokerage = ref(null)
  const loading = ref(false)
  const error = ref(null)

  // 计算属性
  const activeBrokerages = computed(() => {
    return brokerages.value.filter(b => b.status === 'active')
  })

  const defaultBrokerage = computed(() => {
    return brokerages.value.find(b => b.is_default)
  })

  const brokerageCount = computed(() => {
    return brokerages.value.length
  })

  const activeBrokerageCount = computed(() => {
    return activeBrokerages.value.length
  })

  // 操作方法

  /**
   * 获取券商账户列表
   * @param {boolean} includeInactive - 是否包含未激活账户
   */
  async function fetchBrokerages(includeInactive = false) {
    loading.value = true
    error.value = null
    
    try {
      const response = await getBrokerageList({ include_inactive: includeInactive })
      brokerages.value = response.accounts || []
      return response
    } catch (err) {
      error.value = err.message || '获取券商账户列表失败'
      console.error('获取券商账户列表失败:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * 获取单个券商账户详情
   * @param {number} brokerageId - 券商账户ID
   */
  async function fetchBrokerageDetail(brokerageId) {
    loading.value = true
    error.value = null
    
    try {
      const response = await getBrokerageDetail(brokerageId)
      currentBrokerage.value = response
      return response
    } catch (err) {
      error.value = err.message || '获取券商账户详情失败'
      console.error('获取券商账户详情失败:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * 创建券商账户
   * @param {Object} data - 券商账户数据
   */
  async function addBrokerage(data) {
    loading.value = true
    error.value = null
    
    try {
      const response = await createBrokerage(data)
      
      // 添加到列表
      brokerages.value.unshift(response)
      
      // 如果设置为默认，更新其他账户的默认状态
      if (response.is_default) {
        brokerages.value.forEach(b => {
          if (b.id !== response.id) {
            b.is_default = false
          }
        })
      }
      
      return response
    } catch (err) {
      error.value = err.message || '创建券商账户失败'
      console.error('创建券商账户失败:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * 更新券商账户
   * @param {number} brokerageId - 券商账户ID
   * @param {Object} data - 更新数据
   */
  async function modifyBrokerage(brokerageId, data) {
    loading.value = true
    error.value = null
    
    try {
      const response = await updateBrokerage(brokerageId, data)
      
      // 更新列表中的数据
      const index = brokerages.value.findIndex(b => b.id === brokerageId)
      if (index !== -1) {
        brokerages.value[index] = response
      }
      
      // 如果设置为默认，更新其他账户的默认状态
      if (response.is_default) {
        brokerages.value.forEach(b => {
          if (b.id !== response.id) {
            b.is_default = false
          }
        })
      }
      
      // 更新当前账户
      if (currentBrokerage.value?.id === brokerageId) {
        currentBrokerage.value = response
      }
      
      return response
    } catch (err) {
      error.value = err.message || '更新券商账户失败'
      console.error('更新券商账户失败:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * 删除券商账户
   * @param {number} brokerageId - 券商账户ID
   */
  async function removeBrokerage(brokerageId) {
    loading.value = true
    error.value = null
    
    try {
      await deleteBrokerage(brokerageId)
      
      // 从列表中移除
      const index = brokerages.value.findIndex(b => b.id === brokerageId)
      if (index !== -1) {
        brokerages.value.splice(index, 1)
      }
      
      // 清除当前账户
      if (currentBrokerage.value?.id === brokerageId) {
        currentBrokerage.value = null
      }
      
      return true
    } catch (err) {
      error.value = err.message || '删除券商账户失败'
      console.error('删除券商账户失败:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * 设置默认券商账户
   * @param {number} brokerageId - 券商账户ID
   */
  async function setDefault(brokerageId) {
    loading.value = true
    error.value = null
    
    try {
      const response = await setDefaultBrokerage(brokerageId)
      
      // 更新所有账户的默认状态
      brokerages.value.forEach(b => {
        b.is_default = b.id === brokerageId
      })
      
      return response
    } catch (err) {
      error.value = err.message || '设置默认账户失败'
      console.error('设置默认账户失败:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * 激活券商账户
   * @param {number} brokerageId - 券商账户ID
   */
  async function activate(brokerageId) {
    loading.value = true
    error.value = null
    
    try {
      const response = await activateBrokerage(brokerageId)
      
      // 更新列表中的状态
      const brokerage = brokerages.value.find(b => b.id === brokerageId)
      if (brokerage) {
        brokerage.status = 'active'
      }
      
      return response
    } catch (err) {
      error.value = err.message || '激活账户失败'
      console.error('激活账户失败:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * 停用券商账户
   * @param {number} brokerageId - 券商账户ID
   */
  async function deactivate(brokerageId) {
    loading.value = true
    error.value = null
    
    try {
      const response = await deactivateBrokerage(brokerageId)
      
      // 更新列表中的状态
      const brokerage = brokerages.value.find(b => b.id === brokerageId)
      if (brokerage) {
        brokerage.status = 'inactive'
      }
      
      return response
    } catch (err) {
      error.value = err.message || '停用账户失败'
      console.error('停用账户失败:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * 清除错误信息
   */
  function clearError() {
    error.value = null
  }

  /**
   * 重置Store
   */
  function reset() {
    brokerages.value = []
    currentBrokerage.value = null
    loading.value = false
    error.value = null
  }

  return {
    // 状态
    brokerages,
    currentBrokerage,
    loading,
    error,
    
    // 计算属性
    activeBrokerages,
    defaultBrokerage,
    brokerageCount,
    activeBrokerageCount,
    
    // 方法
    fetchBrokerages,
    fetchBrokerageDetail,
    addBrokerage,
    modifyBrokerage,
    removeBrokerage,
    setDefault,
    activate,
    deactivate,
    clearError,
    reset
  }
})
