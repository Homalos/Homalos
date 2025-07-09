#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos_v2
@FileName   : order_trading_gateway
@Date       : 2025/6/28 17:15
@Author     : Donny
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: TTS订单交易网关
"""
import json
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path
from time import sleep

from src.config import global_var
from src.config.constant import Offset, Status, Exchange, Direction, OrderType
from src.config.global_var import product_info, instrument_exchange_id_map
from src.config.path import GlobalPath
from src.core.event_bus import EventBus
from src.core.gateway import BaseGateway
from src.core.object import ContractData, PositionData, OrderData, AccountData, TradeData, OrderRequest, CancelRequest
from src.tts.api import TdApi, THOST_FTDC_HF_Speculation, THOST_FTDC_CC_Immediately, THOST_FTDC_FCC_NotForceClose, \
    THOST_FTDC_TC_GFD, THOST_FTDC_VC_AV, THOST_FTDC_OPT_LimitPrice, THOST_FTDC_TC_IOC, THOST_FTDC_VC_CV, \
    THOST_FTDC_AF_Delete
from src.tts.gateway.tts_gateway_helper import tts_build_contract
from src.tts.gateway.tts_mapping import EXCHANGE_TTS2VT, DIRECTION_TTS2VT, OFFSET_TTS2VT, ORDERTYPE_TTS2VT, \
    STATUS_TTS2VT, OFFSET_VT2TTS, ORDERTYPE_VT2TTS, EXCHANGE_VT2TTS, DIRECTION_VT2TTS
from src.util.file_helper import write_json_file
from src.util.utility import ZoneInfo, get_folder_path, del_num

# 其他常量
MAX_FLOAT = sys.float_info.max
CHINA_TZ = ZoneInfo("Asia/Shanghai")

# 合约数据全局缓存字典
symbol_contract_map: dict[str, ContractData] = {}


class OrderTradingGateway(BaseGateway):
    """
    用于对接期货TTS柜台的交易接口。
    """
    default_name: str = "TTS_TD"

    default_setting: dict[str, str] = {
        "userid": "",
        "password": "",
        "broker_id": "",
        "td_address": "",
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
        self.td_api: TtsTdApi | None = None  # Will be initialized on demand
        self.count: int = 0

        # 加载合约交易所映射文件
        self.instrument_exchange_map: dict = {}
        map_file_path = ""
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            # 构建到 instrument_exchange_id.json 的相对路径
            map_file_path = os.path.join(current_dir, "..", "..", "config_files", "instrument_exchange_id.json")
            map_file_path = os.path.normpath(map_file_path)  # 规范化路径

            if os.path.exists(map_file_path):
                with open(map_file_path, "r", encoding="utf-8") as f:
                    self.instrument_exchange_map = json.load(f)
                self.write_log(f"成功从 {map_file_path} 加载合约交易所映射。")
            else:
                self.write_log(f"警告：合约交易所映射文件未找到于 {map_file_path}。回退逻辑可能受限。")
        except Exception as e:
            self.write_log(f"加载合约交易所映射文件 {map_file_path} 时出错: {e}")


    def connect(self, setting: dict) -> None:
        pass

    def close(self) -> None:
        pass


class TtsTdApi(TdApi):
    """
    TTS交易接口
    """

    def __init__(self, gateway: OrderTradingGateway) -> None:
        super().__init__()

        self.gateway: OrderTradingGateway = gateway
        self.gateway_name: str = gateway.name

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
        """
        self.gateway.write_log("交易服务器连接成功")

        if self.auth_code:
            self.authenticate()
        else:
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
        """
        self.login_status = False
        self.gateway.write_log(f"交易服务器连接断开，原因{reason}")

    def onRspAuthenticate(self, data: dict, error: dict, reqid: int, last: bool) -> None:
        """
        用户授权验证回报
        :param data: 客户端认证响应
        :param error: 响应信息
        :param reqid: 返回用户操作请求的 ID，该 ID 由用户在操作请求时指定。
        :param last: 指示该次返回是否为针对 reqid 的最后一次返回。
        :return: 无
        """
        if not error['ErrorID']:
            self.auth_status = True
            self.gateway.write_log("交易服务器授权验证成功")
            self.login()
        else:
            self.gateway.write_error("交易服务器授权验证失败", error)

    def onRspUserLogin(self, data: dict, error: dict, reqid: int, last: bool) -> None:
        """
        用户登录请求回报
        :param data: 用户登录应答
        :param error: 响应信息
        :param reqid: 返回用户操作请求的 ID，该 ID 由用户在操作请求时指定。
        :param last: 指示该次返回是否为针对 reqid 的最后一次返回。
        :return: 无
        """
        if not error["ErrorID"]:
            self.front_id = data["FrontID"]
            self.session_id = data["SessionID"]
            self.login_status = True
            global_var.td_login_success = True
            self.gateway.write_log("交易服务器登录成功")

            # 自动确认结算单
            tts_req: dict = {
                "BrokerID": self.broker_id,
                "InvestorID": self.userid
            }
            self.req_id += 1
            self.reqSettlementInfoConfirm(tts_req, self.req_id)
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
            direction=DIRECTION_TTS2VT[data["Direction"]],
            offset=OFFSET_TTS2VT.get(data["CombOffsetFlag"], Offset.NONE),
            price=data["LimitPrice"],
            volume=data["VolumeTotalOriginal"],
            status=Status.REJECTED,
            gateway_name=self.gateway_name
        )
        self.gateway.on_order(order)

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
        确认结算单回报
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

                # # 由于流控，单次查询可能失败，通过while循环持续尝试，直到成功发出请求
                # retries = 0
                # max_retries = 5
                # while retries < max_retries:
                #     self.reqid += 1
                #     n: int = self.reqQryInstrument({}, self.reqid)
                #     if not n:
                #         break
                #     else:
                #         self.gateway.write_log(f"reqQryInstrument failed with {n}, retrying in 1s ({retries+1}/{max_retries})")
                #         sleep(1)
                #         retries += 1
                # if retries == max_retries:
                #     self.gateway.write_log("reqQryInstrument failed after max retries.")
                # TODO: 查询所有合约信息，后期考虑要不要统一使用流控方案
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
        # TODO: 后期考虑是否和CTP方案统一，要不要if last or error判断
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
                    direction=DIRECTION_TTS2VT[data["PosiDirection"]],
                    gateway_name=self.gateway_name
                )
                self.positions[key] = position

            # 对于上期所昨仓需要特殊处理
            if position.exchange in [Exchange.SHFE, Exchange.INE]:
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
        :param data: 合约
        :param error: 响应信息
        :param reqid: 返回用户操作请求的 ID，该 ID 由用户在操作请求时指定。
        :param last: 指示该次返回是否为针对 reqid 的最后一次返回。
        :return:
        """
        # TODO: 后期考虑是否和CTP方案统一
        # 合约对象构建
        contract = tts_build_contract(data, self.gateway_name)
        if contract:
            self.gateway.on_contract(contract)
            symbol_contract_map[contract.symbol] = contract

        # 更新exchange_id_map，只取非纯数字的合约和6位以内的合约，即只取期货合约
        if not data.get("InstrumentID", "").isdigit() and len(data.get("InstrumentID", "")) <= 6:
            self.instrument_exchange_id_map[data.get("InstrumentID", "")] = data.get("ExchangeID", "")

        if last:
            self.contract_inited = True
            self.gateway.write_log("合约信息查询成功")

            try:
                write_json_file(GlobalPath.instrument_exchange_id_filepath, self.instrument_exchange_id_map)
            except Exception as e:
                self.gateway.write_error("写入 instrument_exchange_id.json 失败：{}".format(e), error)

            for data in self.order_data:
                self.onRtnOrder(data)
            self.order_data.clear()

            for data in self.trade_data:
                self.onRtnTrade(data)
            self.trade_data.clear()

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

        status: Status = STATUS_TTS2VT.get(data["OrderStatus"], None)
        if not status:
            self.gateway.write_log("收到不支持的委托状态，委托号：{}".format(orderid))
            return

        timestamp: str = f"{data['InsertDate']} {data['InsertTime']}"
        dt: datetime = datetime.strptime(timestamp, "%Y%m%d %H:%M:%S")
        dt: datetime = dt.replace(tzinfo=CHINA_TZ)

        # TODO: 这里和CTP不同的是CTP多了委托类型的判断，后期考虑是否和CTP方案统一

        order: OrderData = OrderData(
            symbol=symbol,
            exchange=contract.exchange,
            orderid=orderid,
            type=ORDERTYPE_TTS2VT[data["OrderPriceType"]],
            direction=DIRECTION_TTS2VT[data["Direction"]],
            offset=OFFSET_TTS2VT[data["CombOffsetFlag"]],
            price=data["LimitPrice"],
            volume=data["VolumeTotalOriginal"],
            traded=data["VolumeTraded"],
            status=STATUS_TTS2VT[data["OrderStatus"]],
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
        dt: datetime = dt.replace(tzinfo=CHINA_TZ)

        trade: TradeData = TradeData(
            symbol=symbol,
            exchange=contract.exchange,
            orderid=orderid,
            trade_id=data["TradeID"],
            direction=DIRECTION_TTS2VT[data["Direction"]],
            offset=OFFSET_TTS2VT[data["OffsetFlag"]],
            price=data["Price"],
            volume=data["Volume"],
            datetime=dt,
            gateway_name=self.gateway_name
        )
        self.gateway.on_trade(trade)

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
            self.gateway.write_error("合约手续费率查询失败。错误 ID：{}".format(
                error.get('ErrorID', 'N/A')), error)
            return

        # 增加对data 和 data['InstrumentID']的有效性检查
        if data is None or not data.get("InstrumentID"):
            # 如果是最后一条回报但数据无效，可能需要记录一下
            if last:
                self.gateway.write_log("收到无效或空的合约手续费数据（最后一条）。ReqID: {}".format(reqid))
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
            self.gateway.write_log("TtsTdApi：尝试创建路径为 {} 的 API".format(api_path_str))
            try:
                self.createFtdcTraderApi(api_path_str.encode("GBK").decode("utf-8"))
                self.gateway.write_log("TtsTdApi：createFtdcTraderApi调用成功。")
            except Exception as e_create:
                self.gateway.write_log("TtsTdApi：createFtdcTraderApi 失败！错误：{}".format(e_create))
                self.gateway.write_log("TtsTdApi：createFtdcTraderApi 回溯：{}".format(traceback.format_exc()))
                return

            self.subscribePrivateTopic(0)
            self.subscribePublicTopic(0)

            self.registerFront(address)

            self.gateway.write_log("TtsTdApi：尝试使用地址初始化 API：{}...".format(address))
            try:
                self.init()
                self.gateway.write_log("TtsTdApi：init 调用成功。")
            except Exception as e_init:
                self.gateway.write_log("TtsTdApi：初始化失败！错误：{}".format(e_init))
                self.gateway.write_log("TtsTdApi：初始化回溯：{}".format(traceback.format_exc()))
                return

            self.connect_status = True
        else:
            self.gateway.write_log("TtsTdApi：已连接，正在尝试身份验证。")
            self.authenticate()

    def authenticate(self) -> None:
        """
        发起授权验证
        """
        if self.auth_failed:
            return

        tts_req: dict = {
            "UserID": self.userid,
            "BrokerID": self.broker_id,
            "AuthCode": self.auth_code,
            "AppID": self.appid
        }

        self.req_id += 1
        self.reqAuthenticate(tts_req, self.req_id)

    def login(self) -> None:
        """
        用户登录
        """
        if self.login_failed:
            return

        tts_req: dict = {
            "UserID": self.userid,
            "Password": self.password,
            "BrokerID": self.broker_id,
            "AppID": self.appid
        }

        self.req_id += 1
        self.reqUserLogin(tts_req, self.req_id)

    def send_order(self, req: OrderRequest) -> str:
        """
        委托下单
        :param req:
        :return:
        """
        if req.offset not in OFFSET_VT2TTS:
            self.gateway.write_log("请选择开平方向")
            return ""

        if req.type not in ORDERTYPE_VT2TTS:
            self.gateway.write_log(f"当前接口不支持该类型的委托{req.type.value}")
            return ""

        exchange = EXCHANGE_VT2TTS.get(req.exchange, None)
        if not exchange:
            self.gateway.write_log(f"不支持的交易所：{req.exchange}")
            return ""

        self.order_ref += 1

        tts_req: dict = {
            "InstrumentID": req.symbol,
            "ExchangeID": exchange,
            "LimitPrice": req.price,
            "VolumeTotalOriginal": int(req.volume),
            "OrderPriceType": ORDERTYPE_VT2TTS.get(req.type, ""),
            "Direction": DIRECTION_VT2TTS.get(req.direction, ""),
            "CombOffsetFlag": OFFSET_VT2TTS.get(req.offset, ""),
            "OrderRef": str(self.order_ref),
            "InvestorID": self.userid,
            "UserID": self.userid,
            "BrokerID": self.broker_id,
            "CombHedgeFlag": THOST_FTDC_HF_Speculation,
            "ContingentCondition": THOST_FTDC_CC_Immediately,
            "ForceCloseReason": THOST_FTDC_FCC_NotForceClose,
            "IsAutoSuspend": 0,
            "TimeCondition": THOST_FTDC_TC_GFD,
            "VolumeCondition": THOST_FTDC_VC_AV,
            "MinVolume": 1
        }

        if req.type == OrderType.FAK:
            tts_req["OrderPriceType"] = THOST_FTDC_OPT_LimitPrice
            tts_req["TimeCondition"] = THOST_FTDC_TC_IOC
            tts_req["VolumeCondition"] = THOST_FTDC_VC_AV
        elif req.type == OrderType.FOK:
            tts_req["OrderPriceType"] = THOST_FTDC_OPT_LimitPrice
            tts_req["TimeCondition"] = THOST_FTDC_TC_IOC
            tts_req["VolumeCondition"] = THOST_FTDC_VC_CV

        self.req_id += 1
        self.reqOrderInsert(tts_req, self.req_id)

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
        exchange = EXCHANGE_VT2TTS.get(req.exchange, None)
        if not exchange:
            self.gateway.write_log(f"不支持的交易所：{req.exchange}")
            return

        front_id, session_id, order_ref = req.orderid.split("_")

        tts_req: dict = {
            "InstrumentID": req.symbol,
            "ExchangeID": exchange,
            "OrderRef": order_ref,
            "FrontID": int(front_id),
            "SessionID": int(session_id),
            "ActionFlag": THOST_FTDC_AF_Delete,
            "BrokerID": self.broker_id,
            "InvestorID": self.userid
        }

        self.req_id += 1
        self.reqOrderAction(tts_req, self.req_id)

    def send_rfq(self, req: OrderRequest) -> str:
        """
        询价请求
        """
        exchange = EXCHANGE_VT2TTS.get(req.exchange, None)
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
        """
        self.req_id += 1
        self.reqQryTradingAccount({}, self.req_id)

    def query_position(self) -> None:
        """
        查询持仓
        """
        if not symbol_contract_map:
            return

        tts_req: dict = {
            "BrokerID": self.broker_id,
            "InvestorID": self.userid
        }

        self.req_id += 1
        self.reqQryInvestorPosition(tts_req, self.req_id)

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

            tts_req: dict = {
                "BrokerID": self.broker_id,
                "InvestorID": self.userid,
                "InstrumentID": symbol
            }
            self.gateway.write_log('开始查询手续费...')
            while True:
                self.req_id += 1
                n: int = self.reqQryInstrumentCommissionRate(tts_req, self.req_id)
                if not n:  # n是0时，表示请求成功
                    break
                else:
                    self.gateway.write_log("查询合约的手续费率，代码为 {}，正在查询手续费..."
                                           .format(n))
                    sleep(1)

    def close(self) -> None:
        """
        关闭连接
        """
        if self.connect_status:
            self.exit()
