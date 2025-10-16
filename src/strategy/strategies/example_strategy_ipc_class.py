#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : example_strategy_ipc_class.py
@Date       : 2025/10/16 11:12
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 示例策略 - 完整实现所有抽象方法
"""
from src.core.constants import Interval
from src.strategy.base_strategy import SpecificStrategyApi

class Strategy(SpecificStrategyApi):
    def __init__(self):
        super().__init__(instrument_id="RU2601", strategy_id="example_ipc_class", sub_kline_type=[Interval.MINUTE])
        self.counter = 0

    def on_init(self) -> None:
        """开盘前执行"""
        print(f"[{self.strategy_id}] 策略初始化")

    def on_close(self) -> None:
        """收盘后执行"""
        print(f"[{self.strategy_id}] 收盘处理")

    def on_alarm(self) -> None:
        """到达设置闹钟时间时执行"""
        pass

    def on_tick(self, tick) -> None:
        """有新的tick产生时执行"""
        self.counter += 1
        if self.counter % 5 == 0:
            print(f"[{self.strategy_id}] 已处理 {self.counter} 个tick")

    def on_bar(self, bar) -> None:
        """有新的Bar产生时执行"""
        pass

    def on_trade(self, trade) -> None:
        """有订单成交时执行"""
        pass

    def on_order(self, order) -> None:
        """订单状态发生改变时执行"""
        pass

def get_strategy():
    return Strategy()
