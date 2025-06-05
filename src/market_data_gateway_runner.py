#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : market_data_gateway_runner.py
@Date       : 2025/6/05 10:00
@Author     : Donny
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 独立的行情网关服务，负责连接CTP行情接口并通过ZMQ发布行情事件
"""
import asyncio
import os
import signal
import sys
from typing import Optional, List, Dict

# 确保项目根目录在路径中
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.config.setting import get_broker_setting
from src.core.event import EventType, SubscribeRequestEvent
from src.core.event_engine import EventEngine
from src.core.object import LogData, SubscribeRequest, GatewayConnectionStatus
from src.ctp.gateway.ctp_gateway import CtpGateway
from src.ctp.gateway.ctp_mapping import EXCHANGE_CTP2VT
from src.util.i18n import _
from src.util.logger import log, setup_logging
from src.util.runner_common import runner_args
from src.messaging.zmq_event_engine import ZmqEventEngine


class MarketDataGatewayService:
    """
    行情网关服务，负责:
    1. 连接CTP行情接口
    2. 订阅合约行情
    3. 通过ZMQ发布行情事件
    4. 接收订阅请求
    """
    
    def __init__(self, event_engine: ZmqEventEngine, environment_name: Optional[str] = None):
        setup_logging(service_name=f"{self.__class__.__name__}[{environment_name or 'default'}]")
        self.event_engine: ZmqEventEngine = event_engine
        self.environment_name: Optional[str] = environment_name
        self.current_broker_setting: Optional[dict] = None
        self.gateway: Optional[CtpGateway] = None
        self._running = True
        
        # 注册订阅请求处理器
        self.event_engine.register(EventType.SUBSCRIBE_REQUEST, self.process_subscribe_request)
        
        # 加载经纪商配置
        self._load_broker_config()
        
        # 默认订阅的合约列表
        self.default_symbols: List[str] = []
        
    def _load_broker_config(self):
        """
        根据 environment_name 加载经纪商配置
        """
        try:
            all_brokers_config = get_broker_setting()
            brokers = all_brokers_config.get("brokers", {})
            default_broker_name = all_brokers_config.get("default_broker")
            
            # 加载默认订阅合约列表
            self.default_symbols = all_brokers_config.get("default_subscriptions", [])
            
            if self.environment_name and self.environment_name in brokers:
                self.current_broker_setting = brokers[self.environment_name]
                self.log(f"已加载环境 [{self.environment_name}] 的经纪商设置")
            elif default_broker_name and default_broker_name in brokers:
                self.environment_name = default_broker_name
                self.current_broker_setting = brokers[self.environment_name]
                self.log(f"未指定环境，已加载默认环境 [{self.environment_name}] 的经纪商设置")
            elif brokers:
                first_broker_name = list(brokers.keys())[0]
                self.environment_name = first_broker_name
                self.current_broker_setting = brokers[first_broker_name]
                self.log(f"未指定环境或默认环境，已加载第一个可用环境 [{self.environment_name}] 的经纪商设置", "WARNING")
            else:
                self.log(f"在经纪商配置中未找到有效的经纪商设置！环境: {self.environment_name}", "ERROR")
                self.current_broker_setting = None
                
        except FileNotFoundError:
            self.log("未找到 broker 配置文件！", "ERROR")
            self.current_broker_setting = None
        except Exception as err:
            self.log(f"加载或解析 broker 配置文件时出错：{err}", "ERROR")
            self.current_broker_setting = None
    
    def initialize_gateway(self):
        """
        初始化CTP行情网关
        """
        self.log("正在初始化CTP行情网关...")
        if not self.current_broker_setting or not self.environment_name:
            self.log("无法初始化CTP行情网关，因为未加载有效的经纪商设置", "ERROR")
            return False
        
        gateway_name = f"CTP_MD_{self.environment_name}"
        self.log(f"创建CTP网关实例，名称: {gateway_name}")
        
        try:
            self.gateway = CtpGateway(gateway_name, self.event_engine)
            self.log(f"行情网关 {gateway_name} 已初始化")
            
            # 检查instrument_exchange_map是否已加载
            if hasattr(self.gateway, 'instrument_exchange_map') and self.gateway.instrument_exchange_map:
                self.log(f"合约交易所映射已加载，共 {len(self.gateway.instrument_exchange_map)} 个合约")
            else:
                self.log("警告：合约交易所映射未加载或为空", "WARNING")
            
            return True
        except Exception as e:
            self.log(f"初始化CTP网关实例时发生异常: {e}", "ERROR")
            import traceback
            self.log(traceback.format_exc(), "ERROR")
            return False
    
    async def connect_gateway(self):
        """
        连接CTP行情网关
        """
        self.log("正在连接CTP行情网关...")
        if not self.gateway or not self.current_broker_setting:
            self.log("无法连接行情网关，网关未初始化或经纪商设置无效", "ERROR")
            return False
        
        # 打印详细的连接信息
        self.log(f"行情网关连接信息:")
        self.log(f"  用户ID: {self.current_broker_setting.get('userid', 'N/A')}")
        self.log(f"  经纪商ID: {self.current_broker_setting.get('broker_id', 'N/A')}")
        self.log(f"  行情地址: {self.current_broker_setting.get('md_address', 'N/A')}")
        self.log(f"  AppID: {self.current_broker_setting.get('appid', 'N/A')}")
        
        # 仅连接行情接口，不连接交易接口
        loop = asyncio.get_event_loop()
        try:
            # 注意：CTP网关的connect_md方法是同步的，需要在线程池中执行
            self.log("开始调用CTP网关的connect_md方法...")
            await loop.run_in_executor(None, self.gateway.connect_md, self.current_broker_setting)
            self.log("CTP行情网关连接指令已发送")
            
            # 检查连接状态
            if self.gateway.md_api and self.gateway.md_api.connect_status:
                self.log("CTP行情网关前置已连接")
            else:
                self.log("CTP行情网关前置连接状态未知", "WARNING")
            
            return True
        except Exception as e:
            self.log(f"连接CTP行情网关失败: {e}", "ERROR")
            import traceback
            self.log(traceback.format_exc(), "ERROR")
            return False
    
    async def subscribe_default_symbols(self):
        """
        订阅默认合约列表
        """
        if not self.gateway or not self.gateway.md_api or not self.gateway.md_api.connect_status:
            self.log("无法订阅合约，行情网关未连接", "WARNING")
            return
        
        if not self.default_symbols:
            self.log("默认订阅合约列表为空，跳过订阅", "WARNING")
            return
        
        self.log(f"开始订阅默认合约，共 {len(self.default_symbols)} 个: {self.default_symbols}")
        
        success_count = 0
        fail_count = 0
        
        for symbol in self.default_symbols:
            try:
                self.log(f"正在处理合约: {symbol}")
                # 尝试从网关的映射中获取交易所信息
                exchange_str = self.gateway.instrument_exchange_map.get(symbol)
                if exchange_str:
                    self.log(f"从映射中获取到合约 {symbol} 的交易所: {exchange_str}")
                    exchange = EXCHANGE_CTP2VT.get(exchange_str)
                    if exchange:
                        self.log(f"转换为交易所枚举: {exchange.value}")
                        req = SubscribeRequest(symbol=symbol, exchange=exchange)
                        loop = asyncio.get_event_loop()
                        await loop.run_in_executor(None, self.gateway.subscribe, req)
                        self.log(f"已订阅合约: {symbol} 交易所: {exchange.value}")
                        success_count += 1
                    else:
                        self.log(f"无法将交易所字符串 '{exchange_str}' 转换为交易所枚举，跳过订阅合约 {symbol}", "WARNING")
                        fail_count += 1
                else:
                    # 尝试猜测交易所
                    self.log(f"合约 {symbol} 未在交易所映射中找到，尝试猜测交易所")
                    exchange = None
                    
                    # 根据合约代码特征猜测交易所
                    if symbol.startswith(("cu", "al", "zn", "pb", "ni", "sn", "au", "ag", "rb", "hc", "ss", "sc", "fu", "bu", "ru")):
                        exchange = Exchange.SHFE
                    elif symbol.startswith(("IF", "IC", "IH", "TS", "TF", "T")):
                        exchange = Exchange.CFFEX
                    elif symbol.startswith(("c", "cs", "a", "b", "m", "y", "p", "fb", "bb", "jd", "l", "v", "pp", "j", "jm", "i")):
                        exchange = Exchange.DCE
                    elif symbol.startswith(("SR", "CF", "CY", "TA", "OI", "MA", "FG", "RM", "ZC", "JR", "LR", "PM", "RI", "RS", "SM", "WH", "AP", "CJ", "UR", "SA", "PF")):
                        exchange = Exchange.CZCE
                    
                    if exchange:
                        self.log(f"猜测合约 {symbol} 的交易所为: {exchange.value}")
                        req = SubscribeRequest(symbol=symbol, exchange=exchange)
                        loop = asyncio.get_event_loop()
                        await loop.run_in_executor(None, self.gateway.subscribe, req)
                        self.log(f"已订阅合约: {symbol} 交易所: {exchange.value}")
                        success_count += 1
                    else:
                        self.log(f"无法猜测合约 {symbol} 的交易所，跳过订阅", "WARNING")
                        fail_count += 1
            except Exception as e:
                self.log(f"订阅合约 {symbol} 时发生异常: {e}", "ERROR")
                import traceback
                self.log(traceback.format_exc(), "ERROR")
                fail_count += 1
        
        self.log(f"默认合约订阅完成，成功: {success_count}，失败: {fail_count}")
    
    async def process_subscribe_request(self, event: SubscribeRequestEvent):
        """
        处理订阅请求事件
        """
        if not self.gateway or not self.gateway.md_api or not self.gateway.md_api.connect_status:
            self.log("收到订阅请求，但行情网关未连接，无法处理", "WARNING")
            return
        
        req: SubscribeRequest = event.data
        self.log(f"收到订阅请求: {req.symbol} 交易所: {req.exchange.value if req.exchange else 'N/A'}")
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.gateway.subscribe, req)
    
    def log(self, msg: str, level: str = "INFO"):
        """
        记录日志
        """
        log_data = LogData(msg=msg, level=level, gateway_name="MarketDataGatewayService")
        
        if self.event_engine and self.event_engine.is_active():
            try:
                loop = asyncio.get_running_loop()
                if loop.is_running():
                    asyncio.create_task(self.event_engine.put(EventType.LOG, log_data))
                else:
                    log(f"(LogEngineLoopInactive) {log_data.msg}", log_data.level)
            except RuntimeError:
                log(f"(LogEngineNoLoop) {log_data.msg}", log_data.level)
        else:
            log(f"{log_data.msg}", log_data.level)
    
    async def start(self):
        """
        启动行情网关服务
        """
        self.log("行情网关服务启动中...")
        
        # 启动事件引擎
        try:
            self.event_engine.start()
            self.log("事件引擎启动成功")
        except Exception as e:
            self.log(f"事件引擎启动失败: {e}", "ERROR")
            import traceback
            self.log(traceback.format_exc(), "ERROR")
            return False
        
        # 初始化网关
        try:
            self.log("开始初始化行情网关...")
            if not self.initialize_gateway():
                self.log("行情网关初始化失败，服务无法启动", "ERROR")
                return False
            self.log("行情网关初始化成功")
        except Exception as e:
            self.log(f"行情网关初始化过程中发生异常: {e}", "ERROR")
            import traceback
            self.log(traceback.format_exc(), "ERROR")
            return False
        
        # 连接网关
        try:
            self.log("开始连接行情网关...")
            if not await self.connect_gateway():
                self.log("行情网关连接失败，服务无法启动", "ERROR")
                return False
            self.log("行情网关连接指令已发送，等待登录结果...")
        except Exception as e:
            self.log(f"行情网关连接过程中发生异常: {e}", "ERROR")
            import traceback
            self.log(traceback.format_exc(), "ERROR")
            return False
        
        # 等待行情网关连接成功
        try:
            retry_count = 0
            max_retries = 10
            while retry_count < max_retries:
                if self.gateway and self.gateway.md_api and self.gateway.md_api.login_status:
                    self.log("行情网关已成功登录")
                    break
                self.log(f"等待行情网关登录... ({retry_count+1}/{max_retries})")
                await asyncio.sleep(1)
                retry_count += 1
            
            if retry_count >= max_retries:
                self.log("行情网关登录超时，服务启动失败", "ERROR")
                return False
        except Exception as e:
            self.log(f"等待行情网关登录过程中发生异常: {e}", "ERROR")
            import traceback
            self.log(traceback.format_exc(), "ERROR")
            return False
        
        # 订阅默认合约
        try:
            self.log("开始订阅默认合约...")
            await self.subscribe_default_symbols()
            self.log("默认合约订阅处理完成")
        except Exception as e:
            self.log(f"订阅默认合约过程中发生异常: {e}", "ERROR")
            import traceback
            self.log(traceback.format_exc(), "ERROR")
            # 不返回False，因为订阅失败不应该导致整个服务停止
        
        self.log("行情网关服务已启动完成")
        return True
    
    async def stop(self):
        """
        停止行情网关服务
        """
        if not self._running:
            return
        
        self._running = False
        self.log("行情网关服务停止中...")
        
        # 关闭网关连接
        if self.gateway:
            self.log("正在关闭行情网关连接...")
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self.gateway.close)
        
        # 停止事件引擎
        await self.event_engine.stop()
        
        self.log("行情网关服务已停止")


async def run_main(environment: Optional[str] = None):
    # ZMQ地址配置
    ZMQ_PUB_ADDRESS = "tcp://*:5556"  # 行情网关发布地址
    ZMQ_SUB_ADDRESS = "tcp://localhost:5555"  # 订阅主引擎命令的地址
    
    # 实例化ZMQ事件引擎
    zmq_event_engine = ZmqEventEngine(pub_addr=ZMQ_PUB_ADDRESS, sub_addr=ZMQ_SUB_ADDRESS, engine_id="MarketDataGatewayZMQ")
    
    # 创建行情网关服务
    market_data_service = MarketDataGatewayService(event_engine=zmq_event_engine, environment_name=environment)
    
    # 用于优雅退出的事件
    stop_event = asyncio.Event()
    
    # 信号处理
    if sys.platform != "win32":  # 类POSIX系统可以使用add_signal_handler
        loop = asyncio.get_event_loop()
        def signal_handler_posix():
            market_data_service.log("捕获到退出信号 (POSIX)，开始关闭...")
            if not stop_event.is_set():
                stop_event.set()
        
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, signal_handler_posix)
            except NotImplementedError:
                market_data_service.log(f"无法为信号 {sig} 添加处理器 (NotImplementedError)。依赖 KeyboardInterrupt。", "WARNING")
    else:  # Windows平台主要依靠KeyboardInterrupt
        market_data_service.log("Windows 平台：请使用 Ctrl+C 来触发关闭。", "INFO")
    
    try:
        # 启动服务
        start_success = await market_data_service.start()
        if not start_success:
            market_data_service.log("行情网关服务启动失败，程序退出", "ERROR")
            return
        
        # 主循环
        while not stop_event.is_set() and market_data_service._running:
            await asyncio.sleep(1)
        
        market_data_service.log("主循环结束或收到停止信号，准备执行停止操作。")
    
    except KeyboardInterrupt:
        market_data_service.log("捕获到 KeyboardInterrupt，开始关闭...")
        if not stop_event.is_set():
            stop_event.set()
    except Exception as e:
        market_data_service.log(f"行情网关服务运行出错: {e}", "CRITICAL")
        import traceback
        market_data_service.log(traceback.format_exc(), "ERROR")
    finally:
        market_data_service.log("执行最终清理...")
        await market_data_service.stop()
        market_data_service.log("所有组件已停止。程序退出。")


if __name__ == "__main__":
    args = runner_args("Broker environment name (e.g., simnow, tts from broker_config.json)")
    asyncio.run(run_main(environment=args.ctp_env)) 