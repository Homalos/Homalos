#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : strategy1.py
@Date       : 2025/10/11 15:42
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 策略demo
"""
import datetime

from src.core.constants import Interval
from src.core.object import OrderData, TradeData, BarData, TickData
from src.strategy.base_strategy import BaseStrategy, SpecificStrategy
from src.utils.log import get_logger


class Strategy1(BaseStrategy):

    def __init__(self):
        super().__init__()
        self.strategy_name: str = "策略1"
        self.strategy_content: str = "策略1测试，用来测试从行情->交易信号->下单全流程"
        self.author: str = "Donny"
        self.instruments: list[str] = ["SA601", "FG601"]
        self.bar_intervals: list[Interval] = [Interval.MINUTE]
        self.logger = get_logger(__class__.__name__)

        # 初始化详细策略文件
        self.specific_strategy_map: dict[str, SpecificStrategy] = {}
        for instrument_id in self.instruments:
            self.specific_strategy_map[instrument_id] = Strategy1.Specific(
                self.strategy_id,
                instrument_id,
                self.bar_intervals
            )

    def one_min(self, now: datetime) -> None:
        """每分钟调用一次执行"""
        pass

    class Specific(SpecificStrategy):
        """
        策略1的详细策略文件
        """
        def __init__(self, strategy_id: str, instrument_id: str, bar_intervals: list[Interval]) -> None:
            super().__init__(instrument_id, bar_intervals)
            self.strategy_id: str = strategy_id
            self.instrument_id: str = instrument_id
            self.bar_intervals: list[Interval] = bar_intervals
            self.logger = get_logger(self.__class__.__name__)

        def on_init(self) -> None:
            self.logger.info(f"{self.strategy_id} 策略开始运行")

        def on_close(self) -> None:
            pass

        def on_alarm(self) -> None:
            pass

        def on_tick(self, tick: TickData) -> None:
            self.logger.info(f"{self.strategy_id} 策略收到行情数据: {tick}")
            pass

        def on_bar(self, bar: BarData) -> None:
            self.logger.info(f"{self.strategy_id} 策略收到K线数据: {bar}")

        def on_trade(self, trade: TradeData) -> None:
            pass

        def on_order(self, order: OrderData) -> None:
            pass


def get_strategy():
    return Strategy1()
