#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : decorators.py
@Date       : 2025/10/16 10:24
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 策略性能监控装饰器

用于监控策略方法执行时间，防止策略逻辑过慢阻塞数据流。
"""
import time
from src.utils.log import get_logger

_logger = get_logger(__name__)


def check_on_tick(func):
    def checkfunc(self, *args, **kwargs):
        start = time.time()
        func(self, *args, **kwargs)
        end = time.time()
        spend_time = end - start
        if spend_time > 0.5:
            _logger.warning('策略{}中的{}合约的{}函数花费{}s，超出规定时间，请注意！'.format(self.strategy_id, self.instrument_id, func.__name__, spend_time))
    return checkfunc

def check_on_bar(func):
    def checkfunc(self, *args, **kwargs):

        start = time.time()
        func(self, *args, **kwargs)
        end = time.time()
        spend_time = end - start
        if spend_time > 1:
            _logger.warning('策略{}中的{}合约的{}函数花费{}s，超出规定时间，请注意！'.format(self.strategy_id, self.instrument_id, func.__name__, spend_time))
        self.kline_lock.release()
    return checkfunc
