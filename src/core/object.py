#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : object
@Date       : 2025/5/28 15:11
@Author     : Donny
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 交易平台中用于一般交易功能的基本数据结构。
"""
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime as Datetime
from typing import Any, Dict, Optional, List

from src.config.constant import Direction, Exchange, Interval, Offset, OptionType, OrderType, Product, Status


ACTIVE_STATUSES = {Status.SUBMITTING, Status.NOT_TRADED, Status.PART_TRADED}


@dataclass
class BaseData:
    """
    任何数据对象都需要一个网关名称作为源，并且应该继承基础数据。
    Any data object needs a gateway_name as source
    and should inherit base data.
    """

    gateway_name: str
    extra: dict | None = field(default=None, init=False)


@dataclass
class TickData(BaseData):
    """
    报价数据包含以下信息：
        * 市场最新交易
        * 订单簿快照
        * 日内市场统计数据。
    """
    symbol: str = None
    exchange: Exchange = None
    datetime: Datetime = None

    trading_day: str = None  # 交易日
    instrument_id: str = None  # 合约代码
    exchange_id: str = None  # 交易所代码
    exchange_inst_id: str = None  # 合约在交易所的代码
    last_price: float = 0.0  # 最新价
    pre_settlement_price: float = 0.0  # 上次结算价
    pre_close_price: float = 0.0  # 昨收盘
    pre_open_interest: float = 0.0  # 昨持仓量
    open_price: float = 0.0  # 今开盘
    highest_price: float = 0.0  # 最高价
    lowest_price: float = 0.0  # 最低价
    volume: float = 0.0  # 数量
    turnover: float = 0.0  # 成交金额
    open_interest: float = 0.0  # 持仓量
    close_price: float = 0.0  # 今收盘
    settlement_price: float = 0.0  # 本次结算价
    upper_limit_price: float = 0.0  # 涨停板价
    lower_limit_price: float = 0.0  # 跌停板价
    pre_delta: float = 0.0  # 昨虚实度
    curr_delta: float = 0.0  # 今虚实度
    update_time: str = None  # 最后修改时间
    update_millisec: int = 0  # 最后修改毫秒
    bid_price_1: float = 0.0  # 申买价一
    bid_volume_1: float = 0.0  # 申买量一
    ask_price_1: float = 0.0  # 申卖价一
    ask_volume_1: float = 0.0  # 申卖量一
    bid_price_2: float = 0.0  # 申买价二
    bid_volume_2: float = 0.0  # 申卖量二
    ask_price_2: float = 0.0  # 申卖价二
    ask_volume_2: float = 0.0  # 申卖量二
    bid_price_3: float = 0.0  # 申买价三
    bid_volume_3: float = 0.0  # 申买量三
    ask_price_3: float  = 0.0 # 申卖价三
    ask_volume_3: float = 0.0  # 申卖量三
    bid_price_4: float = 0.0  # 申买价四
    bid_volume_4: float = 0.0  # 申买量四
    ask_price_4: float = 0.0  # 申卖价四
    ask_volume_4: float = 0.0  # 申卖量四
    bid_price_5: float = 0.0  # 申买价五
    bid_volume_5: float = 0.0  # 申买量五
    ask_price_5: float = 0.0  # 申卖价五
    ask_volume_5: float = 0.0  # 申卖量五
    average_price: float = 0.0  # 当日均价
    action_day: str = None  # 业务日期
    banding_upper_price: float = 0.0  # 上带价
    banding_lower_price: float = 0.0  # 下带价

    # symbol: str
    # exchange: Exchange
    # datetime: Datetime
    #
    # name: str = ""
    # volume: float = 0
    # turnover: float = 0
    # open_interest: float = 0
    # last_price: float = 0
    # last_volume: float = 0
    # limit_up: float = 0
    # limit_down: float = 0
    #
    # open_price: float = 0
    # high_price: float = 0
    # low_price: float = 0
    # pre_close: float = 0

    # bid_price_1: float = 0
    # bid_price_2: float = 0
    # bid_price_3: float = 0
    # bid_price_4: float = 0
    # bid_price_5: float = 0
    #
    # ask_price_1: float = 0
    # ask_price_2: float = 0
    # ask_price_3: float = 0
    # ask_price_4: float = 0
    # ask_price_5: float = 0
    #
    # bid_volume_1: float = 0
    # bid_volume_2: float = 0
    # bid_volume_3: float = 0
    # bid_volume_4: float = 0
    # bid_volume_5: float = 0
    #
    # ask_volume_1: float = 0
    # ask_volume_2: float = 0
    # ask_volume_3: float = 0
    # ask_volume_4: float = 0
    # ask_volume_5: float = 0
    #
    # localtime: Datetime | None = None

    def __post_init__(self) -> None:
        """在初始化之后执行的函数。"""
        self.symbol: str = self.instrument_id

        if self.exchange_id and self.exchange_id.upper() in Exchange.__members__.values():
            self.exchange: Exchange = Exchange(self.exchange_id)

        self.ho_symbol: str = f"{self.symbol}.{self.exchange.value}"


@dataclass
class BarData(BaseData):
    """
    特定交易周期的蜡烛图数据。
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
        """在初始化之后执行的函数。"""
        self.ho_symbol: str = f"{self.symbol}.{self.exchange.value}"


@dataclass
class OrderData(BaseData):
    """
    订单数据包含用于跟踪特定订单的最新状态的信息。
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
        """
        初始化对象后执行的函数。
        在对象初始化完成后，该函数会被自动调用。
        """
        self.ho_symbol: str = f"{self.symbol}.{self.exchange.value}"
        self.ho_orderid: str = f"{self.gateway_name}.{self.orderid}"

    def is_active(self) -> bool:
        """
        检查订单是否有效。
        Check if the order is active.
        """
        return self.status in ACTIVE_STATUSES

    def create_cancel_request(self) -> "CancelRequest":
        """
        从订单创建取消请求对象。
        Create cancel request object from order.
        """
        req: CancelRequest = CancelRequest(
            orderid=self.orderid, symbol=self.symbol, exchange=self.exchange
        )
        return req


@dataclass
class TradeData(BaseData):
    """
    交易数据包含订单成交信息。一个订单可以有多个交易成交。
    Trade data contains information of a fill of an order. One order
    can have several trade fills.
    """
    symbol: str
    exchange: Exchange
    orderid: str
    trade_id: str
    direction: Direction | None = None

    offset: Offset = Offset.NONE
    price: float = 0
    volume: float = 0
    datetime: Datetime | None = None

    def __post_init__(self) -> None:
        """在初始化之后执行的函数。"""
        self.ho_symbol: str = f"{self.symbol}.{self.exchange.value}"
        self.ho_orderid: str = f"{self.gateway_name}.{self.orderid}"
        self.ho_trade_id: str = f"{self.gateway_name}.{self.trade_id}"


@dataclass
class PositionData(BaseData):
    """
    Position数据用于跟踪每个单独的位置持有情况。
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
        """在初始化之后执行的函数。"""
        self.ho_symbol: str = f"{self.symbol}.{self.exchange.value}"
        self.ho_position_id: str = f"{self.gateway_name}.{self.ho_symbol}.{self.direction.value}"


@dataclass
class AccountData(BaseData):
    """
    账户数据包含余额、冻结和可用信息。
    Account data contains information about balance, frozen and
    available.
    """
    account_id: str

    balance: float = 0
    frozen: float = 0

    def __post_init__(self) -> None:
        """在初始化之后执行的函数。"""
        self.available: float = self.balance - self.frozen
        self.ho_account_id: str = f"{self.gateway_name}.{self.account_id}"


@dataclass
class LogData(BaseData):
    """
    日志数据用于在控制台或日志文件中记录日志消息。
    """
    msg: str
    level: int | str = "INFO"

    def __post_init__(self) -> None:
        """在初始化之后执行的函数。"""
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


@dataclass
class QuoteData(BaseData):
    """
    报价数据包含用于跟踪特定报价的最新状态的信息。
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
        """
        初始化后处理函数。
        Args:
            无参数。
        Returns:
            None
        """
        """"""
        self.ho_symbol: str = f"{self.symbol}.{self.exchange.value}"
        self.ho_quote_id: str = f"{self.gateway_name}.{self.quote_id}"

    def is_active(self) -> bool:
        """
        检查报价是否有效。
        Check if the quote is active.
        """
        return self.status in ACTIVE_STATUSES

    def create_cancel_request(self) -> "CancelRequest":
        """
        从报价中创建取消请求对象。
        Create cancel request object from quote.
        """
        req: CancelRequest = CancelRequest(
            orderid=self.quote_id, symbol=self.symbol, exchange=self.exchange
        )
        return req


@dataclass
class SubscribeRequest:
    """
    请求发送到特定网关以订阅报价数据更新。
    Request sending to specific gateway for subscribing tick data update.
    """
    symbol: str
    exchange: Exchange

    def __post_init__(self) -> None:
        """
        初始化后处理函数。
        Args:
            无参数。
        Returns:
            None
        """
        """"""
        self.ho_symbol: str = f"{self.symbol}.{self.exchange.value}"


@dataclass
class OrderRequest:
    """
    请求发送到特定网关以创建新订单。
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
        """
        在对象初始化之后调用此方法，用于对对象进行一些后续处理。
        Args:
            无参数。
        Returns:
            None
        """
        """"""
        self.ho_symbol: str = f"{self.symbol}.{self.exchange.value}"

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式，用于JSON序列化"""
        return {
            "symbol": self.symbol,
            "exchange": self.exchange.value if hasattr(self.exchange, 'value') else str(self.exchange),
            "direction": self.direction.value if hasattr(self.direction, 'value') else str(self.direction),
            "type": self.type.value if hasattr(self.type, 'value') else str(self.type),
            "volume": self.volume,
            "price": self.price,
            "offset": self.offset.value if hasattr(self.offset, 'value') else str(self.offset),
            "reference": self.reference,
            "ho_symbol": getattr(self, 'ho_symbol', f"{self.symbol}.{self.exchange}")
        }

    def create_order_data(self, orderid: str, gateway_name: str) -> OrderData:
        """
        根据请求创建订单数据。
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
    请求发送到特定网关以取消现有订单。
    Request sending to specific gateway for canceling an existing order.
    """
    orderid: str
    symbol: str
    exchange: Exchange

    def __post_init__(self) -> None:
        """在初始化之后执行的函数。"""
        self.ho_symbol: str = f"{self.symbol}.{self.exchange.value}"


@dataclass
class HistoryRequest:
    """
    向特定网关发送查询历史数据的请求。
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
    请求发送到特定网关以创建新的报价。
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
        """在初始化之后执行的函数。"""
        self.ho_symbol: str = f"{self.symbol}.{self.exchange.value}"

    def create_quote_data(self, quote_id: str, gateway_name: str) -> QuoteData:
        """
        根据请求创建报价数据。
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


@dataclass
class StrategyInfo:
    """策略信息"""
    strategy_id: str
    strategy_name: str
    instance: Any
    status: str  # "loading", "loaded", "running", "stopped", "error"
    params: Dict[str, Any]
    strategy_uuid: Optional[str] = None  # 策略UUID唯一标识
    strategy_path: Optional[str] = None  # 策略文件路径
    start_time: Optional[float] = None
    stop_time: Optional[float] = None
    error_message: Optional[str] = None


@dataclass
class RiskCheckResult:
    """风控检查结果"""
    passed: bool
    order_id: str
    reasons: List[str]
    risk_level: str  # "low", "medium", "high", "critical"


@dataclass
class OrderInfo:
    """订单信息扩展"""
    order_data: OrderData
    strategy_id: str
    create_time: float
    update_time: float
    risk_check_result: RiskCheckResult = None

@dataclass
class PerformanceMetrics:
    """性能指标数据类"""
    strategy_id: str

    # 延迟指标
    order_latencies: deque = field(default_factory=lambda: deque(maxlen=1000))
    avg_order_latency: float = 0.0
    max_order_latency: float = 0.0
    min_order_latency: float = float('inf')

    # 交易指标
    total_orders: int = 0
    successful_orders: int = 0
    failed_orders: int = 0
    total_trades: int = 0

    # 盈亏指标
    total_pnl: float = 0.0
    max_draw_down: float = 0.0
    win_count: int = 0
    loss_count: int = 0

    # 性能指标
    tick_processing_rate: float = 0.0
    last_tick_time: float = 0.0
    tick_count: int = 0

    # 时间戳
    start_time: float = field(default_factory=time.time)
    last_update: float = field(default_factory=time.time)

@dataclass
class SystemMetrics:
    """
    系统性能指标
    """
    # CPU和内存
    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    memory_percent: float = 0.0

    # 系统指标
    active_strategies: int = 0
    total_events: int = 0
    event_processing_rate: float = 0.0

    # 网络和延迟
    network_latency: float = 0.0
    system_uptime: float = 0.0

    # 时间戳
    timestamp: float = field(default_factory=time.time)
