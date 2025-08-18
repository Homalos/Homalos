#!/usr/bin/env python
"""
@ProjectName: Homalos_v2
@FileName   : basic_event_bus
@Date       : 2025/8/13 16:20
@Author     : Donny
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 基本事件总线
"""
import time
from collections import defaultdict
from collections.abc import Callable
from queue import Queue, Full, Empty
from threading import Thread, RLock
from types import TracebackType

from src.core.event import Event, EventType
from src.core.logger import get_logger

logger = get_logger("EventBus")


class EventBus:

    DEFAULT_TIMER_INTERVAL = 1  # 默认定时器间隔(秒)
    DEFAULT_QUEUE_SIZE = 10000  # 默认同步处理队列大小

    def __init__(
        self,
        name: str = "EventBus",  # 事件总线名称，改为与EventBus兼容的默认值
        interval: int = DEFAULT_TIMER_INTERVAL,  # 定时器间隔
        *,
        continue_on_error: bool = True,  # 处理器失败策略
        publish_timeout: float = 1.0,  # 发布策略超时等待时长
        stats_snapshot_every_ticks: int | None = None,  # 每N次定时器tick发送一次统计快照
        join_timeout_thread_s: float = 3.0,  # 线程超时等待时长
        join_timeout_timer_s: float = 2.0,  # 定时器超时等待时长
        join_retries: int = 2,  # 线程重试次数
        auto_start: bool = True,  # 自动启动选项，与EventBus行为兼容
    ):
        self._name = name
        self._interval = interval
        # 事件队列
        self._queue: Queue[Event] = Queue(maxsize=self.DEFAULT_QUEUE_SIZE)  # 同步处理队列
        # 事件处理器注册表
        self._handlers: dict[str, list[Callable[[Event], None]]] = defaultdict(list)  # 同步处理器注册表
        self._global_handlers: list[Callable[[Event], None]] = []  # 全局处理器
        self._monitors: list[Callable[[Event], None]] = []  # 事件监控
        self._publish_event_count = 0  # 事件计数，只统计通过 publish 显式发布的事件，不含内部 TIMER 事件。
        self._processed_count = 0  # 处理计数，统计循环处理的所有事件总数（含 TIMER 事件）
        # 错误计数，仅在处理流程抛出未被处理的异常时自增。处理器内部错误若被“继续执行”策略吞掉，不计入 error_count，
        # 只会体现在 event_type_stats[event type].failed。
        self._error_count = 0
        self._dropped_count = 0  # 丢弃计数
        # 事件类型统计（处理/成功/失败/耗时聚合）
        self._event_type_stats: dict[str, dict[str, int]] = defaultdict(
            lambda: {
                "processed": 0,  # 处理计数
                "succeeded": 0,  # 成功计数
                "failed": 0,  # 失败计数，按事件维度统计处理器失败（与全局的 error_count 概念不同）
                "latency_ns_sum": 0,  # 处理耗时
                "latency_count": 0,  # 处理计数
            }
        )
        self._active: bool = False  # 同步处理线程控制标志
        self._thread: Thread | None = None  # 同步处理线程
        self._timer_thread: Thread | None = None  # 定时器处理线程
        self._lock: RLock = RLock()  # 订阅/监控写操作锁
        # 处理器失败策略，默认为True，continue_on_error=True时，记录错误但不中断其它处理器
        # continue_on_error=False时，切换失败策略为 fail-fast，遇错即停止该批处理器后续执行
        self._continue_on_handler_error: bool = continue_on_error
        self._publish_timeout: float | None = publish_timeout
        # 统计快照配置
        self._emit_stats_snapshot: bool = stats_snapshot_every_ticks is not None and stats_snapshot_every_ticks > 0
        self._stats_snapshot_every_ticks: int = stats_snapshot_every_ticks or 0  # 每N次定时器tick发送一次统计快照
        self._timer_tick_count: int = 0
        # 停止等待配置
        self._join_timeout_thread_s: float = join_timeout_thread_s
        self._join_timeout_timer_s: float = join_timeout_timer_s
        self._join_retries: int = max(1, join_retries)
        
        # 自动启动功能（与EventBus兼容）
        if auto_start:
            self.start()

    def subscribe(self, event_type: str, handler: Callable[[Event], None], is_async: bool = False) -> None:
        """
        订阅指定事件类型的消息处理器

        Args:
            event_type (str): 事件类型标识符
            handler (Callable): 事件处理器回调函数
            is_async (bool): 是否异步处理（为兼容EventBus，但BasicEventBus统一按同步处理）

        Returns:
            None: 无返回值
        """
        with self._lock:
            # 尝试获取该事件类型对应的处理函数列表，若无则创建
            try:
                handler_list = self._handlers[event_type]
            except KeyError:
                handler_list = []
                self._handlers[event_type] = handler_list

            # 避免重复订阅同一个处理器（并发安全）
            if handler not in handler_list:
                try:
                    handler_list.append(handler)
                    logger.debug(f"Subscribed handler for {event_type}")
                except Exception as e:
                    logger.error(f"Failed to subscribe handler for {event_type}: {e}")
                    raise
            else:
                logger.debug(f"Handler already subscribed for {event_type}")

    def unsubscribe(self, event_type: str, handler: Callable[[Event], None], is_async: bool = False) -> None:
        """
        取消订阅指定事件类型的消息处理器

        参数:
            event_type (str): 事件类型标识符
            handler (Callable): 要取消订阅的处理器函数
            is_async (bool): 是否异步处理（为兼容EventBus，但BasicEventBus统一按同步处理）

        返回值:
            None
        """
        # 检查事件类型是否存在
        if event_type not in self._handlers:
            logger.debug(f"Handler not found for unsubscription: {event_type}")
            return

        # 获取指定事件类型的所有处理器列表
        handler_list = self._handlers[event_type]

        # 并发安全地检查和移除处理器
        with self._lock:
            if handler in handler_list:
                handler_list.remove(handler)
                logger.debug(f"Unsubscribed handler for {event_type}")
            else:
                logger.debug(f"Handler not found for unsubscription: {event_type}")

            # 如果函数列表为空，则从处理器字典中移除该事件类型
            if not handler_list:
                del self._handlers[event_type]

    def subscribe_global(self, handler: Callable[[Event], None]) -> None:
        """
        为所有事件类型订阅一个新的处理函数。每个函数只能为每种事件类型订阅一次。
        """
        with self._lock:
            if handler not in self._global_handlers:
                self._global_handlers.append(handler)

    def unsubscribe_global(self, handler: Callable[[Event], None]) -> None:
        """
        取消订阅现有的全局处理程序函数。
        """
        if handler in self._global_handlers:
            self._global_handlers.remove(handler)

    def publish(self, event: Event, is_async: bool = False) -> None:
        """
        发布事件到事件总线

        :param event: 要发布的事件对象
        :param is_async: 是否异步处理（为兼容EventBus，但BasicEventBus统一按同步处理）
        :return: 无返回值
        """
        logger.debug("EventBus发布事件: %s 数据类型: %s", event.type, type(event.data))

        # 事件计数
        self._publish_event_count += 1

        # 通知监控器
        self._notify_monitors(event)

        # 将事件放入队列，阻塞直至放入队列
        timeout = self._publish_timeout or 1.0
        try:
            self._queue.put(event, block=True, timeout=timeout)
        except Full:
            self._dropped_count += 1
            logger.warning("Event queue full after timeout %s, dropping event: %s", timeout, event.type)

    def start(self) -> None:
        """启动同步事件处理线程"""
        logger.info(f"EventBus '{self._name}' engines started")

        if self._active:
            return

        self._active = True
        # 启动事件处理线程
        self._thread = Thread(
            target=self.run,
            name=f"{self._name}-Thread",
            daemon=True
        )
        self._thread.start()
        logger.info(f"Started event bus for {self._name}")

        # 启动定时器线程（重复启动保护）
        if self._timer_thread is None or not self._timer_thread.is_alive():
            self._timer_thread = Thread(
                target=self.run_timer,
                args=(self._queue, self._interval),
                name=f"{self._name}-Timer",
                daemon=True
            )
            self._timer_thread.start()
        logger.debug(f"Started Timer for {self._name}")

    def stop(self) -> None:
        """
        停止事件总线的所有运行组件

        该方法会按顺序停止定时器线程和事件处理线程，确保资源得到优雅释放。
        首先检查组件是否处于活跃状态，如果不是则直接返回。
        然后依次停止定时器线程和事件处理线程，并在超时情况下记录警告日志。

        Returns:
            None: 无返回值
        """

        if not self._active:
            return

        # 优先投递关停事件，尽快唤醒阻塞的 get()
        self.put(Event(EventType.SYSTEM_SHUTDOWN))

        self._active = False

        # 封装线程优雅关闭逻辑
        def _stop_thread(thread: Thread | None, timeout: float, name_suffix: str) -> None:
            if thread and thread.is_alive():
                try:
                    for _ in range(self._join_retries):
                        thread.join(timeout=timeout)
                        if not thread.is_alive():
                            return
                    logger.warning(f"Thread failed to stop within timeout for {self._name} ({name_suffix})")
                except Exception as e:
                    logger.error(f"Error stopping thread: {e}", exc_info=True)

        # 优雅关闭定时器线程
        _stop_thread(self._timer_thread, self._join_timeout_timer_s, "timer")

        # 优雅关闭事件处理线程
        _stop_thread(self._thread, self._join_timeout_thread_s, "event handler")

        logger.info(f"Event bus stopped for {self._name}")

    def put(self, event: Event) -> None:
        """
        将事件放入队列中

        Args:
            event (Event): 要放入队列的事件对象

        Returns:
            None: 无返回值

        Raises:
            无异常抛出，队列满时会记录警告日志并丢弃事件
        """
        try:
            # 尝试将事件放入队列
            self._queue.put(event)
        except Full:
            # 队列已满，记录警告日志并丢弃事件
            logger.warning(f"Event queue full, dropping event: {event.type}")

    def run(self) -> None:
        """
        运行事件循环的核心方法

        该方法会持续从事件队列中获取事件并处理，直到收到关闭信号为止。
        方法会在内部维护一个活动状态标志，当该标志为False时循环结束。

        Returns:
            None: 无返回值

        异常处理:
            - Empty: 队列为空时继续循环
            - Exception: 捕获其他异常并记录错误日志
        """
        logger.debug("Event loop started for %s", self._name)

        # 主事件处理循环
        while self._active:
            try:
                # 从队列中获取事件，超时时间为1.0秒
                event: Event = self._queue.get(block=True, timeout=1.0)

                # 检查关闭信号
                if event.type == EventType.SYSTEM_SHUTDOWN:
                    logger.debug("Received shutdown signal in sync event bus")
                    break

                # 记录事件处理开始
                logger.debug(f"Processing sync event: {event.type}")
                self.process(event)

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
        logger.debug(f"Event loop stopped for {self._name}")

    def process(self, event: Event) -> None:
        start_ns = time.time_ns()
        errors_count = 0
        try:
            # 使用快照以避免并发修改影响
            local_handlers = list(self._handlers.get(event.type, []))
            global_handlers = list(self._global_handlers)

            # 特定类型处理器
            errors_count += self._invoke_handlers(
                event,
                local_handlers,
                continue_on_error=self._continue_on_handler_error,
            )

            # 全局处理器
            errors_count += self._invoke_handlers(
                event,
                global_handlers,
                continue_on_error=self._continue_on_handler_error,
            )
        except Exception as e:
            errors_count += 1
            self._error_count += 1
            raise e
        finally:
            # 更新统计信息
            self._processed_count += 1
            end_ns = time.time_ns()
            latency = max(0, end_ns - start_ns)
            stats = self._event_type_stats[event.type]
            stats["processed"] += 1
            if errors_count > 0:
                stats["failed"] += 1
            else:
                stats["succeeded"] += 1
            stats["latency_ns_sum"] += latency
            stats["latency_count"] += 1

    def run_timer(self, queue: Queue[Event], interval: int) -> None:
        while self._active_flag(queue):
            time.sleep(interval)

            self.put(Event(EventType.TIMER))

            # 可选：定期向监控器发出统计快照
            if self._emit_stats_snapshot and self._stats_snapshot_every_ticks > 0:
                self._timer_tick_count = (self._timer_tick_count + 1) % self._stats_snapshot_every_ticks
                if self._timer_tick_count == 0:
                    self._emit_stats_snapshot_to_monitors()

    def get_stats(self) -> dict[str, object]:
        """
        获取当前总线统计信息的浅拷贝快照。
        """
        event_type_stats_copy: dict[str, dict[str, int]] = {
            k: v.copy() for k, v in self._event_type_stats.items()
        }
        return {
            "name": self._name,
            "active": self._active,
            "queue_size": self._queue.qsize(),
            "publish_event_count": self._publish_event_count,
            "processed_count": self._processed_count,
            "error_count": self._error_count,
            "dropped_count": self._dropped_count,
            "event_type_stats": event_type_stats_copy,
            "publish_timeout": self._publish_timeout,
        }

    def add_monitor(self, monitor: Callable[[Event], None]) -> None:
        """
        添加事件监视器到监视器列表中

        :param monitor: 可调用的监视器函数，用于处理事件
        :return: 无返回值
        """
        # 检查监视器是否已存在，避免重复添加（并发安全）
        if monitor not in self._monitors:
            with self._lock:
                if monitor not in self._monitors:
                    self._monitors.append(monitor)
                    logger.debug("Added event monitor")

    def remove_monitor(self, monitor: Callable[[Event], None]) -> None:
        """
        从监视器列表中移除指定的监视器函数

        参数:
            monitor (Callable): 需要被移除的监视器回调函数

        返回值:
            无
        """
        # 检查监视器是否存在于列表中，如果存在则移除（并发安全）
        if monitor in self._monitors:
            with self._lock:
                if monitor in self._monitors:
                    self._monitors.remove(monitor)
                    logger.debug("Removed event monitor")

    def get_bus_name(self) -> str:
        """
        获取总线名称

        Returns:
            str: 总线的名称
        """
        return self._name
    
    @property
    def name(self) -> str:
        """获取事件总线名称（兼容EventBus属性访问）"""
        return self._name

    @staticmethod
    def _invoke_handlers(
            event: Event,
            handlers: list[Callable[[Event], None]],
            *,
            continue_on_error: bool = True,
    ) -> int:
        """
        调用事件处理器列表中的所有处理器函数

        :param event: 事件对象，将传递给每个处理器函数
        :param handlers: 处理器函数列表，每个函数都接受event参数
        :param continue_on_error: 是否在单个处理器失败后继续执行其他处理器
        :return: 错误数量
        """
        errors = 0
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                errors += 1
                logger.error(f"Handler error for {event.type}: {e}", exc_info=True)
                if not continue_on_error:
                    raise e
        return errors

    def _notify_monitors(self, event: Event) -> None:
        """
        通知所有注册的监控器处理事件

        :param event: 要处理的事件对象
        :return: 无返回值
        """
        logger.debug(f"EventBus通知监控器: {event.type}")
        # 遍历所有监控器并调用处理函数（使用快照以避免并发修改）
        for monitor in list(self._monitors):
            try:
                monitor(event)
            except Exception as e:
                logger.error(f"Event monitor error: {e}", exc_info=True)

    def __enter__(self) -> "BasicEventBus":
        """
        进入上下文管理器时调用。
        Args:
            无。
        Returns:
            self: 返回实例本身，以便在with语句中继续使用该实例。
        """
        self.start()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None
    ) -> bool | None:
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
        return None

    def _active_flag(self, sync_queue: Queue[Event]) -> bool:
        """
        检查队列的活跃状态标志。

        :param sync_queue: 要检查的队列对象
        :return: 队列的活跃状态布尔值
        """
        # 如果传入的队列是当前实例的队列，则返回当前活跃状态
        if sync_queue is self._queue:
            return self._active
        # 否则也返回当前活跃状态
        return self._active

    def set_continue_on_error(self, flag: bool) -> None:
        """设置处理器失败时是否继续执行其他处理器。"""
        self._continue_on_handler_error = bool(flag)

    def enable_stats_snapshot(self, every_ticks: int = 60) -> None:
        """启用定期统计快照，通过监控器通知，基于定时器 tick 计数。"""
        if every_ticks <= 0:
            raise ValueError("every_ticks must be > 0")
        self._emit_stats_snapshot = True
        self._stats_snapshot_every_ticks = every_ticks
        self._timer_tick_count = 0

    def disable_stats_snapshot(self) -> None:
        """禁用统计快照通知。"""
        self._emit_stats_snapshot = False
        self._stats_snapshot_every_ticks = 0
        self._timer_tick_count = 0

    def _emit_stats_snapshot_to_monitors(self) -> None:
        """向监控器发送当前统计快照事件。"""
        try:
            snapshot = self.get_stats()
            self._notify_monitors(Event("bus.stats", data=snapshot, source=self._name))
        except Exception as e:
            logger.error(f"Emit stats snapshot error: {e}", exc_info=True)


if __name__ == '__main__':
    print("test BasicEventBus")
    # from datetime import datetime

    # def timer_handler(event: Event) -> None:
    #     """
    #     处理TIMER事件。
    #     """
    #     print(f"timer_handler type: {event.type}")
    #     print(f"timer_handler data: {event.data}")
    #     timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    #     print(f'[{timestamp}] 处理TIMER事件')

    # def bus_stats_handler(event):
    #     """
    #     处理BUS_STATS事件。
    #     """
    #     print(f"bus_stats_handler type: {event.type}")
    #     print(f"bus_stats_handler data: {event.data}")
    #     print(f'收到BUS_STATS事件：{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')

    # def bus_monitor(event: Event) -> None:
    #     if event.type == "bus.stats":
    #         print(f"[monitor] stats snapshot: {event.data}")
    #     else:
    #         print(f"[monitor] {event.type}")

    # print("=" * 50)
    # print("启动事件总线测试...")

    # eb = BasicEventBus(name="Test Engine")

    # # 正确订阅TIMER事件类型
    # eb.subscribe(EventType.TIMER, timer_handler)
    # eb.subscribe("bus.stats", bus_stats_handler)
    # # 注册监控器
    # eb.add_monitor(bus_monitor)
    # eb.start()

    # # 读取一次统计
    # print("[main] stats:", eb.get_stats())

    # print("\n事件总线已启动，按 Ctrl+C 退出...")
    # print("=" * 50)

    # try:
    #     # 保持程序运行
    #     input("按 Enter 键停止测试...\n")
    # except KeyboardInterrupt:
    #     print("\n收到中断信号，正在停止...")
    # finally:
    #     eb.stop()
    #     # 等待停止日志输出完成
    #     time.sleep(0.1)
    #     print("\n" + "=" * 50)
    #     print("测试完成！")
    #     print("=" * 50)
