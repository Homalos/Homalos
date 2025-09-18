#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : test_event_bus_comparison.py
@Date       : 2025/9/18
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 对比测试原版EventBus与增强版EnhancedEventBus的性能
"""

import time
import threading
from concurrent.futures import ThreadPoolExecutor

from src.core.event_bus import EventBus
from src.core.enhanced_event_bus import EnhancedEventBus
from src.core.event import Event
from src.utils.log import get_console_logger

logger = get_console_logger("EventBusComparison")


def benchmark_event_bus(bus_class, bus_name, num_events=1000, event_type_prefix="test"):
    """
    基准测试事件总线性能
    
    Args:
        bus_class: 事件总线类
        bus_name: 事件总线名称
        num_events: 事件数量
        event_type_prefix: 事件类型前缀
    
    Returns:
        dict: 包含性能统计的字典
    """
    logger.info(f"\n{'='*60}")
    logger.info(f"开始测试 {bus_name}")
    logger.info(f"{'='*60}")
    
    # 创建事件总线
    if bus_class == EnhancedEventBus:
        bus = bus_class(
            context=f"{bus_name}Benchmark",
            general_max_workers=50,
            general_add_max_workers=25,
            market_max_workers=100,
            market_add_max_workers=50,
            auto_start=False,
            register_signals=False
        )
    else:
        bus = bus_class(
            context=f"{bus_name}Benchmark",
            max_workers=100,
            auto_start=False,
            register_signals=False
        )
    
    # 统计变量
    processed_count = [0]
    processing_times = []
    thread_names = set()
    
    def event_handler(event: Event):
        start_time = time.time()
        processed_count[0] += 1
        thread_names.add(threading.current_thread().name)
        
        # 模拟一些处理工作
        result = 0
        for i in range(1000):  # 轻量级计算
            result += i
        
        end_time = time.time()
        processing_times.append(end_time - start_time)
    
    def market_handler(event: Event):
        start_time = time.time()
        processed_count[0] += 1
        thread_names.add(threading.current_thread().name)
        
        # 模拟市场数据处理（更轻量级）
        result = 0
        for i in range(500):
            result += i * 2
        
        end_time = time.time()
        processing_times.append(end_time - start_time)
    
    # 订阅事件
    bus.subscribe(f"{event_type_prefix}.general", event_handler)
    bus.subscribe(f"{event_type_prefix}.market", market_handler)
    bus.subscribe("market.tick", market_handler)  # 高频市场事件
    
    # 启动事件总线
    bus.start()
    
    try:
        # 开始基准测试
        logger.info(f"开始发布 {num_events} 个事件...")
        start_time = time.time()
        
        # 发布混合类型的事件
        for i in range(num_events):
            if i % 3 == 0:
                # 普通事件
                event = Event(f"{event_type_prefix}.general", {"id": i, "type": "general"})
                bus.publish(event)
            elif i % 3 == 1:
                # 市场事件
                event = Event(f"{event_type_prefix}.market", {"id": i, "type": "market"})
                bus.publish(event)
            else:
                # 高频市场事件
                event = Event("market.tick", {"id": i, "symbol": "AAPL", "price": 150.0 + i * 0.01})
                bus.publish(event)
        
        publish_time = time.time() - start_time
        
        # 等待所有事件处理完成
        logger.info("等待事件处理完成...")
        timeout = 30  # 30秒超时
        wait_start = time.time()
        
        while processed_count[0] < num_events and (time.time() - wait_start) < timeout:
            time.sleep(0.1)
        
        total_time = time.time() - start_time
        
        # 收集统计信息
        stats = {
            'bus_name': bus_name,
            'total_events': num_events,
            'processed_events': processed_count[0],
            'publish_time': publish_time,
            'total_time': total_time,
            'events_per_second': num_events / total_time if total_time > 0 else 0,
            'unique_threads': len(thread_names),
            'avg_processing_time': sum(processing_times) / len(processing_times) if processing_times else 0,
            'max_processing_time': max(processing_times) if processing_times else 0,
            'min_processing_time': min(processing_times) if processing_times else 0,
        }
        
        # 如果是增强版事件总线，获取线程池统计
        if hasattr(bus, 'get_thread_pool_stats'):
            thread_pool_stats = bus.get_thread_pool_stats()
            stats['thread_pool_stats'] = thread_pool_stats
            
            # 计算总线程池数量
            total_pools = sum(stat['total_pools'] for stat in thread_pool_stats.values())
            stats['total_thread_pools'] = total_pools
        
        # 打印统计结果
        logger.info(f"\n{bus_name} 性能统计:")
        logger.info(f"  发布事件数: {stats['total_events']}")
        logger.info(f"  处理事件数: {stats['processed_events']}")
        logger.info(f"  发布耗时: {stats['publish_time']:.3f} 秒")
        logger.info(f"  总耗时: {stats['total_time']:.3f} 秒")
        logger.info(f"  吞吐量: {stats['events_per_second']:.1f} 事件/秒")
        logger.info(f"  使用线程数: {stats['unique_threads']}")
        logger.info(f"  平均处理时间: {stats['avg_processing_time']*1000:.2f} 毫秒")
        logger.info(f"  最大处理时间: {stats['max_processing_time']*1000:.2f} 毫秒")
        logger.info(f"  最小处理时间: {stats['min_processing_time']*1000:.2f} 毫秒")
        
        if 'thread_pool_stats' in stats:
            logger.info(f"  线程池总数: {stats['total_thread_pools']}")
            for pool_name, pool_stats in stats['thread_pool_stats'].items():
                logger.info(f"    {pool_name}: {pool_stats['total_pools']} 个池, "
                           f"活跃线程 {sum(pool_stats['alive_threads'].values())}")
        
        return stats
        
    finally:
        # 停止事件总线
        bus.stop()
        time.sleep(0.5)  # 给一点时间完全停止


def run_comparison_test():
    """运行对比测试"""
    logger.info("开始事件总线性能对比测试")
    logger.info("="*80)
    
    # 测试配置
    test_configs = [
        {"num_events": 500, "name": "轻量级测试"},
        {"num_events": 2000, "name": "中等负载测试"},
        {"num_events": 5000, "name": "高负载测试"},
    ]
    
    all_results = []
    
    for config in test_configs:
        logger.info(f"\n开始 {config['name']} ({config['num_events']} 个事件)")
        logger.info("="*80)
        
        # 测试原版 EventBus
        try:
            original_stats = benchmark_event_bus(
                EventBus, 
                "原版EventBus", 
                config['num_events'], 
                "original"
            )
            all_results.append(original_stats)
        except Exception as e:
            logger.error(f"原版EventBus测试失败: {e}")
            continue
        
        # 等待一下再测试下一个
        time.sleep(2)
        
        # 测试增强版 EnhancedEventBus
        try:
            enhanced_stats = benchmark_event_bus(
                EnhancedEventBus, 
                "增强版EnhancedEventBus", 
                config['num_events'], 
                "enhanced"
            )
            all_results.append(enhanced_stats)
        except Exception as e:
            logger.error(f"增强版EventBus测试失败: {e}")
            continue
        
        # 对比分析
        if len(all_results) >= 2:
            original = all_results[-2]
            enhanced = all_results[-1]
            
            logger.info(f"\n{config['name']} - 性能对比:")
            logger.info("-" * 60)
            
            # 吞吐量对比
            throughput_improvement = ((enhanced['events_per_second'] - original['events_per_second']) 
                                    / original['events_per_second'] * 100)
            logger.info(f"吞吐量提升: {throughput_improvement:+.1f}%")
            
            # 总时间对比
            time_improvement = ((original['total_time'] - enhanced['total_time']) 
                              / original['total_time'] * 100)
            logger.info(f"总时间改善: {time_improvement:+.1f}%")
            
            # 线程使用对比
            thread_improvement = enhanced['unique_threads'] - original['unique_threads']
            logger.info(f"线程数差异: {thread_improvement:+d}")
            
            # 处理时间对比
            processing_improvement = ((original['avg_processing_time'] - enhanced['avg_processing_time']) 
                                    / original['avg_processing_time'] * 100)
            logger.info(f"平均处理时间改善: {processing_improvement:+.1f}%")
            
            if 'total_thread_pools' in enhanced:
                logger.info(f"增强版线程池总数: {enhanced['total_thread_pools']}")
        
        time.sleep(2)  # 测试间隔
    
    # 最终总结
    logger.info("\n" + "="*80)
    logger.info("测试总结")
    logger.info("="*80)
    
    original_results = [r for r in all_results if "原版" in r['bus_name']]
    enhanced_results = [r for r in all_results if "增强版" in r['bus_name']]
    
    if original_results and enhanced_results:
        # 计算平均性能提升
        avg_throughput_original = sum(r['events_per_second'] for r in original_results) / len(original_results)
        avg_throughput_enhanced = sum(r['events_per_second'] for r in enhanced_results) / len(enhanced_results)
        
        avg_time_original = sum(r['total_time'] for r in original_results) / len(original_results)
        avg_time_enhanced = sum(r['total_time'] for r in enhanced_results) / len(enhanced_results)
        
        overall_throughput_improvement = ((avg_throughput_enhanced - avg_throughput_original) 
                                        / avg_throughput_original * 100)
        overall_time_improvement = ((avg_time_original - avg_time_enhanced) 
                                  / avg_time_original * 100)
        
        logger.info(f"平均吞吐量提升: {overall_throughput_improvement:+.1f}%")
        logger.info(f"平均时间改善: {overall_time_improvement:+.1f}%")
        
        # 推荐使用
        if overall_throughput_improvement > 0:
            logger.info("✓ 推荐使用增强版EnhancedEventBus，性能更优")
        else:
            logger.info("! 在当前测试条件下，性能差异不明显")
    
    logger.info("\n测试完成！")


if __name__ == "__main__":
    run_comparison_test()
