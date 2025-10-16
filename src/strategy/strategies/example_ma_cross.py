#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : example_ma_cross.py
@Date       : 2025/10/16 10:27
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: description
"""
# src/strategy/example_ma_cross.py
from src.strategy.decorators import subscribe
from src.core.event import EventType

def on_init():
    print("策略初始化完成")

def on_stop():
    print("策略停止")

@subscribe(EventType.TICK)
def on_tick(event):
    tick = event.data
    print(f"[MA策略] Tick更新: {tick}")

@subscribe(EventType.BAR)
def on_bar(event):
    bar = event.data
    print(f"[MA策略] Bar更新: {bar}")

@subscribe(EventType.ORDER)
def on_order(event):
    print(f"[MA策略] 订单状态更新: {event.data}")
