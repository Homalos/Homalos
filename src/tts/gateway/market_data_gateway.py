#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos_v2
@FileName   : market_data_gateway.
@Date       : 2025/6/28 17:15
@Author     : Donny
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: TTS行情网关
"""
import asyncio
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.config import global_var
from src.config.constant import Exchange
from src.core.event_bus import EventBus
from src.core.gateway import BaseGateway
from src.core.object import ContractData, TickData, SubscribeRequest
from src.tts.api import MdApi
from src.tts.gateway.tts_mapping import EXCHANGE_TTS2VT
from src.util.utility import ZoneInfo, get_folder_path

# 其他常量
MAX_FLOAT = sys.float_info.max             # 浮点数极限值
CHINA_TZ = ZoneInfo("Asia/Shanghai")       # 中国时区

# 合约数据全局缓存字典
symbol_contract_map: dict[str, ContractData] = {}


class MarketDataGateway(BaseGateway):
    """
    TTS行情网关 - 专门负责行情数据处理，用于对接期货TTS柜台的交易接口。
    """
    default_name: str = "TTS_MD"

    default_setting: dict[str, str] = {
        "userid": "",
        "password": "",
        "broker_id": "",
        "md_address": "",
        "appid": "",
        "auth_code": ""
    }

    exchanges: list[str] = list(EXCHANGE_TTS2VT.values())

    def __init__(self, event_bus: EventBus, name: str) -> None:
        """构造函数"""
        super().__init__(event_bus, name)

        self.event_bus: EventBus = event_bus  # Ensure this line is present
        self.query_functions = None
        # 行情API实例
        self.md_api: TtsMdApi | None = None
        self.count: int = 0

        # 基础属性
        self.instrument_exchange_map: dict[str, str] = {}
        self.setting: dict = {}

        # 连接状态管理
        self._running: bool = True
        self.heartbeat_task: Optional[asyncio.Task] = None

    @staticmethod
    def _prepare_address(address: str) -> str:
        """
        如果没有方案，则帮助程序会在前面添加 tcp:// 作为前缀。
        """
        if not any(address.startswith(scheme) for scheme in ["tcp://", "ssl://", "socks://"]):
            return "tcp://" + address
        return address


    def connect(self, setting: dict) -> None:
        """
        连接行情接口
        """
        if not self.md_api:
            self.md_api = TtsMdApi(self)

        userid: str = setting["userid"]
        password: str = setting["password"]
        broker_id: str = setting["broker_id"]
        md_address: str = self._prepare_address(setting["md_address"])

        self.md_api.connect(md_address, userid, password, broker_id)

    def subscribe(self, req: SubscribeRequest) -> None:
        """
        订阅行情
        """
        if not self.md_api or not self.md_api.connect_status:
            self.write_log("无法订阅行情：行情接口未连接或未初始化。")
            return
        self.md_api.subscribe(req)

    def close(self) -> None:
        """
        关闭接口
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


class TtsMdApi(MdApi):
    """
    TTS行情接口
    """
    def __init__(self, gateway: MarketDataGateway) -> None:
        super().__init__()

        self.gateway: MarketDataGateway = gateway
        self.gateway_name: str = gateway.name

        self.reqid: int = 0

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
        """
        self.gateway.write_log("行情服务器连接成功")
        self.login()

    def onFrontDisconnected(self, reason: int) -> None:
        """
        服务器连接断开回报
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
        self.gateway.write_log("行情服务器连接断开，原因：{}".format(reason))


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
            self.gateway.write_log("行情服务器登录成功")

            for symbol in self.subscribed:
                self.subscribeMarketData(symbol)
        else:
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
            return

        self.gateway.write_error("行情订阅失败", error)

    def onRtnDepthMarketData(self, data: dict) -> None:
        """
        行情数据推送
        """
        # 过滤没有时间戳的异常行情数据
        if not data["UpdateTime"]:
            return

        symbol: str = data["InstrumentID"]
        contract: ContractData = symbol_contract_map.get(symbol, None)
        if not contract:
            return

        # 对大商所的交易日字段取本地日期
        if not data["ActionDay"] or contract.exchange == Exchange.DCE:
            date_str: str = self.current_date
        else:
            date_str = data["ActionDay"]
        # todo: 这块和CTP有点不同，后期考虑以哪个为准统一
        timestamp: str = f"{date_str} {data['UpdateTime']}.{int(data['UpdateMillisec']/100)}"
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
        """
        tts_req: dict = {
            "UserID": self.userid,
            "Password": self.password,
            "BrokerID": self.broker_id
        }
        self.reqid += 1
        self.reqUserLogin(tts_req, self.reqid)

    def subscribe(self, req: SubscribeRequest) -> None:
        """
        订阅行情
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
        """
        if self.connect_status:
            self.exit()

    def update_date(self) -> None:
        """
        更新当前日期
        """
        self.current_date = datetime.now().strftime("%Y%m%d")


def adjust_price(price: float) -> float:
    """将异常的浮点数最大值（MAX_FLOAT）数据调整为0"""
    if price == MAX_FLOAT:
        price = 0
    return price
