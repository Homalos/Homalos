#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos_v2
@FileName   : event_scheduler
@Date       : 2025/1/16
@Author     : Donny
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 智能事件调度器 - 第二阶段优化核心组件
负责事件的智能分发和执行策略选择
"""

import asyncio
import heapq
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Callable

from src.core.async_handler_pool import AsyncHandlerPool, ExecutionResult
from src.core.event import Event
from src.core.logger import get_logger

logger = get_logger("EventScheduler")


class SchedulingStrategy(Enum):
    """调度策略枚举"""
    FIFO = "fifo"  # 先进先出
    PRIORITY = "priority"  # 优先级调度
    LOAD_BALANCED = "load_balanced"  # 负载均衡
    ADAPTIVE = "adaptive"  # 自适应调度


class ExecutionMode(Enum):
    """执行模式枚举"""
    SYNC_ONLY = "sync_only"  # 仅同步执行
    ASYNC_ONLY = "async_only"  # 仅异步执行
    HYBRID = "hybrid"  # 混合执行
    AUTO = "auto"  # 自动选择


@dataclass
class ScheduledEvent:
    """调度事件"""
    event: Event
    priority: int
    scheduled_time: float
    execution_mode: ExecutionMode
    retry_count: int = 0
    max_retries: int = 3
    timeout: float = 30.0
    callback: Optional[Callable] = None
    
    def __lt__(self, other):
        """用于优先级队列排序"""
        if self.priority != other.priority:
            return self.priority > other.priority  # 高优先级先执行
        return self.scheduled_time < other.scheduled_time  # 时间早的先执行


@dataclass
class SchedulerMetrics:
    """调度器指标"""
    total_scheduled: int = 0
    total_executed: int = 0
    total_failed: int = 0
    total_retried: int = 0
    avg_scheduling_delay: float = 0.0
    avg_execution_time: float = 0.0
    current_queue_size: int = 0
    peak_queue_size: int = 0
    
    # 按执行模式统计
    sync_executed: int = 0
    async_executed: int = 0
    hybrid_executed: int = 0
    
    # 按事件类型统计
    event_type_stats: Dict[str, int] = field(default_factory=lambda: defaultdict(int))


class EventScheduler:
    """
    智能事件调度器
    
    功能特性：
    1. 多种调度策略支持
    2. 智能执行模式选择
    3. 负载感知和自适应调度
    4. 事件重试和故障处理
    5. 详细的性能监控
    """
    
    def __init__(self,
                 name: str = "EventScheduler",
                 strategy: SchedulingStrategy = SchedulingStrategy.ADAPTIVE,
                 execution_mode: ExecutionMode = ExecutionMode.AUTO,
                 max_queue_size: int = 10000,
                 batch_size: int = 10,
                 scheduling_interval: float = 0.01,
                 enable_metrics: bool = True):
        
        self._name = name
        self._strategy = strategy
        self._execution_mode = execution_mode
        self._max_queue_size = max_queue_size
        self._batch_size = batch_size
        self._scheduling_interval = scheduling_interval
        self._enable_metrics = enable_metrics
        
        # 事件队列
        self._event_queue: List[ScheduledEvent] = []
        self._queue_lock = threading.Lock()
        
        # 处理器池
        self._handler_pool: Optional[AsyncHandlerPool] = None
        
        # 调度控制
        self._running = False
        self._scheduler_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        # 监控和统计
        self._metrics = SchedulerMetrics()
        self._execution_history: deque = deque(maxlen=10000)
        self._load_stats: Dict[str, float] = defaultdict(float)
        
        # 自适应调度参数
        self._load_threshold = 0.8
        self._performance_window = 1000  # 性能统计窗口大小
        self._last_performance_check = time.time()
    
    def set_handler_pool(self, handler_pool: AsyncHandlerPool) -> None:
        """设置处理器池"""
        self._handler_pool = handler_pool
        logger.debug(f"Handler pool set for scheduler '{self._name}'")
    
    def start(self) -> None:
        """启动调度器"""
        if self._running:
            logger.warning(f"Scheduler '{self._name}' is already running")
            return
        
        if self._handler_pool is None:
            raise RuntimeError("Handler pool must be set before starting scheduler")
        
        self._running = True
        self._stop_event.clear()
        
        # 启动调度线程
        self._scheduler_thread = threading.Thread(
            target=self._scheduling_loop,
            name=f"{self._name}-Scheduler",
            daemon=True
        )
        self._scheduler_thread.start()
        
        logger.info(f"EventScheduler '{self._name}' started")
    
    def stop(self, timeout: float = 30.0) -> None:
        """停止调度器"""
        if not self._running:
            return
        
        logger.info(f"Stopping EventScheduler '{self._name}'...")
        
        self._running = False
        self._stop_event.set()
        
        # 等待调度线程结束
        if self._scheduler_thread and self._scheduler_thread.is_alive():
            self._scheduler_thread.join(timeout=timeout)
            
            if self._scheduler_thread.is_alive():
                logger.warning(f"Scheduler thread did not stop within timeout")
        
        logger.info(f"EventScheduler '{self._name}' stopped")
    
    def schedule_event(self,
                      event: Event,
                      priority: Optional[int] = None,
                      execution_mode: Optional[ExecutionMode] = None,
                      delay: float = 0.0,
                      timeout: float = 30.0,
                      max_retries: int = 3,
                      callback: Optional[Callable] = None) -> bool:
        """
        调度事件
        
        Args:
            event: 要调度的事件
            priority: 事件优先级（覆盖事件自身优先级）
            execution_mode: 执行模式（覆盖默认模式）
            delay: 延迟执行时间（秒）
            timeout: 执行超时时间
            max_retries: 最大重试次数
            callback: 执行完成回调
            
        Returns:
            是否成功调度
        """
        if not self._running:
            logger.warning("Scheduler is not running, cannot schedule event")
            return False
        
        # 检查队列容量
        with self._queue_lock:
            if len(self._event_queue) >= self._max_queue_size:
                logger.warning(f"Event queue is full, dropping event: {event.type}")
                return False
        
        # 确定优先级
        if priority is None:
            priority = event.priority.value if hasattr(event, 'priority') else 0
        
        # 确定执行模式
        if execution_mode is None:
            execution_mode = self._determine_execution_mode(event)
        
        # 创建调度事件
        scheduled_event = ScheduledEvent(
            event=event,
            priority=priority,
            scheduled_time=time.time() + delay,
            execution_mode=execution_mode,
            max_retries=max_retries,
            timeout=timeout,
            callback=callback
        )
        
        # 添加到队列
        with self._queue_lock:
            heapq.heappush(self._event_queue, scheduled_event)
            self._metrics.total_scheduled += 1
            self._metrics.current_queue_size = len(self._event_queue)
            
            # 更新峰值队列大小
            if self._metrics.current_queue_size > self._metrics.peak_queue_size:
                self._metrics.peak_queue_size = self._metrics.current_queue_size
        
        logger.debug(f"Scheduled event: {event.type} with priority {priority}")
        return True
    
    def _determine_execution_mode(self, event: Event) -> ExecutionMode:
        """确定事件执行模式"""
        if self._execution_mode != ExecutionMode.AUTO:
            return self._execution_mode
        
        # 自动选择执行模式
        if self._strategy == SchedulingStrategy.ADAPTIVE:
            return self._adaptive_execution_mode(event)
        
        # 默认混合模式
        return ExecutionMode.HYBRID
    
    def _adaptive_execution_mode(self, event: Event) -> ExecutionMode:
        """自适应执行模式选择"""
        # 获取当前系统负载
        current_load = self._get_current_load()
        
        # 高负载时优先使用异步模式
        if current_load > self._load_threshold:
            return ExecutionMode.ASYNC_ONLY
        
        # 根据事件类型历史性能选择
        event_type = event.type
        if event_type in self._load_stats:
            avg_time = self._load_stats[event_type]
            # 长时间运行的事件使用异步模式
            if avg_time > 1.0:  # 超过1秒
                return ExecutionMode.ASYNC_ONLY
        
        # 默认混合模式
        return ExecutionMode.HYBRID
    
    def _get_current_load(self) -> float:
        """获取当前系统负载"""
        if self._handler_pool is None:
            return 0.0
        
        stats = self._handler_pool.get_stats()
        active_tasks = stats.get('active_tasks', 0)
        max_tasks = stats.get('max_async_tasks', 1)
        
        return active_tasks / max_tasks
    
    def _scheduling_loop(self) -> None:
        """调度主循环"""
        logger.debug(f"Scheduling loop started for '{self._name}'")
        
        while self._running and not self._stop_event.is_set():
            try:
                # 批量处理事件
                events_to_process = self._get_ready_events()
                
                if events_to_process:
                    self._process_events_batch(events_to_process)
                
                # 更新性能统计
                self._update_performance_stats()
                
                # 等待下一个调度周期
                self._stop_event.wait(self._scheduling_interval)
                
            except Exception as e:
                logger.error(f"Error in scheduling loop: {e}", exc_info=True)
                time.sleep(0.1)  # 避免错误循环
        
        logger.debug(f"Scheduling loop stopped for '{self._name}'")
    
    def _get_ready_events(self) -> List[ScheduledEvent]:
        """获取准备执行的事件"""
        ready_events = []
        current_time = time.time()
        
        with self._queue_lock:
            # 获取批量事件
            while (len(ready_events) < self._batch_size and 
                   self._event_queue and 
                   self._event_queue[0].scheduled_time <= current_time):
                
                event = heapq.heappop(self._event_queue)
                ready_events.append(event)
            
            # 更新队列大小
            self._metrics.current_queue_size = len(self._event_queue)
        
        return ready_events
    
    def _process_events_batch(self, events: List[ScheduledEvent]) -> None:
        """批量处理事件"""
        for scheduled_event in events:
            try:
                self._execute_scheduled_event(scheduled_event)
            except Exception as e:
                logger.error(f"Error processing event {scheduled_event.event.type}: {e}", exc_info=True)
                self._handle_execution_failure(scheduled_event, e)
    
    def _execute_scheduled_event(self, scheduled_event: ScheduledEvent) -> None:
        """执行调度事件"""
        start_time = time.time()
        
        try:
            # 根据执行模式选择执行方式
            if scheduled_event.execution_mode == ExecutionMode.SYNC_ONLY:
                results = self._handler_pool.execute_sync(scheduled_event.event)
            elif scheduled_event.execution_mode == ExecutionMode.ASYNC_ONLY:
                # 异步执行（非阻塞）
                self._execute_async_non_blocking(scheduled_event)
                return
            else:
                # 混合模式或自动模式
                results = self._handler_pool.execute_sync(scheduled_event.event)
            
            execution_time = time.time() - start_time
            
            # 处理执行结果
            self._handle_execution_results(scheduled_event, results, execution_time)
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Event execution error: {e}", exc_info=True)
            self._handle_execution_failure(scheduled_event, e, execution_time)
    
    def _execute_async_non_blocking(self, scheduled_event: ScheduledEvent) -> None:
        """非阻塞异步执行"""
        if self._handler_pool._event_loop is None:
            raise RuntimeError("Event loop is not available")
        
        # 在事件循环中创建任务
        future = asyncio.run_coroutine_threadsafe(
            self._async_execute_with_callback(scheduled_event),
            self._handler_pool._event_loop
        )
        
        # 不等待结果，让它异步执行
        logger.debug(f"Started async execution for event: {scheduled_event.event.type}")
    
    async def _async_execute_with_callback(self, scheduled_event: ScheduledEvent) -> None:
        """带回调的异步执行"""
        start_time = time.time()
        
        try:
            results = await self._handler_pool.execute_async(scheduled_event.event)
            execution_time = time.time() - start_time
            
            # 处理执行结果
            self._handle_execution_results(scheduled_event, results, execution_time)
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Async event execution error: {e}", exc_info=True)
            self._handle_execution_failure(scheduled_event, e, execution_time)
    
    def _handle_execution_results(self, scheduled_event: ScheduledEvent, 
                                 results: List[ExecutionResult], execution_time: float) -> None:
        """处理执行结果"""
        success_count = sum(1 for r in results if r.success)
        total_count = len(results)
        
        # 更新统计
        self._metrics.total_executed += 1
        if success_count == total_count:
            # 全部成功
            self._update_execution_stats(scheduled_event, True, execution_time)
        else:
            # 部分或全部失败
            self._metrics.total_failed += 1
            self._update_execution_stats(scheduled_event, False, execution_time)
        
        # 调用回调
        if scheduled_event.callback:
            try:
                scheduled_event.callback(scheduled_event.event, results)
            except Exception as e:
                logger.error(f"Callback error: {e}", exc_info=True)
        
        logger.debug(f"Event execution completed: {scheduled_event.event.type}, "
                    f"success: {success_count}/{total_count}, time: {execution_time:.3f}s")
    
    def _handle_execution_failure(self, scheduled_event: ScheduledEvent, 
                                 error: Exception, execution_time: float = 0.0) -> None:
        """处理执行失败"""
        self._metrics.total_failed += 1
        self._update_execution_stats(scheduled_event, False, execution_time)
        
        # 检查是否需要重试
        if scheduled_event.retry_count < scheduled_event.max_retries:
            scheduled_event.retry_count += 1
            scheduled_event.scheduled_time = time.time() + (2 ** scheduled_event.retry_count)  # 指数退避
            
            # 重新调度
            with self._queue_lock:
                heapq.heappush(self._event_queue, scheduled_event)
                self._metrics.current_queue_size = len(self._event_queue)
            
            self._metrics.total_retried += 1
            logger.warning(f"Retrying event {scheduled_event.event.type} "
                          f"(attempt {scheduled_event.retry_count}/{scheduled_event.max_retries})")
        else:
            logger.error(f"Event {scheduled_event.event.type} failed after {scheduled_event.max_retries} retries")
            
            # 调用回调通知失败
            if scheduled_event.callback:
                try:
                    scheduled_event.callback(scheduled_event.event, [ExecutionResult(
                        success=False,
                        error=error,
                        execution_time=execution_time
                    )])
                except Exception as e:
                    logger.error(f"Failure callback error: {e}", exc_info=True)
    
    def _update_execution_stats(self, scheduled_event: ScheduledEvent, 
                               success: bool, execution_time: float) -> None:
        """更新执行统计"""
        event_type = scheduled_event.event.type
        
        # 更新事件类型统计
        self._metrics.event_type_stats[event_type] += 1
        
        # 更新执行模式统计
        if scheduled_event.execution_mode == ExecutionMode.SYNC_ONLY:
            self._metrics.sync_executed += 1
        elif scheduled_event.execution_mode == ExecutionMode.ASYNC_ONLY:
            self._metrics.async_executed += 1
        else:
            self._metrics.hybrid_executed += 1
        
        # 更新负载统计（用于自适应调度）
        if event_type in self._load_stats:
            # 指数移动平均
            self._load_stats[event_type] = (self._load_stats[event_type] * 0.9 + 
                                           execution_time * 0.1)
        else:
            self._load_stats[event_type] = execution_time
        
        # 记录执行历史
        if self._enable_metrics:
            self._execution_history.append({
                'timestamp': time.time(),
                'event_type': event_type,
                'execution_mode': scheduled_event.execution_mode.value,
                'success': success,
                'execution_time': execution_time,
                'retry_count': scheduled_event.retry_count
            })
    
    def _update_performance_stats(self) -> None:
        """更新性能统计"""
        current_time = time.time()
        
        # 每秒更新一次
        if current_time - self._last_performance_check < 1.0:
            return
        
        self._last_performance_check = current_time
        
        # 计算平均执行时间
        if self._execution_history:
            recent_executions = [h for h in self._execution_history 
                               if current_time - h['timestamp'] < 60]  # 最近1分钟
            
            if recent_executions:
                total_time = sum(h['execution_time'] for h in recent_executions)
                self._metrics.avg_execution_time = total_time / len(recent_executions)
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取调度器指标"""
        with self._queue_lock:
            current_queue_size = len(self._event_queue)
        
        return {
            'name': self._name,
            'strategy': self._strategy.value,
            'execution_mode': self._execution_mode.value,
            'running': self._running,
            'current_queue_size': current_queue_size,
            'max_queue_size': self._max_queue_size,
            'total_scheduled': self._metrics.total_scheduled,
            'total_executed': self._metrics.total_executed,
            'total_failed': self._metrics.total_failed,
            'total_retried': self._metrics.total_retried,
            'success_rate': (self._metrics.total_executed / 
                           max(self._metrics.total_scheduled, 1)),
            'avg_execution_time': self._metrics.avg_execution_time,
            'peak_queue_size': self._metrics.peak_queue_size,
            'execution_mode_stats': {
                'sync': self._metrics.sync_executed,
                'async': self._metrics.async_executed,
                'hybrid': self._metrics.hybrid_executed
            },
            'event_type_stats': dict(self._metrics.event_type_stats),
            'load_stats': dict(self._load_stats)
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """获取调度器统计信息（get_metrics的别名）"""
        return self.get_metrics()
    
    def get_queue_status(self) -> Dict[str, Any]:
        """获取队列状态"""
        with self._queue_lock:
            queue_size = len(self._event_queue)
            
            # 获取队列中的事件类型分布
            event_types = defaultdict(int)
            priorities = defaultdict(int)
            
            for scheduled_event in self._event_queue:
                event_types[scheduled_event.event.type] += 1
                priorities[scheduled_event.priority] += 1
        
        return {
            'current_size': queue_size,
            'max_size': self._max_queue_size,
            'usage_percentage': (queue_size / self._max_queue_size) * 100,
            'event_types': dict(event_types),
            'priorities': dict(priorities)
        }
    
    def clear_queue(self) -> int:
        """清空队列"""
        with self._queue_lock:
            cleared_count = len(self._event_queue)
            self._event_queue.clear()
            self._metrics.current_queue_size = 0
        
        logger.info(f"Cleared {cleared_count} events from queue")
        return cleared_count
    
    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
        return False