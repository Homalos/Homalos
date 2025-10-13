/**
 * 仪表盘数据（硬编码）
 */
export const dashboardData = {
  // 账户总览
  account: {
    totalEquity: 1285600.50,     // 总权益
    availableFunds: 856420.30,   // 可用资金
    marginUsed: 327230.20,       // 保证金占用
    floatingProfitLoss: 12850.50, // 浮动盈亏
    fundUtilizationRate: 25.45   // 资金使用率(%)：327230.20 / 1285600.50 × 100 ≈ 25.45%
  },
  // 今日表现
  todayPerformance: {
    returnRate: 2.35,    // 当日收益率(%)
    profitLoss: 28560.80, // 盈亏金额
    tradeCount: 47       // 交易次数
  },
  // 策略运行状态
  strategyStatus: {
    active: 3,    // 活跃策略
    running: 2,   // 运行中
    stopped: 1    // 已停止
  },
  // 持仓概览
  positions: [
    { name: '黄金(AU)', ratio: 35, color: '#409EFF' },
    { name: '白银(AG)', ratio: 25, color: '#67C23A' },
    { name: '螺纹钢(RB)', ratio: 20, color: '#E6A23C' },
    { name: '铜(CU)', ratio: 15, color: '#F56C6C' },
    { name: '其他', ratio: 5, color: '#909399' }
  ],
  // 图表数据
  chartData: {
    // 权益曲线数据（30天）
    equityCurve: [
      { date: '2024-12-15', value: 1200000 },
      { date: '2024-12-16', value: 1205000 },
      { date: '2024-12-17', value: 1198000 },
      { date: '2024-12-18', value: 1215000 },
      { date: '2024-12-19', value: 1220000 },
      { date: '2024-12-20', value: 1210000 },
      { date: '2024-12-21', value: 1225000 },
      { date: '2024-12-22', value: 1235000 },
      { date: '2024-12-23', value: 1230000 },
      { date: '2024-12-24', value: 1240000 },
      { date: '2024-12-25', value: 1245000 },
      { date: '2024-12-26', value: 1250000 },
      { date: '2024-12-27', value: 1255000 },
      { date: '2024-12-28', value: 1248000 },
      { date: '2024-12-29', value: 1260000 },
      { date: '2024-12-30', value: 1265000 },
      { date: '2024-12-31', value: 1270000 },
      { date: '2025-01-01', value: 1275000 },
      { date: '2025-01-02', value: 1280000 },
      { date: '2025-01-03', value: 1285600 }
    ],
    // 盈亏数据（20天）
    profitLoss: [
      { date: '2024-12-25', profit: 5000 },
      { date: '2024-12-26', profit: 8000 },
      { date: '2024-12-27', profit: -3000 },
      { date: '2024-12-28', profit: 12000 },
      { date: '2024-12-29', profit: -5000 },
      { date: '2024-12-30', profit: 15000 },
      { date: '2024-12-31', profit: 7000 },
      { date: '2025-01-01', profit: -2000 },
      { date: '2025-01-02', profit: 18000 },
      { date: '2025-01-03', profit: 28560 }
    ],
    // 收益率曲线数据（20天）
    returnRate: [
      { date: '2024-12-25', rate: 0 },
      { date: '2024-12-26', rate: 0.42 },
      { date: '2024-12-27', rate: 0.67 },
      { date: '2024-12-28', rate: 0.40 },
      { date: '2024-12-29', rate: 1.25 },
      { date: '2024-12-30', rate: 0.83 },
      { date: '2024-12-31', rate: 1.67 },
      { date: '2025-01-01', rate: 2.25 },
      { date: '2025-01-02', rate: 2.08 },
      { date: '2025-01-03', rate: 3.75 }
    ]
  }
}

