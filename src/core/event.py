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
    RISK_CHECKED = "risk.checked"  # 风控检查事件
    RISK_APPROVED = "risk.approved"  # 风控批准事件
    ORDER_FAILED = "order.failed"

    # 高优先级事件
    ORDER = "order"
    TRADE = "trade"
    QUOTE = "quote"
    ORDER_FILLED = "order.filled"
    RISK_CHECK = "risk.check"
    ORDER_SUBMITTED = "order.submitted"
    ORDER_CANCELLED = "order.cancelled"
    ORDER_CANCEL = "order.cancel"  # 订单撤销事件
    ORDER_UPDATED = "order.updated"
    TRADE_UPDATED = "trade.updated"

    RISK_STRATEGY_SUSPEND_RECOMMENDED = "risk.strategy_suspend_recommended"  # 风控策略暂停建议事件

    GATEWAY_SUBSCRIBE = "gateway.subscribe"  # 网关订阅事件
    GATEWAY_UNSUBSCRIBE = "gateway.unsubscribe"  # 网关取消订阅事件
    GATEWAY_CONNECTED = "gateway.connected"  # 网关连接成功事件
    GATEWAY_DISCONNECTED = "gateway.disconnected"  # 网关断开连接事件
    GATEWAY_READY = "gateway.ready"  # 网关就绪事件
    GATEWAY_STATE_CHANGED = "gateway.state_changed"  # 网关状态变更事件
    # gateway.connection_failed
    GATEWAY_RECONNECT_FAILED = "gateway.reconnect_failed"  # 网关重连失败事件
    GATEWAY_SUBSCRIPTION_SUCCESS = "gateway.subscription.success"  # 网关订阅成功事件
    GATEWAY_SUBSCRIPTION_FAILED = "gateway.subscription.failed"  # 网关订阅失败事件
    GATEWAY_STATUS_QUERY = "gateway.status_query"  # 网关状态查询事件
    GATEWAY_READY_CHECK = "gateway.ready_check"  # 网关就绪检查事件

    GATEWAY_QUERY_ACCOUNT = "gateway.query_account"  # 网关查询账户事件
    GATEWAY_QUERY_POSITION = "gateway.query_position"  # 网关查询持仓事件

    GATEWAY_SEND_ORDER = "gateway.send_order"       # 网关发送订单事件
    GATEWAY_CANCEL_ORDER = "gateway.cancel_order"   # 网关撤单事件

    DATA_SUBSCRIBE = "data.subscribe"  # 数据订阅事件
    DATA_UNSUBSCRIBE = "data.unsubscribe"  # 数据取消订阅事件
    DATA_QUERY_TICK = "data.query.tick"  # 数据查询Tick事件
    DATA_QUERY_BAR = "data.query.bar"  # 数据查询Bar事件
    DATA_QUERY_TICK_RESULT = "data.query.tick.result"  # 数据查询Tick结果事件
    DATA_QUERY_BAR_RESULT = "data.query.bar.result"  # 数据查询Bar结果事件
    DATA_SUBSCRIBE_SUCCESS = "data.subscribe.success"  # 数据订阅成功事件
    DATA_SUBSCRIBE_FAILED = "data.subscribe.failed"  # 数据订阅失败事件
    DATA_PERSIST = "data.persist"  # 数据持久化事件

    STRATEGY_SIGNAL = "strategy.signal"
    STRATEGY_LOADED = "strategy.loaded"             # 策略加载事件
    STRATEGY_LOAD_FAILED = "strategy.load_failed"   # 策略加载失败事件
    STRATEGY_STARTED = "strategy.started"           # 策略启动成功事件
    STRATEGY_START_FAILED = "strategy.start_failed" # 策略启动失败事件
    STRATEGY_STOPPED = "strategy.stopped"           # 策略停止事件
    STRATEGY_STOP_FAILED = "strategy.stop_failed"   # 策略停止失败事件
    STRATEGY_ORDER_PLACED = "strategy.order_placed"  # 策略下单事件

    ENGINE_STOPPED = "engine.stopped"   # 引擎停止事件
    ENGINE_STARTED = "engine.started"   # 引擎启动事件
    
    # 普通事件
    MARKET_TICK = "market.tick"
    MARKET_TICK_RAW = "market.tick.raw"     # tick行情数据处理
    MARKET_BAR = "market.bar"
    MARKET_BAR_RAW = "market.bar.raw"       # bar行情数据处理

    TICK_UPDATED = "tick.updated"
    POSITION_UPDATED = "position.updated"
    ACCOUNT_UPDATED = "account.updated"
    CONTRACT = "contract"
    CONTRACT_UPDATED = "contract.updated"
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
    PERFORMANCE_ALERT = "performance.alert"  # 性能告警事件

    SYSTEM_GATEWAY_CONNECTION_FAILED = "system.gateway_connection_failed"  # 系统网关连接失败事件
    SYSTEM_STARTUP_COMPLETE = "system.startup_complete"  # 系统启动成功事件


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
