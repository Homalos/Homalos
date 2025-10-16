#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : decorators.py
@Date       : 2025/10/16 10:24
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: subscribe 装饰器

src/strategy/decorators.py
"""
import time
from typing import Callable
from src.utils.log import get_logger

_logger = get_logger(__name__)


def subscribe(event_type: str, async_mode: bool = False):
    """
    装饰器：标记策略函数订阅的事件类型

    策略函数打上此装饰器后，系统会自动识别并注册到 EventBus。

    使用示例：
        @subscribe(EventType.TICK)
        def on_tick(event): ...
    """
    def decorator(func: Callable):
        if not hasattr(func, "_subscribe_to"):
            func._subscribe_to = []
        func._subscribe_to.append((event_type, async_mode))
        return func
    return decorator

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
