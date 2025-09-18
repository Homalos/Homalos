#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : data_center_strategy.py
@Date       : 2025/9/18 17:58
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 数据中心的策略，只负责数据存储，继承于策略基类
"""
from src.constants import INSTRUMENT_EXCHANGE_FILENAME
from src.core.constants import Interval
from src.core.object import TickData, BarData, TradeData, OrderData
from src.strategy.base_strategy import BaseStrategy, SpecificStrategyApi
from src.utils.get_path import get_path_ins
from src.utils.log import get_logger
from src.utils.utility import load_json


class DataCenterStrategy(BaseStrategy):

    def __init__(self):
        super().__init__()
        self.strategy_id: str = "0001"
        self.strategy_name: str = "数据中心策略"
        self.sub_ins_id: list[str] = self.load_all_instruments()
        self.sub_kline_type: list[Interval] = [
            Interval.MINUTE, Interval.MINUTE3, Interval.MINUTE5,
            Interval.MINUTE15, Interval.MINUTE30, Interval.MINUTE60
        ]
        self.strategy_content: str = "数据中心策略，存储行情使用"

        # 初始化详细策略文件 - 将在外部初始化时填充
        self.specific_strategy_map = {}

    @staticmethod
    def load_all_instruments() -> list[str]:
        """从文件加载所有期货合约"""
        ins_exchange_dict: dict[str, str] = load_json(str(get_path_ins.get_config_dir() / INSTRUMENT_EXCHANGE_FILENAME))
        return [ins for ins in list(ins_exchange_dict.keys())]

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