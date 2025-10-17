#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : system_integration_example.py
@Date       : 2025/10/17 18:00
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 系统集成示例 - 展示完整的数据流程和模块协调
"""
import asyncio
from pathlib import Path

from src.api.bar_generator.bar_generator import BarGenerator
from src.core.alarm_manager import AlarmManager
from src.core.event_bus import EventBus
from src.core.strategy_manager import StrategyManagerIPC
from src.core.subscription_manager import SubscriptionManager
from src.core.system_coordinator import SystemCoordinator
from src.core.trade_signal_handler import TradeSignalHandler
from src.modules.gateway.market_gateway import MarketGateway
from src.modules.gateway.trader_gateway import TraderGateway
from src.modules.risk.risk import RiskManager
from src.utils.log.logger import get_logger


class IntegratedTradingSystem:
    """
    集成交易系统示例
    
    展示完整的数据流程：
    1. 策略加载和订阅管理
    2. 行情数据接收和分发
    3. K线实时合成
    4. 交易信号处理
    5. 风险控制
    6. 订单执行
    7. 告警和监控
    """
    
    def __init__(self, config: dict):
        self.logger = get_logger("IntegratedTradingSystem")
        self.config = config
        
        # 1. 核心事件总线
        self.event_bus = EventBus(
            context="TradingSystem",
            general_max_workers=500,
            market_max_workers=1000,
            auto_start=True
        )
        
        # 2. 告警管理器
        self.alarm_manager = AlarmManager(
            db_path=str(Path("data/alarms.db")),
            loop=asyncio.get_event_loop()
        )
        
        # 3. 订阅管理器
        self.subscription_manager = SubscriptionManager(self.event_bus)
        
        # 4. 策略管理器
        self.strategy_manager = StrategyManagerIPC(
            strategies_pkg="src.strategy",
            registry_path=str(Path("strategy_registry.json"))
        )
        
        # 5. 交易信号处理器
        self.trade_signal_handler = TradeSignalHandler(self.event_bus)
        
        # 6. 风险管理器
        self.risk_manager = RiskManager(self.event_bus)
        
        # 7. 行情网关
        self.market_gateway = MarketGateway(self.event_bus)
        
        # 8. 交易网关
        self.trader_gateway = TraderGateway(self.event_bus)
        
        # 9. K线合成器
        self.bar_generator = BarGenerator()
        
        # 10. 系统协调器
        self.system_coordinator = SystemCoordinator(self.event_bus)
        
        # 设置模块间引用
        self._setup_module_references()
        
        # 注册模块到协调器
        self._register_modules()
        
        # 设置数据流连接
        self._setup_data_flow()
        
        self.logger.info("集成交易系统初始化完成")
    
    def _setup_module_references(self):
        """设置模块间引用关系"""
        # 策略管理器设置引用
        self.strategy_manager.set_event_bus(self.event_bus)
        self.strategy_manager.set_subscription_manager(self.subscription_manager)
        self.strategy_manager.set_trade_signal_handler(self.trade_signal_handler)
        
        # 告警管理器设置事件循环
        self.strategy_manager.alarm_manager = self.alarm_manager
        
        self.logger.info("模块间引用关系已设置")
    
    def _register_modules(self):
        """向系统协调器注册所有模块"""
        # 注册模块（按启动优先级）
        self.system_coordinator.register_module(
            "event_bus", self.event_bus, dependencies=[], startup_order=1
        )
        
        self.system_coordinator.register_module(
            "alarm_manager", self.alarm_manager, 
            dependencies=["event_bus"], startup_order=2
        )
        
        self.system_coordinator.register_module(
            "subscription_manager", self.subscription_manager,
            dependencies=["event_bus"], startup_order=3
        )
        
        self.system_coordinator.register_module(
            "risk_manager", self.risk_manager,
            dependencies=["event_bus"], startup_order=4
        )
        
        self.system_coordinator.register_module(
            "trade_signal_handler", self.trade_signal_handler,
            dependencies=["event_bus", "risk_manager"], startup_order=5
        )
        
        self.system_coordinator.register_module(
            "market_gateway", self.market_gateway,
            dependencies=["event_bus", "subscription_manager"], startup_order=6
        )
        
        self.system_coordinator.register_module(
            "trader_gateway", self.trader_gateway,
            dependencies=["event_bus", "trade_signal_handler"], startup_order=7
        )
        
        self.system_coordinator.register_module(
            "bar_generator", self.bar_generator,
            dependencies=["market_gateway"], startup_order=8
        )
        
        self.system_coordinator.register_module(
            "strategy_manager", self.strategy_manager,
            dependencies=["subscription_manager", "trade_signal_handler"], startup_order=9
        )
        
        self.logger.info("所有模块已注册到系统协调器")
    
    def _setup_data_flow(self):
        """设置数据流连接"""
        # 1. 行情数据流：行情网关 -> K线合成器 -> 策略
        self.event_bus.subscribe("market.tick", self._handle_tick_data)
        self.event_bus.subscribe("market.bar", self._handle_bar_data)
        
        # 2. 订阅管理流：订阅管理器 -> 行情网关 & K线合成器
        self.event_bus.subscribe("market.subscribe.request", self._handle_subscription_request)
        self.event_bus.subscribe("kline.config.update", self._handle_kline_config_update)
        
        # 3. 交易信号流：策略 -> 信号处理器 -> 风控 -> 交易网关
        self.event_bus.subscribe("strategy.trade.signal", self._handle_strategy_signal)
        self.event_bus.subscribe("trade.order.approved", self._handle_order_approved)
        self.event_bus.subscribe("order.submit.request", self._handle_order_submission)
        
        # 4. 订单回报流：交易网关 -> 策略
        self.event_bus.subscribe("order.status.update", self._handle_order_update)
        self.event_bus.subscribe("trade.execution", self._handle_trade_execution)
        
        # 5. 告警流
        self.event_bus.subscribe("risk.alarm", self._handle_risk_alarm)
        self.event_bus.subscribe("system.alarm", self._handle_system_alarm)
        
        self.logger.info("数据流连接已设置")
    
    async def startup(self):
        """启动整个系统"""
        try:
            self.logger.info("=" * 60)
            self.logger.info("开始启动集成交易系统")
            self.logger.info("=" * 60)
            
            # 使用系统协调器启动所有模块
            await self.system_coordinator.startup_system()
            
            # 连接到CTP网关（如果配置可用）
            if self.config.get("ctp_config"):
                await self._connect_ctp_gateways()
            
            # 加载策略（如果配置了策略）
            if self.config.get("auto_load_strategies", True):
                await self._load_strategies()
            
            self.logger.info("=" * 60)
            self.logger.info("集成交易系统启动完成")
            self.logger.info("=" * 60)
            
            # 打印系统状态
            await self._print_system_status()
            
        except Exception as e:
            self.logger.error(f"系统启动失败: {e}", exc_info=True)
            raise
    
    async def _connect_ctp_gateways(self):
        """连接CTP网关"""
        ctp_config = self.config.get("ctp_config", {})
        
        try:
            # 连接行情网关
            self.logger.info("正在连接行情网关...")
            self.market_gateway.connect(ctp_config)
            
            # 连接交易网关
            self.logger.info("正在连接交易网关...")
            self.trader_gateway.connect(ctp_config)
            
            # 等待网关连接成功
            await asyncio.sleep(5)  # 给网关时间建立连接
            
        except Exception as e:
            self.logger.error(f"连接CTP网关失败: {e}", exc_info=True)
    
    async def _load_strategies(self):
        """加载策略"""
        try:
            # 获取已启用的策略
            enabled_strategies = self.strategy_manager.registry.list_enabled()
            
            for strategy_id in enabled_strategies:
                self.logger.info(f"正在加载策略: {strategy_id}")
                self.strategy_manager.load_strategy(strategy_id)
            
            # 等待策略启动
            await asyncio.sleep(2)
            
            self.logger.info(f"已加载 {len(enabled_strategies)} 个策略")
            
        except Exception as e:
            self.logger.error(f"加载策略失败: {e}", exc_info=True)
    
    async def _print_system_status(self):
        """打印系统状态"""
        status = self.system_coordinator.get_system_status()
        
        self.logger.info("系统状态报告:")
        self.logger.info(f"  - 系统状态: {status['system_status']}")
        self.logger.info(f"  - 启动完成: {status['startup_complete']}")
        self.logger.info(f"  - 数据流就绪: {status['data_flow_initialized']}")
        self.logger.info(f"  - 网关状态: {status['gateways_ready']}")
        self.logger.info(f"  - 模块数量: {status['module_count']}")
        
        # 订阅统计
        sub_stats = self.subscription_manager.get_subscription_stats()
        self.logger.info(f"  - 策略数量: {sub_stats['total_strategies']}")
        self.logger.info(f"  - 订阅合约: {sub_stats['total_instruments']}")
        
        # 风控统计
        risk_stats = self.risk_manager.get_risk_statistics()
        self.logger.info(f"  - 风控状态: 正常")
        
        # 信号处理统计
        signal_stats = self.trade_signal_handler.get_signal_statistics()
        self.logger.info(f"  - 活跃信号: {signal_stats['active_signals']}")
    
    async def shutdown(self):
        """关闭系统"""
        try:
            self.logger.info("开始关闭集成交易系统...")
            
            # 使用系统协调器关闭所有模块
            await self.system_coordinator.shutdown_system()
            
            self.logger.info("集成交易系统已关闭")
            
        except Exception as e:
            self.logger.error(f"系统关闭异常: {e}", exc_info=True)
    
    # ===== 事件处理方法 =====
    
    def _handle_tick_data(self, event):
        """处理tick数据"""
        tick_data = event.payload.get("data")
        if tick_data and hasattr(tick_data, 'instrument_id'):
            # 发送给K线合成器
            if self.bar_generator.is_sub_kline(tick_data.instrument_id):
                self.bar_generator.tick_to_kline(tick_data)
            
            # 发送给策略（通过策略管理器）
            self.strategy_manager.broadcast_market_data("tick", tick_data)
    
    def _handle_bar_data(self, event):
        """处理K线数据"""
        bar_data = event.payload.get("data")
        if bar_data:
            # 发送给策略
            self.strategy_manager.broadcast_market_data("bar", bar_data)
    
    def _handle_subscription_request(self, event):
        """处理订阅请求"""
        payload = event.payload
        instrument_id = payload.get("instrument_id")
        action = payload.get("action")
        
        if action == "subscribe":
            # 转发给行情网关
            from src.core.object import SubscribeRequest
            req = SubscribeRequest(instrument_id=instrument_id)
            self.market_gateway.subscribe(req)
    
    def _handle_kline_config_update(self, event):
        """处理K线配置更新"""
        payload = event.payload
        subscription_map = payload.get("subscription_map", {})
        
        # 更新K线合成器配置
        self.bar_generator.set_kline_type(subscription_map)
        self.bar_generator.init_min_kline_map()
    
    def _handle_strategy_signal(self, event):
        """处理策略交易信号"""
        # 信号会自动路由到交易信号处理器
        pass
    
    def _handle_order_approved(self, event):
        """处理风控通过的订单"""
        # 订单会自动路由到交易网关
        pass
    
    def _handle_order_submission(self, event):
        """处理订单提交请求"""
        payload = event.payload
        order_request = payload.get("order_request")
        
        if order_request:
            # 发送给交易网关
            order_id = self.trader_gateway.send_order(order_request)
            if order_id:
                self.logger.info(f"订单已提交: {order_id}")
    
    def _handle_order_update(self, event):
        """处理订单状态更新"""
        # 订单状态会自动路由到策略
        pass
    
    def _handle_trade_execution(self, event):
        """处理成交回报"""
        # 成交回报会自动路由到策略
        pass
    
    def _handle_risk_alarm(self, event):
        """处理风险告警"""
        payload = event.payload
        self.logger.warning(f"风险告警: {payload.get('message')}")
    
    def _handle_system_alarm(self, event):
        """处理系统告警"""
        payload = event.payload
        severity = payload.get("severity", "info")
        message = payload.get("message", "")
        
        if severity in ["error", "critical"]:
            self.logger.error(f"系统告警: {message}")
        elif severity == "warning":
            self.logger.warning(f"系统告警: {message}")
        else:
            self.logger.info(f"系统通知: {message}")


async def main():
    """主函数示例"""
    # 配置示例
    config = {
        "ctp_config": {
            # 如果有CTP配置，在这里填写
            # "md_address": "tcp://...",
            # "td_address": "tcp://...",
            # "broker_id": "...",
            # "user_id": "...",
            # "password": "...",
            # "app_id": "...",
            # "auth_code": "..."
        },
        "auto_load_strategies": False  # 示例中不自动加载策略
    }
    
    # 创建集成系统
    system = IntegratedTradingSystem(config)
    
    try:
        # 启动系统
        await system.startup()
        
        # 运行系统（在实际应用中，这里会是主循环）
        await asyncio.sleep(10)  # 示例运行10秒
        
        # 展示如何手动注册策略订阅
        system.subscription_manager.register_strategy_subscription(
            strategy_id="example_strategy",
            instruments=["cu2501", "au2501"],
            intervals=["MINUTE", "MINUTE5"]
        )
        
        await asyncio.sleep(5)
        
    except KeyboardInterrupt:
        print("收到中断信号")
    finally:
        # 关闭系统
        await system.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
