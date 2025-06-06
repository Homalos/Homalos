#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : object
@Date       : 2025/5/28 15:11
@Author     : Donny
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: Basic data structure used for general trading function in the trading platform.
"""
from dataclasses import dataclass, field
from datetime import datetime as Datetime
from enum import Enum
from typing import Optional

from src.config.constants import Direction, Exchange, Interval, Offset, OptionType, OrderType, Product, Status

INFO: int = 20

ACTIVE_STATUSES = {Status.SUBMITTING, Status.NOT_TRADED, Status.PART_TRADED}


@dataclass
class BaseData:
    """
    Any data object needs a gateway_name as source
    and should inherit base data.
    """

    gateway_name: str

    extra: dict | None = field(default=None, init=False)


@dataclass
class TickData(BaseData):
    """
    Tick data contains information about:
        * last trade in market
        * orderbook snapshot
        * intraday market statistics.
    """

    symbol: str
    exchange: Exchange
    datetime: Datetime

    name: str = ""
    volume: float = 0
    turnover: float = 0
    open_interest: float = 0
    last_price: float = 0
    last_volume: float = 0
    limit_up: float = 0
    limit_down: float = 0

    open_price: float = 0
    high_price: float = 0
    low_price: float = 0
    pre_close: float = 0

    bid_price_1: float = 0
    bid_price_2: float = 0
    bid_price_3: float = 0
    bid_price_4: float = 0
    bid_price_5: float = 0

    ask_price_1: float = 0
    ask_price_2: float = 0
    ask_price_3: float = 0
    ask_price_4: float = 0
    ask_price_5: float = 0

    bid_volume_1: float = 0
    bid_volume_2: float = 0
    bid_volume_3: float = 0
    bid_volume_4: float = 0
    bid_volume_5: float = 0

    ask_volume_1: float = 0
    ask_volume_2: float = 0
    ask_volume_3: float = 0
    ask_volume_4: float = 0
    ask_volume_5: float = 0

    localtime: Datetime | None = None

    def __post_init__(self) -> None:
        """"""
        self.ho_symbol: str = f"{self.symbol}.{self.exchange.value}"


@dataclass
class BarData(BaseData):
    """
    Candlestick bar data of a certain trading period.
    """

    symbol: str
    exchange: Exchange
    datetime: Datetime

    interval: Interval | None = None
    volume: float = 0
    turnover: float = 0
    open_interest: float = 0
    open_price: float = 0
    high_price: float = 0
    low_price: float = 0
    close_price: float = 0

    def __post_init__(self) -> None:
        """"""
        self.ho_symbol: str = f"{self.symbol}.{self.exchange.value}"


@dataclass
class OrderData(BaseData):
    """
    Order data contains information for tracking latest status
    of a specific order.
    """

    symbol: str
    exchange: Exchange
    orderid: str

    type: OrderType = OrderType.LIMIT
    direction: Direction | None = None
    offset: Offset = Offset.NONE
    price: float = 0
    volume: float = 0
    traded: float = 0
    status: Status = Status.SUBMITTING
    datetime: Datetime | None = None
    reference: str = ""

    def __post_init__(self) -> None:
        """"""
        self.ho_symbol: str = f"{self.symbol}.{self.exchange.value}"
        self.ho_orderid: str = f"{self.gateway_name}.{self.orderid}"

    def is_active(self) -> bool:
        """
        Check if the order is active.
        """
        return self.status in ACTIVE_STATUSES

    def create_cancel_request(self) -> "CancelRequest":
        """
        Create cancel request object from order.
        """
        req: CancelRequest = CancelRequest(
            orderid=self.orderid, symbol=self.symbol, exchange=self.exchange
        )
        return req


@dataclass
class TradeData(BaseData):
    """
    Trade data contains information of a fill of an order. One order
    can have several trade fills.
    """

    symbol: str
    exchange: Exchange
    orderid: str
    tradeid: str
    direction: Direction | None = None

    offset: Offset = Offset.NONE
    price: float = 0
    volume: float = 0
    datetime: Datetime | None = None

    def __post_init__(self) -> None:
        """"""
        self.ho_symbol: str = f"{self.symbol}.{self.exchange.value}"
        self.ho_orderid: str = f"{self.gateway_name}.{self.orderid}"
        self.ho_tradeid: str = f"{self.gateway_name}.{self.tradeid}"


@dataclass
class PositionData(BaseData):
    """
    Position data is used for tracking each individual position holding.
    """

    symbol: str
    exchange: Exchange
    direction: Direction

    volume: float = 0
    frozen: float = 0
    price: float = 0
    pnl: float = 0
    yd_volume: float = 0

    def __post_init__(self) -> None:
        """"""
        self.ho_symbol: str = f"{self.symbol}.{self.exchange.value}"
        self.ho_position_id: str = f"{self.gateway_name}.{self.ho_symbol}.{self.direction.value}"


@dataclass
class AccountData(BaseData):
    """
    Account data contains information about balance, frozen and
    available.
    """

    account_id: str

    balance: float = 0
    frozen: float = 0

    def __post_init__(self) -> None:
        """"""
        self.available: float = self.balance - self.frozen
        self.ho_account_id: str = f"{self.gateway_name}.{self.account_id}"


@dataclass
class LogData(BaseData):
    """
    日志数据用于在控制台或日志文件中记录日志消息。
    """
    msg: str
    level: int | str = INFO
    origin: Optional[str] = None

    def __post_init__(self) -> None:
        """"""
        self.time: Datetime = Datetime.now()


@dataclass
class ContractData(BaseData):
    """
    合约数据包含每份交易合约的基本信息。
    """

    symbol: str
    exchange: Exchange
    name: str
    product: Product
    size: float
    price_tick: float

    min_volume: float = 1                   # minimum order volume
    max_volume: float | None = None      # maximum order volume
    stop_supported: bool = False            # whether server supports stop order
    net_position: bool = False              # whether gateway uses net position volume
    history_data: bool = False              # whether gateway provides bar history data

    option_strike: float | None = None
    option_underlying: str | None = None     # ho_symbol of underlying contract
    option_type: OptionType | None = None
    option_listed: Datetime | None = None
    option_expiry: Datetime | None = None
    option_portfolio: str | None = None
    option_index: str | None = None          # for identifying options with same strike price

    def __post_init__(self) -> None:
        """"""
        self.ho_symbol: str = f"{self.symbol}.{self.exchange.value}"


class GatewayConnectionStatus(Enum):
    """
    网关连接状态枚举。
    """
    CONNECTING = "CONNECTING"
    CONNECTED = "CONNECTED"
    DISCONNECTED = "DISCONNECTED"
    ERROR = "ERROR"


@dataclass
class GatewayStatusData(BaseData):
    """
    网关状态数据。
    """
    status: GatewayConnectionStatus
    message: Optional[str] = None

    # gateway_name is inherited from BaseData


@dataclass
class QuoteData(BaseData):
    """
    Quote data contains information for tracking latest status
    of a specific quote.
    """

    symbol: str
    exchange: Exchange
    quote_id: str

    bid_price: float = 0.0
    bid_volume: int = 0
    ask_price: float = 0.0
    ask_volume: int = 0
    bid_offset: Offset = Offset.NONE
    ask_offset: Offset = Offset.NONE
    status: Status = Status.SUBMITTING
    datetime: Datetime | None = None
    reference: str = ""

    def __post_init__(self) -> None:
        """"""
        self.ho_symbol: str = f"{self.symbol}.{self.exchange.value}"
        self.ho_quote_id: str = f"{self.gateway_name}.{self.quote_id}"

    def is_active(self) -> bool:
        """
        Check if the quote is active.
        """
        return self.status in ACTIVE_STATUSES

    def create_cancel_request(self) -> "CancelRequest":
        """
        Create cancel request object from quote.
        """
        req: CancelRequest = CancelRequest(
            orderid=self.quote_id, symbol=self.symbol, exchange=self.exchange
        )
        return req


@dataclass
class SubscribeRequest:
    """
    Request sending to specific gateway for subscribing tick data update.
    """

    symbol: str
    exchange: Exchange

    def __post_init__(self) -> None:
        """"""
        self.ho_symbol: str = f"{self.symbol}.{self.exchange.value}"


@dataclass
class OrderRequest:
    """
    Request sending to specific gateway for creating a new order.
    """

    symbol: str
    exchange: Exchange
    direction: Direction
    type: OrderType
    volume: float
    price: float = 0
    offset: Offset = Offset.NONE
    reference: str = ""

    def __post_init__(self) -> None:
        """"""
        self.ho_symbol: str = f"{self.symbol}.{self.exchange.value}"

    def create_order_data(self, orderid: str, gateway_name: str) -> OrderData:
        """
        Create order data from request.
        """
        order: OrderData = OrderData(
            symbol=self.symbol,
            exchange=self.exchange,
            orderid=orderid,
            type=self.type,
            direction=self.direction,
            offset=self.offset,
            price=self.price,
            volume=self.volume,
            reference=self.reference,
            gateway_name=gateway_name,
        )
        return order


@dataclass
class CancelRequest:
    """
    Request sending to specific gateway for canceling an existing order.
    """

    orderid: str
    symbol: str
    exchange: Exchange

    def __post_init__(self) -> None:
        """"""
        self.ho_symbol: str = f"{self.symbol}.{self.exchange.value}"


@dataclass
class HistoryRequest:
    """
    Request sending to specific gateway for querying history data.
    """

    symbol: str
    exchange: Exchange
    start: Datetime
    end: Datetime | None = None
    interval: Interval | None = None

    def __post_init__(self) -> None:
        """"""
        self.ho_symbol: str = f"{self.symbol}.{self.exchange.value}"


@dataclass
class QuoteRequest:
    """
    Request sending to specific gateway for creating a new quote.
    """

    symbol: str
    exchange: Exchange
    bid_price: float
    bid_volume: int
    ask_price: float
    ask_volume: int
    bid_offset: Offset = Offset.NONE
    ask_offset: Offset = Offset.NONE
    reference: str = ""

    def __post_init__(self) -> None:
        """"""
        self.ho_symbol: str = f"{self.symbol}.{self.exchange.value}"

    def create_quote_data(self, quote_id: str, gateway_name: str) -> QuoteData:
        """
        Create quote data from request.
        """
        quote: QuoteData = QuoteData(
            symbol=self.symbol,
            exchange=self.exchange,
            quote_id=quote_id,
            bid_price=self.bid_price,
            bid_volume=self.bid_volume,
            ask_price=self.ask_price,
            ask_volume=self.ask_volume,
            bid_offset=self.bid_offset,
            ask_offset=self.ask_offset,
            reference=self.reference,
            gateway_name=gateway_name,
        )
        return quote
