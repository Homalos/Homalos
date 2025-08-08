#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos_v2
@FileName   : event_types
@Date       : 2025/1/16
@Author     : Donny
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 事件类型安全系统 - 第二阶段优化核心组件
提供强类型事件定义、验证和序列化机制
"""
import json
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Type, TypeVar, Generic

from pydantic import BaseModel, ValidationError, field_validator

from src.core.event import Event, EventPriority, EventType
from src.core.logger import get_logger

logger = get_logger("EventTypes")

# 类型变量
T = TypeVar('T')
EventDataType = TypeVar('EventDataType', bound=BaseModel)


class EventCategory(Enum):
    """事件分类"""
    TRADING = "trading"  # 交易相关
    MARKET_DATA = "market_data"  # 市场数据
    STRATEGY = "strategy"  # 策略相关
    RISK = "risk"  # 风险管理
    SYSTEM = "system"  # 系统事件
    NOTIFICATION = "notification"  # 通知事件
    MONITORING = "monitoring"  # 监控事件
    ERROR = "error"  # 错误事件


class EventSeverity(Enum):
    """事件严重程度"""
    DEBUG = 0
    INFO = 1
    WARNING = 2
    ERROR = 3
    CRITICAL = 4


@dataclass
class EventMetadata:
    """事件元数据"""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
    source: str = "unknown"
    correlation_id: Optional[str] = None
    trace_id: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    version: str = "1.0"
    tags: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = {}
        for key, value in self.__dict__.items():
            if value is not None:
                if isinstance(value, dict):
                    result[key] = value.copy()
                else:
                    result[key] = value
            # 跳过值为 None 的字段，不包含在结果字典中
        return result
        # return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EventMetadata':
        """从字典创建"""
        return cls(**data)


class TypedEventData(BaseModel):
    """类型化事件数据基类"""
    
    class Config:
        # 允许额外字段
        extra = "allow"
        # 使用枚举值
        use_enum_values = True
        # 验证赋值
        validate_assignment = True
        # 在pydantic v2中，模型默认是可变的，无需此配置
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典

        Returns:
            Dict[str, Any]: 模型数据的字典表示
        """
        return self.model_dump()
    
    def to_json(self) -> str:
        """
        转换为JSON字符串

        Returns:
            str: 模型数据的JSON字符串表示
        """
        return self.model_dump_json()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TypedEventData':
        """
        从字典创建模型实例

        Args:
            data (Dict[str, Any]): 包含模型数据的字典

        Returns:
            TypedEventData: 创建的模型实例

        Raises:
            ValidationError: 当数据验证失败时抛出
        """
        return cls.model_validate(data)

    @classmethod
    def from_json(cls, json_str: str) -> 'TypedEventData':
        """
        从JSON字符串创建模型实例

        Args:
            json_str (str): 包含模型数据的JSON字符串

        Returns:
            TypedEventData: 创建的模型实例

        Raises:
            ValidationError: 当JSON解析或数据验证失败时抛出
        """
        return cls.model_validate_json(json_str)


class TypedEvent(Generic[EventDataType]):
    """
    类型化事件
    
    提供强类型的事件定义和验证
    """
    
    def __init__(self,
                 event_type: str,
                 data: EventDataType,
                 category: EventCategory = EventCategory.SYSTEM,
                 priority: EventPriority = EventPriority.NORMAL,
                 severity: EventSeverity = EventSeverity.INFO,
                 metadata: Optional[EventMetadata] = None,
                 ttl: Optional[float] = None,
                 retry_policy: Optional[Dict[str, Any]] = None):
        
        self._event_type = event_type
        self._data = data
        self._category = category
        self._priority = priority
        self._severity = severity
        self._metadata = metadata or EventMetadata()
        self._ttl = ttl
        self._retry_policy = retry_policy or {}
        
        # 验证数据
        self._validate_data()
    
    @property
    def event_type(self) -> str:
        return self._event_type
    
    @property
    def data(self) -> EventDataType:
        return self._data
    
    @property
    def category(self) -> EventCategory:
        return self._category
    
    @property
    def priority(self) -> EventPriority:
        return self._priority
    
    @property
    def severity(self) -> EventSeverity:
        return self._severity
    
    @property
    def metadata(self) -> EventMetadata:
        return self._metadata
    
    @property
    def ttl(self) -> Optional[float]:
        return self._ttl
    
    @property
    def retry_policy(self) -> Dict[str, Any]:
        return self._retry_policy
    
    def _validate_data(self) -> None:
        """验证事件数据"""
        if not isinstance(self._data, BaseModel):
            raise TypeError(f"Event data must be a BaseModel instance, got {type(self._data)}")
        
        # 验证数据有效性
        try:
            self._data.model_dump()  # 触发验证
        except ValidationError as e:
            raise ValueError(f"Invalid event data: {e}")
    
    def is_expired(self) -> bool:
        """检查事件是否过期"""
        if self._ttl is None:
            return False
        
        return time.time() - self._metadata.timestamp > self._ttl
    
    def validate(self) -> bool:
        """验证事件数据"""
        try:
            self._validate_data()
            return True
        except (TypeError, ValueError):
            return False
    
    def to_legacy_event(self) -> Event:
        """转换为传统Event对象"""
        return Event(
            event_type=self._event_type,
            data=self._data.model_dump(),
            priority=self._priority
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'event_type': self._event_type,
            'data': self._data.model_dump(),
            'category': self._category.value,
            'priority': self._priority.value,
            'severity': self._severity.value,
            'metadata': self._metadata.to_dict(),
            'ttl': self._ttl,
            'retry_policy': self._retry_policy
        }
    
    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), default=str)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], data_class: Type[EventDataType]) -> 'TypedEvent[EventDataType]':
        """从字典创建"""
        event_data = data_class(**data['data'])
        metadata = EventMetadata.from_dict(data.get('metadata', {}))
        
        return cls(
            event_type=data['event_type'],
            data=event_data,
            category=EventCategory(data.get('category', EventCategory.SYSTEM.value)),
            priority=EventPriority(data.get('priority', EventPriority.NORMAL.value)),
            severity=EventSeverity(data.get('severity', EventSeverity.INFO.value)),
            metadata=metadata,
            ttl=data.get('ttl'),
            retry_policy=data.get('retry_policy', {})
        )
    
    def __str__(self) -> str:
        return f"TypedEvent(type={self._event_type}, category={self._category.value}, severity={self._severity.value})"
    
    def __repr__(self) -> str:
        return self.__str__()


class EventTypeRegistry:
    """
    事件类型注册表
    
    管理所有已注册的事件类型和其数据模型
    """
    
    def __init__(self):
        self._registered_types: Dict[str, Type[TypedEventData]] = {}
        self._type_metadata: Dict[str, Dict[str, Any]] = {}
        self._category_mapping: Dict[str, EventCategory] = {}
        self._priority_mapping: Dict[str, EventPriority] = {}
        self._severity_mapping: Dict[str, EventSeverity] = {}
    
    def register_event_type(self,
                           event_type: str,
                           data_class: Type[TypedEventData],
                           category: EventCategory = EventCategory.SYSTEM,
                           default_priority: EventPriority = EventPriority.NORMAL,
                           default_severity: EventSeverity = EventSeverity.INFO,
                           description: str = "",
                           schema_version: str = "1.0",
                           **metadata) -> None:
        """
        注册事件类型
        
        Args:
            event_type: 事件类型名称
            data_class: 事件数据类
            category: 事件分类
            default_priority: 默认优先级
            default_severity: 默认严重程度
            description: 事件描述
            schema_version: 模式版本
            **metadata: 额外元数据
        """
        if not issubclass(data_class, TypedEventData):
            raise TypeError(f"Data class must inherit from TypedEventData")
        
        if event_type in self._registered_types:
            logger.warning(f"Event type '{event_type}' is already registered, overwriting")
        
        self._registered_types[event_type] = data_class
        self._category_mapping[event_type] = category
        self._priority_mapping[event_type] = default_priority
        self._severity_mapping[event_type] = default_severity
        
        self._type_metadata[event_type] = {
            'description': description,
            'schema_version': schema_version,
            'data_class': data_class.__name__,
            'category': category.value,
            'default_priority': default_priority.value,
            'default_severity': default_severity.value,
            'registered_at': time.time(),
            **metadata
        }
        
        logger.info(f"Registered event type: {event_type} -> {data_class.__name__}")
    
    def unregister_event_type(self, event_type: str) -> bool:
        """注销事件类型"""
        if event_type not in self._registered_types:
            return False
        
        del self._registered_types[event_type]
        del self._type_metadata[event_type]
        del self._category_mapping[event_type]
        del self._priority_mapping[event_type]
        del self._severity_mapping[event_type]
        
        logger.info(f"Unregistered event type: {event_type}")
        return True
    
    def is_registered(self, event_type: str) -> bool:
        """检查事件类型是否已注册"""
        return event_type in self._registered_types
    
    def get_data_class(self, event_type: str) -> Optional[Type[TypedEventData]]:
        """获取事件数据类"""
        return self._registered_types.get(event_type)
    
    def get_category(self, event_type: str) -> Optional[EventCategory]:
        """获取事件分类"""
        return self._category_mapping.get(event_type)
    
    def get_default_priority(self, event_type: str) -> Optional[EventPriority]:
        """获取默认优先级"""
        return self._priority_mapping.get(event_type)
    
    def get_default_severity(self, event_type: str) -> Optional[EventSeverity]:
        """获取默认严重程度"""
        return self._severity_mapping.get(event_type)
    
    def get_metadata(self, event_type: str) -> Optional[Dict[str, Any]]:
        """获取事件类型元数据"""
        return self._type_metadata.get(event_type)
    
    def get_event_type_info(self, event_type: str) -> Optional[Dict[str, Any]]:
        """获取事件类型信息（别名方法）"""
        metadata = self.get_metadata(event_type)
        if metadata is None:
            return None
        
        # 添加数据类引用
        data_class = self.get_data_class(event_type)
        info = metadata.copy()
        info['data_class'] = data_class
        return info
    
    def list_event_types(self) -> List[str]:
        """列出所有已注册的事件类型"""
        return list(self._registered_types.keys())
    
    def get_types_by_category(self, category: EventCategory) -> List[str]:
        """按分类获取事件类型"""
        return [event_type for event_type, cat in self._category_mapping.items() 
                if cat == category]
    
    def create_typed_event(self,
                          event_type: str,
                          data: Dict[str, Any],
                          priority: Optional[EventPriority] = None,
                          severity: Optional[EventSeverity] = None,
                          metadata: Optional[EventMetadata] = None,
                          **kwargs) -> TypedEvent:
        """
        创建类型化事件
        
        Args:
            event_type: 事件类型
            data: 事件数据
            priority: 优先级（可选）
            severity: 严重程度（可选）
            metadata: 元数据（可选）
            **kwargs: 其他参数
            
        Returns:
            类型化事件实例
        """
        if not self.is_registered(event_type):
            raise ValueError(f"Event type '{event_type}' is not registered")
        
        data_class = self.get_data_class(event_type)
        category = self.get_category(event_type)
        
        # 使用默认值
        if priority is None:
            priority = self.get_default_priority(event_type)
        if severity is None:
            severity = self.get_default_severity(event_type)
        
        # 创建事件数据实例
        try:
            event_data = data_class(**data)
        except ValidationError as e:
            raise ValueError(f"Invalid data for event type '{event_type}': {e}")
        
        return TypedEvent(
            event_type=event_type,
            data=event_data,
            category=category,
            priority=priority,
            severity=severity,
            metadata=metadata,
            **kwargs
        )
    
    def validate_event_data(self, event_type: str, data: Dict[str, Any]) -> bool:
        """
        验证事件数据
        
        Args:
            event_type: 事件类型
            data: 事件数据
            
        Returns:
            是否有效
        """
        if not self.is_registered(event_type):
            return False
        
        data_class = self.get_data_class(event_type)
        
        try:
            data_class(**data)
            return True
        except ValidationError:
            return False
    
    def get_schema(self, event_type: str) -> Optional[Dict[str, Any]]:
        """获取事件类型的JSON Schema"""
        if not self.is_registered(event_type):
            return None
        
        data_class = self.get_data_class(event_type)
        return data_class.model_json_schema()
    
    def export_schemas(self) -> Dict[str, Dict[str, Any]]:
        """导出所有事件类型的Schema"""
        schemas = {}
        for event_type in self.list_event_types():
            schemas[event_type] = {
                'schema': self.get_schema(event_type),
                'metadata': self.get_metadata(event_type)
            }
        return schemas
    
    def get_registry_stats(self) -> Dict[str, Any]:
        """获取注册表统计信息"""
        category_counts = {}
        for category in EventCategory:
            category_counts[category.value] = len(self.get_types_by_category(category))
        
        return {
            'total_types': len(self._registered_types),
            'category_distribution': category_counts,
            'registered_types': self.list_event_types()
        }


# 全局事件类型注册表
event_registry = EventTypeRegistry()


# 常用事件数据类型定义
class SystemEventData(TypedEventData):
    """系统事件数据"""
    message: str
    component: str
    level: str = "info"
    details: Dict[str, Any] = {}


class TradingEventData(TypedEventData):
    """交易事件数据"""
    symbol: str
    action: str  # buy, sell, cancel
    quantity: float
    price: Optional[float] = None
    order_id: Optional[str] = None
    strategy_id: Optional[str] = None
    
    @field_validator('quantity')
    def quantity_must_be_positive(self, v):
        if v <= 0:
            raise ValueError('Quantity must be positive')
        return v
    
    @field_validator('price')
    def price_must_be_positive(self, v):
        if v is not None and v <= 0:
            raise ValueError('Price must be positive')
        return v


class MarketDataEventData(TypedEventData):
    """市场数据事件数据"""
    symbol: str
    price: float
    volume: float
    timestamp: float
    bid: Optional[float] = None
    ask: Optional[float] = None
    
    @field_validator('price', 'volume')
    def must_be_positive(self, v):
        if v <= 0:
            raise ValueError('Price and volume must be positive')
        return v


class ErrorEventData(TypedEventData):
    """错误事件数据"""
    error_type: str
    error_message: str
    component: str
    stack_trace: Optional[str] = None
    context: Dict[str, Any] = {}


class NotificationEventData(TypedEventData):
    """通知事件数据"""
    title: str
    message: str
    recipient: str
    channel: str = "email"  # email, sms, push
    priority: str = "normal"  # low, normal, high, urgent
    metadata: Dict[str, Any] = {}


# 注册常用事件类型
def register_common_event_types():
    """注册常用事件类型"""
    event_registry.register_event_type(
        EventType.SYSTEM_STARTUP,
        SystemEventData,
        EventCategory.SYSTEM,
        EventPriority.HIGH,
        EventSeverity.INFO,
        "系统启动事件"
    )
    
    event_registry.register_event_type(
        EventType.SYSTEM_SHUTDOWN,
        SystemEventData,
        EventCategory.SYSTEM,
        EventPriority.HIGH,
        EventSeverity.INFO,
        "系统关闭事件"
    )
    
    event_registry.register_event_type(
        "trading.order.created",
        TradingEventData,
        EventCategory.TRADING,
        EventPriority.HIGH,
        EventSeverity.INFO,
        "订单创建事件"
    )
    
    event_registry.register_event_type(
        "trading.order.filled",
        TradingEventData,
        EventCategory.TRADING,
        EventPriority.HIGH,
        EventSeverity.INFO,
        "订单成交事件"
    )
    
    event_registry.register_event_type(
        "market.tick",
        MarketDataEventData,
        EventCategory.MARKET_DATA,
        EventPriority.NORMAL,
        EventSeverity.DEBUG,
        "市场行情事件"
    )
    
    event_registry.register_event_type(
        "system.error",
        ErrorEventData,
        EventCategory.ERROR,
        EventPriority.HIGH,
        EventSeverity.ERROR,
        "系统错误事件"
    )
    
    event_registry.register_event_type(
        "notification.alert",
        NotificationEventData,
        EventCategory.NOTIFICATION,
        EventPriority.NORMAL,
        EventSeverity.INFO,
        "通知告警事件"
    )
    
    logger.info("Common event types registered")


# 自动注册常用事件类型
register_common_event_types()


# 便捷函数
def create_system_event(message: str, component: str, level: str = "info", **details) -> TypedEvent[SystemEventData]:
    """创建系统事件"""
    return event_registry.create_typed_event(
        "system.startup" if "startup" in message.lower() else "system.shutdown" if "shutdown" in message.lower() else "system.error",
        {
            "message": message,
            "component": component,
            "level": level,
            "details": details
        }
    )


def create_trading_event(symbol: str, action: str, quantity: float, **kwargs) -> TypedEvent[TradingEventData]:
    """创建交易事件"""
    event_type = f"trading.order.{action}" if action in ["created", "filled", "cancelled"] else "trading.order.created"
    
    return event_registry.create_typed_event(
        event_type,
        {
            "symbol": symbol,
            "action": action,
            "quantity": quantity,
            **kwargs
        }
    )


def create_market_data_event(symbol: str, price: float, volume: float, **kwargs) -> TypedEvent[MarketDataEventData]:
    """创建市场数据事件"""
    return event_registry.create_typed_event(
        "market.tick",
        {
            "symbol": symbol,
            "price": price,
            "volume": volume,
            "timestamp": time.time(),
            **kwargs
        }
    )


def create_error_event(error_type: str, error_message: str, component: str, **kwargs) -> TypedEvent[ErrorEventData]:
    """创建错误事件"""
    return event_registry.create_typed_event(
        "system.error",
        {
            "error_type": error_type,
            "error_message": error_message,
            "component": component,
            **kwargs
        }
    )


def create_notification_event(title: str, message: str, recipient: str, **kwargs) -> TypedEvent[NotificationEventData]:
    """创建通知事件"""
    return event_registry.create_typed_event(
        "notification.alert",
        {
            "title": title,
            "message": message,
            "recipient": recipient,
            **kwargs
        }
    )