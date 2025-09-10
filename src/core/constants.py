#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : constants.py
@Date       : 2025/9/8 17:37
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 交易平台中使用的通用常量枚举。

General constant enums used in the trading platform.
"""
from enum import Enum


class Direction(Enum):
    """
    订单/交易/仓位的方向

    Direction of order/trade/position
    """
    LONG = "long"  # 多
    SHORT = "short"  # 空
    NET = "net"  # 净

    BUY_OPEN = "buy_open"
    BUY_CLOSE = "buy_close"
    SELL_OPEN = "sell_open"
    SELL_CLOSE = "sell_close"
    BUY_CLOSE_TODAY = "buy_close_today"
    SELL_CLOSE_TODAY = "sell_close_today"


class Offset(Enum):
    """
    订单的开平仓方向

    Offset of order/trade
    """
    NONE = ""                           # 无
    OPEN = "open"                       # 开
    CLOSE = "close"                     # 平
    CLOSE_TODAY = "close_today"         # 平今
    CLOSE_YESTERDAY = "close_yesterday" # 平昨


class Product(Enum):
    """
    产品类别

    Product class
    """
    FUTURES = "期货"
    OPTION = "期权"


class OrderType(Enum):
    """
    订单类型

    Order type
    """
    LIMIT = "limit"     # 限价
    MARKET = "market"   # 市价
    STOP = "STOP"
    FAK = "FAK"
    FOK = "FOK"
    RFQ = "询价"


class OptionType(Enum):
    """
    期权类型

    Option type.
    """
    CALL = "看涨期权"
    PUT = "看跌期权"


class Exchange(Enum):
    """
    交易所

    Exchange
    """
    # Chinese
    CFFEX = "CFFEX"         # China Financial Futures Exchange
    SHFE = "SHFE"           # Shanghai Futures Exchange
    CZCE = "CZCE"           # Zhengzhou Commodity Exchange
    DCE = "DCE"             # Dalian Commodity Exchange
    INE = "INE"             # Shanghai International Energy Exchange
    GFEX = "GFEX"           # Guangzhou Futures Exchange
    SSE = "SSE"             # Shanghai Stock Exchange
    SZSE = "SZSE"           # Shenzhen Stock Exchange
    BSE = "BSE"             # Beijing Stock Exchange
    CFETS = "CFETS"         # CFETS Bond Market Maker Trading System


class Currency(Enum):
    """
    货币

    Currency
    """
    CNY = "CNY"


class Interval(Enum):
    """
    数据间隔

    Data interval
    """
    # 分钟
    MINUTE = "1m"
    THREE_MINUTE = "3m"
    FIVE_MINUTE = "5m"
    EIGHT_MINUTE = "8m"
    THIRTEEN_MINUTE = "13m"
    TWENTY_ONE_MINUTE = "21m"
    THIRTY_FOUR_MINUTE = "34m"
    FIFTY_FIVE_MINUTE = "55m"
    EIGHTY_NINE_MINUTE = "89m"
    ONE_HUNDRED_FORTY_FOUR_MINUTE = "144m"

    HOUR = "1h"  # 小时
    DAILY = "d"  # 日
    WEEKLY = "w" # 周
