#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : test_thread_pool_simple.py
@Date       : 2025/9/18
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: ThreadPool 线程池的简单测试（不使用unittest）
"""

import threading
import time
import traceback

from src.utils.log import get_console_logger
from src.utils.thread_pool import ThreadPool

# 全局测试统计
test_stats = {
    'passed': 0,
    'failed': 0,
    'errors': []
}

logger = get_console_logger("ThreadPoolTest")


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


def assert_less(actual, expected, message=""):
    """自定义断言：小于"""
    if actual >= expected:
        error_msg = f"断言失败: {actual} 应该小于 {expected}. {message}"
        raise AssertionError(error_msg)


def assert_false(value, message=""):
    """自定义断言：为False"""
    if value:
        error_msg = f"断言失败: 期望 False, 实际 {value}. {message}"
        raise AssertionError(error_msg)


def assert_raises(exception_type, func, *args, **kwargs):
    """自定义断言：抛出异常"""
    try:
        func(*args, **kwargs)
        raise AssertionError(f"期望抛出 {exception_type.__name__} 异常，但没有抛出")
    except exception_type:
        pass  # 期望的异常
    except Exception as e:
        raise AssertionError(f"期望抛出 {exception_type.__name__} 异常，但抛出了 {type(e).__name__}: {e}")


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
    logger.info("测试线程池基本初始化...")
    
    # 测试默认参数
    pool = ThreadPool(max_workers=5)
    assert_equal(pool.max_workers, 5)
    assert_equal(pool.add_max_workers, 5, "默认add_max_workers应该等于max_workers")
    assert_equal(pool.now_pool_num, 1)
    assert_equal(pool.next_pool_num, -1)
    assert_false(pool.prepare_flag)
    
    # 测试自定义参数
    pool2 = ThreadPool(max_workers=10, add_max_workers=8)
    assert_equal(pool2.max_workers, 10)
    assert_equal(pool2.add_max_workers, 8)
    
    # 测试警戒线计算
    assert_equal(pool2.warn_workers_num, 9, "warn_workers_num应该是int(10 * 0.95)")
    assert_equal(pool2.add_warn_workers_num, 7, "add_warn_workers_num应该是int(8 * 0.95)")
    
    pool.clean_pool()
    pool2.clean_pool()
    logger.info("基本初始化测试完成")


def test_context_manager():
    """测试上下文管理器功能"""
    logger.info("测试上下文管理器...")
    
    def simple_task():
        return "task completed"
    
    # 使用上下文管理器
    with ThreadPool(max_workers=3) as pool:
        future = pool.submit(simple_task)
        result = future.result(timeout=5)
        assert_equal(result, "task completed")
    
    logger.info("上下文管理器测试完成")


def test_simple_task_submission():
    """测试简单任务提交"""
    logger.info("测试简单任务提交...")
    
    def add_numbers(a, b):
        return a + b
    
    def multiply_numbers(x, y):
        time.sleep(0.1)  # 模拟工作
        return x * y
    
    pool = ThreadPool(max_workers=3)
    
    try:
        # 提交多个任务
        future1 = pool.submit(add_numbers, 10, 20)
        future2 = pool.submit(multiply_numbers, 5, 6)
        future3 = pool.submit(lambda: "hello world")
        
        # 获取结果
        assert_equal(future1.result(timeout=5), 30)
        assert_equal(future2.result(timeout=5), 30)
        assert_equal(future3.result(timeout=5), "hello world")
        
        logger.info("简单任务提交测试完成")
        
    finally:
        pool.clean_pool()


def test_concurrent_task_execution():
    """测试并发任务执行"""
    logger.info("测试并发任务执行...")
    
    def worker_task(task_id, duration=0.2):
        start_time = time.time()
        time.sleep(duration)
        end_time = time.time()
        return {
            'task_id': task_id,
            'thread_name': threading.current_thread().name,
            'duration': end_time - start_time
        }
    
    pool = ThreadPool(max_workers=5)
    
    try:
        # 提交10个并发任务
        futures = []
        start_time = time.time()
        
        for i in range(10):
            future = pool.submit(worker_task, i, 0.3)
            futures.append(future)
        
        # 收集结果
        results = []
        for future in futures:
            result = future.result(timeout=10)
            results.append(result)
        
        end_time = time.time()
        total_duration = end_time - start_time
        
        # 验证结果
        assert_equal(len(results), 10)
        
        # 检查是否真正并发执行（总时间应该小于串行执行时间）
        assert_less(total_duration, 2.5, "并发执行应该比串行执行更快")
        
        # 检查线程名称的多样性
        thread_names = {result['thread_name'] for result in results}
        assert_greater(len(thread_names), 1, "应该使用多个线程")
        
        logger.info(f"并发任务执行测试完成 - 总耗时: {total_duration:.2f}s, 使用线程数: {len(thread_names)}")
        
    finally:
        pool.clean_pool()


def test_thread_pool_expansion():
    """测试线程池扩展功能"""
    logger.info("测试线程池扩展功能...")
    
    def long_running_task(task_id):
        time.sleep(1)  # 长时间任务
        return f"Task {task_id} completed"
    
    # 使用小的初始线程池
    pool = ThreadPool(max_workers=3, add_max_workers=2)
    
    try:
        # 提交超过初始容量的任务
        futures = []
        for i in range(8):  # 超过初始3个线程的容量
            future = pool.submit(long_running_task, i)
            futures.append(future)
            time.sleep(0.1)  # 稍微延迟，让线程池有时间扩展
        
        # 检查是否创建了额外的线程池
        assert_greater(len(pool.thread_pool_map), 1, "应该创建额外的线程池")
        logger.info(f"线程池数量: {len(pool.thread_pool_map)}")
        
        # 等待所有任务完成
        results = []
        for future in futures:
            result = future.result(timeout=15)
            results.append(result)
        
        assert_equal(len(results), 8)
        logger.info("线程池扩展测试完成")
        
    finally:
        pool.clean_pool()


def test_exception_handling():
    """测试异常处理"""
    logger.info("测试异常处理...")
    
    def failing_task():
        raise ValueError("这是一个测试异常")
    
    def normal_task():
        return "正常完成"
    
    pool = ThreadPool(max_workers=3)
    
    try:
        # 提交会失败的任务
        failing_future = pool.submit(failing_task)
        normal_future = pool.submit(normal_task)
        
        # 检查异常处理
        assert_raises(ValueError, failing_future.result, timeout=5)
        
        # 正常任务应该不受影响
        result = normal_future.result(timeout=5)
        assert_equal(result, "正常完成")
        
        logger.info("异常处理测试完成")
        
    finally:
        pool.clean_pool()


def test_callback_functionality():
    """测试回调功能"""
    logger.info("测试回调功能...")
    
    def test_task(value):
        return value * 2
    
    pool = ThreadPool(max_workers=3)
    
    try:
        # 记录初始活跃线程数
        initial_count = pool.pool_alive_num_map[1]
        
        # 提交任务
        future = pool.submit(test_task, 5)
        
        # 任务提交后，活跃线程数应该增加
        assert_equal(pool.pool_alive_num_map[1], initial_count + 1)
        
        # 等待任务完成
        result = future.result(timeout=5)
        assert_equal(result, 10)
        
        # 稍等一下让回调执行
        time.sleep(0.1)
        
        # 任务完成后，活跃线程数应该恢复
        assert_equal(pool.pool_alive_num_map[1], initial_count)
        
        logger.info("回调功能测试完成")
        
    finally:
        pool.clean_pool()


def test_thread_monitoring():
    """测试线程监控功能"""
    logger.info("测试线程监控功能...")
    
    def monitoring_task():
        time.sleep(0.5)
        return "监控测试"
    
    pool = ThreadPool(max_workers=4)
    
    try:
        # 提交一些任务
        futures = []
        for i in range(3):
            future = pool.submit(monitoring_task)
            futures.append(future)
        
        # 测试监控方法
        time.sleep(0.1)  # 让任务开始执行
        
        # 测试静态方法
        all_threads = ThreadPool.get_pool_all_thread("threadPool")
        thread_count = ThreadPool.get_pool_all_thread_num("threadPool")
        
        assert_greater_equal(len(all_threads), 1)
        assert_greater_equal(thread_count, 1)
        assert_equal(len(all_threads), thread_count)
        
        # 测试实例方法
        pool.show_all_thread()  # 这会打印日志
        
        # 等待任务完成
        for future in futures:
            future.result(timeout=5)
        
        logger.info("线程监控测试完成")
        
    finally:
        pool.clean_pool()


def test_pool_cleanup():
    """测试线程池清理功能"""
    logger.info("测试线程池清理功能...")
    
    def cleanup_test_task():
        time.sleep(0.2)
        return "清理测试"
    
    pool = ThreadPool(max_workers=3, add_max_workers=2)
    
    try:
        # 提交一些任务并创建多个线程池
        futures = []
        for i in range(6):  # 足够触发线程池扩展
            future = pool.submit(cleanup_test_task)
            futures.append(future)
            time.sleep(0.05)
        
        # 等待任务完成
        for future in futures:
            future.result(timeout=5)
        
        # 记录清理前的状态
        pools_before = len(pool.thread_pool_map)
        assert_greater_equal(pools_before, 1)
        
        # 执行清理
        pool.clean_pool()
        
        # 验证清理后的状态
        assert_equal(len(pool.thread_pool_map), 1)
        assert_equal(pool.now_pool_num, 1)
        assert_equal(pool.next_pool_num, -1)
        assert_false(pool.prepare_flag)
        assert_equal(pool.pool_alive_num_map[1], 0)
        
        logger.info(f"线程池清理测试完成 - 清理前: {pools_before}个线程池, 清理后: 1个线程池")
        
    except Exception as e:
        logger.error(f"清理测试失败: {e}")
        raise


def test_stress_testing():
    """压力测试"""
    logger.info("开始压力测试...")
    
    def stress_task(task_id):
        # 模拟一些计算工作
        result = 0
        for i in range(1000):
            result += i
        return f"Task {task_id}: {result}"
    
    pool = ThreadPool(max_workers=5, add_max_workers=3)
    
    try:
        # 提交大量任务
        num_tasks = 50
        futures = []
        start_time = time.time()
        
        for i in range(num_tasks):
            future = pool.submit(stress_task, i)
            futures.append(future)
        
        # 收集所有结果
        results = []
        for future in futures:
            result = future.result(timeout=30)
            results.append(result)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # 验证结果
        assert_equal(len(results), num_tasks)
        
        # 检查性能
        logger.info(f"压力测试完成: {num_tasks}个任务, 耗时: {duration:.2f}s")
        logger.info(f"创建的线程池数量: {len(pool.thread_pool_map)}")
        
        logger.info("压力测试完成")
        
    finally:
        pool.clean_pool()


def test_edge_cases():
    """测试边界情况"""
    logger.info("测试边界情况...")
    
    # 测试最小线程池
    pool1 = ThreadPool(max_workers=1)
    assert_equal(pool1.warn_workers_num, 0, "max_workers=1时，warn_workers_num应该是0")
    
    # 测试回调中的边界情况
    pool2 = ThreadPool(max_workers=2)
    
    try:
        def simple_task():
            return "完成"
        
        future = pool2.submit(simple_task)
        result = future.result(timeout=5)
        assert_equal(result, "完成")
        
        logger.info("边界情况测试完成")
        
    finally:
        pool1.clean_pool()
        pool2.clean_pool()


def run_performance_benchmark():
    """性能基准测试"""
    logger.info("=" * 60)
    logger.info("开始性能基准测试")
    logger.info("=" * 60)
    
    def cpu_intensive_task(n):
        """CPU密集型任务"""
        result = 0
        for i in range(n):
            result += i ** 2
        return result
    
    def io_intensive_task(duration):
        """IO密集型任务（用sleep模拟）"""
        time.sleep(duration)
        return f"IO任务完成，耗时{duration}秒"
    
    # 测试不同配置的性能
    configurations = [
        {"max_workers": 2, "add_max_workers": 2},
        {"max_workers": 4, "add_max_workers": 3},
        {"max_workers": 8, "add_max_workers": 4},
    ]
    
    for config in configurations:
        logger.info(f"\n测试配置: {config}")
        
        with ThreadPool(**config) as pool:
            # CPU密集型测试
            start_time = time.time()
            cpu_futures = [pool.submit(cpu_intensive_task, 10000) for _ in range(10)]
            for future in cpu_futures:
                future.result(timeout=10)
            cpu_duration = time.time() - start_time
            
            # IO密集型测试
            start_time = time.time()
            io_futures = [pool.submit(io_intensive_task, 0.1) for _ in range(20)]
            for future in io_futures:
                future.result(timeout=10)
            io_duration = time.time() - start_time
            
            logger.info(f"CPU密集型任务(10个): {cpu_duration:.2f}秒")
            logger.info(f"IO密集型任务(20个): {io_duration:.2f}秒")
            logger.info(f"创建的线程池数量: {len(pool.thread_pool_map)}")


def run_all_tests():
    """运行所有测试"""
    logger.info("开始运行 ThreadPool 综合测试...")
    logger.info("=" * 80)
    
    # 定义所有测试函数
    tests = [
        ("基本初始化", test_basic_initialization),
        ("上下文管理器", test_context_manager),
        ("简单任务提交", test_simple_task_submission),
        ("并发任务执行", test_concurrent_task_execution),
        ("线程池扩展", test_thread_pool_expansion),
        ("异常处理", test_exception_handling),
        ("回调功能", test_callback_functionality),
        ("线程监控", test_thread_monitoring),
        ("线程池清理", test_pool_cleanup),
        ("压力测试", test_stress_testing),
        ("边界情况", test_edge_cases),
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
    # 运行所有测试
    run_all_tests()
    
    # 运行性能基准测试
    print("\n" + "=" * 80)
    run_performance_benchmark()
    print("所有测试完成！")
