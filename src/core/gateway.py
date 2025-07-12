#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : gateway
@Date       : 2025/5/28 14:30
@Author     : Donny
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 交易网关的基本数据结构。
"""
import asyncio
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, Optional, Callable, Coroutine

from src.core.event import Event
from src.core.event_bus import EventBus
from src.core.logger import get_logger


logger = get_logger("BaseGateway")


class ThreadSafeCallback:
    """线程安全的回调辅助类，用于CTP API回调与Python事件循环的桥接"""
    
    def __init__(self, event_loop: Optional[asyncio.AbstractEventLoop] = None):
        """
        初始化对象。
        Args:
            event_loop (Optional[asyncio.AbstractEventLoop], optional): 事件循环对象。默认为 None。
        """
        self.event_loop = event_loop or asyncio.get_event_loop()  # 事件循环对象
        self.thread_pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="callback_")  # 线程池
        
        # 增强监控和统计
        self.success_count = 0  # 成功计数
        self.failure_count = 0  # 失败计数
        self.retry_count = 0    # 重试计数
        self.max_retries = 3    # 最大重试次数
        self.retry_delay = 0.1  # 重试延迟(秒)
    
    def schedule_async_task(self, coro: Coroutine) -> None:
        """线程安全地调度异步任务（增强版本）"""
        for attempt in range(self.max_retries + 1):
            try:
                # 检查事件循环状态
                if not self.event_loop or self.event_loop.is_closed():
                    logger.error("事件循环已关闭，无法调度异步任务")
                    self.failure_count += 1
                    return
                
                if self.event_loop.is_running():
                    # 事件循环正在运行，使用run_coroutine_threadsafe
                    future = asyncio.run_coroutine_threadsafe(coro, self.event_loop)
                    # 不等待结果，避免阻塞CTP回调线程
                    self.success_count += 1
                    if attempt > 0:
                        self.retry_count += 1
                    return
                else:
                    # 事件循环未运行，记录警告
                    logger.warning("事件循环未运行，无法调度异步任务")
                    self.failure_count += 1
                    return
                    
            except Exception as e:
                if attempt < self.max_retries:
                    logger.warning(f"调度异步任务失败，重试 {attempt + 1}/{self.max_retries}: {e}")
                    import time
                    time.sleep(self.retry_delay)
                else:
                    logger.error(f"调度异步任务最终失败: {e}")
                    self.failure_count += 1
    
    def schedule_callback(self, callback: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
        """线程安全地调度同步回调（增强版本）"""
        for attempt in range(self.max_retries + 1):
            try:
                # 检查事件循环状态
                if not self.event_loop or self.event_loop.is_closed():
                    logger.error("事件循环已关闭，无法调度回调")
                    self.failure_count += 1
                    return
                
                self.event_loop.call_soon_threadsafe(callback, *args, **kwargs)
                self.success_count += 1
                if attempt > 0:
                    self.retry_count += 1
                return
                
            except Exception as e:
                if attempt < self.max_retries:
                    logger.warning(f"调度回调失败，重试 {attempt + 1}/{self.max_retries}: {e}")
                    import time
                    time.sleep(self.retry_delay)
                else:
                    logger.error(f"调度回调最终失败: {e}")
                    self.failure_count += 1
    
    def get_statistics(self) -> Dict[str, int]:
        """获取统计信息"""
        return {
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "retry_count": self.retry_count,
            "total_attempts": self.success_count + self.failure_count
        }
    
    def close(self) -> None:
        """关闭线程池（增强版本）"""
        try:
            # 记录统计信息
            stats = self.get_statistics()
            if stats["total_attempts"] > 0:
                success_rate = (stats["success_count"] / stats["total_attempts"]) * 100
                logger.info(f"ThreadSafeCallback统计: 成功率 {success_rate:.1f}%, "
                           f"成功 {stats['success_count']}, 失败 {stats['failure_count']}, "
                           f"重试 {stats['retry_count']}")
            
            self.thread_pool.shutdown(wait=False)
        except Exception as e:
            logger.error(f"关闭线程池失败: {e}")


class BaseGateway(ABC):
    """
    抽象网关类用于外部系统连接。
    
    每个网关都应该继承这个类，
    并且应该有一个唯一的网关名称。
    """
    default_name: str = ""
    default_setting: Dict[str, Any] = {}

    def __init__(self, event_bus: EventBus, name: str) -> None:
        """初始化网关"""
        self.event_bus = event_bus  # 事件总线对象
        self.name = name  # 网关名称
        
        # 线程安全回调处理器
        self._callback_handler: Optional[ThreadSafeCallback] = None
        self._running = False
        
        # 初始化线程安全回调处理器
        self._init_callback_handler()

    def _init_callback_handler(self) -> None:
        """初始化线程安全回调处理器"""
        try:
            # 获取当前事件循环，如果没有则创建一个
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                # 没有运行中的事件循环，尝试获取默认事件循环
                loop = asyncio.get_event_loop()
            
            self._callback_handler = ThreadSafeCallback(loop)
            logger.debug(f"网关 {self.name} 线程安全回调处理器已初始化")
        except Exception as e:
            logger.error(f"初始化线程安全回调处理器失败: {e}")
            self._callback_handler = None

    def _schedule_async_task(self, coro: Coroutine) -> None:
        """线程安全地调度异步任务（供子类使用）"""
        if self._callback_handler:
            self._callback_handler.schedule_async_task(coro)
        else:
            logger.error(f"网关 {self.name} 回调处理器未初始化，无法调度任务")

    def _schedule_callback(self, callback: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
        """线程安全地调度同步回调（供子类使用）"""
        if self._callback_handler:
            self._callback_handler.schedule_callback(callback, *args, **kwargs)
        else:
            logger.error(f"网关 {self.name} 回调处理器未初始化，无法调度回调")

    def _safe_publish_event(self, event_type: str, data: Any) -> None:
        """线程安全地发布事件"""
        try:
            def publish_event():
                self.event_bus.publish(Event(event_type, data))
            
            self._schedule_callback(publish_event)
        except Exception as e:
            logger.error(f"网关 {self.name} 发布事件失败: {e}")

    def write_log(self, msg: str) -> None:
        """写日志（兼容性方法）"""
        logger.info(f"[{self.name}] {msg}")

    def write_error(self, msg: str, error: Dict[str, Any]) -> None:
        """写错误日志（兼容性方法）"""
        error_id = error.get("ErrorID", "N/A")
        error_msg = error.get("ErrorMsg", str(error))
        log_msg = f"{msg}，代码：{error_id}，信息：{error_msg}"
        logger.error(f"[{self.name}] {log_msg}")

    # 核心回调方法 - CTP网关兼容性接口
    def on_contract(self, contract: Any) -> None:
        """处理合约信息回调"""
        try:
            self._safe_publish_event("contract.updated", {
                "contract": contract,
                "gateway_name": self.name,
                "timestamp": __import__('time').time()
            })
            logger.debug(f"[{self.name}] 合约信息已发布: {getattr(contract, 'symbol', 'unknown')}")
        except Exception as e:
            logger.error(f"[{self.name}] 处理合约信息失败: {e}")

    def on_order(self, order: Any) -> None:
        """处理订单状态回调"""
        try:
            self._safe_publish_event("order.updated", order)
            order_id = getattr(order, 'orderid', 'unknown')
            status = getattr(order, 'status', 'unknown')
            logger.debug(f"[{self.name}] 订单状态已更新: {order_id} -> {status}")
        except Exception as e:
            logger.error(f"[{self.name}] 处理订单状态失败: {e}")

    def on_trade(self, trade: Any) -> None:
        """处理成交回报回调"""
        try:
            self._safe_publish_event("trade.updated", trade)
            trade_id = getattr(trade, 'trade_id', 'unknown')
            symbol = getattr(trade, 'symbol', 'unknown')
            volume = getattr(trade, 'volume', 0)
            price = getattr(trade, 'price', 0)
            logger.info(f"[{self.name}] 成交回报: {trade_id} {symbol} {volume}@{price}")
        except Exception as e:
            logger.error(f"[{self.name}] 处理成交回报失败: {e}")

    def on_account(self, account: Any) -> None:
        """处理账户信息回调"""
        try:
            self._safe_publish_event("account.updated", account)
            account_id = getattr(account, 'account_id', 'unknown')
            balance = getattr(account, 'balance', 0)
            logger.debug(f"[{self.name}] 账户信息已更新: {account_id} 余额:{balance}")
        except Exception as e:
            logger.error(f"[{self.name}] 处理账户信息失败: {e}")

    def on_position(self, position: Any) -> None:
        """处理持仓信息回调"""
        try:
            self._safe_publish_event("position.updated", position)
            symbol = getattr(position, 'symbol', 'unknown')
            volume = getattr(position, 'volume', 0)
            direction = getattr(position, 'direction', 'unknown')
            logger.debug(f"[{self.name}] 持仓信息已更新: {symbol} {direction} {volume}")
        except Exception as e:
            logger.error(f"[{self.name}] 处理持仓信息失败: {e}")

    @abstractmethod
    def connect(self, setting: Dict[str, Any]) -> None:
        """连接外部系统"""
        pass

    @abstractmethod
    def close(self) -> None:
        """关闭连接"""
        if self._callback_handler:
            self._callback_handler.close()
            self._callback_handler = None
        self._running = False

    def get_default_setting(self) -> Dict[str, Any]:
        """获取默认设置"""
        return self.default_setting.copy()

    def get_connection_status(self) -> Dict[str, Any]:
        """获取连接状态"""
        return {
            "name": self.name,
            "connected": False,
            "callback_handler_ready": self._callback_handler is not None
        }
