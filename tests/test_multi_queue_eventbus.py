#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : test_multi_queue_eventbus.py
@Date       : 2025/9/16 10:19
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 测试多队列事件总线，高频 Tick + 订单并发
"""
import time
from datetime import datetime

from src.core.event import Event
from src.core.event_bus import EventBus


def on_tick(event):
    # 高频行情处理
    print(f"{datetime.now()}[行情] {event.payload}")

def on_order(event):
    # 低频但关键的订单处理
    print(f"{datetime.now()}[订单] {event.payload}")

if __name__ == "__main__":
    bus = EventBus()

    # 订阅行情/订单事件
    bus.subscribe("market", on_tick)
    bus.subscribe("general", on_order)

    # 高频推送行情
    def push_ticks():
        for i in range(1000):
            bus.publish(Event("market", payload=f"Tick-{i}"))
            time.sleep(0.001)  # 高频

    # 并发推送订单
    def push_orders():
        for i in range(10):
            bus.publish(Event("general", payload=f"Order-{i}"))
            time.sleep(0.05)

    import threading
    threading.Thread(target=push_ticks).start()
    threading.Thread(target=push_orders).start()

    time.sleep(3)
    
    # 优雅关闭
    print(f"{datetime.now()}开始停止事件总线...")
    bus.stop()
    print(f"{datetime.now()}事件总线已停止")
