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


class KlineType(Enum):
    """
    K线类型
    """
    # 分钟
    MINUTE = '1m'
    MINUTE3 = '3m'
    MINUTE5 = '5m'
    MINUTE8 = '8m'
    MINUTE10 = '10m'
    MINUTE13 = '13m'
    MINUTE15 = '15m'
    MINUTE21 = '21m'
    MINUTE30 = '30m'
    MINUTE34 = '34m'
    MINUTE55 = '55m'
    MINUTE60 = '60m'
    MINUTE89 = '89m'
    MINUTE120 = '120m'
    MINUTE144 = '144m'
    MINUTE180 = '180m'
    MINUTE240 = '240m'

    HOUR = "1h"  # 小时
    DAY = '1d'  # 日
    WEEK = '1w'  # 周
    MONTH = '1M'  # 月
    SEASON = 'season'  # 季
    YEAR = '1y'  # 年
