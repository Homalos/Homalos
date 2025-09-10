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
from pathlib import Path
from typing import SupportsInt

from src.core.base_gateway import BaseGateway
from src.core.constants import Direction
from src.core.event_bus import EventBus
from src.ctp.api import TdApi
from src.ctp.api.ctp_constant import THOST_FTDC_OST_Canceled, THOST_FTDC_OST_AllTraded, \
    THOST_FTDC_OST_PartTradedQueueing, THOST_FTDC_OST_NoTradeQueueing, THOST_FTDC_OST_NoTradeNotQueueing, \
    THOST_TERT_QUICK, THOST_FTDC_D_Buy, THOST_FTDC_D_Sell, THOST_FTDC_OF_CloseToday, THOST_FTDC_HF_Speculation, \
    THOST_FTDC_OPT_LimitPrice, THOST_FTDC_TC_GFD, THOST_FTDC_VC_AV, THOST_FTDC_CC_Immediately, \
    THOST_FTDC_FCC_NotForceClose, THOST_FTDC_AF_Delete
from src.modules.gateway.gateway_const import GatewayConst
from src.modules.gateway.helper import extract_error_msg, get_exchange_name
from src.utils.log import get_logger
from src.utils.utility import prepare_address


class TraderGateway(BaseGateway):

    def __init__(self, event_bus: EventBus = "TraderBus", gateway_name: str = "TraderGateway") -> None:
        super().__init__(event_bus, gateway_name)
        self.gateway_name = gateway_name

        # CTP API相关
        self.td_api: CtpTdApi | None = None

        self.logger = get_logger(__class__.__name__)

    def connect(self, setting: dict) -> None:
        """
        连接交易服务器
        :param setting:
        :return:
        """
        if not self.td_api:
            self.td_api = CtpTdApi(self)

        # 兼容性配置字段处理
        broker_id: str = setting.get("broker_id", "")  # 经纪商代码
        user_id: str = setting.get("user_id", "")  # 用户名
        password: str = setting.get("password", "")  # 密码
        td_address: str = setting.get("td_address", "")  # 交易服务器
        app_id: str = setting.get("appid", "")  # 产品名称
        auth_code: str = setting.get("auth_code", "")  # 授权编码

        # 验证必需字段
        if not all([broker_id, user_id, password, td_address]):
            missing_fields = []
            if not broker_id: missing_fields.append("broker_id")
            if not user_id: missing_fields.append("user_id")
            if not password: missing_fields.append("password")
            if not td_address: missing_fields.append("td_address")
            self.logger.error(f"CTP交易网关连接参数不完整，缺少字段: {missing_fields}")

        td_address = prepare_address(td_address)
        self.td_api.connect(td_address, broker_id, user_id, password, auth_code, app_id)

    def send_order(self, symbol: str, direction: str, price: float, volume: int) -> str:
        """
        委托下单
        :return:
        """
        if not self.td_api or not self.td_api.connect_status or not self.td_api.login_status:
            self.logger.warning("无法发送订单：交易接口未连接、未初始化或未登录交易服务器。")
            return ""
        self.logger.info("正在委托下单...")
        self.logger.info(f"Symbol: {symbol}, Direction: {direction}, Price: {price}, Volume: {volume}")
        return self.td_api.send_order(symbol, direction, price, volume)

    def cancel_order(self, symbol: str) -> None:
        """
        委托撤单
        :return:
        """
        if not self.td_api or not self.td_api.connect_status or not self.td_api.login_status:
            self.logger.warning("无法撤销订单：交易接口未连接、未初始化或未登录交易服务器。")
            return
        self.logger.info(f"Symbol: {symbol}, 正在撤单...")
        self.td_api.cancel_order(symbol)

    def get_order_status_summary(self) -> None:
        """
        获取订单状态汇总
        :return:
        """
        if self.td_api:
            self.td_api.get_order_status_summary()
        else:
            self.logger.warning("交易接口未初始化")

    def logout(self) -> None:
        """
        登出交易服务器
        :return:
        """
        if self.td_api:
            self.td_api.logout()

    def close(self) -> None:
        """
        关闭接口
        :return:
        """
        if self.td_api and self.td_api.connect_status:
            self.td_api.close()


class CtpTdApi(TdApi):
    """
    CTP交易接口
    """
    def __init__(self, gateway: TraderGateway) -> None:
        super().__init__()

        self.gateway: TraderGateway = gateway
        self.gateway_name: str = gateway.gateway_name

        self.logger = get_logger(__class__.__name__)

        self.req_id: int = 0
        self.order_ref: int = 0

        self.connect_status: bool = False
        self.login_status: bool = False
        self.auth_status: bool = False

        self.broker_id: str = ""
        self.user_id: str = ""
        self.password: str = ""
        self.auth_code: str = ""
        self.app_id: str = ""

        self.front_id: int = 0
        self.session_id: int = 0

        # 订单状态跟踪字典  Order Status Tracking Dictionary
        self.order_status_map: dict = {}

        # 订单队列，存储订单ID  An order queue and store the order ID
        self.order_queue: queue.Queue[str] = queue.Queue(maxsize=1000)

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
        self.logger.info("onFrontConnected: 交易服务器连接成功")

        if self.auth_code:
            self.authenticate()  # 调用授权验证方法  Call the authorization verification method
        else:
            self.login()  # 调用登录方法  Calling the login method

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
        self.connect_status = False
        self.login_status = False

        reason_hex = hex(int(reason))  # 错误代码转换成16进制, Error code converted to hexadecimal
        reason_msg = GatewayConst.reason_mapping.get(reason, f"Unknown cause({reason_hex})")
        self.logger.info(f"交易服务器连接断开，原因是：{reason_msg} ({reason_hex})")

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
        rsp_error_msg = extract_error_msg(error, self.onRspAuthenticate.__name__, "交易服务器授权验证失败")
        if rsp_error_msg:
            self.auth_status = False
            self.logger.exception(rsp_error_msg)
        else:
            self.auth_status = True
            self.logger.info("交易服务器授权验证成功")
            self.login()

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
        rsp_error_msg = extract_error_msg(error, self.onRspUserLogin.__name__, "交易服务器登录失败")
        if rsp_error_msg:
            self.login_status = False
            self.logger.exception(rsp_error_msg)
        else:
            self.login_status = True
            self.logger.info("交易服务器登录成功")

            self.front_id = data.get("FrontID")
            self.session_id = data.get("SessionID")

            settlement_req: dict = {
                "BrokerID": self.broker_id,
                "InvestorID": self.user_id
            }
            self.req_id += 1
            self.logger.info("开始确认结算单......")
            # 调用确认结算单方法 Call the settlement confirmation method
            self.reqSettlementInfoConfirm(settlement_req, self.req_id)

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
        rsp_error_msg = extract_error_msg(error, self.onRspSettlementInfoConfirm.__name__,
                                          "结算单确认失败，错误信息")
        if rsp_error_msg:
            self.logger.exception(rsp_error_msg)
        else:
            if last:
                self.logger.info("结算单确认成功")
                # 当结算单确认成功后，将登录成功标志设置为True
                # When the settlement order is confirmed successfully, the login success flag is set to True
                self.login_status = True

                # Next steps
                # print("Start querying all contract information...")
                # self.req_id += 1
                # self.reqQryInstrument({}, self.req_id)
            else:
                self.logger.info("结算单确认中...")

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
        rsp_error_msg = extract_error_msg(error, self.onRspOrderInsert.__name__, "报单录入请求失败")
        if rsp_error_msg:
            self.logger.exception(rsp_error_msg)

            # 验证数据完整性  Verify data integrity
            if not data or "InstrumentID" not in data:
                self.logger.warning("订单插入失败回报数据不完整", error)
                return

            symbol = data.get("InstrumentID")
            # 获取订单数据  Get order data
            order_ref: str = data.get("OrderRef")
            order_id: str = f"{self.front_id}_{self.session_id}_{order_ref}"

            # 获取详细错误信息  Get detailed error information
            print(f"交易订单失败 - Order ID: {order_id}, Symbol: {symbol}", error)
        else:
            # 没有错误，正常返回  No error, return normally
            return

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
        rsp_error_msg = extract_error_msg(error, self.onErrRtnOrderInsert.__name__, "报单录入错误")
        if rsp_error_msg:
            self.logger.exception(rsp_error_msg)
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

        symbol: str = data.get("InstrumentID")
        front_id: int = data.get("FrontID")
        session_id: int = data.get("SessionID")
        order_ref: str = data.get("OrderRef")
        order_id: str = f"{front_id}_{session_id}_{order_ref}"
        status = data.get("OrderStatus")

        if not status:
            self.logger.warning(f"收到不支持的委托状态，委托号：{order_id}")
            return

        # 获取状态名称  Get the status name
        status_name = GatewayConst.order_status_names.get(status, f"Unknown status({status})")
        self.logger.info(f"订单状态更新 - OrderID：{order_id}，状态：{status_name} ({status})")

        # 记录当前订单状态  Record current order status
        old_status = self.order_status_map.get(order_id, "新订单")
        self.order_status_map[order_id] = status

        # 检查是否为撤单状态  Check whether the order is cancelled
        if status == THOST_FTDC_OST_Canceled:
            self.logger.info(f"订单已撤销 - OrderID: {order_id}, Symbol: {symbol}")
            self.logger.info("撤单原因: 系统自动撤单或手动撤单")
        elif status == THOST_FTDC_OST_AllTraded:
            self.logger.info(f"订单全部成交 - OrderID: {order_id}, Symbol: {symbol}")
        elif status == THOST_FTDC_OST_PartTradedQueueing:
            self.logger.info(f"订单部分成交，剩余在队列中 - OrderID: {order_id}, Symbol: {symbol}")
        elif status == THOST_FTDC_OST_NoTradeQueueing:
            self.logger.info(f"订单未成交，在队列中等待 - OrderID: {order_id}, Symbol: {symbol}")
        elif status == THOST_FTDC_OST_NoTradeNotQueueing:
            self.logger.info(f"订单未成交且不在队列中 - OrderID: {order_id}, Symbol: {symbol}")
            self.logger.info("可能原因: 价格超出涨跌停板、资金不足、合约不存在等")

        self.logger.info(f"状态变化: {old_status} -> {status_name}")

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

        # 验证必要的订单系统ID映射
        if "OrderSysID" not in data:
            self.logger.warning(f"成交回报缺少订单系统ID映射: {data.get('OrderSysID', 'N/A')}")
            return

        trade_id = data.get("TradeID")
        order_id: str = data.get("OrderSysID")
        price = data.get("Price")
        volume = data.get("Volume")
        trade_date: str = data.get("TradeDate")
        trade_time: str = data.get("TradeTime")

        self.logger.info(f"onRtnTrade: TradeID: {trade_id}, OrderID: {order_id}, Price: {price}, Volume: {volume}, "
              f"TradeDate: {trade_date}, TradeTime: {trade_time}")

    def onRspOrderAction(self, data: dict, error: dict, reqid: SupportsInt, last: bool) -> None:
        """
        报单操作请求响应，当执行ReqOrderAction后有字段填写不对之类的CTP报错则通过此接口返回

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
        rsp_error_msg = extract_error_msg(error, self.onRspOrderAction.__name__, "报单操作请求失败")
        if rsp_error_msg:
            self.logger.exception(rsp_error_msg)
        else:
            return

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

        rsp_error_msg = extract_error_msg(error, self.onRspUserLogout.__name__, "交易账户登出失败")
        if rsp_error_msg:
            self.logger.exception(rsp_error_msg)
        else:
            self.login_status = False
            self.logger.info("交易账户：{} 已退出".format(data.get("UserID")))

    # ===================== 主动函数 =====================
    def connect(self, address: str, broker_id: str, user_id: str, password: str,  auth_code: str, app_id: str) -> None:
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
        self.broker_id = broker_id
        self.user_id = user_id
        self.password = password
        self.auth_code = auth_code
        self.app_id = app_id

        # 定义连接的是生产还是评测前置，true:使用生产版本的API false:使用测评版本的API
        # Defines whether the connection is to the production or evaluation version of the API,
        # true: use the production version of the API false: use the evaluation version of the API
        is_production_mode = True

        ctp_con_dir: Path = Path.cwd().joinpath("con")

        if not ctp_con_dir.exists():
            ctp_con_dir.mkdir()
        # 消息的状态文件完整路径
        # The full path to the status file for the message
        api_path_str = str(ctp_con_dir) + "/td"
        # 如果没有连接，创建TraderApi实例
        if not self.connect_status:
            self.logger.info("开始创建TraderApi实例......")
            self.logger.info("尝试创建路径为 {} 的 API".format(api_path_str))
            try:
                # 创建TraderApi实例  Create a TraderApi instance
                self.createFtdcTraderApi(api_path_str.encode("GBK").decode("utf-8"), is_production_mode)
                self.logger.info("createFtdcTraderApi 调用成功")
            except Exception as e_create:
                self.logger.exception("createFtdcTraderApi 失败！错误：{}".format(e_create))
                self.logger.exception("createFtdcTraderApi Traceback: {}".format(traceback.format_exc()))
                return
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
            try:
                self.init()
                self.logger.info("init 调用成功。")
            except Exception as e_init:
                self.logger.exception("init 失败！错误：{}".format(e_init))
                self.logger.exception("init Traceback：{}".format(traceback.format_exc()))
                return
            self.logger.info("创建TraderApi实例成功。")
        else:
            print("创建TraderApi实例已经成功，正在尝试身份验证......")
            self.authenticate()

    def authenticate(self) -> None:
        """
        发起授权验证
        :return:
        """
        self.logger.info(f"开始认证......")
        if self.auth_status:
            print("已经认证过，跳过认证")
            return

        auth_req: dict = {
            "UserID": self.user_id,
            "BrokerID": self.broker_id,
            "AuthCode": self.auth_code,
            "AppID": self.app_id
        }

        self.req_id += 1
        self.logger.info(f"发送认证请求，req_id: {self.req_id}")
        self.reqAuthenticate(auth_req, self.req_id)

    def login(self) -> None:
        """
        用户登录
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
        self.logger.info(f"发送登录请求，req_id: {self.req_id}")
        self.reqUserLogin(ctp_req, self.req_id)

    def send_order(self, symbol: str, direction: str, price: float, volume: int) -> str:
        """
        委托下单
        :return:
        """
        self.order_ref += 1
        # 后期考虑优化，将策略中订阅的合约对应交易所缓存起来，避免每次都去查询
        exchange_id = get_exchange_name(symbol)

        if direction.lower() == Direction.BUY_OPEN.value:
            direction_field = THOST_FTDC_D_Buy  # 买卖方向
            comb_offset_flag = '0'  # 开平标志
        elif direction.lower() == Direction.BUY_CLOSE.value:
            direction_field = THOST_FTDC_D_Buy
            comb_offset_flag = '1'
        elif direction.lower() == Direction.SELL_OPEN.value:
            direction_field = THOST_FTDC_D_Sell
            comb_offset_flag = '0'
        elif direction.lower() == Direction.SELL_CLOSE.value:
            direction_field = THOST_FTDC_D_Sell
            comb_offset_flag = '1'
        elif direction.lower() == Direction.BUY_CLOSE_TODAY.value:
            direction_field = THOST_FTDC_D_Buy
            comb_offset_flag = THOST_FTDC_OF_CloseToday
        elif direction.lower() == Direction.SELL_CLOSE_TODAY.value:
            direction_field = THOST_FTDC_D_Sell
            comb_offset_flag = THOST_FTDC_OF_CloseToday
        else:
            self.logger.exception("不支持的买卖方向：{}".format(direction))
            return ""

        ctp_req: dict = {
            "BrokerID": self.broker_id,
            "InvestorID": self.user_id,
            "InstrumentID": symbol,
            "OrderRef": str(self.order_ref),
            "UserID": self.user_id,
            "CombOffsetFlag": comb_offset_flag,  # 开平标志
            "CombHedgeFlag": THOST_FTDC_HF_Speculation,  # 投机套保标志，投机
            "GTDDate": "",  # GTD日期
            "ExchangeID": exchange_id,  # 交易所代码
            "InvestUnitID": "",  # 投资单元代码
            "AccountID": "",  # 投资者帐号
            "CurrencyID": "",  # 币种代码
            "ClientID": "",  # 客户代码
            "VolumeTotalOriginal": volume,  # 数量
            "MinVolume": 1,  # 最小成交量
            "IsAutoSuspend": 0,  # 自动挂起标志
            "RequestID": self.req_id,  # 请求编号
            # "UserForceClose": "",  # 用户强平标志
            "IsSwapOrder": 0,  # 互换单标志
            "OrderPriceType": THOST_FTDC_OPT_LimitPrice,  # 报单价格条件，普通限价单的默认参数
            "Direction": direction_field,  # 买卖方向
            "TimeCondition": THOST_FTDC_TC_GFD,  # 有效期类型，当日有效
            "VolumeCondition": THOST_FTDC_VC_AV,  # 成交量类型，任意数量
            "ContingentCondition": THOST_FTDC_CC_Immediately,  # 触发条件
            "ForceCloseReason": THOST_FTDC_FCC_NotForceClose,  # 强平原因，非强平
            "LimitPrice": price,  # 价格
            "StopPrice": 0  # 止损价
        }

        self.req_id += 1
        try:
            ret_code: int = self.reqOrderInsert(ctp_req, self.req_id)
            if ret_code == 0:
                self.logger.info("委托请求发送成功")
            else:
                self.logger.exception("委托请求发送失败，错误代码：{}".format(ret_code))
                return ""
        except RuntimeError as e:
            self.logger.error("reqOrderInsert 运行时错误！错误：{}".format(e))
            self.logger.error("reqOrderInsert 回溯：{}".format(traceback.format_exc()))

        order_id: str = f"{self.front_id}_{self.session_id}_{self.order_ref}"
        self.logger.info("委托下单成功，OrderID：{}".format(order_id))
        self.order_queue.put(order_id)  # 存入委托号

        return order_id

    def cancel_order(self, symbol: str) -> None:
        """
        委托撤单
        :return:
        """
        front_id, session_id, order_ref = self.order_queue.get().split("_")
        # 后期考虑优化，将策略中订阅的合约对应交易所缓存起来，避免每次都去查询
        exchange_id = get_exchange_name(symbol)

        cancel_req: dict = {
            "BrokerID": self.broker_id,
            "InvestorID": self.user_id,
            "OrderRef": order_ref,
            "ExchangeID": exchange_id,
            "UserID": self.user_id,
            "InstrumentID": symbol,
            "FrontID": int(front_id),
            "SessionID": int(session_id),
            "ActionFlag": THOST_FTDC_AF_Delete,  # 操作标志
        }

        self.req_id += 1
        self.reqOrderAction(cancel_req, self.req_id)

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

        for orderid, status in self.order_status_map.items():
            status_name = GatewayConst.order_status_names.get(status, f"未知状态({status})")
            self.logger.info(f"订单号: {orderid} | 状态: {status_name}")

        self.logger.info("=" * 50 + "\n")

    def logout(self) -> None:
        """
        登出交易服务器，对应响应OnRspUserLogout

        Logout
        :return: None
        """
        self.logger.info("准备登出")
        # 登出请求
        logout_req = {
            "BrokerID": self.broker_id,
            "UserID": self.user_id
        }
        self.req_id += 1

        ret_code = self.reqUserLogout(logout_req, self.req_id)

        if ret_code == 0:
            self.logger.info("reqUserLogout 登出请求已发送")
        else:
            self.logger.warning(f"reqUserLogout 登出请求失败，ret_code: {ret_code}")

    def close(self) -> None:
        """
        关闭连接
        :return:
        """
        if self.connect_status:
            self.exit()
