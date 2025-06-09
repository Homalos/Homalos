#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : event.py
@Date       : 2025/5/28 15:11
@Author     : Donny
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 定义了系统中流转的各种事件
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from src.core.object import (
    TickData,
    OrderData,
    TradeData,
    AccountData,
    PositionData,
    ContractData,
    LogData,
    OrderRequest,
    CancelRequest,
    GatewayStatusData,
    SubscribeRequest
)

class EventType(Enum):
    """
    定义不同事件的类型枚举。
    """
    TICK = "eTick"
    ORDER_UPDATE = "eOrderUpdate"  # 订单状态更新
    TRADE_UPDATE = "eTradeUpdate"  # 成交回报
    POSITION_UPDATE = "ePositionUpdate" # 持仓更新
    ACCOUNT_UPDATE = "eAccountUpdate" # 账户资金更新
    CONTRACT_INFO = "eContractInfo"  # 合约信息
    LOG = "eLog"  # 日志事件
    GATEWAY_STATUS = "eGatewayStatus"  # 网关状态事件
    
    # 由策略或订单管理系统（OMS）生成的事件
    ORDER_REQUEST = "eOrderRequest"       # 新订单请求
    SUBSCRIBE_REQUEST = "eSubscribeRequest" # 行情订阅请求
    CANCEL_ORDER_REQUEST = "eCancelOrderRequest" # 撤单请求
    STRATEGY_SIGNAL = "eStrategySignal"   # 策略产生的通用信号
    BULK_CONTRACTS = "eBulkContracts"     # 批量合约信息事件

@dataclass
class Event:
    """
    基础事件类。
    """
    type: EventType
    data: Any = None

# 为特定事件类型定义更具体的类，以便更好地进行类型提示和结构化
@dataclass
class TickEvent(Event):
    type: EventType = field(default=EventType.TICK, init=False)
    data: TickData = None

@dataclass
class OrderUpdateEvent(Event):
    type: EventType = field(default=EventType.ORDER_UPDATE, init=False)
    data: OrderData = None

@dataclass
class TradeUpdateEvent(Event):
    type: EventType = field(default=EventType.TRADE_UPDATE, init=False)
    data: TradeData = None

@dataclass
class PositionUpdateEvent(Event):
    type: EventType = field(default=EventType.POSITION_UPDATE, init=False)
    data: PositionData = None

@dataclass
class AccountUpdateEvent(Event):
    type: EventType = field(default=EventType.ACCOUNT_UPDATE, init=False)
    data: AccountData = None

@dataclass
class ContractInfoEvent(Event):
    type: EventType = field(default=EventType.CONTRACT_INFO, init=False)
    data: ContractData = None

@dataclass
class LogEvent(Event): # 用于通过事件总线进行系统范围的日志记录
    type: EventType = field(default=EventType.LOG, init=False)
    data: LogData = None

@dataclass
class GatewayStatusEvent(Event):
    type: EventType = field(default=EventType.GATEWAY_STATUS, init=False)
    data: GatewayStatusData = None

# 可能由策略生成的事件
@dataclass
class OrderRequestEvent(Event): # 与 object.OrderRequest (内容) 不同
    type: EventType = field(default=EventType.ORDER_REQUEST, init=False)
    data: OrderRequest = None

@dataclass
class CancelOrderRequestEvent(Event):
    type: EventType = field(default=EventType.CANCEL_ORDER_REQUEST, init=False)
    data: CancelRequest = None

@dataclass
class SubscribeRequestEvent(Event):
    type: EventType = field(default=EventType.SUBSCRIBE_REQUEST, init=False)
    data: SubscribeRequest = None

@dataclass
class StrategySignalEvent(Event): # 更通用的信号
    type: EventType = field(default=EventType.STRATEGY_SIGNAL, init=False)
    data: dict = None # 信号数据可以是字典，以保持灵活性

@dataclass
class BulkContractsEvent(Event): # 批量合约信息事件
    type: EventType = field(default=EventType.BULK_CONTRACTS, init=False)
    data: list[ContractData] = None # 合约数据列表
