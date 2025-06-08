#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : base_strategy.py
@Date       : 2025/5/28 15:11
@Author     : Donny
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description:
"""
from abc import ABC, abstractmethod
from typing import Optional
import asyncio # Added for create_task and get_running_loop

from src.core.event import Event, EventType, OrderRequestEvent, CancelOrderRequestEvent, LogEvent # Ensure LogEvent is imported
from src.core.event_engine import EventEngine
from src.core.object import OrderRequest, CancelRequest, TickData, OrderData, TradeData, LogData, SubscribeRequest # Ensure LogData and SubscribeRequest are imported
from src.config.constants import Exchange
from src.util.logger import log


class BaseStrategy(ABC):
    """
    所有策略的基类，定义了策略的生命周期和核心接口。
    """
    def __init__(self, main_engine, strategy_id: str, params: Optional[dict] = None):
        self.main_engine = main_engine
        self.strategy_id: str = strategy_id
        self.params: dict = params if params is not None else {}
        self.event_engine: EventEngine = self.main_engine.event_engine
        self.active: bool = False

    @abstractmethod
    async def on_init(self):
        """策略初始化时调用。"""
        self.write_log("策略初始化完成。")
        pass

    @abstractmethod
    async def on_start(self):
        """策略启动时调用。"""
        self.active = True
        self.write_log("策略已启动。")
        pass

    @abstractmethod
    async def on_stop(self):
        """策略停止时调用。"""
        self.active = False
        self.write_log("策略已停止。")
        pass

    @abstractmethod
    async def on_tick(self, tick):
        """处理行情TICK事件。"""
        pass
    
    @abstractmethod
    async def on_order_update(self, order_update):
        """处理订单更新事件。"""
        pass

    @abstractmethod
    async def on_trade_update(self, trade_update):
        """处理成交更新事件。"""
        pass

    def start(self):
        """启动策略。"""
        self.active = True

    def stop(self):
        """停止策略。"""
        self.active = False

    async def send_order(self, order_request: OrderRequest):
        """发送订单请求。"""
        await self.main_engine.send_order(order_request)

    async def cancel_order(self, cancel_request: CancelRequest):
        """发送撤单请求。"""
        await self.main_engine.cancel_order(cancel_request)

    async def subscribe(self, symbol: str, exchange: Exchange):
        """订阅行情。"""
        req = SubscribeRequest(symbol=symbol, exchange=exchange)
        await self.main_engine.subscribe(req)

    def write_log(self, msg: str, level: str = "INFO"):
        """记录日志。"""
        # 使用主引擎的日志方法，将日志作为事件发送
        self.main_engine.log(f"[{self.strategy_id}] {msg}", level=level)

    # --- 其他辅助方法（可选）---
    def get_parameters(self) -> dict:
        """获取策略参数。"""
        return self.params

    def update_parameters(self, params: dict):
        """（热）更新策略参数。"""
        self.params.update(params)
        self.write_log(f"策略参数已更新: {self.params}") 