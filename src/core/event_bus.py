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
from datetime import datetime
from queue import Queue, Empty, Full
from threading import Thread
from typing import Any, Dict, List, Callable, Optional

from src.core.event import Event, EventType
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
    DEFAULT_SYNC_QUEUE_SIZE = 10000  # 默认同步处理队列大小
    DEFAULT_ASYNC_QUEUE_SIZE = 10000  # 默认异步处理队列大小
    DEFAULT_TIMER_INTERVAL = 1  # 默认定时器间隔(秒)

    def __init__(self,
                 name: str = "EventBus",
                 interval: int = DEFAULT_TIMER_INTERVAL):
        
        self._name = name  # 事件总线名称
        self._interval: int = interval  # 定时器间隔

        # 事件队列
        self._sync_queue = Queue(maxsize=self.DEFAULT_SYNC_QUEUE_SIZE)  # 同步处理队列
        self._async_queue = Queue(maxsize=self.DEFAULT_ASYNC_QUEUE_SIZE)  # 异步处理队列

        # 事件处理器注册表
        self._sync_handlers: Dict[str, List[Callable]] = defaultdict(list)  # 同步处理器注册表。
        self._async_handlers: Dict[str, List[Callable]] = defaultdict(list)  # 异步处理器注册表。
        self._global_handlers: List[Callable] = []  # 全局处理器(同步)

        self._monitors: List[Callable] = []  # 事件监控
        self._event_count = 0  # 事件计数
        self._sync_processed_count = 0  # 同步处理计数
        self._async_processed_count = 0  # 异步处理计数
        self._error_count = 0  # 错误计数
        self._event_type_stats: Dict[str, int] = defaultdict(int)  # 事件类型统计

        self._sync_active: bool = False  # 同步处理线程控制标志
        self._async_active: bool = False  # 异步处理线程控制标志

        self._sync_thread: Optional[Thread] = None  # 同步处理线程
        self._async_thread: Optional[Thread] = None  # 异步处理线程
        self._sync_timer: Optional[Thread] = None  # 异步定时器处理线程
        self._async_timer: Optional[Thread] = None  # 异步定时器处理线程

        # 启动事件处理线程
        self.start()

    def start(self) -> None:
        """启动所有事件处理线程"""
        self._start_sync()
        self._start_async()
        logger.info(f"EventBus '{self._name}' engines started")

    def stop(self) -> None:
        """停止所有事件处理线程"""
        self._stop_sync()
        self._stop_async()
        logger.info(f"EventBus '{self._name}' engines stopped")

    def _start_sync(self) -> None:
        """启动同步事件处理线程"""
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

    def _stop_sync(self) -> None:
        """停止同步事件处理引擎"""
        if not self._sync_active:
            return

        self._sync_active = False
        
        # 优雅关闭定时器线程
        if self._sync_timer and self._sync_timer.is_alive():
            try:
                self._sync_timer.join(timeout=2.0)
                if self._sync_timer.is_alive():
                    logger.warning(f"Sync timer thread failed to stop within timeout for {self._name}")
            except Exception as e:
                logger.error(f"Error stopping sync timer thread: {e}", exc_info=True)

        # 优雅关闭事件处理线程
        if self._sync_thread and self._sync_thread.is_alive():
            try:
                # 发送停止信号
                self._sync_queue.put(Event(EventType.SHUTDOWN))
                self._sync_thread.join(timeout=3.0)
                if self._sync_thread.is_alive():
                    logger.warning(f"Sync thread failed to stop within timeout for {self._name}")
            except Exception as e:
                logger.error(f"Error stopping sync thread: {e}", exc_info=True)
        logger.info(f"Sync engine stopped for {self._name}")

    def _run_sync_loop(self) -> None:
        """同步事件处理主循环"""
        logger.debug(f"Sync event loop started for {self._name}")
        while self._sync_active:
            try:
                event: Event = self._sync_queue.get(block=True, timeout=0.5)

                # 检查关闭信号
                if event.type == EventType.SHUTDOWN:
                    logger.debug("Received shutdown signal in sync engine")
                    break

                # 记录事件处理开始
                logger.debug(f"Processing sync event: {event.type}")
                self._process_sync_event(event)
                
            except Empty:
                continue
            except Exception as e:
                logger.error(
                    "Sync loop error",
                    extra={
                        "component": self._name,
                        "error": str(e)
                    },
                    exc_info=True
                )
        logger.debug(f"Sync event loop stopped for {self._name}")

    def _start_async(self) -> None:
        """启动异步事件处理线程"""
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

    def _stop_async(self) -> None:
        """停止异步事件处理引擎"""
        if not self._async_active: 
            return

        self._async_active = False

        # 优雅关闭定时器线程
        if self._async_timer and self._async_timer.is_alive():
            try:
                self._async_timer.join(timeout=2.0)
                if self._async_timer.is_alive():
                    logger.warning(f"Async timer thread failed to stop within timeout for {self._name}")
            except Exception as e:
                logger.error(f"Error stopping async timer thread: {e}", exc_info=True)

        # 优雅关闭事件处理线程
        if self._async_thread and self._async_thread.is_alive():
            try:
                # 发送关闭信号
                self._async_queue.put(Event(EventType.SHUTDOWN))
                self._async_thread.join(timeout=3.0)
                if self._async_thread.is_alive():
                    logger.warning(f"Async thread failed to stop within timeout for {self._name}")
            except Exception as e:
                logger.error(f"Error stopping async thread: {e}", exc_info=True)
        logger.info(f"Async engine stopped for {self._name}")

    def _run_async_loop(self) -> None:
        """异步事件处理循环"""
        logger.debug("Async event loop started", extra={"component": self._name})
        while self._async_active:
            try:
                event = self._async_queue.get(timeout=0.5)

                # 检查关闭信号
                if event.type == EventType.SHUTDOWN:
                    logger.debug("Received shutdown signal in async engine")
                    break

                # 记录事件处理开始
                logger.debug("Processing async event", extra={"component": self._name, "event_type": event.type})
                self._process_async_event(event)
                
            except Empty:
                # 超时是正常的，不需要记录
                continue
            except Exception as e:
                logger.error(
                    "Async loop error",
                    extra={
                        "component": self._name,
                        "error": str(e)
                    },
                    exc_info=True
                )
        logger.debug("Async event loop stopped", extra={"component": self._name})

    def _run_timer(self, queue: Queue, interval: int) -> None:
        """定时事件生成器"""
        while self._active_flag(queue):
            time.sleep(interval)
            try:
                queue.put_nowait(Event(EventType.TIMER))
            except Full:
                logger.warning(f"Timer queue full, dropping timer event")

    def publish(self, event: Event, is_async: bool = False) -> None:
        """
        发布事件
        :param event: 事件对象
        :param is_async: 是否异步处理，默认为False
        """
        logger.debug(f"EventBus发布事件: {event.type} 数据类型: {type(event.data)}")
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
        logger.debug(f"EventBus通知监控器: {event.type}")
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
        try:
            # 特定类型处理器
            self._invoke_handlers(event, self._sync_handlers.get(event.type, []))

            # 全局处理器
            self._invoke_handlers(event, self._global_handlers)
            
            # 更新统计信息
            self._sync_processed_count += 1
            self._event_type_stats[event.type] += 1
        except Exception as e:
            self._error_count += 1
            raise e

    def _process_async_event(self, event: Event) -> None:
        """处理异步事件（队列中执行）"""
        try:
            # 特定类型处理器
            self._invoke_handlers(event, self._async_handlers.get(event.type, []))
            
            # 更新统计信息
            self._async_processed_count += 1
            self._event_type_stats[event.type] += 1
        except Exception as e:
            self._error_count += 1
            raise e

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
        :param event_type: 事件类型，字符串
        :param handler: 处理函数
        :param is_async: 是否异步处理，默认为False
        """
        # 类型验证和转换
        if isinstance(event_type, str):
            event_type_str = event_type
        else:
            raise TypeError(f"event_type must be str, got {type(event_type)}")
        
        # 验证处理函数
        if not callable(handler):
            raise TypeError(f"handler must be callable, got {type(handler)}")
        
        handler_list = self._async_handlers[event_type_str] if is_async else self._sync_handlers[event_type_str]

        if handler not in handler_list:
            handler_list.append(handler)
            logger.debug(f"Subscribed handler for {event_type_str} (async={is_async})")
        else:
            logger.warning(f"Handler already subscribed for {event_type_str} (async={is_async})")

    def unsubscribe(self, event_type: str, handler: Callable, is_async: bool = False) -> None:
        """
        取消订阅事件
        :param event_type: 事件类型，字符串
        :param handler: 处理函数
        :param is_async: 是否异步处理，默认为False
        """
        # 类型验证和转换
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

    def load_module(self, module_path: str) -> None:
        """动态加载模块"""
        logger.info(f"Loading module: {module_path}")
        self.publish(Event(EventType.MODULE_LOADED, {"path": module_path}))

    def unload_module(self, module_path: str) -> None:
        """卸载模块"""
        logger.info(f"Unloading module: {module_path}")
        self.publish(Event(EventType.MODULE_UNLOAD, {"path": module_path}))

    @property
    def name(self) -> str:
        """获取事件总线名称"""
        return self._name

    def get_stats(self) -> Dict[str, Any]:
        """获取总线统计信息"""
        return {
            "name": self._name,
            "total_events_published": self._event_count,
            "sync_events_processed": self._sync_processed_count,
            "async_events_processed": self._async_processed_count,
            "total_events_processed": self._sync_processed_count + self._async_processed_count,
            "error_count": self._error_count,
            "event_type_stats": dict(self._event_type_stats),
            "handlers": {
                "sync_handlers": {k: len(v) for k, v in self._sync_handlers.items()},
                "async_handlers": {k: len(v) for k, v in self._async_handlers.items()},
                "global_handlers": len(self._global_handlers),
            },
            "monitors": len(self._monitors),
            "queues": {
                "sync_queue_size": self._sync_queue.qsize(),
                "async_queue_size": self._async_queue.qsize(),
            },
            "status": {
                "sync_active": self._sync_active,
                "async_active": self._async_active,
            }
        }

    # ---------- 上下文管理 ---------- #
    def __enter__(self):
        """
        进入上下文管理器时调用。
        Args:
            无。
        Returns:
            self: 返回实例本身，以便在with语句中继续使用该实例。
        """
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        上下文管理协议退出方法。
        Args:
            exc_type (Exception type, optional): 异常类型。默认为None。
            exc_val (Exception, optional): 异常对象。默认为None。
            exc_tb (Traceback, optional): 异常回溯信息。默认为None。
        Returns:
            bool: 如果异常被处理，则返回True；否则返回False。
        """
        self.stop()
        # 处理异常或记录日志
        if exc_type:
            logger.error(f"EventBus context error: {exc_val}", exc_info=True)
        return False

    def _active_flag(self, queue: Queue) -> bool:
        """根据队列类型返回活动标志"""
        if queue is self._sync_queue:
            return self._sync_active
        return self._async_active


if __name__ == '__main__':
    def timer_handler():
        """
        处理TIMER事件。
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f'[{timestamp}] 处理TIMER事件')

    def shutdown_handler():
        print(f'收到关闭事件：{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')

    print("=" * 50)
    print("启动事件总线测试...")

    eb = EventBus(name="Test Engine")
    
    # 正确订阅TIMER事件类型
    eb.subscribe(EventType.TIMER, timer_handler)
    eb.subscribe(EventType.SHUTDOWN, shutdown_handler)
    
    print("\n事件总线已启动，按 Ctrl+C 退出...")
    print("=" * 50)

    try:
        # 保持程序运行
        input("按 Enter 键停止测试...\n")
    except KeyboardInterrupt:
        print("\n收到中断信号，正在停止...")
    finally:
        eb.stop()
        # 等待停止日志输出完成
        time.sleep(0.1)
        print("\n" + "=" * 50)
        print("测试完成！")
        print("=" * 50)
