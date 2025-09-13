#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : test_traceid2.py
@Date       : 2025/9/10 00:08
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: description
"""
import asyncio

from src.core import trace_context
from src.core.event import Event, EventType
from src.core.event_bus import EventBus
from src.utils.log import get_logger

log = get_logger("market")
bus = EventBus("test")


def on_market_event(event: Event):
    log.info(f"收到行情事件: {event.payload}")

async def main():
    log.info("开始测试")
    bus.subscribe(EventType.TICK, on_market_event)

    # 手动设置 trace_id（比如来自 API 请求入口）
    trace_context.set_trace_id("req-12345")

    bus.start()

    # 发布事件（自动继承 trace_id=req-12345）
    bus.publish(Event(EventType.TICK, {"symbol": "IF2509", "price": 3500}))

    # 等待事件处理
    log.info("停止事件总线...")
    bus.stop()


if __name__ == "__main__":
    asyncio.run(main())
