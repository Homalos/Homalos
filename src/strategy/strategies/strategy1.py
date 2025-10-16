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
from src.core.constants import Interval
from src.core.object import OrderData, TradeData, BarData, TickData
from src.strategy.base_strategy import BaseStrategy, SpecificStrategyApi
from src.utils.log import get_logger


class Strategy1(BaseStrategy):

    def __init__(self):
        super().__init__()
        self.logger = get_logger(__class__.__name__)
        self.strategy_id: str = "strategy1"
        self.strategy_name: str = "策略1"
        self.strategy_content: str = "策略1测试，用来测试从行情->交易信号->下单全流程"
        self.sub_ins_id: list[str] = ["SA601"]
        self.sub_kline_type: list[Interval] = [Interval.MINUTE]

        # 初始化详细策略文件
        self.specific_strategy_map: dict[str, SpecificStrategyApi] = {}
        for ins_id in self.sub_ins_id:
            self.specific_strategy_map[ins_id] = self.specific_strategy_map[ins_id] = Strategy1.Specific(
                ins_id,
                self.strategy_id,
                self.sub_kline_type
            )

    class Specific(SpecificStrategyApi):
        """
        策略1的详细策略文件
        """
        def __init__(self, ins_id: str, strategy_id: str, sub_kline_type: list[Interval]) -> None:
            super().__init__(ins_id, strategy_id, sub_kline_type)
            self.logger = get_logger(self.__class__.__name__)
            self.ins_id: str = ins_id
            self.strategy_id: str = strategy_id
            self.sub_kline_type: list[Interval] = sub_kline_type


        def on_init(self) -> None:
            self.logger.info(f"{self.ins_id}策略开始运行")

        def on_close(self) -> None:
            pass

        def on_alarm(self) -> None:
            pass

        def on_tick(self, tick: TickData) -> None:
            pass

        def on_bar(self, bar: BarData) -> None:
            self.logger.info(f"{self.ins_id}策略收到K线数据: {bar}")

        def on_trade(self, trade: TradeData) -> None:
            pass

        def on_order(self, order: OrderData) -> None:
            pass