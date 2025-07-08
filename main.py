#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos_v2
@FileName   : main
@Date       : 2025/7/5 18:11
@Author     : Donny
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: description
"""
from threading import Thread
from time import sleep

from src.core.event_bus import EventBus, Event
from src.core.logger import get_logger
from src.core.service_registry import ServiceRegistry
from src.services.market_data_service import MarketDataService

logger = get_logger("main")


def setup_trading_system():
    """初始化量化交易系统"""
    # 创建事件总线
    event_bus = EventBus(name="trading_system", max_async_queue_size=20000)

    # 创建服务注册中心
    service_registry = ServiceRegistry(event_bus)
    service_registry.start()

    # 添加控制台监控器
    def console_monitor(event: Event):
        logger.info(f"[Monitor] Event: {event.type} from {event.source}")

    event_bus.add_monitor(console_monitor)

    # 创建核心服务
    market_gateway = MarketDataService(event_bus)
    # trade_gateway = TradeGateway(event_bus)  # 类似MarketGateway的实现
    # strategy_engine = StrategyEngine(event_bus)  # 类似之前实现
    # monitoring_service = MonitoringService(event_bus)  # 类似之前实现

    # 等待服务注册完成
    sleep(1)

    # 服务发现示例
    def discover_and_log_services():
        # 策略引擎发现所有网关服务
        gateways = strategy_engine.discover_services(pattern="gateway")
        logger.info(f"Discovered gateways: {list(gateways.keys())}")

        # 监控服务发现所有服务
        all_services = monitoring_service.discover_services()
        logger.info(f"All registered services: {list(all_services.keys())}")

    # 延迟执行服务发现
    Thread(target=lambda: (sleep(2), discover_and_log_services())).start()

    return {
        "event_bus": event_bus,
        "service_registry": service_registry,
        "services": {
            "market_gateway": market_gateway,
            "trade_gateway": trade_gateway,
            "strategy_engine": strategy_engine,
            "monitoring_service": monitoring_service
        }
    }


# 系统启动
if __name__ == "__main__":
    system = setup_trading_system()

    try:
        # 主线程保持运行
        while True:
            sleep(1)
    except KeyboardInterrupt:
        # 关闭所有服务
        for service in system["services"].values():
            service.shutdown()

        # 停止服务注册中心
        system["service_registry"].stop()

        # 停止事件总线
        system["event_bus"].stop_async_engine()

        logger.info("Trading system shutdown")


def main():
    print("Hello from homalos!")

