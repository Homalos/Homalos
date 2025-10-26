/**
 * 仪表盘归零数据（系统未启动时显示）
 */
export const emptyDashboardData = {
  // 账户总览 - 全部归零
  account: {
    totalEquity: 0,           // 总权益
    availableFunds: 0,        // 可用资金
    marginUsed: 0,            // 保证金占用
    floatingProfitLoss: 0,    // 浮动盈亏
    fundUtilizationRate: 0    // 资金使用率(%)
  },
  // 今日表现 - 全部归零
  todayPerformance: {
    returnRate: 0,      // 当日收益率(%)
    profitLoss: 0,      // 盈亏金额
    tradeCount: 0       // 交易次数
  },
  // 策略运行状态 - 全部归零
  strategyStatus: {
    active: 0,    // 活跃策略
    running: 0,   // 运行中
    stopped: 0    // 已停止
  },
  // 持仓概览 - 空数组
  positions: [],
  // 图表数据 - 空数组
  chartData: {
    equityCurve: [],
    profitLoss: [],
    returnRate: []
  }
}

/**
 * 仪表盘模拟数据（系统启动但未连接实时数据时显示）
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
    // 权益曲线数据（6个月历史数据）
    equityCurve: [
      // 7月数据
      { date: '2024-07-15', value: 1000000 },
      { date: '2024-07-22', value: 1015000 },
      { date: '2024-07-29', value: 1008000 },
      // 8月数据
      { date: '2024-08-05', value: 1025000 },
      { date: '2024-08-12', value: 1040000 },
      { date: '2024-08-19', value: 1035000 },
      { date: '2024-08-26', value: 1055000 },
      // 9月数据
      { date: '2024-09-02', value: 1070000 },
      { date: '2024-09-09', value: 1065000 },
      { date: '2024-09-16', value: 1080000 },
      { date: '2024-09-23', value: 1095000 },
      { date: '2024-09-30', value: 1110000 },
      // 10月数据
      { date: '2024-10-07', value: 1125000 },
      { date: '2024-10-14', value: 1140000 },
      { date: '2024-10-21', value: 1135000 },
      { date: '2024-10-28', value: 1150000 },
      // 11月数据
      { date: '2024-11-04', value: 1165000 },
      { date: '2024-11-11', value: 1180000 },
      { date: '2024-11-18', value: 1175000 },
      { date: '2024-11-25', value: 1190000 },
      // 12月数据
      { date: '2024-12-02', value: 1195000 },
      { date: '2024-12-09', value: 1185000 },
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
      // 1月数据（最新）
      { date: '2025-01-01', value: 1275000 },
      { date: '2025-01-02', value: 1280000 },
      { date: '2025-01-03', value: 1285600 },
      { date: '2025-01-06', value: 1290000 },
      { date: '2025-01-07', value: 1295000 },
      { date: '2025-01-08', value: 1288000 },
      { date: '2025-01-09', value: 1302000 },
      { date: '2025-01-10', value: 1308000 },
      { date: '2025-01-13', value: 1315000 }
    ],
    // 盈亏数据（6个月历史数据）
    profitLoss: [
      // 7月数据
      { date: '2024-07-15', profit: 15000 },
      { date: '2024-07-22', profit: -8000 },
      { date: '2024-07-29', profit: 12000 },
      // 8月数据
      { date: '2024-08-05', profit: 17000 },
      { date: '2024-08-12', profit: 15000 },
      { date: '2024-08-19', profit: -5000 },
      { date: '2024-08-26', profit: 20000 },
      // 9月数据
      { date: '2024-09-02', profit: 15000 },
      { date: '2024-09-09', profit: -5000 },
      { date: '2024-09-16', profit: 15000 },
      { date: '2024-09-23', profit: 15000 },
      { date: '2024-09-30', profit: 15000 },
      // 10月数据
      { date: '2024-10-07', profit: 15000 },
      { date: '2024-10-14', profit: 15000 },
      { date: '2024-10-21', profit: -5000 },
      { date: '2024-10-28', profit: 15000 },
      // 11月数据
      { date: '2024-11-04', profit: 15000 },
      { date: '2024-11-11', profit: 15000 },
      { date: '2024-11-18', profit: -5000 },
      { date: '2024-11-25', profit: 15000 },
      // 12月数据
      { date: '2024-12-02', profit: 5000 },
      { date: '2024-12-09', profit: -10000 },
      { date: '2024-12-16', profit: 15000 },
      { date: '2024-12-23', profit: -5000 },
      { date: '2024-12-25', profit: 5000 },
      { date: '2024-12-26', profit: 8000 },
      { date: '2024-12-27', profit: -3000 },
      { date: '2024-12-28', profit: 12000 },
      { date: '2024-12-29', profit: -5000 },
      { date: '2024-12-30', profit: 15000 },
      { date: '2024-12-31', profit: 7000 },
      // 1月数据（最新）
      { date: '2025-01-01', profit: -2000 },
      { date: '2025-01-02', profit: 18000 },
      { date: '2025-01-03', profit: 28560 },
      { date: '2025-01-06', profit: 12000 },
      { date: '2025-01-07', profit: 8000 },
      { date: '2025-01-08', profit: -15000 },
      { date: '2025-01-09', profit: 25000 },
      { date: '2025-01-10', profit: 18000 },
      { date: '2025-01-13', profit: 22000 }
    ],
    // 收益率曲线数据（6个月历史数据）
    returnRate: [
      // 7月数据
      { date: '2024-07-15', rate: 0 },
      { date: '2024-07-22', rate: 1.5 },
      { date: '2024-07-29', rate: 0.8 },
      // 8月数据
      { date: '2024-08-05', rate: 2.5 },
      { date: '2024-08-12', rate: 4.0 },
      { date: '2024-08-19', rate: 3.5 },
      { date: '2024-08-26', rate: 5.5 },
      // 9月数据
      { date: '2024-09-02', rate: 7.0 },
      { date: '2024-09-09', rate: 6.5 },
      { date: '2024-09-16', rate: 8.0 },
      { date: '2024-09-23', rate: 9.5 },
      { date: '2024-09-30', rate: 11.0 },
      // 10月数据
      { date: '2024-10-07', rate: 12.5 },
      { date: '2024-10-14', rate: 14.0 },
      { date: '2024-10-21', rate: 13.5 },
      { date: '2024-10-28', rate: 15.0 },
      // 11月数据
      { date: '2024-11-04', rate: 16.5 },
      { date: '2024-11-11', rate: 18.0 },
      { date: '2024-11-18', rate: 17.5 },
      { date: '2024-11-25', rate: 19.0 },
      // 12月数据
      { date: '2024-12-02', rate: 19.5 },
      { date: '2024-12-09', rate: 18.5 },
      { date: '2024-12-16', rate: 20.0 },
      { date: '2024-12-23', rate: 19.5 },
      { date: '2024-12-25', rate: 20.0 },
      { date: '2024-12-26', rate: 20.42 },
      { date: '2024-12-27', rate: 20.67 },
      { date: '2024-12-28', rate: 20.40 },
      { date: '2024-12-29', rate: 21.25 },
      { date: '2024-12-30', rate: 20.83 },
      { date: '2024-12-31', rate: 21.67 },
      // 1月数据（最新）
      { date: '2025-01-01', rate: 22.25 },
      { date: '2025-01-02', rate: 22.08 },
      { date: '2025-01-03', rate: 23.75 },
      { date: '2025-01-06', rate: 24.20 },
      { date: '2025-01-07', rate: 24.85 },
      { date: '2025-01-08', rate: 23.65 },
      { date: '2025-01-09', rate: 25.45 },
      { date: '2025-01-10', rate: 26.20 },
      { date: '2025-01-13', rate: 27.15 }
    ]
  }
}

