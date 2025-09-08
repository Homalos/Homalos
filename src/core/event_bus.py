#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : event_bus.py
@Date       : 2025/9/8 09:53
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 事件总线类
同步事件在单独线程消费 → 用线程池执行，不阻塞主线程。
异步事件在 asyncio 循环中消费 → 每个订阅者作为任务提交。
线程安全通过 RLock 确保。

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
"""
import asyncio
import inspect
import threading
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from queue import Queue

from src.core.event import Event


class EventBus:
    def __init__(self, max_workers=1000) -> None:
        self._subscribers: dict[str, list] = defaultdict(list)  # 存储事件类型与订阅者的映射
        self.executor = ThreadPoolExecutor(max_workers=max_workers)  # 用线程池处理同步事件
        self.queue = Queue()  # 用于同步事件的队列
        self.async_queue = asyncio.Queue()  # 用于异步事件的队列
        self._lock = threading.RLock()
        self._publish_timeout: float = 1.0

        # 初始化异步任务的事件循环
        self.loop = self._get_or_create_event_loop()

        # 启动后台线程消费同步事件
        threading.Thread(target=self._sync_event_loop, daemon=True).start()

        # 启动后台协程消费异步事件
        self.loop.create_task(self._async_event_loop())

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
            self._subscribers[event_type] = [
                (s, async_mode) for s, async_mode in self._subscribers[event_type] if s != subscriber
            ]

    def publish(self, event: Event, async_mode=False) -> None:
        """
        发布事件（放入队列）
        :param event:
        :param async_mode: 是否异步模式
        :return:
        """
        if async_mode:
            self.async_queue.put_nowait(event)
        else:
            self.queue.put(event, block=True, timeout=self._publish_timeout)

    # ===================== 内部循环 =====================
    def _sync_event_loop(self) -> None:
        """后台线程：不断消费同步事件"""
        while True:
            event = self.queue.get()
            self._dispatch(event)

    async def _async_event_loop(self) -> None:
        """后台协程：不断消费异步事件"""
        while True:
            event = await self.async_queue.get()
            self._dispatch(event)

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
                if async_mode:
                    if not inspect.iscoroutinefunction(subscriber):
                        raise ValueError(f"异步订阅者必须是 async 函数: {subscriber}")
                    self.loop.create_task(self._safe_async(subscriber, event))
                else:
                    if inspect.iscoroutinefunction(subscriber):
                        raise ValueError(f"同步订阅者不能是 async 函数: {subscriber}")
                    self.executor.submit(self._safe_sync, subscriber, event)
            except Exception as e:
                print(f"[ERROR] 事件 {event.event_type} 处理失败: {e}")

    # ===================== 安全执行封装 =====================
    @staticmethod
    def _safe_sync(subscriber, event):
        """同步订阅者安全执行"""
        try:
            subscriber(event)
        except Exception as e:
            print(f"[ERROR] 同步订阅者 {subscriber} 执行失败: {e}")

    @staticmethod
    async def _safe_async(subscriber, event):
        """异步订阅者安全执行"""
        try:
            await subscriber(event)
        except Exception as e:
            print(f"[ERROR] 异步订阅者 {subscriber} 执行失败: {e}")

    # ===================== 事件循环管理 =====================
    @staticmethod
    def _get_or_create_event_loop():
        """获取或创建事件循环"""
        try:
            return asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop

