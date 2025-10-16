#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : example_strategy_ipc_funcs.py
@Date       : 2025/10/16 11:13
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 示例策略 - 函数式策略（需要包装类）
"""
from src.core.constants import Interval
from src.strategy.base_strategy import SpecificStrategyApi


class StrategyFuncsHolder(SpecificStrategyApi):
    """
    函数式策略的包装类
    将函数式策略包装成符合IPC要求的类
    """
    
    def __init__(self):
        super().__init__(
            instruments="AG2601", 
            strategy_id="example_ipc_funcs", 
            sub_kline_type=[Interval.MINUTE]
        )
        self.tick_count = 0
        self.bar_count = 0

    def on_init(self) -> None:
        """开盘前执行"""
        print(f"[{self.strategy_id}] 函数式策略初始化")

    def on_close(self) -> None:
        """收盘后执行"""
        print(f"[{self.strategy_id}] 收盘 - 处理了 {self.tick_count} 个tick, {self.bar_count} 个bar")

    def on_alarm(self) -> None:
        """到达设置闹钟时间时执行"""
        pass

    def on_tick(self, tick) -> None:
        """有新的tick产生时执行"""
        self.tick_count += 1
        if self.tick_count % 10 == 0:
            print(f"[{self.strategy_id}] [FUNC] 已处理 {self.tick_count} 个tick")

    def on_bar(self, bar) -> None:
        """有新的Bar产生时执行"""
        self.bar_count += 1
        print(f"[{self.strategy_id}] [FUNC] 收到第 {self.bar_count} 个bar")

    def on_trade(self, trade) -> None:
        """有订单成交时执行"""
        pass

    def on_order(self, order) -> None:
        """订单状态发生改变时执行"""
        pass


def get_strategy():
    return StrategyFuncsHolder()
