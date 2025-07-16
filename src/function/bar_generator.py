#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos_v2
@FileName   : bar_generator
@Date       : 2025/7/16 14:49
@Author     : Donny
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: K线合成器
"""
from datetime import datetime

from src.config.constant import Interval
from src.core.object import BarData, TickData


class BarGenerator:
    """单symbol单周期K线合成器"""
    def __init__(self, symbol: str, exchange, interval_minutes: int):
        self.symbol = symbol
        self.exchange = exchange
        self.interval_minutes = interval_minutes
        self.current_bar: BarData | None = None
        self.last_bar_end: datetime | None = None

    def on_tick(self, tick: TickData) -> BarData | None:
        dt = tick.datetime.replace(second=0, microsecond=0)
        # 计算当前tick属于哪个bar周期
        minute = (dt.minute // self.interval_minutes) * self.interval_minutes
        bar_start = dt.replace(minute=minute)
        if self.last_bar_end is None or bar_start > self.last_bar_end:
            # 新K线周期，输出上一根K线
            finished_bar = self.current_bar
            interval_type = Interval.MINUTE if self.interval_minutes == 1 else Interval.MINUTE  # 先全部用MINUTE
            self.current_bar = BarData(
                symbol=self.symbol,
                exchange=self.exchange,
                datetime=bar_start,
                gateway_name=tick.gateway_name,
                interval=interval_type,
                open_price=tick.last_price,
                high_price=tick.last_price,
                low_price=tick.last_price,
                close_price=tick.last_price,
                volume=tick.volume,
                turnover=tick.turnover,
                open_interest=tick.open_interest
            )
            self.last_bar_end = bar_start
            return finished_bar
        else:
            # 更新当前K线
            bar = self.current_bar
            if bar:
                bar.close_price = tick.last_price
                bar.high_price = max(bar.high_price, tick.last_price)
                bar.low_price = min(bar.low_price, tick.last_price)
                bar.volume = tick.volume
                bar.turnover = tick.turnover
                bar.open_interest = tick.open_interest
        return None