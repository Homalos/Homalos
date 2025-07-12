#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos_v2
@FileName   : event
@Date       : 2025/7/6 18:26
@Author     : Donny
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 事件对象
"""
import time
import uuid
from typing import Any, Optional
from enum import IntEnum


class EventPriority(IntEnum):
    """事件优先级枚举"""
    CRITICAL = 0    # 紧急事件（如风控拒绝、系统错误）
    HIGH = 1        # 高优先级（如订单回报、成交回报）
    NORMAL = 2      # 普通优先级（如行情数据）
    LOW = 3         # 低优先级（如日志、统计）


class Event:
    """事件对象，携带类型和数据"""

    __slots__ = ('type', 'data', 'source', 'trace_id', 'timestamp', 'priority')

    def __init__(self, event_type: str, data: Any = None, source: Optional[str] = None, 
                 trace_id: Optional[str] = None, priority: EventPriority = EventPriority.NORMAL):
        self.type = event_type  # 初始化事件类型
        self.data = data  # 初始化事件数据
        self.source = source or "unknown"  # 初始化事件来源，如果没有提供来源，则默认为"unknown"
        self.trace_id = trace_id or str(uuid.uuid4())  # 初始化事件追踪ID，如果没有提供追踪ID，则生成一个新的UUID
        self.timestamp = time.time_ns()  # 初始化事件时间戳
        self.priority = priority  # 初始化事件优先级

    def __repr__(self):
        """
        返回事件对象的字符串表示形式。
        Args:
            无。
        Returns:
            str: 事件对象的字符串表示形式，包含事件类型、事件源、优先级和追踪ID。
        """
        return f"Event(type={self.type}, source={self.source}, priority={self.priority.name}, trace_id={self.trace_id})"

    def __lt__(self, other) -> bool:
        """支持优先级队列排序（优先级数值越小，优先级越高）"""
        if not isinstance(other, Event):
            return NotImplemented
        return self.priority < other.priority


class PriorityEvent(Event):
    """优先级事件，专门用于高优先级场景"""
    
    def __init__(self, event_type: str, data: Any = None, source: Optional[str] = None,
                 trace_id: Optional[str] = None, priority: EventPriority = EventPriority.HIGH):
        """
        初始化方法。
        Args:
            event_type (str): 事件类型。
            data (Any, optional): 事件数据，默认为None。
            source (Optional[str], optional): 事件来源，默认为None。
            trace_id (Optional[str], optional): 跟踪ID，默认为None。
            priority (EventPriority, optional): 事件优先级，默认为EventPriority.HIGH。
        """
        super().__init__(event_type, data, source, trace_id, priority)


class EventType:
    """事件类型常量，按优先级分类"""
    
    # 紧急事件
    SYSTEM_ERROR = "system.error"
    RISK_REJECTED = "risk.rejected"
    ORDER_FAILED = "order.failed"
    GATEWAY_DISCONNECTED = "gateway.disconnected"
    
    # 高优先级事件
    ORDER = "order"
    TRADE = "trade"
    QUOTE = "quote"
    ORDER_FILLED = "order.filled"
    ORDER_SUBMITTED = "order.submitted"
    ORDER_CANCELLED = "order.cancelled"
    RISK_APPROVED = "risk.approved"
    STRATEGY_SIGNAL = "strategy.signal"
    
    # 普通事件
    MARKET_TICK = "market.tick"
    MARKET_BAR = "market.bar"
    POSITION_UPDATE = "position.update"
    ACCOUNT_UPDATE = "account.update"
    CONTRACT = "contract"
    MODULE_LOADED = "module.loaded"
    MODULE_UNLOAD = "module.unload"
    TIMER = "timer"
    SHUTDOWN = "shutdown"
    SERVICE_REGISTER = "service.register"
    SERVICE_UNREGISTER = "service.unregister"
    SERVICE_HEART_BEAT = "service.heartbeat"
    SERVICE_DISCOVERY = "service.discovery"

    SERVICE_UPDATED = "service.updated"  # 广播服务更新事件
    SERVICE_DISCOVERY_RESPONSE = "service.discovery.response"  # 服务发现响应事件
    SERVICE_FAILED = "service.failed"  # 广播服务失败事件
    
    # 低优先级事件
    LOG_MESSAGE = "log.message"
    HEARTBEAT = "service.heartbeat"
    STATISTICS = "system.statistics"


# 便利函数
def create_critical_event(event_type: str, data: Any = None, source: Optional[str] = None) -> Event:
    """创建紧急事件"""
    return Event(event_type, data, source, priority=EventPriority.CRITICAL)

def create_trading_event(event_type: str, data: Any = None, source: Optional[str] = None) -> Event:
    """创建交易相关高优先级事件"""
    return Event(event_type, data, source, priority=EventPriority.HIGH)

def create_market_event(event_type: str, data: Any = None, source: Optional[str] = None) -> Event:
    """创建行情相关普通事件"""
    return Event(event_type, data, source, priority=EventPriority.NORMAL)

def create_log_event(event_type: str, data: Any = None, source: Optional[str] = None) -> Event:
    """创建日志相关低优先级事件"""
    return Event(event_type, data, source, priority=EventPriority.LOW)
