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
        self.type = event_type
        self.data = data
        self.source = source or "unknown"
        self.trace_id = trace_id or str(uuid.uuid4())
        self.timestamp = time.time_ns()
        self.priority = priority

    def __repr__(self):
        return f"Event(type={self.type}, source={self.source}, priority={self.priority.name}, trace_id={self.trace_id})"

    def __lt__(self, other):
        """支持优先级队列排序（优先级数值越小，优先级越高）"""
        if not isinstance(other, Event):
            return NotImplemented
        return self.priority < other.priority


class PriorityEvent(Event):
    """优先级事件，专门用于高优先级场景"""
    
    def __init__(self, event_type: str, data: Any = None, source: Optional[str] = None,
                 trace_id: Optional[str] = None, priority: EventPriority = EventPriority.HIGH):
        super().__init__(event_type, data, source, trace_id, priority)


# 事件类型常量定义
class EventType:
    """事件类型常量，按优先级分类"""
    
    # 紧急事件
    SYSTEM_ERROR = "system.error"
    RISK_REJECTED = "risk.rejected"
    ORDER_FAILED = "order.failed"
    GATEWAY_DISCONNECTED = "gateway.disconnected"
    
    # 高优先级事件  
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
    MODULE_LOADED = "module.loaded"
    MODULE_UNLOAD = "module.unload"
    TIMER = "timer"
    SHUTDOWN = "shutdown"
    
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
