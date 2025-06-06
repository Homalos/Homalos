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

from src.core.event_engine import EventEngine
from src.core.object import TickData, OrderRequest, CancelRequest, OrderData, TradeData
from src.config.constants import Direction, OrderType, Exchange, Offset
from .base_strategy import BaseStrategy

class ExampleStrategy(BaseStrategy):
    """
    一个简单的示例策略，用于演示。
    当价格上涨时买入，当价格下跌时卖出（非常基础的趋势跟踪）。
    """
    strategy_name: str = "策略示例"
    authors: list[str] = ["HomalosAI"]

    def __init__(self, strategy_id: str, event_engine: EventEngine, params: Optional[dict] = None):
        super().__init__(strategy_id, event_engine, params)
        self.subscribed_symbol: str = self.params.get("symbol", "SA509") # 默认订阅SA509
        self.last_tick_price: float = 0.0
        self.order_sent: bool = False # 简单状态，避免重复下单
        self.active_order_id: Optional[str] = None

    async def on_init(self):
        """策略初始化。"""
        self.write_log(f"示例策略 {self.strategy_id} 初始化中...")
        self.write_log(f"参数: {self.params}")
        self.write_log(f"将订阅合约: {self.subscribed_symbol}")
        # 可以在这里加载历史数据或执行其他初始化任务
        await super().on_init() # 调用父类的 on_init

    async def on_start(self):
        """策略启动。"""
        self.write_log(f"示例策略 {self.strategy_id} 启动中...")
        # 实际项目中，订阅行情的动作应该由主引擎或专门的模块根据策略配置来完成
        # 这里只是示意，策略本身不直接调用 gateway.subscribe
        self.write_log(f"策略将关注 {self.subscribed_symbol} 的行情。")
        await super().on_start()

    async def on_stop(self):
        """策略停止。"""
        self.write_log(f"示例策略 {self.strategy_id} 停止中...")
        # 清理资源，例如撤销所有活动订单
        if self.active_order_id:
            self.write_log(f"策略停止，尝试撤销活动订单: {self.active_order_id}")
            # 注意：这里的Exchange需要通过合约信息获取，或者策略参数传入
            # cancel_req = CancelRequest(symbol=self.subscribed_symbol, exchange=Exchange.CFFEX, orderid=self.active_order_id)
            # await self.cancel_order(cancel_req)
        await super().on_stop()

    async def on_tick(self, tick: TickData):
        """处理Tick行情事件。"""
        # self.write_log(f"策略收到TICK事件: 合约={tick.symbol}, 最新价={tick.last_price}")

        if tick.symbol != self.subscribed_symbol or not self.active:
            return

        # self.write_log(f"收到 {tick.symbol} 行情: 最新价={tick.last_price}, 买一价={tick.bid_price_1}, 卖一价={tick.ask_price_1}")

        if self.last_tick_price == 0:
            self.last_tick_price = tick.last_price
            return

        # 简单逻辑：如果当前价格比上一个tick高，并且没有挂单，则买入
        if tick.last_price > self.last_tick_price and not self.order_sent and not self.active_order_id:
            self.write_log(f"价格上涨: {self.last_tick_price} -> {tick.last_price}。准备买入 {self.subscribed_symbol}")
            
            # 假设我们要买入的交易所是CFFEX (中国金融期货交易所)
            # 在实际应用中, exchange应该从合约数据中获取或作为参数传入
            order_req = OrderRequest(
                symbol=self.subscribed_symbol,
                exchange=Exchange.CZCE, # 重要: 这个需要根据合约实际情况来确定
                direction=Direction.LONG,
                type=OrderType.LIMIT, # 限价单
                volume=1,
                price=tick.ask_price_1, # 以卖一价尝试买入
                offset=Offset.OPEN # 开仓
            )
            await self.send_order(order_req)
            self.order_sent = True # 标记已发送订单，等待回报
            self.write_log(f"买入订单已发送 for {self.subscribed_symbol} at {tick.ask_price_1}")

        # 简单逻辑：如果当前价格比上一个tick低，并且有活动订单（假设是之前的买单），则尝试撤销
        # (这是一个非常简化的逻辑，实际中需要管理持仓和更复杂的止损/止盈)
        elif tick.last_price < self.last_tick_price and self.active_order_id:
             self.write_log(f"价格下跌: {self.last_tick_price} -> {tick.last_price}。考虑撤销订单 {self.active_order_id}")
            # cancel_req = CancelRequest(symbol=self.subscribed_symbol, exchange=Exchange.CFFEX, orderid=self.active_order_id)
            # await self.cancel_order(cancel_req)
            # self.order_sent = False # 撤单后允许重新发单（简化）

        self.last_tick_price = tick.last_price

    async def on_order_update(self, order: OrderData):
        """处理订单回报。"""
        await super().on_order_update(order) # 调用父类方法打印日志
        if order.symbol != self.subscribed_symbol:
            return

        if order.is_active():
            self.active_order_id = order.orderid
            self.write_log(f"订单 {order.orderid} 变为活动状态。")
            self.order_sent = True # 确保在订单活动期间不再重复发单
        else:
            # 如果订单不再是活动状态 (e.g. filled, cancelled, rejected)
            if self.active_order_id == order.orderid:
                self.active_order_id = None
            self.order_sent = False # 允许重新发送订单
            self.write_log(f"订单 {order.orderid} 不再活动，状态: {order.status.value}")

    async def on_trade(self, trade: TradeData):
        """处理成交回报。"""
        await super().on_trade(trade)
        if trade.symbol == self.subscribed_symbol:
            self.write_log(f"策略 {self.strategy_id} 记录到成交: {trade.direction} {trade.volume} 手 {trade.symbol} @ {trade.price}")
            # 在这里可以更新策略的内部持仓等状态
            # 如果是买入成交，可能需要设置止损单或进入下一个状态
            if trade.direction == Direction.LONG:
                self.write_log("买入成交，示例策略将不再主动发单，等待手动停止或修改。")
                # self.order_sent = True # 标记，避免立即反向操作或重复操作（根据策略逻辑）
                # self.active_order_id = None # 成交后，原订单不再是活动挂单 