/**
 * 系统监控逻辑 Composable
 */
import { reactive, onUnmounted } from 'vue'
import { getSystemStats } from '@/api/monitor'

export function useSystemMonitor() {
  // 定时器引用
  let monitorTimer = null

  // 系统监控信息
  const systemInfo = reactive({
    cpu: 0,
    memory: 0,
    lastUpdate: null,
    loading: false,
    error: null
  })

  /**
   * 获取系统监控数据
   */
  const fetchSystemStats = async () => {
    try {
      systemInfo.loading = true
      const data = await getSystemStats()
      
      systemInfo.cpu = data.cpu_percent
      systemInfo.memory = data.memory_percent
      systemInfo.lastUpdate = data.timestamp
      systemInfo.error = null
    } catch (error) {
      console.error('获取监控数据失败:', error)
      systemInfo.error = '获取监控数据失败'
      // 保留上次的数据，不清空
    } finally {
      systemInfo.loading = false
    }
  }

  /**
   * 启动监控数据轮询
   */
  const startMonitoring = () => {
    fetchSystemStats()  // 立即获取一次
    monitorTimer = setInterval(fetchSystemStats, 3000)  // 每3秒刷新
  }

  /**
   * 停止监控数据轮询
   */
  const stopMonitoring = () => {
    if (monitorTimer) {
      clearInterval(monitorTimer)
      monitorTimer = null
    }
  }

  // 组件卸载时自动停止监控
  onUnmounted(() => {
    stopMonitoring()
  })

  return {
    systemInfo,
    fetchSystemStats,
    startMonitoring,
    stopMonitoring
  }
}

