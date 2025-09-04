#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Nilotica
@FileName   : ctp_gateway_helper
@Date       : 2025/5/20 16:44
@Author     : Donny
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: ctp gateway helper
"""
from datetime import datetime
from typing import Optional

from src.config.constant import Product, Exchange
from src.core.object import ContractData, TickData
from .ctp_mapping import PRODUCT_CTP2VT, EXCHANGE_CTP2VT, OPTION_TYPE_CTP2VT
from ...core.logger import get_logger
from ...util.utility import adjust_price
from ...util.utility import ZoneInfo

logger = get_logger("ctp_build_contract")


def ctp_build_contract(data: dict, gateway_name: str) -> ContractData | None:
    """
    合约对象构建及期权特殊处理
    """
    product: Product = PRODUCT_CTP2VT.get(data.get("ProductClass"), None)
    contract: Optional[ContractData] = None
    if product:
        contract: ContractData = ContractData(
            symbol=data.get("InstrumentID", ""),
            exchange=EXCHANGE_CTP2VT.get(data.get("ExchangeID", "")),
            name=data.get("InstrumentName", ""),
            product=product,
            size=data.get("VolumeMultiple", 1),
            price_tick=data.get("PriceTick", 0.0),
            min_volume=data.get("MinLimitOrderVolume", 1),
            max_volume=data.get("MaxLimitOrderVolume", 1),
            gateway_name=gateway_name
        )
        # 期权相关
        if contract.product == Product.OPTION:
            if contract.exchange == Exchange.CZCE:
                contract.option_portfolio = data.get("ProductID", "")[:-1]
            else:
                contract.option_portfolio = data.get("ProductID", "")
            contract.option_underlying = data.get("UnderlyingInstrID", "")
            contract.option_type = OPTION_TYPE_CTP2VT.get(data.get("OptionsType"))
            contract.option_strike = data.get("StrikePrice", 0.0)
            contract.option_index = str(data.get("StrikePrice", ""))
            try:
                contract.option_listed = datetime.strptime(data.get("OpenDate", ""), "%Y%m%d")
                contract.option_expiry = datetime.strptime(data.get("ExpireDate", ""), "%Y%m%d")
            except Exception as e:
                logger.error("期权合约构建失败: {}".format(e))
                contract.option_listed = None
                contract.option_expiry = None

    return contract


def ctp_build_tick_data(tick_data: dict, contract: ContractData, current_date: str, gateway_name: str):
    """
    tick 数据构建
    @param tick_data: tick 数据
    @param contract: 合约对象
    @param current_date: 当前日期
    @param gateway_name: 网关名称
    """
    china_tz: ZoneInfo = ZoneInfo("Asia/Shanghai")  # 中国时区

    # 对大商所的交易日字段取本地日期
    if not tick_data["ActionDay"] or contract.exchange == Exchange.DCE:
        date_str: str = current_date
    else:
        date_str = tick_data["ActionDay"]

    # timestamp 年月日时分秒毫秒
    timestamp: str = f"{date_str} {tick_data['UpdateTime']}.{tick_data['UpdateMillisec']}"
    dt_format_obj: datetime = datetime.strptime(timestamp, "%Y%m%d %H:%M:%S.%f")
    dt_obj: datetime = dt_format_obj.replace(tzinfo=china_tz)

    tick: TickData = TickData(
        symbol=tick_data.get("InstrumentID", "UNKNOWN"),
        exchange=contract.exchange,
        datetime=dt_obj,
        trading_day=tick_data["TradingDay"],
        instrument_id=tick_data["InstrumentID"],
        exchange_inst_id=tick_data["ExchangeInstID"],
        last_price=adjust_price(tick_data["LastPrice"]),
        pre_settlement_price=tick_data["PreSettlementPrice"],
        pre_close_price=adjust_price(tick_data["PreClosePrice"]),
        pre_open_interest=tick_data["PreOpenInterest"],
        open_price=adjust_price(tick_data["OpenPrice"]),
        highest_price=adjust_price(tick_data["HighestPrice"]),
        lowest_price=adjust_price(tick_data["LowestPrice"]),
        volume=tick_data["Volume"],
        turnover=tick_data["Turnover"],
        open_interest=tick_data["OpenInterest"],
        close_price=adjust_price(tick_data["ClosePrice"]),
        settlement_price=adjust_price(tick_data["SettlementPrice"]),
        upper_limit_price=tick_data["UpperLimitPrice"],
        lower_limit_price=tick_data["LowerLimitPrice"],
        pre_delta=tick_data["PreDelta"],
        curr_delta=tick_data["CurrDelta"],
        update_time=tick_data["UpdateTime"],
        update_millisec=tick_data["UpdateMillisec"],
        bid_price_1=adjust_price(tick_data["BidPrice1"]),
        bid_volume_1=tick_data["BidVolume1"],
        ask_price_1=adjust_price(tick_data["AskPrice1"]),
        ask_volume_1=tick_data["AskVolume1"],
        bid_price_2=adjust_price(tick_data["BidPrice2"]),
        bid_volume_2=tick_data["BidVolume2"],
        ask_price_2=adjust_price(tick_data["AskPrice2"]),
        ask_volume_2=tick_data["AskVolume2"],
        bid_price_3=adjust_price(tick_data["BidPrice3"]),
        bid_volume_3=tick_data["BidVolume3"],
        ask_price_3=adjust_price(tick_data["AskPrice3"]),
        ask_volume_3=tick_data["AskVolume3"],
        bid_price_4=adjust_price(tick_data["BidPrice4"]),
        bid_volume_4=tick_data["BidVolume4"],
        ask_price_4=adjust_price(tick_data["AskPrice4"]),
        ask_volume_4=tick_data["AskVolume4"],
        bid_price_5=adjust_price(tick_data["BidPrice5"]),
        bid_volume_5=tick_data["BidVolume5"],
        ask_price_5=adjust_price(tick_data["AskPrice5"]),
        ask_volume_5=tick_data["AskVolume5"],
        average_price=adjust_price(tick_data["AveragePrice"]),
        action_day=tick_data["ActionDay"],
        banding_upper_price=tick_data["BandingUpperPrice"],
        banding_lower_price=tick_data["BandingLowerPrice"],
        gateway_name=gateway_name
    )

    if tick_data["BidVolume2"] or tick_data["AskVolume2"]:
        tick.bid_price_2 = adjust_price(tick_data["BidPrice2"])
        tick.bid_price_3 = adjust_price(tick_data["BidPrice3"])
        tick.bid_price_4 = adjust_price(tick_data["BidPrice4"])
        tick.bid_price_5 = adjust_price(tick_data["BidPrice5"])

        tick.ask_price_2 = adjust_price(tick_data["AskPrice2"])
        tick.ask_price_3 = adjust_price(tick_data["AskPrice3"])
        tick.ask_price_4 = adjust_price(tick_data["AskPrice4"])
        tick.ask_price_5 = adjust_price(tick_data["AskPrice5"])

        tick.bid_volume_2 = tick_data["BidVolume2"]
        tick.bid_volume_3 = tick_data["BidVolume3"]
        tick.bid_volume_4 = tick_data["BidVolume4"]
        tick.bid_volume_5 = tick_data["BidVolume5"]

        tick.ask_volume_2 = tick_data["AskVolume2"]
        tick.ask_volume_3 = tick_data["AskVolume3"]
        tick.ask_volume_4 = tick_data["AskVolume4"]
        tick.ask_volume_5 = tick_data["AskVolume5"]

    return tick