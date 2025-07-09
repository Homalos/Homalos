#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos_v2
@FileName   : grid_trading_strategy.py
@Date       : 2025/7/6 23:00
@Author     : Donny
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 网格交易策略 - 基于价格网格的震荡交易策略
"""
import asyncio
from typing import Dict, Any

from src.strategies.base_strategy import BaseStrategy
from src.core.object import TickData, BarData, OrderData, TradeData, OrderRequest
from src.config.constant import Direction, Offset, OrderType, Exchange


class GridTradingStrategy(BaseStrategy):
    """
    网格交易策略
    
    策略逻辑：
    1. 在价格网格上下买卖
    2. 价格下跌时买入，上涨时卖出
    3. 通过频繁交易获取价差收益
    """
    
    strategy_name = "GridTradingStrategy"
    authors = ["Donny"]
    version = "0.0.1"
    description = "基于价格网格的震荡交易策略"
    
    def __init__(self, strategy_id: str, event_bus, params: Dict[str, Any] = None):
        # 默认参数
        default_params = {
            "symbol": "FG509",
            "exchange": "CZCE",
            "grid_spacing": 10.0,   # 网格间距
            "grid_count": 5,        # 网格数量
            "base_volume": 1,       # 基础交易量
            "center_price": 0.0     # 网格中心价格(0表示自动设置)
        }
        
        if params:
            default_params.update(params)
        
        super().__init__(strategy_id, event_bus, default_params)
        
        # 网格数据
        self.grid_levels = []  # 网格价位
        self.grid_orders = {}  # 网格订单 {price: order_id}
        self.center_price = 0.0
        
    async def on_init(self):
        """策略初始化"""
        self.write_log("网格交易策略初始化")
        
        # 获取策略参数
        self.symbol = self.get_parameter("symbol")
        self.exchange = Exchange[self.get_parameter("exchange")]
        self.grid_spacing = self.get_parameter("grid_spacing")
        self.grid_count = self.get_parameter("grid_count")
        self.base_volume = self.get_parameter("base_volume")
        self.center_price = self.get_parameter("center_price")
        
    async def on_start(self):
        """策略启动"""
        self.write_log("网格交易策略启动")
        
        # 订阅行情数据
        await self.subscribe_symbols([self.symbol])
        
        # 初始化网格
        if self.center_price == 0.0:
            # 等待第一个Tick来设置中心价格
            self.write_log("等待行情数据来设置网格中心价格")
        else:
            self.setup_grid()
    
    async def on_stop(self):
        """策略停止"""
        self.write_log("网格交易策略停止")
        
        # 撤销所有网格订单
        for order_id in list(self.grid_orders.values()):
            if order_id:
                await self.cancel_order(order_id)
    
    async def on_tick(self, tick: TickData):
        """处理Tick数据"""
        if tick.symbol != self.symbol:
            return
        
        # 第一次收到行情时设置网格
        if self.center_price == 0.0:
            self.center_price = tick.last_price
            self.setup_grid()
            await self.place_grid_orders(tick.last_price)
        
        # 检查网格订单状态
        await self.check_grid_orders(tick.last_price)
    
    async def on_trade(self, trade: TradeData):
        """处理成交回报"""
        self.write_log(f"网格成交: {trade.symbol} {trade.direction.value} "
                      f"{trade.volume}@{trade.price}")
        
        # 重新在对应价位下单
        await self.replace_grid_order(trade.price, trade.direction)
    
    def setup_grid(self):
        """设置网格价位"""
        self.grid_levels = []
        
        # 计算网格价位
        for i in range(-self.grid_count, self.grid_count + 1):
            price = self.center_price + i * self.grid_spacing
            if price > 0:  # 确保价格为正
                self.grid_levels.append(price)
        
        self.grid_levels.sort()
        self.write_log(f"网格设置完成: 中心价格 {self.center_price}, "
                      f"网格数量 {len(self.grid_levels)}")
    
    async def place_grid_orders(self, current_price: float):
        """下网格订单"""
        for price in self.grid_levels:
            if price < current_price:
                # 在当前价格下方下买单
                await self.place_grid_buy_order(price)
            elif price > current_price:
                # 在当前价格上方下卖单
                await self.place_grid_sell_order(price)
    
    async def place_grid_buy_order(self, price: float):
        """下网格买单"""
        order_request = OrderRequest(
            symbol=self.symbol,
            exchange=self.exchange.value,
            direction=Direction.LONG,
            type=OrderType.LIMIT,
            volume=self.base_volume,
            price=price,
            offset=Offset.OPEN,
            reference=f"{self.strategy_id}_grid_buy_{price}"
        )
        
        order_id = await self.send_order(order_request)
        if order_id:
            self.grid_orders[price] = order_id
    
    async def place_grid_sell_order(self, price: float):
        """下网格卖单"""
        order_request = OrderRequest(
            symbol=self.symbol,
            exchange=self.exchange.value,
            direction=Direction.SHORT,
            type=OrderType.LIMIT,
            volume=self.base_volume,
            price=price,
            offset=Offset.OPEN,
            reference=f"{self.strategy_id}_grid_sell_{price}"
        )
        
        order_id = await self.send_order(order_request)
        if order_id:
            self.grid_orders[price] = order_id
    
    async def replace_grid_order(self, price: float, direction: Direction):
        """重新下网格订单"""
        # 移除旧订单记录
        self.grid_orders.pop(price, None)
        
        # 等待一段时间后重新下单
        await asyncio.sleep(1)
        
        if direction == Direction.LONG:
            # 买单成交后，在更高价位下卖单
            higher_price = price + self.grid_spacing
            if higher_price in self.grid_levels:
                await self.place_grid_sell_order(higher_price)
        else:
            # 卖单成交后，在更低价位下买单
            lower_price = price - self.grid_spacing
            if lower_price in self.grid_levels:
                await self.place_grid_buy_order(lower_price)
    
    async def check_grid_orders(self, current_price: float):
        """检查网格订单状态"""
        # 这里可以添加网格订单的监控和管理逻辑
        pass
