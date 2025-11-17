#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : trading_core_service.py
@Date       : 2025/10/23
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 交易核心服务 - 封装完整的交易系统核心模块
"""
import asyncio
import time
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Optional, Dict, Any

from src.api.bar_generator.bar_generator import BarGenerator
from src.common import load_broker_config
from src.core.alarm_manager import AlarmManager
from src.core.constants import SubscribeAction
from src.core.event import Event, EventType
from src.core.event_bus import EventBus
from src.core.object import SubscribeRequest, TickData
from src.core.subscription_manager import SubscriptionManager
from src.core.system_coordinator import SystemCoordinator
from src.core.trade_signal_handler import TradeSignalHandler
from src.modules.gateway.market_gateway import MarketGateway
from src.modules.gateway.trader_gateway import TraderGateway
from src.modules.risk.risk import RiskManager
from src.system_config import Config
from src.utils.get_path import get_path_ins
from src.utils.log.logger import get_logger
from src.web.schemas.trading_core import (
    TradingCoreStatus,
    ModuleStatus,
    GatewayStatus,
)


class TradingCoreService:
    """
    交易核心服务
    
    职责：
    1. 管理核心模块生命周期（启动、停止、重启）
    2. 提供模块状态查询接口
    3. 与Web层解耦，可独立测试
    
    注意：
    - 该服务不包含StrategyManager，策略管理由StrategyService负责
    - 使用单例模式，确保全局唯一
    """
    
    _instance: Optional['TradingCoreService'] = None
    _lock = Lock()
    
    def __init__(self):
        """私有构造函数，使用get_instance()获取实例"""
        self.logger = get_logger(self.__class__.__name__)
        
        # 核心状态
        self._status: TradingCoreStatus = TradingCoreStatus.STOPPED
        self._status_lock = asyncio.Lock()
        self._error_message: Optional[str] = None
        
        # 核心模块实例
        self._event_bus: Optional[EventBus] = None
        self._alarm_manager: Optional[AlarmManager] = None
        self._subscription_manager: Optional[SubscriptionManager] = None
        self._trade_signal_handler: Optional[TradeSignalHandler] = None
        self._risk_manager: Optional[RiskManager] = None
        self._market_gateway: Optional[MarketGateway] = None
        self._trader_gateway: Optional[TraderGateway] = None
        self._bar_generator: Optional[BarGenerator] = None
        self._system_coordinator: Optional[SystemCoordinator] = None
        
        # 网关状态
        self._md_login_status: bool = False
        self._td_login_status: bool = False
        self._is_login_status: bool = False
        self._td_confirm_status: bool = False
        self._instruments_loaded: bool = False
        
        # 运行时信息
        self._startup_time: Optional[datetime] = None
        self._running_task: Optional[asyncio.Task] = None
        self._monitor_task: Optional[asyncio.Task] = None
        
        # 策略服务引用（用于停止核心时停止所有策略）
        self._strategy_service = None
        self._config: Optional[Dict[str, Any]] = None
        
        # 账户数据推送
        self._latest_account_data: Optional[dict] = None
        self._latest_positions: dict[str, dict] = {}  # 改为字典，key为"instrument_id_direction"
        self._account_ws_queue: Optional[asyncio.Queue] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None  # 主事件循环引用
        
        self.logger.info("交易核心服务已创建（未启动）")
    
    @classmethod
    def get_instance(cls) -> 'TradingCoreService':
        """获取单例实例"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance
    
    def set_strategy_service(self, strategy_service):
        """
        设置策略服务引用
        
        Args:
            strategy_service: StrategyService实例
        """
        self._strategy_service = strategy_service
        self.logger.info("策略服务已关联到交易核心")
    
    def get_running_strategies_count(self) -> int:
        """
        获取运行中的策略数量
        
        Returns:
            int: 运行中的策略数量
        """
        if not self._strategy_service:
            return 0
        
        try:
            manager = self._strategy_service.get_manager()
            running_strategies = manager.get_running_strategies()
            return len(running_strategies)
        except Exception as e:
            self.logger.error(f"获取运行中策略数量失败: {e}")
            return 0
    
    # ========== 核心控制方法 ==========
    
    async def start_core(self, config: Optional[Dict[str, Any]] = None, auto_connect_gateway: bool = False) -> Dict[str, Any]:
        """
        启动交易核心
        
        Args:
            config: 核心配置（可选，使用默认配置）
            auto_connect_gateway: 是否自动连接网关
        
        Returns:
            dict: 启动结果
        """
        async with self._status_lock:
            # 检查当前状态
            if self._status == TradingCoreStatus.RUNNING:
                return {
                    "success": False,
                    "message": "交易核心已在运行中",
                    "status": self._status
                }
            
            if self._status in [TradingCoreStatus.INITIALIZING, TradingCoreStatus.CONNECTING]:
                return {
                    "success": False,
                    "message": f"交易核心正在{self._status.value}，请稍后",
                    "status": self._status
                }
            
            self._status = TradingCoreStatus.INITIALIZING
            self._error_message = None
        
        start_time = time.time()
        
        try:
            self.logger.info("=" * 60)
            self.logger.info("开始启动交易核心")
            self.logger.info("=" * 60)
            
            # 0. 保存事件循环引用（用于线程安全的协程调度）
            self._loop = asyncio.get_running_loop()
            
            # 1. 准备配置
            # 注意：保留已设置的broker配置，只有在明确传入config时才覆盖
            if config is not None:
                self._config = config
                self.logger.info("使用传入的启动配置")
            elif not self._config:
                self._config = {}
                self.logger.info("使用默认空配置")
            else:
                self.logger.info(f"保留现有broker配置: {self._config.get('broker_name', 'unknown')}")
            
            # 2. 初始化核心模块
            await self._initialize_modules()
            
            # 3. 设置模块间引用
            self._setup_module_references()
            
            # 4. 注册模块到系统协调器
            self._register_modules()
            
            # 5. 设置数据流和事件处理器
            self._setup_data_flow()
            self._setup_gateway_event_handlers()
            
            # 6. 启动系统协调器
            if self._system_coordinator:
                await self._system_coordinator.startup_system()
            
            # 7. 更新状态
            async with self._status_lock:
                self._status = TradingCoreStatus.RUNNING
                self._startup_time = datetime.now()
            
            # 8. 自动连接网关（如果需要）
            gateway_msg = ""
            if auto_connect_gateway:
                self.logger.info("准备自动连接CTP网关...")
                gateway_result = await self.connect_gateway()
                if gateway_result['success']:
                    gateway_msg = "，网关已连接"
                else:
                    gateway_msg = f"，网关连接失败: {gateway_result['message']}"
            
            # 9. 更新策略服务的核心依赖（使策略能够订阅行情和交易）
            if self._strategy_service and hasattr(self._strategy_service, 'update_core_dependencies'):
                self._strategy_service.update_core_dependencies()
            
            # 10. 启动监控任务（在网关连接后，确保状态是RUNNING）
            self._monitor_task = asyncio.create_task(self._monitor_loop())
            
            startup_duration = time.time() - start_time
            
            self.logger.info("=" * 60)
            self.logger.info(f"交易核心启动完成，耗时: {startup_duration:.2f}秒{gateway_msg}")
            self.logger.info("=" * 60)
            
            return {
                "success": True,
                "message": f"交易核心启动成功{gateway_msg}",
                "status": self._status,
                "startup_time": startup_duration
            }
            
        except Exception as e:
            error_msg = f"交易核心启动失败: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            
            async with self._status_lock:
                self._status = TradingCoreStatus.ERROR
                self._error_message = error_msg
            
            # 尝试清理已创建的资源
            await self._cleanup_modules()
            
            return {
                "success": False,
                "message": error_msg,
                "status": self._status,
                "startup_time": time.time() - start_time
            }
    
    async def stop_core(self, force: bool = False, timeout: int = 30) -> Dict[str, Any]:
        """
        停止交易核心
        
        Args:
            force: 是否强制停止
            timeout: 等待超时时间（秒）
        
        Returns:
            dict: 停止结果
        """
        async with self._status_lock:
            if self._status == TradingCoreStatus.STOPPED:
                return {
                    "success": True,
                    "message": "交易核心未运行",
                    "status": self._status
                }
            
            if self._status == TradingCoreStatus.STOPPING:
                return {
                    "success": False,
                    "message": "交易核心正在停止中",
                    "status": self._status
                }
            
            self._status = TradingCoreStatus.STOPPING
        
        start_time = time.time()
        
        try:
            self.logger.info("=" * 60)
            self.logger.info("开始停止交易核心")
            self.logger.info("=" * 60)
            
            # 0. 先停止所有运行中的策略（因为策略依赖交易核心）
            stopped_strategies_count = 0
            if self._strategy_service:
                try:
                    self.logger.info("正在停止所有运行中的策略...")
                    stopped_strategies_count = await self._strategy_service.stop_all_strategies()
                    self.logger.info(f"已停止 {stopped_strategies_count} 个策略")
                except Exception as e:
                    self.logger.error(f"停止策略时出错: {e}", exc_info=True)
            
            # 1. 停止监控任务
            if self._monitor_task and not self._monitor_task.done():
                self._monitor_task.cancel()
                try:
                    await asyncio.wait_for(self._monitor_task, timeout=5)
                except (asyncio.CancelledError, asyncio.TimeoutError):
                    pass
            
            # 2. 使用系统协调器关闭所有模块
            if self._system_coordinator:
                await self._system_coordinator.shutdown_system()
            
            # 3. 清理模块实例
            await self._cleanup_modules()
            
            # 4. 重置网关状态
            self._md_login_status = False
            self._td_login_status = False
            self._is_login_status = False
            self._td_confirm_status = False
            self._instruments_loaded = False
            
            # 5. 删除状态文件
            await self._remove_status_file()
            
            # 6. 更新状态
            async with self._status_lock:
                self._status = TradingCoreStatus.STOPPED
                self._startup_time = None
            
            shutdown_duration = time.time() - start_time
            
            self.logger.info("=" * 60)
            self.logger.info(f"交易核心已停止，耗时: {shutdown_duration:.2f}秒")
            self.logger.info("=" * 60)
            
            return {
                "success": True,
                "message": "交易核心停止成功",
                "status": self._status,
                "shutdown_time": shutdown_duration,
                "stopped_strategies_count": stopped_strategies_count
            }
            
        except Exception as e:
            error_msg = f"交易核心停止失败: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            
            return {
                "success": False,
                "message": error_msg,
                "status": self._status,
                "shutdown_time": time.time() - start_time
            }
    
    async def connect_gateway(self, broker_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        连接CTP网关
        
        Args:
            broker_config: 经纪商配置（可选，优先使用账户设置的配置）
        
        Returns:
            dict: 连接结果
        """
        if self._status != TradingCoreStatus.RUNNING:
            return {
                "success": False,
                "message": "交易核心未运行，无法连接网关"
            }
        
        try:
            async with self._status_lock:
                self._status = TradingCoreStatus.CONNECTING
            
            start_time = time.time()
            
            # 获取经纪商配置
            # 优先级：
            # 1. 参数传入的配置
            # 2. 账户登录时设置的配置（self._config）
            # 3. 从brokers.yaml加载的默认配置（已弃用）
            if broker_config is None:
                if self._config:
                    # 使用账户登录时设置的配置
                    broker_data = self._config
                    broker_name = broker_data.get("broker_name", "")
                    broker_config = broker_data.get("broker_config", {})
                    self.logger.info(f"使用账户broker配置连接网关: {broker_name}")
                else:
                    # 回退到旧的配置加载方式（向后兼容）
                    self.logger.warning("未找到账户broker配置，使用brokers.yaml中的默认配置（不安全）")
                    broker_data = load_broker_config()
                    broker_name = broker_data.get("broker_name", "")
                    broker_config = broker_data.get("broker_config", {})
            else:
                # 如果传入了配置，检查是否是嵌套结构
                if "broker_config" in broker_config:
                    broker_name = broker_config.get("broker_name", "")
                    broker_config = broker_config.get("broker_config", {})
                else:
                    broker_name = broker_config.get("broker_id", "unknown")
            
            # 验证配置完整性
            if not broker_config:
                raise ValueError(
                    "经纪商配置为空。\n"
                    "请先登录资金账户（输入密码），系统将自动构建完整的broker配置。\n"
                    "新的安全架构不再从brokers.yaml读取敏感信息。"
                )
            
            # 验证配置中是否包含必需的敏感信息
            required_fields = ["user_id", "password"]
            missing_fields = [field for field in required_fields if not broker_config.get(field)]
            
            if missing_fields:
                raise ValueError(
                    f"broker配置缺少必需字段: {', '.join(missing_fields)}\n"
                    f"请先登录资金账户（输入密码），系统将从数据库获取这些敏感信息。\n"
                    f"如果您使用了免密登录，请重新输入密码后再启动交易核心。"
                )
            
            # 连接行情网关
            if not self._market_gateway or not self._trader_gateway:
                raise RuntimeError("网关未初始化")
            
            self.logger.info(f"{broker_name}正在连接行情网关...")
            self._market_gateway.connect(broker_config)
            
            # 连接交易网关
            self.logger.info(f"{broker_name}正在连接交易网关...")
            self._trader_gateway.connect(broker_config)
            
            # 等待网关连接成功
            timeout = 60.0
            start_wait = time.time()
            
            while not (self._md_login_status and self._td_login_status):
                if time.time() - start_wait > timeout:
                    raise TimeoutError(f"等待登录超时({timeout}秒)")
                await asyncio.sleep(1)
            
            async with self._status_lock:
                self._status = TradingCoreStatus.RUNNING
                self._is_login_status = True
            
            connection_duration = time.time() - start_time
            
            self.logger.info(f"所有网关登录成功，耗时: {connection_duration:.2f}秒")
            
            return {
                "success": True,
                "message": "网关连接成功",
                "gateway": self._get_gateway_status(),
                "connection_time": connection_duration
            }
            
        except Exception as e:
            error_msg = f"网关连接失败: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            
            async with self._status_lock:
                self._status = TradingCoreStatus.RUNNING  # 恢复运行状态
            
            return {
                "success": False,
                "message": error_msg,
                "gateway": self._get_gateway_status()
            }
    
    async def disconnect_gateway(self) -> Dict[str, Any]:
        """
        断开CTP网关连接
        
        Returns:
            dict: 断开结果
        """
        if self._status != TradingCoreStatus.RUNNING:
            return {
                "success": False,
                "message": "交易核心未运行"
            }
        
        try:
            # TODO: 实现网关断开逻辑
            # 目前CTP网关没有提供disconnect方法，需要后续实现
            
            self._md_login_status = False
            self._td_login_status = False
            self._is_login_status = False
            
            return {
                "success": True,
                "message": "网关已断开"
            }
            
        except Exception as e:
            error_msg = f"网关断开失败: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            
            return {
                "success": False,
                "message": error_msg
            }
    
    def set_account_broker_config(self, broker_config: Dict[str, Any]) -> None:
        """
        设置账户的broker配置（用于连接网关）
        
        Args:
            broker_config: 完整的broker配置（包含敏感信息）
        """
        self._config = broker_config
        self.logger.info(f"已设置账户broker配置: {broker_config.get('broker_name', 'unknown')}")
    
    def has_broker_config(self) -> bool:
        """
        检查是否有完整的broker配置
        
        Returns:
            bool: 是否有完整的broker配置（包含敏感信息）
        """
        return self._config is not None and len(self._config) > 0
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取核心状态
        
        Returns:
            dict: 核心状态信息
        """
        # 获取运行时长
        running_time = None
        if self._startup_time and self._status == TradingCoreStatus.RUNNING:
            delta = datetime.now() - self._startup_time
            hours, remainder = divmod(int(delta.total_seconds()), 3600)
            minutes, seconds = divmod(remainder, 60)
            running_time = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        
        # 获取模块状态
        modules = self._get_modules_status()
        
        # 获取统计信息
        stats = self._get_statistics()
        
        # 读取内部状态文件
        internal_status = self._read_status_file()
        
        return {
            "status": self._status,
            "message": self._error_message,
            "gateway": self._get_gateway_status(),
            "modules": modules,
            "running_time": running_time,
            "startup_time": self._startup_time.isoformat() if self._startup_time else None,
            **stats,
            "internal_status": internal_status
        }
    
    # ========== 依赖获取方法（供StrategyService使用） ==========
    
    def get_event_bus(self) -> Optional[EventBus]:
        """获取事件总线"""
        return self._event_bus
    
    def get_subscription_manager(self) -> Optional[SubscriptionManager]:
        """获取订阅管理器"""
        return self._subscription_manager
    
    def get_trade_signal_handler(self) -> Optional[TradeSignalHandler]:
        """获取交易信号处理器"""
        return self._trade_signal_handler
    
    def get_alarm_manager(self) -> Optional[AlarmManager]:
        """获取告警管理器"""
        return self._alarm_manager
    
    # ========== 内部方法 ==========
    
    async def _initialize_modules(self):
        """初始化所有核心模块"""
        self.logger.info("开始初始化核心模块...")
        
        # 1. 事件总线
        self._event_bus = EventBus(
            context="WebTradingCore",
            interval=5,
            timer_enabled=True,
            general_max_workers=500,
            market_max_workers=1000,
            register_signals=False,  # Web环境不注册信号
            auto_start=True
        )
        self.logger.info("✓ EventBus初始化完成")
        
        # 2. 告警管理器
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.get_event_loop()
        
        db_path = str(get_path_ins.get_data_dir() / Config.database_filename)
        self._alarm_manager = AlarmManager(db_path=db_path, loop=loop)
        await self._alarm_manager.startup()
        self.logger.info("✓ AlarmManager初始化完成")
        
        # 3. 订阅管理器
        self._subscription_manager = SubscriptionManager(self._event_bus)
        self.logger.info("✓ SubscriptionManager初始化完成")
        
        # 4. 交易信号处理器
        self._trade_signal_handler = TradeSignalHandler(self._event_bus)
        self.logger.info("✓ TradeSignalHandler初始化完成")
        
        # 5. 风险管理器
        self._risk_manager = RiskManager(self._event_bus)
        self.logger.info("✓ RiskManager初始化完成")
        
        # 6. 行情网关
        self._market_gateway = MarketGateway(self._event_bus)
        self.logger.info("✓ MarketGateway初始化完成")
        
        # 7. 交易网关
        self._trader_gateway = TraderGateway(self._event_bus)
        self.logger.info("✓ TraderGateway初始化完成")
        
        # 8. K线合成器
        self._bar_generator = BarGenerator(self._event_bus)
        self.logger.info("✓ BarGenerator初始化完成")
        
        # 9. 系统协调器
        self._system_coordinator = SystemCoordinator(self._event_bus)
        self.logger.info("✓ SystemCoordinator初始化完成")
        
        self.logger.info("所有核心模块初始化完成")
    
    def _setup_module_references(self):
        """设置模块间引用关系"""
        # 注意：策略管理器由StrategyService单独管理，这里不设置
        self.logger.info("设置模块间引用关系")
    
    def _register_modules(self):
        """向系统协调器注册所有模块"""
        self.logger.info("开始注册模块到系统协调器...")
        
        # 注册模块（按启动优先级）
        self._system_coordinator.register_module(
            "event_bus", self._event_bus, dependencies=[], startup_order=1
        )
        
        self._system_coordinator.register_module(
            "alarm_manager", self._alarm_manager,
            dependencies=["event_bus"], startup_order=2
        )
        
        self._system_coordinator.register_module(
            "subscription_manager", self._subscription_manager,
            dependencies=["event_bus"], startup_order=3
        )
        
        self._system_coordinator.register_module(
            "risk_manager", self._risk_manager,
            dependencies=["event_bus"], startup_order=4
        )
        
        self._system_coordinator.register_module(
            "trade_signal_handler", self._trade_signal_handler,
            dependencies=["event_bus", "risk_manager"], startup_order=5
        )
        
        self._system_coordinator.register_module(
            "market_gateway", self._market_gateway,
            dependencies=["event_bus", "subscription_manager"], startup_order=6
        )
        
        self._system_coordinator.register_module(
            "trader_gateway", self._trader_gateway,
            dependencies=["event_bus", "trade_signal_handler"], startup_order=7
        )
        
        self._system_coordinator.register_module(
            "bar_generator", self._bar_generator,
            dependencies=["market_gateway"], startup_order=8
        )
        
        self.logger.info("所有模块已注册到系统协调器")
    
    def _setup_data_flow(self):
        """设置数据流连接"""
        # 1. 行情数据流
        self._event_bus.subscribe(EventType.TICK, self._handle_tick_data)
        self._event_bus.subscribe(EventType.BAR, self._handle_bar_data)
        
        # 2. 订阅管理流
        self._event_bus.subscribe(EventType.MARKET_SUBSCRIBE_REQUEST, self._handle_subscription_request)
        self._event_bus.subscribe(EventType.KLINE_CONFIG_UPDATE, self._handle_kline_config_update)
        
        # 3. 交易信号流
        self._event_bus.subscribe(EventType.STRATEGY_TRADE_SIGNAL, self._handle_strategy_signal)
        self._event_bus.subscribe(EventType.TRADE_ORDER_APPROVED, self._handle_order_approved)
        self._event_bus.subscribe(EventType.ORDER_SUBMIT_REQUEST, self._handle_order_submission)
        
        # 4. 订单回报流
        self._event_bus.subscribe(EventType.ORDER_STATUS_UPDATE, self._handle_order_update)
        self._event_bus.subscribe(EventType.TRADE_EXECUTION, self._handle_trade_execution)
        
        # 5. 告警流
        self._event_bus.subscribe(EventType.RISK_ALARM, self._handle_risk_alarm)
        self._event_bus.subscribe(EventType.SYSTEM_ALARM, self._handle_system_alarm)
        
        self.logger.info("数据流连接已设置")
    
    def _setup_gateway_event_handlers(self):
        """设置网关事件处理器"""
        self._event_bus.subscribe(EventType.MD_GATEWAY_LOGIN, self._handle_md_login)
        self._event_bus.subscribe(EventType.TD_GATEWAY_LOGIN, self._handle_td_login)
        self._event_bus.subscribe(EventType.TD_CONFIRM_SUCCESS, self._handle_td_confirm)
        self._event_bus.subscribe(EventType.TD_QRY_INS, self._handle_td_qry_ins)
        self._event_bus.subscribe(EventType.ACCOUNT, self._handle_account_data)
        self._event_bus.subscribe(EventType.POSITION, self._handle_position_data)
        
        self.logger.info("网关事件处理器已设置")
    
    async def _cleanup_modules(self):
        """清理所有模块实例"""
        self.logger.info("开始清理模块实例...")
        
        # 清理顺序与创建顺序相反
        self._system_coordinator = None
        self._bar_generator = None
        self._trader_gateway = None
        self._market_gateway = None
        self._risk_manager = None
        self._trade_signal_handler = None
        self._subscription_manager = None
        
        if self._alarm_manager:
            try:
                await self._alarm_manager.shutdown()
            except Exception as e:
                self.logger.error(f"关闭告警管理器失败: {e}")
        self._alarm_manager = None
        
        self._event_bus = None
        
        self.logger.info("模块实例已清理")
    
    def _get_gateway_status(self) -> GatewayStatus:
        """获取网关状态"""
        return GatewayStatus(
            md_login=self._md_login_status,
            td_login=self._td_login_status,
            td_confirm=self._td_confirm_status,
            instruments_loaded=self._instruments_loaded
        )
    
    def _get_modules_status(self) -> Dict[str, ModuleStatus]:
        """获取所有模块状态"""
        modules = {}
        
        if self._status == TradingCoreStatus.RUNNING:
            modules["event_bus"] = ModuleStatus.RUNNING if self._event_bus else ModuleStatus.STOPPED
            modules["alarm_manager"] = ModuleStatus.RUNNING if self._alarm_manager else ModuleStatus.STOPPED
            modules["subscription_manager"] = ModuleStatus.RUNNING if self._subscription_manager else ModuleStatus.STOPPED
            modules["trade_signal_handler"] = ModuleStatus.RUNNING if self._trade_signal_handler else ModuleStatus.STOPPED
            modules["risk_manager"] = ModuleStatus.RUNNING if self._risk_manager else ModuleStatus.STOPPED
            modules["market_gateway"] = ModuleStatus.RUNNING if self._market_gateway else ModuleStatus.STOPPED
            modules["trader_gateway"] = ModuleStatus.RUNNING if self._trader_gateway else ModuleStatus.STOPPED
            modules["bar_generator"] = ModuleStatus.RUNNING if self._bar_generator else ModuleStatus.STOPPED
        else:
            for module_name in ["event_bus", "alarm_manager", "subscription_manager", "trade_signal_handler",
                               "risk_manager", "market_gateway", "trader_gateway", "bar_generator"]:
                modules[module_name] = ModuleStatus.STOPPED
        
        return modules
    
    def _get_statistics(self) -> Dict[str, int]:
        """获取统计信息"""
        stats = {
            "total_strategies": 0,
            "total_instruments": 0,
            "total_orders": 0,
            "position_count": 0,
            "active_signals": 0
        }
        
        if self._status == TradingCoreStatus.RUNNING:
            try:
                if self._subscription_manager:
                    sub_stats = self._subscription_manager.get_subscription_stats()
                    stats["total_strategies"] = sub_stats.get("total_strategies", 0)
                    stats["total_instruments"] = sub_stats.get("total_instruments", 0)
                
                if self._risk_manager:
                    risk_stats = self._risk_manager.get_risk_statistics()
                    stats["total_orders"] = risk_stats.get("total_orders", 0)
                    stats["position_count"] = risk_stats.get("position_count", 0)
                
                if self._trade_signal_handler:
                    signal_stats = self._trade_signal_handler.get_signal_statistics()
                    stats["active_signals"] = signal_stats.get("active_signals", 0)
            except Exception as e:
                self.logger.error(f"获取统计信息失败: {e}")
        
        return stats
    
    def _read_status_file(self) -> Optional[Dict[str, Any]]:
        """读取内部状态文件"""
        try:
            status_file = Path("runtime/trading_core_status.json")
            if status_file.exists():
                import json
                with open(status_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            self.logger.error(f"读取状态文件失败: {e}")
        return None
    
    async def _remove_status_file(self):
        """删除状态文件"""
        try:
            status_file = Path("runtime/trading_core_status.json")
            if status_file.exists():
                status_file.unlink()
                self.logger.info("状态文件已删除")
        except Exception as e:
            self.logger.error(f"删除状态文件失败: {e}")
    
    async def _monitor_loop(self):
        """监控循环"""
        self.logger.info("监控循环已启动")
        
        while self._status == TradingCoreStatus.RUNNING:
            try:
                # TODO: 添加监控逻辑
                # - 定期输出系统状态
                # - 写入状态文件
                # - 健康检查
                
                await asyncio.sleep(5)
            except asyncio.CancelledError:
                self.logger.info("监控循环被取消")
                break
            except Exception as e:
                self.logger.error(f"监控循环异常: {e}", exc_info=True)
                await asyncio.sleep(5)
        
        self.logger.info("监控循环已退出")
    
    # ========== 事件处理方法（从start_homalos.py提取） ==========
    
    def _handle_md_login(self, event: Event):
        """处理行情网关登录事件"""
        data = event.payload
        if data and data.get("code") == 0:
            self._md_login_status = True
            self.logger.info("行情网关登录成功")
        else:
            self._md_login_status = False
            self.logger.error(f"行情网关登录失败: {data.get('message') if data else 'Unknown'}")
    
    def _handle_td_login(self, event: Event):
        """处理交易网关登录事件"""
        data = event.payload
        if data and data.get("code") == 0:
            self.logger.info("交易网关登录成功，等待结算单确认")
            trading_day = data.get("data", {}).get("trading_day")
            if trading_day:
                from src.constants import Const
                Const.trading_day = trading_day
                self.logger.info(f"交易日: {trading_day}")
        else:
            self.logger.error(f"交易网关登录失败: {data.get('message') if data else 'Unknown'}")
    
    def _handle_td_confirm(self, event: Event):
        """处理结算单确认事件"""
        data = event.payload
        if data and data.get("code") == 0:
            self._td_login_status = True
            self._td_confirm_status = True
            self.logger.info("结算单确认成功，交易网关完全就绪")
            # 发送查询合约事件
            if self._event_bus:
                self._event_bus.publish(Event(EventType.DATA_CENTER_QRY_INS, {}))
        else:
            self._td_login_status = False
            self._td_confirm_status = False
            self.logger.error(f"结算单确认失败: {data.get('message') if data else 'Unknown'}")
    
    def _handle_td_qry_ins(self, event: Event):
        """处理查询合约完成事件"""
        data = event.payload
        if data and data.get("code") == 0:
            self._instruments_loaded = True
            self.logger.info("合约信息查询完成")
        else:
            self._instruments_loaded = False
            self.logger.error(f"查询合约失败: {data.get('message') if data else 'Unknown'}")
    
    def _handle_account_data(self, event: Event):
        """处理账户资金数据事件"""
        try:
            data = event.payload
            if not data:
                return
            
            # 从事件中提取AccountData对象
            account_data = data.get("data")
            if not account_data:
                return
            
            # 转换为字典格式
            if hasattr(account_data, 'to_dict'):
                account_dict = account_data.to_dict()
            else:
                # 兼容旧格式
                account_dict = {
                    "account_id": getattr(account_data, 'account_id', ''),
                    "balance": getattr(account_data, 'balance', 0.0),
                    "frozen": getattr(account_data, 'frozen', 0.0),
                    "available": getattr(account_data, 'available', 0.0)
                }
            
            # 保存最新数据
            self._latest_account_data = account_dict
            
            # 清空持仓字典，准备接收新一轮持仓数据
            # 因为账户查询通常在持仓查询之前执行
            self._latest_positions.clear()
            
            # 推送到WebSocket（线程安全）
            if self._account_ws_queue and self._loop:
                asyncio.run_coroutine_threadsafe(
                    self._push_account_to_ws({
                        "type": "account",
                        "data": account_dict
                    }),
                    self._loop
                )
        
        except Exception as e:
            self.logger.error(f"处理账户数据失败: {e}", exc_info=True)
    
    def _handle_position_data(self, event: Event):
        """处理持仓数据事件"""
        try:
            data = event.payload
            if not data:
                return
            
            # 从事件中提取PositionData对象
            position_data = data.get("data")
            if not position_data:
                return
            
            # 转换为字典格式
            if hasattr(position_data, 'to_dict'):
                position_dict = position_data.to_dict()
            else:
                # 兼容旧格式
                position_dict = {
                    "instrument_id": getattr(position_data, 'instrument_id', ''),
                    "exchange_id": getattr(position_data, 'exchange_id', ''),
                    "direction": getattr(position_data, 'direction', ''),
                    "volume": getattr(position_data, 'volume', 0),
                    "frozen": getattr(position_data, 'frozen', 0.0),
                    "price": getattr(position_data, 'price', 0.0),
                    "pnl": getattr(position_data, 'pnl', 0.0),
                    "yd_volume": getattr(position_data, 'yd_volume', 0)
                }
            
            # 使用字典存储持仓数据，自动去重和更新
            # key格式: "instrument_id_direction"
            position_key = f"{position_dict['instrument_id']}_{position_dict['direction']}"
            self._latest_positions[position_key] = position_dict
            
            # 推送到WebSocket（线程安全）
            if self._account_ws_queue and self._loop:
                # 转换为列表推送
                positions_list = list(self._latest_positions.values())
                asyncio.run_coroutine_threadsafe(
                    self._push_account_to_ws({
                        "type": "positions",
                        "data": positions_list
                    }),
                    self._loop
                )
        
        except Exception as e:
            self.logger.error(f"处理持仓数据失败: {e}", exc_info=True)
    
    def _handle_tick_data(self, event: Event):
        """处理tick数据"""
        try:
            if not self._bar_generator:
                self.logger.warning("BarGenerator 未初始化，跳过 tick 处理")
                return
            
            payload = event.payload
            if not isinstance(payload, dict):
                self.logger.warning(f"Tick payload 不是 dict: {type(payload)}")
                return
            
            code = payload.get("code")
            tick_data = payload.get("data")
            
            if code != 0 or not tick_data:
                self.logger.warning(f"Tick 数据无效: code={code}, tick_data={tick_data}")
                return
            
            if not isinstance(tick_data, TickData):
                self.logger.warning(f"Tick data 不是 TickData: {type(tick_data)}")
                return
            
            instrument_id = tick_data.instrument_id
            if not instrument_id:
                self.logger.warning("Tick data 缺少 instrument_id")
                return
            
            # BarGenerator已通过EventBus订阅TICK事件，无需手动调用
            # 避免重复处理和market线程阻塞
            
            # 通过 ZeroMQ 广播 tick 数据给策略进程
            if self._strategy_service and hasattr(self._strategy_service, '_manager'):
                strategy_manager = self._strategy_service._manager
                if strategy_manager:
                    strategy_manager.broadcast_market_data("tick", tick_data)
            else:
                self.logger.warning("StrategyService 或 StrategyManager 未初始化")
            
        except Exception as e:
            self.logger.error(f"处理tick数据失败: {e}", exc_info=True)
    
    def _handle_bar_data(self, event: Event):
        """处理K线数据"""
        try:
            # 解析K线数据
            if isinstance(event.payload, dict):
                bar_data = event.payload.get("bar")  # ← 修复：使用正确的键名 "bar"
            else:
                bar_data = event.payload
            
            if bar_data:
                # K线数据已生成，策略可以通过EventBus订阅
                
                # 通过 ZeroMQ 广播 bar 数据给策略进程
                if self._strategy_service and hasattr(self._strategy_service, '_manager'):
                    strategy_manager = self._strategy_service._manager
                    if strategy_manager:
                        strategy_manager.broadcast_market_data("bar", bar_data)
        except Exception as e:
            self.logger.error(f"处理K线数据失败: {e}", exc_info=True)
    
    def _handle_subscription_request(self, event: Event):
        """处理订阅请求"""
        if not self._market_gateway:
            return
        
        payload = event.payload
        if not isinstance(payload, dict):
            return
        
        data = payload.get("data", {})
        if not isinstance(data, dict):
            return
        
        instrument_id = data.get("instrument_id", "")
        action = data.get("action", SubscribeAction.SUBSCRIBE)
        
        if action == SubscribeAction.SUBSCRIBE:
            req = SubscribeRequest(instrument_id=instrument_id)
            self._market_gateway.subscribe(req)
    
    def _handle_kline_config_update(self, event: Event):
        """处理K线配置更新"""
        if not self._bar_generator:
            return
        
        payload = event.payload
        if not isinstance(payload, dict):
            return
        
        subscription_map = payload.get("subscription_map", {})
        
        self._bar_generator.set_kline_type(subscription_map)
        self._bar_generator.init_min_kline_map()
    
    def _handle_strategy_signal(self, event: Event):
        """处理策略交易信号"""
        pass
    
    def _handle_order_approved(self, event: Event):
        """处理风控通过的订单"""
        pass
    
    def _handle_order_submission(self, event: Event):
        """处理订单提交请求"""
        if not self._trader_gateway:
            return
        
        payload = event.payload
        if not isinstance(payload, dict):
            return
        
        order_request = payload.get("order_request")
        
        if order_request:
            order_id = self._trader_gateway.send_order(order_request)
            if order_id:
                self.logger.info(f"订单已提交: {order_id}")
    
    def _handle_order_update(self, event: Event):
        """处理订单状态更新"""
        pass
    
    def _handle_trade_execution(self, event: Event):
        """处理成交回报"""
        pass
    
    def _handle_risk_alarm(self, event: Event):
        """处理风险告警"""
        payload = event.payload
        if isinstance(payload, dict):
            self.logger.warning(f"风险告警: {payload.get('message')}")
    
    def _handle_system_alarm(self, event: Event):
        """处理系统告警"""
        payload = event.payload
        if not isinstance(payload, dict):
            return
        
        severity = payload.get("severity", "info")
        message = payload.get("message", "")
        
        if severity in ["error", "critical"]:
            self.logger.error(f"系统告警: {message}")
        elif severity == "warning":
            self.logger.warning(f"系统告警: {message}")
        else:
            self.logger.info(f"系统通知: {message}")
    
    # ========== WebSocket 账户数据推送方法 ==========
    
    async def register_account_ws(self, queue: asyncio.Queue):
        """
        注册账户数据 WebSocket 队列
        
        Args:
            queue: WebSocket消息队列
        """
        self._account_ws_queue = queue
        self.logger.info("账户数据WebSocket已注册")
        
        # 如果有缓存数据，立即推送
        if self._latest_account_data:
            await self._push_account_to_ws({
                "type": "account",
                "data": self._latest_account_data
            })
        if self._latest_positions:
            # 转换字典为列表
            positions_list = list(self._latest_positions.values())
            await self._push_account_to_ws({
                "type": "positions",
                "data": positions_list
            })
    
    def unregister_account_ws(self):
        """注销账户数据 WebSocket 队列"""
        self._account_ws_queue = None
        self.logger.info("账户数据WebSocket已注销")
    
    async def _push_account_to_ws(self, message: dict):
        """
        推送账户数据到 WebSocket
        
        Args:
            message: 消息字典
        """
        if self._account_ws_queue:
            try:
                await self._account_ws_queue.put(message)
            except Exception as e:
                self.logger.error(f"推送账户数据到WebSocket失败: {e}")
    
    def get_latest_account_data(self) -> Optional[dict]:
        """
        获取最新账户数据
        
        Returns:
            dict: 账户数据字典，如果没有则返回None
        """
        return self._latest_account_data
    
    def get_latest_positions(self) -> list[dict]:
        """
        获取最新持仓列表
        
        Returns:
            list[dict]: 持仓数据列表
        """
        return list(self._latest_positions.values())


# 全局单例访问
trading_core_service = TradingCoreService.get_instance()

