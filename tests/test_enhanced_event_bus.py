#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : test_enhanced_event_bus.py
@Date       : 2025/9/18
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 测试增强版事件总线（使用自定义线程池）
"""

import asyncio
import time
import threading
import traceback

from src.core.enhanced_event_bus import EnhancedEventBus
from src.core.event import Event
from src.utils.log import get_console_logger

# 全局测试统计
test_stats = {
    'passed': 0,
    'failed': 0,
    'errors': []
}

logger = get_console_logger("EnhancedEventBusTest")


def assert_equal(actual, expected, message=""):
    """自定义断言：相等"""
    if actual != expected:
        error_msg = f"断言失败: 期望 {expected}, 实际 {actual}. {message}"
        raise AssertionError(error_msg)


def assert_greater(actual, expected, message=""):
    """自定义断言：大于"""
    if actual <= expected:
        error_msg = f"断言失败: {actual} 应该大于 {expected}. {message}"
        raise AssertionError(error_msg)


def assert_greater_equal(actual, expected, message=""):
    """自定义断言：大于等于"""
    if actual < expected:
        error_msg = f"断言失败: {actual} 应该大于等于 {expected}. {message}"
        raise AssertionError(error_msg)


def assert_true(value, message=""):
    """自定义断言：为True"""
    if not value:
        error_msg = f"断言失败: 期望 True, 实际 {value}. {message}"
        raise AssertionError(error_msg)


def run_test(test_name, test_func):
    """运行单个测试函数"""
    logger.info("=" * 60)
    logger.info(f"开始测试: {test_name}")
    logger.info("=" * 60)
    
    try:
        test_func()
        test_stats['passed'] += 1
        logger.info(f"✓ {test_name} - 测试通过")
    except Exception as e:
        test_stats['failed'] += 1
        test_stats['errors'].append((test_name, str(e)))
        logger.error(f"✗ {test_name} - 测试失败: {e}")
        logger.error(f"错误详情:\n{traceback.format_exc()}")
    
    logger.info("-" * 60)


def test_basic_initialization():
    """测试基本初始化功能"""
    logger.info("测试增强版事件总线基本初始化...")
    
    # 测试默认参数
    bus = EnhancedEventBus(
        context="TestBus",
        auto_start=False,  # 手动启动以便测试
        register_signals=False
    )
    
    assert_equal(bus._context, "TestBus")
    assert_equal(len(bus._executors), 2)
    assert_true("general" in bus._executors)
    assert_true("market" in bus._executors)
    
    # 启动事件总线
    bus.start()
    assert_true(bus.is_active())
    
    # 停止事件总线
    bus.stop()
    
    logger.info("基本初始化测试完成")


def test_thread_pool_stats():
    """测试线程池统计功能"""
    logger.info("测试线程池统计功能...")
    
    bus = EnhancedEventBus(
        context="StatsBus",
        general_max_workers=10,
        general_add_max_workers=5,
        market_max_workers=20,
        market_add_max_workers=10,
        auto_start=False,
        register_signals=False
    )
    
    bus.start()
    
    try:
        # 获取线程池统计信息
        stats = bus.get_thread_pool_stats()
        
        assert_equal(len(stats), 2)
        assert_true("general" in stats)
        assert_true("market" in stats)
        
        # 检查 general 线程池统计
        general_stats = stats["general"]
        assert_equal(general_stats["max_workers"], 10)
        assert_equal(general_stats["add_max_workers"], 5)
        assert_equal(general_stats["current_pool_num"], 1)
        assert_equal(general_stats["next_pool_num"], -1)
        
        # 检查 market 线程池统计
        market_stats = stats["market"]
        assert_equal(market_stats["max_workers"], 20)
        assert_equal(market_stats["add_max_workers"], 10)
        
        logger.info(f"线程池统计信息: {stats}")
        logger.info("线程池统计测试完成")
        
    finally:
        bus.stop()


def test_event_subscription_and_publishing():
    """测试事件订阅和发布"""
    logger.info("测试事件订阅和发布...")
    
    bus = EnhancedEventBus(
        context="PubSubBus",
        auto_start=False,
        register_signals=False
    )
    
    # 用于收集事件的列表
    received_events = []
    
    def event_handler(event: Event):
        received_events.append(event)
        logger.info(f"收到事件: {event.event_type}, 数据: {event.payload}")
    
    def market_handler(event: Event):
        received_events.append(event)
        logger.info(f"收到市场事件: {event.event_type}, 数据: {event.payload}")
    
    # 订阅事件
    bus.subscribe("test.event", event_handler)
    bus.subscribe("market.tick", market_handler)
    
    bus.start()
    
    try:
        # 发布普通事件
        test_event = Event("test.event", {"message": "Hello World"})
        bus.publish(test_event)
        
        # 发布市场事件
        market_event = Event("market.tick", {"symbol": "AAPL", "price": 150.0})
        bus.publish(market_event)
        
        # 等待事件处理完成
        time.sleep(0.5)
        
        # 验证事件被正确接收
        assert_equal(len(received_events), 2)
        assert_equal(received_events[0].event_type, "test.event")
        assert_equal(received_events[1].event_type, "market.tick")
        
        logger.info("事件订阅和发布测试完成")
        
    finally:
        bus.stop()


def test_high_frequency_events():
    """测试高频事件处理"""
    logger.info("测试高频事件处理...")
    
    bus = EnhancedEventBus(
        context="HighFreqBus",
        market_max_workers=5,
        market_add_max_workers=3,
        auto_start=False,
        register_signals=False
    )
    
    # 用于统计处理的事件数量
    processed_count = [0]  # 使用列表以便在闭包中修改
    
    def high_freq_handler(event: Event):
        processed_count[0] += 1
        # 模拟一些处理时间
        time.sleep(0.01)
    
    bus.subscribe("market.tick", high_freq_handler)
    bus.start()
    
    try:
        # 发布大量高频事件
        num_events = 100
        start_time = time.time()
        
        for i in range(num_events):
            event = Event("market.tick", {"tick_id": i, "price": 100 + i * 0.1})
            bus.publish(event)
        
        # 等待所有事件处理完成
        time.sleep(3.0)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # 验证所有事件都被处理
        assert_equal(processed_count[0], num_events)
        
        # 检查线程池扩展情况
        stats = bus.get_thread_pool_stats()
        market_stats = stats["market"]
        
        logger.info(f"处理{num_events}个高频事件，耗时: {duration:.2f}秒")
        logger.info(f"市场线程池统计: {market_stats}")
        
        # 验证线程池可能已扩展（如果负载足够高）
        if market_stats["total_pools"] > 1:
            logger.info("✓ 线程池成功扩展以处理高频事件")
        
        logger.info("高频事件处理测试完成")
        
    finally:
        bus.stop()


def test_concurrent_event_processing():
    """测试并发事件处理"""
    logger.info("测试并发事件处理...")
    
    bus = EnhancedEventBus(
        context="ConcurrentBus",
        general_max_workers=3,
        general_add_max_workers=2,
        auto_start=False,
        register_signals=False
    )
    
    # 用于记录线程信息
    thread_info = []
    
    def concurrent_handler(event: Event):
        thread_name = threading.current_thread().name
        thread_info.append(thread_name)
        # 模拟处理时间
        time.sleep(0.2)
        logger.info(f"事件 {event.payload['id']} 在线程 {thread_name} 中处理")
    
    bus.subscribe("concurrent.test", concurrent_handler)
    bus.start()
    
    try:
        # 并发发布多个事件
        num_events = 10
        for i in range(num_events):
            event = Event("concurrent.test", {"id": i})
            bus.publish(event)
        
        # 等待所有事件处理完成
        time.sleep(3.0)
        
        # 验证事件被并发处理
        assert_equal(len(thread_info), num_events)
        
        # 检查是否使用了多个线程
        unique_threads = set(thread_info)
        assert_greater(len(unique_threads), 1, "应该使用多个线程并发处理")
        
        logger.info(f"使用了 {len(unique_threads)} 个不同的线程: {unique_threads}")
        logger.info("并发事件处理测试完成")
        
    finally:
        bus.stop()


def test_async_event_handling():
    """测试异步事件处理"""
    logger.info("测试异步事件处理...")
    
    bus = EnhancedEventBus(
        context="AsyncBus",
        auto_start=False,
        register_signals=False
    )
    
    # 用于收集异步事件的列表
    async_events = []
    
    async def async_handler(event: Event):
        async_events.append(event)
        await asyncio.sleep(0.1)  # 模拟异步处理
        logger.info(f"异步处理事件: {event.event_type}")
    
    # 订阅异步事件
    bus.subscribe("async.test", async_handler, async_mode=True)
    bus.start()
    
    try:
        # 发布异步事件
        for i in range(5):
            event = Event("async.test", {"async_id": i})
            bus.publish(event, async_mode=True)
        
        # 等待异步事件处理完成
        time.sleep(1.0)
        
        # 验证异步事件被处理
        assert_equal(len(async_events), 5)
        
        logger.info("异步事件处理测试完成")
        
    finally:
        bus.stop()


def test_mixed_event_types():
    """测试混合事件类型处理"""
    logger.info("测试混合事件类型处理...")
    
    bus = EnhancedEventBus(
        context="MixedBus",
        general_max_workers=3,
        market_max_workers=5,
        auto_start=False,
        register_signals=False
    )
    
    # 统计不同类型事件的处理情况
    general_count = [0]
    market_count = [0]
    
    def general_handler(event: Event):
        general_count[0] += 1
        time.sleep(0.05)  # 模拟处理时间
    
    def market_handler(event: Event):
        market_count[0] += 1
        time.sleep(0.02)  # 市场事件处理更快
    
    # 订阅不同类型的事件
    bus.subscribe("general.order", general_handler)
    bus.subscribe("general.account", general_handler)
    bus.subscribe("market.tick", market_handler)
    bus.subscribe("market.depth", market_handler)
    
    bus.start()
    
    try:
        # 混合发布不同类型的事件
        for i in range(20):
            if i % 4 == 0:
                bus.publish(Event("general.order", {"order_id": i}))
            elif i % 4 == 1:
                bus.publish(Event("general.account", {"account_id": i}))
            elif i % 4 == 2:
                bus.publish(Event("market.tick", {"symbol": f"STOCK{i}"}))
            else:
                bus.publish(Event("market.depth", {"symbol": f"STOCK{i}"}))
        
        # 等待所有事件处理完成
        time.sleep(2.0)
        
        # 验证事件分类处理
        assert_equal(general_count[0], 10)  # general.order + general.account
        assert_equal(market_count[0], 10)   # market.tick + market.depth
        
        # 检查线程池使用情况
        stats = bus.get_thread_pool_stats()
        logger.info(f"最终线程池统计: {stats}")
        
        logger.info("混合事件类型处理测试完成")
        
    finally:
        bus.stop()


def run_all_tests():
    """运行所有测试"""
    logger.info("开始运行 EnhancedEventBus 综合测试...")
    logger.info("=" * 80)
    
    # 定义所有测试函数
    tests = [
        ("基本初始化", test_basic_initialization),
        ("线程池统计", test_thread_pool_stats),
        ("事件订阅发布", test_event_subscription_and_publishing),
        ("高频事件处理", test_high_frequency_events),
        ("并发事件处理", test_concurrent_event_processing),
        ("异步事件处理", test_async_event_handling),
        ("混合事件类型", test_mixed_event_types),
    ]
    
    # 运行所有测试
    for test_name, test_func in tests:
        run_test(test_name, test_func)
    
    # 打印测试总结
    logger.info("=" * 80)
    logger.info("测试总结:")
    logger.info(f"✓ 通过: {test_stats['passed']} 个测试")
    logger.info(f"✗ 失败: {test_stats['failed']} 个测试")
    
    if test_stats['errors']:
        logger.error("失败的测试:")
        for test_name, error in test_stats['errors']:
            logger.error(f"  - {test_name}: {error}")
    
    logger.info("=" * 80)


if __name__ == "__main__":
    run_all_tests()
    print("所有测试完成！")
