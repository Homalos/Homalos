#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : event_engine.py
@Date       : 2025/5/28 15:11
@Author     : Donny
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 负责异步事件的注册、排队和分发。
"""
import asyncio
from collections import defaultdict
from typing import Callable, Any, Coroutine, TypeVar

from src.core.event import Event, EventType, LogEvent # 确保LogData已定义
from src.core.object import LogData # 明确导入LogData
from src.util.logger import log, setup_logging

# 定义一个与基 Event 类绑定的 TypeVar
SpecificEvent = TypeVar('SpecificEvent', bound=Event)

class EventEngine:
    def __init__(self):
        setup_logging(service_name=__class__.__name__)
        # 处理程序列表将存储可调用函数。类型检查器可能需要在此处使用 `Any` 作为事件参数。
        # 如果我们要存储各种 SpecificEvent 类型的处理程序。
        # 类型安全由寄存器中的 SpecificEvent 和 _process 中的运行时调度来强制执行。
        self._handlers: defaultdict[EventType, list[Callable[[Any], Coroutine[Any, Any, None]]]] = defaultdict(list)
        self._event_queue: asyncio.Queue[Event] = asyncio.Queue()
        self._active: bool = False
        self._task: asyncio.Task | None = None # 用于保存事件处理循环的任务

    def is_active(self) -> bool:
        """检查事件引擎是否处于活动状态。"""
        return self._active

    # Updated handler type to use SpecificEvent
    def register(self, event_type: EventType, handler: Callable[[SpecificEvent], Coroutine[Any, Any, None]]):
        """
        注册事件处理器。
        处理器必须是一个异步函数 (async def) 并且其参数类型应为 Event 或其子类。
        """
        if not asyncio.iscoroutinefunction(handler):
            raise TypeError(f"事件处理器 {handler.__name__} 必须是异步函数 (async def)。")

        # 将 SpecificEvent 的处理程序附加到有效包含 Callable[[Event], ...] 的列表中
        # 这是可以接受的，因为 SpecificEvent 受 Event 绑定。
        # _process 方法确保处理程序接收预期特定类型的事件。
        # 如果严格类型检查器对处理程序与 List[Callable[[Event], ...]] 的差异提出异议，请使用 type: ignore。
        self._handlers[event_type].append(handler) # type: ignore
        self._log(f"处理器 {handler.__name__} 已注册处理事件类型 {event_type.value}")

    # 更新处理程序类型以使用 SpecificEvent 来保持一致性
    def unregister(self, event_type: EventType, handler: Callable[[SpecificEvent], Coroutine[Any, Any, None]]):
        """
        注销事件处理器。
        """
        try:
            # 处理程序身份应该适用于删除。
            self._handlers[event_type].remove(handler) # type: ignore
            self._log(f"处理器 {handler.__name__} 已从事件类型 {event_type.value} 注销")
        except ValueError:
            self._log(f"尝试注销处理器 {handler.__name__}失败，该处理器未在事件类型 {event_type.value} 中找到。", "WARNING")

    async def put(self, event: Event):
        """
        将事件放入队列。
        """
        if not self._active:
            self._log(f"警告：事件引擎未激活时尝试放入事件 {event.type.value}。事件将被忽略。")
            return
        await self._event_queue.put(event)

    async def _process(self, event: Event):
        """
        处理单个事件，调用所有已注册的处理器。
        """
        if event.type in self._handlers:
            for handler in self._handlers[event.type]:
                try:
                    # 处理程序需要 Event 的特定子类型（通过寄存器指定为 SpecificEvent）。
                    # 由于 event.type 匹配，因此"event"应该是该 SpecificEvent 子类型的实例。
                    # 此处"event"的静态类型是"Event"，它是兼容的。
                    asyncio.create_task(handler(event))
                except Exception as e:
                    self._log(f"调用处理器 {handler.__name__} 处理事件 {event.type.value} 时出错: {e}", level="ERROR")
        # else:
            # self._log(f"事件 {event.type.value} 没有已注册的处理器。")


    async def _run(self):
        """
        事件处理主循环。
        """
        self._log("事件引擎开始运行。")
        while self._active:
            try:
                event = await self._event_queue.get()
                if event: # 确保我们拿到了一个事件
                    await self._process(event)
                    self._event_queue.task_done() # 标记任务完成
            except asyncio.CancelledError:
                self._log("事件引擎主循环被取消。")
                break # 退出循环
            except Exception as e:
                self._log(f"事件引擎主循环发生错误: {e}", level="ERROR")
                # 可考虑在此处添加一些错误处理逻辑，例如短暂休眠

    def start(self):
        """
        启动事件引擎。
        """
        if not self._active:
            self._active = True
            # 创建并运行事件处理循环的任务
            self._task = asyncio.create_task(self._run())
            self._log("事件引擎已启动。")

    async def stop(self):
        """
        停止事件引擎。
        会等待队列中剩余事件处理完毕。
        """
        if self._active:
            self._log("事件引擎正在停止...")
            self._active = False # 首先标记为不活跃，阻止新事件进入处理逻辑

            # 给队列发送一个None信号或者特定停止事件来优雅地结束 _run 循环（如果需要）
            # 或者直接取消任务，但要确保能处理 CancelledError
            
            # 等待队列中的所有任务完成
            # 注意: 如果_run循环因为_active=False而自然退出，queue.join()可能不是必须的
            # 但如果_process中的任务是create_task创建的，则需要更复杂的机制来等待它们
            # 这里我们先假定_run会处理完当前队列中的事件然后因为_active=False退出

            if self._task:
                try:
                    # 给_run一些时间来处理剩余事件，然后取消它
                    # await asyncio.wait_for(self._event_queue.join(), timeout=5.0) # 等待队列清空
                    # print("事件队列已清空。")
                    self._task.cancel() # 取消主循环任务
                    await self._task # 等待任务确实被取消
                except asyncio.TimeoutError:
                    self._log("等待事件队列清空超时。强制停止。")
                except asyncio.CancelledError:
                    self._log("事件引擎任务已成功取消。") # 预期行为
                except Exception as e:
                    self._log(f"停止事件引擎时发生错误: {e}", level="ERROR")
            
            self._log("事件引擎已停止。")

    def _log(self, message: str, level: str = "INFO"):
        """
        内部日志记录，通过发送 LogEvent 来实现。
        """
        # 如果引擎未激活，或者队列不存在（例如在非常早期的初始化或非常晚的清理阶段），
        # 直接打印可能更安全，以避免尝试在无效状态下使用 self.put。
        if not self._active or not hasattr(self, '_event_queue') or self._event_queue is None:
            log(f"{message}", level)
            return

        log_data = LogData(msg=message, level=level, gateway_name="EventEngine")
        log_event = LogEvent(data=log_data)
        
        try:
            # 尝试获取当前正在运行的循环。这在引擎启动后，在异步上下文中应该是可用的。
            loop = asyncio.get_running_loop()
            if loop.is_running():
                # 创建一个任务以异步方式将日志事件放入队列
                # 这可以防止 _log 方法（通常是同步调用）阻塞。
                asyncio.create_task(self.put(log_event))
            else:
                # 如果循环没有运行（例如，在引擎停止期间的清理阶段）
                log(f"[{log_data.gateway_name}] (LoopNotRunningDuringLog) {log_data.msg}", log_data.level)
        except RuntimeError:
            # 如果没有正在运行的事件循环（例如，从非异步线程调用，或者在引擎完全启动之前/停止之后）
            log(f"[{log_data.gateway_name}] (NoLoopForLogEvent) {log_data.msg}", log_data.level)


# 示例用法 (通常在主程序中)
async def example_tick_handler(event: Event):
    if event.type == EventType.TICK:
        print(f"异步Tick处理器收到: {event.data}")
    await asyncio.sleep(0.1) # 模拟一些IO操作

def sync_order_handler(event: Event): # 同步处理器 - 当前设计不支持直接注册同步处理器
    # 如果需要同步处理，应将其包装在异步函数中，例如使用 loop.run_in_executor
    if event.type == EventType.ORDER_UPDATE:
        print(f"订单更新处理器收到: {event.data}")

async def main():
    engine = EventEngine()
    
    # 注册异步处理器
    engine.register(EventType.TICK, example_tick_handler)
    
    # 对于同步处理器，需要包装
    # loop = asyncio.get_event_loop()
    # async def async_wrapper_for_sync_order_handler(event: Event):
    #     await loop.run_in_executor(None, sync_order_handler, event)
    # engine.register(EventType.ORDER_UPDATE, async_wrapper_for_sync_order_handler)

    engine.start()

    # 模拟事件产生
    await engine.put(Event(type=EventType.TICK, data={"symbol": "BTC", "price": 50000}))
    await engine.put(Event(type=EventType.ORDER_UPDATE, data={"order_id": "123", "status": "FILLED"}))
    await engine.put(Event(type=EventType.TICK, data={"symbol": "ETH", "price": 4000}))
    
    await asyncio.sleep(1) # 给事件一些处理时间
    await engine.stop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("示例程序被中断。") 