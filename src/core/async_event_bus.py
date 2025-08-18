#!/usr/bin/env python
"""
@ProjectName: Homalos_v2
@FileName   : async_event_bus.py
@Date       : 2025/8/17 22:45
@Author     : Donny
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 基于 asyncio 的异步事件总线实现，暂时未使用
"""
import asyncio
import concurrent.futures as cf
import contextlib
import threading
import time
from collections import defaultdict
from collections.abc import Callable, Awaitable
from queue import Queue
from types import TracebackType

from src.core.event import Event, EventType
from src.core.logger import get_logger

logger = get_logger("AsyncEventBus")


class AsyncEventBus:

    DEFAULT_TIMER_INTERVAL = 1  # 默认定时器间隔(秒)
    DEFAULT_QUEUE_SIZE = 10000  # 默认异步处理队列大小

    def __init__(
        self,
                 name: str = "default",  # 事件总线名称
                 interval: int = DEFAULT_TIMER_INTERVAL,  # 定时器间隔
        *,
        continue_on_error: bool = True,  # 处理器失败策略
        publish_timeout: float | None = 1.0,  # 发布策略超时等待时长
        stats_snapshot_every_ticks: int | None = None,  # 每N次定时器tick发送一次统计快照
        join_timeout_thread_s: float = 3.0,  # 线程超时等待时长
        join_retries: int = 2,  # 线程重试次数
    ) -> None:
        # 配置
        self._name = name
        self._interval = interval
        self._continue_on_handler_error: bool = continue_on_error
        self._publish_timeout: float | None = publish_timeout

        # 事件处理与注册
        self._queue: asyncio.Queue[Event] | None = None
        # 只支持异步处理器的类型定义
        handler_type = Callable[[Event], Awaitable[None]]
        self._handlers: dict[str, list[handler_type]] = defaultdict(list)
        self._global_handlers: list[handler_type] = []
        self._monitors: list[handler_type] = []

        # 统计
        self._publish_event_count = 0
        self._processed_count = 0
        self._error_count = 0
        self._dropped_count = 0
        self._event_type_stats: dict[str, dict[str, int]] = defaultdict(
            lambda: {
                "processed": 0,
                "succeeded": 0,
                "failed": 0,
                "latency_ns_sum": 0,
                "latency_count": 0,
            }
        )

        # 定时器/快照
        self._emit_stats_snapshot: bool = (
            stats_snapshot_every_ticks is not None and stats_snapshot_every_ticks > 0
        )
        self._stats_snapshot_every_ticks: int = stats_snapshot_every_ticks or 0
        self._timer_tick_count: int = 0

        # 生命周期/线程
        self._active: bool = False
        self._thread: threading.Thread | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._main_task: asyncio.Task | None = None
        self._timer_task: asyncio.Task | None = None
        self._lock: threading.RLock = threading.RLock()

        # 停止等待配置
        self._join_timeout_thread_s: float = join_timeout_thread_s
        self._join_retries: int = max(1, join_retries)

    # =============== Bus 接口：订阅/取消订阅 ===============
    def subscribe(self, event_type: str, handler: Callable[[Event], Awaitable[None]]) -> None:
        """订阅指定事件类型的处理器。"""
        with self._lock:
            handler_list = self._handlers[event_type]
            if handler not in handler_list:
                handler_list.append(handler)
                logger.debug(f"Subscribed handler for {event_type}")
            else:
                logger.debug(f"Handler already subscribed for {event_type}")

    def unsubscribe(self, event_type: str, handler: Callable[[Event], Awaitable[None]]) -> None:
        """取消订阅指定事件类型的处理器。"""
        with self._lock:
            if event_type not in self._handlers:
                logger.debug(f"Handler not found for unsubscription: {event_type}")
                return
            handler_list = self._handlers[event_type]
            if handler in handler_list:
                handler_list.remove(handler)
                logger.debug(f"Unsubscribed handler for {event_type}")
            else:
                logger.debug(f"Handler not found for unsubscription: {event_type}")
            if not handler_list:
                del self._handlers[event_type]

    def subscribe_global(self, handler: Callable[[Event], Awaitable[None]]) -> None:
        """为所有事件类型订阅一个新的处理函数。"""
        with self._lock:
            if handler not in self._global_handlers:
                self._global_handlers.append(handler)

    def unsubscribe_global(self, handler: Callable[[Event], Awaitable[None]]) -> None:
        """取消订阅现有的全局处理程序函数。"""
        with self._lock:
            if handler in self._global_handlers:
                self._global_handlers.remove(handler)

    # =============== 发布与监控 ===============
    def publish(self, event: Event, topic: str | None = None) -> None:
        """
        发布事件到事件总线（线程安全）。

        语义与 BasicEventBus 保持一致：
        - 计数递增
        - 先通知监控器，再入队
        - 入队遵循 publish_timeout，超时丢弃并计数
        """
        logger.debug("AsyncEventBus发布事件: %s 数据类型: %s", event.type, type(event.data))
        self._publish_event_count += 1

        loop = self._loop
        if loop is None:
            logger.warning("Event loop not started, dropping event: %s", event.type)
            self._dropped_count += 1
            return

        # 检查事件循环是否已关闭
        if loop.is_closed():
            self._dropped_count += 1
            logger.warning("Event loop is closed, dropping event: %s", event.type)
            return

        # 通知监控器（不阻塞调用方）
        try:
            asyncio.run_coroutine_threadsafe(self._notify_monitors_async(event), loop)
        except (RuntimeError, Exception) as e:
            logger.debug(f"Schedule monitor notify failed (loop may be closed): {e}")

        # 入队（遵循超时）
        timeout = self._publish_timeout or 1.0
        try:
            future = asyncio.run_coroutine_threadsafe(self._queue_put_async(event), loop)
            future.result(timeout)
        except cf.TimeoutError:
            self._dropped_count += 1
            logger.warning("Event queue put timeout %s, dropping event: %s", timeout, event.type)
        except RuntimeError as e:
            # 可能是事件循环已关闭
            self._dropped_count += 1
            logger.debug(f"Event publish failed (loop may be closed): {e}")
        except Exception as e:
            self._dropped_count += 1
            logger.error(f"Event publish failed: {e}", exc_info=True)

    async def _queue_put_async(self, event: Event) -> None:
        if self._queue is None:
            raise RuntimeError("Async queue not initialized")
        try:
            await self._queue.put(event)
        except asyncio.CancelledError:
            # 协程被取消，安静地退出
            raise
        except Exception as e:
            # 其他异常，重新抛出
            raise e

    # =============== 生命周期：启动/停止 ===============
    def start(self) -> None:
        """启动异步事件总线：创建独立事件循环与后台线程。"""
        if self._active:
            return
        self._active = True

        # 添加同步机制，确保事件循环完全就绪
        ready_event = threading.Event()

        def _loop_entrypoint() -> None:
            # 初始化任务变量，避免在异常流程中访问未定义变量
            self._main_task = None
            self._timer_task = None

            try:
                self._loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self._loop)
                self._queue = asyncio.Queue(maxsize=self.DEFAULT_QUEUE_SIZE)

                # 创建核心协程任务
                self._main_task = self._loop.create_task(self._run())
                self._timer_task = self._loop.create_task(self._run_timer())

                # 通知主线程事件循环已就绪
                ready_event.set()

                logger.info(f"AsyncEventBus '{self._name}' started")
                self._loop.run_forever()
            except Exception as e:
                logger.error(f"Async loop entrypoint error: {e}", exc_info=True)
                # 即使出错也要通知主线程，避免主线程阻塞
                ready_event.set()
            finally:
                    # 退出时清理任务
                    try:
                        pending: list[asyncio.Task] = []
                        if self._main_task and not self._main_task.done():
                            self._main_task.cancel()
                            pending.append(self._main_task)
                        if self._timer_task and not self._timer_task.done():
                            self._timer_task.cancel()
                            pending.append(self._timer_task)
                        if pending and self._loop is not None:
                            self._loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                    except Exception as e:
                        logger.error(f"Async loop cleanup error: {e}", exc_info=True)
                    finally:
                        with contextlib.suppress(Exception):
                            if self._loop is not None:
                                self._loop.close()

        self._thread = threading.Thread(target=_loop_entrypoint, name=f"{self._name}-AsyncLoop", daemon=True)
        self._thread.start()
        
        # 等待事件循环就绪，最多等待3秒
        if not ready_event.wait(timeout=3.0):
            logger.error(f"AsyncEventBus '{self._name}' failed to start within timeout")
            self._active = False
            raise RuntimeError(f"AsyncEventBus '{self._name}' failed to start within timeout")

    def stop(self) -> None:
        """停止事件总线（同步方法）。"""
        if not self._active:
            return

        # 尽快唤醒消费者并请求关闭
        try:
            self.publish(Event(EventType.SYSTEM_SHUTDOWN))
        except Exception as e:
            logger.warning(f"Failed to publish shutdown event: {e}", exc_info=True)

        self._active = False

        loop = self._loop
        if loop is not None and not loop.is_closed():
            try:
                # 调度清理任务到事件循环
                future = asyncio.run_coroutine_threadsafe(self._cleanup_tasks(), loop)
                # 等待清理完成，使用较短的超时时间
                try:
                    future.result(timeout=1.0)  # 进一步减少超时时间，因为我们已经优化了内部逻辑
                except cf.TimeoutError:
                    logger.debug(f"Cleanup tasks timeout for {self._name}, forcing shutdown")
                    # 超时后强制停止循环
                    if not loop.is_closed():
                        loop.call_soon_threadsafe(loop.stop)
                except Exception as e:
                    logger.error(f"Error during cleanup: {str(e)}")
                    logger.error(f"Exception type: {type(e).__name__}")
                    # 出错时也尝试停止循环
                    if not loop.is_closed():
                        try:
                            loop.call_soon_threadsafe(loop.stop)
                        except Exception:
                            pass
            except Exception as e:
                logger.error(f"Error scheduling cleanup: {e}", exc_info=True)

        # 等待线程退出（带重试）
        thread = self._thread
        if thread and thread.is_alive():
            self._join_thread_with_retry(thread)

        logger.info(f"Async event bus stopped for {self._name}")

    def _join_thread_with_retry(self, thread: threading.Thread) -> None:
        """尝试多次 join 线程直到超时或线程终止。"""
        for _ in range(self._join_retries):
            thread.join(timeout=self._join_timeout_thread_s)
            if not thread.is_alive():
                return
        if thread.is_alive():
            logger.warning("Async loop thread failed to stop within timeout for %s", self._name)

    async def _cleanup_tasks(self) -> None:
        """清理所有挂起的任务并停止事件循环。"""
        try:
            # 收集需要取消的任务
            tasks_to_cancel: list[asyncio.Task] = []
            if self._main_task and not self._main_task.done():
                self._main_task.cancel()
                tasks_to_cancel.append(self._main_task)
            if self._timer_task and not self._timer_task.done():
                self._timer_task.cancel()
                tasks_to_cancel.append(self._timer_task)

            # 等待任务取消完成
            if tasks_to_cancel:
                try:
                    # 使用更短的超时时间，因为_run_timer已经优化了响应速度
                    await asyncio.wait_for(
                        asyncio.gather(*tasks_to_cancel, return_exceptions=True),
                        timeout=0.5
                    )
                except TimeoutError:
                    logger.debug("Some tasks failed to cancel within timeout, continuing cleanup")
                except Exception as e:
                    logger.error(f"Error waiting for task cancellation: {e}", exc_info=True)

        except Exception as e:
            logger.error(f"Error during task cleanup: {e}", exc_info=True)
        finally:
            # 停止事件循环 - 减少延迟时间
            try:
                await asyncio.sleep(0.02)  # 给一点时间让取消操作完成
                loop = asyncio.get_running_loop()
                loop.stop()
            except Exception as e:
                logger.error(f"Error stopping loop in cleanup: {e}", exc_info=True)

    # =============== 事件放入（内部/工具） ===============
    def put(self, event: Event) -> None:
        """将事件放入队列（线程安全）。"""
        loop = self._loop
        if loop is None:
            logger.warning("Event loop not started, dropping event via put(): %s", event.type)
            self._dropped_count += 1
            return
        
        if loop.is_closed():
            self._dropped_count += 1
            logger.debug("Event loop is closed, dropping event via put(): %s", event.type)
            return
            
        try:
            asyncio.run_coroutine_threadsafe(self._queue_put_async(event), loop)
        except RuntimeError as e:
            self._dropped_count += 1
            logger.debug(f"put() failed (loop may be closed): {e}")
        except Exception as e:
            self._dropped_count += 1
            logger.error(f"put() failed: {e}", exc_info=True)

    # =============== 主循环/处理器/定时器（协程） ===============
    def run(self) -> None:
        """兼容接口（未使用）。"""
        return

    def run_timer(self, queue: Queue, interval: int) -> None:
        """兼容接口（未使用，由 _run_timer 协程实现）。"""
        return

    async def _run(self) -> None:
        logger.debug("Async event loop started for %s", self._name)
        assert self._queue is not None
        while self._active:
            try:
                try:
                    event: Event = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                except TimeoutError:
                    continue

                if event.type == EventType.SYSTEM_SHUTDOWN:
                    logger.debug("Received shutdown signal in async event bus")
                    break

                logger.debug(f"Processing async event: {event.type}")
                try:
                    await self._process(event)
                except Exception as e:
                    logger.error(
                        "Async loop error",
                        extra={"component": self._name, "error": str(e)},
                        exc_info=True,
                    )
            except Exception as e:
                logger.error(f"Unexpected async loop error: {e}", exc_info=True)
        logger.debug(f"Async event loop stopped for {self._name}")

    def process(self, event: Event) -> None:
        pass

    async def _process(self, event: Event) -> None:
        start_ns = time.time_ns()
        errors_count = 0
        try:
            with self._lock:
                local_handlers = list(self._handlers.get(event.type, []))
                global_handlers = list(self._global_handlers)

            errors_count += await self._invoke_handlers_async(event, local_handlers)
            errors_count += await self._invoke_handlers_async(event, global_handlers)
        except Exception as e:
            errors_count += 1
            self._error_count += 1
            raise e
        finally:
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

    async def _invoke_handlers_async(
        self,
        event: Event,
        handlers: list[Callable[[Event], Awaitable[None]]],
    ) -> int:
        errors = 0

        for handler in handlers:
            try:
                await handler(event)
            except Exception as e:
                errors += 1
                logger.error(f"Handler error for {event.type}: {e}", exc_info=True)
                if not self._continue_on_handler_error:
                    raise e
        return errors

    async def _run_timer(self) -> None:
        assert self._queue is not None
        while self._active:
            # 使用更小的sleep间隔以便更快响应停止信号
            sleep_intervals = max(1, self._interval * 10)  # 将1秒分为10份
            for _ in range(sleep_intervals):
                if not self._active:
                    return
                await asyncio.sleep(self._interval / sleep_intervals)
            
            if not self._active:
                return
                
            await self._queue.put(Event(EventType.TIMER))

            # 定期向监控器发出统计快照
            if self._emit_stats_snapshot and self._stats_snapshot_every_ticks > 0:
                self._timer_tick_count = (self._timer_tick_count + 1) % self._stats_snapshot_every_ticks
                if self._timer_tick_count == 0:
                    await self._emit_stats_snapshot_to_monitors()

    # =============== 监控器通知与统计 ===============
    async def _notify_monitors_async(self, event: Event) -> None:
        logger.debug(f"AsyncEventBus通知监控器: {event.type}")
        with self._lock:
            monitors = list(self._monitors)

        for monitor in monitors:
            try:
                await monitor(event)
            except Exception as e:
                logger.error(f"Event monitor error: {e}", exc_info=True)

    def add_monitor(self, monitor: Callable[[Event], Awaitable[None]]) -> None:
        """添加事件监视器。"""
        with self._lock:
            if monitor not in self._monitors:
                self._monitors.append(monitor)
                logger.debug("Added event monitor")

    def remove_monitor(self, monitor: Callable[[Event], Awaitable[None]]) -> None:
        """移除事件监视器。"""
        with self._lock:
            if monitor in self._monitors:
                self._monitors.remove(monitor)
                logger.debug("Removed event monitor")

    def get_stats(self) -> dict[str, object]:
        """获取当前总线统计信息的浅拷贝快照。"""
        event_type_stats_copy: dict[str, dict[str, int]] = {k: v.copy() for k, v in self._event_type_stats.items()}
        queue_size = 0
        if self._queue is not None:
            try:
                queue_size = self._queue.qsize()
            except (NotImplementedError, AttributeError):
                queue_size = 0
        return {
            "name": self._name,
            "active": self._active,
            "queue_size": queue_size,
            "publish_event_count": self._publish_event_count,
            "processed_count": self._processed_count,
            "error_count": self._error_count,
            "dropped_count": self._dropped_count,
            "event_type_stats": event_type_stats_copy,
            "publish_timeout": self._publish_timeout,
        }

    async def _emit_stats_snapshot_to_monitors(self) -> None:
        try:
            snapshot = self.get_stats()
            await self._notify_monitors_async(Event("bus.stats", data=snapshot, source=self._name))
        except Exception as e:
            logger.error(f"Emit stats snapshot error: {e}", exc_info=True)

    # =============== 其他工具方法 ===============
    def get_bus_name(self) -> str:
        return self._name

    def set_continue_on_error(self, flag: bool) -> None:
        self._continue_on_handler_error = bool(flag)

    def enable_stats_snapshot(self, every_ticks: int = 60) -> None:
        if every_ticks <= 0:
            raise ValueError("every_ticks must be > 0")
        self._emit_stats_snapshot = True
        self._stats_snapshot_every_ticks = every_ticks
        self._timer_tick_count = 0

    def disable_stats_snapshot(self) -> None:
        self._emit_stats_snapshot = False
        self._stats_snapshot_every_ticks = 0
        self._timer_tick_count = 0

    # =============== 上下文管理器 ===============
    def __enter__(self) -> "AsyncEventBus":
        self.start()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> bool | None:
        self.stop()
        if exc_type:
            logger.error(f"EventBus context error: {exc_val}", exc_info=True)
        return None





if __name__ == '__main__':
    import time
    from src.core.event import Event, EventType

    # 创建异步事件总线
    bus = AsyncEventBus(name="MyAsyncBus", interval=1, stats_snapshot_every_ticks=60)

    # 只支持异步处理器
    async def async_handler(event: Event) -> None:
        print(f"异步处理: {event.type}")

    async def another_async_handler(event: Event) -> None:
        print(f"另一个异步处理: {event.type}")

    # 订阅事件
    bus.subscribe("custom.event", async_handler)
    bus.subscribe("custom.event", another_async_handler)

    # 启动和使用
    bus.start()
    bus.publish(Event("custom.event", data="hello"))
    
    # 等待异步处理完成
    time.sleep(1.0)
    
    # 停止事件总线
    bus.stop()

