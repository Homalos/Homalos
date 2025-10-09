/**
 * 仪表盘数据（硬编码）
 */
export const dashboardData = {
  // 账户总览
  account: {
    totalAssets: 1285600.50,     // 总资产
    availableFunds: 856420.30,   // 可用资金
    marginUsed: 327230.20,       // 保证金占用
    floatingProfitLoss: 12850.50 // 浮动盈亏
  },
  // 今日表现
  todayPerformance: {
    returnRate: 2.35,    // 当日收益率(%)
    profitLoss: 28560.80, // 盈亏金额
    tradeCount: 47       // 交易次数
  },
  // 策略运行状态
  strategyStatus: {
    running: 2,   // 运行中
    stopped: 1,   // 已停止
    error: 0      // 异常
  },
  // 持仓概览
  positions: [
    { name: '黄金(AU)', ratio: 35, color: '#409EFF' },
    { name: '白银(AG)', ratio: 25, color: '#67C23A' },
    { name: '螺纹钢(RB)', ratio: 20, color: '#E6A23C' },
    { name: '铜(CU)', ratio: 15, color: '#F56C6C' },
    { name: '其他', ratio: 5, color: '#909399' }
  ]
}

