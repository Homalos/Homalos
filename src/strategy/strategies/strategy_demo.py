#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : strategy_demo.py
@Date       : 2025/9/11 17:54
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 策略示例
"""
from src.core.constants import Interval
from src.core.object import OrderData, TradeData, BarData, TickData
from src.strategy.base_strategy import BaseStrategy, SpecificStrategyApi
from src.utils.log.logger import get_logger


class StrategyDemo(BaseStrategy):

    def __init__(self):
        super().__init__()
        self.strategy_id: str = "1001"
        self.strategy_name: str = "策略demo1"
        self.sub_ins_id: list[str] = ["SA601"]
        self.sub_kline_type: list[Interval] = [Interval.MINUTE]
        self.strategy_content: str = "策略示例"


        # 初始化详细策略文件 - 将在外部初始化时填充
        self.specific_strategy_map = {}
        for ins in self.sub_ins_id:
            self.specific_strategy_map[ins] = StrategyDemo.Specific(ins, self.strategy_id, self.sub_kline_type)

    class Specific(SpecificStrategyApi):

        def __init__(self, instrument_id: str, strategy_id: str, sub_kline_type: list):
            super().__init__(instrument_id, strategy_id, sub_kline_type)

            self.logger = get_logger(__class__.__name__)

        def on_before_open(self) -> None:
            self.logger.info("on_before_open")

        def on_after_close(self) -> None:
            self.logger.info("on_after_close")

        def on_alarm(self) -> None:
            self.logger.info("on_alarm")

        def on_tick(self, tick: TickData) -> None:
            self.logger.info("on_tick")

        def on_bar(self, bar: BarData) -> None:
            self.logger.info("on_bar")

        def on_rtn_trade(self, trade: TradeData) -> None:
            self.logger.info("on_rtn_trade")

        def on_rtn_order(self, order: OrderData) -> None:
            self.logger.info("on_rtn_order")

