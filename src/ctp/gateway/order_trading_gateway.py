#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos_v2
@FileName   : order_trading_gateway.py
@Date       : 2025/6/26 21:41
@Author     : Donny
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: CTP订单交易网关
"""
import json
import os
import sys
import threading
import time
import traceback
from datetime import datetime
from pathlib import Path
from time import sleep
from typing import Dict, Any, Optional

from src.config import global_var
from src.config.constant import Status, Exchange, Direction, OrderType
from src.config.global_var import product_info, instrument_exchange_id_map
from src.config.path import GlobalPath
from src.core.event import Event, EventType
from src.core.gateway import BaseGateway
from src.core.object import ContractData, PositionData, OrderData, AccountData, TradeData, OrderRequest, CancelRequest
from src.ctp.api import TdApi, THOST_FTDC_HF_Speculation, THOST_FTDC_CC_Immediately, THOST_FTDC_FCC_NotForceClose, \
    THOST_FTDC_AF_Delete
from src.util.utility import ZoneInfo, get_folder_path, del_num
from .ctp_gateway_helper import ctp_build_contract
from .ctp_mapping import STATUS_CTP2VT, DIRECTION_VT2CTP, DIRECTION_CTP2VT, ORDERTYPE_VT2CTP, ORDERTYPE_CTP2VT, \
    OFFSET_VT2CTP, OFFSET_CTP2VT, EXCHANGE_CTP2VT
from ...core.event_bus import EventBus
from ...core.gateway_state import ConnectionState, LoginState
from ...core.logger import get_logger
from ...util.file_helper import write_json_file

logger = get_logger("OrderTradingGateway")

# 其他常量
MAX_FLOAT = sys.float_info.max
CHINA_TZ = ZoneInfo("Asia/Shanghai")

# 合约数据全局缓存字典
symbol_contract_map: dict[str, ContractData] = {}


class OrderTradingGateway(BaseGateway):
    """
    用于对接期货CTP柜台的交易接口。
    """
    default_setting: dict[str, str] = {
        "userid": "",
        "password": "",
        "broker_id": "",
        "td_address": "",
        "md_address": "",
        "appid": "",
        "auth_code": ""
    }

    exchanges: list[str] = list(EXCHANGE_CTP2VT.values())

    def __init__(self,  event_bus: EventBus, gateway_name: str = "CTP_TD") -> None:
        """
        初始化CTP交易网关。

        Args:
            event_bus (EventBus): 事件总线对象。
            gateway_name (str, optional): 网关名称，默认为 "CTP_TD"。
        Returns:
            None
        """
        super().__init__(event_bus, gateway_name)
        self.gateway_name = gateway_name

        self.query_functions = None
        # CTP API相关
        # self.td_api: Optional[CtpTdApi] = None
        self.td_api: CtpTdApi | None = None
        self.count: int = 0
        
        # 网关状态管理
        self._gateway_state: ConnectionState = ConnectionState.DISCONNECTED
        self._contract_query_timeout: int = 60  # 合约查询超时时间(秒)
        self._state_lock = threading.Lock()  # 状态变更锁（改为同步锁）
        
        # 数据缓存 - 用于合约信息未就绪时的数据暂存
        self._pending_orders: list[Dict[str, Any]] = []
        self._pending_trades: list[Dict[str, Any]] = []
        
        # 合约就绪标志
        self._contracts_ready: bool = False
        self.contract_query_start_time: Optional[float] = None

        # 加载合约交易所映射文件
        self.instrument_exchange_map: dict = {}
        map_file_path = ""
        try:
            # current_dir = os.path.dirname(os.path.abspath(__file__))
            # 构建到 instrument_exchange_id.json 的相对路径
            # map_file_path = os.path.join(current_dir, "..", "..", "..", "config", instrument_exchange_id_filename)
            map_file_path = GlobalPath.instrument_exchange_id_filepath
            map_file_path = os.path.normpath(map_file_path) # 规范化路径

            if os.path.exists(map_file_path):
                with open(map_file_path, "r", encoding="utf-8") as f:
                    self.instrument_exchange_map = json.load(f)
                self.write_log(f"成功从 {map_file_path} 加载合约交易所映射。")
            else:
                self.write_log(f"警告：合约交易所映射文件未找到于 {map_file_path}。回退逻辑可能受限。")
        except Exception as e:
            self.write_log(f"加载合约交易所映射文件 {map_file_path} 时出错: {e}")
            
        # 设置网关事件处理器
        self._setup_gateway_event_handlers()

    def set_gateway_state(self, new_state: ConnectionState) -> None:
        """设置网关状态（线程安全，同步版本）"""
        with self._state_lock:
            old_state = self._gateway_state
            self._gateway_state = new_state
            
            # 获取当前线程信息
            current_thread = threading.current_thread()
            thread_info = f"[线程:{current_thread.name}]"
            
            # 发布状态变更事件（线程安全）
            self._safe_publish_event(EventType.GATEWAY_STATE_CHANGED, {
                "gateway_name": self.gateway_name,
                "old_state": old_state.value,
                "new_state": new_state.value,
                "timestamp": time.time(),
                "thread_name": current_thread.name
            })
            
            self.write_log(f"网关状态变更: {old_state.value} -> {new_state.value} {thread_info}")

    def _get_gateway_state(self) -> ConnectionState:
        """获取当前网关状态"""
        return self._gateway_state

    def is_contracts_ready(self) -> bool:
        """检查合约信息是否就绪"""
        return self._contracts_ready and len(symbol_contract_map) > 0

    def add_pending_order_data(self, order_data: Dict[str, Any]) -> None:
        """添加待处理的订单数据"""
        self._pending_orders.append({
            "data": order_data,
            "timestamp": time.time(),
            "type": "order"
        })
        self.write_log(f"订单数据已缓存，等待合约信息就绪。缓存数量: {len(self._pending_orders)}")

    def add_pending_trade_data(self, trade_data: Dict[str, Any]) -> None:
        """添加待处理的成交数据"""
        self._pending_trades.append({
            "data": trade_data,
            "timestamp": time.time(),
            "type": "trade"
        })
        self.write_log(f"成交数据已缓存，等待合约信息就绪。缓存数量: {len(self._pending_trades)}")

    def process_pending_data(self) -> None:
        """处理所有待处理的数据"""
        try:
            # 处理待处理的订单数据
            for pending_item in self._pending_orders:
                try:
                    self.td_api.onRtnOrder(pending_item["data"])
                except Exception as e:
                    self.write_log(f"处理缓存订单数据失败: {e}")
            
            # 处理待处理的成交数据
            for pending_item in self._pending_trades:
                try:
                    self.td_api.onRtnTrade(pending_item["data"])
                except Exception as e:
                    self.write_log(f"处理缓存成交数据失败: {e}")
            
            processed_orders = len(self._pending_orders)
            processed_trades = len(self._pending_trades)
            
            # 清空缓存
            self._pending_orders.clear()
            self._pending_trades.clear()
            
            if processed_orders > 0 or processed_trades > 0:
                self.write_log(f"已处理缓存数据: {processed_orders}个订单, {processed_trades}个成交")
                
        except Exception as e:
            self.write_log(f"处理缓存数据时发生错误: {e}")
    
    def _setup_gateway_event_handlers(self) -> None:
        """设置网关事件处理器"""
        try:
            # 订阅交易相关事件
            self.event_bus.subscribe("gateway.order", self._handle_gateway_order)
            self.event_bus.subscribe("gateway.send_order", self._handle_gateway_send_order)
            self.event_bus.subscribe("gateway.cancel", self._handle_gateway_cancel)
            
            # 订阅查询相关事件
            self.event_bus.subscribe("gateway.query_account", self._handle_query_account)
            self.event_bus.subscribe("gateway.query_position", self._handle_query_position)
            
            logger.info(f"{self.gateway_name} 交易网关事件处理器已注册")
        except Exception as e:
            try:
                logger.error(f"设置交易网关事件处理器失败: {e}")
            except Exception as e2:
                self.write_log(f"设置交易网关事件处理器失败: {e2}")
    
    def _handle_gateway_order(self, event: Event) -> None:
        """处理下单请求"""
        try:
            data = event.data
            order_request = data.get("order_request")
            strategy_id = data.get("strategy_id", "unknown")
            
            if order_request:
                self.write_log(f"交易网关收到下单请求: 策略={strategy_id}")
                order_id = self.send_order(order_request)
                self.write_log(f"下单请求已发送: {order_id}")
            else:
                self.write_log("下单请求数据无效")
                
        except Exception as e:
            self.write_log(f"处理下单请求失败: {e}")
    
    def _handle_gateway_cancel(self, event: Event) -> None:
        """处理撤单请求"""
        try:
            data = event.data
            cancel_request = data.get("cancel_request")
            strategy_id = data.get("strategy_id", "unknown")
            
            if cancel_request:
                self.write_log(f"交易网关收到撤单请求: 策略={strategy_id}")
                self.cancel_order(cancel_request)
                self.write_log(f"撤单请求已发送")
            else:
                self.write_log("撤单请求数据无效")
                
        except Exception as e:
            self.write_log(f"处理撤单请求失败: {e}")

    def _handle_gateway_send_order(self, event: Event) -> None:
        """处理网关下单请求（增强版本，包含合约就绪检查）"""
        try:
            data = event.data
            order_request = data.get("order_request")
            order_data = data.get("order_data")
            
            if not order_request or not order_data:
                self.write_log("下单请求数据不完整")
                return
            
            # 检查网关状态和合约信息就绪状态
            if self._gateway_state != ConnectionState.READY:
                self.write_log(f"网关状态未就绪: {self._gateway_state.value}，拒绝下单请求")
                self._safe_publish_event("order.send_failed", {
                    "order_request": order_request,
                    "order_data": order_data,
                    "reason": f"网关状态未就绪: {self._gateway_state.value}"
                })
                return
            
            # 检查合约信息是否就绪
            if not self.is_contracts_ready():
                self.write_log("合约信息未就绪，拒绝下单请求")
                self._safe_publish_event("order.send_failed", {
                    "order_request": order_request,
                    "order_data": order_data,
                    "reason": "合约信息未就绪"
                })
                return
            
            # 检查具体合约是否存在
            symbol = order_request.symbol
            if symbol not in symbol_contract_map:
                self.write_log(f"合约 {symbol} 不存在于合约映射中，拒绝下单请求")
                self._safe_publish_event("order.send_failed", {
                    "order_request": order_request,
                    "order_data": order_data,
                    "reason": f"合约 {symbol} 不存在"
                })
                return
            
            self.write_log(f"CTP网关收到下单请求: {order_request.symbol} {order_request.direction} {order_request.volume}@{order_request.price}")
            
            # 发送订单到CTP
            if self.td_api:
                order_id = self.td_api.send_order(order_request)
                
                if order_id:
                    self.write_log(f"订单已发送到CTP: {order_id}")
                    # 使用线程安全的方式发布订单已发送到CTP的事件
                    self._safe_publish_event("order.sent_to_ctp", {
                        "order_id": order_id,
                        "order_request": order_request,
                        "order_data": order_data
                    })
                else:
                    self.write_log("订单发送失败")
                    # 使用线程安全的方式发布订单发送失败事件
                    self._safe_publish_event("order.send_failed", {
                        "order_request": order_request,
                        "order_data": order_data,
                        "reason": "CTP send_order返回空"
                    })
            else:
                self.write_log("CTP API未初始化")
                self._safe_publish_event("order.send_failed", {
                    "order_request": order_request,
                    "order_data": order_data,
                    "reason": "CTP API未初始化"
                })
                
        except Exception as e:
            self.write_log(f"处理下单请求失败: {e}")
            # 使用线程安全的方式发布订单发送失败事件
            self._safe_publish_event("order.send_failed", {
                "reason": f"异常: {e}"
            })

    def _handle_query_account(self) -> None:
        """处理账户查询请求"""
        try:
            self.write_log("收到账户查询请求")
            self.query_account()
        except Exception as e:
            self.write_log(f"处理账户查询请求失败: {e}")
    
    def _handle_query_position(self) -> None:
        """处理持仓查询请求"""
        try:
            self.write_log("收到持仓查询请求")
            self.query_position()
        except Exception as e:
            self.write_log(f"处理持仓查询请求失败: {e}")


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
        连接交易服务器
        :param setting:
        :return:
        """
        if not self.td_api:
            self.td_api = CtpTdApi(self)

        # 兼容性配置字段处理 - 支持userid和user_id两种字段名
        userid: str = setting.get("userid", setting.get("user_id", ""))  # 用户名
        password: str = setting.get("password", "")  # 密码
        broker_id: str = setting.get("broker_id", "")  # 经纪商代码
        td_address: str = setting.get("td_address", "")  # 交易服务器
        appid: str = setting.get("appid", setting.get("app_id", ""))  # 产品名称 - 支持appid和app_id
        auth_code: str = setting.get("auth_code", "")  # 授权编码
        
        # 验证必需字段
        if not all([userid, password, broker_id, td_address]):
            missing_fields = []
            if not userid: missing_fields.append("userid/user_id")
            if not password: missing_fields.append("password") 
            if not broker_id: missing_fields.append("broker_id")
            if not td_address: missing_fields.append("td_address")
            raise ValueError(f"CTP交易网关连接参数不完整，缺少字段: {missing_fields}")

        td_address = self._prepare_address(td_address)
        self.td_api.connect(td_address, userid, password, broker_id, auth_code, appid)

        self.init_query() # Querying account/positions is TD related


    def send_order(self, req: OrderRequest) -> str:
        """
        委托下单
        :param req:
        :return:
        """
        if not self.td_api or not self.td_api.connect_status:
            self.write_log("无法发送订单：交易接口未连接或未初始化。")
            return ""
        return self.td_api.send_order(req)

    def cancel_order(self, req: CancelRequest) -> None:
        """
        委托撤单
        :param req:
        :return:
        """
        if not self.td_api or not self.td_api.connect_status:
            self.write_log("无法撤销订单：交易接口未连接或未初始化。")
            return
        self.td_api.cancel_order(req)


    def query_account(self) -> None:
        """
        查询资金
        :return:
        """
        if not self.td_api or not self.td_api.connect_status:
            self.write_log("无法查询资金：交易接口未连接或未初始化。")
            return
        self.td_api.query_account()


    def query_position(self) -> None:
        """
        查询持仓
        :return:
        """
        if not self.td_api or not self.td_api.connect_status:
            self.write_log("无法查询持仓：交易接口未连接或未初始化。")
            return
        self.td_api.query_position()

    def close(self) -> None:
        """
        关闭接口
        :return:
        """
        if self.td_api and self.td_api.connect_status:
            self.td_api.close()

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
        """定时事件处理"""
        if not self.td_api or not self.query_functions: # Timer events are for TD related queries
            return

        self.count += 1
        if self.count < 2:
            return
        self.count = 0

        func = self.query_functions.pop(0)
        func()
        self.query_functions.append(func)

    def init_query(self) -> None:
        """
        初始化查询任务
        :return:
        """
        if not self.td_api:
            self.write_log("交易接口未初始化，跳过查询任务初始化。")
            return
        self.query_functions: list = [self.query_account, self.query_position]



class CtpTdApi(TdApi):
    """
    CTP交易接口
    """
    def __init__(self, gateway: OrderTradingGateway) -> None:
        super().__init__()

        self.gateway: OrderTradingGateway = gateway
        self.gateway_name: str = gateway.gateway_name

        self.req_id: int = 0
        self.order_ref: int = 0

        self.connect_status: bool = False
        self.login_status: bool = False
        self.login_failed: bool = False
        self.auth_status: bool = False
        self.auth_failed: bool = False
        self.contract_inited: bool = False

        self.userid: str = ""
        self.password: str = ""
        self.broker_id: str = ""
        self.auth_code: str = ""
        self.appid: str = ""

        self.front_id: int = 0
        self.session_id: int = 0
        self.order_data: list[dict] = []
        self.trade_data: list[dict] = []
        self.positions: dict[str, PositionData] = {}
        self.sysid_orderid_map: dict[str, str] = {}
        self.parser = product_info
        self.instrument_exchange_id_map = instrument_exchange_id_map

    def onFrontConnected(self) -> None:
        """
        服务器连接成功回报
        当客户端与交易托管系统建立起通信连接时（还未登录前），该方法被调用。
        本方法在完成初始化后调用，可以在其中完成用户登录任务。
        :return: 无
        """
        logger.info("CTP行情API回调: onFrontConnected - 服务器连接成功")
        self.gateway.write_log("交易服务器连接成功")

        if self.auth_code:
            self.authenticate()
        else:
            self.login()

    def onFrontDisconnected(self, reason: int) -> None:
        """
        交易服务器连接断开回报
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
        """
        self.login_status = False
        self.gateway.write_log("交易服务器连接断开，原因：{}".format(reason))

    def onRspAuthenticate(self, data: dict, error: dict, reqid: int, last: bool) -> None:
        """
        用户授权验证回报，当执行 ReqAuthenticate 后，该方法被调用
        :param data: 客户端认证响应
        :param error: 响应信息
        :param reqid: 返回用户操作请求的 ID，该 ID 由用户在操作请求时指定。
        :param last: 指示该次返回是否为针对 reqid 的最后一次返回。
        :return: 无
        """
        if not error.get('ErrorID'):
            self.auth_status = True
            self.gateway.write_log("交易服务器授权验证成功")
            self.login()
        else:
            if error.get('ErrorID') == 63:
                self.auth_failed = True
            self.gateway.write_error("交易服务器授权验证失败", error)

    def onRspUserLogin(self, data: dict, error: dict, reqid: int, last: bool) -> None:
        """
        用户登录请求回报，当执行 ReqUserLogin 后，该方法被调用。
        :param data: 用户登录应答
        :param error: 响应信息
        :param reqid: 返回用户操作请求的 ID，该 ID 由用户在操作请求时指定。
        :param last: 指示该次返回是否为针对 reqid 的最后一次返回。
        :return: 无
        """
        logger.info(f"CTP交易API回调: onRspUserLogin - 登录回报, ErrorID={error.get('ErrorID', 'N/A')}")
        if not error.get("ErrorID"):
            logger.info("交易服务器登录成功")
            global_var.td_login_success = True
            self.login_status = True
            self.front_id = data["FrontID"]
            self.session_id = data["SessionID"]
            self.gateway.login_state = LoginState.LOGGED_IN
            self.gateway.write_log("交易服务器登录成功")

            # 自动确认结算单
            ctp_req: dict = {
                "BrokerID": self.broker_id,
                "InvestorID": self.userid
            }
            self.req_id += 1
            self.reqSettlementInfoConfirm(ctp_req, self.req_id)
        else:
            self.login_failed = True
            self.gateway.write_error("交易服务器登录失败", error)

    def onRspQryProduct(self, data: dict, error: dict, reqid: int, last: bool):
        """
        查询产品回报，当执行 ReqQryProduct 后，该方法被调用
        :param data: 产品信息
        :param error: 响应信息
        :param reqid: 返回用户操作请求的 ID，该 ID 由用户在操作请求时指定。
        :param last: 指示该次返回是否为针对 reqid 的最后一次返回。
        :return: 无
        """
        if not error.get("ErrorID"):
            sec = data['ProductID']
            opt = 'contract_multiplier'

            # 需要判断section是否存在，如果不存在会报错，option不需要检查是否存在
            if not self.parser.has_section(sec):
                self.parser.add_section(sec)

            self.parser.set(sec, opt, str(data['VolumeMultiple']))

            opt = 'minimum_price_change'
            self.parser.set(sec, opt, str(data['PriceTick']))

            if last:
                self.parser.write(open(GlobalPath.product_info_filepath, "w", encoding='utf-8'))
                self.gateway.write_log("查询产品成功！")
        else:
            self.gateway.write_error("查询产品失败", error)

    def onRspOrderInsert(self, data: dict, error: dict, reqid: int, last: bool) -> None:
        """
        报单录入失败回报，当执行ReqOrderInsert后，CTP判定失败后调用
        增强版本：包含合约映射验证和保护逻辑
        :param data:
        :param error:
        :param reqid:
        :param last:
        :return:
        """
        if not error or error.get("ErrorID") == 0:
            # 没有错误，正常返回
            return

        # 验证数据完整性
        if not data or "InstrumentID" not in data:
            self.gateway.write_error("订单插入失败回报数据不完整", error)
            return

        symbol = data["InstrumentID"]
        
        # 检查合约信息是否存在
        if symbol not in symbol_contract_map:
            self.gateway.write_log(f"订单失败：合约 {symbol} 不在合约映射中，可能合约信息尚未加载完成")
            
            # 如果合约信息尚未就绪，将订单数据缓存
            if not self.gateway.is_contracts_ready():
                self.gateway.write_log(f"合约信息未就绪，缓存订单失败数据: {symbol}")
                self.gateway.add_pending_order_data(data)
                return
            else:
                # 合约就绪但找不到该合约，可能是不支持的合约
                self.gateway.write_error(f"不支持的合约: {symbol}", error)
                return

        try:
            # 构建订单数据
            order_ref: str = data["OrderRef"]
            orderid: str = f"{self.front_id}_{self.session_id}_{order_ref}"
            contract: ContractData = symbol_contract_map[symbol]

            order: OrderData = OrderData(
                symbol=symbol,
                exchange=contract.exchange,
                orderid=orderid,
                direction=DIRECTION_CTP2VT[data["Direction"]],
                offset=OFFSET_CTP2VT[data["CombOffsetFlag"]],
                price=data["LimitPrice"],
                volume=data["VolumeTotalOriginal"],
                status=Status.REJECTED,
                gateway_name=self.gateway_name
            )
            
            # 发布订单状态更新
            self.gateway.on_order(order)

            # 记录详细错误信息
            error_id = error.get("ErrorID", "N/A")
            error_msg = error.get("ErrorMsg", "未知错误")
            self.gateway.write_error(f"交易委托失败 - 订单ID: {orderid}, 合约: {symbol}, 错误码: {error_id}, 错误信息: {error_msg}", error)
            
        except Exception as e:
            self.gateway.write_log(f"处理订单插入失败回报时发生异常: {e}")
        self.gateway.write_error("交易委托失败", error)

    def onRspOrderAction(self, data: dict, error: dict, reqid: int, last: bool) -> None:
        """
        委托撤单失败回报
        :param data:
        :param error:
        :param reqid:
        :param last:
        :return:
        """
        self.gateway.write_error("交易撤单失败", error)

    def onRspSettlementInfoConfirm(self, data: dict, error: dict, reqid: int, last: bool) -> None:
        """
        确认结算单回报，当执行 ReqSettlementInfoConfirm 后，该方法被调用。
        :param data: 投资者结算结果确认信息
        :param error: 响应信息
        :param reqid: 返回用户操作请求的 ID，该 ID 由用户在操作请求时指定。
        :param last: 指示该次返回是否为针对 reqid 的最后一次返回。
        :return: 无
        """
        if error and error.get('ErrorID') != 0:
            error_message = "结算单确认失败，错误信息为：{}，错误代码为：{}".format(error.get('ErrorMsg', 'N/A'),
                                                                                   error.get('ErrorID', 'N/A'))
            self.gateway.write_error(error_message, error)
        else:
            if last:
                self.gateway.write_log("结算信息确认成功")
                # 当结算单确认成功后，将登录成功标志设置为True
                # 这条语句之前用户添加过，但通常登录成功在onRspUserLogin中处理
                # global_var.td_login_success = True # 确认此标志的正确管理位置

                self.gateway.write_log("开始查询所有合约信息...")
                self.req_id += 1
                self.reqQryInstrument({}, self.req_id)

    def onRspQryInvestorPosition(self, data: dict, error: dict, reqid: int, last: bool) -> None:
        """
        持仓查询回报，当执行 ReqQryInvestorPosition 后，该方法被调用
        CTP 系统将持仓明细记录按合约，持仓方向，开仓日期（仅针对上期所，区分昨仓、今仓）进行汇总。
        :param data: 投资者持仓
        :param error: 响应信息
        :param reqid: 返回用户操作请求的 ID，该 ID 由用户在操作请求时指定。
        :param last: 指示该次返回是否为针对 reqid 的最后一次返回。
        :return:
        """
        if not data:
            return

        if error and error.get('ErrorID') != 0:
            self.gateway.write_error("查询持仓出错", error)
            return

        # 必须已经收到了合约信息后才能处理
        symbol: str = data["InstrumentID"]
        contract: ContractData = symbol_contract_map.get(symbol, None)

        if contract:
            # 获取之前缓存的持仓数据缓存
            key: str = f"{data['InstrumentID'], data['PosiDirection']}"
            position: PositionData = self.positions.get(key, None)
            if not position:
                position = PositionData(
                    symbol=data["InstrumentID"],
                    exchange=contract.exchange,
                    direction=DIRECTION_CTP2VT[data["PosiDirection"]],
                    gateway_name=self.gateway_name
                )
                self.positions[key] = position

            # 对于上期所昨仓需要特殊处理
            if position.exchange in {Exchange.SHFE, Exchange.INE}:
                if data["YdPosition"] and not data["TodayPosition"]:
                    position.yd_volume = data["Position"]
            # 对于其他交易所昨仓的计算
            else:
                position.yd_volume = data["Position"] - data["TodayPosition"]

            # 获取合约的乘数信息
            size: float = contract.size

            # 计算之前已有仓位的持仓总成本
            cost: float = position.price * position.volume * size

            # 累加更新持仓数量和盈亏
            position.volume += data["Position"]
            position.pnl += data["PositionProfit"]

            # 计算更新后的持仓总成本和均价
            if position.volume and size:
                cost += data["PositionCost"]
                position.price = cost / (position.volume * size)

            # 更新仓位冻结数量
            if position.direction == Direction.LONG:
                position.frozen += data["ShortFrozen"]
            else:
                position.frozen += data["LongFrozen"]

        if last:
            for position in self.positions.values():
                self.gateway.on_position(position)

            self.positions.clear()

    def onRspQryInvestorPositionDetail(self, data: dict, error: dict, reqid: int, last: bool):
        """
        请求查询投资者持仓明细响应，当执行 ReqQryInvestorPositionDetail 后，该方法被调用。
        :param data: 投资者持仓明细
        :param error: 响应信息
        :param reqid: 返回用户操作请求的 ID，该 ID 由用户在操作请求时指定。
        :param last: 指示该次返回是否为针对 reqid 的最后一次返回。
        :return: 无
        """
        if not error.get("ErrorID"):
            if last:
                self.gateway.write_log("查询持仓明细完成")
            if data is None or data['Volume'] == 0:
                return
        else:
            self.gateway.write_error("查询持仓明细失败", error)

    def onRspQryTradingAccount(self, data: dict, error: dict, reqid: int, last: bool) -> None:
        """
        资金查询回报，当执行 ReqQryTradingAccount 后，该方法被调用
        :param data:
        :param error:
        :param reqid:
        :param last:
        :return:
        """
        if "AccountID" not in data:
            return

        account: AccountData = AccountData(
            account_id=data["AccountID"],
            balance=data["Balance"],
            frozen=data["FrozenMargin"] + data["FrozenCash"] + data["FrozenCommission"],
            gateway_name=self.gateway_name
        )
        account.available = data["Available"]
        self.gateway.on_account(account)

    def onRspQryInstrument(self, data: dict, error: dict, reqid: int, last: bool) -> None:
        """
        合约查询回报，当执行 ReqQryInstrument 后，该方法被调用
        增强版本：包含状态管理和超时保护
        :param data: 合约
        :param error: 响应信息
        :param reqid: 返回用户操作请求的 ID，该 ID 由用户在操作请求时指定。
        :param last: 指示该次返回是否为针对 reqid 的最后一次返回。
        :return:
        """
        if error and error.get("ErrorID") != 0:
            self.gateway.write_log(f"CtpTdApi：onRspQryInstrument 出错。最后：{last}，错误 ID：{error.get('ErrorID', 'N/A')}")
            if last:
                # 合约查询失败，设置错误状态（同步调用）
                self.gateway.set_gateway_state(ConnectionState.ERROR)
            return

        # 如果是第一次回报，记录开始时间
        if self.gateway.contract_query_start_time is None:
            self.gateway.contract_query_start_time = time.time()
            self.gateway.write_log("开始处理合约信息...")

        # 处理单个合约数据
        if data:
            try:
                # 合约对象构建
                contract = ctp_build_contract(data, self.gateway_name)
                if contract:
                    self.gateway.on_contract(contract)
                    symbol_contract_map[contract.symbol] = contract
                    
                # 更新exchange_id_map，只取非纯数字的合约和6位以内的合约，即只取期货合约
                instrument_id = data.get("InstrumentID", "")
                if not instrument_id.isdigit() and len(instrument_id) <= 6:
                    self.instrument_exchange_id_map[instrument_id] = data.get("ExchangeID", "")
                    
            except Exception as e:
                self.gateway.write_log(f"处理合约数据失败: {e}")

        # 最后一次回报时的处理
        if last:
            try:
                # 检查是否在超时时间内完成
                if self.gateway.contract_query_start_time:
                    query_duration = time.time() - self.gateway.contract_query_start_time
                    if query_duration > self.gateway._contract_query_timeout:
                        self.gateway.write_log(f"合约查询超时: {query_duration:.2f}秒")
                        self.gateway.set_gateway_state(ConnectionState.ERROR)
                        return

                # 标记合约初始化完成
                self.contract_inited = True
                self.gateway._contracts_ready = True
                
                # 记录合约加载统计
                contract_count = len(symbol_contract_map)
                exchange_count = len(self.instrument_exchange_id_map)
                
                self.gateway.write_log(f"合约信息查询成功 - 共加载 {contract_count} 个合约，{exchange_count} 个交易所映射")
                
                # 保存合约交易所映射文件
                try:
                    write_json_file(str(GlobalPath.instrument_exchange_id_filepath), self.instrument_exchange_id_map)
                    self.gateway.write_log("合约交易所映射文件保存成功")
                except Exception as e:
                    self.gateway.write_error(f"写入 instrument_exchange_id.json 失败：{e}", error)

                # 设置网关状态为就绪（同步调用）
                self.gateway.set_gateway_state(ConnectionState.READY)
                
                # 发布合约就绪事件
                self.gateway._safe_publish_event(EventType.GATEWAY_CONTRACTS_READY, {
                    "gateway_name": self.gateway_name,
                    "contract_count": contract_count,
                    "timestamp": time.time(),
                    "query_duration": time.time() - self.gateway.contract_query_start_time if self.gateway.contract_query_start_time else 0
                })

                # 处理所有缓存的订单和成交数据
                self.gateway.process_pending_data()

                # 处理之前缓存的CTP回调数据
                for data in self.order_data:
                    self.onRtnOrder(data)
                self.order_data.clear()

                for data in self.trade_data:
                    self.onRtnTrade(data)
                self.trade_data.clear()

                self.gateway.write_log("🎉 CTP网关已完全就绪，可以开始交易")
                
            except Exception as e:
                self.gateway.write_log(f"完成合约初始化时发生错误: {e}")
                self.gateway.set_gateway_state(ConnectionState.ERROR)

    def onRtnOrder(self, data: dict) -> None:
        """
        委托更新推送，报单发出后有状态变动则通过此接口返回。公有流
        增强版本：包含合约映射验证和保护逻辑
        :param data:
        :return:
        """
        # 如果合约信息尚未初始化，缓存数据
        if not self.contract_inited:
            self.order_data.append(data)
            return

        if not data or "InstrumentID" not in data:
            self.gateway.write_log("订单更新数据不完整")
            return

        symbol: str = data["InstrumentID"]
        
        # 检查合约是否存在
        if symbol not in symbol_contract_map:
            self.gateway.write_log(f"订单更新：合约 {symbol} 不在合约映射中")
            
            # 如果合约信息尚未就绪，将数据缓存
            if not self.gateway.is_contracts_ready():
                self.gateway.write_log(f"合约信息未就绪，缓存订单更新数据: {symbol}")
                self.gateway.add_pending_order_data(data)
                return
            else:
                self.gateway.write_log(f"跳过不支持的合约订单更新: {symbol}")
                return

        try:
            contract: ContractData = symbol_contract_map[symbol]

            front_id: int = data["FrontID"]
            session_id: int = data["SessionID"]
            order_ref: str = data["OrderRef"]
            orderid: str = f"{front_id}_{session_id}_{order_ref}"

            status: Status = STATUS_CTP2VT.get(data["OrderStatus"], None)
            if not status:
                self.gateway.write_log(f"收到不支持的委托状态，委托号：{orderid}")
                return

            timestamp: str = f"{data['InsertDate']} {data['InsertTime']}"
            dt: datetime = datetime.strptime(timestamp, "%Y%m%d %H:%M:%S")
            dt: datetime = dt.replace(tzinfo=CHINA_TZ)

            tp: tuple = (data["OrderPriceType"], data["TimeCondition"], data["VolumeCondition"])
            order_type: OrderType = ORDERTYPE_CTP2VT.get(tp)
            if not order_type:
                self.gateway.write_log(f"收到不支持的委托类型，委托号：{orderid}")
                return

            order: OrderData = OrderData(
                symbol=symbol,
                exchange=contract.exchange,
                orderid=orderid,
                type=order_type,
                direction=DIRECTION_CTP2VT[data["Direction"]],
                offset=OFFSET_CTP2VT[data["CombOffsetFlag"]],
                price=data["LimitPrice"],
                volume=data["VolumeTotalOriginal"],
                traded=data["VolumeTraded"],
                status=status,
                datetime=dt,
                gateway_name=self.gateway_name
            )
            self.gateway.on_order(order)

            self.sysid_orderid_map[data["OrderSysID"]] = orderid
                
        except Exception as e:
            self.gateway.write_log(f"处理订单更新时发生异常: {e}")

    def onRtnTrade(self, data: dict) -> None:
        """
        成交数据推送，报单发出后有成交则通过此接口返回。私有流
        增强版本：包含合约映射验证和保护逻辑
        :param data:
        :return:
        """
        # 如果合约信息尚未初始化，缓存数据
        if not self.contract_inited:
            self.trade_data.append(data)
            return

        if not data or "InstrumentID" not in data:
            self.gateway.write_log("成交回报数据不完整")
            return

        symbol: str = data["InstrumentID"]
        
        # 检查合约是否存在
        if symbol not in symbol_contract_map:
            self.gateway.write_log(f"成交回报：合约 {symbol} 不在合约映射中")
            
            # 如果合约信息尚未就绪，将数据缓存
            if not self.gateway.is_contracts_ready():
                self.gateway.write_log(f"合约信息未就绪，缓存成交回报数据: {symbol}")
                self.gateway.add_pending_trade_data(data)
                return
            else:
                self.gateway.write_log(f"跳过不支持的合约成交回报: {symbol}")
                return

        try:
            contract: ContractData = symbol_contract_map[symbol]

            # 验证必要的订单系统ID映射
            if "OrderSysID" not in data or data["OrderSysID"] not in self.sysid_orderid_map:
                self.gateway.write_log(f"成交回报缺少订单系统ID映射: {data.get('OrderSysID', 'N/A')}")
                return

            orderid: str = self.sysid_orderid_map[data["OrderSysID"]]

            timestamp: str = f"{data['TradeDate']} {data['TradeTime']}"
            dt: datetime = datetime.strptime(timestamp, "%Y%m%d %H:%M:%S")
            dt = dt.replace(tzinfo=CHINA_TZ)

            trade: TradeData = TradeData(
                symbol=symbol,
                exchange=contract.exchange,
                orderid=orderid,
                trade_id=data["TradeID"],
                direction=DIRECTION_CTP2VT[data["Direction"]],
                offset=OFFSET_CTP2VT[data["OffsetFlag"]],
                price=data["Price"],
                volume=data["Volume"],
                datetime=dt,
                gateway_name=self.gateway_name
            )
            self.gateway.on_trade(trade)
            
        except Exception as e:
            self.gateway.write_log(f"处理成交回报时发生异常: {e}")

    def onRspQryInstrumentCommissionRate(self, data: dict, error: dict, reqid: int, last: bool):
        """
        请求查询合约手续费率响应，当执行 ReqQryInstrumentCommissionRate 后，该方法被调用。
        :param data: 合约手续费率
        :param error: 响应信息
        :param reqid: 返回用户操作请求的 ID，该 ID 由用户在操作请求时指定。
        :param last: 指示该次返回是否为针对 reqid 的最后一次返回。
        :return: 无
        """
        if error.get("ErrorID"):
            self.gateway.write_error("CtpTdApi：OnRspQryInstrumentCommissionRate 查询失败。错误 ID：{}".format(
                error.get('ErrorID', 'N/A')), error)
            return

        # 增加对data 和 data['InstrumentID']的有效性检查
        if data is None or not data.get("InstrumentID"):
            # 如果是最后一条回报但数据无效，可能需要记录一下
            if last:
                self.gateway.write_log(
                    "CtpTdApi：OnRspQryInstrumentCommissionRate 收到无效或空的合约手续费数据（最后一条）。ReqID: {}".format(
                        reqid))
            return

        # print(f'合约名称：{data.InstrumentID}')
        sec = del_num(data['InstrumentID'])

        # 需要判断section是否存在，如果不存在会报错，option不需要检查是否存在
        if not self.parser.has_section(sec):
            self.parser.add_section(sec)

        # 填写开仓手续费率
        opt = 'open_fee_rate'
        self.parser.set(sec, opt, str(data['OpenRatioByMoney']))

        # 填写开仓手续费
        opt = 'open_fee'
        self.parser.set(sec, opt, str(data['OpenRatioByVolume']))

        # 填写平仓手续费率
        opt = 'close_fee_rate'
        self.parser.set(sec, opt, str(data['CloseRatioByMoney']))

        # 填写平仓手续费
        opt = 'close_fee'
        self.parser.set(sec, opt, str(data['CloseRatioByVolume']))

        # 填写平今手续费率
        opt = 'close_today_fee_rate'
        self.parser.set(sec, opt, str(data['CloseTodayRatioByMoney']))

        # 填写平今手续费
        opt = 'close_today_fee'
        self.parser.set(sec, opt, str(data['CloseTodayRatioByVolume']))

        # 写入ini文件
        self.parser.write(open(GlobalPath.product_info_filepath, "w", encoding='utf-8'))

    def onErrRtnOrderAction(self, data: dict, error: dict):
        """
        报单操作错误回报，当执行 ReqOrderAction 后有字段填写不对之类的CTP报错则通过此接口返回
        :param data: 报单操作
        :param error: 响应信息
        :return: 无
        """
        if error['ErrorID'] != 0 and error is not None:
            self.gateway.write_error("报单操作请求失败", error)
        else:
            self.gateway.write_log('报单操作请求成功！')

    def onRspForQuoteInsert(self, data: dict, error: dict, reqid: int, last: bool) -> None:
        """
        询价请求回报
        """
        if not error["ErrorID"]:
            symbol: str = data["InstrumentID"]
            msg: str = f"{symbol}询价请求发送成功"
            self.gateway.write_log(msg)
        else:
            self.gateway.write_error("询价请求发送失败", error)

    def onRspUserLogout(self, data: dict, error: dict, reqid: int, last: bool):
        """
        登出请求响应，当执行ReqUserLogout后，该方法被调用。
        :param data: 用户登出请求
        :param error: 响应信息
        :param reqid: 返回用户操作请求的 ID，该 ID 由用户在操作请求时指定。
        :param last: 指示该次返回是否为针对 reqid 的最后一次返回。
        :return: 无
        """
        self.gateway.write_log('交易账户：{} 已登出'.format(data['UserID']))

    def connect(
            self,
            address: str,
            userid: str,
            password: str,
            brokerid: str,
            auth_code: str,
            appid: str
    ) -> None:
        """
        连接服务器
        :param address:
        :param userid:
        :param password:
        :param brokerid:
        :param auth_code:
        :param appid:
        :return:
        """
        self.userid = userid
        self.password = password
        self.broker_id = brokerid
        self.auth_code = auth_code
        self.appid = appid

        if not self.connect_status:
            path: Path = get_folder_path(self.gateway_name.lower())
            api_path_str = str(path) + "\\td"
            self.gateway.write_log("CtpTdApi：尝试创建路径为 {} 的 API".format(api_path_str))
            try:
                self.createFtdcTraderApi(api_path_str.encode("GBK").decode("utf-8"))
                self.gateway.write_log("CtpTdApi：createFtdcTraderApi调用成功。")
            except Exception as e_create:
                self.gateway.write_log("CtpTdApi：createFtdcTraderApi 失败！错误：{}".format(e_create))
                self.gateway.write_log("CtpTdApi：createFtdcTraderApi 回溯：{}".format(traceback.format_exc()))
                return

            self.subscribePrivateTopic(0)
            self.subscribePublicTopic(0)

            self.registerFront(address)
            self.gateway.write_log("CtpTdApi：尝试使用地址初始化 API：{}...".format(address))
            try:
                self.init()
                self.gateway.write_log("CtpTdApi：init 调用成功。")
            except Exception as e_init:
                self.gateway.write_log("CtpTdApi：初始化失败！错误：{}".format(e_init))
                self.gateway.write_log("CtpTdApi：初始化回溯：{}".format(traceback.format_exc()))
                return

            self.connect_status = True
        else:
            self.gateway.write_log("CtpTdApi：已连接，正在尝试身份验证。")
            self.authenticate()

    def authenticate(self) -> None:
        """
        发起授权验证
        :return:
        """
        if self.auth_failed:
            return

        ctp_req: dict = {
            "UserID": self.userid,
            "BrokerID": self.broker_id,
            "AuthCode": self.auth_code,
            "AppID": self.appid
        }

        self.req_id += 1
        self.reqAuthenticate(ctp_req, self.req_id)

    def login(self) -> None:
        """
        用户登录
        :return:
        """
        if self.login_failed:
            return

        ctp_req: dict = {
            "UserID": self.userid,
            "Password": self.password,
            "BrokerID": self.broker_id
        }

        self.req_id += 1
        self.reqUserLogin(ctp_req, self.req_id)

    def send_order(self, req: OrderRequest) -> str:
        """
        委托下单
        :param req:
        :return:
        """
        if req.offset not in OFFSET_VT2CTP:
            self.gateway.write_log("请选择开平方向")
            return ""

        if req.type not in ORDERTYPE_VT2CTP:
            self.gateway.write_log("当前接口不支持该类型的委托{}".format(req.type.value))
            return ""

        self.order_ref += 1

        tp: tuple = ORDERTYPE_VT2CTP[req.type]
        price_type, time_condition, volume_condition = tp

        ctp_req: dict = {
            "InstrumentID": req.symbol,
            "ExchangeID": req.exchange.value,
            "LimitPrice": req.price,
            "VolumeTotalOriginal": int(req.volume),
            "OrderPriceType": price_type,
            "Direction": DIRECTION_VT2CTP.get(req.direction, ""),
            "CombOffsetFlag": OFFSET_VT2CTP.get(req.offset, ""),
            "OrderRef": str(self.order_ref),
            "InvestorID": self.userid,
            "UserID": self.userid,
            "BrokerID": self.broker_id,
            "CombHedgeFlag": THOST_FTDC_HF_Speculation,
            "ContingentCondition": THOST_FTDC_CC_Immediately,
            "ForceCloseReason": THOST_FTDC_FCC_NotForceClose,
            "IsAutoSuspend": 0,
            "TimeCondition": time_condition,
            "VolumeCondition": volume_condition,
            "MinVolume": 1
        }

        self.req_id += 1
        n: int = self.reqOrderInsert(ctp_req, self.req_id)
        if n:
            self.gateway.write_log("委托请求发送失败，错误代码：{}".format(n))
            return ""

        orderid: str = f"{self.front_id}_{self.session_id}_{self.order_ref}"
        order: OrderData = req.create_order_data(orderid, self.gateway_name)
        self.gateway.on_order(order)

        return order.ho_orderid

    def cancel_order(self, req: CancelRequest) -> None:
        """
        委托撤单
        :param req:
        :return:
        """
        front_id, session_id, order_ref = req.orderid.split("_")

        ctp_req: dict = {
            "InstrumentID": req.symbol,
            "ExchangeID": req.exchange.value,
            "OrderRef": order_ref,
            "FrontID": int(front_id),
            "SessionID": int(session_id),
            "ActionFlag": THOST_FTDC_AF_Delete,
            "BrokerID": self.broker_id,
            "InvestorID": self.userid
        }

        self.req_id += 1
        self.reqOrderAction(ctp_req, self.req_id)

    def send_rfq(self, req: OrderRequest) -> str:
        """
        询价请求
        """
        # TODO: 这里类型后期需要处理一下
        exchange: Exchange = EXCHANGE_CTP2VT.get(req.exchange.value, None)
        if not exchange:
            self.gateway.write_log(f"不支持的交易所：{req.exchange}")
            return ""

        self.order_ref += 1

        tts_req: dict = {
            "InstrumentID": req.symbol,
            "ExchangeID": exchange,
            "ForQuoteRef": str(self.order_ref),
            "BrokerID": self.broker_id,
            "InvestorID": self.userid
        }

        self.req_id += 1
        self.reqForQuoteInsert(tts_req, self.req_id)

        orderid: str = f"{self.front_id}_{self.session_id}_{self.order_ref}"
        ho_orderid: str = f"{self.gateway_name}.{orderid}"

        return ho_orderid

    def query_account(self) -> None:
        """
        查询资金
        :return:
        """
        self.req_id += 1
        self.reqQryTradingAccount({}, self.req_id)

    def query_position(self) -> None:
        """
        查询持仓
        :return:
        """
        if not symbol_contract_map:
            return

        ctp_req: dict = {
            "BrokerID": self.broker_id,
            "InvestorID": self.userid
        }

        self.req_id += 1
        self.reqQryInvestorPosition(ctp_req, self.req_id)

    def update_commission_rate(self):
        """
        更新所有合约的手续费率
        :return: 空
        """
        symbol = ''
        # 暂时只获取期货合约
        all_instrument = list(self.instrument_exchange_id_map.keys())
        all_product = self.parser.sections()
        for product in all_product:
            self.gateway.write_log('产品：{}'.format(product))
            for instrument in all_instrument:
                if product == del_num(instrument):
                    symbol = instrument
                    break
            self.gateway.write_log('合约：{}'.format(symbol))
            if product != del_num(symbol):
                self.gateway.write_log('这里不符！')
                continue

            ctp_req: dict = {
                "BrokerID": self.broker_id,
                "InvestorID": self.userid,
                "InstrumentID": symbol
            }
            self.gateway.write_log('开始查询手续费...')
            while True:
                self.req_id += 1
                n: int = self.reqQryInstrumentCommissionRate(ctp_req, self.req_id)
                if not n:  # n是0时，表示请求成功
                    break
                else:
                    self.gateway.write_log("查询合约的手续费率，代码为 {}，正在查询手续费..."
                                           .format(n))
                    sleep(1)

    def close(self) -> None:
        """
        关闭连接
        :return:
        """
        if self.connect_status:
            self.exit()
