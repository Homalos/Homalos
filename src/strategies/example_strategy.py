#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : example_strategy.py
@Date       : 2025/5/28 15:11
@Author     : Donny
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description:
"""
import asyncio
from typing import Optional
from datetime import datetime, timedelta

from src.core.event_engine import EventEngine
from src.core.object import TickData, OrderRequest, CancelRequest, OrderData, TradeData
from src.config.constants import Direction, OrderType, Exchange, Offset
from .base_strategy import BaseStrategy
from src.core.event import Event, EventType
from src.util.logger import log

class ExampleStrategy(BaseStrategy):
    """
    一个简单的示例策略，用于演示策略的实现。
    """
    strategy_name: str = "策略示例"
    authors: list[str] = ["HomalosAI"]

    def __init__(self, main_engine, strategy_id, params=None):
        """
        初始化策略。

        :param main_engine: 主引擎实例，提供对事件引擎和网关的访问。
        :param strategy_id: 策略的唯一标识符。
        :param params: 策略的参数字典。
        """
        super().__init__(main_engine, strategy_id, params)
        self.last_tick_time: datetime | None = None
        self.order_sent = False
        self.symbol = self.params.get("symbol", "SA509")
        self.exchange = Exchange(self.params.get("exchange", "CZCE"))

    async def on_init(self):
        """策略初始化。"""
        self.write_log(f"策略 {self.strategy_id} 初始化完成。")

    async def on_start(self):
        """策略启动。"""
        self.write_log(f"策略 {self.strategy_id} 启动。")
        self.write_log(f"开始订阅行情: {self.symbol} @ {self.exchange.value}")
        await self.subscribe(self.symbol, self.exchange)

    async def on_stop(self):
        """策略停止。"""
        self.write_log(f"策略 {self.strategy_id} 停止。")

    async def on_tick(self, tick: TickData):
        """
        处理传入的tick数据。
        """
        # 确保只处理本策略订阅的合约
        if tick.symbol != self.symbol:
            return

        self.write_log(f"收到行情: {tick.symbol}, 价格: {tick.last_price}")
        
        current_time = tick.datetime

        if self.last_tick_time is None:
            self.last_tick_time = current_time

        # 简单逻辑：启动10秒后，如果没发过单，就发一个市价单
        if not self.order_sent and (current_time - self.last_tick_time > timedelta(seconds=10)):
            self.order_sent = True
            
            req = OrderRequest(
                symbol=tick.symbol,
                exchange=tick.exchange,
                direction=Direction.LONG,
                type=OrderType.MARKET,
                volume=1,
                offset=Offset.OPEN
            )
            await self.send_order(req)
            self.write_log(f"已为合约 {tick.symbol} 发送市价单")

    async def on_order_update(self, order_update):
        self.write_log(f"收到订单更新: {order_update.orderid} - 状态: {order_update.status.value}")

    async def on_trade_update(self, trade_update):
        self.write_log(f"收到成交回报: {trade_update.orderid} - 成交价: {trade_update.price}")

    async def on_trade(self, trade: TradeData):
        """处理成交回报。"""
        await super().on_trade(trade)
        if trade.symbol == self.symbol:
            self.write_log(f"策略 {self.strategy_id} 记录到成交: {trade.direction} {trade.volume} 手 {trade.symbol} @ {trade.price}")
            # 在这里可以更新策略的内部持仓等状态
            # 如果是买入成交，可能需要设置止损单或进入下一个状态
            if trade.direction == Direction.LONG:
                self.write_log("买入成交，示例策略将不再主动发单，等待手动停止或修改。")
                # self.order_sent = True # 标记，避免立即反向操作或重复操作（根据策略逻辑）
                # self.active_order_id = None # 成交后，原订单不再是活动挂单 

    async def on_order_update(self, order_update):
        self.write_log(f"策略 {self.strategy_id} 收到订单更新: {order_update}")

    async def on_trade_update(self, trade_update):
        self.write_log(f"策略 {self.strategy_id} 收到成交更新: {trade_update}") 