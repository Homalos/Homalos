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
from src.utils.log import get_logger


class BaseStrategy:
    def __init__(self, name: str, subscribe_symbols: list):
        self.name = name
        self.subscribe_symbols = subscribe_symbols
        self.logger = get_logger(context=f"Strategy-{name}")

    async def on_tick(self, tick: dict):
        raise NotImplementedError
