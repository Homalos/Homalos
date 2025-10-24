#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : strategy3.py
@Date       : 2025/10/24
@Author     : Performance Test
@Email      : test@homalos.com
@Software   : PyCharm
@Description: 性能测试策略3
"""
import datetime

from src.core.constants import Interval
from src.core.object import OrderData, TradeData, BarData, TickData
from src.strategy.base_strategy import BaseStrategy, SpecificStrategy
from src.utils.log import get_logger


class Strategy3(BaseStrategy):

    def __init__(self):
        super().__init__()
        self.logger = get_logger(self.__class__.__name__)
        self.strategy_name: str = "策略3"
        self.strategy_content: str = "性能测试策略3 - 用于多策略并发测试"
        self.author: str = "Performance Test"
        self.instruments: list[str] = ["SA601", "FG601"]
        self.bar_intervals: dict[str, list[Interval]] = {
            "SA601": [Interval.MINUTE],
            "FG601": [Interval.MINUTE]
        }

        # 初始化详细策略文件
        self.specific_strategy_map: dict[str, SpecificStrategy] = {}
        for instrument_id in self.instruments:
            self.specific_strategy_map[instrument_id] = Strategy3.Specific(
                self,
                self.strategy_id,
                instrument_id,
                self.bar_intervals.get(instrument_id, [])
            )

    def one_min(self, now: datetime.datetime) -> None:
        """每分钟调用一次执行"""
        pass

    class Specific(SpecificStrategy):
        """
        策略3的详细策略文件
        """
        def __init__(
                self,
                base_strategy: BaseStrategy,
                strategy_id: str,
                instrument_id: str,
                bar_intervals: list[Interval]
        ) -> None:
            super().__init__(base_strategy, instrument_id, bar_intervals)
            self.logger = get_logger(self.__class__.__name__)
            self.strategy_id: str = strategy_id
            self.instrument_id: str = instrument_id
            self.bar_intervals: list[Interval] = bar_intervals
            self.counter: int = 0

        def on_init(self) -> None:
            self.logger.info(f"{self.strategy_id} 策略开始运行")

        def on_close(self) -> None:
            pass

        def on_alarm(self) -> None:
            pass

        def on_tick(self, tick: TickData) -> None:
            self.counter += 1
            # 降低日志频率，避免I/O阻塞
            if self.counter % 1000 == 0:
                self.logger.info(f"{self.strategy_id} 收到tick: {tick.instrument_id} @ {tick.last_price}, 累计: {self.counter}")

        def on_bar(self, bar: BarData) -> None:
            self.logger.info(f"{self.strategy_id} 收到bar: {bar.instrument_id} close={bar.close_price} vol={bar.volume}")

        def on_trade(self, trade: TradeData) -> None:
            pass

        def on_order(self, order: OrderData) -> None:
            pass


def get_strategy():
    return Strategy3()

