#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : strategy1.py
@Date       : 2025/10/11 15:42
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 策略1demo
"""
import datetime

from src.core.constants import Interval
from src.core.object import OrderData, TradeData, BarData, TickData
from src.strategy.base_strategy import BaseStrategy, SpecificStrategy
from src.utils.strategy_logger import get_strategy_logger as get_logger
from src.utils.utility import write_csv


class Strategy1(BaseStrategy):

    def __init__(self):
        super().__init__()
        self.logger = get_logger(self.__class__.__name__)
        self.strategy_name: str = "策略1"
        self.strategy_content: str = "用来测试从行情->交易信号->下单全流程"
        self.author: str = "Lumosylva"
        self.instruments: list[str] = ["SA601", "FG601"]
        self.bar_intervals: dict[str, list[Interval]] = {
            "SA601": [Interval.MINUTE, Interval.MINUTE5],
            "FG601": [Interval.MINUTE]
        }

        # 初始化详细策略文件
        self.specific_strategy_map: dict[str, SpecificStrategy] = {}
        for instrument_id in self.instruments:
            self.specific_strategy_map[instrument_id] = Strategy1.Specific(
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
        策略的详细策略文件
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
            self.base_strategy: BaseStrategy = base_strategy
            self.strategy_id: str = strategy_id
            self.instrument_id: str = instrument_id
            self.bar_intervals: list[Interval] = bar_intervals
            self.counter: int = 0
            # 创建csv文件
            for bar_interval in bar_intervals:
                write_csv(
                    f"{self.instrument_id}_{bar_interval.value}.csv",
                    "w",
                    [
                        "bar_type",
                        "update_time",
                        "instrument_id",
                        "exchange_id",
                        "volume",
                        "open_interest",
                        "open_price",
                        "high_price",
                        "low_price",
                        "close_price",
                        "last_volume"
                    ]
                )

        def on_init(self) -> None:
            self.logger.info(f"{self.strategy_id} 策略开始运行")

        def on_close(self) -> None:
            pass

        def on_alarm(self) -> None:
            pass

        def on_tick(self, tick: TickData) -> None:
            self.counter += 1
            # 降低日志频率，避免I/O阻塞FastAPI事件循环
            if self.counter % 80 == 0:
                self.logger.info(f"{self.strategy_id} 收到tick: {tick.instrument_id} @ {tick.last_price}, 累计: {self.counter}")

        def on_bar(self, bar: BarData) -> None:
            self.logger.info(f"{self.base_strategy.strategy_name} 收到bar: "
                             f"{bar.instrument_id} "
                             f"open={bar.open_price} "
                             f"high={bar.high_price} "
                             f"low={bar.low_price} "
                             f"close={bar.close_price} "
                             f"vol={bar.volume}")

            write_csv(f"{self.instrument_id}_{bar.bar_type.value}.csv",
                      "a+",
                      [
                          bar.bar_type.value,
                          bar.update_time,
                          bar.instrument_id,
                          bar.exchange_id.value,
                          bar.volume,
                          bar.open_interest,
                          bar.open_price,
                          bar.high_price,
                          bar.low_price,
                          bar.close_price,
                          bar.last_volume
                        ]
                      )


        def on_trade(self, trade: TradeData) -> None:
            pass

        def on_order(self, order: OrderData) -> None:
            pass


def get_strategy():
    return Strategy1()
