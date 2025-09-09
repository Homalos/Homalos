#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : test_event_bus.py
@Date       : 2025/9/8 09:56
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 事件总线测试用例
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
    """同步处理市场数据"""
    safe_print(f"[SYNC] 收到市场数据: {event.payload}")
    # 模拟计算逻辑
    time.sleep(0.5)
    safe_print(f"[SYNC] 市场数据处理完成: {event.payload}")

async def strategy_signal_handler(event):
    """异步处理策略信号"""
    safe_print(f"[ASYNC] 策略触发: {event.payload}")
    await asyncio.sleep(1)  # 模拟异步风控/下单
    safe_print(f"[ASYNC] 策略执行完成: {event.payload}")


async def main():
    # 创建事件总线
    event_bus = EventBus()

    # 创建事件类型并订阅
    event_bus.subscribe('market_data', market_data_handler, async_mode=False)  # 同步事件
    event_bus.subscribe('strategy_signal', strategy_signal_handler, async_mode=True)  # 异步事件

    event_bus.start()

    # 发布同步事件（市场数据）
    for i in range(3):
        market_data = Event("market_data", payload={"price": 3500 + i, "volume": 100 * i})
        event_bus.publish(market_data)

    strategy_signal1 = Event("strategy_signal", payload={"strategy": "mean_reversion", "signal": "buy"})
    strategy_signal2 = Event("strategy_signal", payload={"strategy": "trend_follow", "signal": "sell"})

    # 发布异步事件（策略信号）
    event_bus.publish(strategy_signal1, async_mode=True)
    event_bus.publish(strategy_signal2, async_mode=True)

    # 运行一段时间观察效果
    await asyncio.sleep(5)
    event_bus.stop()


if __name__ == "__main__":
    asyncio.run(main())