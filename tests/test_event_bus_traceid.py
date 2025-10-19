#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : test_event_bus_traceid.py
@Date       : 2025/9/9 22:45
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: description
"""
import asyncio
import time

from src.core.constants import RspCode
from src.core.event import Event
from src.core.event_bus import EventBus
from src.core.pack_payload import PackPayload
from src.utils.log import get_logger

_logger = get_logger("strategy")
bus = EventBus("test")


# 订阅策略模块
def handle_market(event: Event):
    # 重新获取logger以确保包含当前的trace_id
    current_logger = get_logger("strategy")
    current_logger.info(f"收到行情: {event.payload}")
    # 下单时返回响应，trace_id 自动继承
    resp = PackPayload.fail(RspCode.TRADE_NO_FUNDS, "资金不足")
    current_logger.info(f"API响应: {resp}")

async def main():
    _logger.info("=== 开始测试 EventBus trace_id 功能 ===")
    
    # 订阅事件
    bus.subscribe("TICK", handle_market)
    
    # 启动事件总线
    bus.start()
    
    # 发布行情事件（自动生成 trace_id）
    _logger.info("发布行情事件...")
    bus.publish(Event("TICK", {"symbol": "rb2501", "price": 3580}))
    
    # 等待事件处理
    time.sleep(1)
    
    # 停止事件总线
    _logger.info("停止事件总线...")
    bus.stop()
    
    _logger.info("=== 测试完成 ===")


if __name__ == "__main__":
    asyncio.run(main())
