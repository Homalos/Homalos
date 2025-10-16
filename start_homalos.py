#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : start_homalos.py
@Date       : 2025/10/11 15:34
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 系统入口
"""
import time

from src.core.strategy_manager import StrategyManager

if __name__ == "__main__":
    manager = StrategyManager("strategies", "strategies.json")
    observer = manager.start_watchdog()
    manager.start_all()

    try:
        while True:
            tick_event = {"type": "tick", "data": {"last_price": 1234.5}}
            manager.broadcast_event(tick_event)
            manager.poll_feedback()
            time.sleep(2)
    except KeyboardInterrupt:
        print("退出中...")
    finally:
        observer.stop()
        observer.join()
