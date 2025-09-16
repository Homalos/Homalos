#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : test_multi_config.py
@Date       : 2025/9/13 22:30
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 测试多配置文件管理
"""
import asyncio
from pathlib import Path

from src.core.event import Event
from src.core.event_bus import EventBus
from src.utils.config_manager import ConfigManager
from src.utils.log import get_logger, logger


def config_update_handler_dev(event: Event):
    log = get_logger("DevHandler")
    log.info(f"开发环境配置更新: {event.payload}")


def config_update_handler_prod(event: Event):
    log = get_logger("ProdHandler")
    log.info(f"生产环境配置更新: {event.payload}")


async def main():
    test_logger = get_logger("TestMultiConfig")
    config_path1 = Path(__file__).resolve().parent.parent / "config" / "extra.dev.yaml"
    config_path2 = Path(__file__).resolve().parent.parent / "config" / "extra.prod.yaml"
    test_logger.info(f"开发配置路径: {config_path1}")
    test_logger.info(f"生产配置路径: {config_path2}")

    # 创建两个独立的事件总线
    bus_dev = EventBus("DevConfigBus")
    bus_prod = EventBus("ProdConfigBus")

    bus_dev.start()
    bus_prod.start()

    # 订阅配置更新事件，使用不同的处理器
    bus_dev.subscribe("CONFIG_UPDATED", config_update_handler_dev)
    bus_prod.subscribe("CONFIG_UPDATED", config_update_handler_prod)

    # 创建两个独立的配置管理器实例
    cfg_dev = ConfigManager(str(config_path1), bus_dev)
    cfg_prod = ConfigManager(str(config_path2), bus_prod)

    # 读取并验证配置
    dev_data_dir = cfg_dev.get("base.data_dir")
    prod_data_dir = cfg_prod.get("base.data_dir")
    
    dev_check = cfg_dev.get("trading_hours.enable_check")
    prod_check = cfg_prod.get("trading_hours.enable_check")
    
    logger.info(f"开发环境数据目录: {dev_data_dir}")
    logger.info(f"生产环境数据目录: {prod_data_dir}")
    logger.info(f"开发环境交易时段检查: {dev_check}")
    logger.info(f"生产环境交易时段检查: {prod_check}")

    # 验证是否正确读取了不同的配置
    if dev_check != prod_check:
        logger.info("✅ 成功读取到不同的配置值，配置管理器工作正常")
    else:
        logger.warning("⚠️ 两个配置文件的值相同，无法验证是否正确分离")

    # 启动文件监听
    cfg_dev.start_watch()
    cfg_prod.start_watch()

    logger.info("系统启动，监控两个配置文件... 按 Ctrl+C 退出")
    logger.info("你可以尝试修改 extra.dev.yaml 或 extra.prod.yaml 来测试")

    try:
        while True:
            await asyncio.sleep(2)
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        cfg_dev.stop_watch()
        cfg_prod.stop_watch()
        bus_dev.stop()
        bus_prod.stop()

    await asyncio.sleep(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("收到 Ctrl+C，程序退出")
