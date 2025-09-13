#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : test_config.py
@Date       : 2025/9/9 14:21
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: config模块测试用例
"""
import asyncio
from pathlib import Path

from src.core.event_bus import EventBus, Event
from src.utils.config import Config
from src.utils.log import get_logger, logger


def config_update_handler(event: Event):
    log = get_logger("config")
    log.info(f"[Handler] 收到配置更新: {event.payload}")


async def main():
    config_path = Path(__file__).resolve().parent.parent / "config"/ "extra.dev.yaml"
    logger.info(f"config_path: {config_path}")

    bus = EventBus("ConfigBus")
    bus.start()

    # 订阅配置更新事件
    bus.subscribe("CONFIG_UPDATED", config_update_handler, async_mode=False)

    # 初始化配置（传入 EventBus）
    cfg = Config(str(config_path), event_bus=bus)

    # 读取配置
    system_name = cfg.get("base.name")
    logger.info(f"初始交易系统名称: {system_name}")

    # 启动文件监听
    cfg.start_watch()

    logger.info("系统启动，等待配置文件变化... 按 Ctrl+C 退出")

    try:
        while True:
            await asyncio.sleep(2)
    except asyncio.CancelledError:
        pass
    finally:
        cfg.stop_watch()
        bus.stop()

    await asyncio.sleep(1)
    bus.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("收到 Ctrl+C，程序退出")
