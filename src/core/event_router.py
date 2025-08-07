#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos_v2
@FileName   : event_router
@Date       : 2025/1/16
@Author     : Donny
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 智能事件路由系统 - 第二阶段优化核心组件
提供高级事件路由、过滤和分发机制
"""

import fnmatch
import re
import threading
import time
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Callable, Union

from src.core.event import Event
from src.core.event_types import TypedEvent
from src.core.logger import get_logger

logger = get_logger("EventRouter")


class RoutingStrategy(Enum):
    """路由策略枚举"""
    BROADCAST = "broadcast"             # 广播到所有匹配的处理器
    ROUND_ROBIN = "round_robin"         # 轮询分发
    LOAD_BALANCED = "load_balanced"     # 负载均衡
    PRIORITY_BASED = "priority_based"   # 基于优先级
    FIRST_MATCH = "first_match"         # 第一个匹配
    RANDOM = "random"                   # 随机选择


class FilterOperator(Enum):
    """过滤操作符"""
    EQUALS = "eq"
    NOT_EQUALS = "ne"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    REGEX = "regex"
    IN = "in"
    NOT_IN = "not_in"
    GREATER_THAN = "gt"
    LESS_THAN = "lt"
    GREATER_EQUAL = "ge"
    LESS_EQUAL = "le"


@dataclass
class RouteFilter:
    """路由过滤器"""
    field: str  # 字段名
    operator: FilterOperator  # 操作符
    value: Any  # 比较值
    case_sensitive: bool = True
    
    def matches(self, event_data: Dict[str, Any]) -> bool:
        """检查事件是否匹配过滤器"""
        try:
            # 获取字段值
            field_value = self._get_field_value(event_data, self.field)
            
            if field_value is None:
                return False
            
            # 执行比较
            return self._compare_values(field_value, self.value, self.operator)
            
        except Exception as e:
            logger.debug(f"Filter matching error: {e}")
            return False

    @staticmethod
    def _get_field_value(data: Dict[str, Any], field_path: str) -> Any:
        """获取嵌套字段值"""
        keys = field_path.split('.')
        value = data
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None
        
        return value
    
    def _compare_values(self, field_value: Any, filter_value: Any, operator: FilterOperator) -> bool:
        """比较值"""
        # 字符串比较时考虑大小写
        if isinstance(field_value, str) and isinstance(filter_value, str) and not self.case_sensitive:
            field_value = field_value.lower()
            filter_value = filter_value.lower()
        
        if operator == FilterOperator.EQUALS:
            return field_value == filter_value
        elif operator == FilterOperator.NOT_EQUALS:
            return field_value != filter_value
        elif operator == FilterOperator.CONTAINS:
            return str(filter_value) in str(field_value)
        elif operator == FilterOperator.NOT_CONTAINS:
            return str(filter_value) not in str(field_value)
        elif operator == FilterOperator.STARTS_WITH:
            return str(field_value).startswith(str(filter_value))
        elif operator == FilterOperator.ENDS_WITH:
            return str(field_value).endswith(str(filter_value))
        elif operator == FilterOperator.REGEX:
            pattern = re.compile(str(filter_value), re.IGNORECASE if not self.case_sensitive else 0)
            return bool(pattern.search(str(field_value)))
        elif operator == FilterOperator.IN:
            return field_value in filter_value
        elif operator == FilterOperator.NOT_IN:
            return field_value not in filter_value
        elif operator == FilterOperator.GREATER_THAN:
            return field_value > filter_value
        elif operator == FilterOperator.LESS_THAN:
            return field_value < filter_value
        elif operator == FilterOperator.GREATER_EQUAL:
            return field_value >= filter_value
        elif operator == FilterOperator.LESS_EQUAL:
            return field_value <= filter_value
        else:
            return False


@dataclass
class RouteRule:
    """路由规则"""
    name: str
    pattern: str  # 事件类型模式（支持通配符）
    filters: List[RouteFilter] = field(default_factory=list)
    target_handlers: List[str] = field(default_factory=list)  # 目标处理器名称
    strategy: RoutingStrategy = RoutingStrategy.BROADCAST
    priority: int = 0  # 规则优先级，数值越大优先级越高
    enabled: bool = True
    max_retries: int = 3
    timeout: float = 30.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def matches_event_type(self, event_type: str) -> bool:
        """检查事件类型是否匹配模式"""
        return fnmatch.fnmatch(event_type, self.pattern)
    
    def matches_event(self, event: Union[Event, TypedEvent]) -> bool:
        """检查事件是否匹配规则"""
        if not self.enabled:
            return False
        
        # 检查事件类型模式
        event_type = event.event_type if isinstance(event, TypedEvent) else event.type
        if not self.matches_event_type(event_type):
            return False
        
        # 检查过滤器
        if self.filters:
            event_data = self._get_event_data(event)
            for filter_rule in self.filters:
                if not filter_rule.matches(event_data):
                    return False
        
        return True

    @staticmethod
    def _get_event_data(event: Union[Event, TypedEvent]) -> Dict[str, Any]:
        """获取事件数据"""
        if isinstance(event, TypedEvent):
            # 安全地获取data，支持字典和对象
            data = event.data
            if hasattr(data, 'dict'):
                data = data.model_dump()
            elif hasattr(data, '__dict__'):
                data = data.__dict__
            
            return {
                'type': event.event_type,
                'category': event.category.value,
                'priority': event.priority.value,
                'severity': event.severity.value,
                'data': data,
                'metadata': event.metadata.to_dict() if hasattr(event.metadata, 'to_dict') else event.metadata
            }
        else:
            return {
                'type': event.type,
                'priority': event.priority.value if hasattr(event.priority, 'value') else event.priority,
                'data': event.data,
                'source': event.source,
                'trace_id': event.trace_id,
                'timestamp': event.timestamp
            }


@dataclass
class RoutingResult:
    """路由结果"""
    rule_name: str
    target_handlers: List[str]
    strategy: RoutingStrategy
    matched_filters: List[str] = field(default_factory=list)
    routing_time: float = 0.0
    success: bool = True
    error: Optional[str] = None


class HandlerRegistry:
    """处理器注册表"""
    
    def __init__(self):
        self._handlers: Dict[str, Callable] = {}
        self._handler_metadata: Dict[str, Dict[str, Any]] = {}
        self._handler_stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            'total_calls': 0,
            'success_calls': 0,
            'error_calls': 0,
            'avg_execution_time': 0.0,
            'last_call_time': 0.0
        })
        self._lock = threading.Lock()
    
    def register_handler(self,
                        name: str,
                        handler: Callable,
                        description: str = "",
                        tags: List[str] = None,
                        **metadata) -> None:
        """注册处理器"""
        with self._lock:
            self._handlers[name] = handler
            self._handler_metadata[name] = {
                'description': description,
                'tags': tags or [],
                'registered_at': time.time(),
                **metadata
            }
        
        logger.info(f"Registered handler: {name}")
    
    def unregister_handler(self, name: str) -> bool:
        """注销处理器"""
        with self._lock:
            if name in self._handlers:
                del self._handlers[name]
                del self._handler_metadata[name]
                if name in self._handler_stats:
                    del self._handler_stats[name]
                logger.info(f"Unregistered handler: {name}")
                return True
        return False
    
    def get_handler(self, name: str) -> Optional[Callable]:
        """获取处理器"""
        return self._handlers.get(name)
    
    def list_handlers(self) -> List[str]:
        """列出所有处理器"""
        return list(self._handlers.keys())
    
    def get_handlers_by_tag(self, tag: str) -> List[str]:
        """按标签获取处理器"""
        handlers = []
        for name, metadata in self._handler_metadata.items():
            if tag in metadata.get('tags', []):
                handlers.append(name)
        return handlers
    
    def update_stats(self, handler_name: str, success: bool, execution_time: float) -> None:
        """更新处理器统计"""
        if handler_name not in self._handler_stats:
            return
        
        stats = self._handler_stats[handler_name]
        stats['total_calls'] += 1
        stats['last_call_time'] = time.time()
        
        if success:
            stats['success_calls'] += 1
        else:
            stats['error_calls'] += 1
        
        # 更新平均执行时间（指数移动平均）
        if stats['avg_execution_time'] == 0:
            stats['avg_execution_time'] = execution_time
        else:
            stats['avg_execution_time'] = (stats['avg_execution_time'] * 0.9 + execution_time * 0.1)
    
    def get_stats(self, handler_name: str) -> Optional[Dict[str, Any]]:
        """获取处理器统计"""
        return self._handler_stats.get(handler_name)
    
    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """获取所有处理器统计"""
        return dict(self._handler_stats)


class EventRouter:
    """
    智能事件路由器
    
    功能特性：
    1. 灵活的路由规则配置
    2. 多种路由策略支持
    3. 高级事件过滤
    4. 处理器负载均衡
    5. 路由性能监控
    """
    
    def __init__(self,
                 name: str = "EventRouter",
                 max_workers: int = 10,
                 enable_metrics: bool = True):
        
        self._name = name
        self._max_workers = max_workers
        self._enable_metrics = enable_metrics
        
        # 路由规则
        self._rules: List[RouteRule] = []
        self._rules_lock = threading.Lock()
        
        # 处理器注册表
        self._handler_registry = HandlerRegistry()
        
        # 路由状态
        self._round_robin_counters: Dict[str, int] = defaultdict(int)
        self._handler_loads: Dict[str, float] = defaultdict(float)
        
        # 线程池
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix=f"{name}-Router")
        
        # 统计信息
        self._routing_stats = {
            'total_routed': 0,
            'successful_routes': 0,
            'failed_routes': 0,
            'avg_routing_time': 0.0,
            'rule_hit_counts': defaultdict(int),
            'strategy_usage': defaultdict(int)
        }
        self._routing_history: deque = deque(maxlen=10000)
        
        logger.info(f"EventRouter '{name}' initialized")
    
    def add_rule(self, rule: RouteRule) -> None:
        """添加路由规则"""
        with self._rules_lock:
            # 按优先级插入
            inserted = False
            for i, existing_rule in enumerate(self._rules):
                if rule.priority > existing_rule.priority:
                    self._rules.insert(i, rule)
                    inserted = True
                    break
            
            if not inserted:
                self._rules.append(rule)
        
        logger.info(f"Added routing rule: {rule.name} (priority: {rule.priority})")
    
    def remove_rule(self, rule_name: str) -> bool:
        """移除路由规则"""
        with self._rules_lock:
            for i, rule in enumerate(self._rules):
                if rule.name == rule_name:
                    del self._rules[i]
                    logger.info(f"Removed routing rule: {rule_name}")
                    return True
        return False
    
    def get_rule(self, rule_name: str) -> Optional[RouteRule]:
        """获取路由规则"""
        with self._rules_lock:
            for rule in self._rules:
                if rule.name == rule_name:
                    return rule
        return None
    
    def list_rules(self) -> List[RouteRule]:
        """列出所有路由规则"""
        with self._rules_lock:
            return self._rules.copy()
    
    def enable_rule(self, rule_name: str) -> bool:
        """启用路由规则"""
        rule = self.get_rule(rule_name)
        if rule:
            rule.enabled = True
            logger.info(f"Enabled routing rule: {rule_name}")
            return True
        return False
    
    def disable_rule(self, rule_name: str) -> bool:
        """禁用路由规则"""
        rule = self.get_rule(rule_name)
        if rule:
            rule.enabled = False
            logger.info(f"Disabled routing rule: {rule_name}")
            return True
        return False
    
    def register_handler(self, name: str, handler: Callable, **metadata) -> None:
        """注册处理器"""
        self._handler_registry.register_handler(name, handler, **metadata)
    
    def unregister_handler(self, name: str) -> bool:
        """注销处理器"""
        return self._handler_registry.unregister_handler(name)
    
    def route_event(self, event: Union[Event, TypedEvent]) -> List[RoutingResult]:
        """
        路由事件
        
        Args:
            event: 要路由的事件
            
        Returns:
            路由结果列表
        """
        start_time = time.time()
        results = []
        
        try:
            # 查找匹配的规则
            matching_rules = self._find_matching_rules(event)
            
            if not matching_rules:
                logger.debug(f"No routing rules matched for event: {self._get_event_type(event)}")
                return results
            
            # 执行路由
            for rule in matching_rules:
                try:
                    result = self._execute_routing_rule(event, rule)
                    results.append(result)
                    
                    # 更新统计
                    self._update_routing_stats(rule, result, time.time() - start_time)
                    
                    if result.success:
                        self._routing_stats['successful_routes'] += 1
                    else:
                        self._routing_stats['failed_routes'] += 1
                        logger.warning(f"Rule '{rule.name}' execution failed: {result.error}")
                        
                except Exception as e:
                    logger.error(f"Error executing rule '{rule.name}': {e}", exc_info=True)
                    self._routing_stats['failed_routes'] += 1
                    
                    # 创建错误结果
                    results.append(RoutingResult(
                        rule_name=rule.name,
                        target_handlers=rule.target_handlers,
                        strategy=rule.strategy,
                        routing_time=time.time() - start_time,
                        success=False,
                        error=str(e)
                    ))
            
            self._routing_stats['total_routed'] += 1
            
        except Exception as e:
            logger.error(f"Error routing event: {e}", exc_info=True)
            self._routing_stats['failed_routes'] += 1
            
            # 创建错误结果
            results.append(RoutingResult(
                rule_name="error",
                target_handlers=[],
                strategy=RoutingStrategy.BROADCAST,
                routing_time=time.time() - start_time,
                success=False,
                error=str(e)
            ))
        
        return results
    
    def _find_matching_rules(self, event: Union[Event, TypedEvent]) -> List[RouteRule]:
        """查找匹配的路由规则"""
        matching_rules = []
        
        with self._rules_lock:
            for rule in self._rules:
                if rule.matches_event(event):
                    matching_rules.append(rule)
        
        return matching_rules
    
    def _execute_routing_rule(self, event: Union[Event, TypedEvent], rule: RouteRule) -> RoutingResult:
        """执行路由规则"""
        start_time = time.time()
        
        try:
            # 选择目标处理器
            selected_handlers = self._select_handlers(rule.target_handlers, rule.strategy)
            
            # 执行处理器
            self._invoke_handlers(event, selected_handlers, rule)
            
            return RoutingResult(
                rule_name=rule.name,
                target_handlers=selected_handlers,
                strategy=rule.strategy,
                routing_time=time.time() - start_time,
                success=True
            )
            
        except Exception as e:
            logger.error(f"Error executing routing rule '{rule.name}': {e}", exc_info=True)
            return RoutingResult(
                rule_name=rule.name,
                target_handlers=rule.target_handlers,
                strategy=rule.strategy,
                routing_time=time.time() - start_time,
                success=False,
                error=str(e)
            )
    
    def _select_handlers(self, available_handlers: List[str], strategy: RoutingStrategy) -> List[str]:
        """根据策略选择处理器"""
        if not available_handlers:
            return []
        
        # 过滤存在的处理器
        valid_handlers = [h for h in available_handlers if self._handler_registry.get_handler(h) is not None]
        
        if not valid_handlers:
            logger.warning(f"No valid handlers found in: {available_handlers}")
            return []
        
        if strategy == RoutingStrategy.BROADCAST:
            return valid_handlers
        elif strategy == RoutingStrategy.FIRST_MATCH:
            return [valid_handlers[0]]
        elif strategy == RoutingStrategy.ROUND_ROBIN:
            return self._round_robin_select(valid_handlers)
        elif strategy == RoutingStrategy.LOAD_BALANCED:
            return self._load_balanced_select(valid_handlers)
        elif strategy == RoutingStrategy.RANDOM:
            import random
            return [random.choice(valid_handlers)]
        else:
            # 默认广播
            return valid_handlers
    
    def _round_robin_select(self, handlers: List[str]) -> List[str]:
        """轮询选择处理器"""
        if not handlers:
            return []
        
        handlers_key = ','.join(sorted(handlers))
        counter = self._round_robin_counters[handlers_key]
        selected = handlers[counter % len(handlers)]
        self._round_robin_counters[handlers_key] = counter + 1
        
        return [selected]
    
    def _load_balanced_select(self, handlers: List[str]) -> List[str]:
        """负载均衡选择处理器"""
        if not handlers:
            return []
        
        # 选择负载最低的处理器
        min_load = float('inf')
        selected_handler = handlers[0]
        
        for handler in handlers:
            load = self._handler_loads.get(handler, 0.0)
            if load < min_load:
                min_load = load
                selected_handler = handler
        
        return [selected_handler]
    
    def _invoke_handlers(self, event: Union[Event, TypedEvent], handlers: List[str], rule: RouteRule) -> None:
        """调用处理器"""
        for handler_name in handlers:
            handler = self._handler_registry.get_handler(handler_name)
            if handler is None:
                logger.warning(f"Handler '{handler_name}' not found")
                continue
            
            # 异步调用处理器
            future = self._executor.submit(self._call_handler, handler, event, handler_name, rule)
            
            # 可以选择等待结果或继续（这里选择继续以提高性能）
            # future.result(timeout=rule.timeout)  # 如果需要同步等待
    
    def _call_handler(self, handler: Callable, event: Union[Event, TypedEvent],
                     handler_name: str, rule: RouteRule) -> None:
        """调用单个处理器"""
        start_time = time.time()
        success = False
        
        try:
            # 更新负载
            self._handler_loads[handler_name] += 1.0
            
            # 调用处理器 - 传递事件数据而不是整个事件对象
            if isinstance(event, TypedEvent):
                # 对于类型化事件，传递data属性
                handler(event.data)
            else:
                # 传统事件，传递data属性
                handler(event.data)
            
            success = True
            logger.debug(f"Handler '{handler_name}' processed event successfully")
            
        except Exception as e:
            logger.error(f"Handler '{handler_name}' failed to process event: {e}", exc_info=True)
            
        finally:
            execution_time = time.time() - start_time
            
            # 更新负载
            self._handler_loads[handler_name] = max(0.0, self._handler_loads[handler_name] - 1.0)
            
            # 更新统计
            self._handler_registry.update_stats(handler_name, success, execution_time)
    
    def _update_routing_stats(self, rule: RouteRule, result: RoutingResult, routing_time: float) -> None:
        """更新路由统计"""
        if not self._enable_metrics:
            return
        
        # 更新规则命中次数
        self._routing_stats['rule_hit_counts'][rule.name] += 1
        
        # 更新策略使用次数
        self._routing_stats['strategy_usage'][rule.strategy.value] += 1
        
        # 更新平均路由时间
        current_avg = self._routing_stats['avg_routing_time']
        if current_avg == 0:
            self._routing_stats['avg_routing_time'] = routing_time
        else:
            self._routing_stats['avg_routing_time'] = current_avg * 0.9 + routing_time * 0.1
        
        # 记录路由历史
        self._routing_history.append({
            'timestamp': time.time(),
            'rule_name': rule.name,
            'strategy': rule.strategy.value,
            'target_handlers': result.target_handlers,
            'success': result.success,
            'routing_time': routing_time
        })

    @staticmethod
    def _get_event_type(event: Union[Event, TypedEvent]) -> str:
        """获取事件类型"""
        return event.event_type if isinstance(event, TypedEvent) else event.type
    
    def get_stats(self) -> Dict[str, Any]:
        """获取路由器统计信息"""
        stats = {
            'name': self._name,
            'handler_stats': self._handler_registry.get_all_stats(),
            'active_rules': len([r for r in self._rules if r.enabled]),
            'total_rules': len(self._rules),
            'registered_handlers': len(self._handler_registry.list_handlers()),
            'current_loads': dict(self._handler_loads)
        }
        # 将routing_stats的内容直接合并到返回字典中
        stats.update(self._routing_stats)
        return stats
    
    def get_rule_stats(self) -> Dict[str, Any]:
        """获取规则统计信息"""
        rule_stats = {}
        
        with self._rules_lock:
            for rule in self._rules:
                rule_stats[rule.name] = {
                    'pattern': rule.pattern,
                    'strategy': rule.strategy.value,
                    'priority': rule.priority,
                    'enabled': rule.enabled,
                    'target_handlers': rule.target_handlers,
                    'filter_count': len(rule.filters),
                    'hit_count': self._routing_stats['rule_hit_counts'].get(rule.name, 0)
                }
        
        return rule_stats
    
    def shutdown(self) -> None:
        """关闭路由器"""
        logger.info(f"Shutting down EventRouter '{self._name}'...")
        
        # 关闭线程池
        self._executor.shutdown(wait=True)
        
        logger.info(f"EventRouter '{self._name}' shutdown complete")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.shutdown()
        return False


# 便捷函数
def create_simple_rule(name: str, pattern: str, handlers: List[str], 
                      strategy: RoutingStrategy = RoutingStrategy.BROADCAST) -> RouteRule:
    """创建简单路由规则"""
    return RouteRule(
        name=name,
        pattern=pattern,
        target_handlers=handlers,
        strategy=strategy
    )


def create_filtered_rule(name: str, pattern: str, handlers: List[str],
                        filters: List[RouteFilter],
                        strategy: RoutingStrategy = RoutingStrategy.BROADCAST) -> RouteRule:
    """创建带过滤器的路由规则"""
    return RouteRule(
        name=name,
        pattern=pattern,
        filters=filters,
        target_handlers=handlers,
        strategy=strategy
    )


def create_filter(field_str: str, operator: FilterOperator, value: Any, **kwargs) -> RouteFilter:
    """创建路由过滤器"""
    return RouteFilter(
        field=field_str,
        operator=operator,
        value=value,
        **kwargs
    )