#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : base_strategy.py
@Date       : 2025/5/28 15:11
@Author     : Donny
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description:
"""
from abc import ABC, abstractmethod
from typing import Optional
import asyncio # Added for create_task and get_running_loop

from src.core.event import Event, EventType, OrderRequestEvent, CancelOrderRequestEvent, LogEvent # Ensure LogEvent is imported
from src.core.event_engine import EventEngine
from src.core.object import OrderRequest, CancelRequest, TickData, OrderData, TradeData, LogData # Ensure LogData is imported
from src.util.logger import log


class BaseStrategy(ABC):
    """
    策略基类
    """
    strategy_name: str = "BaseStrategy"
    authors: list[str] = []

    def __init__(self, strategy_id: str, event_engine: EventEngine, params: Optional[dict] = None):
        self.strategy_id: str = strategy_id
        self.event_engine: EventEngine = event_engine
        self.params: dict = params if params else {}
        self.active: bool = False # 策略是否激活运行

        # 注册希望处理的事件类型
        self._register_handlers()

    def _register_handlers(self):
        """内部方法，用于注册此策略感兴趣的事件类型。"""
        self.event_engine.register(EventType.TICK, self.on_event)
        self.event_engine.register(EventType.ORDER_UPDATE, self.on_event)
        self.event_engine.register(EventType.TRADE_UPDATE, self.on_event)
        # 策略也可以监听其他自定义事件

    def _unregister_handlers(self):
        """内部方法，用于注销事件处理器。"""
        self.event_engine.unregister(EventType.TICK, self.on_event)
        self.event_engine.unregister(EventType.ORDER_UPDATE, self.on_event)
        self.event_engine.unregister(EventType.TRADE_UPDATE, self.on_event)

    async def on_event(self, event: Event):
        """统一的事件处理入口，根据事件类型分发。"""
        if not self.active:
            return

        if event.type == EventType.TICK:
            await self.on_tick(event.data)
        elif event.type == EventType.ORDER_UPDATE:
            await self.on_order_update(event.data)
        elif event.type == EventType.TRADE_UPDATE:
            await self.on_trade(event.data)
        # 可以添加更多事件类型的处理

    @abstractmethod
    async def on_init(self):
        """策略初始化时调用。"""
        self.write_log("策略初始化完成。")
        pass

    @abstractmethod
    async def on_start(self):
        """策略启动时调用。"""
        self.active = True
        self.write_log("策略已启动。")
        pass

    @abstractmethod
    async def on_stop(self):
        """策略停止时调用。"""
        self.active = False
        self._unregister_handlers() # 停止时注销处理器
        self.write_log("策略已停止。")
        pass

    async def on_tick(self, tick: TickData):
        """处理Tick行情事件（如果策略订阅了）。"""
        pass

    async def on_order_update(self, order: OrderData):
        """处理订单回报事件。"""
        self.write_log(f"收到订单回报: {order.orderid}, 状态: {order.status.value}, 成交量: {order.traded}")
        pass

    async def on_trade(self, trade: TradeData):
        """处理成交回报事件。"""
        self.write_log(f"收到成交回报: {trade.orderid}, 方向: {trade.direction.value}, 价格: {trade.price}, 量: {trade.volume}")
        pass

    # --- 策略动作 --- 
    async def send_order(self, order_request: OrderRequest):
        """策略发送订单请求。"""
        if not self.active:
            self.write_log("策略未激活，无法发送订单。", "WARNING")
            return
        await self.event_engine.put(OrderRequestEvent(data=order_request))
        self.write_log(f"发送订单请求: {order_request.symbol}, 方向: {order_request.direction.value}, 类型: {order_request.type.value}, 价格: {order_request.price}, 量: {order_request.volume}")

    async def cancel_order(self, cancel_request: CancelRequest):
        """策略发送撤单请求。"""
        if not self.active:
            self.write_log("策略未激活，无法发送撤单。", "WARNING")
            return
        await self.event_engine.put(CancelOrderRequestEvent(data=cancel_request))
        self.write_log(f"发送撤单请求: {cancel_request.orderid}, 合约: {cancel_request.symbol}")

    def write_log(self, msg: str, level: str = "INFO"):
        """策略记录日志，通过事件引擎发布LogEvent。"""
        # 格式化日志消息，包含策略ID和策略名称作为上下文
        formatted_msg = f"[{self.strategy_id}|{self.strategy_name}] {msg}"
        
        # 创建 LogData 对象
        log_data = LogData(msg=formatted_msg, level=level, gateway_name=self.strategy_id) # 使用 strategy_id 作为 gateway_name 以便区分日志来源

        if self.event_engine:
            log_event = LogEvent(data=log_data)
            try:
                # 尝试获取当前正在运行的循环。
                loop = asyncio.get_running_loop()
                if loop.is_running():
                    # 创建一个任务以异步方式将日志事件放入队列
                    asyncio.create_task(self.event_engine.put(log_event))
                else:
                    # 如果循环没有运行（例如，在引擎停止期间的清理阶段）
                    # 使用 src.util.logger.log (如果已设置) 或 print 进行回退
                    # 为简化，此处直接print，但理想情况下应与EventEngine._log的回退逻辑一致
                    log(f"(LoopNotRunningInStrategyLog) {log_data.msg}", log_data.level)
            except RuntimeError:
                # 如果没有正在运行的事件循环（例如，从非异步线程调用或在引擎设置之前/之后）
                log(f"(NoLoopInStrategyLog) {log_data.msg}", log_data.level)
        else:
            # 如果事件引擎不存在，直接打印
            log(f"[{self.strategy_id}|{self.strategy_name}] (NoEventEngine) {msg}", level)

    # --- 其他辅助方法（可选）---
    def get_parameters(self) -> dict:
        """获取策略参数。"""
        return self.params

    def update_parameters(self, params: dict):
        """（热）更新策略参数。"""
        self.params.update(params)
        self.write_log(f"策略参数已更新: {self.params}") 