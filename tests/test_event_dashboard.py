#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos_v2
@FileName   : test_event_dashboard
@Date       : 2025/8/8 21:35
@Author     : Donny
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: description
"""
import threading
import time

from src.core.event_dashboard import EventDashboard
from src.core.event_monitor import EventMonitor
from src.core.event import Event, EventType, EventPriority
from src.core.logger import get_logger

logger = get_logger("DashboardTest")


print("=" * 50)
print("启动事件监控仪表板测试...")

# 创建监控器
monitor = EventMonitor(name="DashboardTest")

# 创建仪表板
dashboard = EventDashboard(monitor, host='localhost', port=8080)

try:
    # 启动仪表板
    dashboard.start()
    print(f"\n🌐 仪表板已启动: {dashboard.url}")
    print("请在浏览器中打开上述地址查看监控界面")

    # 模拟一些事件数据
    print("\n正在生成模拟事件数据...")

    import random

    def generate_test_events():
        """生成测试事件"""
        event_types = [EventType.MARKET_TICK, EventType.ORDER, EventType.TRADE,
                      EventType.STRATEGY_SIGNAL, EventType.RISK_CHECK]

        while dashboard.is_running:
            try:
                # 随机选择事件类型
                event_type = random.choice(event_types)
                priority = random.choice(list(EventPriority))

                event = Event(event_type, priority=priority)

                # 模拟处理时间和成功率
                processing_time = random.randint(1_000_000, 50_000_000)  # 1-50ms
                queue_wait_time = random.randint(100_000, 10_000_000)    # 0.1-10ms
                success = random.random() > 0.05  # 95%成功率

                monitor.record_event(
                    event=event,
                    processing_time_ns=processing_time,
                    queue_wait_time_ns=queue_wait_time,
                    success=success,
                    error_message="模拟错误" if not success else None
                )

                time.sleep(random.uniform(0.1, 2.0))  # 随机间隔

            except Exception as e:
                logger.error(f"Test event generation error: {e}")
                time.sleep(1.0)

    # 在后台生成测试事件
    test_thread = threading.Thread(target=generate_test_events, daemon=True)
    test_thread.start()

    print("\n按 Ctrl+C 停止服务器...")

    # 保持主线程运行
    while dashboard.is_running:
        time.sleep(1)

except KeyboardInterrupt:
    print("\n收到中断信号，正在停止服务器...")
except Exception as e:
    logger.error(f"Dashboard test error: {e}", exc_info=True)
finally:
    dashboard.stop()
    monitor.stop_monitoring()
    print("\n测试完成！")