#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : test_strategy_pool.py
@Date       : 2025/10/8 00:07
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: description
"""
from src.core.constants import Interval
from src.strategy import StrategyPool


if __name__ == '__main__':

    class Strategy:
        def execute(self):
            pass


    class Strategy1(Strategy):
        # 只在启动程序的时候执行一次
        def __init__(self):
            super().__init__()
            # 策略编号
            self.strategy_id = "1"
            # 订阅的合约
            self.sub_ins_id = ["FG209", "SA209", 'au2208', 'sc2207', 'm2209', 'IF2206', 'rb2210', 'fu2209', 'hc2210',
                          'bu2206']
            self.sub_ins_id = ["FG209", "SA209"]
            # 订阅的K线
            self.sub_kline_type = [Interval.MINUTE]

            self.strategy_content = "记录全市场行情"

        def execute(self):
            print("Executing strategy 1")


    class Strategy2(Strategy):
        # 只在启动程序的时候执行一次
        def __init__(self):
            super().__init__()
            # 策略编号
            self.strategy_id = "2"
            # 订阅的合约
            self.sub_ins_id = ["FG209", "SA209", 'au2208', 'sc2207', 'm2209', 'IF2206', 'rb2210', 'fu2209', 'hc2210',
                          'bu2206']
            self.sub_ins_id = ["au2208", "SA209"]
            # 订阅的K线
            self.sub_kline_type = [Interval.MINUTE, Interval.MINUTE5]

            self.strategy_content = ""

        def execute(self):
            print("Executing strategy 2")


    strategyPool = StrategyPool()
    strategyPool.add_strategy("1", Strategy1())
    strategyPool.add_strategy("2", Strategy2())

    strategy_list = strategyPool.get_strategies()
    print(strategyPool.strategy_map)
    print(len(strategy_list))

    strategyPool.init_sub_id()
    print(strategyPool.sub_ins_id)

    strategyPool.init_kline_type()
    print(strategyPool.sub_kline_type)
