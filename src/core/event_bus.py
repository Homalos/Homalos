#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos_v2
@FileName   : event_bus
@Date       : 2025/7/5 18:11
@Author     : Donny
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 高性能事件总线
"""
import time
from collections import defaultdict
from queue import Queue, Empty, Full
from threading import Thread
from typing import Any, Dict, List, Callable, Optional

from src.core.event import Event
from src.core.event_type import EventType
from src.core.logger import get_logger

logger = get_logger("EventBus")


class EventBus:
    """
    事件总线
    - 支持同步/异步双通道事件处理
    - 内置定时事件生成器
    - 完善的线程管理和资源清理
    - 细粒度监控和统计
    """

    # 默认配置参数
    DEFAULT_SYNC_QUEUE_SIZE = 1000
    DEFAULT_ASYNC_QUEUE_SIZE = 10000
    DEFAULT_TIMER_INTERVAL = 1

    def __init__(self,
                 name: str = "default",
                 max_async_queue_size: int = DEFAULT_ASYNC_QUEUE_SIZE,
                 interval: int = DEFAULT_TIMER_INTERVAL):
        # 系统标识
        self._name = name
        self._interval: int = interval

        # 事件队列
        self._sync_queue = Queue(maxsize=self.DEFAULT_SYNC_QUEUE_SIZE)  # 同步处理队列
        self._async_queue = Queue(maxsize=max_async_queue_size)  # 异步处理队列

        # 事件处理器注册表
        self._sync_handlers: Dict[str, List[Callable]] = defaultdict(list)  # 同步处理器
        self._async_handlers: Dict[str, List[Callable]] = defaultdict(list)  # 异步处理器
        self._global_handlers: List[Callable] = []  # 全局处理器(同步)

        # 事件监控
        self._monitors: List[Callable] = []
        self._event_count = 0

        # 线程控制标志
        self._sync_active: bool = False
        self._async_active: bool = False

        # 线程实例
        self._sync_thread: Optional[Thread] = None
        self._async_thread: Optional[Thread] = None
        self._sync_timer: Optional[Thread] = None
        self._async_timer: Optional[Thread] = None

        # 启动事件处理引擎
        self.start_engines()

    def start_engines(self) -> None:
        """启动所有事件处理引擎"""
        self._start_sync_engine()
        self._start_async_engine()
        logger.info(f"EventBus '{self._name}' engines started")

    def stop_engines(self) -> None:
        """停止所有事件处理引擎"""
        self.stop_sync_engine()
        self.stop_async_engine()
        logger.info(f"EventBus '{self._name}' engines stopped")

    def _start_sync_engine(self) -> None:
        """启动同步事件处理引擎"""
        if self._sync_active:
            return

        self._sync_active = True
        # 启动事件处理线程
        self._sync_thread = Thread(
            target=self._run_sync_loop,
            name=f"EventBus-{self._name}-SyncThread",
            daemon=True
        )
        self._sync_thread.start()
        logger.debug(f"Started sync event engine for {self._name}")

        # 启动定时器线程
        self._sync_timer = Thread(
            target=self._run_timer,
            args=(self._sync_queue, self._interval),
            name=f"EventBus-{self._name}-SyncTimer",
            daemon=True
        )
        self._sync_timer.start()
        logger.debug(f"Started sync Timer for {self._name}")

    def stop_sync_engine(self) -> None:
        """停止同步事件处理引擎"""
        if not self._sync_active:
            return

        self._sync_active = False
        # 优雅关闭线程
        if self._sync_timer and self._sync_timer.is_alive():
            self._sync_timer.join(timeout=2.0)

        if self._sync_thread and self._sync_thread.is_alive():
            # 发送停止信号
            self._sync_queue.put(Event(EventType.SHUTDOWN.value))
            self._sync_thread.join(timeout=3.0)
        logger.info(f"Sync engine stopped for {self._name}")

    def _run_sync_loop(self) -> None:
        """同步事件处理主循环"""
        while self._sync_active:
            try:
                event: Event = self._sync_queue.get(block=True, timeout=0.5)

                # 检查关闭信号
                if event.type == EventType.SHUTDOWN.value:
                    logger.debug("Received shutdown signal in sync engine")
                    break

                self._process_sync_event(event)
            except Empty:
                pass
            except Exception as e:
                logger.error(f"Sync event processing error: {e}", exc_info=True)

    def _start_async_engine(self) -> None:
        """启动异步事件处理引擎"""
        if self._async_active:
            return

        self._async_active = True

        # 启动事件处理线程
        self._async_thread = Thread(
            target=self._run_async_loop,
            name=f"EventBus-{self._name}-AsyncThread",
            daemon=True
        )
        self._async_thread.start()

        logger.debug(f"Started async event engine for {self._name}")

        # 启动定时器线程
        self._async_timer = Thread(
            target=self._run_timer,
            args=(self._async_queue, self._interval),
            name=f"EventBus-{self._name}-AsyncTimer",
            daemon=True
        )
        self._async_timer.start()
        logger.debug(f"Async engine started for {self._name}")

    def stop_async_engine(self) -> None:
        """停止异步事件处理引擎"""
        if not self._sync_active: return

        self._async_active = False

        # 发送关闭信号
        self._async_queue.put(Event(EventType.SHUTDOWN.value))

        # 等待线程终止
        self._async_timer.join(timeout=2.0)
        self._async_thread.join(timeout=3.0)
        logger.debug(f"Async engine stopped for {self._name}")

    def _run_async_loop(self) -> None:
        """异步事件处理循环"""
        while self._async_active:
            try:
                event = self._async_queue.get(timeout=0.5)

                # 检查关闭信号
                if event.type == EventType.SHUTDOWN.value:
                    logger.debug("Received shutdown signal in async engine")
                    break

                self._process_async_event(event)
            except Empty:
                continue
            except Exception as e:
                logger.error(f"Async event processing error: {e}", exc_info=True)

    def _run_timer(self, queue: Queue, interval: int) -> None:
        """定时事件生成器"""
        while self._active_flag(queue):
            time.sleep(interval)
            try:
                queue.put_nowait(Event(EventType.TIMER.value))
            except Full:
                logger.warning(f"Timer queue full, dropping timer event")

    def publish(self, event: Event, is_async: bool = False) -> None:
        """
        发布事件
        :param event: 事件对象
        :param is_async: 是否异步处理，默认为False
        """
        self._event_count += 1

        # 通知监控器
        self._notify_monitors(event)

        # 异步处理
        if is_async:
            self.put_async(event)
        else:
            self._process_sync_event(event)

    def _notify_monitors(self, event: Event) -> None:
        """通知所有事件监控器"""
        for monitor in self._monitors:
            try:
                monitor(event)
            except Exception as e:
                logger.error(f"Event monitor error: {e}", exc_info=True)

    def put_sync(self, event: Event) -> None:
        """将事件放入同步队列"""
        try:
            self._sync_queue.put_nowait(event)
        except Full:
            logger.warning(f"Sync event queue full, dropping event: {event.type}")

    def put_async(self, event: Event) -> None:
        """将事件放入异步队列"""
        try:
            self._async_queue.put_nowait(event)
        except Full:
            logger.warning(f"Async event queue full, dropping event: {event.type}")

    def _process_sync_event(self, event: Event) -> None:
        """处理同步事件（立即执行）"""
        # 特定类型处理器
        self._invoke_handlers(event, self._sync_handlers.get(event.type, []))

        # 全局处理器
        self._invoke_handlers(event, self._global_handlers)

    def _process_async_event(self, event: Event) -> None:
        """处理异步事件（队列中执行）"""
        # 特定类型处理器
        self._invoke_handlers(event, self._async_handlers.get(event.type, []))

    @staticmethod
    def _invoke_handlers(event: Event, handlers: List[Callable]) -> None:
        """安全调用处理器列表"""
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Handler error for {event.type}: {e}", exc_info=True)

    def subscribe(self, event_type: str, handler: Callable, is_async: bool = False) -> None:
        """
        订阅事件
        :param event_type: 事件类型
        :param handler: 处理函数
        :param is_async: 是否异步处理，默认为False
        """
        handler_list = self._async_handlers[event_type] if is_async else self._sync_handlers[event_type]

        if handler not in handler_list:
            handler_list.append(handler)
            logger.debug(f"Subscribed handler for {event_type} (async={is_async})")

    def unsubscribe(self, event_type: str, handler: Callable, is_async: bool = False) -> None:
        """
        取消订阅事件
        :param event_type: 事件类型
        :param handler: 处理函数
        :param is_async: 是否异步处理，默认为False
        """
        handler_list = self._async_handlers[event_type] if is_async else self._sync_handlers[event_type]

        if handler in handler_list:
            handler_list.remove(handler)
            logger.debug(f"Unsubscribed handler for {event_type} (async={is_async})")

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

    def load_module(self, module_path: str) -> None:
        """动态加载模块"""
        logger.info(f"Loading module: {module_path}")
        self.publish(Event(EventType.MODULE_LOADED.value, {"path": module_path}))

    def unload_module(self, module_path: str) -> None:
        """卸载模块"""
        logger.info(f"Unloading module: {module_path}")
        self.publish(Event(EventType.MODULE_UNLOAD.value, {"path": module_path}))

    def get_stats(self) -> Dict[str, Any]:
        """获取总线统计信息"""
        return {
            "name": self._name,
            "event_count": self._event_count,
            "sync_handlers": {k: len(v) for k, v in self._sync_handlers.items()},
            "async_handlers": {k: len(v) for k, v in self._async_handlers.items()},
            "global_handlers": len(self._global_handlers),
            "monitors": len(self._monitors),
            "sync_queue_size": self._sync_queue.qsize(),
            "async_queue_size": self._async_queue.qsize(),
            "sync_active": self._sync_active,
            "async_active": self._async_active
        }

    # ---------- 上下文管理 ---------- #
    def __enter__(self):
        self.start_engines()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop_engines()
        # 处理异常或记录日志
        if exc_type:
            logger.error(f"EventBus context error: {exc_val}", exc_info=True)
        return False

    def _active_flag(self, queue: Queue) -> bool:
        """根据队列类型返回活动标志"""
        if queue is self._sync_queue:
            return self._sync_active
        return self._async_active
