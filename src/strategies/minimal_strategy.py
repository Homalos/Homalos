#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos_v2
@FileName   : minimal_strategy.py
@Date       : 2025/7/9 23:00
@Author     : Donny
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 最小策略 - 用于测试交易引擎全链路功能
"""
import time
from typing import Dict, Any

from src.config.constant import Direction, Offset, OrderType, Exchange
from src.core.object import TickData, BarData, OrderData, TradeData, OrderRequest
from src.strategies.base_strategy import BaseStrategy


class MinimalStrategy(BaseStrategy):
    """
    最小策略 - 用于测试交易引擎全链路
    
    策略逻辑：
    1. 每收到tick就下单买入1手（简单防刷单）
    2. 打印订单状态、成交回报、账户变化
    3. 用于验证交易引擎的完整功能
    """
    
    strategy_name = "MinimalStrategy"
    authors = ["Donny"]
    version = "0.0.1"
    description = "最小策略 - 用于测试交易引擎全链路功能"
    
    def __init__(self, strategy_id: str, event_bus, params: Dict[str, Any] | None = None):
        # 默认参数定义
        default_params = {
            "symbol": "FG509",
            "exchange": "CZCE",
            "volume": 1,            # 交易手数
            "order_interval": 10,   # 下单间隔（秒）
            "max_orders": 5         # 最大订单数
        }
        
        # 合并用户参数
        if params:
            default_params.update(params)
        
        # 先调用父类构造函数初始化self.params
        super().__init__(strategy_id, event_bus, default_params)
        
        # 再获取策略参数
        self.symbol = self.get_parameter("symbol")
        
        # 正确处理exchange参数：字符串转枚举
        exchange_str = self.get_parameter("exchange")
        if isinstance(exchange_str, str):
            self.exchange = Exchange[exchange_str]  # 字符串转枚举
        elif isinstance(exchange_str, Exchange):
            self.exchange = exchange_str  # 已经是枚举对象
        else:
            raise ValueError(f"无效的exchange参数: {exchange_str}")
            
        self.volume = self.get_parameter("volume", 1)
        self.order_interval = self.get_parameter("order_interval", 10)
        self.max_orders = self.get_parameter("max_orders", 5)
        
        # 策略状态初始化
        self.last_order_time = 0
        self.order_count = 0
        self.active_orders = {}  # 活跃订单管理
        
    async def on_init(self):
        """策略初始化"""
        self.write_log("最小策略初始化")
        self.write_log(f"策略参数: {self.symbol}.{self.exchange.value}, "
                      f"手数={self.volume}, 间隔={self.order_interval}秒")
    
    async def on_start(self):
        """策略启动"""
        self.write_log("最小策略启动")
        
        # 订阅行情数据
        await self.subscribe_symbols([self.symbol])
        
        # 重置状态
        self.last_order_time = 0
        self.order_count = 0
        
    async def on_stop(self):
        """策略停止"""
        self.write_log("最小策略停止")
        
        # 撤销所有活跃订单
        for order_id in list(self.active_orders.keys()):
            await self.cancel_order(order_id)
    
    async def on_tick(self, tick: TickData):
        """处理Tick数据"""
        if tick.symbol != self.symbol:
            return
        
        current_time = time.time()
        
        # 防刷单：检查时间间隔和订单数量
        if (current_time - self.last_order_time < self.order_interval or 
            self.order_count >= self.max_orders):
            return
        
        # 下单买入
        await self.place_buy_order(tick.last_price)
        
        # 更新状态
        self.last_order_time = current_time
        self.order_count += 1
    
    async def on_bar(self, bar: BarData):
        """处理Bar数据（可选）"""
        if bar.symbol != self.symbol:
            return
        
        self.write_log(f"收到Bar数据: {bar.symbol} {bar.close_price}", "DEBUG")
    
    async def on_order(self, order: OrderData):
        """处理订单回报"""
        status_value = order.status.value if order.status else "UNKNOWN"
        direction_value = order.direction.value if order.direction else "UNKNOWN"
        self.write_log(f"订单回报: {order.orderid} {status_value} "
                      f"{order.symbol} {direction_value} {order.volume}@{order.price}")
        
        # 更新活跃订单状态
        if order.orderid in self.active_orders:
            if status_value in ["CANCELLED", "REJECTED"]:
                self.active_orders.pop(order.orderid, None)
                self.write_log(f"订单已撤销/拒绝: {order.orderid}")
                
    async def on_trade(self, trade: TradeData):
        """处理成交回报"""
        direction_value = trade.direction.value if trade.direction else "UNKNOWN"
        self.write_log(f"成交回报: {trade.symbol} {direction_value} "
                      f"{trade.volume}@{trade.price} 成交ID:{trade.trade_id}")
        
        # 移除已成交的订单
        if trade.orderid in self.active_orders:
            self.active_orders.pop(trade.orderid, None)
            self.write_log(f"订单已成交: {trade.orderid}")
    
    async def place_buy_order(self, price: float):
        """下单买入"""
        order_request = OrderRequest(
            symbol=self.symbol,
            exchange=self.exchange,
            direction=Direction.LONG,
            type=OrderType.LIMIT,
            volume=self.volume,
            price=price,
            offset=Offset.OPEN,
            reference=f"{self.strategy_id}_buy_{self.order_count}"
        )
        
        order_id = await self.send_order(order_request)
        if order_id:
            self.active_orders[order_id] = order_request
            self.write_log(f"发送买入订单: {self.volume}@{price} (订单#{self.order_count})")
        else:
            self.write_log("发送订单失败", "ERROR")
    
    def _sync_on_tick(self, tick_data: TickData):
        """同步版本的tick处理 - 应急回退逻辑"""
        if tick_data.symbol != self.symbol:
            return
        
        current_time = time.time()
        
        # 防刷单：检查时间间隔和订单数量
        if (current_time - self.last_order_time < self.order_interval or 
            self.order_count >= self.max_orders):
            return
        
        # 同步版本的下单逻辑
        self._sync_place_buy_order(tick_data.last_price)
        
        # 更新状态
        self.last_order_time = current_time
        self.order_count += 1
    
    def _sync_place_buy_order(self, price: float):
        """同步版本的下单 - 发布策略信号事件"""
        # 创建订单请求
        order_request = OrderRequest(
            symbol=self.symbol,
            exchange=self.exchange,
            direction=Direction.LONG,
            type=OrderType.LIMIT,
            volume=self.volume,
            price=price,
            offset=Offset.OPEN,
            reference=f"{self.strategy_id}_sync_buy_{self.order_count}"
        )
        
        # 发布策略信号事件（让交易引擎处理）
        signal_data = {
            "strategy_id": self.strategy_id,
            "action": "place_order",
            "order_request": order_request,
            "timestamp": time.time()
        }
        
        # 通过事件总线发布信号
        try:
            from src.core.event import create_trading_event
            
            event = create_trading_event(
                "strategy.signal",
                signal_data,
                "MinimalStrategy"
            )
            
            if hasattr(self.event_bus, 'publish'):
                self.event_bus.publish(event)
                self.write_log(f"发送同步买入信号: {self.volume}@{price} (订单#{self.order_count})")
            else:
                self.write_log("事件总线不可用", "ERROR")
                
        except Exception as e:
            self.write_log(f"发送策略信号失败: {e}", "ERROR")


# 为策略管理器提供兼容性别名
Strategy = MinimalStrategy
