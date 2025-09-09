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
"""
from dataclasses import dataclass, field

from src.core.constants import Exchange, OrderType, Direction, Offset, Product


@dataclass
class BaseData:
    """
    任何数据对象都需要一个名称作为来源，并且应该继承基础数据。

    Any data object needs a name to originate from and should inherit from a base data.
    """
    source_name: str = ""
    extra: dict | None = field(default=None, init=False)


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
    symbol: str = None
    exchange: Exchange = None

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
