/**
 * 策略数据（硬编码）
 */
export const strategiesData = [
  { 
    // === 基础字段 ===
    id: 'STR001', 
    name: '趋势跟踪策略', 
    status: '运行中', 
    startTime: '2025-10-08 09:30:00',
    runningTime: '12h15m',
    
    // === 基础信息 ===
    description: '基于趋势线和移动平均线的跟踪策略，适用于趋势明显的市场环境，通过识别市场趋势方向进行交易',
    author: '张三',
    createTime: '2025-10-01 14:20:00',
    lastModifyTime: '2025-10-07 16:45:00',
    
    // === 持仓信息 ===
    positions: [
      {
        contract: 'AU2406',
        volume: 10,
        direction: '多',
        holdPrice: 450.5,
        latestPrice: 462.3,
        tradeTime: '2025-10-08 09:15:32',
        orderStatus: '全部成交',
        takeProfitPrice: 460.0,
        stopLossPrice: 445.0,
        margin: 45050.0,
        profitLoss: 1200.5,
        profitLossRatio: 2.67,
        returnRate: 2.67
      },
      {
        contract: 'AG2406',
        volume: 20,
        direction: '空',
        holdPrice: 5200.0,
        latestPrice: 5175.0,
        tradeTime: '2025-10-08 10:20:15',
        orderStatus: '部分成交',
        takeProfitPrice: 5100.0,
        stopLossPrice: 5250.0,
        margin: 104000.0,
        profitLoss: -500.0,
        profitLossRatio: -0.48,
        returnRate: -0.48
      }
    ],
    
    // === 参数配置 ===
    parameters: {
      trading: {
        lotSize: 1,
        maxOrders: 5,
        orderInterval: 60,
        enableCompound: true
      },
      risk: {
        stopLossPercent: 2.0,
        takeProfitPercent: 3.0,
        maxDrawdown: 10.0,
        riskRewardRatio: 1.5
      },
      indicator: {
        maPeriod: 20,
        maType: 'SMA',
        rsiPeriod: 14,
        enableMACD: true
      }
    },
    
    // === 风险控制 ===
    riskControl: {
      maxPosition: 50,
      stopLossRatio: 2.0,
      takeProfitRatio: 3.0,
      maxDrawdown: 10.0,
      maxLeverage: 3.0,
      riskLevel: '中'
    }
  },
  { 
    // === 基础字段 ===
    id: 'STR002', 
    name: '均值回归策略', 
    status: '已停止', 
    startTime: '2025-10-07 14:20:00',
    runningTime: '-',
    
    // === 基础信息 ===
    description: '当价格偏离均值时进行反向交易，预期价格会回归均值，适用于震荡市场',
    author: '李四',
    createTime: '2025-09-25 10:30:00',
    lastModifyTime: '2025-10-06 09:15:00',
    
    // === 持仓信息 ===
    positions: [
      {
        contract: 'CU2406',
        volume: 15,
        direction: '多',
        holdPrice: 68500.0,
        latestPrice: 69065.0,
        tradeTime: '2025-10-07 14:30:28',
        orderStatus: '全部成交',
        takeProfitPrice: 70000.0,
        stopLossPrice: 67500.0,
        margin: 102750.0,
        profitLoss: 850.0,
        profitLossRatio: 0.83,
        returnRate: 0.83
      }
    ],
    
    // === 参数配置 ===
    parameters: {
      trading: {
        lotSize: 2,
        maxOrders: 3,
        orderInterval: 120,
        enableCompound: false
      },
      risk: {
        stopLossPercent: 1.5,
        takeProfitPercent: 2.5,
        maxDrawdown: 8.0,
        riskRewardRatio: 1.8
      },
      indicator: {
        maPeriod: 30,
        maType: 'EMA',
        rsiPeriod: 10,
        enableMACD: false
      }
    },
    
    // === 风险控制 ===
    riskControl: {
      maxPosition: 30,
      stopLossRatio: 1.5,
      takeProfitRatio: 2.5,
      maxDrawdown: 8.0,
      maxLeverage: 2.0,
      riskLevel: '低'
    }
  },
  { 
    // === 基础字段 ===
    id: 'STR003', 
    name: '套利策略', 
    status: '运行中', 
    startTime: '2025-10-08 10:45:00',
    runningTime: '10h50m',
    
    // === 基础信息 ===
    description: '利用不同合约或市场间的价差进行套利交易，风险相对较低，收益稳定',
    author: '王五',
    createTime: '2025-10-03 11:00:00',
    lastModifyTime: '2025-10-08 08:30:00',
    
    // === 持仓信息 ===
    positions: [
      {
        contract: 'RB2406',
        volume: 25,
        direction: '多',
        holdPrice: 3850.0,
        latestPrice: 3875.0,
        tradeTime: '2025-10-08 11:05:45',
        orderStatus: '待成交',
        takeProfitPrice: 3900.0,
        stopLossPrice: 3820.0,
        margin: 96250.0,
        profitLoss: 625.0,
        profitLossRatio: 0.65,
        returnRate: 0.65
      },
      {
        contract: 'RB2409',
        volume: 25,
        direction: '空',
        holdPrice: 3880.0,
        latestPrice: 3850.0,
        tradeTime: '2025-10-08 13:22:18',
        orderStatus: '全部成交',
        takeProfitPrice: 3830.0,
        stopLossPrice: 3910.0,
        margin: 97000.0,
        profitLoss: 750.0,
        profitLossRatio: 0.77,
        returnRate: 0.77
      }
    ],
    
    // === 参数配置 ===
    parameters: {
      trading: {
        lotSize: 3,
        maxOrders: 10,
        orderInterval: 30,
        enableCompound: true
      },
      risk: {
        stopLossPercent: 0.8,
        takeProfitPercent: 1.5,
        maxDrawdown: 5.0,
        riskRewardRatio: 2.0
      },
      indicator: {
        maPeriod: 15,
        maType: 'WMA',
        rsiPeriod: 12,
        enableMACD: true
      }
    },
    
    // === 风险控制 ===
    riskControl: {
      maxPosition: 100,
      stopLossRatio: 0.8,
      takeProfitRatio: 1.5,
      maxDrawdown: 5.0,
      maxLeverage: 5.0,
      riskLevel: '高'
    }
  }
]

