#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos_v2
@FileName   : trade
@Date       : 2025/7/23 00:08
@Author     : Donny
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 交易引擎核心 - 集成策略、风控、订单管理
"""
import asyncio
import time
from typing import Dict, Optional, Any

from src.config.config_manager import ConfigManager
from src.core.event import Event, EventType, create_trading_event
from src.core.event_bus import EventBus
from src.core.logger import get_logger
from src.trade.account_manager import AccountManager
from src.trade.order_manager import OrderManager
from src.trade.performance_metrics import PerformanceMonitor
from src.trade.risk_manager import RiskManager
from src.trade.strategy_manager import StrategyManager

logger = get_logger("TradingEngine")


class TradingEngine:
    """交易引擎核心 - 集成策略、风控、订单管理"""

    def __init__(self, event_bus: EventBus, config: ConfigManager):
        self.event_bus = event_bus
        self.config = config

        # 初始化各管理器
        self.strategy_manager = StrategyManager(event_bus, config)
        self.risk_manager = RiskManager(event_bus, config)
        self.order_manager = OrderManager(event_bus, config)
        self.account_manager = AccountManager(event_bus, config)

        # 引擎状态
        self.is_running = False
        self.start_time: Optional[float] = None

        # 初始化性能监控器
        self.performance_monitor = PerformanceMonitor(event_bus, config)

        # 设置事件处理器
        self._setup_event_handlers()

        logger.info("交易引擎核心初始化完成")

    def _setup_event_handlers(self):
        """设置事件处理器链"""
        # 策略信号 -> 风控检查 -> 订单执行
        self.event_bus.subscribe(EventType.STRATEGY_SIGNAL, self._handle_strategy_signal)

        # 系统控制事件
        self.event_bus.subscribe("engine.start", self._handle_engine_start)
        self.event_bus.subscribe("engine.stop", self._handle_engine_stop)

    @staticmethod
    async def initialize():
        """初始化交易引擎"""
        try:
            logger.info("正在初始化交易引擎...")

            # 可以在这里执行一些初始化任务
            # 例如：加载默认策略、连接数据库等

            logger.info("交易引擎初始化完成")
            return True
        except Exception as e:
            logger.error(f"交易引擎初始化失败: {e}")
            return False

    async def start(self):
        """启动交易引擎"""
        if self.is_running:
            logger.debug("交易引擎已在运行")
            return

        self.is_running = True
        self.start_time = time.time()

        # 启动性能监控
        self.performance_monitor.start_monitoring()

        logger.info("交易引擎已启动")

        # 发布引擎启动事件
        self.event_bus.publish(create_trading_event(
            EventType.ENGINE_STARTED,
            {"start_time": self.start_time},
            "TradingEngine"
        ))

    async def stop(self):
        """停止交易引擎"""
        if not self.is_running:
            logger.warning("交易引擎未在运行")
            return

        # 停止所有策略
        for strategy_uuid in list(self.strategy_manager.strategies.keys()):
            await self.strategy_manager.stop_strategy(strategy_uuid)

        # 停止性能监控
        self.performance_monitor.stop_monitoring()

        self.is_running = False

        logger.info("交易引擎已停止")

        # 发布引擎停止事件
        self.event_bus.publish(create_trading_event(
            EventType.ENGINE_STOPPED,
            {"stop_time": time.time()},
            "TradingEngine"
        ))

    def _handle_strategy_signal(self, event: Event):
        """处理策略信号"""
        data = event.data
        action = data.get("action")
        strategy_id = data.get("strategy_id", "unknown")

        # 记录订单处理开始时间（用于延迟计算）
        process_start_time = time.time()

        if action == "place_order":
            # 策略请求下单 -> 风控检查
            order_request = data["order_request"]

            # 记录订单下达事件
            self.event_bus.publish(Event(EventType.STRATEGY_ORDER_PLACED, {
                "strategy_id": strategy_id,
                "order_request": order_request.__dict__ if hasattr(order_request, '__dict__') else str(order_request),
                "timestamp": process_start_time
            }))

            # 发布风控检查事件
            self.event_bus.publish(create_trading_event(
                EventType.RISK_CHECK,
                {"order_request": order_request, "strategy_id": strategy_id},
                "TradingEngine"
            ))

        elif action == "cancel_order":
            # 策略请求撤单
            order_id = data["order_id"]
            self.event_bus.publish(create_trading_event(
                EventType.ORDER_CANCEL,
                {"order_id": order_id},
                "TradingEngine"
            ))

    def _handle_engine_start(self):
        """处理引擎启动请求"""
        asyncio.create_task(self.start())

    def _handle_engine_stop(self):
        """处理引擎停止请求"""
        asyncio.create_task(self.stop())

    def get_engine_status(self) -> Dict[str, Any]:
        """获取引擎状态"""
        base_status = {
            "is_running": self.is_running,
            "start_time": self.start_time,
            "strategies": self.strategy_manager.get_all_strategies(),
            "account_info": self.account_manager.get_total_account_info()
        }

        # 集成性能监控数据
        if self.performance_monitor:
            base_status["performance"] = {
                "system_metrics": self.performance_monitor.get_system_metrics(),
                "strategy_performance": {
                    strategy_id: self.performance_monitor.get_performance_summary(strategy_id)
                    for strategy_id in self.strategy_manager.strategies.keys()
                }
            }

        return base_status

    def get_performance_metrics(self, strategy_id: str) -> Dict[str, Any]:
        """获取特定策略的性能指标"""
        if self.performance_monitor:
            return self.performance_monitor.get_performance_summary(strategy_id)
        return {}

    def get_system_performance(self) -> Dict[str, Any]:
        """获取系统性能指标"""
        if self.performance_monitor:
            return self.performance_monitor.get_system_metrics()
        return {}
