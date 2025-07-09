#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos_v2
@FileName   : moving_average_strategy.py
@Date       : 2025/7/6 23:00
@Author     : Donny
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 移动平均策略 - 基于双均线交叉的交易策略
"""
from typing import Dict, Any

from src.strategies.base_strategy import BaseStrategy
from src.core.object import TickData, BarData, OrderData, TradeData, OrderRequest
from src.config.constant import Direction, Offset, OrderType, Exchange


class MovingAverageStrategy(BaseStrategy):
    """
    移动平均策略
    
    策略逻辑：
    1. 计算短期和长期移动平均线
    2. 当短期均线上穿长期均线时做多
    3. 当短期均线下穿长期均线时做空
    4. 集成风控和止损逻辑
    """
    
    strategy_name = "MovingAverageStrategy"
    authors = ["Donny"]
    version = "0.0.1"
    description = "基于移动平均线的双线交叉策略"
    
    def __init__(self, strategy_id: str, event_bus, params: Dict[str, Any] = None):
        # 默认参数
        default_params = {
            "symbol": "SA509",
            "exchange": "CZCE",
            "short_window": 5,     # 短期均线周期
            "long_window": 20,      # 长期均线周期
            "volume": 1,            # 交易手数
            "stop_loss": 0.02,      # 止损比例 2%
            "take_profit": 0.05,    # 止盈比例 5%
            "max_positions": 1      # 最大持仓数
        }
        
        if params:
            default_params.update(params)
        
        super().__init__(strategy_id, event_bus, default_params)
        
        # 策略数据
        self.prices = []  # 价格历史
        self.short_ma = 0.0  # 短期均线
        self.long_ma = 0.0   # 长期均线
        
        # 交易状态
        self.position = 0  # 当前持仓 (正数=多头, 负数=空头, 0=无持仓)
        self.entry_price = 0.0  # 入场价格
        self.last_signal = None  # 上一个信号
        
        # 订单管理
        self.active_orders = {}  # 活跃订单
        
    async def on_init(self):
        """策略初始化"""
        self.write_log("移动平均策略初始化")
        
        # 获取策略参数
        self.symbol = self.get_parameter("symbol")
        self.exchange = Exchange[self.get_parameter("exchange")]
        self.short_window = self.get_parameter("short_window")
        self.long_window = self.get_parameter("long_window")
        self.volume = self.get_parameter("volume")
        self.stop_loss = self.get_parameter("stop_loss")
        self.take_profit = self.get_parameter("take_profit")
        self.max_positions = self.get_parameter("max_positions")
        
        self.write_log(f"策略参数: {self.symbol}.{self.exchange.value}, "
                      f"短期={self.short_window}, 长期={self.long_window}, "
                      f"手数={self.volume}")
    
    async def on_start(self):
        """策略启动"""
        self.write_log("移动平均策略启动")
        
        # 订阅行情数据
        await self.subscribe_symbols([self.symbol])
        
        # 重置状态
        self.prices.clear()
        self.position = 0
        self.entry_price = 0.0
        self.last_signal = None
        self.active_orders.clear()
        
    async def on_stop(self):
        """策略停止"""
        self.write_log("移动平均策略停止")
        
        # 撤销所有活跃订单
        for order_id in list(self.active_orders.keys()):
            await self.cancel_order(order_id)
        
        # 平仓所有持仓
        if self.position != 0:
            await self.close_all_positions()
    
    async def on_tick(self, tick: TickData):
        """处理Tick数据"""
        if tick.symbol != self.symbol:
            return
        
        # 更新价格历史
        self.prices.append(tick.last_price)
        
        # 保持价格历史在合理长度
        if len(self.prices) > self.long_window * 2:
            self.prices = self.prices[-self.long_window * 2:]
        
        # 计算移动平均线
        if len(self.prices) >= self.long_window:
            self.short_ma = sum(self.prices[-self.short_window:]) / self.short_window
            self.long_ma = sum(self.prices[-self.long_window:]) / self.long_window
            
            # 生成交易信号
            await self.generate_signal(tick.last_price)
        
        # 检查止损止盈
        if self.position != 0:
            await self.check_stop_loss_take_profit(tick.last_price)
    
    async def on_bar(self, bar: BarData):
        """处理Bar数据（可选）"""
        if bar.symbol != self.symbol:
            return
        
        # 可以基于Bar数据进行更稳定的信号计算
        self.write_log(f"收到Bar数据: {bar.symbol} {bar.close_price}", "DEBUG")
    
    async def on_order(self, order: OrderData):
        """处理订单回报"""
        self.write_log(f"订单回报: {order.orderid} {order.status.value}")
        
        # 更新活跃订单状态
        if order.orderid in self.active_orders:
            if order.status.value in ["CANCELLED", "REJECTED"]:
                self.active_orders.pop(order.orderid, None)
                
    async def on_trade(self, trade: TradeData):
        """处理成交回报"""
        self.write_log(f"成交回报: {trade.symbol} {trade.direction.value} "
                      f"{trade.volume}@{trade.price}")
        
        # 更新持仓
        if trade.direction == Direction.LONG:
            if trade.offset == Offset.OPEN:
                self.position += trade.volume
                self.entry_price = trade.price
            elif trade.offset in [Offset.CLOSE, Offset.CLOSE_TODAY, Offset.CLOSE_YESTERDAY]:
                self.position -= trade.volume
        else:  # SHORT
            if trade.offset == Offset.OPEN:
                self.position -= trade.volume
                self.entry_price = trade.price
            elif trade.offset in [Offset.CLOSE, Offset.CLOSE_TODAY, Offset.CLOSE_YESTERDAY]:
                self.position += trade.volume
        
        # 移除已成交的订单
        if trade.orderid in self.active_orders:
            self.active_orders.pop(trade.orderid, None)
        
        self.write_log(f"当前持仓: {self.position}, 入场价: {self.entry_price}")
    
    async def generate_signal(self, current_price: float):
        """生成交易信号"""
        if self.short_ma == 0 or self.long_ma == 0:
            return
        
        # 计算信号
        if self.short_ma > self.long_ma:
            signal = "BUY"
        elif self.short_ma < self.long_ma:
            signal = "SELL"
        else:
            signal = None
        
        # 避免重复信号
        if signal == self.last_signal:
            return
        
        self.last_signal = signal
        
        # 记录信号
        self.write_log(f"交易信号: {signal}, 短期均线: {self.short_ma:.2f}, "
                      f"长期均线: {self.long_ma:.2f}, 当前价: {current_price:.2f}")
        
        # 执行交易逻辑
        if signal == "BUY":
            await self.on_buy_signal(current_price)
        elif signal == "SELL":
            await self.on_sell_signal(current_price)
    
    async def on_buy_signal(self, current_price: float):
        """处理买入信号"""
        # 检查是否已有持仓
        if self.position >= self.max_positions:
            self.write_log("已达最大持仓，跳过买入信号", "WARNING")
            return
        
        # 如果有空头持仓，先平仓
        if self.position < 0:
            await self.close_short_position(current_price)
        
        # 开多仓
        await self.open_long_position(current_price)
    
    async def on_sell_signal(self, current_price: float):
        """处理卖出信号"""
        # 检查是否已有持仓
        if self.position <= -self.max_positions:
            self.write_log("已达最大持仓，跳过卖出信号", "WARNING")
            return
        
        # 如果有多头持仓，先平仓
        if self.position > 0:
            await self.close_long_position(current_price)
        
        # 开空仓
        await self.open_short_position(current_price)
    
    async def open_long_position(self, price: float):
        """开多仓"""
        order_request = OrderRequest(
            symbol=self.symbol,
            exchange=self.exchange.value,
            direction=Direction.LONG,
            type=OrderType.LIMIT,
            volume=self.volume,
            price=price,
            offset=Offset.OPEN,
            reference=f"{self.strategy_id}_long_open"
        )
        
        order_id = await self.send_order(order_request)
        if order_id:
            self.active_orders[order_id] = order_request
            self.write_log(f"发送开多订单: {self.volume}@{price}")
    
    async def open_short_position(self, price: float):
        """开空仓"""
        order_request = OrderRequest(
            symbol=self.symbol,
            exchange=self.exchange.value,
            direction=Direction.SHORT,
            type=OrderType.LIMIT,
            volume=self.volume,
            price=price,
            offset=Offset.OPEN,
            reference=f"{self.strategy_id}_short_open"
        )
        
        order_id = await self.send_order(order_request)
        if order_id:
            self.active_orders[order_id] = order_request
            self.write_log(f"发送开空订单: {self.volume}@{price}")
    
    async def close_long_position(self, price: float):
        """平多仓"""
        if self.position <= 0:
            return
        
        order_request = OrderRequest(
            symbol=self.symbol,
            exchange=self.exchange.value,
            direction=Direction.SHORT,
            type=OrderType.LIMIT,
            volume=abs(self.position),
            price=price,
            offset=Offset.CLOSE,
            reference=f"{self.strategy_id}_long_close"
        )
        
        order_id = await self.send_order(order_request)
        if order_id:
            self.active_orders[order_id] = order_request
            self.write_log(f"发送平多订单: {abs(self.position)}@{price}")
    
    async def close_short_position(self, price: float):
        """平空仓"""
        if self.position >= 0:
            return
        
        order_request = OrderRequest(
            symbol=self.symbol,
            exchange=self.exchange.value,
            direction=Direction.LONG,
            type=OrderType.LIMIT,
            volume=abs(self.position),
            price=price,
            offset=Offset.CLOSE,
            reference=f"{self.strategy_id}_short_close"
        )
        
        order_id = await self.send_order(order_request)
        if order_id:
            self.active_orders[order_id] = order_request
            self.write_log(f"发送平空订单: {abs(self.position)}@{price}")
    
    async def close_all_positions(self):
        """平仓所有持仓"""
        if self.position > 0:
            # 获取最新价格
            latest_tick = self.get_latest_tick(self.symbol)
            price = latest_tick.last_price if latest_tick else self.entry_price
            await self.close_long_position(price)
        elif self.position < 0:
            # 获取最新价格
            latest_tick = self.get_latest_tick(self.symbol)
            price = latest_tick.last_price if latest_tick else self.entry_price
            await self.close_short_position(price)
    
    async def check_stop_loss_take_profit(self, current_price: float):
        """检查止损止盈"""
        if self.position == 0 or self.entry_price == 0:
            return
        
        # 计算盈亏比例
        if self.position > 0:  # 多头持仓
            pnl_ratio = (current_price - self.entry_price) / self.entry_price
        else:  # 空头持仓
            pnl_ratio = (self.entry_price - current_price) / self.entry_price
        
        # 止损
        if pnl_ratio <= -self.stop_loss:
            self.write_log(f"触发止损: 盈亏比例 {pnl_ratio:.3f}", "WARNING")
            await self.close_all_positions()
        
        # 止盈
        elif pnl_ratio >= self.take_profit:
            self.write_log(f"触发止盈: 盈亏比例 {pnl_ratio:.3f}")
            await self.close_all_positions() 