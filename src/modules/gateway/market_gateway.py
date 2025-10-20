#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : market_gateway.py
@Date       : 2025/9/9 16:49
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 行情网关，专门负责行情数据处理
"""
import traceback
from datetime import datetime
from pathlib import Path
from queue import Queue
from typing import Any, SupportsInt, Optional

from src.core.base_gateway import BaseGateway
from src.core.constants import ErrorReason, Exchange, SubscribeAction
from src.core.event import Event, EventType
from src.core.event_bus import EventBus
from src.core.object import SubscribeRequest, ContractData, TickData
from src.core.pack_payload import PackPayload
from src.ctp.api import MdApi
from src.modules.gateway.gateway_const import REASON_MAPPING, symbol_contract_map, CHINA_TZ
from src.modules.gateway.gateway_helper import extract_error_msg, build_tick_data
from src.utils.log import get_logger
from src.utils.utility import prepare_address


class MarketGateway(BaseGateway):

    def __init__(
            self,
            event_bus: EventBus,
            gateway_name: str = "MarketGateway"
    ) -> None:
        super().__init__(event_bus, gateway_name)
        self.gateway_name = gateway_name
        self.md_api: Optional[CtpMdApi] = None
        self.logger = get_logger(self.__class__.__name__)
        
        # 设置网关事件处理器
        if self.event_bus:
            self._setup_gateway_event_handlers()

    def _setup_gateway_event_handlers(self) -> None:
        """设置网关事件处理器"""
        # 订阅行情订阅请求事件
        self.event_bus.subscribe(EventType.MARKET_SUBSCRIBE_REQUEST, self._handle_market_subscribe_request)
        self.logger.info(f"{self.gateway_name} 网关事件处理器已注册")
    
    def _handle_market_subscribe_request(self, event: Event) -> None:
        """
        处理行情订阅请求事件（带登录状态检查和错误处理）
        
        Args:
            event: 订阅请求事件，payload支持两种格式:
                   1. 单合约: {"instrument_id": "合约代码", "action": "subscribe/unsubscribe"}
                   2. 批量: {"instruments": ["合约1", "合约2", ...], "action": "subscribe/unsubscribe"}
        """
        try:
            # 步骤1：检查网关登录状态
            if not self.md_api or not self.md_api.login_status:
                self.logger.warning("行情网关未登录，拒绝订阅请求")
                self.logger.info("提示：请等待行情网关登录完成后再尝试订阅")
                return
            
            # 步骤2：解析订阅请求
            payload: dict = event.payload
            action: SubscribeAction = payload.get("data", {}).get("action", SubscribeAction.SUBSCRIBE)
            instruments: list[str] = payload.get('data', {}).get("instruments", [])

            if not instruments:
                self.logger.warning("收到空的订阅请求，已忽略")
                return
            
            self.logger.info(f"收到订阅请求: {len(instruments)} 个合约, 操作: {action}")
            
            # 步骤3：执行订阅操作
            # 注意：action 是字符串（枚举的 value），需要与枚举的 value 比较
            if action == SubscribeAction.SUBSCRIBE.value:
                success_count = 0
                failed_list = []
                
                for index, inst_id in enumerate(instruments, 1):
                    try:
                        # 验证合约代码格式
                        if not inst_id or not isinstance(inst_id, str):
                            self.logger.warning(f"无效的合约代码: {inst_id}")
                            failed_list.append(inst_id)
                            continue
                        
                        # 创建订阅请求
                        req = SubscribeRequest(instrument_id=inst_id)
                        self.subscribe(req)
                        success_count += 1
                        
                        # 每10个合约输出一次进度
                        if index % 10 == 0:
                            self.logger.info(f"订阅进度: {index}/{len(instruments)} 个合约...")
                    
                    except Exception as e:
                        self.logger.error(f"✗ 订阅合约 {inst_id} 失败: {e}")
                        failed_list.append(inst_id)
                
                # 输出订阅结果统计
                if failed_list:
                    self.logger.warning(f"订阅完成: 成功 {success_count}/{len(instruments)}, 失败 {len(failed_list)} 个")
                    self.logger.warning(f"失败合约列表: {failed_list}")
                else:
                    self.logger.info(f"所有合约订阅完成: 成功 {success_count}/{len(instruments)} 个")
                
            elif action == SubscribeAction.UNSUBSCRIBE.value:
                # CTP不支持取消订阅，只记录日志
                self.logger.debug(f"收到取消订阅请求(CTP不支持): {len(instruments)} 个合约")
            else:
                self.logger.warning(f"未知的订阅操作: {action}")
        
        except Exception as e:
            self.logger.error(f"处理订阅请求异常: {e}", exc_info=True)
            # 发送告警事件（如果有告警管理器）
            from src.core.event import EventType

            self.event_bus.publish(Event.alarm(
                payload = {
                    "message": f"行情订阅请求处理失败: {str(e)}",
                    "data": {
                        "alarm_type": "subscription_error",
                        "severity": "error",
                        "details": {"error": str(e)}
                    }
                },
                source=self.__class__.__name__
            ))

    def connect(self, setting: dict[str, Any]) -> None:
        """
        连接行情服务器

        Connect to the market server
        :param setting: 登录配置信息 Login configuration information
        :return:
        """
        # 兼容性配置字段处理
        md_address = setting.get("md_address", "")  # 行情服务器地址
        broker_id = setting.get("broker_id", "")  # 经纪商代码
        user_id = setting.get("user_id", "")  # 用户名
        password = setting.get("password", "")  # 密码

        # 参数验证
        if not all([md_address, broker_id, user_id, password]):
            self.logger.error("缺少必需的连接参数")

        md_address = prepare_address(md_address)

        try:
            # 创建API实例
            if not self.md_api:
                self.md_api = CtpMdApi(self)
            # 连接行情服务器
            self.md_api.connect(md_address, broker_id, user_id, password)
        except Exception as e:
            self.logger.exception(f"连接失败: {e}")
            if self.md_api:
                self.md_api.close()

    def subscribe(self, req: SubscribeRequest) -> None:
        """订阅行情"""
        if self.md_api:
            self.md_api.subscribe(req.instrument_id)
        else:
            self.logger.error("行情API未初始化，无法订阅行情")

    def logout(self) -> None:
        """
        登出
        :return:
        """
        if self.md_api:
            self.md_api.logout()

    def close(self) -> None:
        """
        关闭接口
        :return:
        """
        if self.md_api:
            self.md_api.close()

    def update_date(self) -> None:
        """
        更新当前日期
        :return:
        """
        if self.md_api:
            self.md_api.update_date()


class CtpMdApi(MdApi):

    def __init__(self, gateway: MarketGateway):
        super().__init__()
        self.logger = get_logger(self.__class__.__name__)
        self.gateway: MarketGateway = gateway  # 行情网关
        self.gateway_name: str = gateway.gateway_name  # 行情网关名称
        self.req_id: int = 0  # 请求ID
        self.address: str = ""  # 服务器地址 Server address
        self.broker_id: str = ""  # 经纪公司代码
        self.user_id: str = ""  # 用户代码
        self.password: str = ""  # 密码
        self.user_product_info = ""  # 用户端产品信息 User product information

        self.connect_status: bool = False  # 连接状态
        self.login_status: bool = False  # 登录状态

        self.current_date: str = datetime.now().strftime("%Y%m%d")  # 当前自然日
        self.tick_queue: Queue[TickData] = Queue()

    # ===================== 回调函数 =====================
    def onFrontConnected(self) -> None:
        """
        行情服务器连接成功响应
        当客户端与交易托管系统建立起通信连接时（还未登录前），该方法被调用。本方法在完成初始化后调用，可以在其中完成用户登录任务。

        Response for successful connection to the market information server

        This method is called when the client establishes a communication connection with the trading escrow system
        (before logging in). This method is called after initialization is complete and can be used to complete
        the user login task.
        :return: None
        """
        self.connect_status = True  # 设置连接状态为已连接
        self.logger.info("行情服务器连接成功，开始登录......")
        self.login()  # 调用登录方法, Calling the login method

    def onFrontDisconnected(self, reason: SupportsInt) -> None:
        """
        行情服务器连接断开响应

        当客户端与交易托管系统通信连接断开时，该方法被调用。
        当发生这个情况后，API会自动重新连接，客户端可不做处理。
        自动重连地址，可能是原来注册的地址，也可能是系统支持的其它可用的通信地址，它由程序自动选择。
        注:重连之后需要重新登录。6.7.9及以后版本中，断线自动重连的时间间隔为固定1秒。
        :param reason: 错误代号，连接断开原因，为10进制值，因此需要转成16进制后再参照下列代码：
                0x1001（4097） 网络读失败。
                0x1002（4098） 网络写失败。
                0x2001（8193） 接收心跳超时。接收心跳超时。前置每53s会给一个心跳报文给api，如果api超过120s未收到任何新数据，
                则认为网络异常，断开连接
                0x2002（8194） 发送心跳失败。api每15s会发送一个心跳报文给前置，如果api检测到超过40s没发送过任何新数据，则认为网络异常，
                断开连接
                0x2003 收到错误报文
        :return: None

        Response to disconnection from the market server

        This method is called when the client loses communication with the trading escrow system.
        When this happens, the API automatically reconnects, and the client does not need to take any action.
        The automatic reconnection address may be the previously registered address or another supported address,
        which is automatically selected by the program.
        Note: You will need to log in again after reconnecting. In versions 6.7.9 and later,
        the automatic reconnection interval is fixed at 1 second.
        reason: Error code, indicating the reason for the disconnection. This value is in decimal,
        so it must be converted to hexadecimal before referring to the following codes:
                0x1001(4097) Network read failure.
                0x1002(4098) Network write failure.
                0x2001(8193) Heartbeat reception timeout. Heartbeat reception timeout. The frontend sends a heartbeat
                message to the API every 53 seconds. If the API does not receive any new data for more than 120 seconds,
                it considers the network abnormality and disconnects.
                0x2002(8194) Heartbeat transmission failure. Failed to send heartbeat. The API sends a heartbeat
                message to the front-end every 15 seconds. If the API detects that no new data has been sent for more
                than 40 seconds, it will consider the network abnormal and disconnect.
                0x2003 Error message received
        reason: Reason for failure (int value)
        return: None
        """
        self.connect_status = False
        self.login_status = False

        reason_hex: str = hex(int(reason))  # 错误代码转换成16进制字符串
        reason_msg: ErrorReason = REASON_MAPPING.get(reason_hex, ErrorReason.REASON_UNKNOWN)
        self.logger.info(f"行情服务器连接断开，原因是：{reason_msg.value} ({reason_hex})")

    def onRspUserLogin(self, data: dict, error: dict, reqid: SupportsInt, last: bool) -> None:
        """
        登录请求响应，当ReqUserLogin后，该方法被调用。

        :param data: 用户登录应答
        :param error: 响应信息
        :param reqid: 返回用户操作请求的ID，该ID 由用户在操作请求时指定。
        :param last: 指示该次返回是否为针对nRequestID的最后一次返回。
        :return: None

        Login request response. This method is called after ReqUserLogin.
        data: User login response
        error: Response information
        reqid: Returns the ID of the user operation request, which is specified by the user when making
        the operation request.
        last: Indicates whether this is the last return for nRequestID.
        return: None
        """
        rsp_error_msg = extract_error_msg(error, "行情服务器登录请求失败")
        if rsp_error_msg:
            self.login_status = False
            self.logger.exception(rsp_error_msg)

            if self.gateway.event_bus:
                payload = {
                    "code": 1,
                    "message": "行情服务器登录失败",
                    "data": {}
                }
                self.gateway.event_bus.publish(Event(EventType.MD_GATEWAY_LOGIN, payload=payload))
                self.logger.info("已发布 MD_GATEWAY_LOGIN 事件")
            return
        else:
            self.login_status = True
            self.logger.info("行情服务器登录请求成功")
            self.update_date()
            if self.gateway.event_bus:
                payload = {
                    "code": 0,
                    "message": "行情服务器登录成功",
                    "data": {}
                }
                self.gateway.event_bus.publish(Event(EventType.MD_GATEWAY_LOGIN, payload=payload))
                self.logger.info("已发布 MD_GATEWAY_LOGIN 事件")

    def onRspError(self, error: dict, reqid: SupportsInt, last: bool) -> None:
        """
        请求报错响应，针对用户请求的出错通知。

        :param error: 响应信息
        :param reqid: 返回用户操作请求的ID，该ID 由用户在操作请求时指定。
        :param last: 指示该次返回是否为针对nRequestID的最后一次返回。
        :return: None

        Request error response, error notification for user request.

        error: Response information
        reqid: Returns the ID of the user operation request, which is specified by the user when making
        the operation request.
        last: Indicates whether this is the last return for nRequestID.
        return: None
        """
        rsp_error_msg = extract_error_msg(error, "请求报错")
        if rsp_error_msg:
            self.logger.exception(rsp_error_msg)
            return
        else:
            self.logger.info("请求报错响应", error)

    def onRspSubMarketData(self, data: dict, error: dict, reqid: SupportsInt, last: bool) -> None:
        """
        订阅市场行情响应
        订阅行情应答，调用SubscribeMarketData后，通过此接口返回。

        :param data: 指定的合约
        :param error: 响应信息
        :param reqid: 返回用户操作请求的ID，该ID 由用户在操作请求时指定。
        :param last: 指示该次返回是否为针对nRequestID的最后一次返回。
        :return: None

        Subscribe to market information response
        The response to subscribing to market information is returned through this interface after
        calling SubscribeMarketData.

        data: contract
        error: Response information
        reqid: Returns the ID of the user operation request, which is specified by the user when making
        the operation request.
        last: Indicates whether this is the last return for nRequestID.
        return: None
        """
        rsp_error_msg = extract_error_msg(error, "市场行情订阅失败")
        if rsp_error_msg:
            self.logger.exception(rsp_error_msg)
            return
        else:
            if data and "InstrumentID" in data:
                instrument_id = data.get("InstrumentID", "UNKNOWN")
                self.logger.debug(f"返回订阅 {instrument_id} 响应")

    def onRtnDepthMarketData(self, data: dict) -> None:
        """
        深度行情通知，当SubscribeMarketData订阅行情后，行情通知由此推送。

        :param data: 深度行情
        :return: None

        In-depth market notifications. When SubscribeMarketData subscribes to the market,
        market notifications will be pushed here.

        data: In-depth market information
        return: None
        """
        # 此处要判断是否无效数据，例如非交易时间段的数据，避免无效数据推送给上层
        if data:
            # 过滤没有时间戳的异常行情数据
            # Filter out abnormal market data without timestamps
            if not data.get("UpdateTime"):
                self.logger.debug("跳过没有时间戳的市场行情数据")
                return

            instrument_id: str = data.get("InstrumentID", "UNKNOWN")
            # 过滤还没有收到合约数据前的行情推送(没有交易过的数据)
            contract: ContractData | None = symbol_contract_map.get(instrument_id)
            if not contract:
                return

            # 对大商所的交易日字段取本地日期
            if not data["ActionDay"] or contract.exchange_id == Exchange.DCE:
                date_str: str = self.current_date
            else:
                date_str = data["ActionDay"]

            timestamp_str: str = f"{date_str} {data.get('UpdateTime')}.{data.get('UpdateMillisec')}"
            timestamp: datetime = datetime.strptime(timestamp_str, "%Y%m%d %H:%M:%S.%f").replace(tzinfo=CHINA_TZ)
            # 构建系统内的tick行情数据结构
            tick: TickData = build_tick_data(data, contract, timestamp)

            self.logger.debug(f"市场行情数据接收: {tick.instrument_id} @ {tick.update_time} "
                  f"LastPrice={tick.last_price}")

            self.gateway.event_bus.publish(
                Event.tick(
                payload=PackPayload.success(message="推送深度市场行情成功", data=tick),
                source=self.__class__.__name__
            ))

    def onRspUserLogout(self, data: dict, error: dict, reqid: SupportsInt, last: bool):
        """
        登出请求响应，当 ReqUserLogout 后，该方法被调用。
        :param data: 用户登出请求
        :param error: 响应信息
        :param reqid: 返回用户操作请求的 ID，该 ID 由用户在操作请求时指定。
        :param last: 指示该次返回是否为针对 reqid 的最后一次返回。
        :return: 无
        """
        rsp_error_msg = extract_error_msg(error, "行情账户登出失败")
        if rsp_error_msg:
            self.logger.exception(rsp_error_msg)
            return

        if last and data:
            self.logger.info("行情账户：{} 已登出".format(data.get("UserID", "UNKNOWN")))
            self.logger.info("释放接口资源......")
            self.release()  # 删除接口对象本身
            self.logger.info("接口资源释放完毕")

    # ===================== 主动函数 =====================
    def connect(self, address: str, broker_id: str, user_id: str, password: str) -> None:
        """
        连接行情服务器

        :param address: 行情服务器地址
        服务器地址的格式为：“protocol://ipaddress:port”
        如：“tcp://127.0.0.1:17001”。“tcp”代表传输协议，“127.0.0.1”代表服务器地址。“17001”代表行情端口号。
        SSL前置格式：ssl://192.168.0.1:41205
        TCP前置IPv4格式：tcp://192.168.0.1:41205
        TCP前置IPv6格式：tcp6://fe80::20f8:aabb:7d59:887d:35001
        :param broker_id: 经纪公司代码
        :param user_id: 用户代码
        :param password: 密码
        :return: None

        Connect to the market server

        address: Market server address
        The server address format is "protocol://ipaddress:port"
        For example: "tcp://127.0.0.1:17001." "tcp" represents the transport protocol,
        "127.0.0.1" represents the server address, and "17001" represents the market port number.
        SSL prefix format: ssl://192.168.0.1:41205
        TCP prefix format: tcp://192.168.0.1:41205
        TCP prefix format: tcp://192.168.0.1:41205
        TCP prefix format: tcp6://fe80::20f8:aabb:7d59:887d:35001
        broker_id: Brokerage Company Code
        user_id: User Code
        password: password
        return: None
        """
        if self.connect_status:
            self.logger.warning("行情服务器已连接!")
            return

        self.address = address
        self.broker_id = broker_id
        self.user_id = user_id
        self.password = password

        # 是否使用UDP行情
        # Whether to use UDP quotes
        is_using_udp = False

        # 是否使用组播行情(组播行情只能在内网中使用，需要咨询所连接的系统是否支持组播行情。)

        # Whether to use multicast market information (Multicast market information can only be used in the intranet.
        # You need to check whether the connected system supports multicast market information.)
        is_multicast = False

        # 选在连接的是生产还是评测前置，True:使用生产版本的API False:使用测评版本API

        # Select whether to connect to the production or evaluation frontend,
        # True: use the production version of the API False: use the evaluation version of the API
        is_production_mode = True

        # 指定con文件目录来存贮交易托管系统发布消息的状态。默认值代表当前目录。
        # Specifies the con file directory to store the status of the transaction custody system's published messages.
        # The default value represents the current directory.
        ctp_con_dir: Path = Path.cwd().joinpath("con")

        if not ctp_con_dir.exists():
            ctp_con_dir.mkdir()

        # 消息的状态文件完整路径
        # The full path to the status file for the message
        api_path_str = str(ctp_con_dir) + "/md"
        # 如果没有连接，创建MdApi实例
        self.logger.info("开始创建MdApi实例......")
        self.logger.info("尝试创建路径为 {} 的 API".format(api_path_str))
        try:
            # 加上utf-8编码，否则中文路径会乱码
            # Add utf-8 encoding, otherwise the Chinese path will be garbled
            # 在 c++ 底层 createFtdcMdApi 函数中自动调用 RegisterSpi 函数注册SPI实例
            self.createFtdcMdApi(api_path_str.encode("GBK").decode("utf-8"), is_using_udp, is_multicast,
                                 is_production_mode)
            self.logger.info("createFtdcMdApi 调用成功。")

            # 设置交易托管系统的网络通讯地址，交易托管系统拥有多个通信地址，用户可以注册一个或多个地址。
            # 如果注册多个地址则使用最先建立TCP连接的地址。

            # Set the network communication address of the transaction hosting system.
            # The transaction hosting system has multiple communication addresses,
            # and users can register one or more addresses.
            # If multiple addresses are registered, the address that first establishes a TCP connection is used.
            self.registerFront(address)
            self.logger.info("尝试使用地址初始化 API：{}...".format(address))
            # 初始化运行环境,只有调用后,接口才开始发起前置的连接请求。
            # Initialize the operating environment. Only after the call,
            # the interface starts to initiate the pre-connection request.
            self.init()
            self.logger.info("init 调用成功。")

        except Exception as e:
            self.logger.exception("createFtdcMdApi或init 失败！错误：{}".format(e))
            self.logger.exception("createFtdcMdApi或init Traceback: {}".format(traceback.format_exc()))
            return

        self.logger.info("创建MdApi实例成功")

    def login(self) -> None:
        """
        用户登录

        User login
        :return: None
        """
        if not self.connect_status:
            self.logger.warning("请先连接行情服务器再登录！")
            return

        # 用户登录请求
        # User login request
        login_req: dict = {
            # BrokerID: 开启行情身份校验功能后，该字段必需正确填写

            # After turning on the market identity verification function, this field must be filled in correctly
            "BrokerID": self.broker_id,
            # 操作员代码，后续请求中的investorid需要属于该操作员的组织架构下；开启行情身份校验功能后，该字段必需正确填写

            # Operator code. The investorid in subsequent requests must belong to the operator's organizational
            # structure. After the market identity verification function is enabled, this field must be filled in correctly.
            "UserID": self.user_id,
            # 密码
            "Password": self.password,
            # 客户端的产品信息，如软件开发商、版本号等
            # CTP后台用户事件中的用户登录事件所显示的用户端产品信息取自ReqAuthentication接口里的UserProductInfo，而非ReqUserLogin里的。

            # Client product information, such as software developer, version number, etc.
            # The user-side product information displayed in the user login event in the CTP background user event
            # is taken from the UserProductInfo in the ReqAuthentication interface, rather than the ReqUserLogin.
            "UserProductInfo": self.user_product_info
        }

        self.req_id += 1
        # 用户登录请求，对应响应OnRspUserLogin。目前行情登陆不校验账号密码。
        # 自CTP交易系统升级6.6.2版本后，后台支持对用户登录行情前置进行身份校验。若启用该功能后，登录行情前置时要求当前交易日该IP
        # 已成功登录过交易系统，且发起登录行情的请求中必须正确填写BrokerID和UserID，与登录交易的信息保持一致。
        # 不填、填错或该IP未成功登录过交易系统，则校验不通过，会提示“CTP: 不合法登录”；若不启用，则无需验证，可直接发起登录。

        # User login request, corresponding to the response OnRspUserLogin. Currently,
        # market login does not verify the account and password.
        # Since the CTP trading system was upgraded to version 6.6.2, the backend supports identity verification
        # before users log in to the market. If this feature is enabled, the login process requires that the IP
        # address has successfully logged into the trading system on the current trading day. The BrokerID and
        # UserID in the request to initiate the market login must be correctly entered and consistent with the
        # information used to log in to the trading. If these are missing, incorrectly entered, or the IP address
        # has not successfully logged into the trading system, the verification will fail and a "CTP: Illegal Login"
        # message will be displayed. If this feature is not enabled, no verification is required and login can be
        # initiated directly.
        ret_code = self.reqUserLogin(login_req, self.req_id)

        # 0，代表成功。
        # -1，表示网络连接失败；
        # -2，表示未处理请求超过许可数；
        # -3，表示每秒发送请求数超过许可数。

        # 0 indicates success.
        # -1 indicates a network connection failure.
        # -2 indicates the number of unprocessed requests exceeds the permitted number.
        # -3 indicates the number of requests sent per second exceeds the permitted number.
        if ret_code == 0:
            self.logger.info("CTP行情API回调: CtpMdApi - reqUserLogin 调用成功。")
        else:
            self.logger.warning(f"CTP行情API回调: CtpMdApi - reqUserLogin 调用失败，ret_code: {ret_code}")

    def subscribe(self, symbol: str) -> None:
        """
        订阅行情，调用subscribeMarketData

        Subscribe to Quotes
        :return: None
        """
        if not self.connect_login_status():
            return

        if not symbol:
            self.logger.warning("合约为空，跳过订阅")
            return

        self.logger.debug(f"发送订阅 {symbol} 请求...")
        try:
            ret_code = self.subscribeMarketData(symbol)
            # 0，代表成功。
            # -1，表示网络连接失败；
            # -2，表示未处理请求超过许可数；
            # -3，表示每秒发送请求数超过许可数。

            # 0 indicates success.
            # -1 indicates a network connection failure.
            # -2 indicates the number of unprocessed requests exceeds the permitted number.
            # -3 indicates the number of requests sent per second exceeds the permitted number.
            if ret_code == 0:
                self.logger.info(f"订阅 {symbol} 请求已发送")
            else:
                self.logger.exception(f"订阅请求失败 {symbol}，返回代码={ret_code}")
        except Exception as e:
            self.logger.exception("初始化失败！错误：{}".format(e))
            self.logger.exception("初始化 backtrace: {}".format(traceback.format_exc()))

    def logout(self):
        """
        登出行情服务器，对应响应OnRspUserLogout

        Logout
        :return: None
        """
        if not self.login_status:
            self.logger.info("已登出，无需再次登出")
            return

        # 登出请求
        logout_req = {
            "BrokerID": self.broker_id,
            "UserID": self.user_id
        }
        self.req_id += 1
        self.logger.info("开始发送登出行情服务器请求......")
        try:
            ret_code = self.reqUserLogout(logout_req, self.req_id)

            if ret_code == 0:
                self.logger.info("MD 登出请求已发送")
            else:
                self.logger.warning(f"MD 登出请求失败，ret_code: {ret_code}")
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
            self.connect_status = False
            self.exit()
            self.logger.info("关闭连接")

    def update_date(self) -> None:
        """
        更新当前日期

        Update current date
        :return: None
        """
        self.current_date = datetime.now().strftime("%Y%m%d")

    def connect_login_status(self) -> bool:
        """
        检查连接和登录状态

        Check connection and login status
        :return: True or False
        """
        if not self.connect_status or not self.login_status:
            self.logger.warning("没有连接或未登录行情服务器")
            return False
        else:
            return True
