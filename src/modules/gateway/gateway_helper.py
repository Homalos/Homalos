#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : gateway_helper.py
@Date       : 2025/9/10 17:47
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: gateway 的帮助类
"""
from datetime import datetime

from src.constants import INSTRUMENT_EXCHANGE_FILENAME
from src.core.constants import Offset, OrderStatus, Product, Exchange, OrderType, Direction, OpenDate
from src.core.event import EventType, Event
from src.core.event_bus import EventBus
from src.core.object import TickData, ContractData, OrderData, TradeData, PositionDetailData
from src.modules.gateway.gateway_const import (
    MAX_FLOAT,
    DIRECTION_CTP_TO_ENUM,
    OFFSET_CTP_TO_ENUM,
    EXCHANGE_CTP_TO_ENUM,
    OPTION_TYPE_CTP_TO_ENUM
)
from src.utils.get_path import get_path_ins
from src.utils.utility import load_json


def adjust_price(price: float) -> float:
    """将异常的浮点数最大值（MAX_FLOAT）数据调整为0"""
    if price == MAX_FLOAT:
        price = 0
    return price

def extract_error_msg(
        rsp_info: dict,
        custom_msg: str = "出错"
) -> str:
    """
    从响应中提取错误消息
    :param rsp_info: 响应的信息
    :param custom_msg: 自定义消息
    :return: 错误消息
    """
    if rsp_info and rsp_info.get("ErrorID") != 0:
        return (f"{custom_msg}, 错误代码：{rsp_info.get('ErrorID', 'N/A')}, "
                f"错误信息：{rsp_info.get('ErrorMsg', 'Unknown')}")
    else:
        return ""


def get_exchange_name(instrument_id: str) -> str:
    """
    获取交易所名称
    :param instrument_id: 合约代码
    :return: 交易所名称
    """
    return load_json(str(get_path_ins.get_config_dir() / INSTRUMENT_EXCHANGE_FILENAME)).get(instrument_id, "")

# def build_tick_data_general(data: dict) -> TickData:
#     """
#     组装tick数据
#     :param data:
#     :return:
#     """
#     tick: TickData = TickData(
#         trading_day=data.get("TradingDay"),
#         instrument_id=data.get("InstrumentID"),
#         exchange_id=data.get("InstrumentID"),
#         exchange_inst_id=data.get("ExchangeInstID"),
#         last_price=adjust_price(data.get("LastPrice")),
#         pre_settlement_price=adjust_price(data.get("PreSettlementPrice")),
#         pre_close_price=adjust_price(data.get("PreClosePrice")),
#         pre_open_interest=data.get("PreOpenInterest"),
#         open_price=adjust_price(data.get("OpenPrice")),
#         highest_price=adjust_price(data.get("HighestPrice")),
#         lowest_price=adjust_price(data.get("LowestPrice")),
#         volume=data["Volume"],
#         turnover=data["Turnover"],
#         open_interest=data["OpenInterest"],
#         close_price=adjust_price(data.get("ClosePrice")),
#         settlement_price=adjust_price(data.get("SettlementPrice")),
#         upper_limit_price=adjust_price(data.get("UpperLimitPrice")),
#         lower_limit_price=adjust_price(data.get("LowerLimitPrice")),
#         pre_delta=data.get("PreDelta"),
#         curr_delta=data.get("CurrDelta"),
#         update_time=data.get("UpdateTime"),
#         update_millisec=data.get("UpdateMillisec"),
#         bid_price_1=adjust_price(data["BidPrice1"]),
#         bid_volume_1=data["BidVolume1"],
#         ask_price_1=adjust_price(data["AskPrice1"]),
#         ask_volume_1=data["AskVolume1"],
#         timestamp=timestamp
#     )
#
#     if data["BidVolume2"] or data["AskVolume2"]:
#         tick.bid_price_2 = adjust_price(data["BidPrice2"])
#         tick.bid_volume_2 = data["BidVolume2"]
#         tick.ask_price_2 = adjust_price(data["AskPrice2"])
#         tick.ask_volume_2 = data["AskVolume2"]
#         tick.bid_price_3 = adjust_price(data["BidPrice3"])
#         tick.bid_volume_3 = data["BidVolume3"]
#         tick.ask_price_3 = adjust_price(data["AskPrice3"])
#         tick.ask_volume_3 = data["AskVolume3"]
#         tick.bid_price_4 = adjust_price(data["BidPrice4"])
#         tick.bid_volume_4 = data["BidVolume4"]
#         tick.ask_price_4 = adjust_price(data["AskPrice4"])
#         tick.ask_volume_4 = data["AskVolume4"]
#         tick.bid_price_5 = adjust_price(data["BidPrice5"])
#         tick.bid_volume_5 = data["BidVolume5"]
#         tick.ask_price_5 = adjust_price(data["AskPrice5"])
#         tick.ask_volume_5 = data["AskVolume5"]
#
#     return tick


def build_tick_data(data: dict, contract: ContractData, timestamp: datetime) -> TickData:
    """
    组装tick数据
    :param data: 原始数据(tick)
    :param contract: 合约数据
    :param timestamp: 时间戳
    :return: 组装好的tick数据
    """
    tick: TickData = TickData(
        trading_day = data.get("TradingDay"),
        instrument_id = data.get("InstrumentID"),
        exchange_id = contract.exchange_id,
        exchange_inst_id = data.get("ExchangeInstID"),
        last_price = adjust_price(data.get("LastPrice")),
        pre_settlement_price = adjust_price(data.get("PreSettlementPrice")),
        pre_close_price = adjust_price(data.get("PreClosePrice")),
        pre_open_interest = data.get("PreOpenInterest"),
        open_price = adjust_price(data.get("OpenPrice")),
        highest_price = adjust_price(data.get("HighestPrice")),
        lowest_price = adjust_price(data.get("LowestPrice")),
        volume=data["Volume"],
        turnover=data["Turnover"],
        open_interest=data["OpenInterest"],
        close_price = adjust_price(data.get("ClosePrice")),
        settlement_price = adjust_price(data.get("SettlementPrice")),
        upper_limit_price = adjust_price(data.get("UpperLimitPrice")),
        lower_limit_price = adjust_price(data.get("LowerLimitPrice")),
        pre_delta = data.get("PreDelta"),
        curr_delta = data.get("CurrDelta"),
        update_time = data.get("UpdateTime"),
        update_millisec = data.get("UpdateMillisec"),
        bid_price_1=adjust_price(data["BidPrice1"]),
        bid_volume_1=data["BidVolume1"],
        ask_price_1=adjust_price(data["AskPrice1"]),
        ask_volume_1=data["AskVolume1"],
        timestamp = timestamp
    )

    if data["BidVolume2"] or data["AskVolume2"]:
        tick.bid_price_2 = adjust_price(data["BidPrice2"])
        tick.bid_volume_2 = data["BidVolume2"]
        tick.ask_price_2 = adjust_price(data["AskPrice2"])
        tick.ask_volume_2 = data["AskVolume2"]
        tick.bid_price_3 = adjust_price(data["BidPrice3"])
        tick.bid_volume_3 = data["BidVolume3"]
        tick.ask_price_3 = adjust_price(data["AskPrice3"])
        tick.ask_volume_3 = data["AskVolume3"]
        tick.bid_price_4 = adjust_price(data["BidPrice4"])
        tick.bid_volume_4 = data["BidVolume4"]
        tick.ask_price_4 = adjust_price(data["AskPrice4"])
        tick.ask_volume_4 = data["AskVolume4"]
        tick.bid_price_5 = adjust_price(data["BidPrice5"])
        tick.bid_volume_5 = data["BidVolume5"]
        tick.ask_price_5 = adjust_price(data["AskPrice5"])
        tick.ask_volume_5 = data["AskVolume5"]

    return tick

def build_order_data(data: dict, contract: ContractData, order_id: str) -> OrderData:
    """
    组装订单数据
    :param data: 原始数据
    :param contract: 缓存数据
    :param order_id: 订单ID
    :return:
    """
    order: OrderData = OrderData(
        instrument_id = data.get("InstrumentID"),  # 合约代码
        exchange_id = contract.exchange_id,
        order_id = order_id,
        direction = DIRECTION_CTP_TO_ENUM[data.get("Direction")],  # 买卖方向
        offset = OFFSET_CTP_TO_ENUM.get(data.get("CombOffsetFlag"), Offset.NONE),  # 组合开平标志
        price = data.get("LimitPrice"),  # 价格
        volume = data.get("VolumeTotalOriginal"),  # 数量
        order_status = OrderStatus.REJECTED
    )

    return order

def build_rtn_order_data(
        data: dict,
        contract: ContractData,
        order_id: str,
        order_type: OrderType,
        order_status: OrderStatus,
        timestamp: datetime
):
    """
    组装订单数据
    :param data: 原始数据
    :param contract: 缓存数据
    :param order_id: 订单ID
    :param order_type: 订单类型
    :param order_status: 订单状态
    :param timestamp: 时间戳
    :return:
    """
    order: OrderData = OrderData(
        instrument_id = data.get("InstrumentID"),
        exchange_id = contract.exchange_id,
        order_id = order_id,
        order_type = order_type,
        direction = DIRECTION_CTP_TO_ENUM[data.get("Direction")],
        offset = OFFSET_CTP_TO_ENUM.get(data.get("CombOffsetFlag"), Offset.NONE),  # 组合开平标志
        price = data.get("LimitPrice"),  # 价格
        volume = data.get("VolumeTotalOriginal"),  # 数量
        volume_traded = data.get("VolumeTraded"),  # 今成交数量
        order_status = order_status,
        timestamp = timestamp
    )

    return order

def build_trade_data(data: dict, contract: ContractData, order_id: str, timestamp: datetime):
    """
    组装成交数据
    :param data: 原始数据
    :param contract: 缓存数据
    :param order_id: 订单ID
    :param timestamp: 时间戳
    :return:
    """
    trade: TradeData = TradeData(
        instrument_id = data.get("InstrumentID"),
        exchange_id = contract.exchange_id,
        order_id = order_id,
        trade_id = data.get("TradeID"),
        direction = DIRECTION_CTP_TO_ENUM[data.get("Direction")],
        offset = OFFSET_CTP_TO_ENUM[data.get("OffsetFlag")],
        price = data.get("Price"),
        volume = data.get("Volume"),
        timestamp = timestamp
    )

    return trade

def build_contract_data(data: dict, product: Product) -> ContractData:
    """
    合约对象构建及期权特殊处理
    :param data: 合约信息
    :param product: 产品数据
    :return:
    """
    contract: ContractData = ContractData(
        instrument_id = data.get("InstrumentID"),
        exchange_id = EXCHANGE_CTP_TO_ENUM.get(data.get("ExchangeID")),
        instrument_name = data.get("InstrumentName"),
        product = product,
        size = data.get("VolumeMultiple"),
        price_tick = data.get("PriceTick"),
        min_volume = data.get("MinLimitOrderVolume"),
        max_volume = data.get("MaxLimitOrderVolume")
    )
    # 期权相关
    if contract.product == Product.OPTION:
        # 移除郑商所期权产品名称带有的C/P后缀
        if contract.exchange_id == Exchange.CZCE:
            contract.option_portfolio = data.get("ProductID")[:-1]
        else:
            contract.option_portfolio = data.get("ProductID")

        contract.option_underlying = data.get("UnderlyingInstrID")
        contract.option_type = OPTION_TYPE_CTP_TO_ENUM.get(data.get("OptionsType"), None)
        contract.option_strike = data.get("StrikePrice")
        contract.option_index = str(data.get("StrikePrice"))
        contract.option_listed = datetime.strptime(data.get("OpenDate"), "%Y%m%d")
        contract.option_expiry = datetime.strptime(data.get("ExpireDate"), "%Y%m%d")

    return contract


def update_position_detail(data: dict) -> dict:
    """
    持仓明细处理
    :param data: 原始数据
    :return:
    """
    position_detail_map: dict = {}

    instrument_id: str = data.get("InstrumentID")  # 合约代码
    exchange_id: Exchange = EXCHANGE_CTP_TO_ENUM.get(data.get("ExchangeID"))  # 交易所代码
    direction: Direction = DIRECTION_CTP_TO_ENUM.get(data.get("Direction"))  # 买卖
    volume = data.get("Volume")  # 数量
    open_price: float = data.get("OpenPrice")  # 开仓价
    open_date = data.get("OpenDate")  # 开仓日期
    trading_day = data.get("TradingDay")  # 交易日

    # 如果不是上期所和能源中心，命名为：au2206_多，
    if exchange_id != Exchange.SHFE and exchange_id != Exchange.INE:
        position_detail_name = '{}_{}'.format(instrument_id, direction.value)

        # 如果该合约第一次出现，则创建持仓明细类，否则不用，直接添加参数即可
        if position_detail_name not in position_detail_map.keys():
            position_detail_map[position_detail_name] = PositionDetailData()
        # 在开仓价列表中添加开仓价
        for i in range(int(volume)):
            position_detail_map[position_detail_name].open_price_list.insert(0, round(open_price, 2))

    # 如果是上期所或者能源中心，命名为：昨_au2206_多
    elif exchange_id == Exchange.SHFE or exchange_id == Exchange.INE:

        position_date = ''
        # 开仓日期指开仓时的交易日期
        if open_date == trading_day:
            position_date = OpenDate.TODAY.value
        elif open_date != trading_day:
            position_date = OpenDate.YESTERDAY.value

        position_detail_name = '{}_{}_{}'.format(position_date, instrument_id, direction.value)
        # 如果该合约第一次出现，则创建持仓明细类，否则不用，之间添加参数即可
        if position_detail_name not in position_detail_map.keys():
            position_detail_map[position_detail_name] = PositionDetailData()
        for i in range(int(volume)):
            position_detail_map[position_detail_name].open_price_list.insert(0, round(open_price, 2))

    return position_detail_map
