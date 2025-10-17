#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : trade_signal_handler.py
@Date       : 2025/10/17 16:00
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 交易信号处理器 - 协调策略信号到交易执行的完整流程
"""
import asyncio
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from threading import Lock
from typing import Dict, List, Optional, Any, Callable

from src.core.constants import Direction, Offset, Exchange, OrderStatus
from src.core.event import Event, EventType
from src.core.event_bus import EventBus
from src.core.object import OrderRequest, TradeData
from src.utils.log.logger import get_logger


@dataclass
class TradeSignal:
    """交易信号数据结构"""
    strategy_id: str
    instrument_id: str
    direction: Direction
    offset: Offset
    volume: int
    price: float
    exchange_id: Exchange
    signal_id: Optional[str] = None
    timestamp: Optional[datetime] = None
    extra_data: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if self.signal_id is None:
            self.signal_id = str(uuid.uuid4())
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class SignalExecutionRecord:
    """信号执行记录"""
    signal: TradeSignal
    order_request: Optional[OrderRequest] = None
    order_id: Optional[str] = None
    order_status: OrderStatus = OrderStatus.NO_TRADE_QUEUEING  # 使用有效的默认状态
    execution_status: str = "pending"  # pending, risk_checking, approved, rejected, submitted, filled, cancelled
    risk_check_result: Any = None
    submission_time: Optional[datetime] = None
    completion_time: Optional[datetime] = None
    error_message: Optional[str] = None
    trades: List[TradeData] = field(default_factory=list)


class TradeSignalHandler:
    """
    交易信号处理器
    
    功能：
    - 接收和处理策略交易信号
    - 协调信号验证、风控检查、订单提交的完整流程
    - 管理信号和订单的状态跟踪
    - 处理订单回报和成交回报
    - 向策略反馈执行结果
    """
    
    def __init__(self, event_bus: EventBus):
        self.logger = get_logger("TradeSignalHandler")
        self.event_bus = event_bus
        
        # 信号执行记录管理
        self.execution_records: Dict[str, SignalExecutionRecord] = {}  # signal_id -> record
        self.order_signal_map: Dict[str, str] = {}  # order_id -> signal_id
        self.strategy_signals: Dict[str, List[str]] = defaultdict(list)  # strategy_id -> signal_ids
        
        # 状态统计
        self.signal_statistics = {
            "total_signals": 0,
            "approved_signals": 0,
            "rejected_signals": 0,
            "filled_signals": 0,
            "cancelled_signals": 0,
            "error_signals": 0
        }
        
        # 线程锁
        self._lock = Lock()
        
        # 回调函数注册
        self._signal_callbacks: Dict[str, List[Callable]] = defaultdict(list)
        
        self.logger.info("交易信号处理器初始化完成")
    
    async def startup(self):
        """启动交易信号处理器"""
        self.logger.info("交易信号处理器启动中...")
        
        # 订阅事件
        self.event_bus.subscribe(EventType.STRATEGY_TRADE_SIGNAL, self._handle_strategy_signal)
        self.event_bus.subscribe(EventType.TRADE_ORDER_APPROVED, self._handle_order_approved)
        self.event_bus.subscribe(EventType.TRADE_ORDER_REJECTED, self._handle_order_rejected)
        self.event_bus.subscribe(EventType.ORDER_STATUS_UPDATE, self._handle_order_update)
        self.event_bus.subscribe(EventType.TRADE_EXECUTION, self._handle_trade_execution)
        
        self.logger.info("交易信号处理器启动完成")
    
    async def shutdown(self):
        """关闭交易信号处理器"""
        self.logger.info("交易信号处理器关闭中...")
        
        # 保存未完成的信号记录
        with self._lock:
            pending_count = sum(1 for record in self.execution_records.values() 
                              if record.execution_status not in ["filled", "cancelled", "rejected"])
        
        if pending_count > 0:
            self.logger.warning(f"系统关闭时还有 {pending_count} 个未完成的信号")
        
        self.logger.info("交易信号处理器已关闭")
    
    def register_signal_callback(self, callback_type: str, callback: Callable):
        """
        注册信号处理回调函数
        
        Args:
            callback_type: 回调类型 (signal_received, signal_approved, signal_rejected, signal_filled)
            callback: 回调函数
        """
        self._signal_callbacks[callback_type].append(callback)
        self.logger.debug(f"已注册 {callback_type} 回调函数")
    
    def process_trade_signal(self, signal: TradeSignal) -> str:
        """
        处理交易信号（同步接口）
        
        Args:
            signal: 交易信号
            
        Returns:
            str: 信号ID
        """
        # 确保signal_id已生成（在__post_init__中生成）
        if signal.signal_id is None:
            signal.signal_id = str(uuid.uuid4())
        
        signal_id = signal.signal_id  # 明确类型
        
        with self._lock:
            # 创建执行记录
            record = SignalExecutionRecord(signal=signal)
            self.execution_records[signal_id] = record
            self.strategy_signals[signal.strategy_id].append(signal_id)
            
            # 更新统计
            self.signal_statistics["total_signals"] += 1
            
            self.logger.info(f"收到交易信号: {signal.strategy_id} -> {signal.instrument_id} "
                           f"{signal.direction.value} {signal.offset.value} {signal.volume}@{signal.price}")
        
        # 触发回调
        self._trigger_callbacks("signal_received", signal)
        
        # 异步处理信号
        asyncio.create_task(self._process_signal_async(signal_id))
        
        return signal_id
    
    async def _process_signal_async(self, signal_id: str):
        """异步处理交易信号"""
        try:
            with self._lock:
                record = self.execution_records.get(signal_id)
                if not record:
                    self.logger.error(f"找不到信号记录: {signal_id}")
                    return
            
            signal = record.signal
            
            # 1. 验证信号有效性
            validation_result = self._validate_signal(signal)
            if not validation_result["valid"]:
                await self._handle_signal_error(signal_id, validation_result["reason"])
                return
            
            # 2. 创建订单请求
            order_request = self._create_order_request(signal)
            if not order_request:
                await self._handle_signal_error(signal_id, "创建订单请求失败")
                return
            
            # 3. 更新记录状态
            with self._lock:
                record.order_request = order_request
                record.execution_status = "risk_checking"
            
            # 4. 发送到风控模块
            self.logger.debug(f"发送信号到风控检查: {signal_id}")
            risk_event = Event(
                EventType.TRADE_SIGNAL,
                payload={
                    "signal_id": signal_id,
                    "strategy_id": signal.strategy_id,
                    "order_request": order_request
                }
            )
            self.event_bus.publish(risk_event)
            
        except Exception as e:
            self.logger.error(f"处理信号异常: {signal_id}, 错误: {e}", exc_info=True)
            await self._handle_signal_error(signal_id, f"处理异常: {str(e)}")
    
    def _validate_signal(self, signal: TradeSignal) -> Dict[str, Any]:
        """验证交易信号有效性"""
        try:
            # 基础参数检查
            if not signal.instrument_id or signal.instrument_id.strip() == "":
                return {"valid": False, "reason": "合约代码为空"}
            
            if signal.volume <= 0:
                return {"valid": False, "reason": f"订单量无效: {signal.volume}"}
            
            if signal.price <= 0:
                return {"valid": False, "reason": f"价格无效: {signal.price}"}
            
            # 检查方向和开平方向
            if signal.direction not in [Direction.LONG, Direction.SHORT]:
                return {"valid": False, "reason": f"方向无效: {signal.direction}"}
            
            if signal.offset not in [Offset.OPEN, Offset.CLOSE, Offset.CLOSE_TODAY, Offset.CLOSE_YESTERDAY]:
                return {"valid": False, "reason": f"开平方向无效: {signal.offset}"}
            
            return {"valid": True}
            
        except Exception as e:
            return {"valid": False, "reason": f"验证异常: {str(e)}"}
    
    def _create_order_request(self, signal: TradeSignal) -> Optional[OrderRequest]:
        """根据交易信号创建订单请求"""
        try:
            order_request = OrderRequest(
                instrument_id=signal.instrument_id,
                exchange_id=signal.exchange_id,
                direction=signal.direction,
                offset=signal.offset,
                volume=signal.volume,
                price=signal.price
            )
            return order_request
        except Exception as e:
            self.logger.error(f"创建订单请求失败: {e}", exc_info=True)
            return None
    
    async def _handle_signal_error(self, signal_id: str, error_message: str):
        """处理信号错误"""
        with self._lock:
            record = self.execution_records.get(signal_id)
            if record:
                record.execution_status = "error"
                record.error_message = error_message
                record.completion_time = datetime.now()
                
                # 更新统计
                self.signal_statistics["error_signals"] += 1
        
        self.logger.error(f"信号处理错误: {signal_id}, 原因: {error_message}")
        
        # 发送错误通知给策略
        await self._notify_strategy_signal_result(signal_id, "error", error_message)
    
    def _handle_strategy_signal(self, event: Event):
        """处理来自策略的交易信号事件"""
        try:
            payload = event.payload
            
            # 解析信号数据
            signal_data = payload.get("signal_data", {})
            strategy_id = payload.get("strategy_id")
            
            if not strategy_id:
                self.logger.error("策略信号缺少strategy_id")
                return
            
            # 构建交易信号对象
            signal = TradeSignal(
                strategy_id=strategy_id,
                instrument_id=signal_data.get("instrument_id"),
                direction=Direction(signal_data.get("direction")),
                offset=Offset(signal_data.get("offset")),
                volume=signal_data.get("volume"),
                price=signal_data.get("price"),
                exchange_id=Exchange(signal_data.get("exchange_id", "UNKNOWN")),
                extra_data=signal_data.get("extra_data", {})
            )
            
            # 处理信号
            signal_id = self.process_trade_signal(signal)
            self.logger.debug(f"策略信号已接收: {strategy_id} -> {signal_id}")
            
        except Exception as e:
            self.logger.error(f"处理策略信号事件异常: {e}", exc_info=True)
    
    def _handle_order_approved(self, event: Event):
        """处理订单风控通过事件"""
        try:
            payload = event.payload
            signal_id = payload.get("signal_id")
            order_request = payload.get("order_request")
            risk_check_result = payload.get("risk_check_result")
            
            if not signal_id:
                self.logger.warning("订单审批事件缺少signal_id")
                return
            
            with self._lock:
                record = self.execution_records.get(signal_id)
                if not record:
                    self.logger.warning(f"找不到信号记录: {signal_id}")
                    return
                
                record.execution_status = "approved"
                record.risk_check_result = risk_check_result
                
                # 更新统计
                self.signal_statistics["approved_signals"] += 1
            
            self.logger.info(f"信号风控通过: {signal_id}")
            
            # 提交订单到交易网关
            self._submit_order_to_gateway(signal_id, order_request)
            
            # 触发回调
            self._trigger_callbacks("signal_approved", record.signal)
            
        except Exception as e:
            self.logger.error(f"处理订单审批事件异常: {e}", exc_info=True)
    
    def _handle_order_rejected(self, event: Event):
        """处理订单风控拒绝事件"""
        try:
            payload = event.payload
            signal_id = payload.get("signal_id")
            risk_check_result = payload.get("risk_check_result")
            
            if not signal_id:
                self.logger.warning("订单拒绝事件缺少signal_id")
                return
            
            with self._lock:
                record = self.execution_records.get(signal_id)
                if not record:
                    self.logger.warning(f"找不到信号记录: {signal_id}")
                    return
                
                record.execution_status = "rejected"
                record.risk_check_result = risk_check_result
                record.error_message = risk_check_result.reason if risk_check_result else "风控拒绝"
                record.completion_time = datetime.now()
                
                # 更新统计
                self.signal_statistics["rejected_signals"] += 1
            
            self.logger.warning(f"信号被风控拒绝: {signal_id}, 原因: {record.error_message}")
            
            # 触发回调
            self._trigger_callbacks("signal_rejected", record.signal)
            
            # 通知策略
            asyncio.create_task(
                self._notify_strategy_signal_result(signal_id, "rejected", record.error_message)
            )
            
        except Exception as e:
            self.logger.error(f"处理订单拒绝事件异常: {e}", exc_info=True)
    
    def _submit_order_to_gateway(self, signal_id: str, order_request: OrderRequest):
        """提交订单到交易网关"""
        try:
            # 发送订单提交事件
            submit_event = Event(
                EventType.ORDER_SUBMIT_REQUEST,
                payload={
                    "signal_id": signal_id,
                    "order_request": order_request
                }
            )
            self.event_bus.publish(submit_event)
            
            with self._lock:
                record = self.execution_records.get(signal_id)
                if record:
                    record.execution_status = "submitted"
                    record.submission_time = datetime.now()
            
            self.logger.info(f"订单已提交到交易网关: {signal_id}")
            
        except Exception as e:
            self.logger.error(f"提交订单异常: {e}", exc_info=True)
    
    def _handle_order_update(self, event: Event):
        """处理订单状态更新事件"""
        try:
            payload = event.payload
            order_id = payload.get("order_id")
            order_status = payload.get("order_status")
            
            if not order_id:
                return
            
            # 通过订单ID找到对应的信号
            signal_id = self.order_signal_map.get(order_id)
            if not signal_id:
                # 可能是外部订单，不是我们处理的信号
                return
            
            with self._lock:
                record = self.execution_records.get(signal_id)
                if not record:
                    return
                
                record.order_id = order_id
                record.order_status = order_status
                
                # 根据订单状态更新执行状态
                if order_status == OrderStatus.ALL_TRADED:
                    record.execution_status = "filled"
                    record.completion_time = datetime.now()
                    self.signal_statistics["filled_signals"] += 1
                    
                    # 触发回调
                    self._trigger_callbacks("signal_filled", record.signal)
                    
                    # 通知策略
                    asyncio.create_task(
                        self._notify_strategy_signal_result(signal_id, "filled", "订单全部成交")
                    )
                    
                elif order_status == OrderStatus.CANCELED:
                    record.execution_status = "cancelled"
                    record.completion_time = datetime.now()
                    self.signal_statistics["cancelled_signals"] += 1
                    
                    # 通知策略
                    asyncio.create_task(
                        self._notify_strategy_signal_result(signal_id, "cancelled", "订单已撤销")
                    )
            
            self.logger.debug(f"订单状态更新: {order_id} -> {order_status.value if order_status else 'UNKNOWN'}")
            
        except Exception as e:
            self.logger.error(f"处理订单状态更新异常: {e}", exc_info=True)
    
    def _handle_trade_execution(self, event: Event):
        """处理成交回报事件"""
        try:
            payload = event.payload
            trade_data = payload.get("trade_data")
            
            if not trade_data or not hasattr(trade_data, 'order_id'):
                return
            
            order_id = trade_data.order_id
            signal_id = self.order_signal_map.get(order_id)
            
            if not signal_id:
                return
            
            with self._lock:
                record = self.execution_records.get(signal_id)
                if record:
                    record.trades.append(trade_data)
            
            self.logger.debug(f"收到成交回报: {order_id}, 成交量: {trade_data.volume}")
            
        except Exception as e:
            self.logger.error(f"处理成交回报异常: {e}", exc_info=True)
    
    async def _notify_strategy_signal_result(self, signal_id: str, status: str, message: str):
        """通知策略信号执行结果"""
        try:
            record = self.execution_records.get(signal_id)
            if not record:
                return
            
            # 发送结果通知事件给策略管理器
            notify_event = Event(
                EventType.STRATEGY_SIGNAL_RESULT,
                payload={
                    "strategy_id": record.signal.strategy_id,
                    "signal_id": signal_id,
                    "status": status,
                    "message": message,
                    "signal_data": {
                        "instrument_id": record.signal.instrument_id,
                        "direction": record.signal.direction.value,
                        "offset": record.signal.offset.value,
                        "volume": record.signal.volume,
                        "price": record.signal.price
                    }
                }
            )
            self.event_bus.publish(notify_event)
            
        except Exception as e:
            self.logger.error(f"通知策略结果异常: {e}", exc_info=True)
    
    def _trigger_callbacks(self, callback_type: str, signal: TradeSignal):
        """触发回调函数"""
        try:
            callbacks = self._signal_callbacks.get(callback_type, [])
            for callback in callbacks:
                try:
                    callback(signal)
                except Exception as e:
                    self.logger.error(f"回调函数执行异常: {callback_type}, {e}")
        except Exception as e:
            self.logger.error(f"触发回调异常: {e}")
    
    def get_signal_statistics(self) -> Dict[str, Any]:
        """获取信号统计信息"""
        with self._lock:
            stats = self.signal_statistics.copy()
            stats["active_signals"] = len([
                r for r in self.execution_records.values()
                if r.execution_status not in ["filled", "cancelled", "rejected", "error"]
            ])
            return stats
    
    def get_strategy_signals(self, strategy_id: str) -> List[Dict[str, Any]]:
        """获取指定策略的信号记录"""
        with self._lock:
            signal_ids = self.strategy_signals.get(strategy_id, [])
            signals = []
            
            for signal_id in signal_ids:
                record = self.execution_records.get(signal_id)
                if record:
                    signal_info = {
                        "signal_id": signal_id,
                        "instrument_id": record.signal.instrument_id,
                        "direction": record.signal.direction.value,
                        "offset": record.signal.offset.value,
                        "volume": record.signal.volume,
                        "price": record.signal.price,
                        "execution_status": record.execution_status,
                        "timestamp": record.signal.timestamp.isoformat() if record.signal.timestamp else None,
                        "order_id": record.order_id,
                        "error_message": record.error_message
                    }
                    signals.append(signal_info)
            
            return signals
    
    def cancel_signal(self, signal_id: str) -> bool:
        """取消交易信号"""
        try:
            with self._lock:
                record = self.execution_records.get(signal_id)
                if not record:
                    return False
                
                # 只能取消未提交或已提交但未成交的信号
                if record.execution_status in ["pending", "risk_checking", "approved", "submitted"]:
                    if record.order_id:
                        # 如果已有订单ID，发送撤单请求
                        cancel_event = Event(
                            EventType.ORDER_CANCEL_REQUEST,
                            payload={
                                "order_id": record.order_id,
                                "signal_id": signal_id
                            }
                        )
                        self.event_bus.publish(cancel_event)
                    else:
                        # 直接标记为取消
                        record.execution_status = "cancelled"
                        record.completion_time = datetime.now()
                        self.signal_statistics["cancelled_signals"] += 1
                    
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"取消信号异常: {e}", exc_info=True)
            return False
