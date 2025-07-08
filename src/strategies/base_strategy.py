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

from src.core.engine import EventEngine
from src.core.logger import get_logger
from src.core.object import OrderRequest, CancelRequest, TickData, OrderData, TradeData

logger = get_logger(__name__)


class BaseStrategy(ABC):
    """
    策略基类
    """
    strategy_name: str = "BaseStrategy"
    authors: list[str] = []

    def __init__(self, strategy_id: str, event_engine: EventEngine, params: Optional[dict] = None):
        self.strategy_id: str = strategy_id
        self.event_engine: EventEngine = event_engine
        self.params: dict = params if params else {}
        self.active: bool = False # 策略是否激活运行

    @abstractmethod
    async def on_init(self) -> None:
        """策略初始化时调用。"""
        pass

    @abstractmethod
    async def on_start(self):
        """策略启动时调用。"""
        pass

    @abstractmethod
    async def on_stop(self):
        """策略停止时调用。"""
        pass

    @abstractmethod
    async def on_tick(self, tick: TickData):
        """处理Tick行情事件（如果策略订阅了）。"""
        pass

    @abstractmethod
    async def on_order(self, order: OrderData):
        """处理订单回报事件。"""
        pass

    @abstractmethod
    async def on_trade(self, trade: TradeData):
        """处理成交回报事件。"""
        pass

    @abstractmethod
    async def send_order(self, order_request: OrderRequest):
        """发送订单请求。"""
        pass

    @abstractmethod
    async def cancel_order(self, cancel_request: CancelRequest):
        """取消指定订单。"""
        pass

    @abstractmethod
    def write_log(self, msg: str, level: str = "INFO"):
        pass
