/**
 * 仪表盘逻辑 Composable
 */
import { reactive } from 'vue'
import { dashboardData as dashboardDataImport } from '@/mock'

export function useDashboard() {
  // ===== 状态管理 =====
  const dashboardData = reactive(dashboardDataImport)

  // ===== 方法 =====
  
  /**
   * 获取盈亏颜色（中国市场习惯：红涨绿跌）
   */
  const getProfitColor = (value) => {
    if (value > 0) return '#f56c6c'  // 红色（盈利）
    if (value < 0) return '#67c23a'  // 绿色（亏损）
    return '#000000'                  // 黑色（持平）
  }

  /**
   * 刷新仪表盘数据
   * TODO: 未来对接后端API
   */
  const refreshDashboard = async () => {
    // 这里将来会调用API获取最新数据
    console.log('刷新仪表盘数据')
  }

  return {
    // 状态
    dashboardData,
    
    // 方法
    getProfitColor,
    refreshDashboard
  }
}

