#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : start_homalos.py
@Date       : 2025/10/17 18:00
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 系统集成入口 - 完整的数据流程和模块协调
"""
import asyncio
import signal
import sys
import time
from typing import Any

from src.api.bar_generator.bar_generator import BarGenerator
from src.common import load_broker_config
from src.core.alarm_manager import AlarmManager
from src.core.constants import SubscribeAction
from src.core.event import Event, EventType
from src.core.event_bus import EventBus
from src.core.object import SubscribeRequest, TickData
from src.core.strategy_manager import StrategyManager
from src.core.subscription_manager import SubscriptionManager
from src.core.system_coordinator import SystemCoordinator
from src.core.trade_signal_handler import TradeSignalHandler
from src.modules.gateway.market_gateway import MarketGateway
from src.modules.gateway.trader_gateway import TraderGateway
from src.modules.risk.risk import RiskManager
from src.system_config import Config
from src.utils.get_path import get_path_ins
from src.utils.log.logger import get_logger
from src.utils.utility import get_os_info


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
        self.logger = get_logger(self.__class__.__name__)
        self.config = config
        
        # 运行状态管理
        self._running = False
        self._shutdown_initiated = False
        self._monitor_task: asyncio.Task | None = None
        
        # 1. 核心事件总线
        self.event_bus = EventBus(
            context="IntegratedTradingSystem",
            interval=5,  # 定时器间隔5秒
            timer_enabled=True,  # 启用定时器（默认值）
            general_max_workers=500,
            market_max_workers=1000,
            register_signals=False,
            auto_start=True
        )
        self.md_login_status: bool = False  # 行情登录状态
        self.td_login_status: bool = False  # 交易登录状态
        self.is_login_status: bool = False  # 登录状态
        
        # 2. 告警管理器
        self.alarm_manager = AlarmManager(
            db_path=str(get_path_ins.get_data_dir() / Config.database_filename),
            loop=asyncio.get_event_loop()
        )
        
        # 3. 订阅管理器
        self.subscription_manager = SubscriptionManager(self.event_bus)
        
        # 4. 策略管理器
        self.strategy_manager = StrategyManager(
            self.event_bus,
            strategies_pkg="src.strategy.strategies",
            registry_path=str(get_path_ins.get_project_dir() / Config.strategy_registry_path / Config.strategy_registry_file)  # 策略注册文件完整地址
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
        self.bar_generator = BarGenerator(self.event_bus)
        
        # 10. 系统协调器
        self.system_coordinator = SystemCoordinator(self.event_bus)
        
        # 设置模块间引用
        self._setup_module_references()
        
        # 注册模块到协调器
        self._register_modules()

        # 设置网关事件处理器
        self._setup_gateway_event_handlers()
        
        # 设置数据流连接
        self._setup_data_flow()
        
        self.logger.info("集成交易系统初始化完成")
    
    def _setup_module_references(self):
        """设置模块间引用关系"""
        # 策略管理器设置引用
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
    
    def _setup_data_flow(self) -> None:
        """
        设置数据流连接

        Returns:
            None
        """
        # 1. 行情数据流：行情网关 -> K线合成器 -> 策略
        self.event_bus.subscribe(EventType.TICK, self._handle_tick_data)
        self.event_bus.subscribe(EventType.BAR, self._handle_bar_data)
        
        # 2. 订阅管理流：订阅管理器 -> 行情网关 & K线合成器
        self.event_bus.subscribe(EventType.MARKET_SUBSCRIBE_REQUEST, self._handle_subscription_request)
        self.event_bus.subscribe(EventType.KLINE_CONFIG_UPDATE, self._handle_kline_config_update)
        
        # 3. 交易信号流：策略 -> 信号处理器 -> 风控 -> 交易网关
        self.event_bus.subscribe(EventType.STRATEGY_TRADE_SIGNAL, self._handle_strategy_signal)
        self.event_bus.subscribe(EventType.TRADE_ORDER_APPROVED, self._handle_order_approved)
        self.event_bus.subscribe(EventType.ORDER_SUBMIT_REQUEST, self._handle_order_submission)
        
        # 4. 订单回报流：交易网关 -> 策略
        self.event_bus.subscribe(EventType.ORDER_STATUS_UPDATE, self._handle_order_update)
        self.event_bus.subscribe(EventType.TRADE_EXECUTION, self._handle_trade_execution)
        
        # 5. 告警流
        self.event_bus.subscribe(EventType.RISK_ALARM, self._handle_risk_alarm)
        self.event_bus.subscribe(EventType.SYSTEM_ALARM, self._handle_system_alarm)
        
        self.logger.info("数据流连接已设置")
    
    def _setup_gateway_event_handlers(self) -> None:
        """
        设置网关事件处理器，订阅登录相关事件
        
        Returns:
            None
        """
        # 订阅行情网关登录事件
        self.event_bus.subscribe(EventType.MD_GATEWAY_LOGIN, self._handle_md_login)
        # 订阅交易网关登录事件
        self.event_bus.subscribe(EventType.TD_GATEWAY_LOGIN, self._handle_td_login)
        # 订阅确认结算单成功事件
        self.event_bus.subscribe(EventType.TD_CONFIRM_SUCCESS, self._handle_td_confirm)
        # 订阅查询合约完成事件
        self.event_bus.subscribe(EventType.TD_QRY_INS, self._handle_td_qry_ins)
        
        self.logger.info("网关事件处理器已设置")
    
    async def startup(self) -> None:
        """
        启动整个系统

        Returns:
            None
        """
        try:
            self.logger.info("=" * 60)
            self.logger.info("开始启动集成交易系统")
            self.logger.info("=" * 60)
            
            # 使用系统协调器启动所有模块
            await self.system_coordinator.startup_system()
            
            # 连接到行情网关和交易网关
            if self.config.get("broker_name"):
                await self._connect_ctp_gateways()
            
            # 加载策略（如果配置了策略）
            if self.config.get("auto_load_strategies", True) and self.is_login_status:
                await self._load_strategies()
            
            self.logger.info("=" * 60)
            self.logger.info("集成交易系统启动完成")
            self.logger.info("=" * 60)
            
            # 打印系统状态
            await self._print_system_status()
            
        except Exception as e:
            self.logger.error(f"系统启动失败: {e}", exc_info=True)
            raise
    
    async def _connect_ctp_gateways(self) -> None:
        """
        连接CTP网关

        Returns:
            None
        """
        broker_name = self.config.get("broker_name", "")
        broker_config = self.config.get("broker_config", {})

        try:
            # 连接行情网关
            self.logger.info(f"{broker_name}正在连接行情网关...")
            self.market_gateway.connect(broker_config)
            
            # 连接交易网关
            self.logger.info(f"{broker_name}正在连接交易网关...")
            self.trader_gateway.connect(broker_config)
            
            # 等待网关连接成功
            start_time = time.time()    # 开始计时
            timeout = 60.0              # 登录超时时间

            while not (self.md_login_status and self.td_login_status):
                # 检查是否超时
                elapsed_time = time.time() - start_time
                if elapsed_time > timeout:
                    self.logger.warning(
                        f"等待登录超时 ({timeout}秒)，当前状态 - 行情网关: {self.md_login_status}, 交易网关: {self.td_login_status}")
                    break
                await asyncio.sleep(1)

            if not self.md_login_status or not self.td_login_status:
                self.is_login_status = False
                self.logger.error(f"网关登录失败 - 行情网关: {self.md_login_status}, 交易网关: {self.td_login_status}")
            else:
                self.is_login_status = True  # 设置登录状态为True
                self.logger.info(
                    f"所有网关登录成功 - 行情网关: {self.md_login_status}, 交易网关: {self.td_login_status}")

        except Exception as e:
            self.logger.error(f"连接网关失败: {e}", exc_info=True)
    
    async def _load_strategies(self):
        """加载策略"""
        try:
            # 获取已启用的策略
            enabled_strategies = self.strategy_manager.registry.list_enabled()
            
            for strategy_id in enabled_strategies:
                self.logger.info(f"正在加载策略: {strategy_id}")
                self.strategy_manager.load_strategy(strategy_id)
            
            # 等待策略启动和订阅信息注册
            # 策略进程需要时间启动、初始化并发送订阅信息到订阅管理器
            await asyncio.sleep(3)
            
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
        self.logger.info(f"  - 风险统计信息：{risk_stats}")
        self.logger.info("  - 风控状态: 正常")
        
        # 信号处理统计
        signal_stats = self.trade_signal_handler.get_signal_statistics()
        self.logger.info(f"  - 活跃信号: {signal_stats['active_signals']}")
    
    async def shutdown(self):
        """关闭系统"""
        if self._shutdown_initiated:
            self.logger.info("关闭操作正在进行中...")
            return
            
        self._shutdown_initiated = True
        self._running = False
        
        try:
            self.logger.info("开始关闭集成交易系统...")
            
            # 停止监控任务
            if self._monitor_task and not self._monitor_task.done():
                self._monitor_task.cancel()
                try:
                    await self._monitor_task
                except asyncio.CancelledError:
                    pass
            
            # 使用系统协调器关闭所有模块
            await self.system_coordinator.shutdown_system()
            
            self.logger.info("集成交易系统已关闭")
            
        except Exception as e:
            self.logger.error(f"系统关闭异常: {e}", exc_info=True)
    
    async def run(self):
        """
        主循环 - 保持系统运行直到收到停止信号
        
        Returns:
            None
        """
        self.logger.info("进入主循环，系统持续运行中...")
        self._running = True
        
        # 启动监控任务
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        
        try:
            while self._running and not self._shutdown_initiated:
                # 主循环：保持系统运行
                await asyncio.sleep(1)
                
        except asyncio.CancelledError:
            self.logger.info("主循环被取消")
        except Exception as e:
            self.logger.error(f"主循环异常: {e}", exc_info=True)
        finally:
            self.logger.info("退出主循环")
    
    async def _monitor_loop(self):
        """
        监控循环 - 定期输出系统状态
        
        Returns:
            None
        """
        self.logger.info("监控循环已启动")
        last_status_time = time.time()
        status_interval = 60  # 每60秒输出一次状态
        
        try:
            while self._running and not self._shutdown_initiated:
                current_time = time.time()
                
                # 定期输出系统状态
                if current_time - last_status_time >= status_interval:
                    await self._print_runtime_status()
                    last_status_time = current_time
                
                # 短暂休眠避免CPU占用过高
                await asyncio.sleep(5)
                
        except asyncio.CancelledError:
            self.logger.info("监控循环被取消")
        except Exception as e:
            self.logger.error(f"监控循环异常: {e}", exc_info=True)
        finally:
            self.logger.info("监控循环已退出")
    
    async def _print_runtime_status(self):
        """
        打印运行时状态信息
        
        Returns:
            None
        """
        try:
            self.logger.info("=" * 60)
            self.logger.info("系统运行状态报告")
            self.logger.info("=" * 60)
            
            # 系统协调器状态
            status = self.system_coordinator.get_system_status()
            self.logger.info(f"系统状态: {status['system_status']}")
            self.logger.info(f"运行模块: {status['module_count']}")
            
            # 网关状态
            self.logger.info(f"网关状态: 行情={self.md_login_status}, 交易={self.td_login_status}")
            
            # 订阅统计
            sub_stats = self.subscription_manager.get_subscription_stats()
            self.logger.info(f"策略数量: {sub_stats['total_strategies']}")
            self.logger.info(f"订阅合约: {sub_stats['total_instruments']}")
            
            # 风控统计
            risk_stats = self.risk_manager.get_risk_statistics()
            self.logger.info(f"总订单数: {risk_stats['total_orders']}")
            self.logger.info(f"持仓数量: {risk_stats['position_count']}")
            
            # 信号处理统计
            signal_stats = self.trade_signal_handler.get_signal_statistics()
            self.logger.info(f"活跃信号: {signal_stats['active_signals']}")
            
            self.logger.info("=" * 60)
            
        except Exception as e:
            self.logger.error(f"打印运行状态失败: {e}", exc_info=True)
    
    # ===== 事件处理方法 =====
    
    # ----- 网关事件处理 -----
    
    def _handle_md_login(self, event: Event) -> None:
        """
        处理行情网关登录事件
        
        Args:
            event: 行情网关登录事件
            
        Returns:
            None
        """
        data = event.payload
        self.logger.info(f"收到行情网关登录事件: {data}")
        if data and data.get("code") == 0:
            self.md_login_status = True
            self.logger.info("行情网关登录成功")
        else:
            self.md_login_status = False
            self.logger.error(f"行情网关登录失败: {data.get('message') if data else 'Unknown'}")
    
    def _handle_td_login(self, event: Event) -> None:
        """
        处理交易网关登录事件
        
        Args:
            event: 交易网关登录事件
            
        Returns:
            None
        """
        data = event.payload
        self.logger.info(f"收到交易网关登录事件: {data}")
        if data and data.get("code") == 0:
            self.logger.info("交易网关登录成功，等待结算单确认")
            # 获取交易日
            trading_day = data.get("data", {}).get("trading_day")
            if trading_day:
                from src.constants import Const
                Const.trading_day = trading_day
                self.logger.info(f"交易日: {trading_day}")
        else:
            self.logger.error(f"交易网关登录失败: {data.get('message') if data else 'Unknown'}")
    
    def _handle_td_confirm(self, event: Event) -> None:
        """
        处理交易网关确认结算单事件
        
        Args:
            event: 确认结算单事件
            
        Returns:
            None
        """
        data = event.payload
        self.logger.info(f"收到确认结算单事件: {data}")
        if data and data.get("code") == 0:
            self.td_login_status = True
            self.logger.info("结算单确认成功，交易网关完全就绪")
            # 发送查询合约事件
            self._publish_qry_ins()
        else:
            self.td_login_status = False
            self.logger.error(f"结算单确认失败: {data.get('message') if data else 'Unknown'}")
    
    def _publish_qry_ins(self) -> None:
        """
        向交易网关发布查询合约事件
        
        Returns:
            None
        """
        try:
            self.event_bus.publish(Event(EventType.DATA_CENTER_QRY_INS, {}))
            self.logger.info("已发送查询合约事件")
        except Exception as e:
            self.logger.error(f"发送查询合约事件失败: {e}", exc_info=True)
    
    def _handle_td_qry_ins(self, event: Event) -> None:
        """
        处理查询合约完成事件
        
        Args:
            event: 查询合约完成事件
            
        Returns:
            None
        """
        data = event.payload
        self.logger.info(f"收到查询合约完成事件: {data}")
        if data and data.get("code") == 0:
            self.logger.info("合约信息查询完成，系统就绪")
            # 此处可以添加后续的合约初始化逻辑
        else:
            self.logger.error(f"查询合约失败: {data.get('message') if data else 'Unknown'}")
    
    # ----- 行情数据处理 -----
    
    def _handle_tick_data(self, event):
        """
        处理tick数据

        Args:
            event: tick事件

        Returns:
            None
        """
        try:
            # 解析tick数据
            payload = event.payload
            code: int = payload.get("code")
            tick_data: TickData = payload.get("data")

            if code != 0 and not tick_data:
                return

            # 获取合约ID
            instrument_id = tick_data.instrument_id

            if not instrument_id:
                self.logger.warning("tick数据缺少instrument_id")
                return
            
            # 发送给K线合成器
            if self.bar_generator.is_sub_kline(instrument_id):
                self.bar_generator.tick_to_kline(tick_data)
            
            # 发送给策略（通过策略管理器）
            self.strategy_manager.broadcast_market_data("tick", tick_data)
            
        except Exception as e:
            self.logger.error(f"处理tick数据失败: {e}", exc_info=True)
    
    def _handle_bar_data(self, event):
        """
        处理K线数据
        
        Args:
            event: K线事件
            
        Returns:
            None
        """
        try:
            # 解析K线数据
            if isinstance(event.payload, dict):
                bar_data = event.payload.get("data")
            else:
                bar_data = event.payload
            
            if bar_data:
                # 发送给策略
                self.strategy_manager.broadcast_market_data("bar", bar_data)
                
        except Exception as e:
            self.logger.error(f"处理K线数据失败: {e}", exc_info=True)
    
    def _handle_subscription_request(self, event):
        """处理订阅请求"""
        payload: dict = event.payload
        instrument_id: str = payload.get("data", {}).get("instrument_id", "")
        action: SubscribeAction = payload.get("data", {}).get("action", SubscribeAction.SUBSCRIBE)
        
        if action == SubscribeAction.SUBSCRIBE:
            # 转发给行情网关
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

    def get_shutdown_initiated(self) -> bool:
        """获取是否已触发关闭信号"""
        return self._shutdown_initiated


async def main():
    """主函数"""
    logger = get_logger(__name__)
    
    # 配置示例
    broker_config: dict[str, Any] = load_broker_config()
    broker_config["auto_load_strategies"] = True   # 是否自动加载策略

    # 创建集成系统
    system = IntegratedTradingSystem(broker_config)
    
    # 设置信号处理器
    def signal_handler(signum, _frame):
        """信号处理器"""
        logger.info(f"收到信号 {signum}，开始优雅关闭...")
        # 创建关闭任务
        asyncio.create_task(system.shutdown())

    os_info = get_os_info()
    if os_info.get("system") == "Linux" or os_info.get("system") == "Darwin":
        # 注册信号处理器（仅在Unix/Linux系统下可用）
        try:
            loop = asyncio.get_event_loop()
            for sig in (signal.SIGTERM, signal.SIGINT):
                loop.add_signal_handler(sig, lambda s=sig: signal_handler(s, None))  # noqa
            logger.info("信号处理器已注册")
        except NotImplementedError:
            # Windows系统不支持add_signal_handler
            logger.warning("当前系统不支持信号处理器，使用Ctrl+C停止")
    
    try:
        logger.info("=" * 60)
        logger.info("集成交易系统启动中...")
        logger.info("=" * 60)
        
        # 启动系统
        await system.startup()
        
        logger.info("=" * 60)
        logger.info("系统启动完成，进入主循环")
        logger.info("按 Ctrl+C 停止系统")
        logger.info("=" * 60)
        
        # 进入主循环（持续运行）
        await system.run()
        
    except KeyboardInterrupt:
        logger.info("\n收到键盘中断信号 (Ctrl+C)")
    except Exception as e:
        logger.error(f"系统运行异常: {e}", exc_info=True)
    finally:
        logger.info("=" * 60)
        logger.info("开始关闭系统...")
        logger.info("=" * 60)
        
        # 确保系统正确关闭
        if not system.get_shutdown_initiated():
            await system.shutdown()
        
        logger.info("=" * 60)
        logger.info("集成交易系统已完全关闭")
        logger.info("=" * 60)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n程序被用户中断")
        sys.exit(0)
    except Exception as err:
        print(f"\n程序异常退出: {err}")
        sys.exit(1)
