#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : function.py
@Date       : 2025/9/15 14:05
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 业务工具方法
"""
import copy

from src.constants import strategy_map, thread_pool, tick_to_kline_sys
from src.core.object import TickData


def distribute_tick(tick: TickData):
    """
    判断需要给哪些策略传tick，以及哪些合约需要合成min1 K线
    :param tick:
    :return:
    """
    # 传递tick到策略
    for strategy in strategy_map.values():
        if tick.instrument_id in strategy.sub_ins_id:
            # 直接调用行情事件
            thread_pool.submit(strategy.specific_strategy_map[tick.instrument_id].on_tick,tick)

    # tick合成K线
    if tick.instrument_id in tick_to_kline_sys.sub_kline_id:
        tick_to_kline_sys.tick_to_kline(tick)

# def save_tick(strategy, tick: TickData):
#     # 上锁
#     instrument_id = tick.instrument_id
#     strategy.specific_strategy_map[instrument_id].market_data_lock.acquire()
#     strategy.specific_strategy_map[instrument_id].market_data = copy.copy(tick)
#
#     thread_pool.submit(strategy.specific_strategy_map[instrument_id].on_tick)
