#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos_v2
@FileName   : market_data_gateway.py
@Date       : 2025/6/26 21:40
@Author     : Donny
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: CTP行情网关
"""
import asyncio
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional, Any

from src.config import global_var
from src.config.constant import Exchange
from src.config.setting import get_instrument_exchange_id
from src.core.event import Event, EventType
from src.core.event_bus import EventBus
from src.core.gateway import BaseGateway
from src.core.gateway_state import LoginState, ConnectionState
from src.core.logger import get_logger
from src.core.object import TickData, SubscribeRequest, ContractData
from src.ctp.api import MdApi
from src.ctp.gateway.ctp_mapping import EXCHANGE_CTP2VT
from src.util.utility import ZoneInfo, get_folder_path


logger = get_logger("MarketDataGateway")

# 其他常量
MAX_FLOAT = sys.float_info.max             # 浮点数极限值
CHINA_TZ = ZoneInfo("Asia/Shanghai")       # 中国时区

# 合约数据全局缓存字典
symbol_contract_map: dict[str, ContractData] = {}


class MarketDataGateway(BaseGateway):
    """
    CTP行情网关 - 专门负责行情数据处理
    """
    default_setting: dict[str, str] = {
        "user_id": "",
        "password": "",
        "broker_id": "",
        "md_address": "",
        "appid": "",
        "auth_code": ""
    }

    exchanges: list[str] = [exchange.value for exchange in EXCHANGE_CTP2VT.values()]

    def __init__(self, event_bus: EventBus, gateway_name: str = "CTP_MD"):
        """
        初始化行情网关

        Args:
            event_bus: 事件总线
            gateway_name: 网关名称，默认为"CTP_MD"
        Returns:
            None
        """
        super().__init__(event_bus, gateway_name)
        self.gateway_name = gateway_name
        
        # CTP API相关
        self.md_api: CtpMdApi | None = None
        self._connection_state: ConnectionState = ConnectionState.DISCONNECTED
        self.login_state = LoginState.LOGGED_OUT
        
        # 新增：心跳监控任务初始化
        self.heartbeat_task = None
        
        # 心跳监控
        self._last_heartbeat = 0
        self._heartbeat_interval = 30  # 30秒心跳间隔
        
        # 订阅管理（增强）
        self.pending_subscriptions: set[str] = set()  # 待订阅合约
        self.active_subscriptions: set[str] = set()   # 已订阅合约
        
        # 待处理订阅请求队列
        self.pending_subscription_queue: list[dict] = []
        
        # 连接配置缓存（用于重连）
        self._last_connection_config: Optional[dict] = None
        
        # 重连相关属性
        self._enable_auto_reconnect: bool = True
        self._reconnect_task: Optional[asyncio.Task] = None
        self._current_reconnect_attempts: int = 0
        self._max_reconnect_attempts: int = 10
        self._reconnect_interval: float = 5.0
        
        # 设置网关事件处理器
        self._setup_gateway_event_handlers()

    def _is_gateway_ready(self) -> bool:
        """检查网关是否就绪"""
        # 检查连接状态和登录状态
        connection_ready = self._connection_state == ConnectionState.LOGGED_IN
        login_ready = self.login_state == LoginState.LOGGED_IN
        api_ready = (self.md_api is not None and 
                    getattr(self.md_api, 'connect_status', False) and
                    getattr(self.md_api, 'login_status', False))
        
        is_ready = connection_ready and login_ready and api_ready
        logger.debug(f"网关就绪检查: connection={connection_ready}, login={login_ready}, api={api_ready}, result={is_ready}")
        return is_ready

    @staticmethod
    def _get_symbol_exchange(symbol: str) -> Exchange:
        """根据合约代码获取交易所"""
        # 从配置文件中读取合约交易所映射关系
        instrument_exchange_json = get_instrument_exchange_id()
        return Exchange(instrument_exchange_json.get(symbol, None))

    def _queue_pending_subscription(self, strategy_id: str, symbols: list) -> None:
        """将订阅请求加入待处理队列"""
        if not hasattr(self, 'pending_subscription_queue'):
            self.pending_subscription_queue = []
        
        self.pending_subscription_queue.append({
            "strategy_id": strategy_id,
            "symbols": symbols,
            "timestamp": time.time()
        })
        logger.info(f"订阅请求已加入队列: 策略={strategy_id}, 队列长度={len(self.pending_subscription_queue)}")

    def _trigger_reconnection(self) -> None:
        """触发网关重连"""
        if self._connection_state == ConnectionState.DISCONNECTED:
            logger.info("触发行情网关重连...")
            # 这里可以实现重连逻辑
            asyncio.create_task(self._attempt_reconnection())

    async def _attempt_reconnection(self) -> None:
        """尝试重新连接"""
        try:
            max_attempts = 3
            for attempt in range(max_attempts):
                logger.info(f"尝试重连行情网关 (第{attempt + 1}次)")
                
                if self._last_connection_config:
                    self.connect(self._last_connection_config)
                    await asyncio.sleep(5)  # 等待连接建立
                    
                    if self._is_gateway_ready():
                        logger.info("行情网关重连成功")
                        await self._process_pending_subscriptions()
                        break
                else:
                    logger.error("缺少连接配置，无法重连")
                    break
                    
                await asyncio.sleep(2)  # 重试间隔
                
        except Exception as e:
            logger.error(f"重连过程中发生错误: {e}")

    async def _process_pending_subscriptions(self) -> None:
        """处理待处理的订阅请求"""
        if not hasattr(self, 'pending_subscription_queue'):
            return
            
        queue = getattr(self, 'pending_subscription_queue', [])
        if not queue:
            return
            
        logger.info(f"处理 {len(queue)} 个待处理的订阅请求")
        
        for sub_request in queue:
            try:
                # 重新发送订阅事件
                from src.core.event import Event
                event = Event(EventType.GATEWAY_SUBSCRIBE, sub_request)
                self._handle_gateway_subscribe(event)
            except Exception as e:
                logger.error(f"处理待订阅请求失败: {e}")
        
        # 清空队列
        self.pending_subscription_queue.clear()
        logger.info("待处理订阅队列已清空")
    
    def get_connection_status(self) -> dict[str, Any]:
        """获取详细连接状态"""
        return {
            "state": self._connection_state.value,
            "is_connected": self._connection_state in [ConnectionState.CONNECTED, ConnectionState.AUTHENTICATED, ConnectionState.LOGGED_IN],
            "reconnect_attempts": self._current_reconnect_attempts,
            "max_reconnect_attempts": self._max_reconnect_attempts,
            "last_heartbeat": self.last_heartbeat,
            "connection_duration": time.time() - self.connection_start_time if self.connection_start_time else 0,
            "subscriptions": self.get_subscription_status()
        }
    
    def _start_heartbeat_monitor(self) -> None:
        """启动心跳监控（线程安全版本）"""
        if self.heartbeat_task and not self.heartbeat_task.done():
            return
        
        # 使用线程安全的方式调度异步任务
        self._schedule_async_task(self._heartbeat_monitor_loop())
        logger.info("心跳监控已启动")
    
    async def _heartbeat_monitor_loop(self) -> None:
        """心跳监控循环"""
        try:
            while self._running and self._connection_state != ConnectionState.DISCONNECTED:
                await asyncio.sleep(30)  # 每30秒检查一次
                
                current_time = time.time()
                if self.last_heartbeat > 0 and current_time - self.last_heartbeat > 60:
                    # 超过60秒没有心跳，认为连接断开
                    logger.warning("心跳超时，检测到连接断开")
                    await self._handle_connection_lost()
                    
        except asyncio.CancelledError:
            logger.info("心跳监控已停止")
        except Exception as e:
            logger.error(f"心跳监控异常: {e}")
    
    async def _handle_connection_lost(self) -> None:
        """处理连接丢失"""
        try:
            logger.warning("处理连接丢失事件")
            self._connection_state = ConnectionState.DISCONNECTED
            self.last_heartbeat = 0.0

            # 清空订阅状态，等待重连后重新订阅
            self.pending_subscriptions.update(self.active_subscriptions)
            self.active_subscriptions.clear()

            # 发布连接断开事件
            self.event_bus.publish(Event(EventType.GATEWAY_DISCONNECTED, {
                "gateway_name": self.gateway_name,
                "reason": "connection_lost"
            }))

        except Exception as e:
            logger.error(f"处理连接丢失失败: {e}")
    
    def _update_connection_state(self, new_state: ConnectionState) -> None:
        """更新连接状态（线程安全版本）"""
        if self._connection_state != new_state:
            old_state = self._connection_state
            self._connection_state = new_state

            logger.info(f"连接状态变更: {old_state.value} -> {new_state.value}")

            # 使用线程安全的方式发布状态变更事件
            self._safe_publish_event(EventType.GATEWAY_STATE_CHANGED, {
                "gateway_name": self.gateway_name,
                "old_state": old_state.value,
                "new_state": new_state.value
            })

            # 记录特殊状态的时间
            if new_state == ConnectionState.CONNECTED:
                self.connection_start_time = time.time()
                self.last_heartbeat = time.time()
                # 启动心跳监控（线程安全）
                self._start_heartbeat_monitor()
            elif new_state == ConnectionState.DISCONNECTED:
                self.connection_start_time = None
                self.last_heartbeat = 0.0

    def _setup_gateway_event_handlers(self) -> None:
        """设置网关事件处理器"""
        try:
            # 订阅网关订阅/取消订阅事件
            self.event_bus.subscribe(EventType.GATEWAY_SUBSCRIBE, self._handle_gateway_subscribe)
            self.event_bus.subscribe(EventType.GATEWAY_UNSUBSCRIBE, self._handle_gateway_unsubscribe)
            self.event_bus.subscribe(EventType.GATEWAY_CONNECTED, self._on_gateway_connected)
            self.event_bus.subscribe(EventType.GATEWAY_DISCONNECTED, self._on_gateway_disconnected)
            # 订阅合约更新事件，用于同步交易网关的合约数据
            self.event_bus.subscribe(EventType.CONTRACT_UPDATED, self._handle_contract_updated)
            logger.info(f"{self.gateway_name} 网关事件处理器已注册")
        except Exception as e:
            logger.error(f"设置网关事件处理器失败: {e}")

    def _handle_gateway_subscribe(self, event: Event) -> None:
        """处理动态订阅请求 - 增强连接状态验证"""
        try:
            data = event.data
            symbols = data.get("symbols", [])
            strategy_id = data.get("strategy_id", "unknown")

            logger.info(f"网关收到订阅请求: 策略={strategy_id}, 合约={symbols}")

            # 检查网关连接状态
            if not self._is_gateway_ready():
                logger.warning(f"网关未就绪，延迟处理订阅请求: 策略={strategy_id}, 合约={symbols}")
                self._queue_pending_subscription(strategy_id, symbols)
                self._trigger_reconnection()
                return

            for symbol in symbols:
                if symbol not in self.active_subscriptions:
                    # 创建订阅请求
                    subscribe_req = SubscribeRequest(
                        symbol=symbol,
                        exchange=self._get_symbol_exchange(symbol)
                    )

                    # 添加到待订阅列表
                    self.pending_subscriptions.add(symbol)

                    # 调用订阅方法
                    self.subscribe(subscribe_req)

                    logger.info(f"已发送订阅请求: {symbol}")
                else:
                    logger.debug(f"合约 {symbol} 已在订阅列表中")

        except Exception as e:
            logger.error(f"处理订阅请求失败: {e}")

    def _handle_gateway_unsubscribe(self, event: Event) -> None:
        """处理动态取消订阅请求"""
        try:
            data = event.data
            symbols = data.get("symbols", [])
            strategy_id = data.get("strategy_id", "unknown")

            logger.info(f"网关收到取消订阅请求: 策略={strategy_id}, 合约={symbols}")

            for symbol in symbols:
                if symbol in self.active_subscriptions:
                    # 从订阅列表中移除
                    self.active_subscriptions.discard(symbol)
                    self.pending_subscriptions.discard(symbol)

                    logger.info(f"已取消订阅: {symbol}")
                else:
                    logger.debug(f"合约 {symbol} 未在订阅列表中")

        except Exception as e:
            logger.error(f"处理取消订阅请求失败: {e}")

    def _on_gateway_connected(self, event: Event) -> None:
        """处理网关连接成功事件"""
        self._update_connection_state(ConnectionState.CONNECTED)

    def _on_gateway_disconnected(self, event: Event) -> None:
        """处理网关连接断开事件"""
        self._update_connection_state(ConnectionState.DISCONNECTED)
    
    def _handle_contract_updated(self, event: Event) -> None:
        """处理合约更新事件，同步交易网关的合约数据"""
        try:
            data = event.data
            contract = data.get("contract")
            gateway_name = data.get("gateway_name", "unknown")
            
            if contract and hasattr(contract, 'symbol'):
                # 将合约数据同步到行情网关的symbol_contract_map中
                symbol_contract_map[contract.symbol] = contract
                logger.debug(f"已同步合约数据: {contract.symbol} (来自 {gateway_name})")
            else:
                logger.warning(f"收到无效的合约更新事件: {data}")
                
        except Exception as e:
            logger.error(f"处理合约更新事件失败: {e}")

    def get_subscription_status(self) -> dict:
        """获取订阅状态"""
        return {
            "active_subscriptions": list(self.active_subscriptions),
            "pending_subscriptions": list(self.pending_subscriptions),
            "total_active": len(self.active_subscriptions),
            "total_pending": len(self.pending_subscriptions)
        }

    @staticmethod
    def _prepare_address(address: str) -> str:
        """
        如果没有方案，则帮助程序会在前面添加 tcp:// 作为前缀。
        :param address:
        :return:
        """
        if not any(address.startswith(scheme) for scheme in ["tcp://", "ssl://", "socks://"]):
            return "tcp://" + address
        return address

    def connect(self, setting: dict[str, Any]) -> None:
        """连接CTP服务器"""
        try:
            logger.info("开始连接CTP行情服务器...")
            
            # 保存连接配置用于重连
            self._last_connection_config = setting.copy()
            
            # 兼容性配置字段处理
            userid = setting.get("user_id", "")
            password = setting.get("password", "")
            broker_id = setting.get("broker_id", "")
            md_address = setting.get("md_address", "")

            # 参数验证
            if not all([userid, password, broker_id, md_address]):
                raise ValueError("缺少必要的连接参数")
            
            # 创建API实例
            if not self.md_api:
                self.md_api = CtpMdApi(self)
                # 设置网关引用（如果API支持）
                try:
                    setattr(self.md_api, 'gateway', self)
                except AttributeError:
                    pass  # 如果API不支持gateway属性，忽略
            
            # 启动心跳监控
            self._start_heartbeat_monitor()

            md_address: str = self._prepare_address(setting["md_address"])
            self.md_api.connect(md_address, userid, password, broker_id)
            
            self._connection_state = ConnectionState.CONNECTING
            logger.info(f"正在连接到 {md_address}...")
            
        except Exception as e:
            logger.error(f"连接失败: {e}")
            self._connection_state = ConnectionState.DISCONNECTED
            self._handle_connection_failed(str(e))

    def _handle_connection_failed(self, reason: str) -> None:
        """处理连接失败异常"""
        try:
            logger.error(f"行情网关连接失败: {reason}")
            self._connection_state = ConnectionState.DISCONNECTED
            self.login_state = LoginState.LOGGED_OUT
            self.last_heartbeat = 0.0
            # 发布连接失败事件
            if self.event_bus:
                self.event_bus.publish(Event(EventType.GATEWAY_DISCONNECTED, {
                    "gateway_name": self.gateway_name,
                    "reason": reason
                }))
        except Exception as e:
            logger.error(f"_handle_connection_failed处理异常: {e}")

    async def _start_auto_reconnect(self) -> None:
        """启动智能自动重连"""
        if not self._enable_auto_reconnect or not self._last_connection_config:
            return
            
        if self._reconnect_task and not self._reconnect_task.done():
            return  # 重连任务已在运行
            
        self._reconnect_task = asyncio.create_task(self._auto_reconnect_loop())
    
    async def _auto_reconnect_loop(self) -> None:
        """自动重连循环"""
        try:
            while (self._current_reconnect_attempts < self._max_reconnect_attempts and 
                   self._connection_state == ConnectionState.DISCONNECTED and
                   self._enable_auto_reconnect):
                
                self._current_reconnect_attempts += 1
                wait_time = min(self._reconnect_interval * (2 ** (self._current_reconnect_attempts - 1)), 60)  # 指数退避，最大60秒
                
                logger.info(f"第 {self._current_reconnect_attempts}/{self._max_reconnect_attempts} 次重连尝试，等待 {wait_time:.1f} 秒...")
                await asyncio.sleep(wait_time)
                
                try:
                    logger.info(f"尝试自动重连 ({self._current_reconnect_attempts}/{self._max_reconnect_attempts})")
                    if self._last_connection_config:
                        self.connect(self._last_connection_config)
                    
                    # 等待连接结果（最多等待30秒）
                    for _ in range(30):
                        if self._connection_state != ConnectionState.DISCONNECTED:
                            logger.info("自动重连成功")
                            return
                        await asyncio.sleep(1)
                        
                except Exception as e:
                    logger.error(f"自动重连失败: {e}")
            
            if self._current_reconnect_attempts >= self._max_reconnect_attempts:
                logger.error(f"已达到最大重连次数 ({self._max_reconnect_attempts})，停止自动重连")
                self.event_bus.publish(Event(EventType.GATEWAY_RECONNECT_FAILED, {
                    "gateway_name": self.gateway_name,
                    "attempts": self._current_reconnect_attempts
                }))
                
        except asyncio.CancelledError:
            logger.info("自动重连任务已取消")
        except Exception as e:
            logger.error(f"自动重连循环异常: {e}")

    def subscribe(self, req: SubscribeRequest) -> None:
        """
        订阅行情
        :param req:
        :return:
        """
        if not self.md_api or not getattr(self.md_api, 'connect_status', False):
            logger.info("无法订阅行情：行情接口未连接或未初始化。")
            return
        if hasattr(self.md_api, 'subscribe'):
            self.md_api.subscribe(req)
        else:
            logger.info("行情API不支持subscribe方法")

    def close(self) -> None:
        """
        关闭接口
        :return:
        """
        if self.md_api and getattr(self.md_api, 'connect_status', False):
            if hasattr(self.md_api, 'close'):
                self.md_api.close()
            else:
                logger.warning("行情API不支持close方法")

    def process_timer_event(self) -> None:
        """
        定时事件处理
        :return:
        """
        if self.md_api:  # MdApi might not be initialized if only TD is connected
            self.md_api.update_date()

    def on_tick(self, tick: TickData) -> None:
        logger.debug(f"MarketDataGateway.on_tick: 收到tick {tick.symbol} {tick.datetime} {tick.last_price}")
        # 补充：将tick事件发布到事件总线，供DataService消费
        self.event_bus.publish(Event(EventType.MARKET_TICK_RAW, tick))
        # 调用父类的on_tick方法（如果存在）
        if hasattr(super(), 'on_tick'):
            super().on_tick(tick)


class CtpMdApi(MdApi):
    """
    CTP行情接口
    """

    def __init__(self, gateway: MarketDataGateway) -> None:
        super().__init__()

        self.gateway: MarketDataGateway = gateway  # 行情网关
        self.gateway_name: str = gateway.gateway_name  # 行情网关名称

        self.req_id: int = 0  # 请求ID

        self.connect_status: bool = False  # 连接状态
        self.login_status: bool = False  # 登录状态
        self.subscribed: set = set()  # 已订阅的合约

        self.userid: str = ""  # 用户名
        self.password: str = ""  # 密码
        self.broker_id: str = ""  # 经纪公司代码

        self.current_date: str = datetime.now().strftime("%Y%m%d")  # 当前交易日
        self.last_disconnect_time = 0  # 最后一次断开连接的时间

    def onFrontConnected(self) -> None:
        """
        服务器连接成功回报
        :return:
        """
        logger.info("CTP行情API回调: onFrontConnected - 行情服务器连接成功")
        # self.gateway._update_connection_state(ConnectionState.CONNECTED)
        # 发布事件代替直接调用 protected 方法
        self.gateway.event_bus.publish(Event(
            EventType.GATEWAY_CONNECTED,
            {"gateway_name": self.gateway.gateway_name}
        ))
        logger.info("连接状态已更新为CONNECTED，开始登录流程")
        self.login()

    def onFrontDisconnected(self, reason: int) -> None:
        """
        行情服务器连接断开回报
        当客户端与交易托管系统通信连接断开时，该方法被调用。
        当发生这个情况后，API会自动重新连接，客户端可不做处理。
        自动重连地址，可能是原来注册的地址，也可能是系统支持的其它可用的通信地址，它由程序自动选择。
        注:重连之后需要重新认证、登录
        :param reason: 错误代号，连接断开原因，为10进制值，因此需要转成16进制后再参照下列代码：
                0x1001 网络读失败
                0x1002 网络写失败
                0x2001 接收心跳超时
                0x2002 发送心跳失败
                0x2003 收到错误报文
        :return: 无
        :param reason:
        :return:
        """
        logger.warning(f"CTP行情API回调: onFrontDisconnected - 连接断开，原因代码={reason}")
        self.login_status = False
        # self.gateway._update_connection_state(ConnectionState.DISCONNECTED)
        # 发布事件代替直接调用 protected 方法
        self.gateway.event_bus.publish(Event(
            EventType.GATEWAY_DISCONNECTED,
            {"gateway_name": self.gateway.gateway_name}
        ))

        # 解析断开原因
        reason_hex = hex(reason)
        reason_msg = {
            0x1001: "网络读失败",
            0x1002: "网络写失败", 
            0x2001: "接收心跳超时",
            0x2002: "发送心跳失败",
            0x2003: "收到错误报文"
        }.get(reason, f"未知原因({reason_hex})")
        
        logger.info(f"行情服务器连接断开，原因：{reason_msg} ({reason_hex})")
        
        # 触发连接丢失处理
        asyncio.create_task(self.gateway._handle_connection_lost())
        
        # 启动智能重连机制
        if hasattr(self.gateway, '_enable_auto_reconnect') and self.gateway._enable_auto_reconnect:
            asyncio.create_task(self.gateway._start_auto_reconnect())

    def onRspUserLogin(self, data: dict, error: dict, reqid: int, last: bool) -> None:
        """
        用户登录请求回报
        :param data:
        :param error:
        :param reqid:
        :param last:
        :return:
        """
        logger.info(f"CTP行情API回调: onRspUserLogin - 登录回报, ErrorID={error.get('ErrorID', 'N/A')}")
        if not error["ErrorID"]:
            logger.info("行情服务器登录成功，开始更新状态并处理pending订阅")
            self.login_status = True
            global_var.md_login_success = True
            self.gateway._update_connection_state(ConnectionState.LOGGED_IN)
            self.gateway.login_state = LoginState.LOGGED_IN
            logger.info("行情服务器登录成功")
            
            # 更新心跳时间
            self.gateway.last_heartbeat = time.time()

            for symbol in self.subscribed:
                self.subscribeMarketData(symbol)

            # 登录成功后自动处理pending订阅队列
            try:
                logger.info("🚀 登录成功，开始处理pending订阅队列")
                if hasattr(self.gateway, '_process_pending_subscriptions'):
                    # 使用线程安全的方式调度异步任务
                    coro = self.gateway._process_pending_subscriptions()
                    if asyncio.iscoroutine(coro):
                        self.gateway._schedule_async_task(coro)
                    else:
                        # 同步直接调用
                        pass
                logger.info("pending订阅队列处理任务已创建")
                logger.info("登录成功后已触发pending订阅队列处理")
            except Exception as e:
                logger.error(f"处理pending订阅队列异常: {e}")
        else:
            logger.error(f"行情服务器登录失败: {error}")
            self.gateway._update_connection_state(ConnectionState.ERROR)
            self.gateway.login_state = LoginState.LOGIN_FAILED
            self.gateway.write_error("行情服务器登录失败", error)

    def onRspError(self, error: dict, reqid: int, last: bool) -> None:
        """
        请求报错回报
        :param error:
        :param reqid:
        :param last:
        :return:
        """
        logger.error(f"CTP行情API回调: onRspError - 请求报错, ErrorID={error.get('ErrorID', 'N/A')}, ErrorMsg={error.get('ErrorMsg', 'N/A')}")
        self.gateway.write_error("行情接口报错", error)

    def onRspSubMarketData(self, data: dict, error: dict, reqid: int, last: bool) -> None:
        """
        订阅行情回报
        :param data:
        :param error:
        :param reqid:
        :param last:
        :return:
        """
        symbol = data.get("InstrumentID", "UNKNOWN") if data else "UNKNOWN"
        logger.info(f"CTP行情API回调: onRspSubMarketData - 订阅回报, 合约={symbol}, ErrorID={error.get('ErrorID', 'N/A') if error else 'None'}")
        if not error or not error["ErrorID"]:
            # 订阅成功
            if data and "InstrumentID" in data:
                symbol = data["InstrumentID"]
                # 更新网关订阅状态
                if symbol in self.gateway.pending_subscriptions:
                    self.gateway.pending_subscriptions.discard(symbol)
                    self.gateway.active_subscriptions.add(symbol)
                    logger.info(f"行情订阅成功并更新状态: {symbol}")

                    # 发布订阅成功事件，通知DataService更新状态
                    from src.core.event import create_trading_event, EventType
                    success_event = create_trading_event(
                        EventType.GATEWAY_SUBSCRIPTION_SUCCESS,
                        {
                            "symbol": symbol,
                            "gateway_name": self.gateway.gateway_name,
                            "timestamp": time.time()
                        },
                        source="MarketDataGateway"
                    )
                    self.gateway.event_bus.publish(success_event)
                    logger.info(f"📢 已发布订阅成功事件: {symbol}")
                else:
                    logger.warning(f"订阅成功但合约不在pending列表: {symbol}")
            return

        logger.error(f"行情订阅失败: {error}")
        self.gateway.write_error("行情订阅失败", error)

    def onRtnDepthMarketData(self, data: dict) -> None:
        """
        行情数据推送
        :param data:
        :return:
        """
        """行情数据推送"""
        # 更新心跳时间
        self.gateway.last_heartbeat = time.time()
        
        # 获取合约代码用于日志记录
        symbol: str = data.get("InstrumentID", "UNKNOWN")
        
        # 增强日志记录 - 记录所有接收到的行情数据
        logger.debug(f"CTP行情数据接收: {symbol} @ {data.get('UpdateTime', 'N/A')} 价格={data.get('LastPrice', 'N/A')}")
        
        # 过滤没有时间戳的异常行情数据
        if not data["UpdateTime"]:
            logger.warning(f"跳过无时间戳的行情数据: {symbol}")
            return

        # 过滤还没有收到合约数据前的行情推送
        contract: Optional[ContractData] = symbol_contract_map.get(symbol, None)
        if not contract:
            logger.warning(f"跳过行情推送，合约信息不存在: {symbol} (symbol_contract_map中共有{len(symbol_contract_map)}个合约)")
            return

        # 对大商所的交易日字段取本地日期
        if not data["ActionDay"] or contract.exchange == Exchange.DCE:
            date_str: str = self.current_date
        else:
            date_str = data["ActionDay"]

        timestamp: str = f"{date_str} {data['UpdateTime']}.{data['UpdateMillisec']}"
        dt_format_obj: datetime = datetime.strptime(timestamp, "%Y%m%d %H:%M:%S.%f")
        dt_obj: datetime = dt_format_obj.replace(tzinfo=CHINA_TZ)

        tick: TickData = TickData(
            symbol=symbol,
            exchange=contract.exchange,
            datetime=dt_obj,
            name=contract.name,
            volume=data["Volume"],
            turnover=data["Turnover"],
            open_interest=data["OpenInterest"],
            last_price=adjust_price(data["LastPrice"]),
            limit_up=data["UpperLimitPrice"],
            limit_down=data["LowerLimitPrice"],
            open_price=adjust_price(data["OpenPrice"]),
            high_price=adjust_price(data["HighestPrice"]),
            low_price=adjust_price(data["LowestPrice"]),
            pre_close=adjust_price(data["PreClosePrice"]),
            bid_price_1=adjust_price(data["BidPrice1"]),
            ask_price_1=adjust_price(data["AskPrice1"]),
            bid_volume_1=data["BidVolume1"],
            ask_volume_1=data["AskVolume1"],
            gateway_name=self.gateway_name
        )

        if data["BidVolume2"] or data["AskVolume2"]:
            tick.bid_price_2 = adjust_price(data["BidPrice2"])
            tick.bid_price_3 = adjust_price(data["BidPrice3"])
            tick.bid_price_4 = adjust_price(data["BidPrice4"])
            tick.bid_price_5 = adjust_price(data["BidPrice5"])

            tick.ask_price_2 = adjust_price(data["AskPrice2"])
            tick.ask_price_3 = adjust_price(data["AskPrice3"])
            tick.ask_price_4 = adjust_price(data["AskPrice4"])
            tick.ask_price_5 = adjust_price(data["AskPrice5"])

            tick.bid_volume_2 = data["BidVolume2"]
            tick.bid_volume_3 = data["BidVolume3"]
            tick.bid_volume_4 = data["BidVolume4"]
            tick.bid_volume_5 = data["BidVolume5"]

            tick.ask_volume_2 = data["AskVolume2"]
            tick.ask_volume_3 = data["AskVolume3"]
            tick.ask_volume_4 = data["AskVolume4"]
            tick.ask_volume_5 = data["AskVolume5"]

        self.gateway.on_tick(tick)
        # 关键日志：确保行情数据被推送到网关
        logger.info(f"行情数据已推送到网关: {tick.symbol} @ {tick.last_price}")
        logger.debug(f"CtpMdApi.onRtnDepthMarketData: 推送tick {tick.symbol} {tick.datetime} {tick.last_price}")

    def onRspUserLogout(self, data: dict, error: dict, reqid: int, last: bool):
        """
        登出请求响应，当 ReqUserLogout 后，该方法被调用。
        :param data: 用户登出请求
        :param error: 响应信息
        :param reqid: 返回用户操作请求的 ID，该 ID 由用户在操作请求时指定。
        :param last: 指示该次返回是否为针对 reqid 的最后一次返回。
        :return: 无
        """
        logger.info("行情账户：{} 已登出".format(data['UserID']))

    def connect(self, address: str, userid: str, password: str, brokerid: str) -> None:
        """
        连接服务器
        :param address:
        :param userid:
        :param password:
        :param brokerid:
        :return:
        """
        self.userid = userid
        self.password = password
        self.broker_id = brokerid

        # 禁止重复发起连接，会导致异常崩溃
        if not self.connect_status:
            path: Path = get_folder_path(self.gateway_name.lower())
            api_path_str = str(path) + "\\md"
            logger.info("CtpMdApi：尝试创建路径为 {} 的 API".format(api_path_str))
            try:
                self.createFtdcMdApi(api_path_str.encode("GBK").decode("utf-8"))  # 加上utf-8编码，否则中文路径会乱码
                logger.info("CtpMdApi：createFtdcMdApi调用成功。")
            except Exception as e_create:
                logger.error("CtpMdApi：createFtdcMdApi 失败！错误：{}".format(e_create))
                logger.error("CtpMdApi：createFtdcMdApi 回溯：{}".format(traceback.format_exc()))
                return

            self.registerFront(address)
            logger.info("CtpMdApi：尝试使用地址初始化 API：{}...".format(address))
            try:
                self.init()
                logger.info("CtpMdApi：init 调用成功。")
            except Exception as e_init:
                logger.error("CtpMdApi：初始化失败！错误：{}".format(e_init))
                logger.error("CtpMdApi：初始化回溯：{}".format(traceback.format_exc()))
                return

            self.connect_status = True

    def login(self) -> None:
        """
        用户登录
        :return:
        """
        ctp_req: dict = {
            "UserID": self.userid,
            "Password": self.password,
            "BrokerID": self.broker_id
        }

        self.req_id += 1
        self.reqUserLogin(ctp_req, self.req_id)

    def subscribe(self, req: SubscribeRequest) -> None:
        """
        订阅行情
        :param req:
        :return:
        """
        symbol: str = req.symbol
        logger.info(f"🔔 CTP行情API: 准备订阅合约 {symbol}")

        # 过滤重复的订阅
        if symbol in self.subscribed:
            logger.warning(f"⚠️ 合约 {symbol} 已在订阅列表中，跳过重复订阅")
            return

        if self.login_status:
            logger.info(f"📡 CTP行情API: 发送订阅请求 {symbol}")
            result = self.subscribeMarketData(req.symbol)
            logger.info(f"📤 CTP行情API: 订阅请求已发送 {symbol}, 返回值={result}")
        else:
            logger.warning(f"⚠️ CTP行情API: 未登录，无法订阅 {symbol}")
        self.subscribed.add(req.symbol)

    def close(self) -> None:
        """
        关闭连接
        :return:
        """
        if self.connect_status:
            self.exit()

    def update_date(self) -> None:
        """
        更新当前日期
        :return:
        """
        self.current_date = datetime.now().strftime("%Y%m%d")


def adjust_price(price: float) -> float:
    """将异常的浮点数最大值（MAX_FLOAT）数据调整为0"""
    if price == MAX_FLOAT:
        price = 0
    return price