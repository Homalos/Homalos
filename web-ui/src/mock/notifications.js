/**
 * 通知列表（硬编码数据）
 */
export const notificationsData = [
  {
    id: 1,
    title: '策略运行异常',
    content: '趋势跟踪策略在AU2406合约上出现异常，已自动停止运行，请检查策略参数。',
    time: '2025-10-08 22:30:15',
    level: '紧急',
    type: 'danger',
    isRead: false
  },
  {
    id: 2,
    title: '持仓盈利提醒',
    content: '均值回归策略在CU2406合约上盈利已达到止盈价，建议关注市场行情及时调整。',
    time: '2025-10-08 21:45:30',
    level: '重要',
    type: 'warning',
    isRead: false
  },
  {
    id: 3,
    title: '系统更新通知',
    content: '系统将于今晚23:00进行例行维护，预计维护时间30分钟，期间系统将暂停交易。',
    time: '2025-10-08 20:15:00',
    level: '通知',
    type: 'primary',
    isRead: false
  },
  {
    id: 4,
    title: '风险控制提醒',
    content: '当前账户总持仓占比已达70%，接近风控阈值，建议适当降低仓位。',
    time: '2025-10-08 18:20:45',
    level: '重要',
    type: 'warning',
    isRead: true
  },
  {
    id: 5,
    title: '策略启动成功',
    content: '套利策略已成功启动，当前运行状态正常，开始执行交易逻辑。',
    time: '2025-10-08 15:30:00',
    level: '通知',
    type: 'success',
    isRead: true
  }
]

