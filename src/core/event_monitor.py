#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos_v2
@FileName   : event_monitor
@Date       : 2025/1/16
@Author     : Donny
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 事件监控和可视化模块 - 第一阶段基础监控实现
"""
import json
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from typing import Dict, List, Any, Optional, Callable, Tuple

from src.core.event import Event
from src.core.logger import get_logger

logger = get_logger("EventMonitor")


class AlertLevel(Enum):
    """告警级别"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class Alert:
    """告警信息"""
    level: AlertLevel
    message: str
    event_type: Optional[str] = None
    metric_name: Optional[str] = None
    metric_value: Optional[float] = None
    threshold: Optional[float] = None
    timestamp: float = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()


@dataclass
class EventStats:
    """事件统计信息"""
    event_type: str
    count: int = 0
    total_processing_time_ns: int = 0
    total_queue_wait_time_ns: int = 0
    success_count: int = 0
    error_count: int = 0
    last_seen: float = 0
    
    @property
    def avg_processing_time_ms(self) -> float:
        """平均处理时间（毫秒）"""
        if self.count == 0:
            return 0
        return (self.total_processing_time_ns / self.count) / 1_000_000
    
    @property
    def avg_queue_wait_time_ms(self) -> float:
        """平均队列等待时间（毫秒）"""
        if self.count == 0:
            return 0
        return (self.total_queue_wait_time_ns / self.count) / 1_000_000
    
    @property
    def success_rate(self) -> float:
        """成功率"""
        if self.count == 0:
            return 0
        return self.success_count / self.count
    
    @property
    def error_rate(self) -> float:
        """错误率"""
        if self.count == 0:
            return 0
        return self.error_count / self.count


class EventMonitor:
    """
    事件监控器 - 负责收集、分析和展示事件处理指标
    
    功能：
    1. 实时事件统计
    2. 性能指标监控
    3. 异常检测和告警
    4. 基础可视化数据
    """
    
    def __init__(self,
                 name: str = "EventMonitor",
                 stats_window_size: int = 10000,
                 alert_window_minutes: int = 5,
                 performance_threshold_ms: float = 100.0,
                 error_rate_threshold: float = 0.05,
                 queue_wait_threshold_ms: float = 50.0):
        
        self._name = name
        self._stats_window_size = stats_window_size
        self._alert_window_minutes = alert_window_minutes
        self._performance_threshold_ms = performance_threshold_ms
        self._error_rate_threshold = error_rate_threshold
        self._queue_wait_threshold_ms = queue_wait_threshold_ms
        
        # 统计数据存储
        self._event_stats: Dict[str, EventStats] = {}
        self._recent_events: deque = deque(maxlen=stats_window_size)
        self._alerts: deque = deque(maxlen=1000)  # 保留最近1000个告警
        
        # 时间序列数据（用于可视化）
        self._time_series_data: Dict[str, deque] = {
            "event_count": deque(maxlen=300),  # 5分钟数据（每秒一个点）
            "processing_time": deque(maxlen=300),
            "queue_wait_time": deque(maxlen=300),
            "error_rate": deque(maxlen=300),
            "throughput": deque(maxlen=300),
        }
        
        # 告警回调函数
        self._alert_callbacks: List[Callable[[Alert], None]] = []
        
        # 监控状态
        self._monitoring_active = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        
        # 启动监控
        self.start_monitoring()
    
    def start_monitoring(self) -> None:
        """启动监控线程"""
        if self._monitoring_active:
            return
        
        self._monitoring_active = True
        self._monitor_thread = threading.Thread(
            target=self._monitoring_loop,
            name=f"EventMonitor-{self._name}",
            daemon=True
        )
        self._monitor_thread.start()
        logger.info(f"Event monitoring started for {self._name}")
    
    def stop_monitoring(self) -> None:
        """停止监控线程"""
        if not self._monitoring_active:
            return
        
        self._monitoring_active = False
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=2.0)
        logger.info(f"Event monitoring stopped for {self._name}")
    
    def _monitoring_loop(self) -> None:
        """监控主循环"""
        last_stats_time = time.time()
        
        while self._monitoring_active:
            try:
                current_time = time.time()
                
                # 每秒更新一次时间序列数据
                if current_time - last_stats_time >= 1.0:
                    self._update_time_series_data()
                    self._check_alerts()
                    last_stats_time = current_time
                
                time.sleep(0.1)  # 100ms检查间隔
                
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}", exc_info=True)
                time.sleep(1.0)
    
    def record_event(self, event: Event, processing_time_ns: int = 0, 
                    queue_wait_time_ns: int = 0, success: bool = True, 
                    error_message: Optional[str] = None) -> None:
        """记录事件处理信息"""
        with self._lock:
            current_time = time.time()
            
            # 更新事件统计
            if event.type not in self._event_stats:
                self._event_stats[event.type] = EventStats(event_type=event.type)
            stats = self._event_stats[event.type]
            
            stats.count += 1
            stats.total_processing_time_ns += processing_time_ns
            stats.total_queue_wait_time_ns += queue_wait_time_ns
            stats.last_seen = current_time
            
            if success:
                stats.success_count += 1
            else:
                stats.error_count += 1
            
            # 记录到最近事件列表
            event_record = {
                "timestamp": current_time,
                "event_type": event.type,
                "priority": event.priority.name,
                "processing_time_ns": processing_time_ns,
                "queue_wait_time_ns": queue_wait_time_ns,
                "success": success,
                "error_message": error_message,
                "trace_id": event.trace_id,
                "source": event.source
            }
            self._recent_events.append(event_record)
    
    def _update_time_series_data(self) -> None:
        """更新时间序列数据"""
        current_time = time.time()
        
        # 使用锁保护对deque的访问，并创建快照
        with self._lock:
            recent_events_snapshot = list(self._recent_events)
        
        # 计算最近一秒的统计数据
        recent_events = [e for e in recent_events_snapshot 
                        if current_time - e["timestamp"] <= 1.0]
        
        if not recent_events:
            # 没有最近事件，添加零值
            self._time_series_data["event_count"].append((current_time, 0))
            self._time_series_data["processing_time"].append((current_time, 0))
            self._time_series_data["queue_wait_time"].append((current_time, 0))
            self._time_series_data["error_rate"].append((current_time, 0))
            self._time_series_data["throughput"].append((current_time, 0))
            return
        
        # 计算指标
        event_count = len(recent_events)
        avg_processing_time = sum(e["processing_time_ns"] for e in recent_events) / event_count / 1_000_000
        avg_queue_wait_time = sum(e["queue_wait_time_ns"] for e in recent_events) / event_count / 1_000_000
        error_count = sum(1 for e in recent_events if not e["success"])
        error_rate = error_count / event_count if event_count > 0 else 0
        throughput = event_count  # 每秒事件数
        
        # 添加到时间序列
        self._time_series_data["event_count"].append((current_time, event_count))
        self._time_series_data["processing_time"].append((current_time, avg_processing_time))
        self._time_series_data["queue_wait_time"].append((current_time, avg_queue_wait_time))
        self._time_series_data["error_rate"].append((current_time, error_rate))
        self._time_series_data["throughput"].append((current_time, throughput))
    
    def _check_alerts(self) -> None:
        """检查告警条件"""
        current_time = time.time()
        
        # 使用锁保护对deque的访问，并创建快照
        with self._lock:
            recent_events_snapshot = list(self._recent_events)
        
        # 检查最近时间窗口内的数据
        window_start = current_time - (self._alert_window_minutes * 60)
        recent_data = [e for e in recent_events_snapshot 
                      if e["timestamp"] >= window_start]
        
        if not recent_data:
            return
        
        # 计算窗口内的指标
        total_events = len(recent_data)
        error_events = sum(1 for e in recent_data if not e["success"])
        error_rate = error_events / total_events if total_events > 0 else 0
        
        avg_processing_time = sum(e["processing_time_ns"] for e in recent_data) / total_events / 1_000_000
        avg_queue_wait_time = sum(e["queue_wait_time_ns"] for e in recent_data) / total_events / 1_000_000
        
        # 检查错误率告警
        if error_rate > self._error_rate_threshold:
            alert = Alert(
                level=AlertLevel.ERROR,
                message=f"High error rate detected: {error_rate:.2%} (threshold: {self._error_rate_threshold:.2%})",
                metric_name="error_rate",
                metric_value=error_rate,
                threshold=self._error_rate_threshold
            )
            self._add_alert(alert)
        
        # 检查处理时间告警
        if avg_processing_time > self._performance_threshold_ms:
            alert = Alert(
                level=AlertLevel.WARNING,
                message=f"High processing time detected: {avg_processing_time:.2f}ms (threshold: {self._performance_threshold_ms}ms)",
                metric_name="processing_time",
                metric_value=avg_processing_time,
                threshold=self._performance_threshold_ms
            )
            self._add_alert(alert)
        
        # 检查队列等待时间告警
        if avg_queue_wait_time > self._queue_wait_threshold_ms:
            alert = Alert(
                level=AlertLevel.WARNING,
                message=f"High queue wait time detected: {avg_queue_wait_time:.2f}ms (threshold: {self._queue_wait_threshold_ms}ms)",
                metric_name="queue_wait_time",
                metric_value=avg_queue_wait_time,
                threshold=self._queue_wait_threshold_ms
            )
            self._add_alert(alert)
    
    def _add_alert(self, alert: Alert) -> None:
        """添加告警"""
        # 避免重复告警（5分钟内相同类型的告警只发送一次）
        recent_alerts = [a for a in self._alerts 
                        if time.time() - a.timestamp < 300 and 
                           a.metric_name == alert.metric_name and 
                           a.level == alert.level]
        
        if recent_alerts:
            return  # 跳过重复告警
        
        self._alerts.append(alert)
        logger.warning(f"Alert generated: {alert.message}")
        
        # 调用告警回调
        for callback in self._alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"Alert callback error: {e}", exc_info=True)
    
    def add_alert_callback(self, callback: Callable[[Alert], None]) -> None:
        """添加告警回调函数"""
        if callback not in self._alert_callbacks:
            self._alert_callbacks.append(callback)
            logger.debug("Added alert callback")
    
    def remove_alert_callback(self, callback: Callable[[Alert], None]) -> None:
        """移除告警回调函数"""
        if callback in self._alert_callbacks:
            self._alert_callbacks.remove(callback)
            logger.debug("Removed alert callback")
    
    def get_event_stats(self) -> Dict[str, Dict[str, Any]]:
        """获取事件统计信息"""
        with self._lock:
            return {
                event_type: {
                    "count": stats.count,
                    "avg_processing_time_ms": stats.avg_processing_time_ms,
                    "avg_queue_wait_time_ms": stats.avg_queue_wait_time_ms,
                    "success_rate": stats.success_rate,
                    "error_rate": stats.error_rate,
                    "last_seen": stats.last_seen
                }
                for event_type, stats in self._event_stats.items()
            }
    
    def get_time_series_data(self, metric: str, duration_minutes: int = 5) -> List[Tuple[float, float]]:
        """获取时间序列数据"""
        if metric not in self._time_series_data:
            return []
        
        current_time = time.time()
        cutoff_time = current_time - (duration_minutes * 60)
        
        return [(timestamp, value) for timestamp, value in self._time_series_data[metric] 
                if timestamp >= cutoff_time]
    
    def get_recent_alerts(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取最近的告警"""
        with self._lock:
            recent_alerts = list(self._alerts)[-limit:]
        return [asdict(alert) for alert in recent_alerts]
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计数据（兼容性方法）"""
        return self.get_dashboard_data()
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """获取仪表板数据"""
        current_time = time.time()
        
        # 使用锁保护对数据结构的访问，并创建快照
        with self._lock:
            event_stats_snapshot = dict(self._event_stats)
            recent_events_snapshot = list(self._recent_events)
            list(self._alerts)
        
        # 基础统计
        total_events = sum(stats.count for stats in event_stats_snapshot.values())
        total_errors = sum(stats.error_count for stats in event_stats_snapshot.values())
        overall_error_rate = total_errors / total_events if total_events > 0 else 0
        
        # 最近5分钟的数据
        recent_events = [e for e in recent_events_snapshot 
                        if current_time - e["timestamp"] <= 300]
        
        recent_count = len(recent_events)
        recent_errors = sum(1 for e in recent_events if not e["success"])
        recent_error_rate = recent_errors / recent_count if recent_count > 0 else 0
        
        recent_avg_processing_time = 0
        recent_avg_queue_wait_time = 0
        if recent_events:
            recent_avg_processing_time = sum(e["processing_time_ns"] for e in recent_events) / recent_count / 1_000_000
            recent_avg_queue_wait_time = sum(e["queue_wait_time_ns"] for e in recent_events) / recent_count / 1_000_000
        
        # 事件类型分布
        event_type_distribution = {}
        for event_type, stats in event_stats_snapshot.items():
            event_type_distribution[event_type] = {
                "count": stats.count,
                "percentage": (stats.count / total_events * 100) if total_events > 0 else 0
            }
        
        # 优先级分布
        priority_distribution = defaultdict(int)
        for event in recent_events:
            priority_distribution[event["priority"]] += 1
        
        return {
            "timestamp": current_time,
            "summary": {
                "total_events": total_events,
                "total_errors": total_errors,
                "overall_error_rate": overall_error_rate,
                "recent_events_5min": recent_count,
                "recent_errors_5min": recent_errors,
                "recent_error_rate_5min": recent_error_rate,
                "recent_avg_processing_time_ms": recent_avg_processing_time,
                "recent_avg_queue_wait_time_ms": recent_avg_queue_wait_time,
                "throughput_per_min": recent_count / 5 if recent_count > 0 else 0
            },
            "event_type_distribution": event_type_distribution,
            "priority_distribution": dict(priority_distribution),
            "time_series": {
                metric: self.get_time_series_data(metric, 5) 
                for metric in self._time_series_data.keys()
            },
            "recent_alerts": self.get_recent_alerts(10),
            "top_slow_events": self._get_top_slow_events(),
            "top_error_events": self._get_top_error_events()
        }
    
    def _get_top_slow_events(self, limit: int = 5) -> List[Dict[str, Any]]:
        """获取处理时间最长的事件类型"""
        sorted_stats = sorted(
            self._event_stats.items(),
            key=lambda x: x[1].avg_processing_time_ms,
            reverse=True
        )
        
        return [
            {
                "event_type": event_type,
                "avg_processing_time_ms": stats.avg_processing_time_ms,
                "count": stats.count
            }
            for event_type, stats in sorted_stats[:limit]
            if stats.count > 0
        ]
    
    def _get_top_error_events(self, limit: int = 5) -> List[Dict[str, Any]]:
        """获取错误率最高的事件类型"""
        sorted_stats = sorted(
            self._event_stats.items(),
            key=lambda x: x[1].error_rate,
            reverse=True
        )
        
        return [
            {
                "event_type": event_type,
                "error_rate": stats.error_rate,
                "error_count": stats.error_count,
                "total_count": stats.count
            }
            for event_type, stats in sorted_stats[:limit]
            if stats.error_count > 0
        ]
    
    def export_metrics(self, format_str: str = "json") -> str:
        """导出监控指标"""
        data = {
            "export_time": datetime.now().isoformat(),
            "monitor_name": self._name,
            "event_stats": self.get_event_stats(),
            "dashboard_data": self.get_dashboard_data()
        }
        
        if format_str.lower() == "json":
            return json.dumps(data, indent=2, ensure_ascii=False)
        else:
            raise ValueError(f"Unsupported export format: {format_str}")
    
    def reset_stats(self) -> None:
        """重置统计数据"""
        with self._lock:
            self._event_stats.clear()
            self._recent_events.clear()
            self._alerts.clear()
            for deque_data in self._time_series_data.values():
                deque_data.clear()
        logger.info("Event monitor stats reset")
    
    def __enter__(self):
        self.start_monitoring()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop_monitoring()
        return False


class EventMonitorIntegration:
    """
    事件监控集成器 - 将监控器与事件总线集成
    """
    
    def __init__(self, event_bus, monitor: EventMonitor):
        self.event_bus = event_bus
        self.monitor = monitor
        self._last_metrics_check = time.time()
        
        # 注册监控回调 - 兼容不同类型的事件总线
        if hasattr(self.event_bus, 'add_monitor'):
            # 普通EventBus
            self.event_bus.add_monitor(self._monitor_callback)
        elif hasattr(self.event_bus, 'subscribe_global'):
            # EnhancedEventBusV2
            self.event_bus.subscribe_global(self._enhanced_monitor_callback)
        else:
            logger.warning("Event bus does not support monitoring")
        
        # 启动指标收集线程
        self._metrics_thread = threading.Thread(
            target=self._metrics_collection_loop,
            name="EventMonitorMetricsCollection",
            daemon=True
        )
        self._metrics_active = True
        self._metrics_thread.start()
        
        logger.info("Event monitor integrated with event bus")
    
    def _monitor_callback(self, event: Event) -> None:
        """监控回调函数 - 记录事件发布（普通EventBus）"""
        # 简单记录事件发布，详细指标由_metrics_collection_loop处理
        self.monitor.record_event(
            event=event,
            processing_time_ns=0,
            queue_wait_time_ns=0,
            success=True
        )
    
    def _enhanced_monitor_callback(self, event_data: dict) -> None:
        """增强监控回调函数 - 处理EnhancedEventBusV2的事件（字典格式）"""
        try:
            # 从EnhancedEventBusV2获取的是字典格式的事件数据
            from src.core.event import Event, EventPriority
            
            # 创建Event对象
            temp_event = Event(
                event_type=event_data.get('type', 'unknown'),
                data=event_data.get('data', {}),
                priority=EventPriority.NORMAL
            )
            
            # 记录事件（初始记录，详细指标由_metrics_collection_loop处理）
            self.monitor.record_event(
                event=temp_event,
                processing_time_ns=0,
                queue_wait_time_ns=0,
                success=True
            )
            
        except Exception as e:
            logger.error(f"Enhanced monitor callback error: {e}", exc_info=True)
    
    def _metrics_collection_loop(self) -> None:
        """指标收集循环 - 从EnhancedEventBus获取详细指标"""
        while self._metrics_active:
            try:
                # 检查是否是EnhancedEventBusV2，如果是则获取详细指标
                if hasattr(self.event_bus, 'get_processing_results'):
                    self._collect_enhanced_metrics()
                elif hasattr(self.event_bus, '_event_metrics'):
                    self._collect_enhanced_metrics()
                
                time.sleep(1.0)  # 每秒检查一次
                
            except Exception as e:
                logger.error(f"Metrics collection error: {e}", exc_info=True)
                time.sleep(1.0)
    
    def _collect_enhanced_metrics(self) -> None:
        """从EnhancedEventBus收集详细指标"""
        try:
            # 获取新的事件指标
            current_time = time.time()
            new_metrics = []
            
            # 从EnhancedEventBus的_event_metrics中获取新指标
            for metrics in self.event_bus.get_event_metrics():
                if metrics.timestamp / 1_000_000_000 > self._last_metrics_check:
                    new_metrics.append(metrics)
            
            # 记录新指标到EventMonitor
            for metrics in new_metrics:
                # 创建一个临时事件对象
                from src.core.event import Event, EventType, EventPriority
                temp_event = Event(
                    event_type=metrics.event_type,
                    priority=EventPriority.NORMAL
                )
                
                self.monitor.record_event(
                    event=temp_event,
                    processing_time_ns=metrics.processing_time_ns,
                    queue_wait_time_ns=metrics.queue_wait_time_ns,
                    success=metrics.success,
                    error_message=metrics.error_message
                )
            
            self._last_metrics_check = current_time
            
        except Exception as e:
            logger.error(f"Enhanced metrics collection error: {e}", exc_info=True)
    
    def stop(self) -> None:
        """停止指标收集"""
        self._metrics_active = False
        if self._metrics_thread and self._metrics_thread.is_alive():
            self._metrics_thread.join(timeout=2.0)
        logger.info("Event monitor integration stopped")


# if __name__ == '__main__':
#     def test_alert_callback(alert: Alert):
#         print(f"🚨 告警: [{alert.level.value.upper()}] {alert.message}")
#
#     print("=" * 50)
#     print("启动事件监控测试...")
#
#     # 创建监控器
#     monitor = EventMonitor(
#         name="TestMonitor",
#         performance_threshold_ms=10.0,  # 降低阈值以便测试
#         error_rate_threshold=0.1
#     )
#
#     # 添加告警回调
#     monitor.add_alert_callback(test_alert_callback)
#
#     try:
#         # 模拟事件处理
#         print("\n模拟事件处理...")
#
#         from src.core.event import Event, EventType, EventPriority
#
#         # 正常事件
#         for i in range(10):
#             event = Event(EventType.MARKET_TICK, priority=EventPriority.NORMAL)
#             monitor.record_event(
#                 event=event,
#                 processing_time_ns=5_000_000,  # 5ms
#                 queue_wait_time_ns=1_000_000,  # 1ms
#                 success=True
#             )
#
#         # 慢事件
#         for i in range(3):
#             event = Event(EventType.ORDER, priority=EventPriority.HIGH)
#             monitor.record_event(
#                 event=event,
#                 processing_time_ns=20_000_000,  # 20ms (超过阈值)
#                 queue_wait_time_ns=2_000_000,  # 2ms
#                 success=True
#             )
#
#         # 错误事件
#         for i in range(2):
#             event = Event(EventType.STRATEGY_ERROR, priority=EventPriority.HIGH)
#             monitor.record_event(
#                 event=event,
#                 processing_time_ns=15_000_000,  # 15ms
#                 queue_wait_time_ns=3_000_000,  # 3ms
#                 success=False,
#                 error_message="测试错误"
#             )
#
#         time.sleep(2)  # 等待监控处理
#
#         # 显示统计信息
#         print("\n=== 事件统计 ===")
#         stats = monitor.get_event_stats()
#         for event_type, stat in stats.items():
#             print(f"{event_type}: {stat['count']}次, 成功率: {stat['success_rate']:.2%}, "
#                   f"平均处理时间: {stat['avg_processing_time_ms']:.2f}ms")
#
#         # 显示仪表板数据
#         print("\n=== 仪表板摘要 ===")
#         dashboard = monitor.get_dashboard_data()
#         summary = dashboard["summary"]
#         print(f"总事件数: {summary['total_events']}")
#         print(f"总错误数: {summary['total_errors']}")
#         print(f"整体错误率: {summary['overall_error_rate']:.2%}")
#         print(f"平均处理时间: {summary['recent_avg_processing_time_ms']:.2f}ms")
#
#         # 显示告警
#         print("\n=== 最近告警 ===")
#         alerts = monitor.get_recent_alerts()
#         for alert in alerts:
#             print(f"[{alert['level'].upper()}] {alert['message']}")
#
#         input("\n按 Enter 键停止测试...")
#
#     except KeyboardInterrupt:
#         print("\n收到中断信号，正在停止...")
#     finally:
#         monitor.stop_monitoring()
#         print("\n测试完成！")