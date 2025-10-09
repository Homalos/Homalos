/**
 * 策略模板库（硬编码数据，模拟.py文件）
 */
export const strategyTemplates = [
  {
    fileName: 'trend_following_strategy.py',
    name: '趋势跟踪策略',
    description: '基于移动平均线和趋势线识别市场趋势方向，顺势而为，适合趋势明显的市场环境',
    author: '系统管理员',
    defaultRiskControl: {
      maxPosition: 50,
      stopLossRatio: 2.0,
      takeProfitRatio: 3.0,
      maxDrawdown: 10.0
    }
  },
  {
    fileName: 'mean_reversion_strategy.py',
    name: '均值回归策略',
    description: '当价格偏离均值过多时进行反向交易，预期价格会回归均值，适用于震荡市场',
    author: '系统管理员',
    defaultRiskControl: {
      maxPosition: 30,
      stopLossRatio: 1.5,
      takeProfitRatio: 2.5,
      maxDrawdown: 8.0
    }
  },
  {
    fileName: 'breakout_strategy.py',
    name: '突破策略',
    description: '监控关键支撑和阻力位，当价格突破时快速进场，捕捉强势行情',
    author: '系统管理员',
    defaultRiskControl: {
      maxPosition: 40,
      stopLossRatio: 2.5,
      takeProfitRatio: 4.0,
      maxDrawdown: 12.0
    }
  },
  {
    fileName: 'grid_trading_strategy.py',
    name: '网格交易策略',
    description: '在价格区间内设置多个网格，低买高卖，适合震荡行情下的稳健获利',
    author: '系统管理员',
    defaultRiskControl: {
      maxPosition: 60,
      stopLossRatio: 1.0,
      takeProfitRatio: 1.5,
      maxDrawdown: 6.0
    }
  },
  {
    fileName: 'volatility_strategy.py',
    name: '波动率策略',
    description: '基于市场波动率变化进行交易决策，在波动加剧时捕捉机会',
    author: '系统管理员',
    defaultRiskControl: {
      maxPosition: 35,
      stopLossRatio: 3.0,
      takeProfitRatio: 5.0,
      maxDrawdown: 15.0
    }
  }
]

