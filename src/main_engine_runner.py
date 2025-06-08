#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : main_engine_runner.py
@Date       : 2025/6/06 18:00
@Author     : Donny
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 提供了启动、协调和停止整个系统的框架。
"""
import asyncio
import logging
import os
import signal
import sys
from typing import Dict, Type, Optional

from src.config import global_var
from src.config.setting import get_broker_setting
from src.core.base_gateway import BaseGateway
from src.core.event import (
    EventType, LogEvent, GatewayStatusEvent, SubscribeRequestEvent,
    TickEvent, OrderUpdateEvent, TradeUpdateEvent, OrderRequestEvent, CancelOrderRequestEvent,
    PositionUpdateEvent, AccountUpdateEvent, ContractInfoEvent
)
from src.core.object import (
    OrderRequest, CancelRequest, LogData, GatewayStatusData,
    GatewayConnectionStatus, SubscribeRequest, PositionData, AccountData, ContractData
)
from src.ctp.gateway.ctp_gateway import CtpGateway
from src.messaging.zmq_event_engine import ZmqEventEngine
from src.strategies.base_strategy import BaseStrategy
from src.strategies.example_strategy import ExampleStrategy
from src.util.logger import log, setup_logging
from src.util.runner_common import runner_args

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


class MainEngine:
    """
    主引擎，负责协调各个组件。
    - 初始化并管理事件引擎和网关
    - 加载并管理策略
    - 处理核心事件
    """

    def __init__(self, event_engine: ZmqEventEngine, environment_name: Optional[str] = None):
        env_for_logging = environment_name or 'default'
        setup_logging(service_name=f"{self.__class__.__name__}[{env_for_logging}]")

        self.event_engine: ZmqEventEngine = event_engine
        self.gateways: Dict[str, BaseGateway] = {}
        self.strategies: Dict[str, BaseStrategy] = {}
        self._running = True
        self.environment_name: Optional[str] = environment_name
        self.current_broker_setting: Optional[dict] = None

        # 事件注册
        self.event_engine.register(EventType.GATEWAY_STATUS, self.process_gateway_status_event)
        self.event_engine.register(EventType.TICK, self.process_tick_event)
        self.event_engine.register(EventType.ORDER_UPDATE, self.process_order_update)
        self.event_engine.register(EventType.TRADE_UPDATE, self.process_trade_update)
        self.event_engine.register(EventType.POSITION_UPDATE, self.process_position_update)
        self.event_engine.register(EventType.ACCOUNT_UPDATE, self.process_account_update)
        self.event_engine.register(EventType.LOG, self.process_log_event)
        self.event_engine.register(EventType.CONTRACT_INFO, self.process_contract_event)

        self._load_broker_config()

    async def process_gateway_status_event(self, event: GatewayStatusEvent):
        """处理网关状态事件。"""
        status_data: GatewayStatusData = event.data
        log_msg = f"网关状态更新 [{status_data.gateway_name}]: {status_data.status.value}"
        if status_data.message:
            log_msg += f" - {status_data.message}"

        log_level = "INFO"
        if status_data.status == GatewayConnectionStatus.ERROR:
            log_level = "ERROR"
        elif status_data.status == GatewayConnectionStatus.DISCONNECTED:
            log_level = "WARNING"

        self.log(log_msg, level=log_level)

    async def process_tick_event(self, event: TickEvent):
        """处理行情事件，并分发给所有策略"""
        for strategy in self.strategies.values():
            if strategy.active:
                await strategy.on_tick(event.data)

    async def process_order_update(self, event: OrderUpdateEvent):
        """处理订单更新"""
        for strategy in self.strategies.values():
            if strategy.active:
                await strategy.on_order_update(event.data)

    async def process_trade_update(self, event: TradeUpdateEvent):
        """处理成交更新"""
        for strategy in self.strategies.values():
            if strategy.active:
                await strategy.on_trade_update(event.data)

    async def process_position_update(self, event: PositionUpdateEvent):
        """处理持仓更新"""
        position: PositionData = event.data
        self.log(f"账户持仓更新: {position.symbol}, 方向: {position.direction.value}, "
                 f"数量: {position.volume}, 昨仓: {position.yd_volume}, "
                 f"均价: {position.price:.2f}, 盈亏: {position.pnl:.2f}",
                 "INFO")
        for strategy in self.strategies.values():
            if strategy.active:
                await strategy.on_position_update(position)

    async def process_account_update(self, event: AccountUpdateEvent):
        """处理账户资金更新"""
        account: AccountData = event.data
        self.log(f"账户资金更新: {account.account_id}, "
                 f"余额: {account.balance:.2f}, "
                 f"可用: {account.available:.2f}, "
                 f"冻结: {account.frozen:.2f}",
                 "INFO")

    async def process_log_event(self, event: LogEvent):
        """处理日志事件。"""
        log_data: LogData = event.data
        # 只处理来自交易网关的日志，以避免信息泛滥
        if log_data.gateway_name and ("TD" in log_data.gateway_name or "CTP_TD" in log_data.gateway_name):
            level_str = log_data.level if isinstance(log_data.level, str) else logging.getLevelName(log_data.level)
            self.log(f"[{log_data.gateway_name}] {log_data.msg}", level=level_str)

    async def process_contract_event(self, event: ContractInfoEvent):
        """处理合约信息事件。"""
        contract: ContractData = event.data
        self.log(f"接收到合约信息: {contract.symbol} - {contract.name} @ {contract.exchange.value}", "DEBUG")

    def log(self, msg: str, level: str = "INFO"):
        """
        使用全局记录器记录消息。
        """
        log(msg, level)

    def add_gateway(self, gateway_class: Type[BaseGateway], gateway_name_prefix: str = "CTP_TD"):
        """添加并初始化一个网关"""
        if not self.current_broker_setting or not self.environment_name:
            self.log(f"无法添加 {gateway_name_prefix} 网关，因为未加载有效的CTP配置。", "ERROR")
            return None

        actual_gateway_name = f"{gateway_name_prefix}_{self.environment_name}"
        if actual_gateway_name in self.gateways:
            self.log(f"网关 {actual_gateway_name} 已存在。", "WARNING")
            return self.gateways[actual_gateway_name]

        gateway = gateway_class(actual_gateway_name, self.event_engine)
        self.gateways[actual_gateway_name] = gateway
        self.log(f"网关 {actual_gateway_name} ({gateway_class.__name__}) 已添加。")
        return gateway

    def add_strategy(self, strategy_class: Type[BaseStrategy], strategy_id: str, params: dict):
        """添加并初始化一个策略"""
        if strategy_id in self.strategies:
            self.log(f"策略 {strategy_id} 已存在。", "WARNING")
            return

        strategy = strategy_class(self, strategy_id, params)
        self.strategies[strategy_id] = strategy
        self.log(f"策略 {strategy_id} 已添加。")

    async def send_order(self, req: OrderRequest):
        """将策略的订单请求发送到事件总线。"""
        if self.gateways:
            await self.event_engine.put(OrderRequestEvent(data=req))
            self.log(f"订单请求已发送至事件总线: {req.symbol}")
        else:
            self.log("无可用网关，无法发送订单。", "ERROR")

    async def cancel_order(self, req: CancelRequest):
        """将策略的撤单请求发送到事件总线。"""
        if self.gateways:
            await self.event_engine.put(CancelOrderRequestEvent(data=req))
            self.log(f"撤单请求已发送至事件总线: {req.orderid}")
        else:
            self.log("无可用网关，无法撤销订单。", "ERROR")

    async def subscribe(self, req: SubscribeRequest):
        """将策略的订阅请求发送到事件总线。"""
        self.log(f"订阅请求已发送至事件总线: {req.symbol}")
        await self.event_engine.put(SubscribeRequestEvent(data=req))

    def get_default_gateway_name(self) -> str:
        if not self.gateways:
            return ""

    def _load_broker_config(self):
        """加载券商配置"""
        try:
            all_brokers_config = get_broker_setting()
            brokers = all_brokers_config.get("brokers", {})
            default_broker_name = all_brokers_config.get("default_broker")

            env_to_load = self.environment_name or default_broker_name
            if env_to_load and env_to_load in brokers:
                self.environment_name = env_to_load
                self.current_broker_setting = brokers[env_to_load]
                self.log(f"已加载环境 [{self.environment_name}] 的经纪商设置")
            elif brokers:
                first_broker_name = list(brokers.keys())[0]
                self.environment_name = first_broker_name
                self.current_broker_setting = brokers[first_broker_name]
                self.log(f"未指定环境或默认环境，已加载第一个可用环境 [{self.environment_name}] 的经纪商设置", "WARNING")
            else:
                self.log(f"在经纪商配置中未找到有效的经纪商设置！环境: {self.environment_name}", "ERROR")
                self.current_broker_setting = None
        except Exception as e:
            self.log(f"加载或解析 broker 配置文件时出错：{e}", "ERROR")
            self.current_broker_setting = None

    async def wait_for_login(self, timeout: int) -> bool:
        """
        等待登录成功。
        :param timeout: 超时时间（秒）
        :return: bool
        """
        start_time = asyncio.get_event_loop().time()
        while True:
            if global_var.td_login_success:
                return True

            if asyncio.get_event_loop().time() - start_time >= timeout:
                return False

            await asyncio.sleep(0.5)

    async def start(self):
        """启动主引擎和所有组件"""
        self.log("主引擎启动中...")
        self.event_engine.start()

        if self.current_broker_setting:
            td_gateway = self.add_gateway(CtpGateway)
            if td_gateway:
                self.log(f"正在连接交易网关，使用账户: {self.current_broker_setting.get('userid', 'N/A')} @ {self.current_broker_setting.get('td_address', 'N/A')}")
                loop = asyncio.get_event_loop()
                try:
                    loop.run_in_executor(None, td_gateway.connect_td, self.current_broker_setting)
                    self.log("交易网关连接指令已发送")

                    self.log("等待交易服务器登录...")
                    login_success = await self.wait_for_login(timeout=15)
                    if login_success:
                        self.log("交易服务器登录成功。")
                    else:
                        self.log("交易服务器登录超时或失败。", "ERROR")

                except Exception as e:
                    self.log(f"连接交易网关失败: {e}", "ERROR")
        else:
            self.log("未添加CTP交易网关，因为经纪商设置加载失败或不完整。", "ERROR")

        # 添加策略
        self.add_strategy(ExampleStrategy, "Example_SA509_1", {"symbol": "SA509", "exchange": "CZCE"})

        # 初始化策略
        for strategy_name, strategy in self.strategies.items():
            self.log(f"正在初始化策略 {strategy_name}...")
            await strategy.on_init()

        # 启动策略
        for strategy_name, strategy in self.strategies.items():
            self.log(f"正在启动策略 {strategy_name}...")
            await strategy.on_start()

        self.log("主引擎已启动完成。")

    async def stop(self):
        """停止主引擎和所有组件"""
        if not self._running:
            return
        self._running = False
        self.log("主引擎停止中...")

        for gw_name, gateway in self.gateways.items():
            self.log(f"正在关闭网关 {gw_name}...")
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda: gateway.close())

        await self.event_engine.stop()
        self.log("主引擎已停止。")


async def run_main_engine(environment: Optional[str] = None):
    """主引擎运行入口"""
    zmq_event_engine = ZmqEventEngine(engine_id="MainEngineZMQ", environment_name=environment)
    main_engine = MainEngine(event_engine=zmq_event_engine, environment_name=environment)

    stop_event = asyncio.Event()

    def handle_signal():
        main_engine.log("捕获到退出信号，开始关闭...")
        if not stop_event.is_set():
            stop_event.set()

    if sys.platform == "win32":
        main_engine.log("Windows 平台：请使用 Ctrl+C 来触发关闭。", "INFO")
    else:
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, handle_signal)
            except NotImplementedError:
                main_engine.log(f"无法为信号 {sig} 添加处理器。依赖 KeyboardInterrupt。", "WARNING")

    try:
        await main_engine.start()
        await stop_event.wait()
    except KeyboardInterrupt:
        main_engine.log("捕获到 KeyboardInterrupt，触发关闭...")
    except Exception as e:
        main_engine.log(f"主引擎运行出错: {e}", "CRITICAL")
        import traceback
        main_engine.log(traceback.format_exc(), "ERROR")
    finally:
        main_engine.log("执行最终清理...")
        await main_engine.stop()
        main_engine.log("所有组件已停止。程序退出。")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    args = runner_args("Broker environment name (e.g., simnow, tts from broker_config.json)")

    asyncio.run(run_main_engine(environment=args.ctp_env))
