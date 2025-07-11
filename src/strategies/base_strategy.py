#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos_v2
@FileName   : base_strategy.py
@Date       : 2025/7/6 22:30
@Author     : Donny
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 策略基类 - 适配MVP架构
"""
import asyncio
import threading
import time
from abc import ABC, abstractmethod
from collections import defaultdict
from typing import Optional, Dict, List, Any, Set

from src.core.event import Event, EventType, create_trading_event, create_market_event
from src.core.event_bus import EventBus
from src.core.logger import get_logger
from src.core.object import OrderRequest, TickData, OrderData, TradeData, BarData

logger = get_logger("BaseStrategy")


class BaseStrategy(ABC):
    """
    策略基类 - 适配新架构
    
    新架构特性：
    1. 事件驱动设计
    2. 自动风控集成
    3. 行情订阅管理
    4. 状态生命周期管理
    5. 策略性能统计
    """
    
    # 策略元信息
    strategy_name: str = "BaseStrategy"
    authors: List[str] = []
    version: str = "1.0.0"
    description: str = ""
    
    def __init__(self, strategy_id: str, event_bus: EventBus, params: Optional[Dict[str, Any]] = None):
        self.strategy_id: str = strategy_id
        self.event_bus: EventBus = event_bus
        self.params: Dict[str, Any] = params if params else {}
        
        # 事件循环引用（用于跨线程异步调用）
        self.main_loop: Optional[asyncio.AbstractEventLoop] = None
        self.main_thread_id: Optional[int] = None
        
        # 策略状态
        self.active: bool = False
        self.initialized: bool = False
        self.start_time: Optional[float] = None
        self.stop_time: Optional[float] = None
        
        # 订阅管理
        self.subscribed_symbols: Set[str] = set()
        self.tick_cache: Dict[str, TickData] = {}
        self.bar_cache: Dict[str, Dict[str, BarData]] = defaultdict(dict)  # symbol -> interval -> bar
        
        # 交易记录
        self.pending_orders: Dict[str, OrderData] = {}
        self.filled_orders: Dict[str, TradeData] = {}
        
        # 性能统计
        self.stats = {
            "total_orders": 0,
            "filled_orders": 0,
            "total_pnl": 0.0,
            "win_count": 0,
            "loss_count": 0,
            "last_trade_time": None
        }
        
        # 注册事件处理器
        self._setup_event_handlers()
    
    def _setup_event_handlers(self):
        """设置事件处理器"""
        # 订阅与策略相关的事件
        self.event_bus.subscribe(f"market.tick.{self.strategy_id}", self._handle_tick_event)
        self.event_bus.subscribe(f"market.bar.{self.strategy_id}", self._handle_bar_event)
        self.event_bus.subscribe(EventType.ORDER_FILLED, self._handle_trade_event)
        self.event_bus.subscribe(EventType.ORDER_CANCELLED, self._handle_order_event)
        self.event_bus.subscribe(EventType.RISK_REJECTED, self._handle_risk_rejected)
    
    def _handle_tick_event(self, event: Event):
        """处理Tick事件"""
        tick_data = event.data
        if isinstance(tick_data, TickData):
            # 更新缓存
            self.tick_cache[tick_data.symbol] = tick_data
            
            # 添加调试日志
            self.write_log(f"收到tick事件: {tick_data.symbol} {tick_data.last_price} 事件类型:{event.type}", "DEBUG")
            
            # 安全地调用策略的tick处理
            self._safe_call_async(self.on_tick(tick_data))
    
    def _handle_bar_event(self, event: Event):
        """处理Bar事件"""
        bar_data = event.data
        if isinstance(bar_data, BarData):
            # 更新缓存
            interval = bar_data.interval.value if bar_data.interval else '1m'
            self.bar_cache[bar_data.symbol][interval] = bar_data
            
            # 安全地调用策略的bar处理
            self._safe_call_async(self.on_bar(bar_data))
    
    def _handle_trade_event(self, event: Event):
        """处理成交事件"""
        trade_data = event.data
        if isinstance(trade_data, TradeData):
            # 检查是否是本策略的成交
            if trade_data.orderid in self.pending_orders:
                self.filled_orders[trade_data.trade_id] = trade_data
                
                # 更新统计
                self.stats["filled_orders"] += 1
                self.stats["last_trade_time"] = time.time()
                
                # 简单的盈亏统计（需要通过其他方式计算）
                # 这里可以根据价格和持仓计算盈亏
                
                # 调用策略的成交处理
                asyncio.create_task(self.on_trade(trade_data))
    
    def _handle_order_event(self, event: Event):
        """处理订单事件"""
        order_data = event.data
        if isinstance(order_data, OrderData):
            # 检查是否是本策略的订单
            if order_data.orderid in self.pending_orders:
                # 调用策略的订单处理
                asyncio.create_task(self.on_order(order_data))
    
    def _handle_risk_rejected(self, event: Event):
        """处理风控拒绝事件"""
        data = event.data
        # 可以在这里添加风控拒绝的处理逻辑
        self.write_log(f"订单被风控拒绝: {data.get('reasons', [])}", "WARNING")

    def _safe_call_async(self, coro):
        """安全地调用异步方法 - 改进的线程安全版本"""
        try:
            # 方法1: 优先尝试获取当前线程的事件循环
            current_loop = asyncio.get_running_loop()
            current_loop.create_task(coro)
            return
        except RuntimeError:
            pass
        
        # 方法2: 如果有保存的主线程事件循环，使用线程安全调用
        if self.main_loop and not self.main_loop.is_closed():
            try:
                current_thread_id = threading.get_ident()
                if current_thread_id == self.main_thread_id:
                    # 同一线程，直接创建任务
                    self.main_loop.create_task(coro)
                else:
                    # 不同线程，使用线程安全方式
                    self.main_loop.call_soon_threadsafe(
                        lambda: self.main_loop.create_task(coro)
                    )
                return
            except Exception as e:
                self.write_log(f"主线程事件循环调用失败: {e}", "WARNING")
        
        # 方法3: 同步回退 - 使用同步版本的处理器
        try:
            self.write_log("使用同步回退处理事件", "DEBUG")
            self._sync_fallback_handler(coro)
        except Exception as e:
                         self.write_log(f"同步回退失败: {e}", "ERROR")
    
    def _sync_fallback_handler(self, coro):
        """同步回退处理器 - 当无法使用异步时的备用方案"""

        # 检查协程的实际方法
        if hasattr(coro, 'cr_frame') and coro.cr_frame:
            func_name = coro.cr_frame.f_code.co_name
            if func_name == 'on_tick' and hasattr(coro, 'cr_frame'):
                # 提取tick_data参数
                tick_data = None
                try:
                    # 从协程的局部变量中获取tick_data
                    if 'tick' in coro.cr_frame.f_locals:
                        tick_data = coro.cr_frame.f_locals['tick']
                    elif 'tick_data' in coro.cr_frame.f_locals:
                        tick_data = coro.cr_frame.f_locals['tick_data']
                    
                    if tick_data:
                        self._sync_on_tick(tick_data)
                        return
                except Exception as e:
                    self.write_log(f"提取tick_data失败: {e}", "DEBUG")
        
        # 如果无法识别或提取参数，关闭协程
        try:
            coro.close()
        except:
            pass
        self.write_log("使用同步回退但无法处理该协程类型", "WARNING")
    
    def _sync_on_tick(self, tick_data: TickData):
        """同步版本的tick处理 - 子类可重写提供同步逻辑"""
        # 默认实现：记录日志
        self.write_log(f"同步处理tick: {tick_data.symbol} @ {tick_data.last_price}", "DEBUG")
        
        # 这里可以添加基本的交易逻辑，比如检查条件并下单
        # 子类应该重写这个方法来实现具体的同步交易逻辑
    
    # ============ 生命周期方法 ============
    
    async def initialize(self):
        """策略初始化"""
        if self.initialized:
            return
        
        try:
            # 保存主线程的事件循环引用
            try:
                self.main_loop = asyncio.get_running_loop()
                self.main_thread_id = threading.get_ident()
                self.write_log(f"保存主线程事件循环: 线程ID={self.main_thread_id}", "DEBUG")
            except RuntimeError:
                self.write_log("未找到运行中的事件循环，将使用同步回退", "WARNING")
            
            await self.on_init()
            self.initialized = True
            self.write_log(f"策略 {self.strategy_id} 初始化完成")
        except Exception as e:
            self.write_log(f"策略初始化失败: {e}", "ERROR")
            raise
    
    async def start(self):
        """启动策略"""
        if not self.initialized:
            await self.initialize()
        
        if self.active:
            self.write_log("策略已在运行中", "WARNING")
            return
        
        try:
            await self.on_start()
            self.active = True
            self.start_time = time.time()
            self.write_log(f"策略 {self.strategy_id} 启动成功")
        except Exception as e:
            self.write_log(f"策略启动失败: {e}", "ERROR")
            raise
    
    async def stop(self):
        """停止策略"""
        if not self.active:
            self.write_log("策略未在运行", "WARNING")
            return
        
        try:
            await self.on_stop()
            self.active = False
            self.stop_time = time.time()
            
            # 取消所有订阅
            if self.subscribed_symbols:
                await self.unsubscribe_symbols(list(self.subscribed_symbols))
            
            self.write_log(f"策略 {self.strategy_id} 停止成功")
        except Exception as e:
            self.write_log(f"策略停止失败: {e}", "ERROR")
            raise
    
    # ============ 抽象方法 - 子策略必须实现 ============
    
    @abstractmethod
    async def on_init(self) -> None:
        """策略初始化时调用"""
        pass
    
    @abstractmethod
    async def on_start(self):
        """策略启动时调用"""
        pass
    
    @abstractmethod
    async def on_stop(self):
        """策略停止时调用"""
        pass
    
    @abstractmethod
    async def on_tick(self, tick: TickData):
        """处理Tick行情事件"""
        pass
    
    async def on_bar(self, bar: BarData):
        """处理Bar行情事件（可选实现）"""
        pass
    
    async def on_order(self, order: OrderData):
        """处理订单回报事件（可选实现）"""
        pass
    
    async def on_trade(self, trade: TradeData):
        """处理成交回报事件（可选实现）"""
        pass
    
    # ============ 交易接口 ============
    
    async def send_order(self, order_request: OrderRequest) -> Optional[str]:
        """发送订单请求"""
        try:
            # 发布下单信号给交易引擎
            self.event_bus.publish(create_trading_event(
                EventType.STRATEGY_SIGNAL,
                {
                    "action": "place_order",
                    "order_request": order_request,
                    "strategy_id": self.strategy_id
                },
                f"Strategy_{self.strategy_id}"
            ))
            
            # 更新统计
            self.stats["total_orders"] += 1
            
            self.write_log(f"发送订单请求: {order_request.symbol} {order_request.direction.value} {order_request.volume}@{order_request.price}")
            
            # 返回策略ID（实际订单ID会在订单回报中获得）
            return self.strategy_id
            
        except Exception as e:
            self.write_log(f"发送订单失败: {e}", "ERROR")
            return None
    
    async def cancel_order(self, order_id: str):
        """取消指定订单"""
        try:
            # 发布撤单信号给交易引擎
            self.event_bus.publish(create_trading_event(
                EventType.STRATEGY_SIGNAL,
                {
                    "action": "cancel_order",
                    "order_id": order_id,
                    "strategy_id": self.strategy_id
                },
                f"Strategy_{self.strategy_id}"
            ))
            
            self.write_log(f"发送撤单请求: {order_id}")
            
        except Exception as e:
            self.write_log(f"撤单失败: {e}", "ERROR")
    
    # ============ 行情订阅接口 ============
    
    async def subscribe_symbols(self, symbols: List[str]):
        """订阅行情数据"""
        try:
            # 发布订阅请求
            self.event_bus.publish(create_market_event(
                "data.subscribe",
                {"symbols": symbols, "strategy_id": self.strategy_id},
                f"Strategy_{self.strategy_id}"
            ))
            
            # 更新订阅列表
            self.subscribed_symbols.update(symbols)
            
            self.write_log(f"订阅行情: {symbols}")
            
        except Exception as e:
            self.write_log(f"订阅行情失败: {e}", "ERROR")
    
    async def unsubscribe_symbols(self, symbols: List[str]):
        """取消订阅行情数据"""
        try:
            # 发布取消订阅请求
            self.event_bus.publish(create_market_event(
                "data.unsubscribe",
                {"symbols": symbols, "strategy_id": self.strategy_id},
                f"Strategy_{self.strategy_id}"
            ))
            
            # 更新订阅列表
            self.subscribed_symbols.difference_update(symbols)
            
            self.write_log(f"取消订阅行情: {symbols}")
            
        except Exception as e:
            self.write_log(f"取消订阅失败: {e}", "ERROR")
    
    # ============ 数据访问接口 ============
    
    def get_latest_tick(self, symbol: str) -> Optional[TickData]:
        """获取最新Tick数据"""
        return self.tick_cache.get(symbol)
    
    def get_latest_bar(self, symbol: str, interval: str = "1m") -> Optional[BarData]:
        """获取最新Bar数据"""
        return self.bar_cache.get(symbol, {}).get(interval)
    
    def get_parameter(self, key: str, default: Any = None) -> Any:
        """获取策略参数"""
        return self.params.get(key, default)
    
    def set_parameter(self, key: str, value: Any):
        """设置策略参数"""
        self.params[key] = value
    
    # ============ 工具方法 ============
    
    def write_log(self, msg: str, level: str = "INFO"):
        """写日志"""
        log_msg = f"[{self.strategy_id}] {msg}"
        
        if level == "DEBUG":
            logger.debug(log_msg)
        elif level == "INFO":
            logger.info(log_msg)
        elif level == "WARNING":
            logger.warning(log_msg)
        elif level == "ERROR":
            logger.error(log_msg)
        else:
            logger.info(log_msg)
    
    def get_strategy_stats(self) -> Dict[str, Any]:
        """获取策略统计信息"""
        runtime = None
        if self.start_time:
            if self.stop_time:
                runtime = self.stop_time - self.start_time
            elif self.active:
                runtime = time.time() - self.start_time
        
        win_rate = 0.0
        if self.stats["win_count"] + self.stats["loss_count"] > 0:
            win_rate = self.stats["win_count"] / (self.stats["win_count"] + self.stats["loss_count"])
        
        return {
            "strategy_id": self.strategy_id,
            "strategy_name": self.strategy_name,
            "active": self.active,
            "initialized": self.initialized,
            "runtime": runtime,
            "subscribed_symbols": list(self.subscribed_symbols),
            "stats": {
                **self.stats,
                "win_rate": win_rate
            }
        }
    
    def __str__(self) -> str:
        return f"Strategy({self.strategy_id}, {self.strategy_name}, active={self.active})"
    
    def __repr__(self) -> str:
        return self.__str__()
