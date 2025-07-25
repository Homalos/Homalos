#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos_v2
@FileName   : test_phase2_optimization
@Date       : 2025/1/16
@Author     : Donny
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 第二阶段优化测试脚本
测试异步处理池、事件调度器、类型安全、路由机制、健康监控等新功能
"""

import asyncio
import time
import threading
import random
import json
from typing import Dict, List, Any
from dataclasses import dataclass
from datetime import datetime

# 导入测试模块
from src.core.async_handler_pool import AsyncHandlerPool, async_handler, sync_handler
from src.core.event_scheduler import EventScheduler, SchedulingStrategy, ExecutionMode
from src.core.event_types import (
    TypedEvent, EventTypeRegistry, EventCategory, EventSeverity,
    SystemEventData, TradingEventData, MarketDataEventData
)
from src.core.event_router import EventRouter, RoutingStrategy, RouteFilter
from src.core.health_monitor import HealthMonitor, SystemResourceCheck, CustomHealthCheck
from src.core.enhanced_event_bus import (
    EnhancedEventBus, EventBusConfig, ProcessingMode,
    create_enhanced_event_bus, create_high_performance_event_bus
)
from src.core.logger import get_logger

logger = get_logger("Phase2Test")


@dataclass
class TestResult:
    """测试结果"""
    test_name: str
    success: bool
    duration: float
    details: Dict[str, Any]
    error: str = ""


class Phase2OptimizationTester:
    """第二阶段优化测试器"""
    
    def __init__(self):
        self.results: List[TestResult] = []
        self.start_time = time.time()
        
        # 测试数据收集
        self.async_handler_results = []
        self.sync_handler_results = []
        self.routing_results = []
        self.health_check_results = []
        
        logger.info("Phase2OptimizationTester initialized")
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """运行所有测试"""
        logger.info("Starting Phase 2 optimization tests...")
        
        test_methods = [
            self.test_async_handler_pool,
            self.test_event_scheduler,
            self.test_event_types_safety,
            self.test_event_router,
            self.test_health_monitor,
            self.test_enhanced_event_bus_v2,
            self.test_high_performance_mode,
            self.test_integration_scenario,
            self.test_stress_performance
        ]
        
        for test_method in test_methods:
            try:
                logger.info(f"Running test: {test_method.__name__}")
                await test_method()
                logger.info(f"Test completed: {test_method.__name__}")
            except Exception as e:
                logger.error(f"Test failed: {test_method.__name__} - {e}", exc_info=True)
                self.results.append(TestResult(
                    test_name=test_method.__name__,
                    success=False,
                    duration=0.0,
                    details={},
                    error=str(e)
                ))
        
        return self.generate_test_report()
    
    async def test_async_handler_pool(self) -> None:
        """测试异步处理器池"""
        start_time = time.time()
        
        # 创建处理器池
        pool = AsyncHandlerPool(
            name="TestPool",
            max_workers=3,
            max_async_tasks=5,
            default_timeout=10.0
        )
        
        try:
            # 定义测试处理器
            async def async_test_handler(event):
                await asyncio.sleep(0.1)
                self.async_handler_results.append(f"async_{event.data.get('id')}")
                return f"async_result_{event.data.get('id')}"
            
            def sync_test_handler(event):
                time.sleep(0.05)
                self.sync_handler_results.append(f"sync_{event.data.get('id')}")
                return f"sync_result_{event.data.get('id')}"
            
            # 注册处理器
            pool.register_handler(async_test_handler, event_types=["async_test"])
            pool.register_handler(sync_test_handler, event_types=["sync_test"])
            
            # 创建测试事件
            from src.core.event import Event
            events = []
            for i in range(20):
                if i % 2 == 0:
                    event = Event("async_test", {"id": i, "type": "async"})
                else:
                    event = Event("sync_test", {"id": i, "type": "sync"})
                events.append(event)
            
            # 执行测试
            results = []
            for event in events:
                result = await pool.execute_async(event)
                results.extend(result)
            
            # 验证结果
            async_count = len(self.async_handler_results)
            sync_count = len(self.sync_handler_results)
            
            success = (
                async_count == 10 and
                sync_count == 10 and
                len(results) == 20
            )
            
            self.results.append(TestResult(
                test_name="test_async_handler_pool",
                success=success,
                duration=time.time() - start_time,
                details={
                    'async_results': async_count,
                    'sync_results': sync_count,
                    'execution_results': len(results)
                }
            ))
            
        except Exception as e:
            self.results.append(TestResult(
                test_name="test_async_handler_pool",
                success=False,
                duration=time.time() - start_time,
                details={},
                error=str(e)
            ))
    
    async def test_event_scheduler(self) -> None:
        """测试事件调度器"""
        start_time = time.time()
        
        # 创建调度器
        scheduler = EventScheduler(
            name="TestScheduler",
            strategy=SchedulingStrategy.ADAPTIVE,
            execution_mode=ExecutionMode.AUTO
        )
        
        # 创建处理器池
        pool = AsyncHandlerPool(name="SchedulerTestPool")
        
        try:
            # 定义处理器
            async def priority_handler(event):
                await asyncio.sleep(0.1)
                return f"priority_{event.data.get('priority', 0)}"
            
            def load_handler(event):
                time.sleep(0.05)
                return f"load_{event.data.get('load', 0)}"
            
            # 注册处理器
            pool.register_handler(priority_handler, event_types=["priority_test"])
            pool.register_handler(load_handler, event_types=["load_test"])
            
            # 创建测试事件
            from src.core.event import Event
            test_events = [
                Event("priority_test", {"id": i, "priority": random.randint(1, 10)})
                for i in range(5)
            ] + [
                Event("load_test", {"id": i, "load": random.randint(1, 5)})
                for i in range(5)
            ]
            
            # 执行测试
            all_results = []
            for event in test_events:
                results = await pool.execute_async(event)
                all_results.extend(results)
            
            success = (
                len(all_results) == 10 and
                all(r.success for r in all_results)
            )
            
            self.results.append(TestResult(
                test_name="test_event_scheduler",
                success=success,
                duration=time.time() - start_time,
                details={
                    'total_results': len(all_results),
                    'success_count': sum(1 for r in all_results if r.success)
                }
            ))
            
        except Exception as e:
            self.results.append(TestResult(
                test_name="test_event_scheduler",
                success=False,
                duration=time.time() - start_time,
                details={},
                error=str(e)
            ))
    
    async def test_event_types_safety(self) -> None:
        """测试事件类型安全"""
        start_time = time.time()
        
        # 创建类型注册表
        registry = EventTypeRegistry()
        
        # 注册事件类型
        registry.register_event_type(
            "system.startup",
            SystemEventData,
            EventCategory.SYSTEM,
            EventSeverity.INFO
        )
        
        registry.register_event_type(
            "trading.order",
            TradingEventData,
            EventCategory.TRADING,
            EventSeverity.INFO
        )
        
        registry.register_event_type(
            "market.data",
            MarketDataEventData,
            EventCategory.MARKET_DATA,
            EventSeverity.DEBUG
        )
        
        # 创建类型化事件
        system_event = registry.create_typed_event(
            "system.startup",
            {
                "message": "EventBus started",
                "component": "EventBus",
                "level": "info",
                "details": {"version": "2.0"}
            }
        )
        
        trading_event = registry.create_typed_event(
            "trading.order",
            {
                "symbol": "AAPL",
                "action": "buy",
                "quantity": 100,
                "price": 150.0
            }
        )
        
        market_event = registry.create_typed_event(
            "market.data",
            {
                "symbol": "AAPL",
                "price": 150.0,
                "volume": 1000,
                "timestamp": time.time()
            }
        )
        
        # 验证事件
        events_created = [system_event, trading_event, market_event]
        validation_results = []
        
        for event in events_created:
            try:
                # 验证事件数据
                is_valid = event.validate()
                validation_results.append(is_valid)
            except Exception as e:
                logger.error(f"Event validation failed: {e}")
                validation_results.append(False)
        
        # 测试类型注册表功能
        registered_types = registry.list_event_types()
        type_info = registry.get_event_type_info("system.startup")
        
        success = (
            len(registered_types) == 3 and
            all(validation_results) and
            type_info is not None and
            type_info['data_class'].__name__ == 'SystemEventData'
        )
        
        # 创建可序列化的type_info副本
        serializable_type_info = type_info.copy() if type_info else None
        if serializable_type_info and 'data_class' in serializable_type_info:
            serializable_type_info['data_class'] = serializable_type_info['data_class'].__name__
        
        self.results.append(TestResult(
            test_name="test_event_types_safety",
            success=success,
            duration=time.time() - start_time,
            details={
                'registered_types': registered_types,
                'validation_results': validation_results,
                'events_created': len(events_created),
                'type_info': serializable_type_info
            }
        ))
    
    async def test_event_router(self) -> None:
        """测试事件路由器"""
        start_time = time.time()
        
        # 创建路由器
        router = EventRouter(
            name="TestRouter",
            max_workers=5,
            enable_metrics=True
        )
        
        # 定义处理器
        def handler_a(data):
            self.routing_results.append(f"handler_a_{data.get('id')}")
        
        def handler_b(data):
            self.routing_results.append(f"handler_b_{data.get('id')}")
        
        def handler_c(data):
            self.routing_results.append(f"handler_c_{data.get('id')}")
        
        # 注册处理器
        router.register_handler("handler_a", handler_a)
        router.register_handler("handler_b", handler_b)
        router.register_handler("handler_c", handler_c)
        
        # 添加路由规则
        from src.core.event_router import RouteRule, RouteFilter, FilterOperator, RoutingStrategy
        
        # 只有优先级 > 5 的事件才路由到 handler_a
        high_priority_rule = RouteRule(
            name="high_priority",
            pattern="*",
            filters=[RouteFilter("data.priority", FilterOperator.GREATER_THAN, 5)],
            target_handlers=["handler_a"],
            strategy=RoutingStrategy.BROADCAST
        )
        router.add_rule(high_priority_rule)
        
        # 交易事件路由到 handler_b 和 handler_c
        trading_rule = RouteRule(
            name="trading_events",
            pattern="trading.*",
            target_handlers=["handler_b", "handler_c"],
            strategy=RoutingStrategy.BROADCAST
        )
        router.add_rule(trading_rule)
        
        # 测试路由
        test_events = [
            {"id": 1, "type": "system.startup", "priority": 3},
            {"id": 2, "type": "trading.order", "priority": 7},
            {"id": 3, "type": "market.data", "priority": 2},
            {"id": 4, "type": "trading.fill", "priority": 8}
        ]
        
        all_handlers = [handler_a, handler_b, handler_c]
        routing_test_results = []
        
        for event in test_events:
            from src.core.event import Event
            event_obj = Event(event_type=event['type'], data=event)
            routing_results = router.route_event(event_obj)
            routing_test_results.append({
                'event_id': event['id'],
                'original_handlers': len(all_handlers),
                'routing_results': len(routing_results)
            })
        
        router_stats = router.get_stats()
        
        success = (
            len(routing_test_results) == 4 and
            router_stats['total_routed'] == 2 and  # 只有2个事件匹配路由规则
            router_stats['successful_routes'] == 4 and  # 2个事件各触发2个处理器
            router_stats['failed_routes'] == 0 and
            router_stats['active_rules'] == 2
        )
        
        self.results.append(TestResult(
            test_name="test_event_router",
            success=success,
            duration=time.time() - start_time,
            details={
                'routing_results': routing_test_results,
                'router_stats': router_stats,
                'rules_count': len(router._rules)
            }
        ))
    
    async def test_health_monitor(self) -> None:
        """测试健康监控"""
        start_time = time.time()
        
        # 创建健康监控器
        monitor = HealthMonitor(
            name="TestHealthMonitor",
            check_interval=1.0,
            enable_alerts=True
        )
        
        # 添加系统资源检查
        monitor.add_check(SystemResourceCheck(
            cpu_threshold=90.0,
            memory_threshold=90.0,
            disk_threshold=95.0
        ))
        
        # 添加自定义检查
        def custom_check():
            # 模拟检查逻辑
            return {
                'status': 'healthy',
                'message': 'Custom check passed',
                'details': {'test_value': random.randint(1, 100)}
            }
        
        monitor.add_check(CustomHealthCheck(
            name="custom_test",
            check_func=custom_check,
            interval=2.0
        ))
        
        # 添加告警回调
        def alert_callback(result):
            self.health_check_results.append({
                'check_name': result.check_name,
                'status': result.status.value,
                'message': result.message
            })
        
        monitor.add_alert_callback(alert_callback)
        
        try:
            # 启动监控
            monitor.start()
            
            # 等待几次检查
            await asyncio.sleep(3.0)
            
            # 手动运行检查
            manual_result = monitor.run_check_now("system_resources")
            
            # 获取健康报告
            health_report = monitor.get_health_report()
            monitor_stats = monitor.get_stats()
            
            success = (
                manual_result is not None and
                health_report is not None and
                monitor_stats['running'] and
                monitor_stats['total_checks_registered'] == 2
            )
            
            self.results.append(TestResult(
                test_name="test_health_monitor",
                success=success,
                duration=time.time() - start_time,
                details={
                    'health_report': health_report,
                    'monitor_stats': monitor_stats,
                    'manual_check_result': manual_result.to_dict() if manual_result else None,
                    'alert_callbacks_triggered': len(self.health_check_results)
                }
            ))
            
        finally:
            monitor.stop()
    
    async def test_enhanced_event_bus_v2(self) -> None:
        """测试增强事件总线 V2"""
        start_time = time.time()
        
        # 创建配置
        config = EventBusConfig(
            name="TestEventBusV2",
            max_queue_size=1000,
            processing_mode=ProcessingMode.HYBRID,
            async_pool_size=5,
            sync_pool_size=3,
            enable_health_monitoring=True,
            enable_metrics=True
        )
        
        # 创建事件总线
        bus = EnhancedEventBus(config)
        
        # 测试数据收集
        processed_events = []
        
        # 定义处理器
        async def async_event_handler(event_data):
            await asyncio.sleep(0.01)
            # 从事件数据的data字段中获取用户ID
            user_id = event_data.get('data', {}).get('id', event_data.get('id'))
            processed_events.append(f"async_{user_id}")
        
        def sync_event_handler(event_data):
            # 从事件数据的data字段中获取用户ID
            user_id = event_data.get('data', {}).get('id', event_data.get('id'))
            processed_events.append(f"sync_{user_id}")
        
        try:
            # 启动事件总线
            bus.start()
            
            # 等待启动完成
            await asyncio.sleep(1.0)
            
            # 订阅事件
            bus.subscribe("test.async", async_event_handler)
            bus.subscribe("test.sync", sync_event_handler)
            bus.subscribe_global(lambda data: processed_events.append(f"global_{data.get('data', {}).get('id', data.get('id'))}"))
            
            # 发布事件
            event_ids = []
            for i in range(20):
                if i % 2 == 0:
                    event_id = bus.publish("test.async", {"id": i, "type": "async"})
                else:
                    event_id = bus.publish("test.sync", {"id": i, "type": "sync"})
                event_ids.append(event_id)
            
            # 等待处理完成
            await asyncio.sleep(2.0)
            
            # 获取统计信息
            stats = bus.get_stats()
            metrics = bus.get_metrics()
            health_report = bus.get_health_report()
            
            success = (
                len(event_ids) == 20 and
                len(processed_events) >= 40 and  # 每个事件至少被2个处理器处理
                stats['status'] == 'running' and
                metrics.total_events_published == 20 and
                health_report is not None
            )
            
            self.results.append(TestResult(
                test_name="test_enhanced_event_bus_v2",
                success=success,
                duration=time.time() - start_time,
                details={
                    'events_published': len(event_ids),
                    'events_processed': len(processed_events),
                    'bus_stats': stats,
                    'metrics': metrics.to_dict(),
                    'health_status': health_report['overall_status'] if health_report else None
                }
            ))
            
        finally:
            bus.stop()
    
    async def test_high_performance_mode(self) -> None:
        """测试高性能模式"""
        start_time = time.time()
        
        # 创建高性能事件总线
        bus = create_high_performance_event_bus("HighPerfTestBus")
        
        # 性能测试数据
        performance_results = []
        
        async def perf_handler(event_data):
            # 模拟轻量级处理
            await asyncio.sleep(0.001)
            # 从事件数据的data字段中获取用户ID
            user_id = event_data.get('data', {}).get('id', event_data.get('id'))
            performance_results.append(user_id)
        
        try:
            bus.start()
            await asyncio.sleep(1.0)
            
            # 订阅事件
            bus.subscribe("perf.test", perf_handler)
            
            # 高频发布事件
            publish_start = time.time()
            event_count = 1000
            
            for i in range(event_count):
                bus.publish("perf.test", {"id": i, "timestamp": time.time()})
            
            publish_time = time.time() - publish_start
            
            # 等待处理完成
            await asyncio.sleep(5.0)
            
            # 获取性能指标
            metrics = bus.get_metrics()
            stats = bus.get_stats()
            
            # 计算性能指标
            publish_rate = event_count / publish_time
            processing_rate = len(performance_results) / (time.time() - publish_start)
            
            success = (
                len(performance_results) >= event_count * 0.95 and  # 至少95%的事件被处理
                publish_rate > 1000 and  # 发布速率 > 1000 events/sec
                metrics.avg_processing_time < 0.1  # 平均处理时间 < 100ms
            )
            
            self.results.append(TestResult(
                test_name="test_high_performance_mode",
                success=success,
                duration=time.time() - start_time,
                details={
                    'events_published': event_count,
                    'events_processed': len(performance_results),
                    'publish_rate': publish_rate,
                    'processing_rate': processing_rate,
                    'avg_processing_time': metrics.avg_processing_time,
                    'max_processing_time': metrics.max_processing_time
                }
            ))
            
        finally:
            bus.stop()
    
    async def test_integration_scenario(self) -> None:
        """测试集成场景"""
        start_time = time.time()
        
        # 创建完整的集成环境
        bus = create_enhanced_event_bus("IntegrationTestBus")
        
        # 集成测试数据
        integration_results = {
            'system_events': [],
            'trading_events': [],
            'market_events': [],
            'error_events': []
        }
        
        # 定义不同类型的处理器
        async def system_handler(event_data):
            await asyncio.sleep(0.01)
            integration_results['system_events'].append(event_data)
        
        async def trading_handler(event_data):
            await asyncio.sleep(0.02)
            integration_results['trading_events'].append(event_data)
            # 模拟交易处理可能的错误
            if random.random() < 0.1:
                raise Exception("Trading processing error")
        
        def market_handler(event_data):
            integration_results['market_events'].append(event_data)
        
        def error_handler(event_data):
            integration_results['error_events'].append(event_data)
        
        try:
            bus.start()
            await asyncio.sleep(1.0)
            
            # 订阅不同类型的事件
            bus.subscribe("system.*", system_handler)
            bus.subscribe("trading.*", trading_handler)
            bus.subscribe("market.*", market_handler)
            bus.subscribe("error.*", error_handler)
            
            # 模拟真实的事件流
            event_types = [
                "system.startup", "system.shutdown", "system.heartbeat",
                "trading.order", "trading.fill", "trading.cancel",
                "market.tick", "market.depth", "market.trade",
                "error.connection", "error.timeout"
            ]
            
            # 发布混合事件
            for i in range(100):
                event_type = random.choice(event_types)
                bus.publish(event_type, {
                    "id": i,
                    "type": event_type,
                    "timestamp": time.time(),
                    "data": f"test_data_{i}"
                })
                
                # 随机延迟模拟真实场景
                if i % 10 == 0:
                    await asyncio.sleep(0.01)
            
            # 等待处理完成
            await asyncio.sleep(3.0)
            
            # 验证集成结果
            total_processed = sum(len(events) for events in integration_results.values())
            stats = bus.get_stats()
            metrics = bus.get_metrics()
            
            success = (
                total_processed >= 80 and  # 至少80%的事件被处理
                len(integration_results['system_events']) > 0 and
                len(integration_results['trading_events']) > 0 and
                len(integration_results['market_events']) > 0 and
                metrics.total_events_published == 100
            )
            
            self.results.append(TestResult(
                test_name="test_integration_scenario",
                success=success,
                duration=time.time() - start_time,
                details={
                    'integration_results': {k: len(v) for k, v in integration_results.items()},
                    'total_processed': total_processed,
                    'bus_stats': stats,
                    'error_rate': metrics.total_events_failed / metrics.total_events_processed if metrics.total_events_processed > 0 else 0
                }
            ))
            
        finally:
            bus.stop()
    
    async def test_stress_performance(self) -> None:
        """压力性能测试"""
        start_time = time.time()
        
        # 创建高性能配置
        config = EventBusConfig(
            name="StressTestBus",
            max_queue_size=50000,
            processing_mode=ProcessingMode.ASYNC_ONLY,
            async_pool_size=20,
            sync_pool_size=1,
            enable_health_monitoring=True,
            enable_circuit_breaker=True
        )
        
        bus = EnhancedEventBus(config)
        
        # 压力测试数据
        stress_results = []
        error_count = 0
        
        async def stress_handler(event_data):
            nonlocal error_count
            try:
                # 模拟变化的处理时间
                processing_time = random.uniform(0.001, 0.01)
                await asyncio.sleep(processing_time)
                
                # 从事件数据的data字段中获取用户ID
                user_id = event_data.get('data', {}).get('id', event_data.get('id'))
                stress_results.append({
                    'id': user_id,
                    'processing_time': processing_time,
                    'timestamp': time.time()
                })
                
                # 模拟偶发错误
                if random.random() < 0.02:  # 2% 错误率
                    raise Exception("Simulated processing error")
                    
            except Exception:
                error_count += 1
                raise
        
        try:
            bus.start()
            await asyncio.sleep(1.0)
            
            # 订阅事件
            bus.subscribe("stress.test", stress_handler)
            
            # 高强度压力测试
            stress_start = time.time()
            event_count = 5000
            
            # 并发发布事件
            async def publish_batch(start_id, batch_size):
                for i in range(batch_size):
                    bus.publish("stress.test", {
                        "id": start_id + i,
                        "batch": start_id // batch_size,
                        "timestamp": time.time()
                    })
            
            # 分批并发发布
            batch_size = 100
            batch_tasks = []
            for i in range(0, event_count, batch_size):
                task = asyncio.create_task(publish_batch(i, min(batch_size, event_count - i)))
                batch_tasks.append(task)
            
            await asyncio.gather(*batch_tasks)
            publish_duration = time.time() - stress_start
            
            # 等待处理完成
            await asyncio.sleep(10.0)
            
            # 获取最终统计
            final_metrics = bus.get_metrics()
            final_stats = bus.get_stats()
            health_report = bus.get_health_report()
            
            # 计算性能指标
            publish_rate = event_count / publish_duration
            success_rate = len(stress_results) / event_count
            error_rate = error_count / event_count
            
            success = (
                success_rate >= 0.95 and  # 成功率 >= 95%
                error_rate <= 0.05 and    # 错误率 <= 5%
                publish_rate > 5000 and   # 发布速率 > 5000 events/sec
                final_metrics.avg_processing_time < 0.05  # 平均处理时间 < 50ms
            )
            
            self.results.append(TestResult(
                test_name="test_stress_performance",
                success=success,
                duration=time.time() - start_time,
                details={
                    'events_published': event_count,
                    'events_processed': len(stress_results),
                    'error_count': error_count,
                    'publish_rate': publish_rate,
                    'success_rate': success_rate,
                    'error_rate': error_rate,
                    'avg_processing_time': final_metrics.avg_processing_time,
                    'max_processing_time': final_metrics.max_processing_time,
                    'health_status': health_report['overall_status'] if health_report else None
                }
            ))
            
        finally:
            bus.stop()
    
    def generate_test_report(self) -> Dict[str, Any]:
        """生成测试报告"""
        total_duration = time.time() - self.start_time
        
        # 统计结果
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r.success)
        failed_tests = total_tests - passed_tests
        
        # 按测试分类统计
        test_categories = {
            'core_components': ['test_async_handler_pool', 'test_event_scheduler', 'test_event_types_safety'],
            'routing_health': ['test_event_router', 'test_health_monitor'],
            'integration': ['test_enhanced_event_bus_v2', 'test_integration_scenario'],
            'performance': ['test_high_performance_mode', 'test_stress_performance']
        }
        
        category_results = {}
        for category, test_names in test_categories.items():
            category_tests = [r for r in self.results if r.test_name in test_names]
            category_results[category] = {
                'total': len(category_tests),
                'passed': sum(1 for r in category_tests if r.success),
                'failed': sum(1 for r in category_tests if not r.success),
                'avg_duration': sum(r.duration for r in category_tests) / len(category_tests) if category_tests else 0
            }
        
        # 性能指标汇总
        performance_summary = {
            'total_async_handlers': len(self.async_handler_results),
            'total_sync_handlers': len(self.sync_handler_results),
            'total_routing_results': len(self.routing_results),
            'total_health_checks': len(self.health_check_results)
        }
        
        # 生成报告
        report = {
            'test_summary': {
                'total_tests': total_tests,
                'passed_tests': passed_tests,
                'failed_tests': failed_tests,
                'success_rate': (passed_tests / total_tests) * 100 if total_tests > 0 else 0,
                'total_duration': total_duration
            },
            'category_results': category_results,
            'performance_summary': performance_summary,
            'detailed_results': [{
                'test_name': r.test_name,
                'success': r.success,
                'duration': r.duration,
                'error': r.error,
                'details': r.details
            } for r in self.results],
            'timestamp': datetime.now().isoformat(),
            'phase': 'Phase 2 - Advanced Features'
        }
        
        return report


async def main():
    """主函数"""
    print("\n" + "="*80)
    print("HOMALOS 事件系统第二阶段优化测试")
    print("="*80)
    
    # 创建测试器
    tester = Phase2OptimizationTester()
    
    try:
        # 运行所有测试
        report = await tester.run_all_tests()
        
        # 输出测试报告
        print("\n" + "-"*60)
        print("测试结果汇总")
        print("-"*60)
        
        summary = report['test_summary']
        print(f"总测试数: {summary['total_tests']}")
        print(f"通过测试: {summary['passed_tests']}")
        print(f"失败测试: {summary['failed_tests']}")
        print(f"成功率: {summary['success_rate']:.1f}%")
        print(f"总耗时: {summary['total_duration']:.2f}秒")
        
        # 分类结果
        print("\n" + "-"*60)
        print("分类测试结果")
        print("-"*60)
        
        for category, results in report['category_results'].items():
            print(f"{category}: {results['passed']}/{results['total']} 通过 (平均耗时: {results['avg_duration']:.2f}s)")
        
        # 性能汇总
        print("\n" + "-"*60)
        print("性能测试汇总")
        print("-"*60)
        
        perf = report['performance_summary']
        print(f"异步处理器执行: {perf['total_async_handlers']}")
        print(f"同步处理器执行: {perf['total_sync_handlers']}")
        print(f"路由测试结果: {perf['total_routing_results']}")
        print(f"健康检查触发: {perf['total_health_checks']}")
        
        # 详细结果
        print("\n" + "-"*60)
        print("详细测试结果")
        print("-"*60)
        
        for result in report['detailed_results']:
            status = "✓ 通过" if result['success'] else "✗ 失败"
            print(f"{result['test_name']}: {status} ({result['duration']:.2f}s)")
            if not result['success'] and result['error']:
                print(f"  错误: {result['error']}")
        
        # 保存详细报告
        with open('phase2_test_report.json', 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\n详细报告已保存到: phase2_test_report.json")
        
        # 最终评估
        if summary['success_rate'] >= 90:
            print("\n🎉 第二阶段优化测试: 优秀 (≥90% 通过率)")
        elif summary['success_rate'] >= 80:
            print("\n✅ 第二阶段优化测试: 良好 (≥80% 通过率)")
        elif summary['success_rate'] >= 70:
            print("\n⚠️  第二阶段优化测试: 及格 (≥70% 通过率)")
        else:
            print("\n❌ 第二阶段优化测试: 需要改进 (<70% 通过率)")
        
    except Exception as e:
        logger.error(f"测试执行失败: {e}", exc_info=True)
        print(f"\n❌ 测试执行失败: {e}")
    
    print("\n" + "="*80)
    print("测试完成")
    print("="*80)


if __name__ == "__main__":
    # 运行测试
    asyncio.run(main())