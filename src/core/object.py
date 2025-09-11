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
    symbol: str = None
    exchange: Exchange = None


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
    symbol: str = None
    exchange: Exchange = None
    order_id: str = None

    type: OrderType = OrderType.LIMIT
    direction: Direction | None = None
    offset: Offset = Offset.NONE
    price: float = 0
    volume: float = 0
    traded: float = 0


@dataclass
class PositionData(BaseData):
    """
    Position数据用于跟踪每个单独的位置持有情况。
    Position data is used for tracking each individual position holding.
    """
    symbol: str = None
    exchange: Exchange = None
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
    symbol: str =  None
    exchange: Exchange = None
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
    symbol: str = None
    exchange: Exchange = None

