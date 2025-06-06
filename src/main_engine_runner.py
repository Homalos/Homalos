#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : main_engine_runner.py
@Date       : 2025/6/01 19:03
@Author     : Donny
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 提供了启动、协调和停止整个系统的框架。
"""
import asyncio
import os
import signal
import sys
from typing import Dict, Type, Optional

from src.config.constants import Exchange
from src.config.setting import get_broker_setting
from src.core.base_gateway import BaseGateway
from src.core.event import EventType, OrderRequestEvent, CancelOrderRequestEvent, LogEvent, GatewayStatusEvent, SubscribeRequestEvent
from src.core.event_engine import EventEngine
from src.core.object import LogData, OrderRequest, CancelRequest, SubscribeRequest, GatewayStatusData, GatewayConnectionStatus
from src.ctp.gateway.ctp_gateway import CtpGateway
from src.ctp.gateway.ctp_mapping import EXCHANGE_CTP2VT
from src.strategies.base_strategy import BaseStrategy
from src.strategies.example_strategy import ExampleStrategy
from src.util.i18n import _
from src.util.logger import log, setup_logging
from src.util.runner_common import runner_args
from src.messaging.zmq_event_engine import ZmqEventEngine
from src.config import global_var

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


class MainEngine:
    def __init__(self, event_engine: EventEngine | ZmqEventEngine, environment_name: Optional[str] = None):
        setup_logging(service_name=f"{self.__class__.__name__}[{args.ctp_env if 'args' in globals() and args.ctp_env else environment_name or 'default'}]")
        self.event_engine: EventEngine | ZmqEventEngine = event_engine
        self.gateways: Dict[str, BaseGateway] = {}
        self.strategies: Dict[str, BaseStrategy] = {}
        self._running = True
        self.environment_name: Optional[str] = environment_name
        self.current_broker_setting: Optional[dict] = None
        self.using_external_md_service = True  # 标记是否使用外部行情服务

        self.event_engine.register(EventType.ORDER_REQUEST, self.process_order_request)
        self.event_engine.register(EventType.CANCEL_ORDER_REQUEST, self.process_cancel_order_request)
        self.event_engine.register(EventType.LOG, self.process_log_event)
        self.event_engine.register(EventType.GATEWAY_STATUS, self.process_gateway_status_event)

        self._load_broker_config()

    def _load_broker_config(self):
        """
        根据 environment_name 或默认值加载代理配置。
        :return:
        """
        try:
            all_brokers_config = get_broker_setting() 
            brokers = all_brokers_config.get("brokers", {})
            default_broker_name = all_brokers_config.get("default_broker")

            if self.environment_name and self.environment_name in brokers:
                self.current_broker_setting = brokers[self.environment_name]
                self.log(_(f"已加载环境 [{self.environment_name}] 的经纪商设置"))
            elif default_broker_name and default_broker_name in brokers:
                self.environment_name = default_broker_name # Update environment_name to the one being used
                self.current_broker_setting = brokers[self.environment_name]
                self.log(_(f"未指定环境，已加载默认环境 [{self.environment_name}] 的经纪商设置"))
            elif brokers: 
                first_broker_name = list(brokers.keys())[0]
                self.environment_name = first_broker_name # Update environment_name
                self.current_broker_setting = brokers[first_broker_name]
                self.log(_(f"未指定环境或默认环境，已加载第一个可用环境 [{self.environment_name}] 的经纪商设置"), "WARNING")
            else:
                self.log(_(f"在经纪商配置中未找到有效的经纪商设置！环境: {self.environment_name}"), "ERROR")
                self.current_broker_setting = None

        except FileNotFoundError:
            self.log(_("未找到 broker 配置文件！"), "ERROR")
            self.current_broker_setting = None
        except Exception as err:
            self.log(_(f"加载或解析 broker 配置文件时出错：{err}"), "ERROR")
            self.current_broker_setting = None

    async def process_order_request(self, event: OrderRequestEvent):
        """
        处理来自策略的订单请求。
        :param event:
        :return:
        """
        req: OrderRequest = event.data
        # Determine gateway based on the exchange in the order request
        gateway_name = self.get_default_gateway_name(exchange_filter=req.exchange.value if req.exchange else None)
        
        if gateway_name and gateway_name in self.gateways:
            gateway = self.gateways[gateway_name]
            loop = asyncio.get_event_loop()
            order_id = await loop.run_in_executor(None, gateway.send_order, req)
            if order_id:
                self.log(f"主引擎：订单请求已发送至网关 {gateway_name}，获取到的订单ID (可能为本地): {order_id}")
            else:
                self.log(f"主引擎：订单请求发送至网关 {gateway_name} 失败。", "ERROR")
        elif gateway_name: # Gateway name was determined but not found in self.gateways
            self.log(f"主引擎：为交易所 {req.exchange.value if req.exchange else 'N/A'} 确定的订单网关 {gateway_name} 未在已加载的网关中找到。", "ERROR")
        else: # No suitable gateway could be determined
            self.log(f"主引擎：无法为交易所 {req.exchange.value if req.exchange else 'N/A'} 确定合适的订单网关。", "ERROR")

    async def process_cancel_order_request(self, event: CancelOrderRequestEvent):
        """
        处理来自策略的撤单请求。
        :param event:
        :return:
        """
        req: CancelRequest = event.data
        # Determine gateway based on the exchange in the cancel request
        gateway_name = self.get_default_gateway_name(exchange_filter=req.exchange.value if req.exchange else None)

        if gateway_name and gateway_name in self.gateways:
            gateway = self.gateways[gateway_name]
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, gateway.cancel_order, req)
            self.log(f"主引擎：撤单请求已发送至网关 {gateway_name} for order {req.orderid}")
        elif gateway_name: # Gateway name was determined but not found in self.gateways
            self.log(f"主引擎：为交易所 {req.exchange.value if req.exchange else 'N/A'} 确定的撤单网关 {gateway_name} 未在已加载的网关中找到。", "ERROR")
        else: # No suitable gateway could be determined
            self.log(f"主引擎：无法为交易所 {req.exchange.value if req.exchange else 'N/A'} 确定合适的撤单网关。", "ERROR")

    @staticmethod
    async def process_log_event(event: LogEvent):
        """处理日志事件。"""
        log_data: LogData = event.data
        if log_data.origin and log_data.origin != "MainEngine":
            return
        log(f"{log_data.msg}", log_data.level)

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

    async def wait_for_login(self, timeout: int, login_type: str) -> bool:
        """
        等待登录成功。
        :param timeout: 超时时间（秒）
        :param login_type: 'md' 或 'td'
        :return: bool
        """
        start_time = asyncio.get_event_loop().time()
        while True:
            if login_type == 'md' and global_var.md_login_success:
                return True
            if login_type == 'td' and global_var.td_login_success:
                return True

            if asyncio.get_event_loop().time() - start_time >= timeout:
                return False

            await asyncio.sleep(0.5)

    def get_default_gateway_name(self, exchange_filter: Optional[str] = None) -> str:
        """
        获取默认网关名称。如果提供了交易所过滤器，则尝试找到支持该交易所的网关。
        :param exchange_filter:
        :return:
        """
        if not self.gateways:
            return ""
        
        # Construct the expected name for a CTP gateway based on the current environment
        if self.environment_name:
            ctp_gw_name = f"CTP_TD_{self.environment_name}"  # 修改为只查找交易网关
            if ctp_gw_name in self.gateways:
                if exchange_filter and exchange_filter in self.gateways[ctp_gw_name].exchanges:
                    return ctp_gw_name
                elif not exchange_filter:
                    return ctp_gw_name
        
        if exchange_filter:
            for name, gw in self.gateways.items():
                if exchange_filter in gw.exchanges: 
                    return name
        
        return list(self.gateways.keys())[0]

    def add_gateway(self, gateway_class: Type[BaseGateway], gateway_name_prefix: str = "CTP_TD"):
        """
        添加并初始化一个网关。
        对于CTP网关，它将使用 self.current_broker_setting。
        gateway_name 将基于 environment_name (broker name) 和 prefix 构建, e.g., CTP_TD_simnow
        """
        actual_gateway_name = gateway_name_prefix # Default if not CTP or no environment
        gw_settings_to_use = None

        if gateway_class == CtpGateway:
            if not self.current_broker_setting or not self.environment_name:
                self.log(f"无法添加 {gateway_name_prefix} 网关，因为未从配置加载有效的 CTP 经纪商设置 (当前环境: {self.environment_name})。", "ERROR")
                return None
            actual_gateway_name = f"{gateway_name_prefix}_{self.environment_name}"
            gw_settings_to_use = self.current_broker_setting
        # else:
            # Placeholder for other gateway types' settings, e.g., from get_global_setting()
            # gw_settings_to_use = get_global_setting(f"{gateway_name_prefix.upper()}.")

        if actual_gateway_name in self.gateways:
            self.log(f"网关 {actual_gateway_name} 已存在。", "WARNING")
            # Return existing gateway and its presumed settings
            return self.gateways[actual_gateway_name] 
            
        if not gw_settings_to_use and gateway_class.default_setting:
             gw_settings_to_use = gateway_class.default_setting
        
        if not gw_settings_to_use: # Check specific for CTP after trying default_setting
            if gateway_class == CtpGateway:
                 self.log(f"CTP 网关 {actual_gateway_name} 的账户配置信息为空或未找到。", "ERROR")
                 return None
            else: # For other types, this might be acceptable if they don't require settings
                 self.log(f"网关 {actual_gateway_name} 的配置为空，但其类型非 CTP。", "WARNING")

        gateway = gateway_class(actual_gateway_name, self.event_engine)
        self.gateways[actual_gateway_name] = gateway
        self.log(f"网关 {actual_gateway_name} ({gateway_class.__name__}) 已添加。")
        # We don't return settings from here anymore, connect will fetch them in start()
        return gateway

    def add_strategy(self, strategy_class: Type[BaseStrategy], strategy_id: str, params: Optional[dict] = None):
        """
        添加并初始化一个策略。
        :param strategy_class:
        :param strategy_id:
        :param params:
        :return:
        """
        if strategy_id in self.strategies:
            self.log(f"策略 {strategy_id} 已存在。", "WARNING")
            return
        strategy = strategy_class(strategy_id, self.event_engine, params)
        self.strategies[strategy_id] = strategy
        self.log(f"策略 {strategy_id} ({strategy_class.strategy_name}) 已添加。")
        return strategy

    def log(self, msg: str, level: str = "INFO"):
        """
        辅助方法将 LogEvent 放到事件引擎上，或者在不活动时打印。
        :param msg:
        :param level:
        :return:
        """
        log_data = LogData(msg=msg, level=level, gateway_name="MainEngine", origin="MainEngine")

        if self.event_engine and self.event_engine.is_active():
            # 直接 await put 方法，而不是创建任务
            # 这使得任何在 put 方法中发生的异常都能被捕获和记录
            try:
                # 确保我们处于可以 await 的上下文中
                # 注意：这假设 log() 是从协程中调用的。
                loop = asyncio.get_running_loop()
                if loop.is_running():
                     asyncio.run_coroutine_threadsafe(self.event_engine.put(LogEvent(data=log_data)), loop)
                else:
                    log(f"(LogEngineLoopInactive) {log_data.msg}", log_data.level)
            except RuntimeError:
                 log(f"(LogEngineNoLoop) {log_data.msg}", log_data.level)
            except Exception as e:
                log(f"记录日志事件时出错: {e}", "ERROR")
        else:
            # Fallback to print if event_engine is not available or not active
            log(f"{log_data.msg}", log_data.level)

    async def send_subscribe_request(self, symbol: str, exchange: Exchange):
        """
        发送订阅请求到行情网关服务
        """
        if not self.event_engine or not self.event_engine.is_active():
            self.log(f"无法发送订阅请求，事件引擎未激活", "ERROR")
            return
            
        req = SubscribeRequest(symbol=symbol, exchange=exchange)
        self.log(f"发送订阅请求: {symbol} 交易所: {exchange.value}")
        
        # 创建订阅请求事件并发送
        event = SubscribeRequestEvent(data=req)
        await self.event_engine.put(event)
        self.log(f"订阅请求已发送: {symbol}")

    async def start(self):
        """
        启动主引擎和所有组件。
        :return:
        """
        self.log("主引擎启动中...")
        self.event_engine.start()

        # 只连接交易网关，不再连接行情网关
        if self.current_broker_setting and self.environment_name:
            # 添加交易网关
            td_gateway = self.add_gateway(CtpGateway, "CTP_TD")
            
            if td_gateway:
                self.log(f"正在连接交易网关，使用账户: {self.current_broker_setting.get('userid', 'N/A')} @ {self.current_broker_setting.get('td_address', 'N/A')}")
                loop = asyncio.get_event_loop()
                try:
                    # 只连接交易接口
                    await loop.run_in_executor(None, td_gateway.connect_td, self.current_broker_setting)
                    self.log(f"交易网关连接指令已发送")

                    # 增加延时等待，检查登录状态
                    self.log("等待交易服务器登录...")
                    login_success = await self.wait_for_login(timeout=15, login_type='td')
                    if not login_success:
                        self.log("交易服务器登录超时或失败。", "ERROR")
                    else:
                        self.log("交易服务器登录成功。")

                except Exception as e:
                    self.log(f"连接交易网关失败: {e}", "ERROR")
        else:
            self.log("未添加CTP交易网关，因为经纪商设置加载失败、不完整或未指定有效环境。", "ERROR")

        # --- 统一处理合约订阅 ---
        symbols_to_subscribe = set()

        # 1. 从配置文件收集默认合约
        if self.current_broker_setting:
            default_subscriptions = self.current_broker_setting.get("default_subscriptions", [])
            if not default_subscriptions:
                all_brokers_config = get_broker_setting()
                default_subscriptions = all_brokers_config.get("default_subscriptions", [])
            
            for symbol in default_subscriptions:
                symbols_to_subscribe.add(symbol)
        
        # 2. 从策略实例收集合约
        for strategy in self.strategies.values():
            if hasattr(strategy, 'subscribed_symbol'):
                symbols_to_subscribe.add(strategy.subscribed_symbol)

        # 3. 遍历去重后的集合，发送订阅请求
        if symbols_to_subscribe:
            self.log(f"开始统一订阅合约列表: {list(symbols_to_subscribe)}")
            for symbol in symbols_to_subscribe:
                exchange_enum = self._guess_exchange_from_symbol(symbol)
                if exchange_enum:
                    await self.send_subscribe_request(symbol, exchange_enum)
                else:
                    self.log(f"无法确定合约 {symbol} 的交易所，跳过订阅", "WARNING")
        else:
            self.log("未找到需要订阅的合约。", "WARNING")
        
        # 初始化并启动策略
        for strategy_id, strategy in self.strategies.items():
            self.log(f"正在初始化策略 {strategy_id}...")
            await strategy.on_init()
            self.log(f"正在启动策略 {strategy_id}...")
            await strategy.on_start()
        
        self.log("主引擎已启动完成。所有组件运行中。")

    def _guess_exchange_from_symbol(self, symbol: str) -> Optional[Exchange]:
        """
        根据合约代码特征猜测交易所。
        :param symbol: 合约代码
        :return: Exchange枚举或None
        """
        if symbol.startswith(("cu", "al", "zn", "pb", "ni", "sn", "au", "ag", "rb", "hc", "ss", "sc", "fu", "bu", "ru")):
            return Exchange.SHFE
        elif symbol.startswith(("IF", "IC", "IH", "TS", "TF", "T")):
            return Exchange.CFFEX
        elif symbol.startswith(("c", "cs", "a", "b", "m", "y", "p", "fb", "bb", "jd", "l", "v", "pp", "j", "jm", "i")):
            return Exchange.DCE
        elif symbol.startswith(("SR", "CF", "CY", "TA", "OI", "MA", "FG", "RM", "ZC", "JR", "LR", "PM", "RI", "RS", "SM", "WH", "AP", "CJ", "UR", "SA", "PF")):
            return Exchange.CZCE
        return None

    async def stop(self):
        """
        停止主引擎和所有组件。
        :return:
        """
        if not self._running:
            return
        self._running = False
        self.log("主引擎停止中...")

        # 停止策略
        for strategy_id, strategy in self.strategies.items():
            self.log(f"正在停止策略 {strategy_id}...")
            await strategy.on_stop()

        # 关闭网关连接
        for gw_name, gateway in self.gateways.items():
            self.log(f"正在关闭网关 {gw_name}...")
            loop = asyncio.get_event_loop()
            # Use lambda to wrap gateway.close()
            await loop.run_in_executor(None, lambda: gateway.close())  # type: ignore[call-arg]
            # gateway.close()

        # 停止事件引擎
        await self.event_engine.stop()
        self.log("主引擎已停止。")

async def run_main(environment: Optional[str] = None):
    # Configuration for ZMQ addresses (should be moved to a config file later)
    ZMQ_PUB_ADDRESS = "tcp://*:5555"  # 主引擎发布地址
    ZMQ_SUB_ADDRESS = "tcp://localhost:5556" # 订阅行情网关服务的地址

    # Instantiate the chosen event engine
    zmq_event_engine = ZmqEventEngine(pub_addr=ZMQ_PUB_ADDRESS, 
                                     sub_addr=ZMQ_SUB_ADDRESS, 
                                     engine_id="MainEngineZMQ",
                                     environment_name=environment)
    
    # in_process_event_engine = EventEngine()
    main_engine = MainEngine(event_engine=zmq_event_engine, environment_name=environment)

    example_params = {"symbol": "SA509"}
    main_engine.add_strategy(ExampleStrategy, "ExampleStrategy01", example_params)

    stop_event = asyncio.Event()

    # 为Windows和POSIX系统设置信号处理
    def handle_signal():
        main_engine.log("捕获到退出信号，开始关闭...")
        if not stop_event.is_set():
            stop_event.set()

    if sys.platform == "win32":
        # 在Windows上，add_signal_handler对SIGINT/SIGTERM支持不佳
        # KeyboardInterrupt将是主要退出方式
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
        main_engine.log("主引擎启动完成，进入主循环等待。")
        await stop_event.wait()  # 等待停止信号
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
    # import argparse
    # parser = argparse.ArgumentParser()
    # parser.add_argument("--ctp_env", type=str, help="Broker environment name (e.g., simnow, tts from broker_config.json)")
    # args = parser.parse_args()

    # Ensure src.config.setting.get_broker_setting() is correctly implemented
    # to load your broker_config.json (or equivalent YAML)
    # from src.config.path import GlobalPath
    # from src.util.file_helper import load_json
    # def _get_broker_config_manual(): # Example: if get_broker_setting isn't there
    #     return load_json(str(GlobalPath.project_files_path.joinpath("broker_config.json")))
    # if not hasattr(src.config.setting, 'get_broker_setting'):
    #     print("Warning: src.config.setting.get_broker_setting not found, attempting manual load of broker_config.json for demo.")
    #     import src.config.setting
    #     src.config.setting.get_broker_setting = _get_broker_config_manual

    asyncio.run(run_main(environment=args.ctp_env))