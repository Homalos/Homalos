#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : basegateway
@Date       : 2025/5/28 15:27
@Author     : Donny
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 网关基类
"""
from abc import ABC, abstractmethod
from typing import Any, Optional
import asyncio

# Import data objects used in type hints
from .object import (
    TickData,
    TradeData,
    OrderData,
    PositionData,
    AccountData,
    ContractData,
    LogData,
    SubscribeRequest, 
    OrderRequest, 
    CancelRequest, 
    QuoteRequest, 
    HistoryRequest, 
    BarData,
    GatewayStatusData,
    GatewayConnectionStatus
)
from src.core.event_engine import EventEngine
from src.core.event import LogEvent, GatewayStatusEvent


class BaseGateway(ABC):

    # 网关的默认名称。
    default_name: str = ""

    # 设置连接函数字典所需的字段。
    default_setting: Any = None

    # 网关支持的交易。
    exchanges: list[str] = []

    def __init__(self, gateway_name: str, event_engine: Optional[EventEngine] = None):
        self.gateway_name: str = gateway_name
        self.event_engine: Optional[EventEngine] = event_engine
        if self.event_engine:
            try:
                self.main_loop = asyncio.get_running_loop()
            except RuntimeError:  # No running event loop
                # 如果 BaseGateway 是在非异步上下文中实例化的，则可能会发生这种情况。
                # 或者在设置异步事件循环之前。
                # 如果使用了 event_engine，则可能需要回退或特殊处理。
                # 在循环正常可用之前。
                # 目前，我们允许它为 None 并在 on_log 中处理。
                self.main_loop = None 
        else:
            self.main_loop = None

    def on_event(self, event_type: str, data: Any = None) -> None:
        pass

    def on_tick(self, tick: TickData) -> None:
        log_data = LogData(msg=f"收到行情: {tick.symbol}", level="DEBUG", gateway_name=self.gateway_name)
        self.on_log(log_data)

    def on_trade(self, trade: TradeData) -> None:
        log_data = LogData(msg=f"收到成交: {trade.symbol}, {trade.orderid}", level="INFO", gateway_name=self.gateway_name)
        self.on_log(log_data)

    def on_order(self, order: OrderData) -> None:
        log_data = LogData(msg=f"收到订单更新: {order.symbol}, {order.orderid}, {order.status}", level="INFO", gateway_name=self.gateway_name)
        self.on_log(log_data)

    def on_position(self, position: PositionData) -> None:
        log_data = LogData(msg=f"收到持仓更新: {position.symbol}, {position.direction}, {position.volume}", level="INFO", gateway_name=self.gateway_name)
        self.on_log(log_data)

    def on_account(self, account: AccountData) -> None:
        log_data = LogData(msg=f"收到账户资金更新: {account.account_id}, 平衡: {account.balance}", level="INFO", gateway_name=self.gateway_name)
        self.on_log(log_data)

    def on_contract(self, contract: ContractData) -> None:
        log_data = LogData(msg=f"收到合约信息: {contract.symbol}", level="INFO", gateway_name=self.gateway_name)
        self.on_log(log_data)

    def on_log(self, log: LogData) -> None:
        if self.event_engine and self.main_loop and self.main_loop.is_running():
            # 检查是否从循环线程调用
            try:
                current_loop = asyncio.get_running_loop()
                if current_loop is self.main_loop:
                    # 已经在主循环的线程中，可以使用create_task
                    asyncio.create_task(self.event_engine.put(LogEvent(data=log)))
                else:
                    # 从另一个线程调用（例如，CTP 线程）
                    asyncio.run_coroutine_threadsafe(self.event_engine.put(LogEvent(data=log)), self.main_loop)
            except RuntimeError: # 当前线程中没有正在运行的循环，因此必须来自另一个线程
                 asyncio.run_coroutine_threadsafe(self.event_engine.put(LogEvent(data=log)), self.main_loop)
        elif self.event_engine: # 主循环未运行或未设置，但引擎存在
            # 这是一个后备或错误情况，直接打印可能是最好的
            timestamp_str = log.time.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3] # Milliseconds
            print(f"{timestamp_str} [{log.level}] [{log.gateway_name or self.gateway_name}] (LogLoopIssue) {log.msg}")
        else: # 没有事件引擎
            timestamp_str = log.time.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3] # Milliseconds
            print(f"{timestamp_str} [{log.level}] [{log.gateway_name or self.gateway_name}] {log.msg}")

    def on_gateway_status(self, status: GatewayConnectionStatus, message: Optional[str] = None) -> None:
        """
        创建并发送一个 GatewayStatusEvent。
        """
        gateway_status_data = GatewayStatusData(
            gateway_name=self.gateway_name,
            status=status,
            message=message
        )
        if self.event_engine and self.main_loop and self.main_loop.is_running():
            try:
                current_loop = asyncio.get_running_loop()
                if current_loop is self.main_loop:
                    asyncio.create_task(self.event_engine.put(GatewayStatusEvent(data=gateway_status_data)))
                else:
                    asyncio.run_coroutine_threadsafe(self.event_engine.put(GatewayStatusEvent(data=gateway_status_data)), self.main_loop)
            except RuntimeError: # No running loop in current thread, so must be from another thread
                 asyncio.run_coroutine_threadsafe(self.event_engine.put(GatewayStatusEvent(data=gateway_status_data)), self.main_loop)
        elif self.event_engine:
            # Fallback if loop not running or not set but engine exists
            print(f"GatewayStatus: [{self.gateway_name}] {status.value} - {message or ''} (EventLoopIssue)")
        else:
            print(f"GatewayStatus: [{self.gateway_name}] {status.value} - {message or ''}")

    def write_log(self, msg: str, level: str = "INFO") -> None:
        log_data = LogData(msg=msg, level=level, gateway_name=self.gateway_name)
        self.on_log(log_data)

    @abstractmethod
    def connect(self, setting: dict) -> None:
        """
        启动网关连接。
        要实现此方法，您必须：
        * 必要时连接到服务器
        * 如果所有必要的连接都已建立，则记录连接状态
        * 执行以下查询并响应 on_xxxx 和 write_log 语句
        * 合约：on_contract
        * 账户资产：on_account
        * 账户持仓：on_position
        * 账户订单：on_order
        * 账户交易：on_trade
        * 如果上述任何查询失败，则记录日志。

        未来计划：
        响应回调/更改状态，而不是 write_log
        """
        pass

    @abstractmethod
    def close(self) -> None:
        """
        关闭网关连接。
        """
        pass

    @abstractmethod
    def subscribe(self, req: SubscribeRequest) -> None:
        """
        订阅 tick 数据更新。
        """
        pass

    @abstractmethod
    def send_order(self, req: OrderRequest) -> str:
        """
        向服务器发送新订单。

        实现应完成以下任务：
        * 使用 OrderRequest.create_order_data 从请求创建 OrderData
        * 为 OrderData.orderid 分配一个唯一的（网关实例范围）ID
        * 向服务器发送请求
        * 如果请求已发送，则 OrderData.status 应设置为 Status.SUBMITTING
        * 如果请求发送失败，则 OrderData.status 应设置为 Status.REJECTED
        * 响应 on_order:
        * 返回 ho_orderid

        :return str ho_orderid 用于创建 OrderData
        """
        pass

    @abstractmethod
    def cancel_order(self, req: CancelRequest) -> None:
        """
        取消现有订单。
        实现应完成以下任务：
        * 向服务器发送请求
        """
        pass

    @staticmethod
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

        :return str ho_quote_id 用于创建 QuoteData
        """
        pass

    def cancel_quote(self, req: CancelRequest) -> None:
        """
        取消现有报价。
        实施应完成以下任务：
        * 向服务器发送请求
        """
        return

    @abstractmethod
    def query_account(self) -> None:
        """
        查询账户余额。
        """
        pass

    @abstractmethod
    def query_position(self) -> None:
        """
        查询持仓情况。
        """
        pass

    def query_history(self, req: HistoryRequest) -> list[BarData]:
        """
        查询 bar 历史数据。
        """
        pass

    def process_timer_event(self, event: Any) -> None:
        pass

    def get_default_setting(self) -> Any:
        """
        返回默认设置字典。
        """
        return self.default_setting
