#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : trader_gateway.py
@Date       : 2025/9/10 20:29
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 交易网关，负责将订单发送到交易所
"""
import queue
import traceback
from datetime import datetime
from pathlib import Path
from typing import SupportsInt

from src.constants import INSTRUMENT_EXCHANGE_FILENAME, PRODUCT_INFO_FILENAME, Const
from src.core.base_gateway import BaseGateway
from src.core.constants import (
    ErrorReason,
    Currency,
    Exchange,
    Direction,
    Product,
    OrderStatus,
    OrderType,
    RspCode,
    RspMsg
)
from src.core.event import EventType, Event
from src.core.event_bus import EventBus
from src.core.object import (
    OrderRequest,
    CancelRequest,
    ContractData,
    OrderData,
    PositionData,
    AccountData,
    TradeData
)
from src.core.strategy_trade_logger import get_strategy_trade_logger
from src.ctp.api import TdApi
from src.ctp.api.ctp_constant import (
    THOST_TERT_QUICK,
    THOST_FTDC_HF_Speculation,
    THOST_FTDC_CC_Immediately,
    THOST_FTDC_FCC_NotForceClose,
    THOST_FTDC_AF_Delete
)
from src.modules.gateway.gateway_const import (
    REASON_MAPPING,
    ORDER_STATUS_CTP_TO_ENUM,
    symbol_contract_map,
    DIRECTION_CTP_TO_ENUM,
    PRODUCT_CTP_TO_ENUM,
    CHINA_TZ,
    ORDER_TYPE_CTP_TO_ENUM,
    DIRECTION_ENUM_TO_CTP,
    OFFSET_ENUM_TO_CTP,
    ORDER_TYPE_ENUM_TO_CTP
)
from src.modules.gateway.gateway_helper import (
    extract_error_msg,
    build_order_data,
    build_contract_data, build_rtn_order_data, build_trade_data, update_position_detail
)
from src.utils.get_path import get_path_ins
from src.utils.log import get_logger
from src.utils.utility import (
    prepare_address,
    write_json,
    load_ini,
    write_ini,
    del_num,
    delete_file,
    sleep
)


class TraderGateway(BaseGateway):

    def __init__(
            self,
            event_bus: EventBus,
            gateway_name: str = "TraderGateway"
    ) -> None:
        super().__init__(event_bus, gateway_name)
        self.event_bus = event_bus
        self.gateway_name: str = gateway_name
        self.td_api: CtpTdApi | None = None
        self.count: int = 0  # 资金和持仓的查询间隔
        self.query_functions: list = []
        self.logger = get_logger(self.__class__.__name__)
        self._last_account_data: dict | None = None  # 保存最后一次查询的账户数据

        
        # 设置网关事件处理器
        if self.event_bus:
            self._setup_gateway_event_handlers()
    
    def _setup_gateway_event_handlers(self) -> None:
        """设置网关事件处理器"""
        # 订阅订单提交请求事件
        self.event_bus.subscribe(EventType.ORDER_SUBMIT_REQUEST, self._handle_order_submit)
        # 订阅订单撤销请求事件
        self.event_bus.subscribe(EventType.ORDER_CANCEL_REQUEST, self._handle_order_cancel)
        self.logger.info(f"{self.gateway_name} 网关事件处理器已注册")
    
    def _handle_order_submit(self, event: Event) -> None:
        """
        处理订单提交请求事件
        
        Args:
            event: 订单提交事件，payload格式:
                   {"signal_id": "信号ID", "order_request": OrderRequest对象, "strategy_id": "策略ID"}
        """
        try:
            payload = event.payload
            order_request = payload.get('order_request')
            signal_id = payload.get('signal_id')
            strategy_id = payload.get('strategy_id')
            
            if not order_request:
                self.logger.warning("订单提交请求数据为空")
                return
            
            self.logger.info(f"收到订单提交请求: {order_request.instrument_id} "
                           f"{order_request.direction.value} {order_request.volume}@{order_request.price}")
            
            # 提交订单
            order_id = self.send_order(order_request)
            
            if order_id:
                self.logger.info(f"订单提交成功，OrderID: {order_id}, SignalID: {signal_id}")
                
                # 转发到策略日志
                try:
                    if strategy_id:
                        strategy_logger = get_strategy_trade_logger()
                        strategy_logger.log_order_submitted(
                            strategy_id,
                            order_request.instrument_id,
                            order_id,
                            signal_id
                        )
                except Exception as e:
                    self.logger.debug(f"转发策略日志失败: {e}")
            else:
                self.logger.error(f"订单提交失败，SignalID: {signal_id}")
            
        except Exception as e:
            self.logger.error(f"处理订单提交请求失败: {e}", exc_info=True)
    
    def _handle_order_cancel(self, event: Event) -> None:
        """
        处理订单撤销请求事件
        
        Args:
            event: 订单撤销事件，payload格式:
                   {"order_id": "订单ID", "signal_id": "信号ID"}
        """
        try:
            payload = event.payload
            order_id = payload.get('order_id')
            signal_id = payload.get('signal_id')
            
            if not order_id:
                self.logger.warning("订单撤销请求缺少order_id")
                return
            
            self.logger.info(f"收到订单撤销请求: OrderID={order_id}, SignalID={signal_id}")
            
            # 这里需要构造CancelRequest，但需要从order_id中提取信息
            # 暂时记录日志，后续可以完善
            self.logger.warning("订单撤销功能需要进一步完善，需要instrument_id和exchange_id信息")
            
        except Exception as e:
            self.logger.error(f"处理订单撤销请求失败: {e}", exc_info=True)

    def connect(self, setting: dict) -> None:
        """
        连接交易服务器
        :param setting:
        :return:
        """
        # 兼容性配置字段处理
        td_address: str = setting.get("td_address", "")  # 交易服务器
        broker_id: str = setting.get("broker_id", "")  # 经纪商代码
        user_id: str = setting.get("user_id", "")  # 用户名
        password: str = setting.get("password", "")  # 密码
        app_id: str = setting.get("app_id", "")  # 产品名称
        auth_code: str = setting.get("auth_code", "")  # 授权编码

        # 验证必需字段
        required_fields = [td_address, broker_id, user_id, password]
        if not all(required_fields):
            missing_fields = []
            if not td_address:
                missing_fields.append("td_address")
            if not broker_id: 
                missing_fields.append("broker_id")
            if not user_id: 
                missing_fields.append("user_id")
            if not password: 
                missing_fields.append("password")

            self.logger.error(f"CTP交易网关连接参数不完整，缺少字段: {missing_fields}")
            return
        
        # 记录app_id和auth_code状态（某些环境可以为空）
        self.logger.info(f"连接参数: broker_id={broker_id}, user_id={user_id}, app_id='{app_id}', auth_code='{auth_code}'")
        if not app_id:
            self.logger.info("app_id为空，某些CTP环境（如simnow）可以使用空值")
        if not auth_code:
            self.logger.info("auth_code为空，某些CTP环境（如simnow）可以使用空值")

        td_address = prepare_address(td_address)
        try:
            # 创建API实例
            if not self.td_api:
                self.td_api = CtpTdApi(self)
            # 连接交易服务器
            self.td_api.connect(td_address, broker_id, user_id, password, auth_code, app_id)
        except Exception as e:
            self.logger.exception(f"连接失败: {e}")
            if self.td_api:
                self.td_api.close()

        # 初始化定时查询账户资金和持仓信息
        self.init_query_acc_pos()

    def send_order(self, req: OrderRequest) -> str:
        """
        委托下单
        :return:
        """
        if self.td_api:
            return self.td_api.send_order(req)
        return ""

    def cancel_order(self, req: CancelRequest) -> None:
        """
        委托撤单
        :return:
        """
        if self.td_api:
            self.td_api.cancel_order(req)

    def update_instrument_handler(self, event: Event) -> None:
        self.logger.info(f"收到更新合约事件：{event.event_type}")
        self.logger.info("开始更新所有合约信息......")
        if self.td_api:
            self.td_api.query_instrument()

    def query_account(self) -> None:
        """查询资金"""
        if self.td_api:
            self.td_api.query_account()

    def query_position(self) -> None:
        """查询持仓"""
        if self.td_api:
            self.td_api.query_position()

    def close(self) -> None:
        """关闭接口"""
        if self.td_api:
            self.td_api.close()

    def logout(self) -> None:
        """
        登出交易服务器
        :return:
        """
        if self.td_api:
            self.td_api.logout()

    def process_timer_event(self, event: Event) -> None:
        """定时事件处理 - 轮流查询账户和持仓"""
        self.logger.debug(f"收到TIMER事件: {event.event_type}")
        if not self.td_api or not self.query_functions:
            return

        self.count += 1
        if self.count < 2:  # 每2次TIMER事件（如interval=5，则10秒执行一次）
            return
        self.count = 0
        # 轮流执行查询任务
        func = self.query_functions.pop(0)
        func()
        self.query_functions.append(func)

        if self.td_api:
            self.td_api.update_date()

    def init_query_acc_pos(self) -> None:
        """初始化查询任务"""
        if not self.td_api:
            self.logger.warning("交易接口未初始化，跳过查询任务初始化。")
            return
        self.count: int = 0
        self.query_functions: list = [self.query_account, self.query_position]
        # 订阅定时器事件
        self.event_bus.subscribe(EventType.TIMER, self.process_timer_event)

    def get_order_status_summary(self) -> None:
        """
        获取订单状态汇总
        :return:
        """
        if self.td_api:
            self.td_api.get_order_status_summary()
        else:
            self.logger.warning("交易接口未初始化")

    def connect_login_status(self) -> bool:
        """
        检查交易接口初始化、服务器连接和登录状态
        :return:
        """
        if not self.td_api or not self.td_api.connect_status or not self.td_api.login_status:
            self.logger.warning("交易接口未连接、未初始化或未登录交易服务器。")
            return False
        else:
            return True


class CtpTdApi(TdApi):
    """
    CTP交易接口
    """

    def __init__(self, gateway: TraderGateway) -> None:
        super().__init__()

        self.gateway: TraderGateway = gateway
        self.gateway_name: str = gateway.gateway_name
        self.logger = get_logger(self.__class__.__name__)

        # 流程：连接 -> 授权 -> 登录 -> 确认结算单
        self.connect_status: bool = False  # 连接状态
        self.auth_status: bool = False  # 授权状态
        self.login_status: bool = False  # 登录状态
        self.has_confirmed: bool = False    # 是否已确认过结算单
        self.contract_inited: bool = False  # 初始化合约状态

        self.address: str = ""  # 服务器地址 Server address
        self.broker_id: str = ""  # 经纪公司代码
        self.user_id: str = ""  # 用户代码
        self.user_product_info: str = "Homalos"  # 用户端产品信息
        self.password: str = ""  # 密码
        self.auth_code: str = ""  # 认证码
        self.app_id: str = ""  # App代码
        self.trading_day: str = ""  # 交易日
        self.login_time: str = ""  # 登录时间

        self.req_id: int = 0
        # 使用FrontID+SessionID+OrderRef撤单
        self.front_id: int = 0
        self.session_id: int = 0
        self.order_ref: int = 0

        # 订单状态跟踪字典  Order Status Tracking Dictionary
        self.order_status_map: dict = {}
        # 持仓明细
        self.position_detail_map: dict = {}

        # 订单队列，存储订单ID  An order queue and store the order ID
        self.order_queue: queue.Queue[str] = queue.Queue(maxsize=1000)

        self.order_data: list[dict] = []  # 订单数据
        self.trade_data: list[dict] = []  # 成交数据
        self.positions: dict[str, PositionData] = {}  # 持仓数据
        self.instrument_exchange_map: dict = {}  # 合约代码和交易所映射

        self.sysid_order_id_map: dict[str, str] = {}  # 系统ID和订单ID映射

        self.current_date: str = datetime.now().strftime("%Y%m%d")  # 当前自然日

        self.instrument_exchange_filepath: str = str(get_path_ins.get_config_dir() / INSTRUMENT_EXCHANGE_FILENAME)

        self.product_info_filepath: str = str(get_path_ins.get_config_dir() / PRODUCT_INFO_FILENAME)

    # ===================== 回调函数 =====================
    def onFrontConnected(self) -> None:
        """
        交易服务器连接成功响应
        当客户端与交易托管系统建立起通信连接时（还未登录前），该方法被调用。
        本方法在完成初始化后调用，可以在其中完成用户登录任务。

        Successful Trade Server Connection Response
        This method is called when the client establishes a communication connection with the trade hosting system
        (but before logging in).
        This method is called after initialization is complete and can be used to complete user login tasks.
        :return: None
        """
        self.connect_status = True  # 设置连接状态为已连接
        self.logger.info("交易服务器连接成功")

        # 若没有验证授权，则调用授权验证方法，授权回调中调用登录方法
        if not self.auth_status and self.auth_code:
            self.authenticate()
        else:
            # 若已经授权或不需要认证，则直接登录方法
            if not self.auth_status:
                # 如果不需要认证（auth_code为空），则跳过认证
                self.auth_status = True
                self.logger.info("跳过认证，直接登录")
            self.login()

    def onFrontDisconnected(self, reason: SupportsInt) -> None:
        """
        交易服务器连接断开响应
        当客户端与交易托管系统通信连接断开时，该方法被调用。
        当发生这个情况后，API会自动重新连接，客户端可不做处理。
        自动重连地址，可能是原来注册的地址，也可能是系统支持的其它可用的通信地址，它由程序自动选择。

        注:重连之后需要重新认证、登录。6.7.9及以后版本中，断线自动重连的时间间隔为固定1秒。
        :param reason: 错误代号，连接断开原因，为10进制值，因此需要转成16进制后再参照下列代码：
                0x1001（4097） 网络读失败。recv=-1
                0x1002（4098） 网络写失败。send=-1
                0x2001（8193） 接收心跳超时。接收心跳超时。前置每53s会给一个心跳报文给api，如果api超过120s未收到任何新数据，
                则认为网络异常，断开连接
                0x2002（8194） 发送心跳失败。api每15s会发送一个心跳报文给前置，如果api检测到超过40s没发送过任何新数据，则认为网络异常，
                断开连接
                0x2003 收到错误报文
        :return: None


        Trade server disconnection response
        This method is called when the client loses communication with the transaction hosting system.
        When this happens, the API will automatically reconnect and the client does not need to take any action.
        The automatic reconnection address may be the originally registered address or other available communication
        addresses supported by the system. It is automatically selected by the program.
        Note: You will need to re-authenticate and log in after reconnecting. In versions 6.7.9 and later,
        the automatic reconnection interval is fixed at 1 second.
        reason: The error code, the reason for disconnection, is a decimal value, so it needs to be converted to
        hexadecimal before referring to the following code:
                0x1001（4097） Network read failed.recv=-1
                0x1002（4098） Network write failed.send=-1
                0x2001（8193） Receive heartbeat timeout. Receive heartbeat timeout. The frontend sends a heartbeat
                message to the API every 53 seconds. If the API does not receive any new data for more than 120 seconds,
                it considers the network abnormality and disconnects.
                0x2002（8194） Failed to send heartbeat. The API sends a heartbeat message to the front-end every 15
                seconds. If the API detects that no new data has been sent for more than 40 seconds, it will consider
                the network abnormal and disconnect.
                0x2003 Received an error message
        return: None
        """
        # 断开连接，重置状态
        self.connect_status = False
        self.auth_status = False
        self.login_status = False

        reason_hex: str = hex(int(reason))  # 错误代码转换成16进制字符串, Error code converted to hexadecimal
        reason_msg: ErrorReason = REASON_MAPPING.get(reason_hex, ErrorReason.REASON_UNKNOWN)
        self.logger.info(f"交易服务器连接断开，原因是：{reason_msg.value} ({reason_hex})")

    def onRspAuthenticate(self, data: dict, error: dict, reqid: SupportsInt, last: bool) -> None:
        """
        用户授权验证响应，当执行 ReqAuthenticate 后，该方法被调用
        :param data: 客户端认证响应
        :param error: 响应信息
        :param reqid: 返回用户操作请求的 ID，该 ID 由用户在操作请求时指定。
        :param last: 指示该次返回是否为针对 reqid 的最后一次返回。
        :return: None

        User authorization verification response. This method is called after ReqAuthenticate is executed.
        data: Client authentication response
        error: Response information
        reqid: Returns the ID of the user operation request, which is specified by the user when making the operation request.
        last: Indicates whether this return is the last return for reqid.
        return: None
        """
        rsp_error_msg = extract_error_msg(error, "交易服务器授权验证失败")
        if rsp_error_msg:
            self.auth_status = False
            self.login_status = False
            self.logger.exception(rsp_error_msg)
            return
        else:
            # 请求响应的所有数据包全部返回，并且没有错误，则认为成功
            if last and data:
                self.auth_status = True
                self.logger.info(f"用户：{self.user_id} 交易服务器授权验证成功")
                self.login()
            if not last:
                self.logger.info("用户授权验证中...")

    def onRspUserLogin(self, data: dict, error: dict, reqid: SupportsInt, last: bool) -> None:
        """
        用户登录请求响应，当执行 ReqUserLogin 后，该方法被调用。
        :param data: 用户登录应答
        :param error: 响应信息
        :param reqid: 返回用户操作请求的 ID，该 ID 由用户在操作请求时指定。
        :param last: 指示该次返回是否为针对 reqid 的最后一次返回。
        :return: 无

        Response to user login request. This method is called after ReqUserLogin is executed.
        data: User login response
        error: Response information
        reqid: Returns the ID of the user operation request, which is specified by the user when making the
        operation request.
        last: Indicates whether this return is the last return for reqid.
        return: None
        """
        rsp_error_msg = extract_error_msg(error, "交易服务器登录失败！")
        if rsp_error_msg:
            self.login_status = False
            self.logger.exception(rsp_error_msg)

            if self.gateway.event_bus:
                payload = {
                    "code": RspCode.LOGIN_TD_FAILED,
                    "message": RspMsg.LOGIN_TD_FAILED,
                    "data": {}
                }
                self.gateway.event_bus.publish(Event(EventType.TD_GATEWAY_LOGIN, payload=payload))
                self.logger.info("已发布 TD_GATEWAY_LOGIN 事件")
            return
        else:
            # 请求响应的所有数据包全部返回，并且没有错误，则认为成功
            if last and data:
                self.login_status = True
                self.logger.info("登录交易服务器成功")

                self.trading_day = data.get("TradingDay", "")
                self.login_time = data.get("LoginTime", "")
                self.front_id = data.get("FrontID", 0)
                self.session_id = data.get("SessionID", 0)

                if self.gateway.event_bus:
                    payload = {
                        "code": RspCode.LOGIN_TD_SUCCESS,
                        "message": RspMsg.LOGIN_TD_SUCCESS,
                        "data": {
                            "trading_day": self.trading_day,
                            "login_time": self.login_time,
                            "front_id": self.front_id,
                            "session_id": self.session_id
                        }
                    }
                    self.gateway.event_bus.publish(Event(EventType.TD_GATEWAY_LOGIN, payload=payload))
                    self.logger.info("已发布 TD_GATEWAY_LOGIN 事件")

                settlement_req: dict = {
                    "BrokerID": self.broker_id,
                    "InvestorID": self.user_id
                }
                # 判断是否是新的交易日
                if self.trading_day != Const.trading_day:
                    self.req_id += 1
                    self.logger.info("开始确认结算单......")
                    # 调用确认结算单方法 Call the settlement confirmation method
                    self.reqSettlementInfoConfirm(settlement_req, self.req_id)
                else:
                    # 同一个交易日，如果没有确认过结算单，则进行确认
                    if not self.has_confirmed:
                        self.req_id += 1
                        self.logger.info("开始确认结算单......")
                        # 调用确认结算单方法 Call the settlement confirmation method
                        self.reqSettlementInfoConfirm(settlement_req, self.req_id)
                    else:
                        self.logger.info("结算单已经确认过，跳过再次确认")
                        # 这里的处理逻辑：确认过和跳过确认都发送确认成功事件
                        if self.gateway.event_bus:
                            payload = {
                                "code": RspCode.SETTLEMENT_CONFIRM_ALREADY,
                                "message": RspMsg.SETTLEMENT_CONFIRM_ALREADY,
                                "data": {}
                            }
                            self.gateway.event_bus.publish(Event(EventType.TD_ALREADY_CONFIRMED, payload=payload))
                            self.logger.info("已发布 TD_ALREADY_CONFIRMED 事件")

            if not last:
                self.logger.info("等待确认结算单......")

    def onRspSettlementInfoConfirm(self, data: dict, error: dict, reqid: SupportsInt, last: bool) -> None:
        """
        投资者结算结果确认响应，当执行ReqSettlementInfoConfirm后，该方法被调用。
        :param data: 投资者结算结果确认信息
        :param error: 响应信息
        :param reqid: 返回用户操作请求的 ID，该 ID 由用户在操作请求时指定。
        :param last: 指示该次返回是否为针对 reqid 的最后一次返回。
        :return: None

        Investor settlement result confirmation response. This method is called after ReqSettlementInfoConfirm is executed.
        data: Investor settlement result confirmation information
        error: Response information
        reqid: Returns the ID of the user operation request, which is specified by the user when making the operation request.
        last: Indicates whether this return is the last return for reqid.
        return: None
        """
        rsp_error_msg = extract_error_msg(error, "结算单确认失败！")
        if rsp_error_msg:
            self.has_confirmed = False
            self.logger.exception(rsp_error_msg)
        else:
            if not data:
                return

            # 请求响应的所有数据包全部返回，并且没有错误，则认为成功
            # 当结算单确认成功后，将确认结算标志设置为True
            self.has_confirmed = True
            confirm_date: str = data.get("ConfirmDate", "")
            confirm_time = data.get("ConfirmTime")
            settlement_id = data.get("SettlementID")
            self.logger.info(f"确认日期：{confirm_date}, 时间：{confirm_time}, 结算编号：{settlement_id}")

            if last:
                Const.trading_day = confirm_date
                self.logger.info("结算单确认成功")
                # 发布结算单确认成功事件
                if self.gateway.event_bus:
                    payload = {
                        "code": 0,
                        "message": "结算单确认成功",
                        "data": {
                            "confirm_date": confirm_date,
                            "confirm_time": confirm_time,
                            "settlement_id": settlement_id
                        }
                    }
                    self.gateway.event_bus.publish(Event(EventType.TD_CONFIRM_SUCCESS, payload=payload))
                    self.logger.info("已发布 TD_CONFIRM_SUCCESS 事件")
            else:
                self.logger.info("结算单确认中...")

    def onRspQryInvestorPosition(self, data: dict, error: dict, reqid: SupportsInt, last: bool) -> None:
        """
        请求查询投资者持仓响应，当执行ReqQryInvestorPosition后，该方法被调用。
        CTP 系统将持仓明细记录按合约，持仓方向，开仓日期（仅针对上期所，区分昨仓、今仓）进行汇总。
        卖可平数量=多头仓-shortfrozen
        买可平数量=空头仓-longfrozen
        :param data: 投资者持仓
        :param error: 响应信息
        :param reqid: 返回用户操作请求的ID，该ID 由用户在操作请求时指定。
        :param last: 指示该次返回是否为针对nRequestID的最后一次返回。
        :return: None
        """
        rsp_error_msg = extract_error_msg(error, "请求查询投资者持仓发生错误！")
        if rsp_error_msg:
            self.logger.exception(rsp_error_msg)
            return
        else:
            if not data:
                return

            # 必须已经收到了合约信息后才能处理
            instrument_id: str = data.get("InstrumentID", "")
            # 从缓存中获取合约信息
            contract: ContractData | None = symbol_contract_map.get(instrument_id)
            if contract:
                posi_direction: str = data.get("PosiDirection", "")  # 获取持仓多空方向
                position_key: str = f"{instrument_id, posi_direction}"
                # 获取之前缓存的持仓数据缓存
                position: PositionData | None = self.positions.get(position_key)
                if not position:
                    position = PositionData(
                        instrument_id = instrument_id,
                        exchange_id = contract.exchange_id,
                        direction = DIRECTION_CTP_TO_ENUM[posi_direction]
                    )
                    self.positions[position_key] = position

                # 对于上期所和上海国际能源交易中心昨仓需要特殊处理
                if position.exchange_id in {Exchange.SHFE, Exchange.INE}:
                    if data.get("YdPosition") and not data.get("TodayPosition"):
                        position.yd_volume = data.get("Position", 0)
                # 对于其他交易所昨仓的计算
                else:
                    position.yd_volume = data.get("Position", 0) - data.get("TodayPosition", 0)

                # 获取合约的乘数信息
                size: int = contract.size

                # 计算之前已有仓位的持仓总成本
                cost: float = position.price * position.volume * size

                # 累加更新持仓数量和盈亏
                position.volume += data.get("Position", 0)
                position.pnl += data.get("PositionProfit", 0.0)

                # 计算更新后的持仓总成本和均价
                if position.volume and size:
                    cost += data.get("PositionCost", 0.0)
                    position.price = cost / (position.volume * size)

                # 更新仓位冻结数量
                if position.direction == Direction.LONG:
                    position.frozen += data.get("ShortFrozen", 0)
                else:
                    position.frozen += data.get("LongFrozen", 0)


            if last:
                self.logger.info("查询所有持仓成功")
                for position in self.positions.values():
                    # 只推送持仓数量大于0的仓位
                    if position.volume > 0:
                        # 将仓位数据推送到事件总线
                        self.gateway.on_position(position)
                        self.logger.info(f"持仓数据: {position}")

                self.positions.clear()

    def onRspQryInvestorPositionDetail(self, data: dict, error: dict, reqid: SupportsInt, last: bool) -> None:
        """
        请求查询投资者持仓明细响应，当执行ReqQryInvestorPositionDetail后，该方法被调用。
        :param data: 投资者持仓明细
        :param error: 响应信息
        :param reqid: 返回用户操作请求的 ID，该 ID 由用户在操作请求时指定。
        :param last: 指示该次返回是否为针对 reqid 的最后一次返回。
        :return: 无
        """
        rsp_error_msg = extract_error_msg(error, "请求查询投资者持仓明细发生错误！")
        if rsp_error_msg:
            self.logger.exception(rsp_error_msg)
            return
        else:
            if not data or data.get("Volume") == 0:
                return

            if data:
                self.position_detail_map = update_position_detail(data)

            if last:
                self.logger.info("查询投资者持仓明细完成")

    def onRspQryTradingAccount(self, data: dict, error: dict, reqid: SupportsInt, last: bool) -> None:
        """
        请求查询资金账户响应，当执行ReqQryTradingAccount后，该方法被调用。
        :param data: 资金账户
        :param error: 响应信息
        :param reqid: 返回用户操作请求的ID，该ID 由用户在操作请求时指定。
        :param last: 指示该次返回是否为针对nRequestID的最后一次返回。
        :return: None
        """
        rsp_error_msg = extract_error_msg(error, "请求查询资金账户发生错误！")
        if rsp_error_msg:
            self.logger.exception(rsp_error_msg)
            return
        else:
            if not data:
                return

            if "AccountID" not in data:
                return

            account: AccountData = AccountData(
                account_id = data.get("AccountID", ""),
                balance = data.get("Balance", 0.0),
                frozen = data.get("FrozenMargin", 0.0) + data.get("FrozenCash", 0.0) + data.get("FrozenCommission", 0.0)
            )
            account.available = data.get("Available", 0.0)
            
            # 记录日志
            if last:
                self.logger.info("查询资金账户成功")
                self.logger.info(f"账户数据: {account}")
            
            # 保存最后一次查询的账户数据（用于WebSocket直接获取）
            self._last_account_data = {
                "account_id": account.account_id,
                "balance": account.balance,
                "frozen": account.frozen,
                "available": account.available
            }
            
            # 推送账户信息到事件总线
            self.gateway.on_account(account)

    def onRspQryInstrument(self, data: dict, error: dict, reqid: SupportsInt, last: bool) -> None:
        """
        请求查询合约响应，当执行ReqQryInstrument后，该方法被调用。
        :param data: 合约信息
        :param error: 响应信息
        :param reqid: 返回用户操作请求的 ID，该 ID 由用户在操作请求时指定。
        :param last: 指示该次返回是否为针对 reqid 的最后一次返回。
        :return: None
        """
        rsp_error_msg = extract_error_msg(error, "请求查询合约发生错误")
        if rsp_error_msg:
            self.logger.exception(rsp_error_msg)
            return
        else:
            if not data:
                return

            # 获取产品类型枚举
            product: Product | None = PRODUCT_CTP_TO_ENUM.get(data.get("ProductClass", ""))
            if product:
                contract = build_contract_data(data, product)
                # TODO: 后期考虑是否推送合约信息到事件总线
                # self.gateway.on_contract(contract)
                product = contract.product
                if product == Product.FUTURES:
                    instrument_id: str = contract.instrument_id
                    symbol_contract_map[instrument_id] = contract
                    # 缓存合约和交易所的映射关系
                    self.instrument_exchange_map[instrument_id] = data.get("ExchangeID", "")
                else:
                    self.logger.debug(f"跳过非期货产品类型: {product.value}")

            if last:
                self.contract_inited = True
                self.logger.info("合约信息查询成功")

                # 记录查询到的合约数量
                instrument_count: int = len(self.instrument_exchange_map)
                self.logger.info(f"共查询到 {instrument_count} 个合约->交易所映射")
                # 如果需要更新并且合约数量不为0，则保存
                if instrument_count != 0:
                    sleep(0.5)
                    delete_file(self.instrument_exchange_filepath)
                    # 保存合约交易所映射文件
                    try:
                        write_json(self.instrument_exchange_filepath, self.instrument_exchange_map)
                        self.logger.info(f"合约交易所映射文件保存成功: {self.instrument_exchange_filepath}")
                    except Exception as e:
                        self.logger.exception(f"写入{self.instrument_exchange_filepath}失败：{e}")

                for data in self.order_data:
                    self.onRtnOrder(data)
                self.order_data.clear()

                for data in self.trade_data:
                    self.onRtnTrade(data)
                self.trade_data.clear()

                # 设置查询合约状态
                if self.gateway.event_bus:
                    payload = {
                        "code": RspCode.CONTRACT_SYMBOL_QUERY_COMPLETE,
                        "message": RspMsg.CONTRACT_SYMBOL_QUERY_COMPLETE,
                        "data": {}
                    }
                    self.gateway.event_bus.publish(Event(EventType.TD_QRY_INS, payload=payload))
                    self.logger.info("已发布 TD_QRY_INS 事件")

    def onRspQryProduct(self, data: dict, error: dict, reqid: SupportsInt, last: bool) -> None:
        """
        查请求查询产品响应，当执行ReqQryProduct后，该方法被调用。
        :param data: 产品信息
        :param error: 响应信息
        :param reqid: 返回用户操作请求的 ID，该 ID 由用户在操作请求时指定。
        :param last: 指示该次返回是否为针对 reqid 的最后一次返回。
        :return: 无
        """
        rsp_error_msg = extract_error_msg(error, "查请求查询产品发生错误！")
        if rsp_error_msg:
            self.logger.exception(rsp_error_msg)
            return
        else:
            if not data:
                return

            # 获取产品代码
            product_id = data.get("ProductID", "")

            parser = load_ini(self.product_info_filepath)
            # 需要判断section是否存在，如果不存在会报错，option不需要检查是否存在
            if not parser.has_section(product_id):
                parser.add_section(product_id)

            parser.set(product_id, 'contract_multiplier', str(data.get("VolumeMultiple")))

            parser.set(product_id, 'minimum_price_change', str(data.get("PriceTick")))

            if last:
                self.logger.info("查询产品成功！")
                write_ini(parser, self.product_info_filepath)

    def onRspQryInstrumentCommissionRate(self, data: dict, error: dict, reqid: SupportsInt, last: bool) -> None:
        """
        请求查询合约手续费率响应，当执行ReqQryInstrumentCommissionRate后，该方法被调用。
        :param data: 合约手续费率
        :param error: 响应信息
        :param reqid: 返回用户操作请求的 ID，该 ID 由用户在操作请求时指定。
        :param last: 指示该次返回是否为针对 reqid 的最后一次返回。
        :return: None
        """
        rsp_error_msg = extract_error_msg(error, "请求查询合约手续费率发生错误！")
        if rsp_error_msg:
            self.logger.exception(rsp_error_msg)
            return
        else:
            # 增加对data 和 data['InstrumentID']的有效性检查
            if not data or not data.get("InstrumentID", ""):
                # 如果是最后一条回报但数据无效，可能需要记录一下
                if last:
                    self.logger.info("OnRspQryInstrumentCommissionRate 收到无效或空的合约手续费数据（最后一条）。"
                                     "ReqID: {}".format(self.req_id))
                return

            section = del_num(data.get("InstrumentID"))
            parser = load_ini(self.product_info_filepath)
            # 需要判断section是否存在，如果不存在会报错，option不需要检查是否存在
            if not parser.has_section(section):
                parser.add_section(section)

            # 填写开仓手续费率
            parser.set(section, 'open_fee_rate', str(data.get("OpenRatioByMoney")))
            # 填写开仓手续费
            parser.set(section, 'open_fee', str(data.get("OpenRatioByVolume")))
            # 填写平仓手续费率
            parser.set(section, 'close_fee_rate', str(data.get("CloseRatioByMoney")))
            # 填写平仓手续费
            parser.set(section, 'close_fee', str(data.get("CloseRatioByVolume")))
            # 填写平今手续费率
            parser.set(section, 'close_today_fee_rate', str(data.get("CloseTodayRatioByMoney")))
            # 填写平今手续费
            parser.set(section, 'close_today_fee', str(data.get("CloseTodayRatioByVolume")))

            # 写入ini文件
            write_ini(parser, self.product_info_filepath)

    def onRspOrderInsert(self, data: dict, error: dict, reqid: SupportsInt, last: bool) -> None:
        """
        报单录入请求响应，当执行ReqOrderInsert后有字段填写不对之类的CTP报错则通过此接口返回
        :param data: 输入报单
        :param error: 响应信息
        :param reqid: 返回用户操作请求的ID，该ID 由用户在操作请求时指定。
        :param last: 指示该次返回是否为针对nRequestID的最后一次返回。
        :return: None

        Order entry request response. When a CTP error such as incorrect field filling occurs after executing
        ReqOrderInsert, it is returned through this interface.
        data: Enter order
        error: Response information
        reqid: Returns the ID of the user operation request, which is specified by the user when making
        the operation request.
        last: Indicates whether this is the last return for nRequestID.
        return: None
        """
        rsp_error_msg = extract_error_msg(error, "报单录入请求发生错误！")
        if rsp_error_msg:
            self.logger.exception(rsp_error_msg)
            return
        else:
            if last and data:
                order_ref: str = data.get("OrderRef", "")  # 报单引用
                instrument_id: str = data.get("InstrumentID", "")  # 合约代码

                order_id: str = f"{self.front_id}_{self.session_id}_{order_ref}"

                # 获取合约信息
                contract: ContractData = symbol_contract_map[instrument_id]
                order: OrderData = build_order_data(data, contract, order_id)

                # 将订单数据推送到事件总线，方便其他模块处理
                self.logger.info(f"订单号：{order.order_id}, "
                                 f"买卖方向：{order.direction}, "
                                 f"组合开平标志：{order.offset}, "
                                 f"价格：{order.price}, "
                                 f"数量：{order.volume}, "
                                 f"合约代码：{order.instrument_id}")
                # 推送订单数据到数据总线
                self.gateway.on_order(order)

            if not last:
                self.logger.info("报单录入请求响应中......")

    def onErrRtnOrderInsert(self, data: dict, error: dict) -> None:
        """
        报单录入错误回报，当执行ReqOrderInsert后有字段填写不对之类的CTP报错则通过此接口返回
        :param data: 输入报单
        :param error: 响应信息
        :return: None

        Report order entry errors. When a CTP error such as incorrect field filling is found after executing
        ReqOrderInsert, this interface will be used to return the error.
        data: Enter order
        error: Response information
        return: None
        """
        rsp_error_msg = extract_error_msg(error, "报单录入错误")
        if rsp_error_msg:
            self.logger.exception(rsp_error_msg)
            return
        else:
            # 没有错误，正常返回 No error, return normally
            return

    def onRtnOrder(self, data: dict) -> None:
        """
        报单通知，当执行ReqOrderInsert后并且报出后，收到返回则调用此接口，私有流回报。

        Order notification: After ReqOrderInsert is executed and reported, this interface is called when a
        return is received, which is a private flow return.
        :param data: 报单 declaration
        :return: None
        """
        if not data or "InstrumentID" not in data:
            # 订单更新数据不完整
            self.logger.warning("订单更新数据不完整")
            return

        # 合约未初始化
        if not self.contract_inited:
            self.order_data.append(data)
            return

        instrument_id: str = data.get("InstrumentID", "")  # 合约代码
        # 从缓存中获取合约信息
        contract: ContractData = symbol_contract_map[instrument_id]

        order_ref: str = data.get("OrderRef", "")  # 报单引用
        front_id: int = data.get("FrontID", 0)  # 前置编号
        session_id: int = data.get("SessionID", 0)  # 会话编号

        order_id: str = f"{front_id}_{session_id}_{order_ref}"

        order_status: OrderStatus | None = ORDER_STATUS_CTP_TO_ENUM.get(data.get("OrderStatus", ""))
        if not order_status:
            self.logger.info(f"收到不支持的委托状态，委托号：{order_id}")
            return

        # 获取状态
        self.logger.info(f"订单状态更新 - OrderID：{order_id}，状态：{order_status.value})")

        # 记录当前订单状态  Record current order status
        old_status: str = self.order_status_map.get(order_id, "新订单")
        self.order_status_map[order_id] = order_status

        # 检查是否为撤单状态  Check whether the order is cancelled
        if order_status == OrderStatus.CANCELED:
            self.logger.info(f"订单已撤销 - OrderID: {order_id}, InstrumentID: {instrument_id}")
            self.logger.info("撤单原因: 系统自动撤单或手动撤单")
        elif order_status == OrderStatus.ALL_TRADED:
            self.logger.info(f"订单全部成交 - OrderID: {order_id}, InstrumentID: {instrument_id}")
        elif order_status == OrderStatus.PART_TRADED_QUEUEING:
            self.logger.info(f"订单部分成交，剩余在队列中 - OrderID: {order_id}, InstrumentID: {instrument_id}")
        elif order_status == OrderStatus.NO_TRADE_QUEUEING:
            self.logger.info(f"订单未成交，在队列中等待 - OrderID: {order_id}, InstrumentID: {instrument_id}")
        elif order_status == OrderStatus.NO_TRADE_NOT_QUEUEING:
            self.logger.info(f"订单未成交且不在队列中 - OrderID: {order_id}, InstrumentID: {instrument_id}")
            self.logger.info("可能原因: 价格超出涨跌停板、资金不足、合约不存在等")

        self.logger.info(f"状态变化: {old_status} -> {order_status.value}")

        timestamp_str: str = f"{data.get('InsertDate', '')} {data.get('InsertTime', '')}"
        timestamp: datetime = datetime.strptime(timestamp_str, "%Y%m%d %H:%M:%S").replace(tzinfo=CHINA_TZ)

        tp: tuple = (data.get("OrderPriceType", ""), data.get("TimeCondition", ""), data.get("VolumeCondition", ""))
        order_type: OrderType | None = ORDER_TYPE_CTP_TO_ENUM.get(tp)
        if not order_type:
            self.logger.info(f"收到不支持的委托类型，委托号：{order_id}")
            return

        order: OrderData = build_rtn_order_data(data, contract, order_id, order_type, order_status, timestamp)

        # 发布订单状态更新事件到事件总线
        if self.gateway.event_bus:
            order_status_event = Event(
                EventType.ORDER_STATUS_UPDATE,
                payload={
                    "code": 0,
                    "message": "发布订单状态更新",
                    "data": {
                        "order_id": order_id,
                        "order_status": order_status,
                        "order_data": order,
                        "instrument_id": instrument_id
                    }
                }
            )
            self.gateway.event_bus.publish(order_status_event)
            self.logger.debug(f"已发布订单状态更新事件: {order_id} -> {order_status.value}")
        
        sysid = data.get("OrderSysID", "")
        if sysid:
            self.sysid_order_id_map[sysid] = order_id
        self.logger.info(f"订单更新 - order：{order}")

    def onRtnTrade(self, data: dict) -> None:
        """
        成交通知，报单发出后有成交则通过此接口返回。私有流

        Transaction notification, after the order is issued, if there is a transaction, it will be returned
        through this interface. Private flow
        :param data: 成交  make a deal
        :return: None
        """
        if not data or "InstrumentID" not in data:
            self.logger.warning("成交回报数据不完整")
            return

        # 验证必要的报单编号
        if "OrderSysID" not in data:
            self.logger.warning("成交回报缺少报单编号OrderSysID")
            return

        if not self.contract_inited:
            self.trade_data.append(data)
            return

        instrument_id: str = data.get("InstrumentID", "")  # 合约代码
        # 从缓存中获取合约信息
        contract: ContractData = symbol_contract_map[instrument_id]
        # 从缓存中获取报单编号
        order_sys_id: str = data.get("OrderSysID", "")
        order_id: str = self.sysid_order_id_map.get(order_sys_id, "")
        # 成交日期和成交时间组合为时间戳
        timestamp_str: str = f"{data.get('TradeDate', '')} {data.get('TradeTime', '')}"
        timestamp: datetime = datetime.strptime(timestamp_str, "%Y%m%d %H:%M:%S").replace(tzinfo=CHINA_TZ)

        trade: TradeData = build_trade_data(data, contract, order_id, timestamp)

        # 发布成交回报事件到事件总线
        if self.gateway.event_bus:
            trade_execution_event = Event(
                EventType.TRADE_EXECUTION,
                payload={
                    "code": 0,
                    "message": "发布成交回报",
                    "data": {
                        "trade_data": trade,
                        "order_id": order_id,
                        "instrument_id": instrument_id
                    }
                }
            )
            self.gateway.event_bus.publish(trade_execution_event)
            self.logger.info(f"✓ 已发布成交回报事件到事件总线: TradeID={trade.trade_id}, OrderID={order_id}, Instrument={instrument_id}")
        else:
            self.logger.warning("⚠️ 事件总线未初始化，无法发布成交事件")

        self.logger.info(f"TradeID: {trade.trade_id}, "
                         f"OrderSysID: {trade.order_id}, "
                         f"Direction: {trade.direction}, "
                         f"OffsetFlag: {trade.offset}, "
                         f"Price: {trade.price}, "
                         f"Volume: {trade.volume}, "
                         f"InstrumentID: {trade.instrument_id}")
        # TODO: 写入交易流水

    def onRspOrderAction(self, data: dict, error: dict, reqid: SupportsInt, last: bool) -> None:
        """
        撤销报单操作请求响应，当执行ReqOrderAction后有字段填写不对之类的CTP报错则通过此接口返回

        ActionFlag：目前只有删除（撤单）的操作，修改（改单）的操作还没有，可以通过撤单之后重新报单实现。
        :param data: 输入报单操作
        :param error: 响应信息
        :param reqid: 返回用户操作请求的ID，该ID 由用户在操作请求时指定。
        :param last: 指示该次返回是否为针对nRequestID的最后一次返回。
        :return: None

        Order operation request response. When a CTP error such as incorrect field filling is found after
        executing ReqOrderAction, it is returned through this interface.

        ActionFlag：Currently, there is only the deletion (cancellation) operation, and the modification
        (change order) operation is not available. It can be achieved by canceling the order and then re-submitting the order.
        data: Enter order operation
        error: Response information
        reqid: Returns the ID of the user operation request, which is specified by the user when making the
        operation request.
        last: Indicates whether this is the last return for nRequestID.
        return: None
        """
        # Transaction cancellation failed
        rsp_error_msg = extract_error_msg(error, "撤销报单操作请求失败")
        if rsp_error_msg:
            self.logger.exception(rsp_error_msg)
            return
        else:
            if not data:
                return

            self.logger.info("撤销报单操作请求成功")
            order_ref = data.get("OrderRef")
            front_id = data.get("FrontID")
            session_id = data.get("SessionID")
            # 组合成订单号OrderID
            order_id: str = f"{front_id}_{session_id}_{order_ref}"

            self.order_status_map.pop(order_id, None)

            if not last:
                self.logger.info("撤销报单操作请求响应中......")

    def onErrRtnOrderAction(self, data: dict, error: dict) -> None:
        """
        报单操作错误回报，当执行ReqOrderAction后有字段填写不对之类的CTP报错则通过此接口返回
        :param data: 报单操作
        :param error:
        :return:
        """
        rsp_error_msg = extract_error_msg(error, "撤销报单操作错误")
        if rsp_error_msg:
            self.logger.exception(rsp_error_msg)
            return
        else:
            if data:
                self.logger.info(f"报单操作错误回报: {data}")
                return

    def onRspForQuoteInsert(self, data: dict, error: dict, reqid: SupportsInt, last: bool) -> None:
        """
        询价录入请求响应，当执行ReqForQuoteInsert后有字段填写不对之类的CTP报错则通过此接口返回。
        :param data: 输入的询价
        :param error: 响应信息
        :param reqid: 返回用户操作请求的ID，该ID 由用户在操作请求时指定。
        :param last: 指示该次返回是否为针对nRequestID的最后一次返回。
        :return:
        """
        rsp_error_msg = extract_error_msg(error, "询价录入请求错误")
        if rsp_error_msg:
            self.logger.exception(rsp_error_msg)
            return
        else:
            if data:
                instrument_id: str = data.get("InstrumentID", "")   
                self.logger.info(f"{instrument_id} 询价录入请求成功")

    def onRspUserLogout(self, data: dict, error: dict, reqid: SupportsInt, last: bool) -> None:
        """
        登出请求响应，当执行ReqUserLogout后，该方法被调用。
        :param data: 用户登出请求
        :param error: 响应信息
        :param reqid: 返回用户操作请求的 ID，该 ID 由用户在操作请求时指定。
        :param last: 指示该次返回是否为针对 reqid 的最后一次返回。
        :return: None

        Logout request response. This method is called after ReqUserLogout is executed.
        data: User logout request
        error: Response information
        reqid: Returns the ID of the user operation request, which is specified by the user when making
        the operation request.
        last: Indicates whether this return is the last return for reqid.
        return: None
        """

        rsp_error_msg = extract_error_msg(error, "交易账户登出失败")
        if rsp_error_msg:
            self.logger.exception(rsp_error_msg)
            return

        if data:
            self.login_status = False
            self.logger.info("交易账户：{} 已退出".format(data.get("UserID", "UNKNOWN")))

        if last:
            self.logger.info("释放接口资源......")
            self.release()  # 删除接口对象本身
            self.logger.info("接口资源释放完毕")

    # ===================== 主动函数 =====================
    def connect(self,
                address: str,
                broker_id: str,
                user_id: str,
                password: str,
                auth_code: str,
                app_id: str
                ) -> None:
        """
        连接交易服务器  连接交易服务器
        :param address: 交易服务器地址  Trading server address
        :param user_id:
        :param password:
        :param broker_id:
        :param auth_code:
        :param app_id:
        :return:
        """
        if self.connect_status:
            self.logger.warning("交易服务器已连接!")
            return

        self.address = address
        self.broker_id = broker_id
        self.user_id = user_id
        self.password = password
        self.auth_code = auth_code
        self.app_id = app_id

        # 定义连接的是生产还是评测前置，true:使用生产版本的API false:使用测评版本的API
        # Defines whether the connection is to the production or evaluation version of the API,
        # true: use the production version of the API false: use the evaluation version of the API
        is_production_mode = True

        if not self.connect_status:
            ctp_con_dir: Path = Path.cwd().joinpath("con")

            if not ctp_con_dir.exists():
                ctp_con_dir.mkdir()
            # 消息的状态文件完整路径
            # The full path to the status file for the message
            api_path_str = str(ctp_con_dir) + "/td"
            # 如果没有连接，创建TraderApi实例
            self.logger.info("开始创建TraderApi实例......")
            self.logger.info("尝试创建路径为 {} 的 API".format(api_path_str))

            try:
                # 创建TraderApi实例  Create a TraderApi instance
                # 在 c++ 底层 createFtdcMdApi 函数中自动调用 RegisterSpi 函数注册SPI实例
                self.createFtdcTraderApi(api_path_str.encode("GBK").decode("utf-8"), is_production_mode)
                self.logger.info("createFtdcTraderApi 调用成功")

                # 订阅私有流和公共流。
                # 私有流重传方式
                # THOST_TERT_RESTART: 从本交易日开始重传
                # THOST_TERT_RESUME: 从上次收到的续传
                # THOST_TERT_QUICK: 只传送登录后私有流/公有流的内容
                # 该方法要在Init方法前调用。若不调用则不会收到私有流/公有流的数据。
                self.subscribePrivateTopic(THOST_TERT_QUICK)
                self.subscribePublicTopic(THOST_TERT_QUICK)

                self.registerFront(address)
                self.logger.info("尝试使用地址初始化 API：{}......".format(address))

                self.init()
                self.logger.info("init 调用成功")
            except Exception as e_create:
                self.logger.exception("createFtdcTraderApi 或 init 失败！错误：{}".format(e_create))
                self.logger.exception("createFtdcTraderApi 或 init Traceback: {}".format(traceback.format_exc()))
                return

            self.logger.info("创建TraderApi实例成功")
        else:
            print("已连接，正在尝试身份验证...")
            self.authenticate()

    def authenticate(self) -> None:
        """
        发起授权验证，调用reqAuthenticate
        :return:
        """
        self.logger.info("开始认证......")
        if self.auth_status:
            self.logger.info("已经认证过，跳过认证")
            return

        auth_req: dict = {
            "BrokerID": self.broker_id,
            "UserID": self.user_id,
            "UserProductInfo": self.user_product_info,
            "AuthCode": self.auth_code,
            "AppID": self.app_id
        }

        self.req_id += 1
        self.logger.info("发送认证请求......")
        self.reqAuthenticate(auth_req, self.req_id)

    def login(self) -> None:
        """
        用户登录，调用reqUserLogin
        :return:
        """
        self.logger.info("开始登录......")
        if self.login_status:
            self.logger.info("已经登录过，跳过登录")
            return

        ctp_req: dict = {
            "BrokerID": self.broker_id,
            "UserID": self.user_id,
            "Password": self.password
        }

        self.req_id += 1
        self.logger.info("发送登录请求......")
        self.reqUserLogin(ctp_req, self.req_id)

    def send_order(self, req: OrderRequest) -> str:
        """
        委托下单，调用ReqOrderInsert
        # 报单录入请求，录入错误时对应响应OnRspOrderInsert、OnErrRtnOrderInsert，正确时对应回报OnRtnOrder、OnRtnTrade。
        # 可以录入限价单、市价单、条件单等交易所支持的指令，撤单时使用ReqOrderAction。
        # 不支持预埋单录入，预埋单请使用ReqParkedOrderInsert。
        :param req: 报单录入请求字段
        :return:
        """
        if not self.all_status_ready():
            self.logger.warning(f"网关状态未就绪: connect={self.connect_status}, auth={self.auth_status}, login={self.login_status}, confirmed={self.has_confirmed}")
            return ""

        if not req:
            self.logger.warning("订单请求为空")
            return ""

        if req.offset not in OFFSET_ENUM_TO_CTP:
            self.logger.warning("请选择开平方向")
            return ""

        if req.order_type not in ORDER_TYPE_ENUM_TO_CTP:
            self.logger.warning(f"当前接口不支持该类型的委托 {req.order_type.value}")
            return ""

        self.order_ref += 1

        # 从委托类型映射获取报单价格条件、有效期类型、成交量类型
        tp: tuple = ORDER_TYPE_ENUM_TO_CTP[req.order_type]
        price_type, time_condition, volume_condition = tp

        # 开平标志
        comb_offset_flag = OFFSET_ENUM_TO_CTP.get(req.offset, "")
        # 买卖方向
        direction = DIRECTION_ENUM_TO_CTP.get(req.direction, "")

        order_req: dict = {
            "BrokerID": self.broker_id,
            "InvestorID": self.user_id,
            "InstrumentID": req.instrument_id,
            "OrderRef": str(self.order_ref),
            "UserID": self.user_id,
            "CombOffsetFlag": comb_offset_flag,  # 开平标志
            "CombHedgeFlag": THOST_FTDC_HF_Speculation,  # 投机套保标志，投机
            # "GTDDate": "",  # GTD日期
            "ExchangeID": req.exchange_id.value,  # 交易所代码
            # "InvestUnitID": "",  # 投资单元代码
            # "AccountID": "",  # 投资者帐号
            # "CurrencyID": "",  # 币种代码
            # "ClientID": "",  # 客户代码
            "VolumeTotalOriginal": req.volume,  # 数量
            "MinVolume": 1,  # 最小成交量
            "IsAutoSuspend": 0,  # 自动挂起标志
            "RequestID": self.req_id,  # 请求编号
            "IsSwapOrder": 0,  # 互换单标志
            "OrderPriceType": price_type,  # 报单价格条件，普通限价单的默认参数
            "Direction": direction,  # 买卖方向
            "TimeCondition": time_condition,  # 有效期类型，当日有效
            "VolumeCondition": volume_condition,  # 成交量类型，任意数量
            "ContingentCondition": THOST_FTDC_CC_Immediately,  # 触发条件
            "ForceCloseReason": THOST_FTDC_FCC_NotForceClose,  # 强平原因，非强平
            "LimitPrice": req.price,  # 价格
            # "StopPrice": 0  # 止损价
        }

        self.req_id += 1
        self.logger.info("开始发送委托下单请求......")
        try:
            ret_code: int = self.reqOrderInsert(order_req, self.req_id)
            if ret_code == 0:
                self.logger.info("委托下单请求发送成功")
            else:
                self.logger.exception("委托下单请求发送失败，错误代码：{}".format(ret_code))
                return ""
        except RuntimeError as e:
            self.logger.error("运行时错误！错误：{}".format(e))
            self.logger.error("traceback: {}".format(traceback.format_exc()))

        order_id: str = f"{self.front_id}_{self.session_id}_{self.order_ref}"
        self.logger.info(f"委托下单成功，OrderID: {order_id}")

        # 将订单请求数据推送到事件总线
        order: OrderData = req.create_order_data(order_id)
        if self.gateway.event_bus:
            send_order_event = Event(
                EventType.ORDER_SUBMIT_REQUEST,
                payload={
                    "code": 0,
                    "message": "发布订单委托",
                    "data": {
                        "order_data": order,
                        "instrument_id": req.instrument_id
                    }
                }
            )
            self.gateway.event_bus.publish(send_order_event)
            self.logger.debug(f"已发布订单委托事件: "
                              f"InstrumentID={req.instrument_id}, "
                              f"ExchangeID={req.exchange_id.value}, "
                              f"CombOffsetFlag={comb_offset_flag}, "
                              f"DDirection={direction}, "
                              f"Volume={req.volume}"
                              )

        return order_id

    def cancel_order(self, req: CancelRequest) -> None:
        """
        委托撤单，调用reqOrderAction撤销报单
        :return:
        """
        if not self.all_status_ready():
            return

        if not req:
            return

        front_id, session_id, order_ref = req.order_id.split("_")

        cancel_req: dict = {
            "BrokerID": self.broker_id,
            "InvestorID": self.user_id,
            "OrderRef": order_ref,
            "ExchangeID": req.exchange_id.value,
            "UserID": self.user_id,
            "InstrumentID": req.instrument_id,
            "FrontID": int(front_id),
            "SessionID": int(session_id),
            "ActionFlag": THOST_FTDC_AF_Delete,  # 操作标志
        }

        self.req_id += 1
        self.logger.info("开始发送委托撤单请求......")
        try:
            ret_code: int = self.reqOrderAction(cancel_req, self.req_id)
            if ret_code == 0:
                self.logger.info("委托撤单请求发送成功")
            else:
                self.logger.exception("委托撤单请求发送失败，错误代码：{}".format(ret_code))
                return
        except RuntimeError as e:
            self.logger.error("运行时错误！错误：{}".format(e))
            self.logger.error("traceback: {}".format(traceback.format_exc()))

        cancel_order: CancelRequest = req.create_cancel_order()
        # 将委托撤单请求数据推送到事件总线
        if self.gateway.event_bus:
            cancel_order_event = Event(
                EventType.ORDER_CANCEL_REQUEST,
                payload={
                    "code": 0,
                    "message": "发布委托撤单",
                    "data": cancel_order
                }
            )
            self.gateway.event_bus.publish(cancel_order_event)
            self.logger.debug(f"已发布委托撤单事件: "
                              f"OrderID={req.order_id}, "
                              f"OrderRef={order_ref}, "
                              f"InstrumentID={req.instrument_id}, "
                              f"ExchangeID={req.exchange_id.value}"
                              )

    def query_instrument(self) -> None:
        """
        查询合约
        :return:
        """
        self.req_id += 1
        self.reqQryInstrument({}, self.req_id)

    def query_account(self) -> None:
        """查询资金"""
        self.req_id += 1

        qry_req: dict = {
            "BrokerID": self.broker_id,
            "InvestorID": self.user_id,
            "CurrencyID": Currency.CNY.value
        }
        # 调用请求查询资金账户，响应: onRspQryTradingAccount
        self.reqQryTradingAccount(qry_req, self.req_id)

    def query_position(self) -> None:
        """查询持仓"""
        qry_req: dict = {
            "BrokerID": self.broker_id,
            "InvestorID": self.user_id
        }

        self.req_id += 1
        # 请求查询投资者持仓，对应响应 onRspQryInvestorPosition。
        # CTP系统将持仓明细记录按合约，持仓方向，开仓日期（仅针对上期所和能源所，区分昨仓、今仓）进行汇总。
        self.reqQryInvestorPosition(qry_req, self.req_id)

    def logout(self) -> None:
        """
        登出交易服务器，调用reqUserLogout，对应响应OnRspUserLogout

        Logout
        :return: None
        """
        # 登出请求
        logout_req = {
            "BrokerID": self.broker_id,
            "UserID": self.user_id
        }
        self.req_id += 1
        self.logger.info("开始发送登出交易服务器请求......")
        try:
            ret_code = self.reqUserLogout(logout_req, self.req_id)

            if ret_code == 0:
                self.logger.info("TD 登出请求已发送")
            else:
                self.logger.warning(f"TD 登出请求失败，ret_code: {ret_code}")
        except RuntimeError as e:
            self.logger.error("运行时错误！错误：{}".format(e))
            self.logger.error("traceback: {}".format(traceback.format_exc()))

    def close(self) -> None:
        """
        关闭连接

        Close the connection
        :return: None
        """
        if self.connect_status:
            self.logger.info("关闭连接")
            self.connect_status = False
            self.exit()

    def update_date(self) -> None:
        """
        更新当前日期

        Update current date
        :return: None
        """
        self.current_date = datetime.now().strftime("%Y%m%d")

    def get_order_status_summary(self) -> None:
        """
        获取所有订单状态汇总
        :return:
        """
        self.logger.info("\n" + "=" * 50)
        self.logger.info("订单状态汇总")
        self.logger.info("=" * 50)

        if not self.order_status_map:
            self.logger.info("暂无订单记录")
            return

        for order_id, order_status in self.order_status_map.items():
            status_name = ORDER_STATUS_CTP_TO_ENUM.get(order_status, f"未知状态({order_status})")
            self.logger.info(f"订单号: {order_id} | 状态: {status_name}")

        self.logger.info("=" * 50 + "\n")

    def connect_login_ready(self) -> bool:
        """
        连接和登录是否就绪

        Check connection and login status
        :return: True or False
        """
        if not self.connect_status or not self.login_status:
            self.logger.warning("没有连接或未登录交易服务器")
            return False
        else:
            return True

    def all_status_ready(self) -> bool:
        """
        所有状态是否就绪，包括连接、认证、授权、登录、确认结算单
        :return: True or False
        """
        if not self.connect_status or not self.auth_status or not self.login_status or not self.has_confirmed:
            return False
        else:
            return True
