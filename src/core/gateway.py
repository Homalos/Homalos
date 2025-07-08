from abc import ABC, abstractmethod

from src.core.event import Event
from .event_bus import EventBus
from .event_type import EventType

from .object import (
    AccountData,
    BarData,
    CancelRequest,
    ContractData,
    Exchange,
    HistoryRequest,
    LogData,
    OrderData,
    OrderRequest,
    PositionData,
    QuoteData,
    QuoteRequest,
    SubscribeRequest,
    TickData,
    TradeData,
)


class BaseGateway(ABC):
    """
    用于创建连接到不同交易系统的网关的抽象网关类。

    # 如何实现网关：

    ---
    ## 基础知识
    网关应满足：
    * 此类应是线程安全的：
    * 所有方法均应是线程安全的
    * 对象之间不存在可变的共享属性。
    * 所有方法均应是非阻塞的
    * 满足文档字符串中针对每个方法和回调函数编写的所有要求。
    * 连接断开时自动重新连接。

    ---
    ## 方法必须实现：
    所有 @abstractmethod

    ---
    ## 回调函数必须手动响应：
    * on_tick
    * on_trade
    * on_order
    * on_position
    * on_account
    * on_contract

    传递给回调函数的所有 XxxData 均应为常量，这意味着
    该对象在传递给 on_xxxx 后不应被修改。
    因此，如果您使用缓存来存储数据的引用，请在将数据传递给 on_xxxx 之前使用 copy.copy 创建一个新对象。
    """

    # Default name for the gateway.
    default_name: str = ""

    # Fields required in setting dict for connect function.
    default_setting: dict[str, str | int | float | bool] = {}

    # Exchanges supported in the gateway.
    exchanges: list[Exchange] = []

    def __init__(self, event_bus: EventBus, name: str) -> None:
        """"""
        self.event_bus: EventBus = event_bus
        self.name: str = name

    def on_event(self, event_type: str, data: object = None) -> None:
        """
        General event push.
        """
        event: Event = Event(event_type, data)
        self.event_bus.put_sync(event)

    def on_tick(self, tick: TickData) -> None:
        """
        Tick event push.
        Tick event of a specific ho_symbol is also pushed.
        """
        self.on_event(EventType.TICK.value, tick)
        self.on_event(EventType.TICK.value + tick.ho_symbol, tick)

    def on_trade(self, trade: TradeData) -> None:
        """
        Trade event push.
        Trade event of a specific ho_symbol is also pushed.
        """
        self.on_event(EventType.TRADE.value, trade)
        self.on_event(EventType.TRADE.value + trade.ho_symbol, trade)

    def on_order(self, order: OrderData) -> None:
        """
        Order event push.
        Order event of a specific ho_orderid is also pushed.
        """
        self.on_event(EventType.ORDER.value, order)
        self.on_event(EventType.ORDER.value + order.ho_orderid, order)

    def on_position(self, position: PositionData) -> None:
        """
        Position event push.
        Position event of a specific ho_symbol is also pushed.
        """
        self.on_event(EventType.POSITION.value, position)
        self.on_event(EventType.POSITION.value + position.ho_symbol, position)

    def on_account(self, account: AccountData) -> None:
        """
        Account event push.
        Account event of a specific ho_account_id is also pushed.
        """
        self.on_event(EventType.ACCOUNT.value, account)
        self.on_event(EventType.ACCOUNT.value + account.ho_account_id, account)

    def on_quote(self, quote: QuoteData) -> None:
        """
        Quote event push.
        Quote event of a specific ho_symbol is also pushed.
        """
        self.on_event(EventType.QUOTE.value, quote)
        self.on_event(EventType.QUOTE.value + quote.ho_symbol, quote)

    def on_log(self, log: LogData) -> None:
        """
        Log event push.
        """
        self.on_event(EventType.LOG.value, log)

    def on_contract(self, contract: ContractData) -> None:
        """
        Contract event push.
        """
        self.on_event(EventType.CONTRACT.value, contract)

    def write_log(self, msg: str) -> None:
        """
        Write a log event from gateway.
        """
        log: LogData = LogData(msg=msg, gateway_name=self.name)
        self.on_log(log)

    def write_error(self, msg: str, error: dict) -> None:
        """输出错误信息日志"""
        error_id = error.get("ErrorID", "N/A")
        error_msg = error.get("ErrorMsg", str(error))
        log_msg = f"{msg}，{'代码'}：{error_id}，{'信息'}：{error_msg}"
        self.write_log(log_msg)

    @abstractmethod
    def connect(self, setting: dict) -> None:
        """
        Start gateway connection.

        to implement this method, you must:
        * connect to server if necessary
        * log connected if all necessary connection is established
        * do the following query and response corresponding on_xxxx and write_log
            * contracts : on_contract
            * account asset : on_account
            * account holding: on_position
            * orders of account: on_order
            * trades of account: on_trade
        * if any of query above is failed,  write log.

        future plan:
        response callback/change status instead of write_log

        """
        pass

    @abstractmethod
    def close(self) -> None:
        """
        Close gateway connection.
        """
        pass

    def subscribe(self, req: SubscribeRequest) -> None:
        """
        Subscribe tick data update.
        """
        pass

    def send_order(self, req: OrderRequest) -> str:
        """
        Send a new order to server.

        implementation should finish the tasks blow:
        * create an OrderData from req using OrderRequest.create_order_data
        * assign a unique(gateway instance scope) id to OrderData.orderid
        * send request to server
            * if request is sent, OrderData.status should be set to Status.SUBMITTING
            * if request is failed to sent, OrderData.status should be set to Status.REJECTED
        * response on_order:
        * return vt_orderid

        :return str vt_orderid for created OrderData
        """
        pass

    def cancel_order(self, req: CancelRequest) -> None:
        """
        Cancel an existing order.
        implementation should finish the tasks blow:
        * send request to server
        """
        pass


    def send_quote(self, req: QuoteRequest) -> str:
        """
        向服务器发送新的双边报价。

        实现应完成以下任务：
        * 使用 QuoteRequest.create_quote_data 从请求创建 QuoteData
        * 为 QuoteData.quote_id 分配一个唯一的（网关实例范围）ID
        * 向服务器发送请求
        * 如果请求已发送，则 QuoteData.status 应设置为 Status.SUBMITTING
        * 如果请求发送失败，则 QuoteData.status 应设置为 Status.REJECTED
        * on_quote 响应：
        * 返回 ho_quote_id

        :return str ho_quote_id for created QuoteData
        """
        return ""

    def cancel_quote(self, req: CancelRequest) -> None:
        """
        取消现有报价。
        实施应完成以下任务：
        * 向服务器发送请求
        """
        return

    def query_account(self) -> None:
        """
        Query account balance.
        """
        pass

    def query_position(self) -> None:
        """
        Query holding positions.
        """
        pass

    def query_history(self, req: HistoryRequest) -> list[BarData]:
        """
        Query bar history data.
        """
        return []

    def get_default_setting(self) -> dict[str, str | int | float | bool]:
        """
        Return default setting dict.
        """
        return self.default_setting
