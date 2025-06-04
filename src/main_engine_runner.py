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
from src.core.event import EventType, OrderRequestEvent, CancelOrderRequestEvent, LogEvent
from src.core.event_engine import EventEngine
from src.core.object import LogData, OrderRequest, CancelRequest, SubscribeRequest
from src.ctp.gateway.ctp_gateway import CtpGateway
from src.ctp.gateway.ctp_mapping import EXCHANGE_CTP2VT
from src.strategies.base_strategy import BaseStrategy
from src.strategies.example_strategy import ExampleStrategy
from src.util.i18n import _
from src.util.logger import log, setup_logging
from src.util.runner_common import runner_args
from src.messaging.zmq_event_engine import ZmqEventEngine

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

        self.event_engine.register(EventType.ORDER_REQUEST, self.process_order_request)
        self.event_engine.register(EventType.CANCEL_ORDER_REQUEST, self.process_cancel_order_request)
        self.event_engine.register(EventType.LOG, self.process_log_event)

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
        log(f"{log_data.msg}", log_data.level)

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
            ctp_gw_name = f"CTP_{self.environment_name}"
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

    def add_gateway(self, gateway_class: Type[BaseGateway], gateway_name_prefix: str = "CTP"):
        """
        添加并初始化一个网关。
        对于CTP网关，它将使用 self.current_broker_setting。
        gateway_name 将基于 environment_name (broker name) 和 prefix 构建, e.g., CTP_simnow
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
        log_data = LogData(msg=msg, level=level, gateway_name=self.gateway_name if hasattr(self, 'gateway_name') else "MainEngine")

        if self.event_engine and self.event_engine.is_active(): # Changed to use is_active()
            # Create a task to put the log event onto the queue
            # This assumes log() is called from an async context or where create_task is appropriate
            try:
                loop = asyncio.get_running_loop()
                if loop.is_running(): # Ensure loop is running for create_task
                    asyncio.create_task(self.event_engine.put(LogEvent(data=log_data)))
                else: # Fallback if loop isn't running (e.g. during early init or shutdown)
                    log(f"(LogEngineLoopInactive) {log_data.msg}", log_data.level)
            except RuntimeError: # No running loop, e.g. called from a non-async thread before engine start
                 log(f"(LogEngineNoLoop) {log_data.msg}", log_data.level)
        else:
            # Fallback to print if event_engine is not available or not active
            log(f"{log_data.msg}", log_data.level)

    async def start(self):
        """
        启动主引擎和所有组件。
        :return:
        """
        self.log("主引擎启动中...")
        self.event_engine.start()

        gateways_to_connect = list(self.gateways.items())

        for gw_name, gateway in gateways_to_connect:
            settings_for_connect = None
            if isinstance(gateway, CtpGateway):
                # For CTP gateway, settings must come from the loaded current_broker_setting
                if self.current_broker_setting and self.environment_name == gw_name.split('_', 1)[-1]: # Ensure settings match gateway
                    settings_for_connect = self.current_broker_setting
                else:
                    self.log(f"CTP 网关 {gw_name} 的特定环境设置 ({self.environment_name}) 未找到或不匹配。无法连接。", "ERROR")
                    continue # Skip connecting this gateway
            # else:
                # For other gateway types, load their specific global settings if needed
                # settings_for_connect = get_global_setting(f"{gw_name.upper()}.") 
                # if not settings_for_connect and hasattr(gateway, 'default_setting') and gateway.default_setting:
                #    settings_for_connect = gateway.default_setting
                pass # Placeholder

            if not settings_for_connect and hasattr(gateway, 'default_setting') and gateway.default_setting and not isinstance(gateway, CtpGateway):
                 settings_for_connect = gateway.default_setting
                 self.log(f"网关 {gw_name} 使用其默认设置进行连接。", "INFO")
            
            if settings_for_connect:
                self.log(f"正在连接网关 {gw_name} 使用设置: {settings_for_connect.get('userid', 'N/A')} @ {settings_for_connect.get('td_address', 'N/A')}")
                loop = asyncio.get_event_loop()
                try:
                    await loop.run_in_executor(None, gateway.connect, settings_for_connect)
                    self.log(f"网关 {gw_name} 连接指令已发送。 (具体连接状态需查看后续日志)")

                    # 假设连接成功后，为示例策略订阅行情
                    if isinstance(gateway, CtpGateway): # 特别为CTP网关处理
                        for strat_id, strat in self.strategies.items():
                            if isinstance(strat, ExampleStrategy) and hasattr(strat, 'subscribed_symbol'):
                                symbol_to_subscribe = strat.subscribed_symbol
                                exchange_for_symbol: Optional[Exchange] = None

                                # Try to get CTP exchange string from gateway's instrument_exchange_map
                                ctp_exchange_str = gateway.instrument_exchange_map.get(symbol_to_subscribe)
                                
                                if ctp_exchange_str:
                                    exchange_for_symbol = EXCHANGE_CTP2VT.get(ctp_exchange_str)
                                
                                if exchange_for_symbol:
                                    sub_req = SubscribeRequest(symbol=symbol_to_subscribe, exchange=exchange_for_symbol)
                                    self.log(f"为策略 {strat_id} 订阅行情: {symbol_to_subscribe} on {exchange_for_symbol.value}")
                                    await loop.run_in_executor(None, gateway.subscribe, sub_req)
                                else:
                                    self.log(f"无法确定合约 {symbol_to_subscribe} (CTP Exchange: {ctp_exchange_str}) 的交易所枚举，无法为其订阅行情。", "WARNING")
                except Exception as e:
                    self.log(f"连接网关 {gw_name} 失败: {e}", "ERROR")       
            else:
                self.log(f"网关 {gw_name} 的配置未找到，跳过连接。", "WARNING")

        # 初始化并启动策略
        for strategy_id, strategy in self.strategies.items():
            self.log(f"正在初始化策略 {strategy_id}...")
            await strategy.on_init()
            self.log(f"正在启动策略 {strategy_id}...")
            await strategy.on_start()
        
        self.log("主引擎已启动完成。所有组件运行中。")

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
    ZMQ_PUB_ADDRESS = "tcp://*:5555"  # Address for components to publish events
    ZMQ_SUB_ADDRESS = "tcp://localhost:5555" # Address for this MainEngine instance to subscribe

    # Instantiate the chosen event engine
    zmq_event_engine = ZmqEventEngine(pub_addr=ZMQ_PUB_ADDRESS, sub_addr=ZMQ_SUB_ADDRESS, engine_id="MainEngineZMQ")
    
    # in_process_event_engine = EventEngine()
    main_engine = MainEngine(event_engine=zmq_event_engine, environment_name=environment)

    if main_engine.current_broker_setting and main_engine.environment_name:
        main_engine.add_gateway(CtpGateway, "CTP")
    else:
        main_engine.log("未添加CTP网关，因为经纪商设置加载失败、不完整或未指定有效环境。", "ERROR")

    example_params = {"symbol": "SA509"}
    main_engine.add_strategy(ExampleStrategy, "ExampleStrategy01", example_params)

    stop_event = asyncio.Event()

    # Simplified signal handling for Windows compatibility
    if sys.platform != "win32": # POSIX-like systems can use add_signal_handler
        loop = asyncio.get_event_loop()
        def signal_handler_posix():
            main_engine.log("捕获到退出信号 (POSIX)，开始关闭...")
            if not stop_event.is_set():
                stop_event.set()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, signal_handler_posix)
            except NotImplementedError:
                main_engine.log(f"无法为信号 {sig} 添加处理器 (NotImplementedError)。依赖 KeyboardInterrupt。", "WARNING")
    else: # For Windows, rely primarily on KeyboardInterrupt
        main_engine.log("Windows 平台：请使用 Ctrl+C 来触发关闭。", "INFO")
        # On Windows, Ctrl+C raises KeyboardInterrupt in the main thread
        # which will be caught by the try...except block below.

    try:
        await main_engine.start()
        while not stop_event.is_set() and main_engine._running:
            await asyncio.sleep(1)
        main_engine.log("主循环结束或收到停止信号，准备执行停止操作。")

    except KeyboardInterrupt:
        main_engine.log("捕获到 KeyboardInterrupt，开始关闭...")
        if not stop_event.is_set(): # Ensure stop_event is set if KeyboardInterrupt is the trigger
            stop_event.set()
    except Exception as e:
        main_engine.log(f"主引擎运行出错: {e}", "CRITICAL")
        import traceback
        main_engine.log(traceback.format_exc(), "ERROR")
    finally:
        main_engine.log("执行最终清理...")
        # Ensure stop is called, especially if loop was exited due to stop_event
        if not main_engine._running and stop_event.is_set(): # If already being stopped by an internal mechanism that also set stop_event
             pass # main_engine.stop() will be called if _running became false.
        elif main_engine._running: # If loop exited due to stop_event but engine thinks it's still running
            main_engine._running = False # Mark as not running before calling stop if not already
        
        await main_engine.stop() # This will now handle the actual stopping sequence
        main_engine.log("所有组件已停止。程序退出。")

if __name__ == "__main__":
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