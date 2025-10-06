#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : base_strategy.py
@Date       : 2025/9/10 16:44
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 策略基类
"""
from abc import ABC, abstractmethod
from typing import Optional

from src.core.constants import Interval
from src.core.object import TickData, BarData, OrderData, TradeData
from src.strategy.strategy_function import check_on_tick, check_on_bar


class BaseStrategy(object):
    def __init__(self):
        self.strategy_id: str = ""
        self.strategy_name: str = ""  # 策略名称
        self.sub_ins_id: list[str] = []  # 订阅的合约
        self.sub_kline_type: list[Interval] = []  # K线类型
        self.strategy_content: str = ""  # 策略内容介绍

        # 初始化详细策略文件
        self.specific_strategy_map: dict[str, SpecificStrategyApi] = {}

    def one_min(self, now_time):
        pass


class SpecificStrategyApi(ABC):

    def __init__(self, instrument_id: str, strategy_id: str, sub_kline_type: list):

        self.instrument_id = instrument_id
        self.strategy_id = strategy_id
        self.sub_kline_type = sub_kline_type

        self.kline_lock = None
        self.bar_data: Optional[BarData] = None

    @abstractmethod
    def on_before_open(self) -> None:
        """开盘前执行"""
        pass

    @abstractmethod
    def on_after_close(self) -> None:
        """收盘后执行"""
        pass

    @abstractmethod
    def on_alarm(self) -> None:
        """到达设置闹钟时间时执行"""
        pass

    @check_on_tick
    @abstractmethod
    def on_tick(self, tick: TickData) -> None:
        """有新的tick产生时执行"""
        pass

    @check_on_bar
    @abstractmethod
    def on_bar(self, bar: BarData) -> None:
        """有新的Bar产生时执行"""
        pass

    @abstractmethod
    def on_rtn_trade(self, trade: TradeData) -> None:
        """有订单成交时执行"""
        pass

    @abstractmethod
    def on_rtn_order(self, order: OrderData) -> None:
        """订单状态发生改变时执行"""
        pass

