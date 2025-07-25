#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos_v2
@FileName   : async_handler_pool
@Date       : 2025/1/16
@Author     : Donny
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 异步处理器池 - 第二阶段优化核心组件
支持协程处理器的并发执行和生命周期管理
"""

import asyncio
import inspect
import threading
import time
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union

from src.core.event import Event
from src.core.logger import get_logger

logger = get_logger("AsyncHandlerPool")


class HandlerType(Enum):
    """处理器类型枚举"""
    SYNC = "sync"  # 同步处理器
    ASYNC = "async"  # 异步处理器
    HYBRID = "hybrid"  # 混合处理器（支持同步和异步）


class PoolStatus(Enum):
    """处理器池状态枚举"""
    INITIALIZING = "initializing"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class HandlerInfo:
    """处理器信息"""
    handler: Callable
    handler_type: HandlerType
    event_types: List[str]
    priority: int = 0
    max_concurrent: int = 10
    timeout: float = 30.0
    retry_count: int = 3
    created_at: float = field(default_factory=time.time)
    
    # 统计信息
    total_calls: int = 0
    success_calls: int = 0
    error_calls: int = 0
    total_time: float = 0.0
    last_call_time: Optional[float] = None
    last_error: Optional[str] = None


@dataclass
class ExecutionResult:
    """执行结果"""
    success: bool
    result: Any = None
    error: Optional[Exception] = None
    execution_time: float = 0.0
    handler_info: Optional[HandlerInfo] = None


class AsyncHandlerPool:
    """
    异步处理器池
    
    功能特性：
    1. 支持同步和异步处理器混合执行
    2. 协程池管理和生命周期控制
    3. 处理器负载均衡和故障转移
    4. 详细的性能监控和统计
    5. 动态扩缩容和资源管理
    """
    
    def __init__(self,
                 name: str = "AsyncHandlerPool",
                 max_workers: int = 50,
                 max_async_tasks: int = 100,
                 default_timeout: float = 30.0,
                 enable_monitoring: bool = True):
        
        self._name = name
        self._max_workers = max_workers
        self._max_async_tasks = max_async_tasks
        self._default_timeout = default_timeout
        self._enable_monitoring = enable_monitoring
        
        # 处理器注册表
        self._handlers: Dict[str, HandlerInfo] = {}
        self._event_handlers: Dict[str, List[HandlerInfo]] = defaultdict(list)
        self._global_handlers: List[HandlerInfo] = []
        
        # 执行环境
        self._thread_pool: Optional[ThreadPoolExecutor] = None
        self._event_loop: Optional[asyncio.AbstractEventLoop] = None
        self._loop_thread: Optional[threading.Thread] = None
        
        # 状态管理
        self._status = PoolStatus.INITIALIZING
        self._active_tasks: Dict[str, asyncio.Task] = {}
        self._task_semaphore: Optional[asyncio.Semaphore] = None
        
        # 监控和统计
        self._execution_history: deque = deque(maxlen=10000)
        self._performance_metrics: Dict[str, Any] = defaultdict(float)
        self._error_counts: Dict[str, int] = defaultdict(int)
        
        # 启动处理器池
        self._initialize()
    
    def _initialize(self) -> None:
        """初始化处理器池"""
        try:
            # 创建线程池
            self._thread_pool = ThreadPoolExecutor(
                max_workers=self._max_workers,
                thread_name_prefix=f"{self._name}-ThreadPool"
            )
            
            # 启动事件循环线程
            self._start_event_loop()
            
            self._status = PoolStatus.RUNNING
            logger.info(f"AsyncHandlerPool '{self._name}' initialized successfully")
            
        except Exception as e:
            self._status = PoolStatus.ERROR
            logger.error(f"Failed to initialize AsyncHandlerPool '{self._name}': {e}", exc_info=True)
            raise
    
    def _start_event_loop(self) -> None:
        """启动异步事件循环线程"""
        def run_loop():
            try:
                # 创建新的事件循环
                self._event_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self._event_loop)
                
                # 创建任务信号量
                self._task_semaphore = asyncio.Semaphore(self._max_async_tasks)
                
                logger.debug(f"Event loop started for {self._name}")
                self._event_loop.run_forever()
                
            except Exception as e:
                logger.error(f"Event loop error in {self._name}: {e}", exc_info=True)
                self._status = PoolStatus.ERROR
        
        self._loop_thread = threading.Thread(
            target=run_loop,
            name=f"{self._name}-EventLoop",
            daemon=True
        )
        self._loop_thread.start()
        
        # 等待事件循环启动
        timeout = 5.0
        start_time = time.time()
        while self._event_loop is None and time.time() - start_time < timeout:
            time.sleep(0.01)
        
        if self._event_loop is None:
            raise RuntimeError(f"Failed to start event loop for {self._name}")
    
    def register_handler(self,
                        handler: Callable,
                        event_types: Union[str, List[str]] = None,
                        priority: int = 0,
                        max_concurrent: int = 10,
                        timeout: float = None,
                        retry_count: int = 3) -> str:
        """
        注册事件处理器
        
        Args:
            handler: 处理器函数（同步或异步）
            event_types: 处理的事件类型列表
            priority: 处理器优先级（数字越大优先级越高）
            max_concurrent: 最大并发执行数
            timeout: 执行超时时间
            retry_count: 重试次数
            
        Returns:
            处理器ID
        """
        if timeout is None:
            timeout = self._default_timeout
        
        # 检测处理器类型
        handler_type = self._detect_handler_type(handler)
        
        # 标准化事件类型
        if event_types is None:
            event_types = []
        elif isinstance(event_types, str):
            event_types = [event_types]
        
        # 生成处理器ID
        handler_id = f"{handler.__name__}_{id(handler)}"
        
        # 创建处理器信息
        handler_info = HandlerInfo(
            handler=handler,
            handler_type=handler_type,
            event_types=event_types,
            priority=priority,
            max_concurrent=max_concurrent,
            timeout=timeout,
            retry_count=retry_count
        )
        
        # 注册处理器
        self._handlers[handler_id] = handler_info
        
        # 注册到事件类型映射
        if event_types:
            for event_type in event_types:
                self._event_handlers[event_type].append(handler_info)
                # 按优先级排序
                self._event_handlers[event_type].sort(key=lambda h: h.priority, reverse=True)
        else:
            # 全局处理器
            self._global_handlers.append(handler_info)
            self._global_handlers.sort(key=lambda h: h.priority, reverse=True)
        
        logger.debug(f"Registered {handler_type.value} handler '{handler_id}' for events: {event_types}")
        return handler_id
    
    def unregister_handler(self, handler_id: str) -> bool:
        """
        取消注册处理器
        
        Args:
            handler_id: 处理器ID
            
        Returns:
            是否成功取消注册
        """
        if handler_id not in self._handlers:
            return False
        
        handler_info = self._handlers[handler_id]
        
        # 从事件类型映射中移除
        for event_type in handler_info.event_types:
            if event_type in self._event_handlers:
                self._event_handlers[event_type] = [
                    h for h in self._event_handlers[event_type] if h != handler_info
                ]
        
        # 从全局处理器中移除
        if handler_info in self._global_handlers:
            self._global_handlers.remove(handler_info)
        
        # 从注册表中移除
        del self._handlers[handler_id]
        
        logger.debug(f"Unregistered handler '{handler_id}'")
        return True
    
    def _detect_handler_type(self, handler: Callable) -> HandlerType:
        """检测处理器类型"""
        if inspect.iscoroutinefunction(handler):
            return HandlerType.ASYNC
        elif callable(handler):
            return HandlerType.SYNC
        else:
            raise TypeError(f"Invalid handler type: {type(handler)}")
    
    async def execute_async(self, event: Event) -> List[ExecutionResult]:
        """
        异步执行事件处理
        
        Args:
            event: 要处理的事件
            
        Returns:
            执行结果列表
        """
        if self._status != PoolStatus.RUNNING:
            raise RuntimeError(f"Handler pool is not running: {self._status}")
        
        # 获取相关处理器
        handlers = self._get_handlers_for_event(event)
        
        if not handlers:
            logger.debug(f"No handlers found for event type: {event.type}")
            return []
        
        # 并发执行所有处理器
        tasks = []
        for handler_info in handlers:
            task = self._create_execution_task(event, handler_info)
            tasks.append(task)
        
        # 等待所有任务完成
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理结果
        execution_results = []
        for i, result in enumerate(results):
            if isinstance(result, ExecutionResult):
                execution_results.append(result)
            else:
                # 异常情况
                execution_results.append(ExecutionResult(
                    success=False,
                    error=result if isinstance(result, Exception) else Exception(str(result)),
                    handler_info=handlers[i]
                ))
        
        return execution_results
    
    def execute_sync(self, event: Event) -> List[ExecutionResult]:
        """
        同步执行事件处理（阻塞调用）
        
        Args:
            event: 要处理的事件
            
        Returns:
            执行结果列表
        """
        if self._event_loop is None:
            raise RuntimeError("Event loop is not running")
        
        # 在事件循环中执行异步方法
        future = asyncio.run_coroutine_threadsafe(
            self.execute_async(event),
            self._event_loop
        )
        
        try:
            return future.result(timeout=self._default_timeout)
        except asyncio.TimeoutError:
            logger.error(f"Sync execution timeout for event: {event.type}")
            return [ExecutionResult(
                success=False,
                error=asyncio.TimeoutError("Execution timeout")
            )]
    
    def _get_handlers_for_event(self, event: Event) -> List[HandlerInfo]:
        """获取事件的相关处理器"""
        handlers = []
        
        # 特定事件类型的处理器
        if event.type in self._event_handlers:
            handlers.extend(self._event_handlers[event.type])
        
        # 全局处理器
        handlers.extend(self._global_handlers)
        
        # 按优先级排序
        handlers.sort(key=lambda h: h.priority, reverse=True)
        
        return handlers
    
    async def _create_execution_task(self, event: Event, handler_info: HandlerInfo) -> ExecutionResult:
        """创建执行任务"""
        async with self._task_semaphore:
            if handler_info.handler_type == HandlerType.ASYNC:
                return await self._execute_async_handler(event, handler_info)
            else:
                return await self._execute_sync_handler(event, handler_info)
    
    async def _execute_async_handler(self, event: Event, handler_info: HandlerInfo) -> ExecutionResult:
        """执行异步处理器"""
        start_time = time.time()
        
        try:
            # 执行异步处理器
            result = await asyncio.wait_for(
                handler_info.handler(event),
                timeout=handler_info.timeout
            )
            
            execution_time = time.time() - start_time
            
            # 更新统计信息
            self._update_handler_stats(handler_info, True, execution_time)
            
            return ExecutionResult(
                success=True,
                result=result,
                execution_time=execution_time,
                handler_info=handler_info
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            
            # 更新统计信息
            self._update_handler_stats(handler_info, False, execution_time, str(e))
            
            logger.error(f"Async handler error: {e}", exc_info=True)
            
            return ExecutionResult(
                success=False,
                error=e,
                execution_time=execution_time,
                handler_info=handler_info
            )
    
    async def _execute_sync_handler(self, event: Event, handler_info: HandlerInfo) -> ExecutionResult:
        """执行同步处理器"""
        start_time = time.time()
        
        try:
            # 在线程池中执行同步处理器
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self._thread_pool,
                handler_info.handler,
                event
            )
            
            execution_time = time.time() - start_time
            
            # 更新统计信息
            self._update_handler_stats(handler_info, True, execution_time)
            
            return ExecutionResult(
                success=True,
                result=result,
                execution_time=execution_time,
                handler_info=handler_info
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            
            # 更新统计信息
            self._update_handler_stats(handler_info, False, execution_time, str(e))
            
            logger.error(f"Sync handler error: {e}", exc_info=True)
            
            return ExecutionResult(
                success=False,
                error=e,
                execution_time=execution_time,
                handler_info=handler_info
            )
    
    def _update_handler_stats(self, handler_info: HandlerInfo, success: bool, 
                             execution_time: float, error_msg: str = None) -> None:
        """更新处理器统计信息"""
        handler_info.total_calls += 1
        handler_info.total_time += execution_time
        handler_info.last_call_time = time.time()
        
        if success:
            handler_info.success_calls += 1
        else:
            handler_info.error_calls += 1
            handler_info.last_error = error_msg
        
        # 记录执行历史
        if self._enable_monitoring:
            self._execution_history.append({
                'timestamp': time.time(),
                'handler_id': f"{handler_info.handler.__name__}_{id(handler_info.handler)}",
                'success': success,
                'execution_time': execution_time,
                'error': error_msg
            })
    
    def get_stats(self) -> Dict[str, Any]:
        """获取处理器池统计信息"""
        total_handlers = len(self._handlers)
        active_tasks = len(self._active_tasks)
        
        # 计算处理器统计
        handler_stats = {}
        for handler_id, handler_info in self._handlers.items():
            avg_time = (handler_info.total_time / handler_info.total_calls 
                       if handler_info.total_calls > 0 else 0)
            
            handler_stats[handler_id] = {
                'type': handler_info.handler_type.value,
                'event_types': handler_info.event_types,
                'total_calls': handler_info.total_calls,
                'success_calls': handler_info.success_calls,
                'error_calls': handler_info.error_calls,
                'success_rate': (handler_info.success_calls / handler_info.total_calls 
                               if handler_info.total_calls > 0 else 0),
                'avg_execution_time': avg_time,
                'last_call_time': handler_info.last_call_time,
                'last_error': handler_info.last_error
            }
        
        return {
            'name': self._name,
            'status': self._status.value,
            'total_handlers': total_handlers,
            'active_tasks': active_tasks,
            'max_workers': self._max_workers,
            'max_async_tasks': self._max_async_tasks,
            'execution_history_size': len(self._execution_history),
            'handler_stats': handler_stats,
            'thread_pool_active': self._thread_pool is not None,
            'event_loop_running': (self._event_loop is not None and 
                                 not self._event_loop.is_closed())
        }
    
    def shutdown(self, timeout: float = 30.0) -> None:
        """关闭处理器池"""
        logger.info(f"Shutting down AsyncHandlerPool '{self._name}'...")
        
        self._status = PoolStatus.STOPPING
        
        try:
            # 关闭线程池
            if self._thread_pool:
                self._thread_pool.shutdown(wait=True)
                self._thread_pool = None
            
            # 关闭事件循环
            if self._event_loop and not self._event_loop.is_closed():
                # 取消所有活动任务
                for task in self._active_tasks.values():
                    task.cancel()
                
                # 停止事件循环
                self._event_loop.call_soon_threadsafe(self._event_loop.stop)
                
                # 等待循环线程结束
                if self._loop_thread and self._loop_thread.is_alive():
                    self._loop_thread.join(timeout=timeout)
            
            self._status = PoolStatus.STOPPED
            logger.info(f"AsyncHandlerPool '{self._name}' shutdown completed")
            
        except Exception as e:
            self._status = PoolStatus.ERROR
            logger.error(f"Error during shutdown: {e}", exc_info=True)
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.shutdown()
        return False


# 装饰器支持
def async_handler(event_types: Union[str, List[str]] = None,
                 priority: int = 0,
                 max_concurrent: int = 10,
                 timeout: float = 30.0,
                 retry_count: int = 3):
    """
    异步处理器装饰器
    
    Args:
        event_types: 处理的事件类型
        priority: 处理器优先级
        max_concurrent: 最大并发数
        timeout: 超时时间
        retry_count: 重试次数
    """
    def decorator(func):
        func._async_handler_config = {
            'event_types': event_types,
            'priority': priority,
            'max_concurrent': max_concurrent,
            'timeout': timeout,
            'retry_count': retry_count
        }
        return func
    return decorator


def sync_handler(event_types: Union[str, List[str]] = None,
                priority: int = 0,
                max_concurrent: int = 10,
                timeout: float = 30.0,
                retry_count: int = 3):
    """
    同步处理器装饰器
    
    Args:
        event_types: 处理的事件类型
        priority: 处理器优先级
        max_concurrent: 最大并发数
        timeout: 超时时间
        retry_count: 重试次数
    """
    def decorator(func):
        func._sync_handler_config = {
            'event_types': event_types,
            'priority': priority,
            'max_concurrent': max_concurrent,
            'timeout': timeout,
            'retry_count': retry_count
        }
        return func
    return decorator