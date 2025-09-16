#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
简单的多队列事件总线测试
"""
import time
from datetime import datetime

from src.core.event import Event
from src.core.event_bus import EventBus


def on_test(event):
    print(f"{datetime.now().strftime('%H:%M:%S.%f')[:-3]} - 处理: {event.payload}")


if __name__ == "__main__":
    print("开始测试多队列事件总线...")
    
    bus = EventBus()
    bus.subscribe("test", on_test)
    
    # 发布一些测试事件
    for i in range(10):
        bus.publish(Event("test", payload=f"消息{i}"))
        time.sleep(0.01)
    
    print("等待处理完成...")
    time.sleep(0.5)
    
    print("开始停止事件总线...")
    bus.stop()
    print("事件总线已停止")
