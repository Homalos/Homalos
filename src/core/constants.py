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
from enum import Enum, IntEnum


class ErrorReason(Enum):
    """
    错误原因枚举

    Error reason enum
    """
    REASON_0x1001 = "网络读失败"
    REASON_0x1002 = "网络写失败"
    REASON_0x2001 = "接收心跳超时"
    REASON_0x2002 = "发送心跳失败"
    REASON_0x2003 = "收到错误报文"
    REASON_UNKNOWN = "未知原因"


class Direction(Enum):
    """
    订单/交易/仓位的方向

    Direction of order/trade/position
    """
    LONG = "多"  # 多
    SHORT = "空"  # 空
    NET = "净"  # 净


class Offset(Enum):
    """
    订单的开平仓方向

    Offset of order/trade
    """
    NONE = ""                           # 无
    BUY_OPEN = "buy_open"
    BUY_CLOSE = "buy_close"
    SELL_OPEN = "sell_open"
    SELL_CLOSE = "sell_close"
    CLOSE_TODAY = "close_today"             # 平今
    BUY_CLOSE_TODAY = "buy_close_today"     # 买平今
    SELL_CLOSE_TODAY = "sell_close_today"   # 卖平今
    CLOSE_YESTERDAY = "close_yesterday"     # 平昨

    OPEN = "open"  # 开
    CLOSE = "close"  # 平


class OrderStatus(Enum):
    """
    订单状态

    Order status
    """
    SUBMITTING = "提交中"
    ALL_TRADED = "全部成交"
    PART_TRADED_QUEUEING = "部分成交还在队列中"
    PART_TRADED_NOT_QUEUEING = "部分成交不在队列中"
    NO_TRADE_QUEUEING = "未成交还在队列中"
    NO_TRADE_NOT_QUEUEING = "未成交不在队列中"
    CANCELED = "已撤单"
    REJECTED = "已拒单"


class Product(Enum):
    """
    产品类别

    Product class
    """
    FUTURES = "期货"
    OPTION = "期权"
    SPREAD = "价差"


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
    # 中国交易所
    CFFEX = "CFFEX"         # 中国金融期货交易所 China Financial Futures Exchange
    SHFE = "SHFE"           # 上海期货交易所 Shanghai Futures Exchange
    CZCE = "CZCE"           # 郑州商品交易所 Zhengzhou Commodity Exchange
    DCE = "DCE"             # 大连商品交易所 Dalian Commodity Exchange
    INE = "INE"             # 上海国际能源交易中心 Shanghai International Energy Exchange
    GFEX = "GFEX"           # 广州期货交易所 Guangzhou Futures Exchange
    # SSE = "SSE"             # 上海证券交易所 Shanghai Stock Exchange
    # SZSE = "SZSE"           # 深圳证券交易所 Shenzhen Stock Exchange
    # BSE = "BSE"             # 北京证券交易所 Beijing Stock Exchange


class Currency(Enum):
    """
    货币

    Currency
    """
    CNY = "CNY"


class Interval(Enum):
    """
    K线周期
    Interval of bar data.
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

class OpenDate(Enum):
    """
    开仓日期
    """
    TODAY = "今"
    YESTERDAY = "昨"

# ================= 错误码定义 =================
class ErrorCode(IntEnum):
    """
    系统的错误码，和CTP的错误码有所区别
    详情参考：Homalos 期货量化交易系统 - API 响应规范.md
    """

    # 通用
    SUCCESS = 0
    PARAM_ERROR = 1001              # 参数错误
    AUTH_FAILED = 1002              # 鉴权失败
    PERMISSION_DENIED = 1003        # 权限不足
    TOO_MANY_REQUESTS = 1004        # 请求过于频繁
    NOT_FOUND = 1005                # 数据不存在
    SYSTEM_ERROR = 1006             # 系统繁忙
    UNKNOWN_ERROR = 1999            # 未知错误

    # 行情模块 2xxx
    MARKET_SYMBOL_NOT_FOUND = 2001  # 合约不存在
    MARKET_DELAYED = 2002           # 行情数据延迟
    MARKET_TYPE_INVALID = 2003      # 不支持的行情类型
    MARKET_SUB_EXISTS = 2004        # 订阅已存在

    # 交易模块 3xxx
    TRADE_ORDER_FAILED = 3001       # 下单失败
    TRADE_CANCEL_FAILED = 3002      # 撤单失败
    TRADE_NO_FUNDS = 3003           # 资金不足
    TRADE_RISK_LIMIT = 3004         # 超过风控限制
    TRADE_ORDER_INVALID = 3005      # 无效的订单 ID

    # 风控模块 4xxx
    RISK_CHECK_FAILED = 4001        # 风控检查未通过
    RISK_CONFIG_MISSING = 4002      # 风控配置缺失
    RISK_SERVICE_UNAVAILABLE = 4003 # 风控服务不可用

    # 策略模块 5xxx
    STRATEGY_NOT_FOUND = 5001       # 策略未找到
    STRATEGY_RUNTIME_ERROR = 5002   # 策略运行错误
    STRATEGY_PARAM_INVALID = 5003   # 策略参数无效
    STRATEGY_BLOCKED_BY_RISK = 5004 # 策略被风控阻止

    # 策略模块 5xxx
    DATA_CENTER_START_FAILED = 6001  # 据中心启动失败
    DATA_CENTER__RUNTIME_ERROR = 6002  # 数据中心内部异常
    DATA_CENTER_PARAM_INVALID = 6003  # 配置参数缺失或不合法


class Task(Enum):
    """
    任务类型
    """
    DAILY = "daily"
    ONCE = "once"
    MINUTE = "minute"
    WEEKDAY = "weekday"
    MONTHLY = "monthly"

