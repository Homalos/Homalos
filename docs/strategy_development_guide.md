# Homalos量化交易策略开发指南

## 1. 概述

本指南旨在帮助开发者快速上手Homalos量化交易系统的策略开发。通过本指南，您将学会如何：
- 创建自定义交易策略
- 理解策略生命周期
- 实现风险管理
- 进行策略测试和调试

## 2. 快速开始

### 2.1 使用策略模板

我们提供了完整的策略开发模板 `src/strategies/strategy_template.py`，推荐基于此模板开发策略：

```bash
# 复制模板创建新策略
cp src/strategies/strategy_template.py src/strategies/my_strategy.py
```

### 2.2 策略基本结构

```python
from .base_strategy import BaseStrategy

class MyStrategy(BaseStrategy):
    strategy_name = "我的策略"
    strategy_version = "1.0.0"
    strategy_author = "您的姓名"
    
    def __init__(self, strategy_id: str, event_bus, params: Dict[str, Any]):
        super().__init__(strategy_id, event_bus, params)
        # 初始化代码
    
    async def on_init(self) -> None:
        """策略初始化"""
        pass
    
    async def on_start(self) -> None:
        """策略启动"""
        pass
    
    async def on_tick(self, tick: TickData) -> None:
        """处理实时行情"""
        pass

# 重要：必须有这个别名用于动态加载
Strategy = MyStrategy
```

## 3. 策略生命周期

### 3.1 生命周期阶段

1. **初始化 (Initialize)**: `on_init()`
   - 订阅行情数据
   - 初始化技术指标
   - 加载历史数据

2. **启动 (Start)**: `on_start()`
   - 策略开始运行
   - 设置初始状态

3. **运行 (Running)**: 
   - `on_tick()`: 处理实时行情
   - `on_bar()`: 处理K线数据
   - `on_order()`: 处理订单回报
   - `on_trade()`: 处理成交回报

4. **停止 (Stop)**: `on_stop()`
   - 平仓所有持仓
   - 撤销所有挂单
   - 清理资源

### 3.2 生命周期流程图

```
[创建] -> [初始化] -> [启动] -> [运行] -> [停止] -> [销毁]
   |         |         |        |        |        |
   v         v         v        v        v        v
__init__  on_init   on_start  on_tick  on_stop   cleanup
                              on_bar
                              on_order
                              on_trade
```

## 4. 核心功能实现

### 4.1 行情数据订阅

```python
async def on_init(self) -> None:
    # 订阅单个合约
    await self.subscribe_market_data(["rb2501"])
    
    # 订阅多个合约
    await self.subscribe_market_data(["rb2501", "hc2501", "i2501"])
```

### 4.2 技术指标计算

```python
def _calculate_moving_average(self, prices: List[float], period: int) -> float:
    """计算移动平均"""
    if len(prices) < period:
        return 0.0
    return sum(prices[-period:]) / period

def _calculate_rsi(self, prices: List[float], period: int = 14) -> float:
    """计算RSI指标"""
    if len(prices) < period + 1:
        return 50.0
    
    gains = []
    losses = []
    
    for i in range(1, len(prices)):
        diff = prices[i] - prices[i-1]
        if diff > 0:
            gains.append(diff)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(-diff)
    
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    
    if avg_loss == 0:
        return 100.0
    
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))
```

### 4.3 交易信号生成

```python
def _generate_signal(self, tick: TickData) -> str:
    """生成交易信号"""
    # 确保有足够的数据
    if len(self.price_history) < self.slow_period:
        return "HOLD"
    
    # 计算技术指标
    fast_ma = self._calculate_moving_average(self.price_history, self.fast_period)
    slow_ma = self._calculate_moving_average(self.price_history, self.slow_period)
    
    # 生成信号
    if fast_ma > slow_ma and self.current_position <= 0:
        return "BUY"
    elif fast_ma < slow_ma and self.current_position >= 0:
        return "SELL"
    else:
        return "HOLD"
```

### 4.4 订单管理

```python
async def _place_order(self, direction: Direction, price: float, volume: int):
    """下单"""
    order_request = OrderRequest(
        symbol=self.symbol,
        exchange=self.exchange,
        direction=direction,
        type=OrderType.LIMIT,
        volume=volume,
        price=price,
        offset=self._determine_offset(direction)
    )
    
    order_id = await self.send_order(order_request)
    if order_id:
        self.pending_orders[order_id] = order_request
        self.write_log(f"订单已发送: {order_id}")
    return order_id

def _determine_offset(self, direction: Direction) -> Offset:
    """确定开平方向"""
    if self.current_position == 0:
        return Offset.OPEN
    elif (direction == Direction.LONG and self.current_position < 0) or \
         (direction == Direction.SHORT and self.current_position > 0):
        return Offset.CLOSE
    else:
        return Offset.OPEN
```

## 5. 风险管理

### 5.1 基础风控

```python
def _risk_check(self, tick: TickData) -> bool:
    """风险检查"""
    # 检查最大持仓
    if abs(self.current_position) >= self.max_position:
        return False
    
    # 检查日亏损限制
    if self.daily_pnl < -self.max_daily_loss:
        self.write_log("触发日亏损限制")
        return False
    
    # 检查交易时间
    if not self._is_trading_time():
        return False
    
    return True

def _is_trading_time(self) -> bool:
    """检查是否在交易时间"""
    import datetime
    now = datetime.datetime.now()
    
    # 简化的交易时间检查
    if now.hour < 9 or now.hour > 15:
        return False
    
    return True
```

### 5.2 止损止盈

```python
def _update_stop_levels(self) -> None:
    """更新止损止盈"""
    if self.current_position == 0:
        self.stop_loss_price = None
        self.take_profit_price = None
        return
    
    entry_price = self.get_average_entry_price()
    
    if self.current_position > 0:  # 多头
        self.stop_loss_price = entry_price - self.stop_loss_points
        self.take_profit_price = entry_price + self.take_profit_points
    else:  # 空头
        self.stop_loss_price = entry_price + self.stop_loss_points
        self.take_profit_price = entry_price - self.take_profit_points

async def _check_stop_conditions(self, tick: TickData) -> None:
    """检查止损止盈条件"""
    if self.current_position == 0:
        return
    
    # 止损检查
    if self.stop_loss_price:
        if (self.current_position > 0 and tick.last_price <= self.stop_loss_price) or \
           (self.current_position < 0 and tick.last_price >= self.stop_loss_price):
            await self._trigger_stop_loss()
    
    # 止盈检查
    if self.take_profit_price:
        if (self.current_position > 0 and tick.last_price >= self.take_profit_price) or \
           (self.current_position < 0 and tick.last_price <= self.take_profit_price):
            await self._trigger_take_profit()
```

## 6. 参数管理

### 6.1 参数配置

```python
@dataclass
class StrategyParams:
    # 交易参数
    symbol: str = "rb2501"
    volume: int = 1
    
    # 技术指标参数
    fast_period: int = 5
    slow_period: int = 20
    
    # 风控参数
    stop_loss: float = 50.0
    take_profit: float = 100.0
    max_position: int = 10
    max_daily_loss: float = 1000.0

def _load_strategy_params(self, params: Dict[str, Any]) -> None:
    """加载策略参数"""
    for key, value in params.items():
        if hasattr(self.strategy_params, key):
            setattr(self.strategy_params, key, value)
            self.write_log(f"参数更新: {key} = {value}")
```

### 6.2 动态参数调整

```python
async def update_parameters(self, new_params: Dict[str, Any]) -> bool:
    """动态更新参数"""
    try:
        for key, value in new_params.items():
            if hasattr(self.strategy_params, key):
                old_value = getattr(self.strategy_params, key)
                setattr(self.strategy_params, key, value)
                self.write_log(f"参数更新: {key} {old_value} -> {value}")
        
        # 重新初始化相关组件
        await self._reinitialize_indicators()
        return True
        
    except Exception as e:
        self.write_log(f"参数更新失败: {e}")
        return False
```

## 7. 日志和监控

### 7.1 日志记录

```python
# 使用不同级别的日志
self.write_log("普通信息", level="info")
self.write_log("警告信息", level="warning") 
self.write_log("错误信息", level="error")

# 记录重要事件
self.write_log(f"开仓: {direction} {volume}手 @ {price}")
self.write_log(f"平仓: 盈亏 {pnl:.2f}")
self.write_log(f"风控触发: {reason}")
```

### 7.2 状态监控

```python
def get_strategy_status(self) -> Dict[str, Any]:
    """获取策略状态"""
    return {
        "strategy_name": self.strategy_name,
        "status": self.status,
        "position": self.current_position,
        "pnl": {
            "daily": self.daily_pnl,
            "total": self.total_pnl
        },
        "orders": {
            "pending": len(self.pending_orders),
            "total": self.total_orders
        },
        "indicators": self._get_current_indicators(),
        "risk": {
            "stop_loss": self.stop_loss_price,
            "take_profit": self.take_profit_price
        }
    }
```

## 8. 测试和调试

### 8.1 策略加载测试

```python
# 通过Web API加载策略
POST /api/v1/strategies/load
{
    "strategy_path": "src/strategies/my_strategy.py",
    "strategy_id": "my_strategy_001",
    "params": {
        "symbol": "rb2501",
        "fast_period": 5,
        "slow_period": 20,
        "volume": 1
    }
}
```

### 8.2 模拟交易测试

```python
# 在策略中添加模拟模式
def __init__(self, strategy_id: str, event_bus, params: Dict[str, Any]):
    super().__init__(strategy_id, event_bus, params)
    self.simulation_mode = params.get("simulation", True)
    
async def send_order(self, order_request: OrderRequest) -> str:
    if self.simulation_mode:
        return await self._simulate_order(order_request)
    else:
        return await super().send_order(order_request)

async def _simulate_order(self, order_request: OrderRequest) -> str:
    """模拟订单执行"""
    order_id = f"SIM_{int(time.time())}"
    
    # 模拟订单成交
    trade_data = TradeData(
        trade_id=f"TRADE_{order_id}",
        order_id=order_id,
        symbol=order_request.symbol,
        direction=order_request.direction,
        volume=order_request.volume,
        price=order_request.price,
        datetime=datetime.now()
    )
    
    # 延迟模拟成交
    asyncio.create_task(self._delayed_trade_simulation(trade_data))
    return order_id
```

## 9. 性能优化

### 9.1 数据管理优化

```python
from collections import deque

class OptimizedStrategy(BaseStrategy):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # 使用deque限制数据长度，提高性能
        self.price_history = deque(maxlen=1000)
        self.volume_history = deque(maxlen=1000)
        
    def _update_data(self, tick: TickData):
        """高效的数据更新"""
        self.price_history.append(tick.last_price)
        self.volume_history.append(tick.volume)
```

### 9.2 计算优化

```python
class CachedIndicators:
    """缓存技术指标计算结果"""
    
    def __init__(self):
        self._cache = {}
        self._last_update = {}
    
    def get_sma(self, prices: deque, period: int) -> float:
        cache_key = f"sma_{period}_{len(prices)}"
        
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        if len(prices) < period:
            return 0.0
        
        result = sum(list(prices)[-period:]) / period
        self._cache[cache_key] = result
        return result
```

## 10. 常见问题和解决方案

### 10.1 策略加载失败

**问题**: 策略无法加载
**解决方案**:
1. 检查文件路径是否正确
2. 确保策略类有 `Strategy = MyStrategy` 别名
3. 检查import语句是否正确
4. 查看日志文件获取详细错误信息

### 10.2 行情数据接收异常

**问题**: 没有收到行情数据
**解决方案**:
1. 检查合约代码是否正确
2. 确认已调用 `subscribe_market_data()`
3. 检查网关连接状态
4. 验证交易时间

### 10.3 订单执行失败

**问题**: 订单无法执行
**解决方案**:
1. 检查账户余额和可用资金
2. 验证价格和数量的合理性
3. 确认开平仓方向正确
4. 检查风控规则是否阻止交易

## 11. 最佳实践

### 11.1 代码组织

1. **模块化设计**: 将不同功能拆分到不同方法中
2. **参数外部化**: 所有策略参数都应该可配置
3. **错误处理**: 所有外部调用都要有异常处理
4. **日志记录**: 记录关键操作和决策过程

### 11.2 测试策略

1. **先模拟后实盘**: 在模拟环境充分测试后再上实盘
2. **小资金验证**: 用小资金验证策略的实际表现
3. **监控关键指标**: 关注胜率、盈亏比、最大回撤等
4. **及时止损**: 设置合理的止损机制

### 11.3 风险控制

1. **资金管理**: 合理控制单次交易资金比例
2. **仓位管理**: 避免过度集中持仓
3. **时间控制**: 设置策略运行时间窗口
4. **监控告警**: 设置异常情况的告警机制

## 12. 示例策略

查看以下示例策略文件了解具体实现：

- `src/strategies/minimal_strategy.py` - 最简单的策略示例
- `src/strategies/moving_average_strategy.py` - 移动平均策略
- `src/strategies/grid_trading_strategy.py` - 网格交易策略
- `src/strategies/strategy_template.py` - 完整功能模板

## 13. 技术支持

如果在开发过程中遇到问题，可以：

1. 查看系统日志文件 `logs/homalos_*.log`
2. 使用Web界面的策略管理功能
3. 参考现有策略代码实现
4. 联系技术支持团队

---

祝您开发愉快！ 