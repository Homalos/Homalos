#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos_v2
@FileName   : enhanced_event_bus_v2
@Date       : 2025/1/16
@Author     : Donny
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 增强事件总线 V2 - 第二阶段优化版本
整合异步处理池、事件调度器、类型安全、路由机制和健康监控
"""

import json
import threading
import time
import uuid
import weakref
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Callable, Set, TypeVar

from src.core.async_handler_pool import AsyncHandlerPool, ExecutionResult
from src.core.event_router import EventRouter, RoutingStrategy
from src.core.event_scheduler import EventScheduler, SchedulingStrategy, ExecutionMode
from src.core.event_types import TypedEvent, EventTypeRegistry
from src.core.health_monitor import HealthMonitor, HealthCheck, HealthStatus, HealthCheckResult
from src.core.logger import get_logger

logger = get_logger("EnhancedEventBus")

T = TypeVar('T')


class EventBusStatus(Enum):
    """事件总线状态"""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"


class ProcessingMode(Enum):
    """处理模式"""
    SYNC_ONLY = "sync_only"  # 仅同步处理
    ASYNC_ONLY = "async_only"  # 仅异步处理
    HYBRID = "hybrid"  # 混合处理
    AUTO = "auto"  # 自动选择


@dataclass
class EventBusConfig:
    """事件总线配置"""
    # 基础配置
    name: str = "EnhancedEventBus"
    max_queue_size: int = 10000
    processing_mode: ProcessingMode = ProcessingMode.HYBRID
    
    # 异步处理池配置
    async_pool_size: int = 10
    sync_pool_size: int = 5
    pool_timeout: float = 30.0
    
    # 调度器配置
    scheduling_strategy: SchedulingStrategy = SchedulingStrategy.ADAPTIVE
    execution_mode: ExecutionMode = ExecutionMode.AUTO
    
    # 路由配置
    routing_strategy: RoutingStrategy = RoutingStrategy.BROADCAST
    enable_event_filtering: bool = True
    
    # 健康监控配置
    enable_health_monitoring: bool = True
    health_check_interval: float = 30.0
    
    # 性能配置
    enable_metrics: bool = True
    metrics_history_size: int = 1000
    enable_detailed_logging: bool = False
    
    # 容错配置
    max_retry_attempts: int = 3
    retry_delay: float = 1.0
    enable_circuit_breaker: bool = True
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout: float = 60.0


@dataclass
class EventProcessingResult:
    """事件处理结果"""
    event_id: str
    event_type: str
    success: bool
    execution_time: float
    handler_count: int
    error_count: int
    retry_count: int
    details: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'event_id': self.event_id,
            'event_type': self.event_type,
            'success': self.success,
            'execution_time': self.execution_time,
            'handler_count': self.handler_count,
            'error_count': self.error_count,
            'retry_count': self.retry_count,
            'details': self.details,
            'errors': self.errors,
            'timestamp': self.timestamp
        }


@dataclass
class EventBusMetrics:
    """事件总线指标"""
    # 基础统计
    total_events_published: int = 0
    total_events_processed: int = 0
    total_events_failed: int = 0
    total_events_retried: int = 0
    
    # 性能统计
    avg_processing_time: float = 0.0
    max_processing_time: float = 0.0
    min_processing_time: float = float('inf')
    
    # 队列统计
    current_queue_size: int = 0
    max_queue_size_reached: int = 0
    queue_overflow_count: int = 0
    
    # 处理器统计
    active_handlers: int = 0
    total_handlers_registered: int = 0
    
    # 健康统计
    health_status: str = "unknown"
    last_health_check: float = 0.0
    
    # 时间戳
    timestamp: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'total_events_published': self.total_events_published,
            'total_events_processed': self.total_events_processed,
            'total_events_failed': self.total_events_failed,
            'total_events_retried': self.total_events_retried,
            'avg_processing_time': self.avg_processing_time,
            'max_processing_time': self.max_processing_time,
            'min_processing_time': self.min_processing_time if self.min_processing_time != float('inf') else 0.0,
            'current_queue_size': self.current_queue_size,
            'max_queue_size_reached': self.max_queue_size_reached,
            'queue_overflow_count': self.queue_overflow_count,
            'active_handlers': self.active_handlers,
            'total_handlers_registered': self.total_handlers_registered,
            'health_status': self.health_status,
            'last_health_check': self.last_health_check,
            'timestamp': self.timestamp
        }


class EventBusHealthCheck(HealthCheck):
    """事件总线健康检查"""
    
    def __init__(self, event_bus: 'EnhancedEventBus', **kwargs):
        super().__init__("event_bus_v2", **kwargs)
        self.event_bus = weakref.ref(event_bus)  # 使用弱引用避免循环引用
    
    async def check(self) -> HealthCheckResult:
        """检查事件总线健康状态"""
        try:
            bus = self.event_bus()
            if bus is None:
                return HealthCheckResult(
                    check_name=self.name,
                    status=HealthStatus.CRITICAL,
                    message="Event bus instance no longer exists"
                )
            
            if bus.status != EventBusStatus.RUNNING:
                return HealthCheckResult(
                    check_name=self.name,
                    status=HealthStatus.CRITICAL,
                    message=f"Event bus is not running (status: {bus.status.value})"
                )
            
            # 获取指标
            metrics = bus.get_metrics()
            
            # 检查队列使用率
            queue_usage = (metrics.current_queue_size / bus.config.max_queue_size) * 100
            
            # 检查错误率
            total_processed = metrics.total_events_processed
            error_rate = (metrics.total_events_failed / total_processed) * 100 if total_processed > 0 else 0
            
            # 检查平均处理时间
            avg_time = metrics.avg_processing_time
            
            # 判断状态
            status = HealthStatus.HEALTHY
            messages = []
            
            if queue_usage > 80:
                status = HealthStatus.WARNING if queue_usage < 95 else HealthStatus.CRITICAL
                messages.append(f"High queue usage: {queue_usage:.1f}%")
            
            if error_rate > 5:
                if status != HealthStatus.CRITICAL:
                    status = HealthStatus.WARNING if error_rate < 20 else HealthStatus.CRITICAL
                messages.append(f"High error rate: {error_rate:.1f}%")
            
            if avg_time > 5.0:
                if status != HealthStatus.CRITICAL:
                    status = HealthStatus.WARNING if avg_time < 10.0 else HealthStatus.CRITICAL
                messages.append(f"High avg processing time: {avg_time:.2f}s")
            
            message = "; ".join(messages) if messages else "Event bus is healthy"
            
            return HealthCheckResult(
                check_name=self.name,
                status=status,
                message=message,
                details={
                    'queue_usage_percent': queue_usage,
                    'error_rate_percent': error_rate,
                    'avg_processing_time': avg_time,
                    'metrics': metrics.to_dict()
                }
            )
            
        except Exception as e:
            return HealthCheckResult(
                check_name=self.name,
                status=HealthStatus.UNKNOWN,
                message=f"Failed to check event bus: {str(e)}",
                error=str(e)
            )


class EnhancedEventBus:
    """
    增强事件总线 V2
    
    第二阶段优化特性：
    1. 异步处理器池 - 高并发异步处理
    2. 智能事件调度 - 多种调度策略
    3. 事件类型安全 - 强类型事件系统
    4. 智能事件路由 - 高级路由和过滤
    5. 健康监控系统 - 全面的健康检查
    6. 性能优化 - 更好的并发性能
    7. 容错机制 - 熔断器和重试
    """
    
    def __init__(self, config: Optional[EventBusConfig] = None):
        self.config = config or EventBusConfig()
        self._status = EventBusStatus.STOPPED
        self._start_time: Optional[float] = None
        
        # 核心组件
        self._handler_pool: Optional[AsyncHandlerPool] = None
        self._scheduler: Optional[EventScheduler] = None
        self._router: Optional[EventRouter] = None
        self._health_monitor: Optional[HealthMonitor] = None
        self._type_registry = EventTypeRegistry()
        
        # 事件队列
        self._event_queue: asyncio.Queue = asyncio.Queue(maxsize=self.config.max_queue_size)
        self._processing_tasks: Set[asyncio.Task] = set()
        
        # 处理器注册
        self._handlers: Dict[str, List[Callable]] = defaultdict(list)
        self._global_handlers: List[Callable] = []
        self._handlers_lock = threading.Lock()
        
        # 监控和指标
        self._metrics = EventBusMetrics()
        self._metrics_history: deque = deque(maxlen=self.config.metrics_history_size)
        self._processing_results: deque = deque(maxlen=1000)
        
        # 熔断器状态
        self._circuit_breaker_failures: Dict[str, int] = defaultdict(int)
        self._circuit_breaker_last_failure: Dict[str, float] = {}
        self._circuit_breaker_open: Set[str] = set()
        
        # 事件循环
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._loop_thread: Optional[threading.Thread] = None
        self._shutdown_event = asyncio.Event()
        
        logger.info(f"EnhancedEventBus '{self.config.name}' initialized")
    
    @property
    def name(self) -> str:
        """获取事件总线名称"""
        return self.config.name
    
    @property
    def status(self) -> EventBusStatus:
        """获取事件总线状态"""
        return self._status
    
    @property
    def is_running(self) -> bool:
        """是否正在运行"""
        return self._status == EventBusStatus.RUNNING
    
    def start(self) -> None:
        """启动事件总线"""
        if self._status != EventBusStatus.STOPPED:
            logger.warning(f"EventBus '{self.name}' is already running or starting")
            return
        
        logger.info(f"Starting EventBus '{self.name}'...")
        self._status = EventBusStatus.STARTING
        
        try:
            # 启动事件循环线程
            self._start_event_loop()
            
            # 等待事件循环启动
            timeout = 10.0
            start_time = time.time()
            while self._loop is None and time.time() - start_time < timeout:
                time.sleep(0.1)
            
            if self._loop is None:
                raise RuntimeError("Failed to start event loop")
            
            # 在事件循环中初始化组件
            future = asyncio.run_coroutine_threadsafe(self._initialize_components(), self._loop)
            future.result(timeout=30.0)
            
            self._status = EventBusStatus.RUNNING
            self._start_time = time.time()
            
            logger.info(f"EventBus '{self.name}' started successfully")
            
        except Exception as e:
            self._status = EventBusStatus.ERROR
            logger.error(f"Failed to start EventBus '{self.name}': {e}", exc_info=True)
            raise
    
    def stop(self, timeout: float = 30.0) -> None:
        """停止事件总线"""
        if self._status not in [EventBusStatus.RUNNING, EventBusStatus.ERROR]:
            return
        
        logger.info(f"Stopping EventBus '{self.name}'...")
        self._status = EventBusStatus.STOPPING
        
        try:
            if self._loop and self._loop.is_running():
                # 在事件循环中执行清理
                future = asyncio.run_coroutine_threadsafe(self._cleanup_components(), self._loop)
                future.result(timeout=timeout)
                
                # 停止事件循环
                self._loop.call_soon_threadsafe(self._shutdown_event.set)
            
            # 等待事件循环线程结束
            if self._loop_thread and self._loop_thread.is_alive():
                self._loop_thread.join(timeout=timeout)
            
            self._status = EventBusStatus.STOPPED
            logger.info(f"EventBus '{self.name}' stopped")
            
        except Exception as e:
            self._status = EventBusStatus.ERROR
            logger.error(f"Error stopping EventBus '{self.name}': {e}", exc_info=True)
    
    def _start_event_loop(self) -> None:
        """启动事件循环线程"""
        def run_loop():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            
            try:
                self._loop.run_until_complete(self._event_loop_main())
            except Exception as e:
                logger.error(f"Event loop error: {e}", exc_info=True)
            finally:
                self._loop.close()
                self._loop = None
        
        self._loop_thread = threading.Thread(
            target=run_loop,
            name=f"{self.name}-EventLoop",
            daemon=True
        )
        self._loop_thread.start()
    
    async def _event_loop_main(self) -> None:
        """事件循环主函数"""
        logger.debug(f"Event loop started for '{self.name}'")
        
        # 启动事件处理任务
        processing_task = asyncio.create_task(self._process_events())
        
        # 等待关闭信号
        await self._shutdown_event.wait()
        
        # 取消处理任务
        processing_task.cancel()
        
        # 等待所有处理任务完成
        if self._processing_tasks:
            await asyncio.gather(*self._processing_tasks, return_exceptions=True)
        
        logger.debug(f"Event loop stopped for '{self.name}'")
    
    async def _initialize_components(self) -> None:
        """初始化组件"""
        logger.debug(f"Initializing components for '{self.name}'")
        
        # 初始化异步处理器池
        self._handler_pool = AsyncHandlerPool(
            name=f"{self.name}-HandlerPool",
            max_async_tasks=self.config.async_pool_size,
            max_workers=self.config.sync_pool_size,
            default_timeout=self.config.pool_timeout
        )
        
        # 初始化事件调度器
        self._scheduler = EventScheduler(
            name=f"{self.name}-Scheduler",
            strategy=self.config.scheduling_strategy,
            execution_mode=self.config.execution_mode
        )
        
        # 初始化事件路由器
        self._router = EventRouter(
            name=f"{self.name}-Router"
        )
        
        # 初始化健康监控
        if self.config.enable_health_monitoring:
            self._health_monitor = HealthMonitor(
                name=f"{self.name}-HealthMonitor",
                check_interval=self.config.health_check_interval
            )
            
            # 添加事件总线健康检查
            self._health_monitor.add_check(EventBusHealthCheck(self))
            self._health_monitor.start()
        
        logger.debug(f"Components initialized for '{self.name}'")
    
    async def _cleanup_components(self) -> None:
        """清理组件"""
        logger.debug(f"Cleaning up components for '{self.name}'")
        
        # 停止健康监控
        if self._health_monitor:
            self._health_monitor.stop()
        
        # 停止处理器池
        if self._handler_pool:
            self._handler_pool.shutdown()
        
        logger.debug(f"Components cleaned up for '{self.name}'")
    
    async def _process_events(self) -> None:
        """处理事件主循环"""
        logger.debug(f"Event processing started for '{self.name}'")
        
        while not self._shutdown_event.is_set():
            try:
                # 等待事件（带超时）
                try:
                    event_data = await asyncio.wait_for(
                        self._event_queue.get(),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue
                
                # 创建处理任务
                task = asyncio.create_task(self._handle_event(event_data))
                self._processing_tasks.add(task)
                
                # 清理完成的任务
                self._processing_tasks = {t for t in self._processing_tasks if not t.done()}
                
            except Exception as e:
                logger.error(f"Error in event processing loop: {e}", exc_info=True)
                await asyncio.sleep(0.1)
        
        logger.debug(f"Event processing stopped for '{self.name}'")
    
    async def _handle_event(self, event_data: Dict[str, Any]) -> None:
        """处理单个事件"""
        event_id = event_data.get('id', str(uuid.uuid4()))
        event_type = event_data.get('type', 'unknown')
        
        start_time = time.time()
        result = EventProcessingResult(
            event_id=event_id,
            event_type=event_type,
            success=False,
            execution_time=0.0,
            handler_count=0,
            error_count=0,
            retry_count=0
        )
        
        try:
            # 检查熔断器
            if self._is_circuit_breaker_open(event_type):
                logger.warning(f"Circuit breaker open for event type: {event_type}")
                result.errors.append("Circuit breaker open")
                result.error_count += 1
                # 更新指标并标记任务完成
                result.execution_time = time.time() - start_time
                self._update_metrics(result)
                self._processing_results.append(result)
                self._event_queue.task_done()
                return
            
            # 获取处理器
            handlers = self._get_handlers_for_event(event_type)
            result.handler_count = len(handlers)
            
            if not handlers:
                logger.debug(f"No handlers found for event type: {event_type}")
                result.success = True
                # 更新指标并标记任务完成
                result.execution_time = time.time() - start_time
                self._update_metrics(result)
                self._processing_results.append(result)
                self._event_queue.task_done()
                return
            
            # 使用路由器过滤处理器
            if self._router and self.config.enable_event_filtering:
                from src.core.event import Event
                event = Event(
                    event_type=event_type,
                    data=event_data.get('data', {})
                )
                routing_results = self._router.route_event(event)
                if routing_results:
                    # 从路由结果中提取处理器名称，然后获取实际的处理器函数
                    handler_names = []
                    for result in routing_results:
                        if result.success:
                            handler_names.extend(result.target_handlers)
                    
                    # 根据处理器名称获取实际的处理器函数
                    routed_handlers = []
                    for name in handler_names:
                        handler = self._router._handler_registry.get_handler(name)
                        if handler:
                            routed_handlers.append(handler)
                    
                    handlers = routed_handlers if routed_handlers else handlers
            
            # 直接执行处理器（调度器主要用于事件队列管理）
            execution_results = await self._execute_handlers_direct(event_data, handlers)
            
            # 处理执行结果
            success_count = 0
            for exec_result in execution_results:
                if exec_result.success:
                    success_count += 1
                else:
                    result.error_count += 1
                    if exec_result.error:
                        result.errors.append(str(exec_result.error))
            
            result.success = success_count > 0
            
            # 重置熔断器计数（如果有成功的处理）
            if success_count > 0:
                self._reset_circuit_breaker(event_type)
            else:
                self._increment_circuit_breaker(event_type)
            
        except Exception as e:
            logger.error(f"Error handling event {event_id}: {e}", exc_info=True)
            result.errors.append(str(e))
            result.error_count += 1
            self._increment_circuit_breaker(event_type)
        
        finally:
            # 更新结果
            result.execution_time = time.time() - start_time
            
            # 更新指标
            self._update_metrics(result)
            
            # 存储结果
            self._processing_results.append(result)
            
            # 标记队列任务完成
            self._event_queue.task_done()
    
    async def _execute_handlers_direct(self, event_data: Dict[str, Any], handlers: List[Callable]) -> List[ExecutionResult]:
        """直接执行处理器"""
        results = []
        
        for handler in handlers:
            try:
                # 直接调用处理器，不使用AsyncHandlerPool
                # 因为AsyncHandlerPool需要Event对象，而我们这里有的是字典数据
                start_time = time.time()
                handler_result = None
                
                # 检查处理器是否期望Event对象（通过检查参数名称）
                import inspect
                sig = inspect.signature(handler)
                param_names = list(sig.parameters.keys())
                
                # 如果处理器的第一个参数名为'event'，则创建Event对象
                if param_names and param_names[0] == 'event':
                    from src.core.event import Event, EventPriority
                    event_obj = Event(
                        event_type=event_data.get('type', 'unknown'),
                        data=event_data.get('data', {}),
                        source=event_data.get('source', 'unknown'),
                        priority=EventPriority.NORMAL,
                        timestamp=int(event_data.get('timestamp', time.time()) * 1_000_000_000)
                    )
                    
                    if asyncio.iscoroutinefunction(handler):
                        handler_result = await handler(event_obj)
                    else:
                        handler_result = handler(event_obj)
                else:
                    # 否则直接传递字典数据
                    if asyncio.iscoroutinefunction(handler):
                        handler_result = await handler(event_data)
                    else:
                        handler_result = handler(event_data)
                
                result = ExecutionResult(
                    success=True,
                    result=handler_result,
                    execution_time=time.time() - start_time
                )
                
                results.append(result)
                
            except Exception as e:
                results.append(ExecutionResult(
                    success=False,
                    error=e,
                    execution_time=time.time() - start_time
                ))
        
        return results
    
    def _get_handlers_for_event(self, event_type: str) -> List[Callable]:
        """获取事件的处理器"""
        import fnmatch
        handlers = []
        
        with self._handlers_lock:
            # 添加精确匹配的处理器
            handlers.extend(self._handlers.get(event_type, []))
            
            # 添加通配符匹配的处理器
            for pattern, pattern_handlers in self._handlers.items():
                if pattern != event_type and fnmatch.fnmatch(event_type, pattern):
                    handlers.extend(pattern_handlers)
            
            # 添加全局处理器
            handlers.extend(self._global_handlers)
        
        return handlers
    
    def _is_circuit_breaker_open(self, event_type: str) -> bool:
        """检查熔断器是否打开"""
        if not self.config.enable_circuit_breaker:
            return False
        
        if event_type in self._circuit_breaker_open:
            # 检查是否应该重置
            last_failure = self._circuit_breaker_last_failure.get(event_type, 0)
            if time.time() - last_failure > self.config.circuit_breaker_timeout:
                self._circuit_breaker_open.discard(event_type)
                self._circuit_breaker_failures[event_type] = 0
                return False
            return True
        
        return False
    
    def _increment_circuit_breaker(self, event_type: str) -> None:
        """增加熔断器失败计数"""
        if not self.config.enable_circuit_breaker:
            return
        
        self._circuit_breaker_failures[event_type] += 1
        self._circuit_breaker_last_failure[event_type] = time.time()
        
        if self._circuit_breaker_failures[event_type] >= self.config.circuit_breaker_threshold:
            self._circuit_breaker_open.add(event_type)
            logger.warning(f"Circuit breaker opened for event type: {event_type}")
    
    def _reset_circuit_breaker(self, event_type: str) -> None:
        """重置熔断器"""
        if event_type in self._circuit_breaker_failures:
            self._circuit_breaker_failures[event_type] = 0
        self._circuit_breaker_open.discard(event_type)
    
    def _update_metrics(self, result: EventProcessingResult) -> None:
        """更新指标"""
        self._metrics.total_events_processed += 1
        
        if result.success:
            # 更新处理时间统计
            if self._metrics.avg_processing_time == 0:
                self._metrics.avg_processing_time = result.execution_time
            else:
                self._metrics.avg_processing_time = (
                    self._metrics.avg_processing_time * 0.9 + result.execution_time * 0.1
                )
            
            self._metrics.max_processing_time = max(
                self._metrics.max_processing_time, result.execution_time
            )
            self._metrics.min_processing_time = min(
                self._metrics.min_processing_time, result.execution_time
            )
        else:
            self._metrics.total_events_failed += 1
        
        if result.retry_count > 0:
            self._metrics.total_events_retried += 1
        
        # 更新队列统计
        self._metrics.current_queue_size = self._event_queue.qsize()
        self._metrics.max_queue_size_reached = max(
            self._metrics.max_queue_size_reached, self._metrics.current_queue_size
        )
        
        # 更新处理器统计
        with self._handlers_lock:
            self._metrics.total_handlers_registered = sum(
                len(handlers) for handlers in self._handlers.values()
            ) + len(self._global_handlers)
        
        # 更新健康状态
        if self._health_monitor:
            self._metrics.health_status = self._health_monitor.get_overall_health().value
            self._metrics.last_health_check = time.time()
        
        # 添加到历史记录
        self._metrics.timestamp = time.time()
        self._metrics_history.append(self._metrics.to_dict())
    
    # 公共接口方法
    
    def subscribe(self, event_type: str, handler: Callable) -> None:
        """订阅事件"""
        with self._handlers_lock:
            self._handlers[event_type].append(handler)
        
        logger.debug(f"Handler subscribed to event type: {event_type}")
    
    def unsubscribe(self, event_type: str, handler: Callable) -> bool:
        """取消订阅事件"""
        with self._handlers_lock:
            if event_type in self._handlers and handler in self._handlers[event_type]:
                self._handlers[event_type].remove(handler)
                if not self._handlers[event_type]:
                    del self._handlers[event_type]
                logger.debug(f"Handler unsubscribed from event type: {event_type}")
                return True
        return False
    
    def subscribe_global(self, handler: Callable) -> None:
        """订阅全局事件"""
        with self._handlers_lock:
            self._global_handlers.append(handler)
        
        logger.debug("Global handler subscribed")
    
    def unsubscribe_global(self, handler: Callable) -> bool:
        """取消订阅全局事件"""
        with self._handlers_lock:
            if handler in self._global_handlers:
                self._global_handlers.remove(handler)
                logger.debug("Global handler unsubscribed")
                return True
        return False
    
    def publish(self, event_type: str, data: Any = None, **kwargs) -> str:
        """发布事件"""
        if not self.is_running:
            raise RuntimeError(f"EventBus '{self.name}' is not running")
        
        # 创建事件数据
        event_data = {
            'id': str(uuid.uuid4()),
            'type': event_type,
            'data': data,
            'timestamp': time.time(),
            **kwargs
        }
        
        # 添加到队列
        try:
            if self._loop:
                asyncio.run_coroutine_threadsafe(
                    self._event_queue.put(event_data),
                    self._loop
                )
            else:
                raise RuntimeError("Event loop not available")
            
            self._metrics.total_events_published += 1
            
            if self.config.enable_detailed_logging:
                logger.debug(f"Event published: {event_type} (id: {event_data['id']})")
            
            return event_data['id']
            
        except Exception as e:
            logger.error(f"Failed to publish event: {e}", exc_info=True)
            raise
    
    def publish_typed(self, event: TypedEvent[T]) -> str:
        """发布类型化事件"""
        return self.publish(
            event_type=event.event_type,
            data=event.data,
            metadata=event.metadata,
            category=event.category.value if event.category else None,
            severity=event.severity.value if event.severity else None
        )
    
    def get_metrics(self) -> EventBusMetrics:
        """获取指标"""
        # 更新当前队列大小
        self._metrics.current_queue_size = self._event_queue.qsize()
        return self._metrics
    
    def get_metrics_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取指标历史"""
        return list(self._metrics_history)[-limit:]
    
    def get_processing_results(self, limit: int = 100) -> List[EventProcessingResult]:
        """获取处理结果"""
        return list(self._processing_results)[-limit:]
    
    def get_health_report(self) -> Optional[Dict[str, Any]]:
        """获取健康报告"""
        if self._health_monitor:
            return self._health_monitor.get_health_report()
        return None
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        uptime = time.time() - self._start_time if self._start_time else 0
        
        stats = {
            'name': self.name,
            'status': self._status.value,
            'uptime': uptime,
            'config': {
                'max_queue_size': self.config.max_queue_size,
                'processing_mode': self.config.processing_mode.value,
                'async_pool_size': self.config.async_pool_size,
                'sync_pool_size': self.config.sync_pool_size
            },
            'metrics': self._metrics.to_dict(),
            'queue_size': self._event_queue.qsize(),
            'active_tasks': len(self._processing_tasks),
            'circuit_breaker_open': list(self._circuit_breaker_open)
        }
        
        # 添加组件统计
        if self._handler_pool:
            stats['handler_pool'] = self._handler_pool.get_stats()
        
        if self._scheduler:
            stats['scheduler'] = self._scheduler.get_stats()
        
        if self._router:
            stats['router'] = self._router.get_stats()
        
        if self._health_monitor:
            stats['health_monitor'] = self._health_monitor.get_stats()
        
        return stats
    
    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
        return False


# 便捷函数
def create_enhanced_event_bus(name: str = "EnhancedEventBus", **config_kwargs) -> EnhancedEventBus:
    """创建增强事件总线"""
    config = EventBusConfig(name=name, **config_kwargs)
    return EnhancedEventBus(config)


def create_high_performance_event_bus(name: str = "HighPerformanceEventBus") -> EnhancedEventBus:
    """创建高性能事件总线"""
    config = EventBusConfig(
        name=name,
        max_queue_size=50000,
        processing_mode=ProcessingMode.ASYNC_ONLY,
        async_pool_size=20,
        sync_pool_size=1,
        scheduling_strategy=SchedulingStrategy.LOAD_BALANCED,
        execution_mode=ExecutionMode.ASYNC_ONLY,
        enable_health_monitoring=True,
        enable_metrics=True,
        enable_circuit_breaker=True
    )
    return EnhancedEventBus(config)


if __name__ == "__main__":
    # 演示用法
    import asyncio
    
    async def demo():
        # 创建事件总线
        bus = create_enhanced_event_bus("DemoEventBus")
        
        # 定义处理器
        async def async_handler(event_data):
            print(f"Async handler: {event_data}")
            await asyncio.sleep(0.1)
        
        def sync_handler(event_data):
            print(f"Sync handler: {event_data}")
        
        try:
            # 启动事件总线
            bus.start()
            
            # 订阅事件
            bus.subscribe("test_event", async_handler)
            bus.subscribe("test_event", sync_handler)
            
            # 发布事件
            for i in range(5):
                event_id = bus.publish("test_event", {"message": f"Hello {i}"})
                print(f"Published event: {event_id}")
            
            # 等待处理完成
            await asyncio.sleep(2.0)
            
            # 获取统计信息
            stats = bus.get_stats()
            print(f"Stats: {json.dumps(stats, indent=2)}")
            
        finally:
            # 停止事件总线
            bus.stop()
    
    # 运行演示
    asyncio.run(demo())