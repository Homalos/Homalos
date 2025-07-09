#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos_v2
@FileName   : test_event_monitors
@Date       : 2025/7/9 10:31
@Author     : Donny
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: description
"""
# !/usr/bin/env python
# -*- coding: utf-8 -*-
"""
事件总线监控器测试实例
演示监控器的作用和应用场景
"""
import time
import json
from datetime import datetime
from collections import defaultdict
from typing import Dict, List, Any

from src.core.event_bus import EventBus
from src.core.event import Event, EventType


class EventMonitor:
    """事件监控器基类"""

    def __init__(self, name: str):
        self.name = name
        self.event_count = 0
        self.event_history: List[Dict[str, Any]] = []

    def monitor(self, event: Event) -> None:
        """监控事件（子类需要实现）"""
        raise NotImplementedError


class EventLogger(EventMonitor):
    """事件日志监控器 - 记录所有事件"""

    def monitor(self, event: Event) -> None:
        self.event_count += 1
        event_record = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event.type,
            "event_data": event.data,
            "sequence": self.event_count
        }
        self.event_history.append(event_record)

        print(f"[{self.name}] 记录事件 #{self.event_count}: {event.type}")
        if event.data:
            print(f"    数据: {event.data}")


class EventAnalyzer(EventMonitor):
    """事件分析监控器 - 分析事件模式和统计"""

    def __init__(self, name: str):
        super().__init__(name)
        self.event_type_stats = defaultdict(int)
        self.event_frequency = defaultdict(list)
        self.last_event_time = None

    def monitor(self, event: Event) -> None:
        self.event_count += 1
        current_time = datetime.now()

        # 统计事件类型
        self.event_type_stats[event.type] += 1

        # 记录事件频率
        if self.last_event_time:
            interval = (current_time - self.last_event_time).total_seconds()
            self.event_frequency[event.type].append(interval)

        self.last_event_time = current_time

        # 分析异常模式
        if self.event_type_stats[event.type] > 10:
            print(f"[{self.name}] 警告: {event.type} 事件频率过高 ({self.event_type_stats[event.type]}次)")

    def get_analysis_report(self) -> Dict[str, Any]:
        """获取分析报告"""
        report = {
            "total_events": self.event_count,
            "event_type_distribution": dict(self.event_type_stats),
            "average_intervals": {}
        }

        for event_type, intervals in self.event_frequency.items():
            if intervals:
                avg_interval = sum(intervals) / len(intervals)
                report["average_intervals"][event_type] = avg_interval

        return report


class PerformanceMonitor(EventMonitor):
    """性能监控器 - 监控事件处理性能"""

    def __init__(self, name: str):
        super().__init__(name)
        self.processing_times = []
        self.slow_events = []
        self.threshold_ms = 100  # 100ms阈值

    def monitor(self, event: Event) -> None:
        self.event_count += 1
        start_time = time.time()

        # 模拟事件处理时间监控
        # 在实际应用中，这里会记录事件处理的开始时间
        processing_time = time.time() - start_time
        self.processing_times.append(processing_time)

        # 检测慢事件
        if processing_time * 1000 > self.threshold_ms:
            slow_event = {
                "event_type": event.type,
                "processing_time_ms": processing_time * 1000,
                "timestamp": datetime.now().isoformat()
            }
            self.slow_events.append(slow_event)
            print(f"[{self.name}] 性能警告: {event.type} 处理时间 {processing_time * 1000:.2f}ms")

    def get_performance_report(self) -> Dict[str, Any]:
        """获取性能报告"""
        if not self.processing_times:
            return {"error": "No events processed"}

        avg_time = sum(self.processing_times) / len(self.processing_times)
        max_time = max(self.processing_times)
        min_time = min(self.processing_times)

        return {
            "total_events": self.event_count,
            "average_processing_time_ms": avg_time * 1000,
            "max_processing_time_ms": max_time * 1000,
            "min_processing_time_ms": min_time * 1000,
            "slow_events_count": len(self.slow_events),
            "slow_events": self.slow_events
        }


class SecurityMonitor(EventMonitor):
    """安全监控器 - 监控可疑事件"""

    def __init__(self, name: str):
        super().__init__(name)
        self.suspicious_events = []
        self.blocked_events = []
        self.suspicious_patterns = [
            "SHUTDOWN",  # 频繁的关闭事件
            "ERROR",  # 错误事件
            "CRITICAL"  # 严重事件
        ]

    def monitor(self, event: Event) -> None:
        self.event_count += 1

        # 检查可疑模式
        if event.type in self.suspicious_patterns:
            suspicious_event = {
                "event_type": event.type,
                "timestamp": datetime.now().isoformat(),
                "data": event.data
            }
            self.suspicious_events.append(suspicious_event)
            print(f"[{self.name}] 安全警告: 检测到可疑事件 {event.type}")

        # 检查异常数据
        if event.data and isinstance(event.data, dict):
            if "error" in str(event.data).lower():
                print(f"[{self.name}] 安全警告: 事件数据包含错误信息")

    def get_security_report(self) -> Dict[str, Any]:
        """获取安全报告"""
        return {
            "total_events": self.event_count,
            "suspicious_events_count": len(self.suspicious_events),
            "suspicious_events": self.suspicious_events,
            "blocked_events_count": len(self.blocked_events)
        }


def demo_monitor_usage():
    """演示监控器的使用"""
    print("=" * 60)
    print("事件总线监控器测试演示")
    print("=" * 60)

    # 创建事件总线
    eb = EventBus(name="MonitorDemo")

    # 创建各种监控器
    logger_monitor = EventLogger("事件日志器")
    analyzer_monitor = EventAnalyzer("事件分析器")
    performance_monitor = PerformanceMonitor("性能监控器")
    security_monitor = SecurityMonitor("安全监控器")

    # 添加监控器到事件总线
    eb.add_monitor(logger_monitor.monitor)
    eb.add_monitor(analyzer_monitor.monitor)
    eb.add_monitor(performance_monitor.monitor)
    eb.add_monitor(security_monitor.monitor)

    # 定义事件处理器
    def timer_handler(event):
        print(f"[处理器] 处理TIMER事件")

    def trade_handler(event):
        print(f"[处理器] 处理交易事件: {event.data}")

    def error_handler(event):
        print(f"[处理器] 处理错误事件: {event.data}")

    # 订阅事件
    eb.subscribe(EventType.TIMER, timer_handler)
    eb.subscribe(EventType.ORDER_FILLED, trade_handler)
    eb.subscribe(EventType.SYSTEM_ERROR, error_handler)

    print("\n开始发布测试事件...")

    # 发布各种事件
    eb.publish(Event(EventType.ORDER_FILLED, {"symbol": "AAPL", "price": 150.25, "quantity": 100}))
    time.sleep(0.5)

    eb.publish(Event(EventType.ORDER_FILLED, {"symbol": "GOOGL", "price": 2750.50, "quantity": 50}))
    time.sleep(0.5)

    eb.publish(Event(EventType.SYSTEM_ERROR, {"message": "Connection timeout", "code": 5001}))
    time.sleep(0.5)

    # 等待一些TIMER事件
    print("\n等待TIMER事件...")
    time.sleep(3)

    # 发布更多事件
    eb.publish(Event(EventType.ORDER_FILLED, {"symbol": "MSFT", "price": 320.75, "quantity": 200}))
    eb.publish(Event(EventType.SHUTDOWN, {"reason": "Scheduled maintenance"}))

    print("\n" + "=" * 60)
    print("监控器报告")
    print("=" * 60)

    # 获取各种监控报告
    print("\n1. 事件分析报告:")
    analysis_report = analyzer_monitor.get_analysis_report()
    print(json.dumps(analysis_report, indent=2, ensure_ascii=False))

    print("\n2. 性能监控报告:")
    performance_report = performance_monitor.get_performance_report()
    print(json.dumps(performance_report, indent=2, ensure_ascii=False))

    print("\n3. 安全监控报告:")
    security_report = security_monitor.get_security_report()
    print(json.dumps(security_report, indent=2, ensure_ascii=False))

    print("\n4. 事件总线统计:")
    bus_stats = eb.get_stats()
    print(json.dumps(bus_stats, indent=2, ensure_ascii=False))

    # 停止事件总线
    eb.stop()
    print("\n" + "=" * 60)
    print("监控器测试完成")
    print("=" * 60)


if __name__ == "__main__":
    demo_monitor_usage()
