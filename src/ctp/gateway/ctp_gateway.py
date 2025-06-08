import asyncio
import json
import os
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path
from time import sleep
from typing import cast

from src.config.constants import Status, Exchange, Direction, OrderType
from src.config.global_var import product_info, instrument_exchange_id_map
from src.config.path import GlobalPath
from src.util.file_helper import write_json_file
from src.util.i18n import _
from src.util.utility import ZoneInfo, get_folder_path
from .ctp_gateway_helper import ctp_build_contract
from .ctp_mapping import STATUS_CTP2VT, DIRECTION_VT2CTP, DIRECTION_CTP2VT, ORDERTYPE_VT2CTP, ORDERTYPE_CTP2VT, \
    OFFSET_VT2CTP, OFFSET_CTP2VT, EXCHANGE_CTP2VT, PRODUCT_CTP2VT
from ..api import (
    MdApi,
    TdApi,
    THOST_FTDC_AF_Delete,
    THOST_FTDC_CC_Immediately,
    THOST_FTDC_FCC_NotForceClose,
    THOST_FTDC_HF_Speculation,
)
from ...config import global_var
from ...core.base_gateway import BaseGateway
from ...core.event import (
    TickEvent, OrderUpdateEvent, TradeUpdateEvent,
    AccountUpdateEvent, PositionUpdateEvent, ContractInfoEvent
)
# Import EventEngine and specific event types
from ...core.event_engine import EventEngine
from ...core.object import ContractData, SubscribeRequest, OrderRequest, CancelRequest, TickData, PositionData, \
    OrderData, AccountData, TradeData, GatewayConnectionStatus
from ...gateway_helper import del_num

# 其他常量
MAX_FLOAT = sys.float_info.max             # 浮点数极限值
CHINA_TZ = ZoneInfo("Asia/Shanghai")       # 中国时区

# 合约数据全局缓存字典
symbol_contract_map: dict[str, ContractData] = {}


class CtpGateway(BaseGateway):
    """
    用于对接期货CTP柜台的交易接口。
    """

    default_name: str = "CTP"

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

    def __init__(self, gateway_name: str, event_engine: EventEngine) -> None:
        super().__init__(gateway_name, event_engine)
        self.query_functions = None
        self.td_api: CtpTdApi | None = None
        self.md_api: CtpMdApi | None = None
        self.count: int = 0

        # 加载合约交易所映射文件
        self.instrument_exchange_map: dict = {}
        map_file_path = ""
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            # 构建到 instrument_exchange_id.json 的相对路径
            map_file_path = os.path.join(current_dir, "..", "..", "config", "project_files", "instrument_exchange_id.json")
            map_file_path = os.path.normpath(map_file_path) # 规范化路径

            if os.path.exists(map_file_path):
                with open(map_file_path, "r", encoding="utf-8") as f:
                    self.instrument_exchange_map = json.load(f)
                self.write_log(f"成功从 {map_file_path} 加载合约交易所映射。")
            else:
                self.write_log(f"警告：合约交易所映射文件未找到于 {map_file_path}。回退逻辑可能受限。")
        except Exception as e:
            self.write_log(f"加载合约交易所映射文件 {map_file_path} 时出错: {e}")

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

    def connect_md(self, setting: dict) -> None:
        """
        只连接行情接口
        :param setting:
        :return:
        """
        if not self.md_api:
            self.md_api = CtpMdApi(self)

        userid: str = setting["userid"]
        password: str = setting["password"]
        broker_id: str = setting["broker_id"]
        md_address: str = self._prepare_address(setting["md_address"])

        self.md_api.connect(md_address, userid, password, broker_id)

    def connect_td(self, setting: dict) -> None:
        """
        只连接交易接口
        :param setting:
        :return:
        """
        if not self.td_api:
            self.td_api = CtpTdApi(self)

        userid: str = setting["userid"]  # 用户名
        password: str = setting["password"]  # 密码
        broker_id: str = setting["broker_id"]  # 经纪商代码
        td_address: str = setting["td_address"]  # 交易服务器
        appid: str = setting["appid"]  # 产品名称
        auth_code: str = setting["auth_code"]  # 授权编码

        td_address = self._prepare_address(td_address)
        self.td_api.connect(td_address, userid, password, broker_id, auth_code, appid)

        self.init_query() # Querying account/positions is TD related

    def connect(self, setting: dict) -> None:
        """
        连接行情和交易接口（保持兼容性，推荐分别调用connect_md和connect_td）
        :param setting:
        :return:
        """
        self.write_log(_("注意：CtpGateway.connect() 同时连接行情和交易。推荐分别调用 connect_md() 和 connect_td() 以实现更清晰的职责分离。"))
        self.connect_md(setting)
        self.connect_td(setting)

    def subscribe(self, req: SubscribeRequest) -> None:
        """
        订阅行情
        :param req:
        :return:
        """
        self.write_log(f"GATEWAY-DEBUG: CtpGateway.subscribe called for {req.symbol}.")

        if not self.md_api:
            self.write_log("GATEWAY-DEBUG: self.md_api is None. Cannot subscribe.", "ERROR")
            return

        self.write_log(f"GATEWAY-DEBUG: md_api.connect_status is {self.md_api.connect_status}.")

        if not self.md_api.connect_status:
            self.write_log("GATEWAY-DEBUG: md_api is not connected. Cannot subscribe.", "ERROR")
            return

        self.write_log("GATEWAY-DEBUG: Forwarding subscribe request to CtpMdApi.")
        self.md_api.subscribe(req)

    def send_order(self, req: OrderRequest) -> str:
        """
        委托下单
        :param req:
        :return:
        """
        if not self.td_api or not self.td_api.connect_status:
            self.write_log(_("无法发送订单：交易接口未连接或未初始化。"))
            return ""
        return self.td_api.send_order(req)

    def cancel_order(self, req: CancelRequest) -> None:
        """
        委托撤单
        :param req:
        :return:
        """
        if not self.td_api or not self.td_api.connect_status:
            self.write_log(_("无法撤销订单：交易接口未连接或未初始化。"))
            return
        self.td_api.cancel_order(req)

    def query_account(self) -> None:
        """
        查询资金
        :return:
        """
        if not self.td_api or not self.td_api.connect_status:
            self.write_log(_("无法查询资金：交易接口未连接或未初始化。"))
            return
        self.td_api.query_account()

    def query_position(self) -> None:
        """
        查询持仓
        :return:
        """
        if not self.td_api or not self.td_api.connect_status:
            self.write_log(_("无法查询持仓：交易接口未连接或未初始化。"))
            return
        self.td_api.query_position()

    def close(self) -> None:
        """
        关闭接口
        :return:
        """
        if self.td_api and self.td_api.connect_status:
            self.td_api.close()
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
        log_msg = f"{_(msg)}，{_('代码')}：{error_id}，{_('信息')}：{error_msg}"
        self.write_log(log_msg)

    def process_timer_event(self, event):
        """定时事件处理"""
        self.count += 1
        if self.count < 2:
            return
        self.count = 0

        func = self.query_functions.pop(0)
        func()
        self.query_functions.append(func)

        self.md_api.update_date()

    def init_query(self) -> None:
        """
        初始化查询任务
        :return:
        """
        if not self.td_api:
            self.write_log("交易接口未初始化，跳过查询任务初始化。")
            return
        self.count: int = 0
        self.query_functions: list = [self.query_account, self.query_position]

    # --- Override BaseGateway on_xxx methods to publish events ---
    def on_tick(self, tick: TickData) -> None:
        """行情推送"""
        if self.event_engine:
            asyncio.run_coroutine_threadsafe(self.event_engine.put(TickEvent(data=tick)), self.main_loop)
        else:
            super().on_tick(tick) # Fallback or if engine is optional

    def on_trade(self, trade: TradeData) -> None:
        """成交推送"""
        if self.event_engine:
            asyncio.run_coroutine_threadsafe(self.event_engine.put(TradeUpdateEvent(data=trade)), self.main_loop)
        else:
            super().on_trade(trade)

    def on_order(self, order: OrderData) -> None:
        """委托推送"""
        if self.event_engine:
            asyncio.run_coroutine_threadsafe(self.event_engine.put(OrderUpdateEvent(data=order)), self.main_loop)
        else:
            super().on_order(order)

    def on_position(self, position: PositionData) -> None:
        """持仓推送"""
        if self.event_engine:
            asyncio.run_coroutine_threadsafe(self.event_engine.put(PositionUpdateEvent(data=position)), self.main_loop)
        else:
            super().on_position(position)

    def on_account(self, account: AccountData) -> None:
        """资金推送"""
        if self.event_engine:
            asyncio.run_coroutine_threadsafe(self.event_engine.put(AccountUpdateEvent(data=account)), self.main_loop)
        else:
            super().on_account(account)

    def on_contract(self, contract: ContractData) -> None:
        """合约推送"""
        if self.event_engine:
            asyncio.run_coroutine_threadsafe(self.event_engine.put(ContractInfoEvent(data=contract)), self.main_loop)
        else:
            super().on_contract(contract)

    # on_log is handled by BaseGateway modification if event_engine is passed to super()


class CtpMdApi(MdApi):
    """
    CTP行情接口
    """

    def __init__(self, gateway: CtpGateway) -> None:
        super().__init__()

        self.gateway: CtpGateway = gateway
        self.gateway_name: str = gateway.gateway_name

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
        self.gateway.write_log(_("行情服务器连接成功"))
        self.gateway.on_gateway_status(GatewayConnectionStatus.CONNECTED, "行情服务器前置已连接")
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
        self.connect_status = False # Also update connect_status as CTP might not auto-reconnect if true
        
        # 转换原因代码为16进制并给出对应解释
        reason_hex = hex(reason)
        reason_text = ""
        if reason == 0x1001:
            reason_text = "网络读失败"
        elif reason == 0x1002:
            reason_text = "网络写失败"  
        elif reason == 0x2001:
            reason_text = "接收心跳超时"
        elif reason == 0x2002:
            reason_text = "发送心跳失败"
        elif reason == 0x2003:
            reason_text = "收到错误报文"
            
        self.gateway.write_log(_("行情服务器连接断开，原因：{} ({}:{})").format(reason, reason_hex, reason_text))
        self.gateway.on_gateway_status(GatewayConnectionStatus.DISCONNECTED, f"行情服务器连接已断开，原因: {reason}")
        
        # 记录当前断开时间，用于判断是否需要防止过于频繁重连
        self.last_disconnect_time = time.time()

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
            self.gateway.write_log(_("行情服务器登录成功"))
            self.gateway.on_gateway_status(GatewayConnectionStatus.CONNECTED, "行情服务器登录成功")

            # 登录成功后尝试订阅已记录的合约
            if self.subscribed:
                self.gateway.write_log(f"登录成功，开始订阅之前记录的 {len(self.subscribed)} 个合约")
                for symbol in self.subscribed:
                    self.gateway.write_log(f"尝试订阅之前记录的合约: {symbol}")
                    try:
                        result = self.subscribeMarketData(symbol)
                        if result == 0:
                            self.gateway.write_log(f"合约 {symbol} 订阅请求已发送")
                        else:
                            self.gateway.write_log(f"合约 {symbol} 订阅请求发送失败，错误码: {result}", "ERROR")
                    except Exception as e:
                        self.gateway.write_log(f"订阅合约 {symbol} 时发生异常: {e}", "ERROR")
            else:
                self.gateway.write_log("登录成功，但没有需要订阅的合约")
        else:
            self.gateway.write_error(_("行情服务器登录失败"), error)
            self.gateway.on_gateway_status(GatewayConnectionStatus.ERROR, f"行情服务器登录失败: {error.get('ErrorMsg', '未知错误')}")

    def onRspError(self, error: dict, reqid: int, last: bool) -> None:
        """
        请求报错回报
        :param error:
        :param reqid:
        :param last:
        :return:
        """
        self.gateway.write_error(_("行情接口报错"), error)

    def onRspSubMarketData(self, data: dict, error: dict, reqid: int, last: bool) -> None:
        """
        订阅行情回报
        :param data:
        :param error:
        :param reqid:
        :param last:
        :return:
        """
        symbol = data.get("InstrumentID", "N/A")
        error_id = error.get("ErrorID", 0) if error else 0
        error_msg = error.get("ErrorMsg", "") if error else ""
        
        # 无论成功失败都用明显格式记录
        self.gateway.write_log(f"===== 收到订阅回报: 合约={symbol}, 错误ID={error_id}, 消息='{error_msg}' =====", "INFO")
        
        # 详细记录原始数据，帮助诊断
        self.gateway.write_log(f"订阅回报原始数据: data={data}, error={error}, reqid={reqid}, last={last}", "INFO")

        if error_id != 0:
            self.gateway.write_log(f"合约 {symbol} 行情订阅失败: {error_msg}", "ERROR")
        else:
            self.gateway.write_log(f"合约 {symbol} 行情订阅成功。")
            # 尝试手动触发一个测试请求，可能帮助激活行情
            self.req_id += 1
            self.gateway.write_log(f"发送测试请求 ID: {self.req_id}", "INFO")
            # 此处故意留空，只发送请求ID

    def onRtnDepthMarketData(self, data: dict) -> None:
        """
        行情数据推送
        :param data:
        :return:
        """
        # 使用非常明显的格式记录行情接收
        self.gateway.write_log(f"******************************************", "INFO")
        self.gateway.write_log(f"******** 收到行情数据推送回调 ********", "INFO")
        self.gateway.write_log(f"******************************************", "INFO")
        
        # 详细记录原始数据
        self.gateway.write_log(f"收到原始行情数据回调，原始数据: {data}", "INFO")
        
        # 增加更明显的行情数据接收日志
        instrument_id_log = data.get("InstrumentID", "UNKNOWN")
        last_price_log = data.get("LastPrice", 0)
        update_time_log = data.get("UpdateTime", "N/A")
        
        # 使用INFO级别记录行情数据，确保在日志中可见
        self.gateway.write_log(f"==== 收到行情数据: 合约={instrument_id_log}, 价格={last_price_log}, 时间={update_time_log} ====", "INFO")
        
        # 保留原来的调试日志，但降低级别
        self.gateway.write_log(f"CTP原始行情到达: 合约={instrument_id_log}, 最新价={last_price_log}, 时间={update_time_log}", "DEBUG")

        # 过滤没有时间戳的异常行情数据
        if not data.get("UpdateTime"):
            self.gateway.write_log(f"过滤掉没有时间戳的异常行情数据: {instrument_id_log}", "WARNING")
            return

        instrument_id: str = data["InstrumentID"]
        exchange_enum: Exchange | None = None
        # TickData.name 将默认为 instrument_id。完整的合约名称通过 ContractInfoEvent 提供。
        contract_name: str = instrument_id

        # 1. 优先尝试从 gateway 的 instrument_exchange_map (来自JSON文件) 获取交易所
        json_exchange_str = self.gateway.instrument_exchange_map.get(instrument_id)
        if json_exchange_str:
            try:
                exchange_enum = cast(Exchange, Exchange[json_exchange_str]) # 将"CZCE"之类的字符串转换为Exchange.CZCE
                self.gateway.write_log(f"CtpMdApi: Determined exchange for {instrument_id} as {exchange_enum} from JSON map ('{json_exchange_str}').", "DEBUG")
            except KeyError:
                self.gateway.write_log(f"CtpMdApi: Invalid exchange string '{json_exchange_str}' in JSON map for {instrument_id}. Trying CTP ExchangeID.", "WARNING")
        else:
            self.gateway.write_log(f"CtpMdApi: InstrumentID {instrument_id} not found in JSON map. Trying CTP ExchangeID.", "DEBUG")

        # 2. 如果 JSON map 未能确定交易所，则尝试使用 CTP 提供的 ExchangeID
        if not exchange_enum:
            ctp_exchange_id_value = data.get("ExchangeID")
            if ctp_exchange_id_value and ctp_exchange_id_value != "":
                exchange_str_from_ctp = str(ctp_exchange_id_value)
                exchange_enum = EXCHANGE_CTP2VT.get(exchange_str_from_ctp)
                if exchange_enum:
                    self.gateway.write_log(f"CtpMdApi: Determined exchange for {instrument_id} as {exchange_enum} from CTP ExchangeID ('{exchange_str_from_ctp}').", "DEBUG")
                else:
                    self.gateway.write_log(f"CtpMdApi: Unknown CTP ExchangeID '{exchange_str_from_ctp}' for {instrument_id}. Available CTP_IDs: {list(EXCHANGE_CTP2VT.keys())}", "WARNING")
            else:
                self.gateway.write_log(f"CtpMdApi: CTP ExchangeID is empty or not provided for {instrument_id}.", "DEBUG")

        # 最后检查：如果在所有回退之后仍无法确定交换，则删除勾选。
        if not exchange_enum:
            self.gateway.write_log(f"CtpMdApi: CRITICAL: Unable to determine exchange for {instrument_id} after all fallbacks. Dropping tick. JSON_Map_Exchange: '{json_exchange_str}', CTP_ID_was: '{data.get('ExchangeID')}'")
            return

        # 对大商所的交易日字段取本地日期
        if not data["ActionDay"] or (exchange_enum == Exchange.DCE if exchange_enum else False): # Check resolved exchange
            date_str: str = self.current_date
        else:
            date_str = data["ActionDay"]

        timestamp: str = f"{date_str} {data['UpdateTime']}.{data['UpdateMillisec']}"
        dt: datetime = datetime.strptime(timestamp, "%Y%m%d %H:%M:%S.%f")
        dt = dt.replace(tzinfo=CHINA_TZ)

        tick: TickData = TickData(
            symbol=instrument_id,
            exchange=exchange_enum,         # Use determined/fallback exchange
            datetime=dt,
            name=contract_name,             # name is now instrument_id
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

    def onRspUserLogout(self, data: dict, error: dict, reqid: int, last: bool):
        """
        登出请求响应，当 ReqUserLogout 后，该方法被调用。
        :param data: 用户登出请求
        :param error: 响应信息
        :param reqid: 返回用户操作请求的 ID，该 ID 由用户在操作请求时指定。
        :param last: 指示该次返回是否为针对 reqid 的最后一次返回。
        :return: 无
        """
        self.gateway.write_log(_("行情账户：{} 已登出").format(data['UserID']))

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
            self.gateway.on_gateway_status(GatewayConnectionStatus.CONNECTING, "行情接口尝试连接中...")
            path: Path = get_folder_path(self.gateway_name.lower())
            self.createFtdcMdApi((str(path) + "\\Md").encode("GBK").decode("utf-8"))  # 加上utf-8编码，否则中文路径会乱码

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
        self.gateway.write_log(f"MD-API-DEBUG: CtpMdApi.subscribe called for {req.symbol}.")
        symbol: str = req.symbol

        # 过滤重复的订阅
        if symbol in self.subscribed:
            self.gateway.write_log(f"合约 {symbol} 已在订阅列表中，跳过重复订阅")
            return

        if self.login_status:
            self.gateway.write_log(f"行情网关已登录，立即订阅合约: {req.symbol}")
            try:
                # CTP API需要接收单个字符串，而不是字符串列表
                result = self.subscribeMarketData(req.symbol)
                if result == 0:
                    self.gateway.write_log(f"合约 {req.symbol} 订阅请求已发送，返回值: {result}")
                else:
                    self.gateway.write_log(f"合约 {req.symbol} 订阅请求发送失败，错误码: {result}", "ERROR")
                    # 添加更具体的错误代码解释
                    error_explanations = {
                        -1: "网络连接失败",
                        -2: "未处于登录状态",
                        -3: "流控限制"
                    }
                    if result in error_explanations:
                        self.gateway.write_log(f"错误原因: {error_explanations[result]}", "ERROR")
            except Exception as e:
                self.gateway.write_log(f"订阅时发生异常: {e}", "ERROR")
                import traceback
                self.gateway.write_log(traceback.format_exc(), "ERROR")
        else:
            self.gateway.write_log(f"行情网关未登录，将合约 {req.symbol} 加入待订阅列表")
        
        # 无论是否成功发送，都将合约加入到订阅列表中
        # 如果当前未登录，将在登录成功后尝试订阅
        self.subscribed.add(req.symbol)

    def close(self) -> None:
        """
        关闭连接
        :return:
        """
        if self.connect_status:
            self.gateway.on_gateway_status(GatewayConnectionStatus.DISCONNECTED, "行情接口已关闭")
            self.exit()
            self.connect_status = False
            self.login_status = False

    def update_date(self) -> None:
        """
        更新当前日期
        :return:
        """
        self.current_date = datetime.now().strftime("%Y%m%d")


class CtpTdApi(TdApi):
    """
    CTP交易接口
    """

    def __init__(self, gateway: CtpGateway) -> None:
        super().__init__()

        self.gateway: CtpGateway = gateway
        self.gateway_name: str = gateway.gateway_name

        self.req_id: int = 0
        self.order_ref: int = 0

        self.connect_status: bool = False
        self.login_status: bool = False
        self.auth_status: bool = False
        self.login_failed: bool = False
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
        self.gateway.write_log(_("交易服务器连接成功"))
        self.gateway.on_gateway_status(GatewayConnectionStatus.CONNECTED, "交易服务器前置已连接")
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
        self.auth_status = False # Reset auth status on disconnect
        self.connect_status = False # Also update connect_status
        self.gateway.write_log(_("交易服务器连接断开，原因：{}").format(reason))
        self.gateway.on_gateway_status(GatewayConnectionStatus.DISCONNECTED, f"交易服务器连接已断开，原因: {reason}")

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
            self.gateway.write_log(_("交易服务器授权验证成功"))
            # Don't send CONNECTED here, login is next. If auth is part of "connected", this might change.
            self.login()
        else:
            if error.get('ErrorID') == 63: # Specific error code for auth failure
                self.auth_failed = True
            self.gateway.write_error(_("交易服务器授权验证失败"), error)
            self.gateway.on_gateway_status(GatewayConnectionStatus.ERROR, f"交易服务器授权失败: {error.get('ErrorMsg', '未知错误')}")

    def onRspUserLogin(self, data: dict, error: dict, reqid: int, last: bool) -> None:
        """
        用户登录请求回报，当执行 ReqUserLogin 后，该方法被调用。
        :param data: 用户登录应答
        :param error: 响应信息
        :param reqid: 返回用户操作请求的 ID，该 ID 由用户在操作请求时指定。
        :param last: 指示该次返回是否为针对 reqid 的最后一次返回。
        :return: 无
        """
        if not error.get("ErrorID"):
            self.front_id = data["FrontID"]
            self.session_id = data["SessionID"]
            self.login_status = True
            global_var.td_login_success = True
            self.gateway.write_log(_("交易服务器登录成功"))
            self.gateway.on_gateway_status(GatewayConnectionStatus.CONNECTED, "交易服务器登录成功")
            ctp_req: dict = {"BrokerID": self.broker_id, "InvestorID": self.userid}
            self.req_id += 1
            self.reqSettlementInfoConfirm(ctp_req, self.req_id)
        else:
            self.login_failed = True
            self.gateway.write_error(_("交易服务器登录失败"), error)
            self.gateway.on_gateway_status(GatewayConnectionStatus.ERROR, f"交易服务器登录失败: {error.get('ErrorMsg', '未知错误')}")

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
                self.gateway.write_log(_("查询产品成功！"))
        else:
            self.gateway.write_error(_("查询产品失败"), error)

    def onRspOrderInsert(self, data: dict, error: dict, reqid: int, last: bool) -> None:
        """
        委托下单失败回报
        :param data:
        :param error:
        :param reqid:
        :param last:
        :return:
        """
        order_ref: str = data["OrderRef"]
        orderid: str = f"{self.front_id}_{self.session_id}_{order_ref}"

        symbol: str = data["InstrumentID"]
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
        self.gateway.on_order(order)

        self.gateway.write_error(_("交易委托失败"), error)

    def onRspOrderAction(self, data: dict, error: dict, reqid: int, last: bool) -> None:
        """
        委托撤单失败回报
        :param data:
        :param error:
        :param reqid:
        :param last:
        :return:
        """
        self.gateway.write_error(_("交易撤单失败"), error)

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
            error_message = _("结算单确认失败，错误信息为：{}，错误代码为：{}").format(error.get('ErrorMsg', 'N/A'), error.get('ErrorID', 'N/A'))
            self.gateway.write_error(error_message, error)
        else:
            if last:
                self.gateway.write_log(_("结算信息确认成功"))
                # 当结算单确认成功后，将登录成功标志设置为True (这条语句之前用户添加过，但通常登录成功在onRspUserLogin中处理)
                global_var.td_login_success = True # 确认此标志的正确管理位置
                
                self.gateway.write_log(_("开始查询所有合约信息..."))
                # 由于流控，单次查询可能失败，通过while循环持续尝试，直到成功发出请求
                retries = 0
                max_retries = 5
                while retries < max_retries:
                    self.req_id += 1
                    n: int = self.reqQryInstrument({}, self.req_id)
                    if not n:
                        break
                    else:
                        self.gateway.write_log(f"reqQryInstrument failed with {n}, retrying in 1s ({retries + 1}/{max_retries})")
                        sleep(1)
                        retries += 1
                if retries == max_retries:
                    self.gateway.write_log("reqQryInstrument failed after max retries.")

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
        # 仅当有数据时才处理，但要继续检查 'last' 标志
        if data:
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

        # 'last' 标志表示查询响应流的结束。
        # 即使最后一个数据包是空的，也应始终检查此块。
        if last:
            for position in self.positions.values():
                self.gateway.on_position(position)

            self.positions.clear()
            self.gateway.write_log("持仓查询回报处理完毕。")

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
                self.gateway.write_log(_("查询持仓明细完成"))
            if data is None or data['Volume'] == 0:
                return
        else:
            self.gateway.write_error(_("查询持仓明细失败"), error)

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
        合约查询回报
        """
        self.gateway.write_log(f"GATEWAY-DEBUG: 收到合约查询回报 - reqid: {reqid}, last: {last}")
        self.gateway.write_log(f"GATEWAY-DEBUG: 错误信息: {error}")
        
        if error and error.get("ErrorID", 0) != 0:
            self.gateway.write_log(f"GATEWAY-DEBUG: 合约查询失败: {error.get('ErrorMsg', '未知错误')}", "ERROR")
            return

        try:
            if data:
                self.gateway.write_log(f"GATEWAY-DEBUG: 收到合约数据: {data}")
                
                # 使用ctp_build_contract创建合约对象
                contract = ctp_build_contract(data, self.gateway_name)
                if contract:
                    self.gateway.write_log(f"GATEWAY-DEBUG: 创建合约对象: {contract}")
                    self.gateway.on_contract(contract)
                    symbol_contract_map[contract.symbol] = contract
                
                # 更新exchange_id_map
                if not data.get("InstrumentID", "").isdigit() and len(data.get("InstrumentID", "")) <= 6:
                    self.instrument_exchange_id_map[data.get("InstrumentID", "")] = data.get("ExchangeID", "")

            if last:
                self.contract_inited = True
                self.gateway.write_log("GATEWAY-DEBUG: 合约查询完成")
                
                # 处理缓存的订单和成交数据
                for order_data in self.order_data:
                    self.onRtnOrder(order_data)
                self.order_data.clear()

                for trade_data in self.trade_data:
                    self.onRtnTrade(trade_data)
                self.trade_data.clear()
                
                # 保存合约映射文件
                try:
                    write_json_file(GlobalPath.instrument_exchange_id_filepath, self.instrument_exchange_id_map)
                    self.gateway.write_log("GATEWAY-DEBUG: 合约交易所映射已保存到文件")
                except Exception as e:
                    self.gateway.write_log(f"GATEWAY-DEBUG: 保存合约交易所映射失败: {e}", "ERROR")
                
                self.gateway.write_log("GATEWAY-DEBUG: 开始查询账户资金")
                self.query_account()
        except Exception as e:
            self.gateway.write_log(f"GATEWAY-DEBUG: 处理合约数据时出错: {e}", "ERROR")
            import traceback
            self.gateway.write_log(traceback.format_exc(), "ERROR")

    def query_instrument(self) -> None:
        """
        查询合约信息
        """
        self.gateway.write_log("GATEWAY-DEBUG: 开始查询合约信息")
        self.reqid += 1
        self.reqQryInstrument({}, self.reqid)

    def onRtnOrder(self, data: dict) -> None:
        """
        委托更新推送，报单发出后有状态变动则通过此接口返回。公有流
        :param data:
        :return:
        """
        if not self.contract_inited:
            self.order_data.append(data)
            return

        symbol: str = data["InstrumentID"]
        contract: ContractData = symbol_contract_map[symbol]

        front_id: int = data["FrontID"]
        session_id: int = data["SessionID"]
        order_ref: str = data["OrderRef"]
        orderid: str = f"{front_id}_{session_id}_{order_ref}"

        status: Status = STATUS_CTP2VT.get(data["OrderStatus"], None)
        if not status:
            self.gateway.write_log(_("收到不支持的委托状态，委托号：{}").format(orderid))
            return

        timestamp: str = f"{data['InsertDate']} {data['InsertTime']}"
        dt: datetime = datetime.strptime(timestamp, "%Y%m%d %H:%M:%S")
        dt = dt.replace(tzinfo=CHINA_TZ)

        tp: tuple = (data["OrderPriceType"], data["TimeCondition"], data["VolumeCondition"])
        order_type: OrderType = ORDERTYPE_CTP2VT.get(tp)
        if not order_type:
            self.gateway.write_log(_("收到不支持的委托类型，委托号：{}").format(orderid))
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

    def onRtnTrade(self, data: dict) -> None:
        """
        成交数据推送，报单发出后有成交则通过此接口返回。私有流
        :param data:
        :return:
        """
        if not self.contract_inited:
            self.trade_data.append(data)
            return

        symbol: str = data["InstrumentID"]
        contract: ContractData = symbol_contract_map[symbol]

        orderid: str = self.sysid_orderid_map[data["OrderSysID"]]

        timestamp: str = f"{data['TradeDate']} {data['TradeTime']}"
        dt: datetime = datetime.strptime(timestamp, "%Y%m%d %H:%M:%S")
        dt = dt.replace(tzinfo=CHINA_TZ)

        trade: TradeData = TradeData(
            symbol=symbol,
            exchange=contract.exchange,
            orderid=orderid,
            tradeid=data["TradeID"],
            direction=DIRECTION_CTP2VT[data["Direction"]],
            offset=OFFSET_CTP2VT[data["OffsetFlag"]],
            price=data["Price"],
            volume=data["Volume"],
            datetime=dt,
            gateway_name=self.gateway_name
        )
        self.gateway.on_trade(trade)

    def onRspForQuoteInsert(self, data: dict, error: dict, reqid: int, last: bool) -> None:
        """询价请求回报"""
        if not error["ErrorID"]:
            symbol: str = data["InstrumentID"]
            msg: str = f"{symbol}询价请求发送成功"
            self.gateway.write_log(msg)
        else:
            self.gateway.write_error("询价请求发送失败", error)

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
            self.gateway.write_error(_("CtpTdApi：OnRspQryInstrumentCommissionRate 查询失败。错误 ID：{}").format(error.get('ErrorID', 'N/A')), error)
            return
        
        # 增加对data 和 data['InstrumentID']的有效性检查
        if data is None or not data.get("InstrumentID"):
            # 如果是最后一条回报但数据无效，可能需要记录一下
            if last:
                self.gateway.write_log(_("CtpTdApi：OnRspQryInstrumentCommissionRate 收到无效或空的合约手续费数据（最后一条）。ReqID: {}").format(reqid))
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
            self.gateway.write_error(_("报单操作请求失败"), error)
        else:
            self.gateway.write_log(_('报单操作请求成功！'))

    def onRspUserLogout(self, data: dict, error: dict, reqid: int, last: bool):
        """
        登出请求响应，当执行ReqUserLogout后，该方法被调用。
        :param data: 用户登出请求
        :param error: 响应信息
        :param reqid: 返回用户操作请求的 ID，该 ID 由用户在操作请求时指定。
        :param last: 指示该次返回是否为针对 reqid 的最后一次返回。
        :return: 无
        """
        self.gateway.write_log(_('交易账户：{} 已登出').format(data['UserID']))

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
            self.gateway.on_gateway_status(GatewayConnectionStatus.CONNECTING, "交易接口尝试连接中...")
            path: Path = get_folder_path(self.gateway_name.lower())
            api_path_str = str(path) + "\\Td"
            self.gateway.write_log(_("CtpTdApi：尝试创建路径为 {} 的 API").format(api_path_str))
            try:
                self.createFtdcTraderApi(api_path_str.encode("GBK").decode("utf-8"))
                self.gateway.write_log(_("CtpTdApi：createFtdcTraderApi调用成功。"))
            except Exception as e_create:
                self.gateway.write_log(_("CtpTdApi：createFtdcTraderApi 失败！错误：{}").format(e_create))
                self.gateway.write_log(_("CtpTdApi：createFtdcTraderApi 回溯：{}").format(traceback.format_exc()))
                return

            self.subscribePrivateTopic(0)
            self.subscribePublicTopic(0)

            self.registerFront(address)
            self.gateway.write_log(_("CtpTdApi：尝试使用地址初始化 API：{}...").format(address))
            try:
                self.init()
                self.gateway.write_log(_("CtpTdApi：init 调用成功。"))
            except Exception as e_init:
                self.gateway.write_log(_("CtpTdApi：初始化失败！错误：{}").format(e_init))
                self.gateway.write_log(_("CtpTdApi：初始化回溯：{}").format(traceback.format_exc()))
                return

            self.connect_status = True
        else:
            self.gateway.write_log(_("CtpTdApi：已连接，正在尝试身份验证。"))
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
            self.gateway.write_log(_("请选择开平方向"))
            return ""

        if req.type not in ORDERTYPE_VT2CTP:
            self.gateway.write_log(_("当前接口不支持该类型的委托{}").format(req.type.value))
            return ""

        exchange: Exchange = req.exchange
        if not exchange:
            self.gateway.write_log(f"不支持的交易所：{req.exchange}")
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
            self.gateway.write_log(_("委托请求发送失败，错误代码：{}").format(n))
            return ""

        orderid: str = f"{self.front_id}_{self.session_id}_{self.order_ref}"
        order: OrderData = req.create_order_data(orderid, self.gateway_name)
        self.gateway.on_order(order)

        return order.ho_orderid     # Changed from ho_orderid to ho_orderid

    def cancel_order(self, req: CancelRequest) -> None:
        """
        委托撤单
        :param req:
        :return:
        """
        exchange: Exchange = req.exchange
        if not exchange:
            self.gateway.write_log(f"不支持的交易所：{req.exchange}")
            return

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
            self.gateway.write_log(_('产品：{}'.format(product)))
            for instrument in all_instrument:
                if product == del_num(instrument):
                    symbol = instrument
                    break
            self.gateway.write_log(_('合约：{}'.format(symbol)))
            if product != del_num(symbol):
                self.gateway.write_log(_('这里不符！'))
                continue

            ctp_req: dict = {
                "BrokerID": self.broker_id,
                "InvestorID": self.userid,
                "InstrumentID": symbol
            }
            self.gateway.write_log(_('开始查询手续费...'))
            while True:
                self.req_id += 1
                n: int = self.reqQryInstrumentCommissionRate(ctp_req, self.req_id)
                if not n:  # n是0时，表示请求成功
                    break
                else:
                    self.gateway.write_log(_("CtpTdApi：reqQryInstrumentCommissionRate，代码为 {}，正在查询手续费...")
                                           .format(n))
                    sleep(1)

    def close(self) -> None:
        """
        关闭连接
        :return:
        """
        if self.connect_status:
            self.gateway.on_gateway_status(GatewayConnectionStatus.DISCONNECTED, "交易接口已关闭")
            self.exit()
            self.connect_status = False
            self.login_status = False


def adjust_price(price: float) -> float:
    """
    将异常的浮点数最大值（MAX_FLOAT）数据调整为0
    :param price:
    :return:
    """
    if price == MAX_FLOAT:
        price = 0
    return price
