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
from datetime import datetime
from pathlib import Path
from typing import Optional, Any
from enum import Enum
import time

from src.config import global_var
from src.config.constant import Exchange
from src.core.event_bus import EventBus
from src.core.gateway import BaseGateway
from src.core.object import TickData, SubscribeRequest, ContractData
from src.ctp.api import MdApi
from src.ctp.gateway.ctp_mapping import EXCHANGE_CTP2VT
from src.util.utility import ZoneInfo, get_folder_path
from src.core.logger import get_logger
from src.core.event import Event
logger = get_logger("MarketDataGateway")

# 其他常量
MAX_FLOAT = sys.float_info.max             # 浮点数极限值
CHINA_TZ = ZoneInfo("Asia/Shanghai")       # 中国时区

# 合约数据全局缓存字典
symbol_contract_map: dict[str, ContractData] = {}


class ConnectionState(Enum):
    """连接状态枚举"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    AUTHENTICATED = "authenticated"
    LOGGED_IN = "logged_in"
    ERROR = "error"


class MarketDataGateway(BaseGateway):
    """
    CTP行情网关 - 专门负责行情数据处理
    """
    default_name: str = "CTP_MD"

    default_setting: dict[str, str] = {
        "userid": "",
        "password": "",
        "broker_id": "",
        "md_address": "",
        "appid": "",
        "auth_code": ""
    }

    exchanges: list[str] = list(EXCHANGE_CTP2VT.values())

    def __init__(self, event_bus: EventBus, name: str) -> None:
        """CTP行情网关构造函数

        Args:
            event_bus: 事件引擎实例
            name: 名称
        """
        super().__init__(event_bus, name)
        self.event_bus: EventBus = event_bus  # Ensure this line is present
        self.query_functions = None
        # 行情API实例
        self.md_api: CtpMdApi | None = None
        self.count: int = 0

        # 基础属性
        self.instrument_exchange_map: dict[str, str] = {}
        self.setting: dict = {}

        # 连接状态管理
        self._running: bool = True
        self.heartbeat_task: Optional[asyncio.Task] = None
        
        # 连接状态管理增强
        self.connection_state: ConnectionState = ConnectionState.DISCONNECTED
        self.reconnect_attempts: int = 0
        self.max_reconnect_attempts: int = 10
        self.last_heartbeat: float = 0.0
        self.connection_start_time: Optional[float] = None
        
        # 自动重连配置
        self._enable_auto_reconnect: bool = True
        self._reconnect_interval: float = 5.0  # 重连间隔（秒）
        self._max_reconnect_attempts: int = 10  # 最大重连次数
        self._current_reconnect_attempts: int = 0
        self._reconnect_task: Optional[asyncio.Task] = None
        self._last_connection_config: Optional[dict] = None
        
        # 订阅状态管理
        self.pending_subscriptions: set[str] = set()  # 待订阅合约
        self.active_subscriptions: set[str] = set()   # 已订阅合约
        
        # 设置网关事件处理器
        self._setup_gateway_event_handlers()
    
    def get_connection_status(self) -> dict[str, Any]:
        """获取详细连接状态"""
        return {
            "state": self.connection_state.value,
            "is_connected": self.connection_state in [ConnectionState.CONNECTED, ConnectionState.AUTHENTICATED, ConnectionState.LOGGED_IN],
            "reconnect_attempts": self.reconnect_attempts,
            "max_reconnect_attempts": self.max_reconnect_attempts,
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
            while self._running and self.connection_state != ConnectionState.DISCONNECTED:
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
            self.connection_state = ConnectionState.DISCONNECTED
            self.last_heartbeat = 0.0
            
            # 清空订阅状态，等待重连后重新订阅
            self.pending_subscriptions.update(self.active_subscriptions)
            self.active_subscriptions.clear()
            
            # 发布连接断开事件
            self.event_bus.publish(Event("gateway.disconnected", {
                "gateway_name": self.name,
                "reason": "connection_lost"
            }))
            
        except Exception as e:
            logger.error(f"处理连接丢失失败: {e}")
    
    def _update_connection_state(self, new_state: ConnectionState) -> None:
        """更新连接状态（线程安全版本）"""
        if self.connection_state != new_state:
            old_state = self.connection_state
            self.connection_state = new_state

            logger.info(f"连接状态变更: {old_state.value} -> {new_state.value}")

            # 使用线程安全的方式发布状态变更事件
            self._safe_publish_event("gateway.state_changed", {
                "gateway_name": self.name,
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
            self.event_bus.subscribe("gateway.subscribe", self._handle_gateway_subscribe)
            self.event_bus.subscribe("gateway.unsubscribe", self._handle_gateway_unsubscribe)
            logger.info(f"{self.name} 网关事件处理器已注册")
        except Exception as e:
            logger.error(f"设置网关事件处理器失败: {e}")

    def _handle_gateway_subscribe(self, event: Event) -> None:
        """处理动态订阅请求"""
        try:
            data = event.data
            symbols = data.get("symbols", [])
            strategy_id = data.get("strategy_id", "unknown")

            logger.info(f"网关收到订阅请求: 策略={strategy_id}, 合约={symbols}")

            for symbol in symbols:
                if symbol not in self.active_subscriptions:
                    # 创建订阅请求
                    subscribe_req = SubscribeRequest(
                        symbol=symbol,
                        exchange=Exchange.CZCE  # 默认交易所，实际应根据合约解析
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

    def connect(self, setting: dict) -> None:
        """
        连接行情服务器
        :param setting:
        :return:
        """
        if not self.md_api:
            self.md_api = CtpMdApi(self)

        # 兼容性配置字段处理 - 支持userid和user_id两种字段名
        userid: str = setting.get("userid", setting.get("user_id", ""))
        password: str = setting.get("password", "")
        broker_id: str = setting.get("broker_id", "")
        md_address: str = self._prepare_address(setting.get("md_address", ""))
        
        # 验证必需字段
        if not all([userid, password, broker_id, md_address]):
            missing_fields = []
            if not userid: missing_fields.append("userid/user_id")
            if not password: missing_fields.append("password") 
            if not broker_id: missing_fields.append("broker_id")
            if not md_address: missing_fields.append("md_address")
            raise ValueError(f"CTP行情网关连接参数不完整，缺少字段: {missing_fields}")

        # 保存连接配置以供重连使用
        self._last_connection_config = setting.copy()
        
        # 重置重连计数器
        self._current_reconnect_attempts = 0

        self.md_api.connect(md_address, userid, password, broker_id)
    
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
                   self.connection_state == ConnectionState.DISCONNECTED and
                   self._enable_auto_reconnect):
                
                self._current_reconnect_attempts += 1
                wait_time = min(self._reconnect_interval * (2 ** (self._current_reconnect_attempts - 1)), 60)  # 指数退避，最大60秒
                
                logger.info(f"第 {self._current_reconnect_attempts}/{self._max_reconnect_attempts} 次重连尝试，等待 {wait_time:.1f} 秒...")
                await asyncio.sleep(wait_time)
                
                try:
                    self.write_log(f"尝试自动重连 ({self._current_reconnect_attempts}/{self._max_reconnect_attempts})")
                    self.connect(self._last_connection_config)
                    
                    # 等待连接结果（最多等待30秒）
                    for _ in range(30):
                        if self.connection_state != ConnectionState.DISCONNECTED:
                            logger.info("自动重连成功")
                            return
                        await asyncio.sleep(1)
                        
                except Exception as e:
                    logger.error(f"自动重连失败: {e}")
            
            if self._current_reconnect_attempts >= self._max_reconnect_attempts:
                logger.error(f"已达到最大重连次数 ({self._max_reconnect_attempts})，停止自动重连")
                self.event_bus.publish(Event("gateway.reconnect_failed", {
                    "gateway_name": self.name,
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
        if not self.md_api or not self.md_api.connect_status:
            self.write_log("无法订阅行情：行情接口未连接或未初始化。")
            return
        self.md_api.subscribe(req)


    def close(self) -> None:
        """
        关闭接口
        :return:
        """
        if self.md_api and self.md_api.connect_status:
            self.md_api.close()

    def write_error(self, msg: str, error: dict) -> None:
        """
        输出错误信息日志
        :param msg:
        :param error:
        :return:
        """
        error_id = error.get("ErrorID", "N/A")
        error_msg = error.get("ErrorMsg", str(error))
        log_msg = f"{msg}，{'代码'}：{error_id}，{'信息'}：{error_msg}"
        self.write_log(log_msg)

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
        self.event_bus.publish(Event("market.tick.raw", tick))
        super().on_tick(tick)


class CtpMdApi(MdApi):
    """
    CTP行情接口
    """

    def __init__(self, gateway: MarketDataGateway) -> None:
        super().__init__()

        self.gateway: MarketDataGateway = gateway
        self.gateway_name: str = gateway.name

        self.req_id: int = 0

        self.connect_status: bool = False
        self.login_status: bool = False
        self.subscribed: set = set()

        self.userid: str = ""
        self.password: str = ""
        self.broker_id: str = ""

        self.current_date: str = datetime.now().strftime("%Y%m%d")
        self.last_disconnect_time = 0

    def onFrontConnected(self) -> None:
        """
        服务器连接成功回报
        :return:
        """
        self.gateway.write_log("行情服务器连接成功")
        self.gateway._update_connection_state(ConnectionState.CONNECTED)
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
        self.login_status = False
        self.gateway._update_connection_state(ConnectionState.DISCONNECTED)
        
        # 解析断开原因
        reason_hex = hex(reason)
        reason_msg = {
            0x1001: "网络读失败",
            0x1002: "网络写失败", 
            0x2001: "接收心跳超时",
            0x2002: "发送心跳失败",
            0x2003: "收到错误报文"
        }.get(reason, f"未知原因({reason_hex})")
        
        self.gateway.write_log(f"行情服务器连接断开，原因：{reason_msg} ({reason_hex})")
        
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
        if not error["ErrorID"]:
            self.login_status = True
            global_var.md_login_success = True
            self.gateway._update_connection_state(ConnectionState.LOGGED_IN)
            self.gateway.write_log("行情服务器登录成功")
            
            # 更新心跳时间
            self.gateway.last_heartbeat = time.time()

            for symbol in self.subscribed:
                self.subscribeMarketData(symbol)
        else:
            self.gateway._update_connection_state(ConnectionState.ERROR)
            self.gateway.write_error("行情服务器登录失败", error)

    def onRspError(self, error: dict, reqid: int, last: bool) -> None:
        """
        请求报错回报
        :param error:
        :param reqid:
        :param last:
        :return:
        """
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
        if not error or not error["ErrorID"]:
            # 订阅成功
            if data and "InstrumentID" in data:
                symbol = data["InstrumentID"]
                # 更新网关订阅状态
                if symbol in self.gateway.pending_subscriptions:
                    self.gateway.pending_subscriptions.discard(symbol)
                    self.gateway.active_subscriptions.add(symbol)
                    self.gateway.write_log(f"行情订阅成功: {symbol}")
            return

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
        
        # 过滤没有时间戳的异常行情数据
        if not data["UpdateTime"]:
            return

        # 过滤还没有收到合约数据前的行情推送
        symbol: str = data["InstrumentID"]
        contract: ContractData = symbol_contract_map.get(symbol, None)
        if not contract:
            return

        # 对大商所的交易日字段取本地日期
        if not data["ActionDay"] or contract.exchange == Exchange.DCE:
            date_str: str = self.current_date
        else:
            date_str = data["ActionDay"]

        timestamp: str = f"{date_str} {data['UpdateTime']}.{data['UpdateMillisec']}"
        dt: datetime = datetime.strptime(timestamp, "%Y%m%d %H:%M:%S.%f")
        dt: datetime = dt.replace(tzinfo=CHINA_TZ)

        tick: TickData = TickData(
            symbol=symbol,
            exchange=contract.exchange,
            datetime=dt,
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
        self.gateway.write_log("行情账户：{} 已登出".format(data['UserID']))

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
            self.createFtdcMdApi((str(path) + "\\md").encode("GBK").decode("utf-8"))  # 加上utf-8编码，否则中文路径会乱码

            self.registerFront(address)
            self.init()

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

        # 过滤重复的订阅
        if symbol in self.subscribed:
            return

        if self.login_status:
            self.subscribeMarketData(req.symbol)
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