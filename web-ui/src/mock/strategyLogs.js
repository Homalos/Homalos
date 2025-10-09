/**
 * 策略操作日志（硬编码数据）
 */
export const strategyLogsData = [
  {
    id: 1,
    timestamp: '2025-10-09 10:30:15',
    level: 'success',
    category: '添加策略',
    message: '成功添加策略 "趋势跟踪策略"',
    details: { strategyId: 'STR001', strategyName: '趋势跟踪策略' }
  },
  {
    id: 2,
    timestamp: '2025-10-09 10:31:22',
    level: 'success',
    category: '启动策略',
    message: '策略 "趋势跟踪策略" 已启动',
    details: { strategyId: 'STR001', strategyName: '趋势跟踪策略' }
  },
  {
    id: 3,
    timestamp: '2025-10-09 12:15:45',
    level: 'info',
    category: '持仓变动',
    message: '策略 "趋势跟踪策略" 在 AU2406 建立多头持仓 10 手',
    details: { strategyId: 'STR001', contract: 'AU2406', direction: '多', volume: 10 }
  },
  {
    id: 4,
    timestamp: '2025-10-09 14:20:00',
    level: 'success',
    category: '添加策略',
    message: '成功添加策略 "均值回归策略"',
    details: { strategyId: 'STR002', strategyName: '均值回归策略' }
  },
  {
    id: 5,
    timestamp: '2025-10-09 14:25:30',
    level: 'warning',
    category: '停止策略',
    message: '策略 "均值回归策略" 已停止',
    details: { strategyId: 'STR002', strategyName: '均值回归策略' }
  },
  {
    id: 6,
    timestamp: '2025-10-09 15:10:12',
    level: 'info',
    category: '参数配置',
    message: '策略 "趋势跟踪策略" 风险参数已更新',
    details: { strategyId: 'STR001', maxPosition: 50, stopLossRatio: 2.0 }
  },
  {
    id: 7,
    timestamp: '2025-10-09 16:45:00',
    level: 'success',
    category: '添加策略',
    message: '成功添加策略 "套利策略"',
    details: { strategyId: 'STR003', strategyName: '套利策略' }
  },
  {
    id: 8,
    timestamp: '2025-10-09 16:46:15',
    level: 'success',
    category: '启动策略',
    message: '策略 "套利策略" 已启动',
    details: { strategyId: 'STR003', strategyName: '套利策略' }
  },
  {
    id: 9,
    timestamp: '2025-10-09 18:30:25',
    level: 'warning',
    category: '风险控制',
    message: '策略 "趋势跟踪策略" 触发止损，自动平仓',
    details: { strategyId: 'STR001', contract: 'AG2406', reason: '止损' }
  },
  {
    id: 10,
    timestamp: '2025-10-09 20:15:40',
    level: 'error',
    category: '策略异常',
    message: '策略 "套利策略" 运行异常：网络连接失败',
    details: { strategyId: 'STR003', error: '网络连接失败' }
  }
]

