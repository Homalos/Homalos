#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : constants
@Date       : 2025/5/28 15:05
@Author     : Donny
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 交易平台中使用的通用常量枚举。
General constant enums used in the trading platform.
"""
from enum import Enum


class Direction(Enum):
    """
    订单/交易/仓位的方向。
    Direction of order/trade/position.
    """
    LONG = "long"  # 多
    SHORT = "short"  # 空
    NET = "net"  # 净


class Offset(Enum):
    """
    订单的开平仓方向。
    Offset of order/trade.
    """
    NONE = ""
    OPEN = "open"  # 开
    CLOSE = "close"  # 平
    CLOSE_TODAY = "close_today"  # 平今
    CLOSE_YESTERDAY = "close_yesterday"  # 平昨


class Status(Enum):
    """
    订单状态。
    Order status.
    """
    SUBMITTING = "submitting"  # 提交中
    NOT_TRADED = "not_traded"  # 未成交
    PART_TRADED = "part_traded"  # 部分成交
    ALL_TRADED = "all_traded"  # 全部成交
    CANCELLED = "cancelled"  # 已撤销
    REJECTED = "rejected"  # 拒单


class Product(Enum):
    """
    产品类别。
    Product class.
    """
    FUTURES = "期货"
    OPTION = "期权"
    EQUITY = "股票"
    INDEX = "指数"
    FOREX = "外汇"
    SPOT = "现货"
    ETF = "ETF"
    BOND = "债券"
    WARRANT = "权证"
    SPREAD = "价差"
    FUND = "基金"
    CFD = "CFD"
    SWAP = "互换"


class OrderType(Enum):
    """
    订单类型。
    Order type.
    """
    LIMIT = "limit"  # 限价
    MARKET = "market"  # 市价
    STOP = "STOP"
    FAK = "FAK"
    FOK = "FOK"
    RFQ = "询价"


class OptionType(Enum):
    """
    期权类型。
    Option type.
    """
    CALL = "看涨期权"
    PUT = "看跌期权"


class Exchange(Enum):
    """
    交易所。
    Exchange.
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
    SHHK = "SHHK"           # Shanghai-HK Stock Connect
    SZHK = "SZHK"           # Shenzhen-HK Stock Connect
    SGE = "SGE"             # Shanghai Gold Exchange
    WXE = "WXE"             # Wuxi Steel Exchange
    CFETS = "CFETS"         # CFETS Bond Market Maker Trading System
    XBOND = "XBOND"         # CFETS X-Bond Anonymous Trading System

    # Global
    NYSE = "NYSE"  # New York Stock Exchnage
    NASDAQ = "NASDAQ"  # Nasdaq Exchange
    SEHK = "SEHK"  # Stock Exchange of Hong Kong

    # Special Function
    LOCAL = "LOCAL"         # For local generated data


class Currency(Enum):
    """
    货币。
    Currency.
    """
    CNY = "CNY"


class Interval(Enum):
    """
    K线时间单位。
    Interval of bar data.
    """
    MINUTE = "1m"
    HOUR = "1h"
    DAILY = "d"
    WEEKLY = "w"
    TICK = "tick"
