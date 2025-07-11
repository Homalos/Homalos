#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos_v2
@FileName   : performance_monitor.py
@Date       : 2025/1/15 16:00
@Author     : Donny
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 性能监控模块 - 实时监控系统和策略性能指标
"""
import asyncio
import psutil
import time
import threading
from collections import defaultdict, deque
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

from src.core.event_bus import EventBus
from src.config.config_manager import ConfigManager
from src.core.event import Event, create_log_event
from src.core.logger import get_logger

logger = get_logger("PerformanceMonitor")


@dataclass
class PerformanceMetrics:
    """性能指标数据类"""
    strategy_id: str
    
    # 延迟指标
    order_latencies: deque = field(default_factory=lambda: deque(maxlen=1000))
    avg_order_latency: float = 0.0
    max_order_latency: float = 0.0
    min_order_latency: float = float('inf')
    
    # 交易指标
    total_orders: int = 0
    successful_orders: int = 0
    failed_orders: int = 0
    total_trades: int = 0
    
    # 盈亏指标
    total_pnl: float = 0.0
    max_drawdown: float = 0.0
    win_count: int = 0
    loss_count: int = 0
    
    # 性能指标
    tick_processing_rate: float = 0.0
    last_tick_time: float = 0.0
    tick_count: int = 0
    
    # 时间戳
    start_time: float = field(default_factory=time.time)
    last_update: float = field(default_factory=time.time)


@dataclass
class SystemMetrics:
    """系统性能指标"""
    # CPU和内存
    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    memory_percent: float = 0.0
    
    # 系统指标
    active_strategies: int = 0
    total_events: int = 0
    event_processing_rate: float = 0.0
    
    # 网络和延迟
    network_latency: float = 0.0
    system_uptime: float = 0.0
    
    # 时间戳
    timestamp: float = field(default_factory=time.time)


class PerformanceMonitor:
    """性能监控器 - 实时监控系统和策略性能"""
    
    def __init__(self, event_bus: EventBus, config: ConfigManager):
        self.event_bus = event_bus
        self.config = config
        
        # 性能数据存储
        self.strategy_metrics: Dict[str, PerformanceMetrics] = {}
        self.system_metrics: SystemMetrics = SystemMetrics()
        self.metrics_history: List[SystemMetrics] = []
        
        # 监控配置
        self.monitoring_enabled = config.get("monitoring.enabled", True)
        self.metrics_interval = config.get("monitoring.metrics_interval", 10)
        self.max_history_size = 1000
        
        # 性能阈值
        self.thresholds = {
            "order_latency_ms": config.get("monitoring.thresholds.order_latency_ms", 10),
            "tick_processing_rate": config.get("monitoring.thresholds.tick_processing_rate", 1000),
            "memory_usage_mb": config.get("monitoring.thresholds.memory_usage_mb", 500),
            "cpu_usage_percent": config.get("monitoring.thresholds.cpu_usage_percent", 80)
        }
        
        # 监控状态
        self._running = False
        self._monitor_task: Optional[asyncio.Task] = None
        self._stats_lock = threading.Lock()
        
        # 设置事件处理器
        self._setup_event_handlers()
        
        logger.info("性能监控器初始化完成")
    
    def _setup_event_handlers(self) -> None:
        """设置事件处理器"""
        try:
            # 策略性能事件
            self.event_bus.subscribe("strategy.order_placed", self._handle_order_placed)
            self.event_bus.subscribe("strategy.order_filled", self._handle_order_filled)
            self.event_bus.subscribe("strategy.trade_executed", self._handle_trade_executed)
            
            # 市场数据事件
            self.event_bus.subscribe("market.tick", self._handle_tick_processed)
            
            # 系统事件
            self.event_bus.subscribe("system.event_processed", self._handle_event_processed)
            
            logger.info("性能监控事件处理器已注册")
        except Exception as e:
            logger.error(f"设置性能监控事件处理器失败: {e}")
    
    def start_monitoring(self) -> None:
        """启动性能监控"""
        if self._running or not self.monitoring_enabled:
            return
        
        self._running = True
        self._monitor_task = asyncio.create_task(self._monitoring_loop())
        logger.info("性能监控已启动")
    
    def stop_monitoring(self) -> None:
        """停止性能监控"""
        if not self._running:
            return
        
        self._running = False
        if self._monitor_task:
            self._monitor_task.cancel()
        
        logger.info("性能监控已停止")
    
    async def _monitoring_loop(self) -> None:
        """监控主循环"""
        try:
            while self._running:
                # 收集系统指标
                await self._collect_system_metrics()
                
                # 检查性能阈值
                self._check_performance_thresholds()
                
                # 更新策略指标
                self._update_strategy_metrics()
                
                # 保存历史数据
                self._save_metrics_history()
                
                # 等待下次监控
                await asyncio.sleep(self.metrics_interval)
                
        except asyncio.CancelledError:
            logger.info("性能监控循环已停止")
        except Exception as e:
            logger.error(f"性能监控循环异常: {e}")
    
    async def _collect_system_metrics(self) -> None:
        """收集系统性能指标"""
        try:
            # CPU和内存使用率
            self.system_metrics.cpu_percent = psutil.cpu_percent(interval=0.1)
            memory_info = psutil.virtual_memory()
            self.system_metrics.memory_mb = memory_info.used / 1024 / 1024
            self.system_metrics.memory_percent = memory_info.percent
            
            # 活跃策略数量
            self.system_metrics.active_strategies = len(self.strategy_metrics)
            
            # 更新时间戳
            self.system_metrics.timestamp = time.time()
            
        except Exception as e:
            logger.error(f"收集系统指标失败: {e}")
    
    def _check_performance_thresholds(self) -> None:
        """检查性能阈值并发送告警"""
        try:
            # 检查内存使用
            if self.system_metrics.memory_mb > self.thresholds["memory_usage_mb"]:
                self._send_performance_alert(
                    "high_memory_usage",
                    f"内存使用过高: {self.system_metrics.memory_mb:.1f}MB > {self.thresholds['memory_usage_mb']}MB"
                )
            
            # 检查CPU使用
            if self.system_metrics.cpu_percent > self.thresholds["cpu_usage_percent"]:
                self._send_performance_alert(
                    "high_cpu_usage",
                    f"CPU使用过高: {self.system_metrics.cpu_percent:.1f}% > {self.thresholds['cpu_usage_percent']}%"
                )
            
            # 检查策略延迟
            for strategy_id, metrics in self.strategy_metrics.items():
                if metrics.avg_order_latency > self.thresholds["order_latency_ms"] / 1000:
                    self._send_performance_alert(
                        "high_order_latency",
                        f"策略 {strategy_id} 订单延迟过高: {metrics.avg_order_latency*1000:.1f}ms"
                    )
                    
        except Exception as e:
            logger.error(f"检查性能阈值失败: {e}")
    
    def _send_performance_alert(self, alert_type: str, message: str) -> None:
        """发送性能告警"""
        try:
            alert_event = create_log_event(
                "performance.alert",
                {
                    "alert_type": alert_type,
                    "message": message,
                    "timestamp": time.time(),
                    "system_metrics": self.system_metrics.__dict__
                },
                "PerformanceMonitor"
            )
            
            self.event_bus.publish(alert_event)
            logger.warning(f"性能告警: {message}")
            
        except Exception as e:
            logger.error(f"发送性能告警失败: {e}")
    
    def _update_strategy_metrics(self) -> None:
        """更新策略性能指标"""
        current_time = time.time()
        
        with self._stats_lock:
            for strategy_id, metrics in self.strategy_metrics.items():
                # 更新平均延迟
                if metrics.order_latencies:
                    metrics.avg_order_latency = sum(metrics.order_latencies) / len(metrics.order_latencies)
                    metrics.max_order_latency = max(metrics.order_latencies)
                    metrics.min_order_latency = min(metrics.order_latencies)
                
                # 更新tick处理速率
                if metrics.last_tick_time > 0:
                    time_diff = current_time - metrics.last_tick_time
                    if time_diff > 0:
                        metrics.tick_processing_rate = metrics.tick_count / time_diff
                
                # 更新时间戳
                metrics.last_update = current_time
    
    def _save_metrics_history(self) -> None:
        """保存指标历史"""
        try:
            # 保存系统指标历史
            self.metrics_history.append(SystemMetrics(**self.system_metrics.__dict__))
            
            # 限制历史数据大小
            if len(self.metrics_history) > self.max_history_size:
                self.metrics_history = self.metrics_history[-self.max_history_size:]
                
        except Exception as e:
            logger.error(f"保存指标历史失败: {e}")
    
    def record_order_latency(self, strategy_id: str, latency: float) -> None:
        """记录订单延迟"""
        with self._stats_lock:
            if strategy_id not in self.strategy_metrics:
                self.strategy_metrics[strategy_id] = PerformanceMetrics(strategy_id=strategy_id)
            
            metrics = self.strategy_metrics[strategy_id]
            metrics.order_latencies.append(latency)
            metrics.total_orders += 1
    
    def record_strategy_performance(self, strategy_id: str, metrics: Dict[str, Any]) -> None:
        """记录策略性能数据"""
        with self._stats_lock:
            if strategy_id not in self.strategy_metrics:
                self.strategy_metrics[strategy_id] = PerformanceMetrics(strategy_id=strategy_id)
            
            strategy_metrics = self.strategy_metrics[strategy_id]
            
            # 更新各项指标
            for key, value in metrics.items():
                if hasattr(strategy_metrics, key):
                    setattr(strategy_metrics, key, value)
    
    def get_performance_summary(self, strategy_id: str) -> Dict[str, Any]:
        """获取策略性能摘要"""
        with self._stats_lock:
            if strategy_id not in self.strategy_metrics:
                return {}
            
            metrics = self.strategy_metrics[strategy_id]
            
            # 计算胜率
            win_rate = 0.0
            total_trades = metrics.win_count + metrics.loss_count
            if total_trades > 0:
                win_rate = metrics.win_count / total_trades
            
            # 计算运行时间
            runtime = time.time() - metrics.start_time
            
            return {
                "strategy_id": strategy_id,
                "runtime_seconds": runtime,
                "order_performance": {
                    "total_orders": metrics.total_orders,
                    "successful_orders": metrics.successful_orders,
                    "failed_orders": metrics.failed_orders,
                    "success_rate": metrics.successful_orders / max(metrics.total_orders, 1)
                },
                "latency_metrics": {
                    "avg_latency_ms": metrics.avg_order_latency * 1000,
                    "max_latency_ms": metrics.max_order_latency * 1000,
                    "min_latency_ms": metrics.min_order_latency * 1000 if metrics.min_order_latency != float('inf') else 0
                },
                "trading_performance": {
                    "total_trades": metrics.total_trades,
                    "win_count": metrics.win_count,
                    "loss_count": metrics.loss_count,
                    "win_rate": win_rate,
                    "total_pnl": metrics.total_pnl,
                    "max_drawdown": metrics.max_drawdown
                },
                "tick_processing": {
                    "tick_count": metrics.tick_count,
                    "processing_rate": metrics.tick_processing_rate
                },
                "last_update": metrics.last_update
            }
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """获取系统性能指标"""
        return {
            "system_performance": {
                "cpu_percent": self.system_metrics.cpu_percent,
                "memory_mb": self.system_metrics.memory_mb,
                "memory_percent": self.system_metrics.memory_percent,
                "active_strategies": self.system_metrics.active_strategies,
                "total_events": self.system_metrics.total_events,
                "event_processing_rate": self.system_metrics.event_processing_rate
            },
            "performance_thresholds": self.thresholds,
            "monitoring_status": {
                "enabled": self.monitoring_enabled,
                "running": self._running,
                "metrics_interval": self.metrics_interval
            },
            "timestamp": self.system_metrics.timestamp
        }
    
    def get_historical_metrics(self, minutes: int = 60) -> List[Dict[str, Any]]:
        """获取历史性能指标"""
        cutoff_time = time.time() - (minutes * 60)
        
        return [
            {
                "timestamp": metric.timestamp,
                "cpu_percent": metric.cpu_percent,
                "memory_mb": metric.memory_mb,
                "memory_percent": metric.memory_percent,
                "active_strategies": metric.active_strategies,
                "total_events": metric.total_events,
                "event_processing_rate": metric.event_processing_rate
            }
            for metric in self.metrics_history
            if metric.timestamp >= cutoff_time
        ]
    
    # 事件处理器
    def _handle_order_placed(self, event: Event) -> None:
        """处理订单下达事件"""
        try:
            data = event.data
            strategy_id = data.get("strategy_id", "unknown")
            order_time = data.get("timestamp", time.time())
            
            # 记录订单延迟（从策略信号到下单的时间）
            latency = time.time() - order_time
            self.record_order_latency(strategy_id, latency)
            
        except Exception as e:
            logger.error(f"处理订单下达事件失败: {e}")
    
    def _handle_order_filled(self, event: Event) -> None:
        """处理订单成交事件"""
        try:
            data = event.data
            strategy_id = data.get("strategy_id", "unknown")
            
            with self._stats_lock:
                if strategy_id not in self.strategy_metrics:
                    self.strategy_metrics[strategy_id] = PerformanceMetrics(strategy_id=strategy_id)
                
                self.strategy_metrics[strategy_id].successful_orders += 1
                
        except Exception as e:
            logger.error(f"处理订单成交事件失败: {e}")
    
    def _handle_trade_executed(self, event: Event) -> None:
        """处理交易执行事件"""
        try:
            data = event.data
            strategy_id = data.get("strategy_id", "unknown")
            pnl = data.get("pnl", 0.0)
            
            with self._stats_lock:
                if strategy_id not in self.strategy_metrics:
                    self.strategy_metrics[strategy_id] = PerformanceMetrics(strategy_id=strategy_id)
                
                metrics = self.strategy_metrics[strategy_id]
                metrics.total_trades += 1
                metrics.total_pnl += pnl
                
                if pnl > 0:
                    metrics.win_count += 1
                else:
                    metrics.loss_count += 1
                
        except Exception as e:
            logger.error(f"处理交易执行事件失败: {e}")
    
    def _handle_tick_processed(self, event: Event) -> None:
        """处理tick处理事件"""
        try:
            # 更新tick处理统计
            with self._stats_lock:
                current_time = time.time()
                
                # 更新所有策略的tick计数（简化处理）
                for metrics in self.strategy_metrics.values():
                    metrics.tick_count += 1
                    metrics.last_tick_time = current_time
                    
        except Exception as e:
            logger.error(f"处理tick事件失败: {e}")
    
    def _handle_event_processed(self, event: Event) -> None:
        """处理事件处理统计"""
        try:
            self.system_metrics.total_events += 1
            
        except Exception as e:
            logger.error(f"处理事件统计失败: {e}") 