#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : test_event_bus2.py
@Date       : 2025/9/8 20:26
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: description
"""
import asyncio
import threading
import time
from src.core.event import Event
from src.core.event_bus import EventBus


print_lock = threading.Lock()


def safe_print(*args, **kwargs):
    """线程安全的打印函数，保证一次只允许一个线程打印"""
    with print_lock:
        print(*args, **kwargs)


def market_data_handler(event: Event):
    # 同步订阅者
    safe_print(f"[SYNC] 收到市场数据: {event.payload}")
    time.sleep(0.5)
    safe_print(f"[SYNC] 处理完成: {event.payload}")


async def strategy_handler(event: Event):
    # 异步订阅者
    safe_print(f"[ASYNC] 策略触发: {event.payload}")
    await asyncio.sleep(1)
    safe_print(f"[ASYNC] 策略完成: {event.payload}")


async def main():
    bus = EventBus("FuturesBus")
    safe_print(">>> 启动事件总线")
    bus.start()

    bus.subscribe("tick_data", market_data_handler, async_mode=False)
    bus.subscribe("signal", strategy_handler, async_mode=True)

    # 发布同步事件
    for i in range(3):
        bus.publish(Event("tick_data", payload={"price": 3500 + i, "volume": 100 * i}))

    # 发布异步事件
    bus.publish(Event("signal", payload={"signal": "buy", "strategy": "mean_reversion"}), async_mode=True)
    bus.publish(Event("signal", payload={"signal": "sell", "strategy": "trend_follow"}), async_mode=True)

    # 等待一段时间，模拟运行
    await asyncio.sleep(2)

    safe_print(">>> 停止事件总线")
    # 手动停止（也可以 Ctrl+C）
    bus.stop()


if __name__ == "__main__":
    asyncio.run(main())
