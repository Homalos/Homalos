#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
策略开发模板
用途：为策略开发者提供标准化的策略开发框架
作者：Homalos Team
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import time

from .base_strategy import BaseStrategy
from ..core.object import TickData, BarData, OrderData, TradeData, PositionData
from ..core.object import OrderRequest, CancelRequest
from ..config.constant import Direction, Offset, OrderType, Exchange


@dataclass
class StrategyParams:
    """策略参数配置类"""
    # 基本参数
    symbol: str = "rb2501"  # 交易合约
    exchange: str = "SHFE"  # 交易所
    volume: int = 1  # 交易手数
    
    # 策略专用参数（示例）
    fast_period: int = 5  # 快线周期
    slow_period: int = 20  # 慢线周期
    stop_loss: float = 50.0  # 止损点数
    take_profit: float = 100.0  # 止盈点数
    
    # 风控参数
    max_position: int = 10  # 最大持仓
    max_daily_loss: float = 1000.0  # 最大日亏损


class StrategyTemplate(BaseStrategy):
    """
    策略开发模板
    
    这是一个完整的策略开发模板，包含：
    1. 参数配置管理
    2. 数据管理和指标计算
    3. 信号生成逻辑
    4. 订单管理
    5. 风险控制
    6. 状态监控
    
    开发者可以基于此模板快速开发自己的策略
    """
    
    # 策略元信息
    strategy_name = "策略开发模板"
    strategy_version = "1.0.0"
    strategy_author = "开发者姓名"
    strategy_description = "这是一个策略开发模板，展示了完整的策略开发框架"
    
    def __init__(self, strategy_id: str, event_bus, params: Dict[str, Any]):
        super().__init__(strategy_id, event_bus, params)
        
        # 解析策略参数
        self.strategy_params = StrategyParams()
        self._load_strategy_params(params)
        
        # 数据存储
        self.tick_data: Dict[str, TickData] = {}  # 最新tick数据
        self.bar_data: List[BarData] = []  # K线数据
        self.indicators: Dict[str, Any] = {}  # 技术指标
        
        # 交易状态
        self.current_position = 0  # 当前持仓
        self.pending_orders: Dict[str, OrderData] = {}  # 挂单记录
        self.trade_history: List[TradeData] = []  # 成交记录
        
        # 策略状态
        self.last_signal_time = 0  # 最后信号时间
        self.daily_pnl = 0.0  # 当日盈亏
        self.total_pnl = 0.0  # 总盈亏
        
        # 风控状态
        self.stop_loss_price: Optional[float] = None
        self.take_profit_price: Optional[float] = None
        
        self.write_log(f"策略模板初始化完成: {self.strategy_params}")
    
    def _load_strategy_params(self, params: Dict[str, Any]) -> None:
        """加载策略参数"""
        for key, value in params.items():
            if hasattr(self.strategy_params, key):
                setattr(self.strategy_params, key, value)
                self.write_log(f"参数设置: {key} = {value}")
    
    async def on_init(self) -> None:
        """策略初始化"""
        self.write_log("开始策略初始化...")
        
        # 订阅行情数据
        symbols = [self.strategy_params.symbol]
        await self.subscribe_market_data(symbols)
        
        # 初始化技术指标
        self._init_indicators()
        
        # 加载历史数据（如果需要）
        await self._load_historical_data()
        
        self.write_log("策略初始化完成")
    
    async def on_start(self) -> None:
        """策略启动"""
        self.write_log("策略开始运行...")
        self.status = "running"
    
    async def on_stop(self) -> None:
        """策略停止"""
        self.write_log("策略停止运行...")
        
        # 平仓所有持仓
        await self._close_all_positions()
        
        # 撤销所有挂单
        await self._cancel_all_orders()
        
        self.status = "stopped"
    
    async def on_tick(self, tick: TickData) -> None:
        """处理tick数据"""
        if tick.symbol != self.strategy_params.symbol:
            return
        
        # 更新tick数据
        self.tick_data[tick.symbol] = tick
        
        # 更新技术指标
        self._update_indicators(tick)
        
        # 风控检查
        if not self._risk_check(tick):
            return
        
        # 生成交易信号
        signal = self._generate_signal(tick)
        
        # 执行交易逻辑
        await self._execute_signal(signal, tick)
    
    async def on_bar(self, bar: BarData) -> None:
        """处理K线数据"""
        if bar.symbol != self.strategy_params.symbol:
            return
        
        # 保存K线数据
        self.bar_data.append(bar)
        
        # 限制数据长度
        if len(self.bar_data) > 200:
            self.bar_data = self.bar_data[-200:]
        
        # 基于K线的信号生成（如果需要）
        # signal = self._generate_bar_signal(bar)
        # await self._execute_signal(signal, bar)
    
    async def on_order(self, order: OrderData) -> None:
        """处理订单回报"""
        self.write_log(f"订单回报: {order.order_id} {order.status}")
        
        # 更新挂单记录
        if order.order_id in self.pending_orders:
            self.pending_orders[order.order_id] = order
            
            # 如果订单完成，从挂单记录中移除
            if order.status in ["完全成交", "已撤销"]:
                del self.pending_orders[order.order_id]
    
    async def on_trade(self, trade: TradeData) -> None:
        """处理成交回报"""
        self.write_log(f"成交回报: {trade.trade_id} {trade.direction} {trade.volume}@{trade.price}")
        
        # 记录成交
        self.trade_history.append(trade)
        
        # 更新持仓
        if trade.direction == Direction.LONG:
            if trade.offset == Offset.OPEN:
                self.current_position += trade.volume
            else:  # 平仓
                self.current_position -= trade.volume
        else:  # SHORT
            if trade.offset == Offset.OPEN:
                self.current_position -= trade.volume
            else:  # 平仓
                self.current_position += trade.volume
        
        # 更新盈亏
        self._update_pnl(trade)
        
        # 更新止损止盈
        self._update_stop_levels()
        
        self.write_log(f"当前持仓: {self.current_position}, 当日盈亏: {self.daily_pnl:.2f}")
    
    def _init_indicators(self) -> None:
        """初始化技术指标"""
        self.indicators = {
            "sma_fast": [],  # 快速移动平均
            "sma_slow": [],  # 慢速移动平均
            "prices": [],    # 价格序列
            "volumes": []    # 成交量序列
        }
        
        self.write_log("技术指标初始化完成")
    
    def _update_indicators(self, tick: TickData) -> None:
        """更新技术指标"""
        # 添加最新价格
        self.indicators["prices"].append(tick.last_price)
        self.indicators["volumes"].append(tick.volume)
        
        # 限制数据长度
        max_length = max(self.strategy_params.slow_period + 10, 100)
        for key in self.indicators:
            if len(self.indicators[key]) > max_length:
                self.indicators[key] = self.indicators[key][-max_length:]
        
        # 计算移动平均
        prices = self.indicators["prices"]
        if len(prices) >= self.strategy_params.fast_period:
            fast_sma = sum(prices[-self.strategy_params.fast_period:]) / self.strategy_params.fast_period
            self.indicators["sma_fast"].append(fast_sma)
        
        if len(prices) >= self.strategy_params.slow_period:
            slow_sma = sum(prices[-self.strategy_params.slow_period:]) / self.strategy_params.slow_period
            self.indicators["sma_slow"].append(slow_sma)
    
    def _generate_signal(self, tick: TickData) -> str:
        """生成交易信号"""
        # 检查数据完整性
        if (len(self.indicators.get("sma_fast", [])) < 2 or 
            len(self.indicators.get("sma_slow", [])) < 2):
            return "HOLD"
        
        # 获取指标值
        fast_sma = self.indicators["sma_fast"][-1]
        slow_sma = self.indicators["sma_slow"][-1]
        prev_fast = self.indicators["sma_fast"][-2]
        prev_slow = self.indicators["sma_slow"][-2]
        
        # 生成信号逻辑（示例：均线交叉）
        if prev_fast <= prev_slow and fast_sma > slow_sma:
            return "BUY"  # 金叉买入
        elif prev_fast >= prev_slow and fast_sma < slow_sma:
            return "SELL"  # 死叉卖出
        else:
            return "HOLD"  # 持有
    
    async def _execute_signal(self, signal: str, tick: TickData) -> None:
        """执行交易信号"""
        current_time = time.time()
        
        # 防止频繁交易
        if current_time - self.last_signal_time < 60:  # 60秒内不重复交易
            return
        
        if signal == "BUY" and self.current_position < self.strategy_params.max_position:
            await self._place_buy_order(tick.last_price)
            self.last_signal_time = current_time
            
        elif signal == "SELL" and self.current_position > -self.strategy_params.max_position:
            await self._place_sell_order(tick.last_price)
            self.last_signal_time = current_time
    
    async def _place_buy_order(self, price: float) -> None:
        """下买单"""
        order_request = OrderRequest(
            symbol=self.strategy_params.symbol,
            exchange=Exchange.SHFE,  # 根据实际情况调整
            direction=Direction.LONG,
            type=OrderType.LIMIT,
            volume=self.strategy_params.volume,
            price=price,
            offset=Offset.OPEN if self.current_position >= 0 else Offset.CLOSE
        )
        
        order_id = await self.send_order(order_request)
        if order_id:
            self.write_log(f"买入订单已发送: {order_id} @ {price}")
    
    async def _place_sell_order(self, price: float) -> None:
        """下卖单"""
        order_request = OrderRequest(
            symbol=self.strategy_params.symbol,
            exchange=Exchange.SHFE,  # 根据实际情况调整
            direction=Direction.SHORT,
            type=OrderType.LIMIT,
            volume=self.strategy_params.volume,
            price=price,
            offset=Offset.OPEN if self.current_position <= 0 else Offset.CLOSE
        )
        
        order_id = await self.send_order(order_request)
        if order_id:
            self.write_log(f"卖出订单已发送: {order_id} @ {price}")
    
    def _risk_check(self, tick: TickData) -> bool:
        """风险检查"""
        # 检查日亏损限制
        if self.daily_pnl < -self.strategy_params.max_daily_loss:
            self.write_log("达到日亏损限制，停止交易")
            return False
        
        # 检查止损
        if self.stop_loss_price and self.current_position != 0:
            if (self.current_position > 0 and tick.last_price <= self.stop_loss_price) or \
               (self.current_position < 0 and tick.last_price >= self.stop_loss_price):
                asyncio.create_task(self._trigger_stop_loss())
                return False
        
        # 检查止盈
        if self.take_profit_price and self.current_position != 0:
            if (self.current_position > 0 and tick.last_price >= self.take_profit_price) or \
               (self.current_position < 0 and tick.last_price <= self.take_profit_price):
                asyncio.create_task(self._trigger_take_profit())
                return False
        
        return True
    
    async def _trigger_stop_loss(self) -> None:
        """触发止损"""
        self.write_log("触发止损平仓")
        await self._close_all_positions()
        self.stop_loss_price = None
        self.take_profit_price = None
    
    async def _trigger_take_profit(self) -> None:
        """触发止盈"""
        self.write_log("触发止盈平仓")
        await self._close_all_positions()
        self.stop_loss_price = None
        self.take_profit_price = None
    
    def _update_stop_levels(self) -> None:
        """更新止损止盈价位"""
        if self.current_position == 0:
            self.stop_loss_price = None
            self.take_profit_price = None
            return
        
        if not self.trade_history:
            return
        
        # 获取最新成交价
        last_trade = self.trade_history[-1]
        entry_price = last_trade.price
        
        if self.current_position > 0:  # 多头持仓
            self.stop_loss_price = entry_price - self.strategy_params.stop_loss
            self.take_profit_price = entry_price + self.strategy_params.take_profit
        else:  # 空头持仓
            self.stop_loss_price = entry_price + self.strategy_params.stop_loss
            self.take_profit_price = entry_price - self.strategy_params.take_profit
    
    def _update_pnl(self, trade: TradeData) -> None:
        """更新盈亏"""
        # 简化的盈亏计算（实际应考虑手续费、保证金等）
        if len(self.trade_history) >= 2:
            prev_trade = self.trade_history[-2]
            if trade.direction != prev_trade.direction:  # 平仓交易
                pnl = abs(trade.price - prev_trade.price) * trade.volume
                if (prev_trade.direction == Direction.LONG and trade.price > prev_trade.price) or \
                   (prev_trade.direction == Direction.SHORT and trade.price < prev_trade.price):
                    self.daily_pnl += pnl
                    self.total_pnl += pnl
                else:
                    self.daily_pnl -= pnl
                    self.total_pnl -= pnl
    
    async def _load_historical_data(self) -> None:
        """加载历史数据（可选实现）"""
        # 这里可以实现从数据库或外部数据源加载历史数据
        # 用于策略的预热和回测
        pass
    
    async def _close_all_positions(self) -> None:
        """平仓所有持仓"""
        if self.current_position == 0:
            return
        
        if self.current_position > 0:
            # 平多头
            order_request = OrderRequest(
                symbol=self.strategy_params.symbol,
                exchange=Exchange.SHFE,
                direction=Direction.SHORT,
                type=OrderType.MARKET,
                volume=abs(self.current_position),
                price=0,  # 市价单
                offset=Offset.CLOSE
            )
        else:
            # 平空头
            order_request = OrderRequest(
                symbol=self.strategy_params.symbol,
                exchange=Exchange.SHFE,
                direction=Direction.LONG,
                type=OrderType.MARKET,
                volume=abs(self.current_position),
                price=0,  # 市价单
                offset=Offset.CLOSE
            )
        
        order_id = await self.send_order(order_request)
        if order_id:
            self.write_log(f"平仓订单已发送: {order_id}")
    
    async def _cancel_all_orders(self) -> None:
        """撤销所有挂单"""
        for order_id in list(self.pending_orders.keys()):
            cancel_request = CancelRequest(
                order_id=order_id,
                symbol=self.strategy_params.symbol,
                exchange=Exchange.SHFE
            )
            await self.cancel_order(cancel_request)
            self.write_log(f"撤单请求已发送: {order_id}")
    
    def get_strategy_status(self) -> Dict[str, Any]:
        """获取策略状态"""
        return {
            "strategy_name": self.strategy_name,
            "strategy_id": self.strategy_id,
            "status": self.status,
            "current_position": self.current_position,
            "daily_pnl": self.daily_pnl,
            "total_pnl": self.total_pnl,
            "pending_orders": len(self.pending_orders),
            "trade_count": len(self.trade_history),
            "parameters": self.strategy_params.__dict__,
            "indicators": {
                "fast_sma": self.indicators.get("sma_fast", [])[-1] if self.indicators.get("sma_fast") else 0,
                "slow_sma": self.indicators.get("sma_slow", [])[-1] if self.indicators.get("sma_slow") else 0,
            },
            "stop_loss_price": self.stop_loss_price,
            "take_profit_price": self.take_profit_price
        }


# 策略类的别名，用于动态加载
Strategy = StrategyTemplate 