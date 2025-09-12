#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : gateway_const.py
@Date       : 2025/9/10 21:26
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 网关常量
"""
import sys
from zoneinfo import ZoneInfo

from src.core.constants import ErrorReason, Direction, Offset, OrderStatus, Product, Exchange, OptionType, OrderType
from src.core.object import ContractData
from src.ctp.api.ctp_constant import (
    THOST_FTDC_OST_Unknown,
    THOST_FTDC_OST_AllTraded,
    THOST_FTDC_OST_PartTradedQueueing,
    THOST_FTDC_OST_PartTradedNotQueueing,
    THOST_FTDC_OST_NoTradeQueueing,
    THOST_FTDC_OST_NoTradeNotQueueing,
    THOST_FTDC_OST_Canceled,
    THOST_FTDC_D_Buy,
    THOST_FTDC_D_Sell,
    THOST_FTDC_PD_Long,
    THOST_FTDC_PD_Short,
    THOST_FTDC_OF_Open,
    THOST_FTDC_OFEN_Close,
    THOST_FTDC_OFEN_CloseToday,
    THOST_FTDC_OFEN_CloseYesterday,
    THOST_FTDC_PC_Futures,
    THOST_FTDC_PC_Options,
    THOST_FTDC_PC_SpotOption,
    THOST_FTDC_PC_Combination,
    THOST_FTDC_CP_CallOptions,
    THOST_FTDC_CP_PutOptions,
    THOST_FTDC_OPT_LimitPrice,
    THOST_FTDC_TC_GFD,
    THOST_FTDC_VC_AV,
    THOST_FTDC_OPT_AnyPrice,
    THOST_FTDC_TC_IOC,
    THOST_FTDC_VC_CV
)

# 合约数据全局缓存字典
symbol_contract_map: dict[str, ContractData] = {}

MAX_FLOAT = sys.float_info.max          # 浮点数极限值
CHINA_TZ = ZoneInfo("Asia/Shanghai")    # 中国时区

# 错误码与错误原因映射
REASON_MAPPING: dict[str, ErrorReason] = {
    "0x1001": ErrorReason.REASON_0x1001,
    "0x1002": ErrorReason.REASON_0x1002,
    "0x2001": ErrorReason.REASON_0x2001,
    "0x2002": ErrorReason.REASON_0x2002,
    "0x2003": ErrorReason.REASON_0x2003
}

# 订单状态从CTP常量到枚举常量的映射
ORDER_STATUS_CTP_TO_ENUM: dict[str, OrderStatus] = {
    THOST_FTDC_OST_Unknown: OrderStatus.SUBMITTING,
    THOST_FTDC_OST_AllTraded: OrderStatus.ALL_TRADED,
    THOST_FTDC_OST_PartTradedQueueing: OrderStatus.PART_TRADED_QUEUEING,
    THOST_FTDC_OST_PartTradedNotQueueing: OrderStatus.PART_TRADED_NOT_QUEUEING,
    THOST_FTDC_OST_NoTradeQueueing: OrderStatus.NO_TRADE_QUEUEING,
    THOST_FTDC_OST_NoTradeNotQueueing: OrderStatus.NO_TRADE_NOT_QUEUEING,
    THOST_FTDC_OST_Canceled: OrderStatus.CANCELED
}

# ================== 买卖方向的映射，long -> buy, short -> sell ==================
# 买卖方向从枚举常量到CTP常量的映射
DIRECTION_ENUM_TO_CTP: dict[Direction, str] = {
    Direction.LONG: THOST_FTDC_D_Buy,
    Direction.SHORT: THOST_FTDC_D_Sell
}
# 买卖方向从CTP常量到枚举常量的映射
DIRECTION_CTP_TO_ENUM: dict[str, Direction] = {v: k for k, v in DIRECTION_ENUM_TO_CTP.items()}
DIRECTION_CTP_TO_ENUM[THOST_FTDC_PD_Long] = Direction.LONG
DIRECTION_CTP_TO_ENUM[THOST_FTDC_PD_Short] = Direction.SHORT

# 委托类型映射
ORDER_TYPE_ENUM_TO_CTP: dict[OrderType, tuple] = {
    OrderType.LIMIT: (THOST_FTDC_OPT_LimitPrice, THOST_FTDC_TC_GFD, THOST_FTDC_VC_AV),
    OrderType.MARKET: (THOST_FTDC_OPT_AnyPrice, THOST_FTDC_TC_GFD, THOST_FTDC_VC_AV),
    OrderType.FAK: (THOST_FTDC_OPT_LimitPrice, THOST_FTDC_TC_IOC, THOST_FTDC_VC_AV),
    OrderType.FOK: (THOST_FTDC_OPT_LimitPrice, THOST_FTDC_TC_IOC, THOST_FTDC_VC_CV),
}
ORDER_TYPE_CTP_TO_ENUM: dict[tuple, OrderType] = {v: k for k, v in ORDER_TYPE_ENUM_TO_CTP.items()}

# ================== 开平方向映射 ==================
# 从枚举常量到CTP常量的映射
OFFSET_ENUM_TO_CTP: dict[Offset, str] = {
    Offset.OPEN: THOST_FTDC_OF_Open,
    Offset.CLOSE: THOST_FTDC_OFEN_Close,
    Offset.CLOSE_TODAY: THOST_FTDC_OFEN_CloseToday,
    Offset.CLOSE_YESTERDAY: THOST_FTDC_OFEN_CloseYesterday,
}
# 从CTP常量到枚举常量的映射
OFFSET_CTP_TO_ENUM: dict[str, Offset] = {v: k for k, v in OFFSET_ENUM_TO_CTP.items()}

# 产品类型映射
PRODUCT_CTP_TO_ENUM: dict[str, Product] = {
    THOST_FTDC_PC_Futures: Product.FUTURES,
    THOST_FTDC_PC_Options: Product.OPTION,
    THOST_FTDC_PC_SpotOption: Product.OPTION,
    THOST_FTDC_PC_Combination: Product.SPREAD
}

# 期权类型映射
OPTION_TYPE_CTP_TO_ENUM: dict[str, OptionType] = {
    THOST_FTDC_CP_CallOptions: OptionType.CALL,
    THOST_FTDC_CP_PutOptions: OptionType.PUT
}

# 交易所映射
EXCHANGE_CTP_TO_ENUM: dict[str, Exchange] = {
    "CFFEX": Exchange.CFFEX,
    "SHFE": Exchange.SHFE,
    "CZCE": Exchange.CZCE,
    "DCE": Exchange.DCE,
    "INE": Exchange.INE,
    "GFEX": Exchange.GFEX
}
