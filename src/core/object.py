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

1. 使用@dataclass装饰器来修饰一个类。
2. 使用@dataclass装饰器可以方便地定义一个数据类。数据类通常用于存储数据，并自动生成诸如__init__、__repr__、__eq__等特殊方法。
3. 在类中定义字段，使用类型注解来指定字段的类型。
4. 后初始化处理，可以用def __post_init__(self)
5. 类型提示必需：所有字段必须明确标注类型（如str、int），或用typing.Any表示任意类型
6. 可变默认值：列表、字典等可变默认值需用field(default_factory=list)避免所有实例共享引用
7. 继承行为：父类和子类的字段按声明顺序合并，但需注意字段顺序冲突
"""
from dataclasses import dataclass, field
from datetime import datetime

from src.core.constants import Exchange, OrderType, Direction, Offset, Product, OptionType, OrderStatus, Interval


@dataclass
class BaseData:
    """
    任何数据对象都需要一个名称作为来源，并且应该继承基础数据。
    Any data object needs a name to originate from and should inherit from a base data.
    """
    source_name: str = ""
    # 可变默认值需使用field，init=False：不包含在__init__参数中
    extra: dict | None = field(default=None, init=False)


@dataclass
class TickData(BaseData):
    """
    tick报价数据包含以下信息：
        1. 市场最新交易
        2. 订单簿快照
        3. 日内市场统计数据
    """
    trading_day: str = None
    exchange_id: Exchange = None
    last_price: float = 0.0
    pre_settlement_price: float = 0.0
    pre_close_price: float = 0.0
    pre_open_interest: float = 0.0
    open_price: float = 0.0
    highest_price: float = 0.0
    lowest_price: float = 0.0
    volume: int = 0
    turnover: float = 0.0
    open_interest: float = 0.0
    close_price: float = 0.0
    settlement_price: float = 0.0
    upper_limit_price: float = 0.0
    lower_limit_price: float = 0.0
    pre_delta: float = 0.0
    curr_delta: float = 0.0
    update_time: str = None
    update_millisec: int = 0
    bid_price_1: float = 0.0
    bid_volume_1: int = 0.0
    ask_price_1: float = 0.0
    ask_volume_1: int = 0
    bid_price_2: float = 0.0
    bid_volume_2: int = 0
    ask_price_2: float = 0.0
    ask_volume_2: int = 0
    bid_price_3: float = 0.0
    bid_volume_3: int = 0
    ask_price_3: float = 0.0
    ask_volume_3: int = 0
    bid_price_4: float = 0.0
    bid_volume_4: int = 0
    ask_price_4: float = 0.0
    ask_volume_4: int = 0
    bid_price_5: float = 0.0
    bid_volume_5: int = 0
    ask_price_5: float = 0.0
    ask_volume_5: int = 0
    average_price: float = 0.0
    action_day: str = None
    instrument_id: str = None
    exchange_inst_id: str = None
    banding_upper_price: float = 0.0
    banding_lower_price: float = 0.0
    # 时间戳，自定义的字段，在原始数据中不存在
    timestamp: datetime = None


@dataclass
class BarData(BaseData):
    """
    特定交易周期的蜡烛图数据
    Candlestick bar data of a certain trading period.
    """
    bar_type: Interval = None
    update_time: datetime = None
    instrument_id: str = None
    exchange_id: Exchange = None
    volume: int = 0
    open_interest: float = 0.0
    open_price: float = 0.0
    high_price: float = 0.0
    low_price: float = float('inf')
    close_price: float = 0.0
    last_volume: int = 0  # 上一根K线的成交量，用于计算当前K线的成交量

@dataclass
class OrderData(BaseData):
    """
    订单数据
    """
    instrument_id: str = None
    exchange_id: Exchange = None
    order_id: str = None

    order_type: OrderType = OrderType.LIMIT  # 报单类型
    direction: Direction | None = None  # 买卖方向
    offset: Offset = Offset.NONE  # 组合开平标志
    price: float = 0.0  # 价格
    volume: int = 0  # 数量
    volume_traded: int = 0  # 今成交数量
    order_status: OrderStatus = OrderStatus.SUBMITTING  # 报单状态
    timestamp: datetime = None

    def create_cancel_request(self) -> "CancelRequest":
        """
        根据订单信息创建撤单请求对象。
        Create cancel request object from order.
        """
        req: CancelRequest = CancelRequest(
            order_id=self.order_id, instrument_id=self.instrument_id, exchange_id=self.exchange_id
        )
        return req


@dataclass
class TradeData(BaseData):
    """
    交易数据包含订单成交的相关信息。一个订单可能包含多个成交记录。
    Trade data contains information of a fill of an order. One order can have several trade fills.
    """
    instrument_id: str = None
    exchange_id: Exchange = None
    order_id: str = None  # 报单编号
    trade_id: str = None  # 成交编号
    direction: Direction = None  # 买卖方向

    offset: Offset = Offset.NONE  # 开平标志
    price: float = 0.0  # 价格
    volume: int = 0  # 数量
    timestamp: datetime = None


@dataclass
class PositionData(BaseData):
    """
    Position数据用于跟踪每个单独的位置持有情况。
    Position data is used for tracking each individual position holding.
    """
    instrument_id: str = None
    exchange_id: Exchange = None
    direction: Direction = None

    volume: int = 0
    frozen: float = 0.0
    price: float = 0.0
    pnl: float = 0.0
    yd_volume: int = 0  # 上日成交量


@dataclass
class PositionDetailData(BaseData):
    """
    PositionDetailData数据用于跟踪持仓明细。
    """
    strategy_id: int = 0
    open_price_list: list[float] = None


@dataclass
class AccountData(BaseData):
    """
    账户数据包含余额、冻结和可用信息。
    Account data contains information about balance, frozen and available.
    """
    account_id: str = None
    balance: float = 0.0
    frozen: float = 0.0

    def __post_init__(self) -> None:
        self.available: float = self.balance - self.frozen

@dataclass
class ContractData(BaseData):
    """
    合约数据包含每份交易合约的基本信息。
    """
    instrument_id: str =  None
    exchange_id: Exchange = None
    instrument_name: str = None
    product: Product = None
    size: int = 0
    price_tick: float = 0.0

    min_volume: int = 1           # 最小成交量
    max_volume: int = None        # 最大成交量
    stop_supported: bool = False    # 是否支持 stop order
    net_position: bool = False      # 网关是否使用净持仓量
    history_data: bool = False      # 网关是否提供K线历史数据

    option_strike: float = 0.0
    option_underlying: str = None     # vt_symbol of underlying contract
    option_type: OptionType = None
    option_listed: datetime = None
    option_expiry: datetime = None
    option_portfolio: str = None
    option_index: str = None          # for identifying options with same strike price

# ================== 请求 ==================
@dataclass
class SubscribeRequest:
    """
    请求发送到特定网关以订阅报价数据更新。
    Request sending to specific gateway for subscribing tick data update.
    """
    instrument_id: str = None
    exchange_id: Exchange = None


@dataclass
class OrderRequest:
    """
    订单委托请求
    Request sending to specific gateway for creating a new order.
    """
    instrument_id: str = None
    exchange_id: Exchange = None
    direction: Direction = None
    order_type: OrderType = None
    volume: int = 0
    price: float = 0.0
    offset: Offset = Offset.NONE

    def create_order_data(self, order_id: str) -> OrderData:
        """
        根据请求创建订单数据。
        Create order data from request.
        """
        order: OrderData = OrderData(
            instrument_id=self.instrument_id,
            exchange_id=self.exchange_id,
            order_id=order_id,
            order_type=self.order_type,
            direction=self.direction,
            price=self.price,
            volume=self.volume,
            offset = self.offset
        )
        return order


@dataclass
class CancelRequest:
    """
    撤销订单委托请求
    Request sending to specific gateway for canceling an existing order.
    """
    order_id: str = None
    instrument_id: str = None
    exchange_id: Exchange = None


@dataclass
class HistoryRequest:
    """
    向特定网关发送请求以查询历史数据。
    Request sending to specific gateway for querying history data.
    """
    instrument_id: str = None
    exchange_id: Exchange = None
    start_datetime: datetime = None
    end_datetime: datetime = None
    interval: Interval = None


@dataclass
class TradingSchedule:
    """交易时间配置"""
    init_strategy_times: list[str] = field(default_factory=lambda: [""])
    login_times: list[str] = field(default_factory=lambda: [""])
    before_open_times: list[str] = field(default_factory=lambda: [""])
    sub_id_times: list[str] = field(default_factory=lambda: [""])
    after_close_times: list[str] = field(default_factory=lambda: [""])
    check_interval: int = 60  # 检查间隔（秒）
