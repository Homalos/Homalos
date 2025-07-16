#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos_v2
@FileName   : bar_manager
@Date       : 2025/7/16 14:55
@Author     : Donny
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 多symbol多周期K线管理器
"""
from collections import defaultdict
from typing import DefaultDict

from src.core.logger import get_logger
from src.core.object import TickData, BarData
from src.function.bar_generator import BarGenerator


logger = get_logger("BarManager")


class BarManager:
    """多symbol多周期K线管理器"""
    def __init__(self, intervals: list[int]):
        self.intervals = intervals
        self.generators: DefaultDict[str, dict[int, BarGenerator]] = defaultdict(dict)

    def on_tick(self, tick: TickData) -> list[BarData]:
        bars: list[BarData] = []
        symbol = tick.symbol
        exchange = tick.exchange
        logger.debug(f"BarManager收到tick: {symbol} {tick.datetime} {tick.last_price}")
        for interval in self.intervals:
            if interval not in self.generators[symbol]:
                self.generators[symbol][interval] = BarGenerator(symbol, exchange, interval)
            bar = self.generators[symbol][interval].on_tick(tick)
            if bar is not None:
                logger.info(f"BarManager生成K线: {bar.symbol} {bar.datetime} O:{bar.open_price} H:{bar.high_price} L:{bar.low_price} C:{bar.close_price}")
                bars.append(bar)
        return bars