#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos_v2
@FileName   : enhanced_event_bus
@Date       : 2025/1/16 
@Author     : Donny
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 增强版事件总线 - 第一阶段优化实现
包含：优先级队列、背压机制、事件监控、异常恢复机制
"""
import heapq
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from queue import Empty
from threading import Thread, Lock
from typing import Any, Dict, List, Callable, Optional

from src.core.event import Event, EventType, EventPriority
from src.core.logger import get_logger

logger = get_logger("EnhancedEventBus")


class BackpressureStrategy(Enum):
    """背压策略枚举"""
    DROP_OLDEST = "drop_oldest"  # 丢弃最旧的事件
    DROP_NEWEST = "drop_newest"  # 丢弃最新的事件
    DROP_LOW_PRIORITY = "drop_low_priority"  # 丢弃低优先级事件
    REJECT_NEW = "reject_new"  # 拒绝新事件


@dataclass
class EventMetrics:
    """事件处理指标"""
    event_type: str
    processing_time_ns: int
    queue_wait_time_ns: int
    success: bool
    error_message: Optional[str] = None
    timestamp: int = field(default_factory=lambda: time.time_ns())


@dataclass
class QueueStats:
    """队列统计信息"""
    current_size: int
    max_size: int
    total_enqueued: int
    total_dequeued: int
    total_dropped: int
    backpressure_triggered: int


class PriorityQueue:
    """线程安全的优先级队列实现"""
    
    def __init__(self, maxsize: int = 0):
        self._maxsize = maxsize
        self._queue = []
        self._index = 0  # 用于保证相同优先级事件的FIFO顺序
        self._lock = Lock()
        self._not_empty = threading.Condition(self._lock)
        self._not_full = threading.Condition(self._lock)
        
        # 统计信息
        self._enqueued_count = 0
        self._dequeued_count = 0
        self._dropped_count = 0
        
    def put(self, item: Event, block: bool = True, timeout: Optional[float] = None) -> bool:
        """放入事件，返回是否成功"""
        with self._not_full:
            if self._maxsize > 0:
                if not block:
                    if self._qsize() >= self._maxsize:
                        return False
                elif timeout is None:
                    while self._qsize() >= self._maxsize:
                        self._not_full.wait()
                elif timeout < 0:
                    raise ValueError("'timeout' must be a non-negative number")
                else:
                    endtime = time.time() + timeout
                    while self._qsize() >= self._maxsize:
                        remaining = endtime - time.time()
                        if remaining <= 0.0:
                            return False
                        self._not_full.wait(remaining)
            
            self._put(item)
            self._enqueued_count += 1
            self._not_empty.notify()
            return True
    
    def put_nowait(self, item: Event) -> bool:
        """非阻塞放入事件"""
        return self.put(item, block=False)
    
    def get(self, block: bool = True, timeout: Optional[float] = None) -> Event:
        """获取事件"""
        with self._not_empty:
            if not block:
                if not self._qsize():
                    raise Empty
            elif timeout is None:
                while not self._qsize():
                    self._not_empty.wait()
            elif timeout < 0:
                raise ValueError("'timeout' must be a non-negative number")
            else:
                endtime = time.time() + timeout
                while not self._qsize():
                    remaining = endtime - time.time()
                    if remaining <= 0.0:
                        raise Empty
                    self._not_empty.wait(remaining)
            
            item = self._get()
            self._dequeued_count += 1
            self._not_full.notify()
            return item
    
    def get_nowait(self) -> Event:
        """非阻塞获取事件"""
        return self.get(block=False)
    
    def _put(self, item: Event) -> None:
        """内部放入方法"""
        # 使用负优先级和索引确保优先级高的先出队，相同优先级FIFO
        heapq.heappush(self._queue, (item.priority.value, self._index, item))
        self._index += 1
    
    def _get(self) -> Event:
        """内部获取方法"""
        priority, index, item = heapq.heappop(self._queue)
        return item
    
    def _qsize(self) -> int:
        """队列大小"""
        return len(self._queue)
    
    def qsize(self) -> int:
        """线程安全的队列大小"""
        with self._lock:
            return self._qsize()
    
    def empty(self) -> bool:
        """队列是否为空"""
        with self._lock:
            return not self._qsize()
    
    def full(self) -> bool:
        """队列是否已满"""
        with self._lock:
            return 0 < self._maxsize <= self._qsize()
    
    def get_stats(self) -> QueueStats:
        """获取队列统计信息"""
        with self._lock:
            return QueueStats(
                current_size=self._qsize(),
                max_size=self._maxsize,
                total_enqueued=self._enqueued_count,
                total_dequeued=self._dequeued_count,
                total_dropped=self._dropped_count,
                backpressure_triggered=0  # 将在EnhancedEventBus中维护
            )
    
    def drop_event(self) -> None:
        """记录丢弃事件"""
        with self._lock:
            self._dropped_count += 1


class EnhancedEventBus:
    """
    增强版事件总线 - 第一阶段优化
    
    新增功能：
    1. 优先级队列处理
    2. 队列背压机制
    3. 事件处理监控
    4. 异常恢复机制
    5. 基础性能统计
    """
    
    # 默认配置参数
    DEFAULT_SYNC_QUEUE_SIZE = 10000
    DEFAULT_ASYNC_QUEUE_SIZE = 10000
    DEFAULT_TIMER_INTERVAL = 1
    DEFAULT_BACKPRESSURE_THRESHOLD = 0.8  # 80%触发背压
    DEFAULT_MAX_RETRY_ATTEMPTS = 3
    DEFAULT_RETRY_DELAY = 0.1  # 100ms
    
    def __init__(self,
                 name: str = "EnhancedEventBus",
                 interval: int = DEFAULT_TIMER_INTERVAL,
                 sync_queue_size: int = DEFAULT_SYNC_QUEUE_SIZE,
                 async_queue_size: int = DEFAULT_ASYNC_QUEUE_SIZE,
                 backpressure_threshold: float = DEFAULT_BACKPRESSURE_THRESHOLD,
                 backpressure_strategy: BackpressureStrategy = BackpressureStrategy.DROP_LOW_PRIORITY,
                 max_retry_attempts: int = DEFAULT_MAX_RETRY_ATTEMPTS,
                 retry_delay: float = DEFAULT_RETRY_DELAY):
        
        self._name = name
        self._interval = interval
        self._backpressure_threshold = backpressure_threshold
        self._backpressure_strategy = backpressure_strategy
        self._max_retry_attempts = max_retry_attempts
        self._retry_delay = retry_delay
        
        # 使用优先级队列替代普通队列
        self._sync_queue = PriorityQueue(maxsize=sync_queue_size)
        self._async_queue = PriorityQueue(maxsize=async_queue_size)
        
        # 事件处理器注册表
        self._sync_handlers: Dict[str, List[Callable]] = defaultdict(list)
        self._async_handlers: Dict[str, List[Callable]] = defaultdict(list)
        self._global_handlers: List[Callable] = []
        
        # 监控和统计
        self._monitors: List[Callable] = []
        self._event_metrics: deque = deque(maxlen=10000)  # 保留最近10000个事件指标
        self._processing_times: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        
        # 统计计数器
        self._event_count = 0
        self._sync_processed_count = 0
        self._async_processed_count = 0
        self._error_count = 0
        self._backpressure_triggered_count = 0
        self._retry_count = 0
        self._event_type_stats: Dict[str, int] = defaultdict(int)
        
        # 线程控制
        self._sync_active: bool = False
        self._async_active: bool = False
        self._sync_thread: Optional[Thread] = None
        self._async_thread: Optional[Thread] = None
        self._sync_timer: Optional[Thread] = None
        self._async_timer: Optional[Thread] = None
        
        # 启动事件处理线程
        self.start()

    def get_event_metrics(self) -> deque:
        return self._event_metrics
    
    def start(self) -> None:
        """启动所有事件处理线程"""
        self._start_sync()
        self._start_async()
        logger.info(f"EnhancedEventBus '{self._name}' engines started")
    
    def stop(self) -> None:
        """停止所有事件处理线程"""
        self._stop_sync()
        self._stop_async()
        logger.info(f"EnhancedEventBus '{self._name}' engines stopped")
    
    def _start_sync(self) -> None:
        """启动同步事件处理线程"""
        if self._sync_active:
            return
        
        self._sync_active = True
        self._sync_thread = Thread(
            target=self._run_sync_loop,
            name=f"EnhancedEventBus-{self._name}-SyncThread",
            daemon=True
        )
        self._sync_thread.start()
        
        self._sync_timer = Thread(
            target=self._run_timer,
            args=(self._sync_queue, self._interval),
            name=f"EnhancedEventBus-{self._name}-SyncTimer",
            daemon=True
        )
        self._sync_timer.start()
        logger.debug(f"Started sync engine for {self._name}")
    
    def _stop_sync(self) -> None:
        """停止同步事件处理引擎"""
        if not self._sync_active:
            return
        
        self._sync_active = False
        
        # 优雅关闭
        if self._sync_timer and self._sync_timer.is_alive():
            try:
                self._sync_timer.join(timeout=2.0)
            except Exception as e:
                logger.error(f"Error stopping sync timer: {e}")
        
        if self._sync_thread and self._sync_thread.is_alive():
            try:
                self._sync_queue.put_nowait(Event(EventType.SHUTDOWN))
                self._sync_thread.join(timeout=3.0)
            except Exception as e:
                logger.error(f"Error stopping sync thread: {e}")
        
        logger.info(f"Sync engine stopped for {self._name}")
    
    def _start_async(self) -> None:
        """启动异步事件处理线程"""
        if self._async_active:
            return
        
        self._async_active = True
        self._async_thread = Thread(
            target=self._run_async_loop,
            name=f"EnhancedEventBus-{self._name}-AsyncThread",
            daemon=True
        )
        self._async_thread.start()
        
        self._async_timer = Thread(
            target=self._run_timer,
            args=(self._async_queue, self._interval),
            name=f"EnhancedEventBus-{self._name}-AsyncTimer",
            daemon=True
        )
        self._async_timer.start()
        logger.debug(f"Started async engine for {self._name}")
    
    def _stop_async(self) -> None:
        """停止异步事件处理引擎"""
        if not self._async_active:
            return
        
        self._async_active = False
        
        # 优雅关闭
        if self._async_timer and self._async_timer.is_alive():
            try:
                self._async_timer.join(timeout=2.0)
            except Exception as e:
                logger.error(f"Error stopping async timer: {e}")
        
        if self._async_thread and self._async_thread.is_alive():
            try:
                self._async_queue.put_nowait(Event(EventType.SHUTDOWN))
                self._async_thread.join(timeout=3.0)
            except Exception as e:
                logger.error(f"Error stopping async thread: {e}")
        
        logger.info(f"Async engine stopped for {self._name}")
    
    def _run_sync_loop(self) -> None:
        """同步事件处理主循环"""
        logger.debug(f"Enhanced sync event loop started for {self._name}")
        while self._sync_active:
            try:
                event = self._sync_queue.get(timeout=0.5)
                
                if event.type == EventType.SHUTDOWN:
                    logger.debug("Received shutdown signal in sync engine")
                    break
                
                self._process_sync_event_with_monitoring(event)
                
            except Empty:
                continue
            except Exception as e:
                logger.error(f"Sync loop error: {e}", exc_info=True)
                self._error_count += 1
        
        logger.debug(f"Enhanced sync event loop stopped for {self._name}")
    
    def _run_async_loop(self) -> None:
        """异步事件处理循环"""
        logger.debug(f"Enhanced async event loop started for {self._name}")
        while self._async_active:
            try:
                event = self._async_queue.get(timeout=0.5)
                
                if event.type == EventType.SHUTDOWN:
                    logger.debug("Received shutdown signal in async engine")
                    break
                
                self._process_async_event_with_monitoring(event)
                
            except Empty:
                continue
            except Exception as e:
                logger.error(f"Async loop error: {e}", exc_info=True)
                self._error_count += 1
        
        logger.debug(f"Enhanced async event loop stopped for {self._name}")
    
    def _run_timer(self, queue: PriorityQueue, interval: int) -> None:
        """定时事件生成器"""
        while self._active_flag(queue):
            time.sleep(interval)
            try:
                timer_event = Event(EventType.TIMER, priority=EventPriority.LOW)
                if not queue.put_nowait(timer_event):
                    logger.warning("Timer queue full, dropping timer event")
            except Exception as e:
                logger.error(f"Timer error: {e}")
    
    def _active_flag(self, queue: PriorityQueue) -> bool:
        """根据队列类型返回活动标志"""
        if queue is self._sync_queue:
            return self._sync_active
        return self._async_active
    
    def publish(self, event: Event, is_async: bool = False) -> bool:
        """发布事件，返回是否成功"""
        self._event_count += 1
        
        # 通知监控器
        self._notify_monitors(event)
        
        if is_async:
            return self._put_async_with_backpressure(event)
        else:
            # 同步事件直接处理
            self._process_sync_event_with_monitoring(event)
            return True
    
    def _put_async_with_backpressure(self, event: Event) -> bool:
        """异步放入事件，支持背压机制"""
        queue_stats = self._async_queue.get_stats()
        current_usage = queue_stats.current_size / queue_stats.max_size if queue_stats.max_size > 0 else 0
        
        # 检查是否触发背压
        if current_usage >= self._backpressure_threshold:
            self._backpressure_triggered_count += 1
            return self._handle_backpressure(event, self._async_queue)
        
        return self._async_queue.put_nowait(event)
    
    def _handle_backpressure(self, event: Event, queue: PriorityQueue) -> bool:
        """处理背压情况"""
        logger.warning(f"Backpressure triggered for queue, strategy: {self._backpressure_strategy.value}")
        
        if self._backpressure_strategy == BackpressureStrategy.DROP_LOW_PRIORITY:
            # 如果是低优先级事件，直接丢弃
            if event.priority in [EventPriority.LOW, EventPriority.NORMAL]:
                queue.drop_event()
                logger.debug(f"Dropped low priority event: {event.type}")
                return False
            # 高优先级事件强制入队
            return queue.put_nowait(event)
        
        elif self._backpressure_strategy == BackpressureStrategy.REJECT_NEW:
            queue.drop_event()
            logger.debug(f"Rejected new event due to backpressure: {event.type}")
            return False
        
        # 其他策略暂时按拒绝新事件处理
        queue.drop_event()
        return False
    
    def _process_sync_event_with_monitoring(self, event: Event) -> None:
        """带监控的同步事件处理"""
        start_time = time.time_ns()
        queue_wait_time = start_time - event.timestamp
        success = True
        error_message = None
        
        try:
            self._process_sync_event_with_retry(event)
            self._sync_processed_count += 1
            self._event_type_stats[event.type] += 1
        except Exception as e:
            success = False
            error_message = str(e)
            self._error_count += 1
            logger.error(f"Sync event processing failed: {e}", exc_info=True)
        finally:
            processing_time = time.time_ns() - start_time
            
            # 记录指标
            metrics = EventMetrics(
                event_type=event.type,
                processing_time_ns=processing_time,
                queue_wait_time_ns=queue_wait_time,
                success=success,
                error_message=error_message
            )
            self._event_metrics.append(metrics)
            self._processing_times[event.type].append(processing_time)
    
    def _process_async_event_with_monitoring(self, event: Event) -> None:
        """带监控的异步事件处理"""
        start_time = time.time_ns()
        queue_wait_time = start_time - event.timestamp
        success = True
        error_message = None
        
        try:
            self._process_async_event_with_retry(event)
            self._async_processed_count += 1
            self._event_type_stats[event.type] += 1
        except Exception as e:
            success = False
            error_message = str(e)
            self._error_count += 1
            logger.error(f"Async event processing failed: {e}", exc_info=True)
        finally:
            processing_time = time.time_ns() - start_time
            
            # 记录指标
            metrics = EventMetrics(
                event_type=event.type,
                processing_time_ns=processing_time,
                queue_wait_time_ns=queue_wait_time,
                success=success,
                error_message=error_message
            )
            self._event_metrics.append(metrics)
            self._processing_times[event.type].append(processing_time)
    
    def _process_sync_event_with_retry(self, event: Event) -> None:
        """带重试的同步事件处理"""
        for attempt in range(self._max_retry_attempts):
            try:
                # 特定类型处理器
                self._invoke_handlers(event, self._sync_handlers.get(event.type, []))
                # 全局处理器
                self._invoke_handlers(event, self._global_handlers)
                return  # 成功处理，退出重试循环
            except Exception as e:
                if attempt < self._max_retry_attempts - 1:
                    self._retry_count += 1
                    logger.warning(f"Sync event processing failed (attempt {attempt + 1}), retrying: {e}")
                    time.sleep(self._retry_delay * (2 ** attempt))  # 指数退避
                else:
                    raise e  # 最后一次尝试失败，抛出异常
    
    def _process_async_event_with_retry(self, event: Event) -> None:
        """带重试的异步事件处理"""
        for attempt in range(self._max_retry_attempts):
            try:
                # 特定类型处理器
                self._invoke_handlers(event, self._async_handlers.get(event.type, []))
                return  # 成功处理，退出重试循环
            except Exception as e:
                if attempt < self._max_retry_attempts - 1:
                    self._retry_count += 1
                    logger.warning(f"Async event processing failed (attempt {attempt + 1}), retrying: {e}")
                    time.sleep(self._retry_delay * (2 ** attempt))  # 指数退避
                else:
                    raise e  # 最后一次尝试失败，抛出异常
    
    @staticmethod
    def _invoke_handlers(event: Event, handlers: List[Callable]) -> None:
        """安全调用处理器列表"""
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Handler error for {event.type}: {e}", exc_info=True)
                raise e  # 重新抛出异常以触发重试机制
    
    def _notify_monitors(self, event: Event) -> None:
        """通知所有事件监控器"""
        for monitor in self._monitors:
            try:
                monitor(event)
            except Exception as e:
                logger.error(f"Event monitor error: {e}", exc_info=True)
    
    # 兼容原EventBus的接口
    def subscribe(self, event_type: str, handler: Callable, is_async: bool = False) -> None:
        """订阅事件"""
        if isinstance(event_type, str):
            event_type_str = event_type
        else:
            raise TypeError(f"event_type must be str, got {type(event_type)}")
        
        if not callable(handler):
            raise TypeError(f"handler must be callable, got {type(handler)}")
        
        handler_list = self._async_handlers[event_type_str] if is_async else self._sync_handlers[event_type_str]
        
        if handler not in handler_list:
            handler_list.append(handler)
            logger.debug(f"Subscribed handler for {event_type_str} (async={is_async})")
        else:
            logger.warning(f"Handler already subscribed for {event_type_str} (async={is_async})")
    
    def unsubscribe(self, event_type: str, handler: Callable, is_async: bool = False) -> None:
        """取消订阅事件"""
        if isinstance(event_type, str):
            event_type_str = event_type
        else:
            raise TypeError(f"event_type must be str, got {type(event_type)}")
        
        handler_list = self._async_handlers[event_type_str] if is_async else self._sync_handlers[event_type_str]
        
        if handler in handler_list:
            handler_list.remove(handler)
            logger.debug(f"Unsubscribed handler for {event_type_str} (async={is_async})")
        else:
            logger.warning(f"Handler not found for unsubscription: {event_type_str} (async={is_async})")
    
    def subscribe_global(self, handler: Callable) -> None:
        """订阅所有事件（仅同步）"""
        if handler not in self._global_handlers:
            self._global_handlers.append(handler)
            logger.debug("Subscribed global event handler")
    
    def unsubscribe_global(self, handler: Callable) -> None:
        """取消订阅全局事件处理器（仅同步）"""
        if handler in self._global_handlers:
            self._global_handlers.remove(handler)
            logger.debug("Unsubscribed global event handler")
    
    def add_monitor(self, monitor: Callable) -> None:
        """添加事件监控器"""
        if monitor not in self._monitors:
            self._monitors.append(monitor)
            logger.debug("Added event monitor")
    
    def remove_monitor(self, monitor: Callable) -> None:
        """移除事件监控器"""
        if monitor in self._monitors:
            self._monitors.remove(monitor)
            logger.debug("Removed event monitor")
    
    @property
    def name(self) -> str:
        """获取事件总线名称"""
        return self._name
    
    @property
    def is_running(self) -> bool:
        """检查事件总线是否正在运行"""
        return self._sync_active or self._async_active
    
    def get_stats(self) -> Dict[str, Any]:
        """获取增强的统计信息"""
        sync_queue_stats = self._sync_queue.get_stats()
        async_queue_stats = self._async_queue.get_stats()
        
        # 计算平均处理时间
        avg_processing_times = {}
        for event_type, times in self._processing_times.items():
            if times:
                avg_processing_times[event_type] = sum(times) / len(times) / 1_000_000  # 转换为毫秒
        
        return {
            "name": self._name,
            "total_events_published": self._event_count,
            "sync_events_processed": self._sync_processed_count,
            "async_events_processed": self._async_processed_count,
            "total_events_processed": self._sync_processed_count + self._async_processed_count,
            "error_count": self._error_count,
            "retry_count": self._retry_count,
            "backpressure_triggered_count": self._backpressure_triggered_count,
            "event_type_stats": dict(self._event_type_stats),
            "avg_processing_times_ms": avg_processing_times,
            "handlers": {
                "sync_handlers": {k: len(v) for k, v in self._sync_handlers.items()},
                "async_handlers": {k: len(v) for k, v in self._async_handlers.items()},
                "global_handlers": len(self._global_handlers),
            },
            "monitors": len(self._monitors),
            "queue_stats": {
                "sync": {
                    "current_size": sync_queue_stats.current_size,
                    "max_size": sync_queue_stats.max_size,
                    "total_enqueued": sync_queue_stats.total_enqueued,
                    "total_dequeued": sync_queue_stats.total_dequeued,
                    "total_dropped": sync_queue_stats.total_dropped,
                },
                "async": {
                    "current_size": async_queue_stats.current_size,
                    "max_size": async_queue_stats.max_size,
                    "total_enqueued": async_queue_stats.total_enqueued,
                    "total_dequeued": async_queue_stats.total_dequeued,
                    "total_dropped": async_queue_stats.total_dropped,
                }
            },
            "status": {
                "sync_active": self._sync_active,
                "async_active": self._async_active,
            },
            "config": {
                "backpressure_threshold": self._backpressure_threshold,
                "backpressure_strategy": self._backpressure_strategy.value,
                "max_retry_attempts": self._max_retry_attempts,
                "retry_delay": self._retry_delay,
            }
        }
    
    def get_recent_metrics(self, limit: int = 100) -> List[EventMetrics]:
        """获取最近的事件处理指标"""
        return list(self._event_metrics)[-limit:]
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """获取性能摘要"""
        if not self._event_metrics:
            return {"message": "No metrics available"}
        
        recent_metrics = list(self._event_metrics)[-1000:]  # 最近1000个事件
        
        total_events = len(recent_metrics)
        successful_events = sum(1 for m in recent_metrics if m.success)
        failed_events = total_events - successful_events
        
        processing_times = [m.processing_time_ns for m in recent_metrics]
        queue_wait_times = [m.queue_wait_time_ns for m in recent_metrics]
        
        return {
            "total_recent_events": total_events,
            "success_rate": successful_events / total_events if total_events > 0 else 0,
            "failure_rate": failed_events / total_events if total_events > 0 else 0,
            "avg_processing_time_ms": sum(processing_times) / len(processing_times) / 1_000_000 if processing_times else 0,
            "avg_queue_wait_time_ms": sum(queue_wait_times) / len(queue_wait_times) / 1_000_000 if queue_wait_times else 0,
            "max_processing_time_ms": max(processing_times) / 1_000_000 if processing_times else 0,
            "max_queue_wait_time_ms": max(queue_wait_times) / 1_000_000 if queue_wait_times else 0,
        }
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取事件处理指标（兼容性方法）"""
        return {
            "total_events": self._event_count,
            "processed_events": self._sync_processed_count + self._async_processed_count,
            "error_events": self._error_count,
            "retry_events": self._retry_count,
            "backpressure_events": self._backpressure_triggered_count,
            "success_rate": (self._sync_processed_count + self._async_processed_count) / max(self._event_count, 1),
            "error_rate": self._error_count / max(self._event_count, 1)
        }
    
    # 上下文管理
    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
        if exc_type:
            logger.error(f"EnhancedEventBus context error: {exc_val}", exc_info=True)
        return False


if __name__ == '__main__':
    def test_handler(event: Event):
        print(f"处理事件: {event.type}, 优先级: {event.priority.name}")
        if event.type == "test.error":
            raise Exception("测试异常")
    
    def test_monitor(event: Event):
        print(f"监控事件: {event.type}")
    
    print("=" * 50)
    print("启动增强版事件总线测试...")
    
    # 创建增强版事件总线
    enhanced_bus = EnhancedEventBus(
        name="TestEnhancedBus",
        sync_queue_size=100,
        async_queue_size=100,
        backpressure_threshold=0.8
    )
    
    # 订阅事件
    enhanced_bus.subscribe("test.normal", test_handler)
    enhanced_bus.subscribe("test.high", test_handler)
    enhanced_bus.subscribe("test.critical", test_handler)
    enhanced_bus.subscribe("test.error", test_handler)
    enhanced_bus.add_monitor(test_monitor)
    
    try:
        # 测试不同优先级事件
        print("\n发布不同优先级事件...")
        enhanced_bus.publish(Event("test.normal", priority=EventPriority.NORMAL))
        enhanced_bus.publish(Event("test.high", priority=EventPriority.HIGH))
        enhanced_bus.publish(Event("test.critical", priority=EventPriority.CRITICAL))
        
        # 测试异常处理和重试
        print("\n测试异常处理...")
        enhanced_bus.publish(Event("test.error", priority=EventPriority.HIGH))
        
        time.sleep(2)  # 等待处理完成
        
        # 显示统计信息
        print("\n=== 统计信息 ===")
        stats = enhanced_bus.get_stats()
        print(f"总事件数: {stats['total_events_published']}")
        print(f"处理成功: {stats['sync_events_processed']}")
        print(f"错误数: {stats['error_count']}")
        print(f"重试数: {stats['retry_count']}")
        
        # 显示性能摘要
        print("\n=== 性能摘要 ===")
        perf = enhanced_bus.get_performance_summary()
        print(f"成功率: {perf['success_rate']:.2%}")
        print(f"平均处理时间: {perf['avg_processing_time_ms']:.2f}ms")
        print(f"平均队列等待时间: {perf['avg_queue_wait_time_ms']:.2f}ms")
        
        input("\n按 Enter 键停止测试...")
        
    except KeyboardInterrupt:
        print("\n收到中断信号，正在停止...")
    finally:
        enhanced_bus.stop()
        print("\n测试完成！")