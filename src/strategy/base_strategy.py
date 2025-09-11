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
from src.core.object import TickData, BarData, OrderData, TradeData
from src.strategy.strategy_function import check_on_tick, check_on_bar


class BaseStrategy(object):
    def __init__(self):
        self.strategy_name = ""  # 策略名称
        self.sub_ins_id = []  # 订阅的合约
        self.sub_kline_type = []  # K线类型
        self.strategy_content = ""  # 策略内容介绍

    def one_min(self, now_time):
        pass



class SpecificStrategyApi(object):

    def __init__(self, instrument_id: str, strategy_id: str, sub_kline_type: list):
        self.instrument_id = instrument_id
        self.strategy_id = strategy_id
        self.sub_kline_type = sub_kline_type

    def on_before_open(self):
        """开盘前执行"""
        pass

    def on_after_close(self):
        """收盘后执行"""
        pass

    def on_alarm(self):
        """到达设置闹钟时间时执行"""
        pass

    @check_on_tick
    def on_tick(self, tick: TickData):
        """有新的tick产生时执行"""
        # raise NotImplementedError
        pass

    @check_on_bar
    def on_bar(self, bar: BarData):
        """有新的Bar产生时执行"""
        pass

    def on_rtn_trade(self, trade: TradeData):
        """有订单成交时执行"""
        pass

    def on_rtn_order(self, order: OrderData):
        """订单状态发生改变时执行"""
        pass

