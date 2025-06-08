#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : market_data_service.py
@Date       : 2025/6/02 11:00
@Author     : Donny
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 专门负责行情数据处理和分发的服务。
"""
import asyncio
import logging
import os
import signal
import sys
import time
from typing import Dict, Type, Optional

from src.config import global_var
from src.config.setting import get_broker_setting
from src.core.base_gateway import BaseGateway
from src.core.event import EventType, SubscribeRequestEvent, LogEvent, GatewayStatusEvent, TickEvent
from src.core.object import SubscribeRequest, LogData, GatewayStatusData, GatewayConnectionStatus, TickData
from src.ctp.gateway.ctp_gateway import CtpGateway
from src.messaging.zmq_event_engine import ZmqEventEngine
from src.util.logger import log, setup_logging
from src.util.runner_common import runner_args

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


class MarketDataEngine:
    """
    专门负责行情数据处理和分发的引擎。
    - 连接行情网关
    - 接收来自其他服务的订阅请求
    - 将行情数据通过ZMQ发布出去
    """

    def __init__(self, event_engine: ZmqEventEngine, environment_name: Optional[str] = None):
        # args might not be globally available if not run as main, so handle it.
        env_for_logging = (
            args.ctp_env 
            if 'args' in globals() and hasattr(args, 'ctp_env') 
            else environment_name or 'default'
        )
        setup_logging(service_name=f"{self.__class__.__name__}[{env_for_logging}]")

        self.event_engine: ZmqEventEngine = event_engine
        self.gateways: Dict[str, BaseGateway] = {}
        self._running = True
        self.environment_name: Optional[str] = environment_name
        self.current_broker_setting: Optional[dict] = None
        
        # 心跳检测相关变量
        self.last_tick_time = 0
        self.subscribed_symbols = set()
        self.heartbeat_task = None
        
        # 注册对订阅请求的处理
        self.event_engine.register(EventType.SUBSCRIBE_REQUEST, self.process_subscribe_request)
        self.event_engine.register(EventType.GATEWAY_STATUS, self.process_gateway_status_event)
        self.event_engine.register(EventType.TICK, self.process_tick_event)
        self.event_engine.register(EventType.LOG, self.process_log_event)

        self._load_broker_config()

    async def process_log_event(self, event: LogEvent):
        """处理日志事件。"""
        log_data: LogData = event.data
        # 仅处理来自此服务所拥有的网关的日志事件
        if log_data.gateway_name in self.gateways:
            level_str = log_data.level if isinstance(log_data.level, str) else logging.getLevelName(log_data.level)
            # 使用 self.log 以确保格式一致
            self.log(f"{log_data.msg}", level=level_str)

    async def process_tick_event(self, event: TickEvent):
        """处理行情Tick事件，更新最后接收时间"""
        tick: TickData = event.data
        self.last_tick_time = time.time()
        # 仅记录日志，不进行其他处理
        self.log(f"接收到行情Tick: {tick.symbol} @ {tick.exchange.value if tick.exchange else 'N/A'}, 价格: {tick.last_price}")
        
    async def heartbeat_check(self):
        """定期检查行情连接状态"""
        self.log("行情心跳检测任务已启动")
        while self._running:
            current_time = time.time()
            if self.last_tick_time > 0:
                elapsed = current_time - self.last_tick_time
                self.log(f"距离上次收到行情已经过去 {elapsed:.1f} 秒")
                
                # 如果30秒没有收到行情数据，考虑重新订阅
                if elapsed > 30 and self.subscribed_symbols:
                    self.log(f"长时间未收到行情，尝试重新订阅所有合约: {self.subscribed_symbols}", "WARNING")
                    gateway_name = self.get_default_gateway_name()
                    if gateway_name and gateway_name in self.gateways:
                        gateway = self.gateways[gateway_name]
                        for symbol in self.subscribed_symbols:
                            self.log(f"重新订阅合约: {symbol}")
                            # 这里需要知道合约对应的交易所，简化处理
                            # 实际应用中应该从缓存或查询得到
                            # TODO: 完善重新订阅逻辑
            
            # 每10秒检查一次
            await asyncio.sleep(10)
        
        self.log("行情心跳检测任务已停止")

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

    async def process_subscribe_request(self, event: SubscribeRequestEvent):
        """处理行情订阅请求"""
        req: SubscribeRequest = event.data
        self.log(f"收到行情订阅请求: {req.symbol} @ {req.exchange.value if req.exchange else 'N/A'}")
        
        # 记录订阅的合约，用于心跳检查时重新订阅
        self.subscribed_symbols.add(req.symbol)
        
        gateway_name = self.get_default_gateway_name()
        if gateway_name and gateway_name in self.gateways:
            gateway = self.gateways[gateway_name]
            self.log(f"使用网关 {gateway_name} 处理订阅请求")
            
            try:
                loop = asyncio.get_event_loop()
                # 不等待执行器完成。订阅请求应该是"即发即忘"，
                # 响应将通过 CTP 回调异步到达。
                # 等待这里会导致死锁。
                self.log(f"正在异步发送订阅请求到网关...")
                loop.run_in_executor(None, gateway.subscribe, req)
                self.log(f"订阅请求已异步发送到网关，等待回调响应")
            except Exception as e:
                self.log(f"发送订阅请求时出错: {e}", "ERROR")
                import traceback
                self.log(traceback.format_exc(), "ERROR")
        else:
            self.log(f"无法处理订阅请求，未找到合适的行情网关支持交易所 {req.exchange.value if req.exchange else 'N/A'}", "ERROR")

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

    def log(self, msg: str, level: str = "INFO"):
        """
        使用全局记录器记录消息。
        """
        # 直接使用导入的 log 函数，而不是通过事件引擎发布，以确保本地日志的可靠性。
        log(msg, level)

    def add_gateway(self, gateway_class: Type[BaseGateway], gateway_name_prefix: str = "CTP_MD"):
        """添加并初始化一个行情网关"""
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
    
    def get_default_gateway_name(self) -> str:
        """获取默认的行情网关名称"""
        if not self.gateways:
            return ""

        if self.environment_name:
            ctp_gw_name = f"CTP_MD_{self.environment_name}"
            if ctp_gw_name in self.gateways:
                return ctp_gw_name

        return list(self.gateways.keys())[0]

    async def wait_for_login(self, timeout: int) -> bool:
        """等待行情服务器登录成功"""
        start_time = asyncio.get_event_loop().time()
        while True:
            if global_var.md_login_success:
                return True
            if asyncio.get_event_loop().time() - start_time >= timeout:
                return False
            await asyncio.sleep(0.5)

    async def start(self):
        """启动行情引擎和所有组件"""
        self.log("行情数据引擎启动中...")
        self.event_engine.start()

        if self.current_broker_setting:
            md_gateway = self.add_gateway(CtpGateway, "CTP_MD")
            if md_gateway:
                self.log(f"正在连接行情网关，使用账户: {self.current_broker_setting.get('userid', 'N/A')} @ {self.current_broker_setting.get('md_address', 'N/A')}")
                loop = asyncio.get_event_loop()
                try:
                    loop.run_in_executor(None, md_gateway.connect_md, self.current_broker_setting)
                    self.log("行情网关连接指令已发送")
                    
                    self.log("等待行情服务器登录...")
                    login_success = await self.wait_for_login(timeout=10)
                    if login_success:
                        self.log("行情服务器登录成功。")
                    else:
                        self.log("行情服务器登录超时或失败。", "ERROR")

                except Exception as e:
                    self.log(f"连接行情网关失败: {e}", "ERROR")
        else:
            self.log("未添加CTP行情网关，因为经纪商设置加载失败或不完整。", "ERROR")
            
        # 启动心跳检测任务
        self.heartbeat_task = asyncio.create_task(self.heartbeat_check())
        self.log("心跳检测任务已启动")

        self.log("行情数据引擎已启动完成。等待订阅请求...")

    async def stop(self):
        """停止行情引擎和所有组件"""
        if not self._running:
            return
        self._running = False
        self.log("行情数据引擎停止中...")
        
        # 取消心跳检测任务
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
            try:
                await self.heartbeat_task
            except asyncio.CancelledError:
                self.log("心跳检测任务已取消")

        for gw_name, gateway in self.gateways.items():
            self.log(f"正在关闭网关 {gw_name}...")
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda: gateway.close()) # type: ignore

        await self.event_engine.stop()
        self.log("行情数据引擎已停止。")


async def run_market_data_service(environment: Optional[str] = None):
    
    zmq_event_engine = ZmqEventEngine(
        engine_id="MarketDataEngineZMQ",
        environment_name=environment
    )

    md_engine = MarketDataEngine(event_engine=zmq_event_engine, environment_name=environment)
    
    stop_event = asyncio.Event()

    def handle_signal():
        md_engine.log("捕获到退出信号，开始关闭...")
        if not stop_event.is_set():
            stop_event.set()

    if sys.platform == "win32":
        md_engine.log("Windows 平台：请使用 Ctrl+C 来触发关闭。", "INFO")
    else:
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, handle_signal)
            except NotImplementedError:
                md_engine.log(f"无法为信号 {sig} 添加处理器。依赖 KeyboardInterrupt。", "WARNING")

    try:
        await md_engine.start()
        await stop_event.wait()
    except KeyboardInterrupt:
        md_engine.log("捕获到 KeyboardInterrupt，触发关闭...")
    except Exception as e:
        md_engine.log(f"行情服务运行出错: {e}", "CRITICAL")
        import traceback
        md_engine.log(traceback.format_exc(), "ERROR")
    finally:
        md_engine.log("执行最终清理...")
        await md_engine.stop()
        md_engine.log("所有组件已停止。程序退出。")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
    args = runner_args("Broker environment name for Market Data Service (e.g., simnow, tts from broker_config.json)")
    
    asyncio.run(run_market_data_service(environment=args.ctp_env)) 