#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : object.py
@Date       : 2025/9/8 17:34
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 交易平台中用于一般交易功能的基本数据结构。
使用@dataclass装饰器来修饰一个类。
使用@dataclass装饰器可以方便地定义一个数据类。数据类通常用于存储数据，并自动生成诸如__init__、__repr__、__eq__等特殊方法。
在类中定义字段，使用类型注解来指定字段的类型。
后初始化处理，可以用def __post_init__(self)
类型提示必需：所有字段必须明确标注类型（如str、int），或用typing.Any表示任意类型
可变默认值：列表、字典等可变默认值需用field(default_factory=list)避免所有实例共享引用
继承行为：父类和子类的字段按声明顺序合并，但需注意字段顺序冲突
"""
import datetime
from dataclasses import dataclass, field

from src.core.constants import Exchange, OrderType, Direction, Offset, Product


@dataclass
class BaseData:
    """
    任何数据对象都需要一个名称作为来源，并且应该继承基础数据。

    Any data object needs a name to originate from and should inherit from a base data.
    """
    source_name: str = ""
    extra: dict | None = field(default=None, init=False)  # 可变默认值需使用field，init=False：不包含在__init__参数中


@dataclass
class TickData(BaseData):
    """
    tick报价数据包含以下信息：
        * 市场最新交易
        * 订单簿快照
        * 日内市场统计数据
    """
    trading_day: str = None
    instrument_id: str = None
    exchange_id: Exchange = None
    exchange_inst_id: str = None
    last_price: float = 0
    pre_settlement_price: float = 0
    pre_close_price: float = 0
    pre_open_interest: float = 0
    open_price: float = 0
    highest_price: float = 0
    lowest_price: float = 0
    volume: float = 0
    turnover: float = 0
    open_interest: float = 0
    close_price: float = 0
    settlement_price: float = 0
    upper_limit_price: float = 0
    lower_limit_price: float = 0
    pre_delta = None
    curr_delta = None
    update_time = datetime.time()
    update_millisec: float = 0
    bid_price_1: float = 0
    bid_volume_1: float = 0
    ask_price_1: float = 0
    ask_volume_1: float = 0
    bid_price_2: float = 0
    bid_volume_2: float = 0
    ask_price_2: float = 0
    ask_volume_2: float = 0
    bid_price_3: float = 0
    bid_volume_3: float = 0
    ask_price_3: float = 0
    ask_volume_3: float = 0
    bid_price_4: float = 0
    bid_volume_4: float = 0
    ask_price_4: float = 0
    ask_volume_4: float = 0
    bid_price_5: float = 0
    bid_volume_5: float = 0
    ask_price_5: float = 0
    ask_volume_5: float = 0
    average_price: float = 0
    action_day: str = None
    banding_upper_price: float = 0
    banding_lower_price: float = 0


@dataclass
class BarData(BaseData):
    """
    特定交易周期的蜡烛图数据

    Candlestick bar data of a certain trading period.
    """
    bar_type = None
    update_time: datetime = datetime.time()
    instrument_id: str = None
    exchange_id: Exchange = None
    volume: int = 0
    open_interest: float = 0
    open_price: float = 0
    high_price: float = 0
    low_price = float('inf')
    close_price: float = 0
    last_volume: int = 0  # 上一根K线的成交量，用于计算当前K线的成交量

@dataclass
class OrderData(BaseData):
    """
    订单数据
    """
    instrument_id: str = None
    exchange_id: Exchange = None
    order_id: str = None

    type: OrderType = OrderType.LIMIT
    direction: Direction | None = None
    offset: Offset = Offset.NONE
    price: float = 0
    volume: float = 0
    traded: float = 0


@dataclass
class TradeData(BaseData):
    """
    Trade data contains information of a fill of an order. One order
    can have several trade fills.
    """
    instrument_id: str = None
    exchange_id: Exchange = None
    order_id: str = None
    trade_id: str = None
    direction: Direction = None

    offset: Offset = Offset.NONE
    price: float = 0
    volume: float = 0


@dataclass
class PositionData(BaseData):
    """
    Position数据用于跟踪每个单独的位置持有情况。
    Position data is used for tracking each individual position holding.
    """
    instrument_id: str = None
    exchange_id: Exchange = None
    direction: Direction = None

    volume: float = 0
    frozen: float = 0
    price: float = 0
    pnl: float = 0
    yd_volume: float = 0

@dataclass
class AccountData(BaseData):
    """
    账户数据包含余额、冻结和可用信息。
    Account data contains information about balance, frozen and
    available.
    """
    account_id: str = None
    balance: float = 0
    frozen: float = 0

@dataclass
class ContractData(BaseData):
    """
    合约数据包含每份交易合约的基本信息。
    """
    instrument_id: str =  None
    exchange_id: Exchange = None
    name: str = None
    product: Product = None
    size: float = 0
    price_tick: float = 0

@dataclass
class SubscribeRequest:
    """
    请求发送到特定网关以订阅报价数据更新。
    Request sending to specific gateway for subscribing tick data update.
    """
    instrument_id: str = None
    exchange_id: Exchange = None

