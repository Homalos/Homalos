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
        available: 10,
        direction: '多',
        holdPrice: 450.5,
        latestPrice: 462.3,
        tradeTime: '2025-10-08 09:15:32',
        takeProfitPrice: 460.0,
        stopLossPrice: 445.0,
        margin: 45050.0,
        marketValue: 462300.0,
        profitLoss: 1200.5,
        priceDiff: 11.8,
        markToMarketPL: 1180.0,
        profitLossRatio: 2.67,
        returnRate: 2.67
      },
      {
        contract: 'AG2406',
        volume: 20,
        available: 20,
        direction: '空',
        holdPrice: 5200.0,
        latestPrice: 5175.0,
        tradeTime: '2025-10-08 10:20:15',
        takeProfitPrice: 5100.0,
        stopLossPrice: 5250.0,
        margin: 104000.0,
        marketValue: 1035000.0,
        profitLoss: -500.0,
        priceDiff: -25.0,
        markToMarketPL: -500.0,
        profitLossRatio: -0.48,
        returnRate: -0.48
      }
    ],
    
    // === 委托列表 ===
    orders: [
      {
        orderTime: '2025-10-08 09:15:20',
        contract: 'AU2406',
        direction: '买',
        offset: '开仓',
        orderPrice: 450.5,
        orderVolume: 10,
        filledVolume: 10,
        cancelableVolume: 0,
        avgPrice: 450.5,
        status: 'filled',
        orderType: 'limit'
      },
      {
        orderTime: '2025-10-08 10:20:08',
        contract: 'AG2406',
        direction: '卖',
        offset: '开仓',
        orderPrice: 5200.0,
        orderVolume: 25,
        filledVolume: 20,
        cancelableVolume: 5,
        avgPrice: 5200.0,
        status: 'partiallyFilled',
        orderType: 'limit'
      },
      {
        orderTime: '2025-10-08 14:30:15',
        contract: 'CU2406',
        direction: '买',
        offset: '开仓',
        orderPrice: 68500.0,
        orderVolume: 5,
        filledVolume: 0,
        cancelableVolume: 5,
        avgPrice: null,
        status: 'submitted',
        orderType: 'limit'
      }
    ],
    
    // === 成交明细 ===
    trades: [
      {
        tradeTime: '2025-10-08 09:15:32',
        contract: 'AU2406',
        direction: '买',
        offset: '开仓',
        tradePrice: 450.5,
        tradeVolume: 10,
        tradeId: 'T202510080915320001',
        commission: 22.53,
        tradeType: 'normal'
      },
      {
        tradeTime: '2025-10-08 10:20:15',
        contract: 'AG2406',
        direction: '卖',
        offset: '开仓',
        tradePrice: 5200.0,
        tradeVolume: 20,
        tradeId: 'T202510081020150001',
        commission: 52.00,
        tradeType: 'normal'
      },
      {
        tradeTime: '2025-10-08 11:45:22',
        contract: 'AU2406',
        direction: '卖',
        offset: '平仓',
        tradePrice: 462.3,
        tradeVolume: 5,
        tradeId: 'T202510081145220001',
        commission: 11.56,
        tradeType: 'normal'
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
        available: 15,
        direction: '多',
        holdPrice: 68500.0,
        latestPrice: 69065.0,
        tradeTime: '2025-10-07 14:30:28',
        takeProfitPrice: 70000.0,
        stopLossPrice: 67500.0,
        margin: 102750.0,
        marketValue: 1035975.0,
        profitLoss: 850.0,
        priceDiff: 565.0,
        markToMarketPL: 8475.0,
        profitLossRatio: 0.83,
        returnRate: 0.83
      }
    ],
    
    // === 委托列表 ===
    orders: [
      {
        orderTime: '2025-10-07 14:30:15',
        contract: 'CU2406',
        direction: '买',
        offset: '开仓',
        orderPrice: 68500.0,
        orderVolume: 15,
        filledVolume: 15,
        cancelableVolume: 0,
        avgPrice: 68500.0,
        status: 'filled',
        orderType: 'market'
      },
      {
        orderTime: '2025-10-07 16:45:22',
        contract: 'AL2406',
        direction: '卖',
        offset: '开仓',
        orderPrice: 19200.0,
        orderVolume: 10,
        filledVolume: 0,
        cancelableVolume: 0,
        avgPrice: null,
        status: 'cancelled',
        orderType: 'limit'
      }
    ],
    
    // === 成交明细 ===
    trades: [
      {
        tradeTime: '2025-10-07 14:30:28',
        contract: 'CU2406',
        direction: '买',
        offset: '开仓',
        tradePrice: 68500.0,
        tradeVolume: 15,
        tradeId: 'T202510071430280001',
        commission: 51.38,
        tradeType: 'normal'
      },
      {
        tradeTime: '2025-10-07 15:20:10',
        contract: 'CU2406',
        direction: '卖',
        offset: '平仓',
        tradePrice: 68800.0,
        tradeVolume: 8,
        tradeId: 'T202510071520100001',
        commission: 27.52,
        tradeType: 'autoClose'
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
        available: 25,
        direction: '多',
        holdPrice: 3850.0,
        latestPrice: 3875.0,
        tradeTime: '2025-10-08 11:05:45',
        takeProfitPrice: 3900.0,
        stopLossPrice: 3820.0,
        margin: 96250.0,
        marketValue: 96875.0,
        profitLoss: 625.0,
        priceDiff: 25.0,
        markToMarketPL: 625.0,
        profitLossRatio: 0.65,
        returnRate: 0.65
      },
      {
        contract: 'RB2409',
        volume: 25,
        available: 25,
        direction: '空',
        holdPrice: 3880.0,
        latestPrice: 3850.0,
        tradeTime: '2025-10-08 13:22:18',
        takeProfitPrice: 3830.0,
        stopLossPrice: 3910.0,
        margin: 97000.0,
        marketValue: 96250.0,
        profitLoss: 750.0,
        priceDiff: -30.0,
        markToMarketPL: 750.0,
        profitLossRatio: 0.77,
        returnRate: 0.77
      }
    ],
    
    // === 委托列表 ===
    orders: [
      {
        orderTime: '2025-10-08 11:05:32',
        contract: 'RB2406',
        direction: '买',
        offset: '开仓',
        orderPrice: 3850.0,
        orderVolume: 25,
        filledVolume: 25,
        cancelableVolume: 0,
        avgPrice: 3850.0,
        status: 'filled',
        orderType: 'limit'
      },
      {
        orderTime: '2025-10-08 13:22:10',
        contract: 'RB2409',
        direction: '卖',
        offset: '开仓',
        orderPrice: 3880.0,
        orderVolume: 25,
        filledVolume: 25,
        cancelableVolume: 0,
        avgPrice: 3880.0,
        status: 'filled',
        orderType: 'limit'
      },
      {
        orderTime: '2025-10-08 15:30:00',
        contract: 'RB2406',
        direction: '卖',
        offset: '平仓',
        orderPrice: 3900.0,
        orderVolume: 10,
        filledVolume: 0,
        cancelableVolume: 0,
        avgPrice: null,
        status: 'rejected',
        orderType: 'conditional'
      },
      {
        orderTime: '2025-10-08 16:00:00',
        contract: 'I2406',
        direction: '买',
        offset: '开仓',
        orderPrice: 950.0,
        orderVolume: 30,
        filledVolume: 15,
        cancelableVolume: 15,
        avgPrice: 950.0,
        status: 'partiallyFilled',
        orderType: 'limit'
      }
    ],
    
    // === 成交明细 ===
    trades: [
      {
        tradeTime: '2025-10-08 11:05:45',
        contract: 'RB2406',
        direction: '买',
        offset: '开仓',
        tradePrice: 3850.0,
        tradeVolume: 25,
        tradeId: 'T202510081105450001',
        commission: 48.13,
        tradeType: 'normal'
      },
      {
        tradeTime: '2025-10-08 13:22:18',
        contract: 'RB2409',
        direction: '卖',
        offset: '开仓',
        tradePrice: 3880.0,
        tradeVolume: 25,
        tradeId: 'T202510081322180001',
        commission: 48.50,
        tradeType: 'normal'
      },
      {
        tradeTime: '2025-10-08 14:35:20',
        contract: 'RB2406',
        direction: '卖',
        offset: '平仓',
        tradePrice: 3875.0,
        tradeVolume: 10,
        tradeId: 'T202510081435200001',
        commission: 19.38,
        tradeType: 'cancelFilled'
      },
      {
        tradeTime: '2025-10-08 16:00:15',
        contract: 'I2406',
        direction: '买',
        offset: '开仓',
        tradePrice: 950.0,
        tradeVolume: 15,
        tradeId: 'T202510081600150001',
        commission: 7.13,
        tradeType: 'normal'
      },
      {
        tradeTime: '2025-10-08 16:05:30',
        contract: 'RB2409',
        direction: '买',
        offset: '平仓',
        tradePrice: 3850.0,
        tradeVolume: 25,
        tradeId: 'T202510081605300001',
        commission: 48.13,
        tradeType: 'forcedClose'
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

