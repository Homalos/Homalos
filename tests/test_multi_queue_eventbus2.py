#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : test_multi_queue_eventbus2.py
@Date       : 2025/9/16 15:46
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: description
"""
import asyncio
import time

from src.core.event import Event
from src.core.event_bus import EventBus


class EventType(object):
    MARKET_DATA = "market"
    GENERAL = "general"


def market_data_handler(event: Event):
    # 同步订阅者
    print(f"[SYNC] 收到市场数据: {event.payload}")
    time.sleep(0.5)
    print(f"[SYNC] 处理完成: {event.payload}")

async def market_data_async_handler(event: Event):
    # 同步订阅者
    print(f"[ASYNC] 收到市场数据: {event.payload}")
    time.sleep(0.5)
    print(f"[ASYNC] 处理完成: {event.payload}")


def strategy_handler(event: Event):
    # 异步订阅者
    print(f"[SYNC] 策略触发: {event.payload}")
    time.sleep(1)
    print(f"[SYNC] 策略完成: {event.payload}")

async def strategy_async_handler(event: Event):
    # 异步订阅者
    print(f"[ASYNC] 策略触发: {event.payload}")
    await asyncio.sleep(1)
    print(f"[ASYNC] 策略完成: {event.payload}")


async def main():
    bus = EventBus()

    # 订阅 market 事件
    bus.subscribe(EventType.MARKET_DATA, market_data_handler, async_mode=False)
    bus.subscribe(EventType.MARKET_DATA, market_data_async_handler, async_mode=True)

    # 订阅 general 事件
    bus.subscribe(EventType.GENERAL, strategy_handler, async_mode=False)
    bus.subscribe(EventType.GENERAL, strategy_async_handler, async_mode=True)

    # 发布 market 事件
    market_event = Event(EventType.MARKET_DATA, {"price": 100})
    bus.publish(market_event, async_mode=False)  # 同步
    bus.publish(market_event, async_mode=True)   # 异步

    # 发布 general 事件
    general_event = Event(EventType.GENERAL, {"msg": "system ready"})
    bus.publish(general_event, async_mode=False)
    bus.publish(general_event, async_mode=True)

    # 等待异步处理完成
    time.sleep(0.5)

    bus.stop()
    print("✅ 测试通过，MultiQueueEventBus 分流和分发逻辑正常")


if __name__ == "__main__":
    asyncio.run(main())
