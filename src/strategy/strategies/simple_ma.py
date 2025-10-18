#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : simple_ma.py
@Date       : 2025/10/16 11:32
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: description
"""
from src.strategy.base_strategy import SpecificStrategyApi
from src.core.object import TickData

class Strategy(SpecificStrategyApi):
    def __init__(self, symbol="rb2501", window=5, **_):
        super().__init__(symbol, "simple_ma", [])
        self.prices = []
        self.window = window

    def on_tick(self, tick: TickData):
        self.prices.append(tick["last_price"])
        if len(self.prices) > self.window:
            self.prices.pop(0)
        avg = sum(self.prices) / len(self.prices)
        print(f"[{self.instrument_id}] tick={tick['last_price']} avg={avg}")

    def on_bar(self, bar): pass
    def on_init(self): pass
    def on_close(self): pass
    def on_alarm(self): pass
    def on_trade(self, trade): pass
    def on_order(self, order): pass
