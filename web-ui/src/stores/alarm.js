/**
 * 告警管理Store
 * 
 * 功能：
 * - 管理告警列表状态
 * - WebSocket连接管理
 * - 告警数据的CRUD操作
 * - 未读告警计数
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import request from '@/api/request'

const API_BASE = '/api'

export const useAlarmStore = defineStore('alarm', () => {
  // ========== 状态 ==========
  const alarms = ref([])
  const stats = ref({
    status_stats: {},
    severity_stats: {},
    type_stats: {},
    today_count: 0,
    active_count: 0
  })
  const config = ref({
    cpu_threshold: 80,
    memory_threshold: 85,
    retention_days: 30,
    email_enabled: true
  })
  
  // WebSocket连接
  const ws = ref(null)
  const wsConnected = ref(false)
  const wsReconnectAttempts = ref(0)
  const maxReconnectAttempts = 10
  
  // 分页
  const currentPage = ref(1)
  const pageSize = ref(20)
  const totalAlarms = ref(0)
  
  // 筛选
  const filters = ref({
    status: null,
    severity: null,
    alarm_type: null,
    start_date: null,
    end_date: null
  })
  
  // ========== 计算属性 ==========
  const unreadCount = computed(() => stats.value.active_count || 0)
  
  const recentAlarms = computed(() => {
    return alarms.value.slice(0, 5)
  })
  
  // ========== WebSocket管理 ==========
  function connectWebSocket() {
    if (ws.value && ws.value.readyState === WebSocket.OPEN) {
      console.log('[AlarmStore] WebSocket已连接')
      return
    }
    
    try {
      ws.value = new WebSocket(`ws://localhost:8000/api/alarms/ws`)
      
      ws.value.onopen = () => {
        console.log('[AlarmStore] 告警WebSocket连接成功')
        wsConnected.value = true
        wsReconnectAttempts.value = 0
      }
      
      ws.value.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data)
          handleWebSocketMessage(message)
        } catch (error) {
          console.error('[AlarmStore] 解析WebSocket消息失败:', error)
        }
      }
      
      ws.value.onerror = (error) => {
        console.error('[AlarmStore] WebSocket错误:', error)
      }
      
      ws.value.onclose = () => {
        console.log('[AlarmStore] 告警WebSocket连接断开')
        wsConnected.value = false
        
        // 自动重连
        if (wsReconnectAttempts.value < maxReconnectAttempts) {
          wsReconnectAttempts.value++
          const delay = Math.min(1000 * Math.pow(2, wsReconnectAttempts.value), 30000)
          console.log(`[AlarmStore] ${delay}ms后尝试重连 (${wsReconnectAttempts.value}/${maxReconnectAttempts})`)
          setTimeout(connectWebSocket, delay)
        }
      }
      
      // 心跳
      setInterval(() => {
        if (ws.value && ws.value.readyState === WebSocket.OPEN) {
          ws.value.send(JSON.stringify({ type: 'ping' }))
        }
      }, 25000)
      
    } catch (error) {
      console.error('[AlarmStore] 创建WebSocket连接失败:', error)
    }
  }
  
  function disconnectWebSocket() {
    if (ws.value) {
      ws.value.close()
      ws.value = null
      wsConnected.value = false
    }
  }
  
  function handleWebSocketMessage(message) {
    console.log('[AlarmStore] 收到消息:', message)
    
    switch (message.type) {
      case 'connected':
        console.log('[AlarmStore] 连接确认:', message.message)
        break
      
      case 'alarm':
        // 新告警到达
        handleNewAlarm(message.data)
        break
      
      case 'pong':
        // 心跳响应
        break
      
      case 'ping':
        // 服务器心跳，回复pong
        if (ws.value && ws.value.readyState === WebSocket.OPEN) {
          ws.value.send(JSON.stringify({ type: 'pong' }))
        }
        break
      
      default:
        console.warn('[AlarmStore] 未知消息类型:', message.type)
    }
  }
  
  function handleNewAlarm(alarmData) {
    console.log('[AlarmStore] 新告警:', alarmData)
    
    // 添加到列表顶部
    alarms.value.unshift(alarmData)
    
    // 更新统计
    stats.value.active_count++
    stats.value.today_count++
    
    // 显示通知
    showNotification(alarmData)
    
    // 刷新列表（如果在告警管理页面）
    if (window.location.pathname.includes('/alarms')) {
      fetchAlarms()
    }
  }
  
  function showNotification(alarmData) {
    // 浏览器通知
    if ('Notification' in window && Notification.permission === 'granted') {
      const severityEmoji = {
        info: 'ℹ️',
        warning: '⚠️',
        error: '❌',
        critical: '🚨'
      }
      
      new Notification(`${severityEmoji[alarmData.severity]} Homalos告警`, {
        body: alarmData.message,
        icon: '/logo.svg',
        tag: alarmData.alarm_id
      })
    }
  }
  
  // ========== API操作 ==========
  async function fetchAlarms() {
    try {
      const params = {
        page: currentPage.value,
        page_size: pageSize.value,
        ...filters.value
      }
      
      // 移除null值
      Object.keys(params).forEach(key => {
        if (params[key] === null || params[key] === undefined) {
          delete params[key]
        }
      })
      
      const response = await request.get(`${API_BASE}/alarms`, { params })
      alarms.value = response.items
      totalAlarms.value = response.total
      currentPage.value = response.page
      pageSize.value = response.page_size
    } catch (error) {
      console.error('[AlarmStore] 获取告警列表失败:', error)
      throw error
    }
  }
  
  async function fetchAlarmDetail(alarmId) {
    try {
      const response = await request.get(`${API_BASE}/alarms/${alarmId}`)
      return response
    } catch (error) {
      console.error('[AlarmStore] 获取告警详情失败:', error)
      throw error
    }
  }
  
  async function fetchStats() {
    try {
      const response = await request.get(`${API_BASE}/alarms/stats/summary`)
      stats.value = response
    } catch (error) {
      console.error('[AlarmStore] 获取告警统计失败:', error)
      throw error
    }
  }
  
  async function acknowledgeAlarm(alarmId) {
    try {
      await request.post(`${API_BASE}/alarms/${alarmId}/acknowledge`)
      // 更新本地状态
      const alarm = alarms.value.find(a => a.alarm_id === alarmId)
      if (alarm) {
        alarm.status = 'acknowledged'
        alarm.acknowledged_at = new Date().toISOString()
      }
      // 刷新统计
      await fetchStats()
    } catch (error) {
      console.error('[AlarmStore] 确认告警失败:', error)
      throw error
    }
  }
  
  async function resolveAlarm(alarmId) {
    try {
      await request.post(`${API_BASE}/alarms/${alarmId}/resolve`)
      // 更新本地状态
      const alarm = alarms.value.find(a => a.alarm_id === alarmId)
      if (alarm) {
        alarm.status = 'resolved'
        alarm.resolved_at = new Date().toISOString()
      }
      // 刷新统计
      await fetchStats()
    } catch (error) {
      console.error('[AlarmStore] 解决告警失败:', error)
      throw error
    }
  }
  
  async function fetchConfig() {
    try {
      const response = await request.get(`${API_BASE}/alarms/config/settings`)
      config.value = response
    } catch (error) {
      console.error('[AlarmStore] 获取告警配置失败:', error)
      throw error
    }
  }
  
  async function updateConfig(newConfig) {
    try {
      await request.put(`${API_BASE}/alarms/config/settings`, newConfig)
      config.value = { ...config.value, ...newConfig }
    } catch (error) {
      console.error('[AlarmStore] 更新告警配置失败:', error)
      throw error
    }
  }
  
  async function triggerTestAlarm(testData) {
    try {
      await request.post(`${API_BASE}/alarms/test`, testData)
    } catch (error) {
      console.error('[AlarmStore] 触发测试告警失败:', error)
      throw error
    }
  }
  
  function setFilters(newFilters) {
    filters.value = { ...filters.value, ...newFilters }
    currentPage.value = 1
  }
  
  function setPage(page) {
    currentPage.value = page
  }
  
  function resetFilters() {
    filters.value = {
      status: null,
      severity: null,
      alarm_type: null,
      start_date: null,
      end_date: null
    }
    currentPage.value = 1
  }
  
  // 请求浏览器通知权限
  function requestNotificationPermission() {
    if ('Notification' in window && Notification.permission === 'default') {
      Notification.requestPermission()
    }
  }
  
  return {
    // 状态
    alarms,
    stats,
    config,
    wsConnected,
    currentPage,
    pageSize,
    totalAlarms,
    filters,
    
    // 计算属性
    unreadCount,
    recentAlarms,
    
    // WebSocket
    connectWebSocket,
    disconnectWebSocket,
    
    // API操作
    fetchAlarms,
    fetchAlarmDetail,
    fetchStats,
    acknowledgeAlarm,
    resolveAlarm,
    fetchConfig,
    updateConfig,
    triggerTestAlarm,
    setFilters,
    setPage,
    resetFilters,
    requestNotificationPermission
  }
})

