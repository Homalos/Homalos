#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : event_bus.py
@Date       : 2025/9/8 09:53
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 事件总线类（支持同步+异步）
- 同步事件在单独线程消费 → 用线程池执行，不阻塞主线程。
- 异步事件在 asyncio 事件循环中消费 → 每个订阅者作为任务提交。
- 支持 start()/stop() 控制
- 支持信号处理（SIGINT / SIGTERM）
- 支持线程安全通过 RLock 确保。
- 支持信号处理（SIGINT / SIGTERM）可配置

解释：
1. 事件消费解耦
publish 只负责投递事件。
_sync_event_loop 和 _async_event_loop 专门负责消费，不会阻塞发布。

2. 异常处理更健壮
_safe_sync / _safe_async 捕获订阅者异常，保证不会影响其他订阅者。

3. 线程池大小可配置
EventBus(max_workers=20) 就能调整线程池。

4. 事件循环规范化
_get_or_create_event_loop 避免 asyncio.get_event_loop() 的弃用问题。

5. 线程安全
subscribe、unsubscribe、_dispatch 都加了 RLock，防止竞争条件。

6. 信号处理可配置
仅在主线程且允许注册时注册信号处理，避免在非主线程中注册信号处理。
在 stop() 中恢复原处理器并重置 _signal_registered。
_signal_handler 不做阻塞操作：仅注入关停事件，然后用后台线程调用 stop()
EventBus(register_signals=False) 就能关闭信号处理。
"""
import asyncio
import inspect
import signal
import threading
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from queue import Queue, Empty, Full

from src.core import trace_context
from src.core.event import Event, EventType
from src.utils.log.logger import get_logger


class EventBus(object):
    def __init__(self,
                 context: str = "EventBus",
                 max_workers: int=1000,
                 register_signals: bool = True,
                 auto_start: bool = True,  # 自动启动选项，与EventBus行为兼容
                 ) -> None:

        self.logger = get_logger(context=context)
        self._context: str = context  # 上下文(可传入服务名/模块名作为上下文)
        self._subscribers: dict[str, list] = defaultdict(list)  # 存储事件类型与订阅者的映射
        self._executor = ThreadPoolExecutor(max_workers=max_workers)  # 用线程池处理同步事件，max_workers：线程池大小
        self._queue: Queue[Event] = Queue()  # 用于同步事件的队列
        self._async_queue: asyncio.Queue[Event] | None = None  # 用于异步事件的队列
        self._lock = threading.RLock()
        self._queue_timeout: float = 1.0  # 从队列中获取事件超时时间(秒)
        self._sync_thread_quit_timeout: float = 2.0  # 同步任务退出超时时间(秒)

        # 控制运行状态
        self._active = False  # 事件总线是否激活
        self._stopped = threading.Event()  # 用于停止事件总线的事件

        # 同步任务的线程
        self._sync_thread = None

        # 异步任务的事件循环
        self._loop = None
        self._async_task: asyncio.Task | None = None

        # 是否注册过信号处理
        self._signal_registered = False
        self._register_signals = register_signals
        self._old_sigint = None
        self._old_sigterm = None

        # 自动启动功能
        if auto_start:
            self.start()

    # ===================== 启动 / 停止 =====================
    def start(self):
        """启动事件总线"""
        if self._active:
            self.logger.warning("EventBus 已经启动，跳过重复启动")
            return

        if self._loop is None:
            self._loop = self._get_or_create_event_loop()

        # 在事件循环中创建异步队列
        if self._async_queue is None:
            self._async_queue = asyncio.Queue()

        self._active = True
        self._stopped.clear()

        # 启动同步消费线程
        self._sync_thread = threading.Thread(target=self._sync_event_loop, daemon=True)
        self._sync_thread.start()

        if self._async_task is None:
            # 启动异步消费协程
            self._async_task = self._loop.create_task(self._async_event_loop(), name="AsyncEventLoop")

        # 注册信号处理器（仅主线程执行一次，可配置）
        if (self._register_signals and not self._signal_registered
                and threading.current_thread() is threading.main_thread()):
            try:
                self._old_sigint = signal.getsignal(signal.SIGINT)
                self._old_sigterm = signal.getsignal(signal.SIGTERM)
                signal.signal(signal.SIGINT, self._signal_handler)
                signal.signal(signal.SIGTERM, self._signal_handler)
                self._signal_registered = True
            except ValueError:
                # 非主线程调用时 signal.signal 会报错，忽略即可
                pass

        self.logger.info(f"{self._context} 已启动")

    def stop(self):
        """优雅关闭事件总线"""
        with self._lock:
            if not self._active:
                return

            if self._stopped.is_set():
                return

            self.logger.info("正在停止...")

            self._active = False
            # 标记停止
            self._stopped.set()

            # 通知同步/异步循环退出，给队列发送停止信号
            self._queue.put(Event(EventType.EVENT_BUS_SHUTDOWN))
            if self._loop and not self._loop.is_closed() and self._async_queue is not None:
                try:
                    self._loop.call_soon_threadsafe(self._async_queue.put_nowait, Event(EventType.EVENT_BUS_SHUTDOWN))
                except RuntimeError:
                    # 如果事件循环已经关闭，忽略错误
                    pass

            # 等待同步线程退出
            if self._sync_thread and self._sync_thread.is_alive():
                self._sync_thread.join(timeout=self._sync_thread_quit_timeout)

            # 优雅关闭线程池
            self._executor.shutdown(wait=True)

            # 取消未完成的异步任务
            if self._async_task and not self._async_task.done():
                self._async_task.cancel()

            # 恢复原有信号处理器
            if self._signal_registered and threading.current_thread() is threading.main_thread():
                try:
                    if self._old_sigint is not None:
                        signal.signal(signal.SIGINT, self._old_sigint)
                    if self._old_sigterm is not None:
                        signal.signal(signal.SIGTERM, self._old_sigterm)
                except ValueError:
                    pass
                finally:
                    self._signal_registered = False

            # 清理资源
            self._async_queue = None
            self._loop = None
            self._async_task = None
            self._sync_thread = None

            self.logger.info("已优雅停止")

    def _signal_handler(self, signum, _frame):
        """接收到 SIGINT/SIGTERM 时调用 stop"""
        self.logger.info(f"收到信号 {signum}，准备停止...")
        # 轻量化：仅注入停止事件并在后台线程触发 stop，避免在信号回调中做阻塞操作
        try:
            try:
                self._queue.put_nowait(Event(EventType.EVENT_BUS_SHUTDOWN))
            except Full:
                # 理论上无限队列不会满，这里仅防御
                pass

            if self._loop and self._async_queue is not None:
                try:
                    self._loop.call_soon_threadsafe(self._async_queue.put_nowait, Event(EventType.EVENT_BUS_SHUTDOWN))
                except (RuntimeError, asyncio.QueueFull):
                    # 事件循环已关闭，或异步队列已满（极少发生）
                    pass
        finally:
            threading.Thread(target=self.stop, daemon=True).start()

    # ===================== 状态查询 =====================
    def is_active(self) -> bool:
        """检查事件总线是否激活"""
        return self._active

    def get_subscriber_count(self, event_type: str | None = None) -> int:
        """获取订阅者数量"""
        with self._lock:
            if event_type:
                return len(self._subscribers.get(event_type, []))
            else:
                return sum(len(subscribers) for subscribers in self._subscribers.values())

    def get_registered_event_types(self) -> list[str]:
        """获取已注册的事件类型"""
        with self._lock:
            return list(self._subscribers.keys())

    # ===================== 基础功能 =====================
    def subscribe(self, event_type: str, subscriber, async_mode=False) -> None:
        """
        订阅事件，指定是否为异步处理
        :param event_type: 事件类型
        :param subscriber: 事件的订阅者
        :param async_mode: 是否异步模式
        :return:
        """
        with self._lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            self._subscribers[event_type].append((subscriber, async_mode))

    def unsubscribe(self, event_type, subscriber) -> None:
        """
        取消订阅事件
        :param event_type: 事件类型
        :param subscriber: 事件的订阅者
        :return:
        """
        with self._lock:
            if event_type in self._subscribers:
                self._subscribers[event_type] = [
                    (s, async_mode) for s, async_mode in self._subscribers[event_type] if s != subscriber
                ]
                # 如果列表为空，删除该事件类型
                if not self._subscribers[event_type]:
                    del self._subscribers[event_type]

    def publish(self, event: Event, async_mode=False) -> None:
        """
        发布事件（放入队列）
        :param event:
        :param async_mode: 是否异步模式
        :return:
        """
        if not self._active or self._stopped.is_set():
            self.logger.warning("已停止，忽略事件发布")
            return

        # 发布事件时自动继承 trace_id
        if not event.trace_id:
            # 如果事件本身没有 trace_id，尝试继承上下文 trace_id
            trace_id = trace_context.get_trace_id()
            if not trace_id:
                trace_id = trace_context.set_trace_id()  # 自动生成
            event.trace_id = trace_id

        if async_mode:
            if self._loop is not None and self._async_queue is not None:
                try:
                    self._loop.call_soon_threadsafe(self._async_queue.put_nowait, event)
                except RuntimeError as e:
                    self.logger.error(f"异步事件发布失败: {e}")
            else:
                self.logger.warning("异步事件发布失败：事件循环或队列未初始化")
        else:
            self._queue.put(event)

    # ===================== 内部循环 =====================
    def _sync_event_loop(self) -> None:
        """后台线程：消费同步事件"""
        try:
            while self._active and not self._stopped.is_set():
                try:
                    event = self._queue.get(block=True, timeout=self._queue_timeout)
                except Empty:
                    continue
                if event.event_type == EventType.EVENT_BUS_SHUTDOWN:  # 停止信号
                    self._dispatch(event)  # 先分发停止事件给订阅者
                    break
                self._dispatch(event)
        except Exception as e:
            self.logger.exception(f"同步事件循环异常: {e}")
        finally:
            self.logger.info("同步事件循环已退出")

    async def _async_event_loop(self) -> None:
        """后台协程：消费异步事件"""
        if self._async_queue is None:
            self.logger.warning("异步队列未初始化")
            return
            
        try:
            while self._active and not self._stopped.is_set():
                try:
                    event = await asyncio.wait_for(self._async_queue.get(), timeout=self._queue_timeout)
                    if event.event_type == EventType.EVENT_BUS_SHUTDOWN:  # 停止信号
                        self._dispatch(event)  # 先分发停止事件给订阅者
                        break
                    self._dispatch(event)
                except asyncio.TimeoutError:
                    # 超时继续循环，检查停止条件
                    continue
        except asyncio.CancelledError:
            # 任务被取消时优雅退出
            self.logger.info("异步事件循环被取消")
        except Exception as e:
            self.logger.exception(f"异步事件循环异常: {e}")
        finally:
            self.logger.info("异步事件循环已退出")

    # ===================== 分发逻辑 =====================
    def _dispatch(self, event: Event) -> None:
        """
        分发事件到订阅者
        :param event: 事件
        :return:
        """
        with self._lock:
            subscribers = list(self._subscribers.get(event.event_type, []))  # 拷贝快照，避免迭代时修改

        for subscriber, async_mode in subscribers:
            try:
                # 自动设置 trace_id 到上下文
                trace_context.set_trace_id(event.trace_id)

                if async_mode:
                    if not inspect.iscoroutinefunction(subscriber):
                        raise ValueError(f"异步订阅者必须是 async 函数: {subscriber}")
                    if self._loop is not None:
                        self._loop.create_task(self._safe_async(subscriber, event))
                else:
                    if inspect.iscoroutinefunction(subscriber):
                        raise ValueError(f"同步订阅者不能是 async 函数: {subscriber}")
                    self._executor.submit(self._safe_sync, subscriber, event)
            except Exception as e:
                self.logger.exception(f"事件 {event.event_type} 处理失败: {e}")

    # ===================== 安全执行封装 =====================
    def _safe_sync(self, subscriber, event):
        """同步订阅者安全执行"""
        try:
            # 在新线程中自动设置上下文 trace_id
            trace_context.set_trace_id(event.trace_id)
            subscriber(event)
        except Exception as e:
            self.logger.exception(f"同步订阅者 {subscriber} 执行失败: {e}")

    async def _safe_async(self, subscriber, event):
        """异步订阅者安全执行"""
        try:
            # 在异步任务中自动设置上下文 trace_id
            trace_context.set_trace_id(event.trace_id)
            await subscriber(event)
        except Exception as e:
            self.logger.exception(f"异步订阅者 {subscriber} 执行失败: {e}")

    # ===================== 事件循环管理 =====================
    @staticmethod
    def _get_or_create_event_loop():
        """获取或创建事件循环"""
        try:
            # 优先使用当前运行的事件循环
            return asyncio.get_running_loop()
        except RuntimeError:
            # 如果没有运行的事件循环，创建一个新的
            try:
                # 先尝试获取当前线程的事件循环
                loop = asyncio.get_event_loop()
                if loop.is_closed():
                    raise RuntimeError("Loop is closed")
                return loop
            except RuntimeError:
                # 创建新的事件循环
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                # 启动事件循环（在后台线程中）
                threading.Thread(target=loop.run_forever, daemon=True).start()
                return loop

