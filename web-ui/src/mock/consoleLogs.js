/**
 * 控制台日志（硬编码数据）
 */
export const consoleLogsData = [
  {
    id: 1,
    timestamp: '2025-10-09 09:00:15',
    level: 'success',
    category: '系统启动',
    message: '数据中心启动成功',
    details: { component: 'dataCenter' }
  },
  {
    id: 2,
    timestamp: '2025-10-09 09:00:30',
    level: 'info',
    category: '数据同步',
    message: '开始同步市场数据...',
    details: { component: 'dataCenter' }
  },
  {
    id: 3,
    timestamp: '2025-10-09 09:05:45',
    level: 'success',
    category: '系统启动',
    message: '量化交易系统启动成功',
    details: { component: 'tradingSystem' }
  },
  {
    id: 4,
    timestamp: '2025-10-09 12:30:00',
    level: 'warning',
    category: '系统停止',
    message: '量化交易系统已停止',
    details: { component: 'tradingSystem' }
  },
  {
    id: 5,
    timestamp: '2025-10-09 14:15:20',
    level: 'success',
    category: '系统启动',
    message: '量化交易系统重新启动',
    details: { component: 'tradingSystem' }
  },
  {
    id: 6,
    timestamp: '2025-10-09 16:45:00',
    level: 'info',
    category: '系统检查',
    message: '系统运行正常，所有模块状态良好',
    details: { }
  },
  {
    id: 7,
    timestamp: '2025-10-09 18:00:00',
    level: 'warning',
    category: '系统停止',
    message: '数据中心停止运行',
    details: { component: 'dataCenter' }
  }
]

