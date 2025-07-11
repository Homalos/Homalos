#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos_v2
@FileName   : test_performance_framework.py
@Date       : 2025/1/15 16:30
@Author     : Donny
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 性能测试框架 - 端到端、压力测试和基准测试
"""
import asyncio
import statistics
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Any, Optional

import psutil
import pytest

from src.config.config_manager import ConfigManager
from src.config.constant import Direction, OrderType, Exchange
from src.core.event import Event, create_trading_event
from src.core.event_bus import EventBus
from src.core.logger import get_logger
from src.core.object import OrderRequest, TickData
from src.services.data_service import DataService
from src.services.performance_monitor import PerformanceMonitor
from src.services.trading_engine import TradingEngine

logger = get_logger("PerformanceTest")


@dataclass
class TestResult:
    """测试结果数据类"""
    test_name: str
    success: bool
    duration: float
    metrics: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None


@dataclass
class BenchmarkResult:
    """基准测试结果"""
    operation: str
    total_operations: int
    duration: float
    operations_per_second: float
    avg_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    error_count: int
    success_rate: float


class PerformanceTestFramework:
    """性能测试框架"""
    
    def __init__(self) -> None:
        # 测试配置 - 使用专用测试配置文件
        self.test_config = {
            "event_bus_name": "test_trading_system",
            "config_file": "config/test_system.yaml"
        }
        
        # 组件
        self.event_bus: Optional[EventBus] = None
        self.config: Optional[ConfigManager] = None
        self.trading_engine: Optional[TradingEngine] = None
        self.data_service: Optional[DataService] = None
        self.performance_monitor: Optional[PerformanceMonitor] = None
        
        # 测试结果
        self.test_results: List[TestResult] = []
        self.benchmark_results: List[BenchmarkResult] = []
        
        logger.info("性能测试框架初始化完成")
    
    async def setup_test_environment(self) -> bool:
        """设置测试环境 - 增强版"""
        try:
            logger.info("🔧 设置性能测试环境...")
            
            # 初始化基础组件
            self.config = ConfigManager(self.test_config["config_file"])
            self.event_bus = EventBus(name=self.test_config["event_bus_name"])
            
            # 启动事件总线
            self.event_bus.start()
            
            # 等待事件总线完全启动
            await asyncio.sleep(0.5)
            
            # 初始化核心服务
            self.trading_engine = TradingEngine(self.event_bus, self.config)
            self.data_service = DataService(self.event_bus, self.config)
            self.performance_monitor = PerformanceMonitor(self.event_bus, self.config)
            
            # 初始化服务 - 添加重试机制
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    await self.trading_engine.initialize()
                    await self.data_service.initialize()
                    break
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    logger.warning(f"初始化失败，重试 {attempt + 1}/{max_retries}: {e}")
                    await asyncio.sleep(1)
            
            # 启动服务
            await self.trading_engine.start()
            self.performance_monitor.start_monitoring()
            
            # 验证组件状态
            if not self._verify_components_ready():
                raise Exception("组件未正确初始化")
            
            logger.info("✅ 测试环境设置完成")
            return True
            
        except Exception as e:
            logger.error(f"❌ 测试环境设置失败: {e}")
            return False
    
    def _verify_components_ready(self) -> bool:
        """验证组件就绪状态"""
        checks = [
            self.event_bus is not None,
            self.trading_engine is not None,
            self.data_service is not None,
            self.performance_monitor is not None
        ]
        return all(checks)
    
    async def teardown_test_environment(self) -> None:
        """清理测试环境"""
        try:
            logger.info("🧹 清理测试环境...")
            
            if self.performance_monitor:
                self.performance_monitor.stop_monitoring()
            
            if self.trading_engine:
                await self.trading_engine.stop()
            
            if self.data_service:
                await self.data_service.shutdown()
            
            if self.event_bus:
                self.event_bus.stop()
            
            logger.info("✅ 测试环境清理完成")
            
        except Exception as e:
            logger.error(f"❌ 测试环境清理失败: {e}")
    
    async def run_end_to_end_test(self) -> TestResult:
        """端到端测试 - 完整交易流程"""
        test_name = "端到端交易流程测试"
        start_time = time.time()
        
        try:
            logger.info(f"🚀 开始 {test_name}")
            
            # 生成测试策略ID
            strategy_id = f"test_strategy_{uuid.uuid4().hex[:8]}"
            
            # 模拟策略加载
            assert self.trading_engine is not None
            load_success = await self.trading_engine.strategy_manager.load_strategy(
                "src/strategies/minimal_strategy.py",
                strategy_id,
                {
                    "symbol": "FG509",
                    "exchange": "CZCE",
                    "volume": 1,
                    "order_interval": 5,
                    "max_orders": 10
                }
            )
            
            if not load_success:
                raise Exception("策略加载失败")
            
            # 启动策略
            start_success = await self.trading_engine.strategy_manager.start_strategy(strategy_id)
            if not start_success:
                raise Exception("策略启动失败")
            
            # 模拟市场数据
            await self._send_mock_market_data("FG509", 100)
            
            # 模拟下单
            order_request = OrderRequest(
                symbol="FG509",
                exchange=Exchange.CZCE,
                direction=Direction.LONG,
                type=OrderType.LIMIT,
                volume=1,
                price=4500.0
            )
            
            order_id = await self.trading_engine.order_manager.place_order(order_request, strategy_id)
            if not order_id:
                raise Exception("下单失败")
            
            # 等待订单处理
            await asyncio.sleep(1)
            
            # 停止策略
            await self.trading_engine.strategy_manager.stop_strategy(strategy_id)
            
            duration = time.time() - start_time
            
            # 收集性能指标
            assert self.performance_monitor is not None
            performance_metrics = self.performance_monitor.get_performance_summary(strategy_id) if hasattr(self.performance_monitor, 'get_performance_summary') else {}
            system_metrics = self.performance_monitor.get_system_metrics() if hasattr(self.performance_monitor, 'get_system_metrics') else {}
            
            result = TestResult(
                test_name=test_name,
                success=True,
                duration=duration,
                metrics={
                    "strategy_performance": performance_metrics,
                    "system_performance": system_metrics,
                    "order_id": order_id
                }
            )
            
            logger.info(f"✅ {test_name} 完成，耗时: {duration:.3f}秒")
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"❌ {test_name} 失败: {e}")
            
            return TestResult(
                test_name=test_name,
                success=False,
                duration=duration,
                error_message=str(e)
            )
    
    async def run_stress_test(self, concurrent_operations: int = 100, duration_seconds: int = 30) -> TestResult:
        """压力测试 - 并发操作测试"""
        test_name = f"压力测试_{concurrent_operations}并发_{duration_seconds}秒"
        start_time = time.time()
        
        try:
            logger.info(f"🚀 开始 {test_name}")
            
            # 记录系统初始状态
            initial_memory = psutil.virtual_memory().used / 1024 / 1024
            initial_cpu = psutil.cpu_percent()
            
            # 并发任务列表
            tasks = []
            results = []
            
            # 创建并发任务
            for i in range(concurrent_operations):
                task = asyncio.create_task(self._concurrent_trading_operation(f"stress_test_{i}"))
                tasks.append(task)
            
            # 运行指定时间
            test_end_time = start_time + duration_seconds
            completed_count = 0
            error_count = 0
            
            while time.time() < test_end_time and tasks:
                done, pending = await asyncio.wait(tasks, timeout=1.0, return_when=asyncio.FIRST_COMPLETED)
                
                for task in done:
                    tasks.remove(task)
                    try:
                        result = await task
                        results.append(result)
                        completed_count += 1
                    except Exception as e:
                        error_count += 1
                        logger.warning(f"并发任务失败: {e}")
                    
                    # 创建新任务补充
                    if time.time() < test_end_time:
                        new_task = asyncio.create_task(
                            self._concurrent_trading_operation(f"stress_test_{completed_count + error_count}")
                        )
                        tasks.append(new_task)
            
            # 取消剩余任务
            for task in tasks:
                task.cancel()
            
            # 记录系统最终状态
            final_memory = psutil.virtual_memory().used / 1024 / 1024
            final_cpu = psutil.cpu_percent()
            
            duration = time.time() - start_time
            
            # 计算性能指标
            operations_per_second = completed_count / duration
            memory_usage_increase = final_memory - initial_memory
            
            result = TestResult(
                test_name=test_name,
                success=True,
                duration=duration,
                metrics={
                    "completed_operations": completed_count,
                    "error_operations": error_count,
                    "operations_per_second": operations_per_second,
                    "memory_usage_increase_mb": memory_usage_increase,
                    "initial_cpu_percent": initial_cpu,
                    "final_cpu_percent": final_cpu,
                    "success_rate": completed_count / (completed_count + error_count) if (completed_count + error_count) > 0 else 0
                }
            )
            
            logger.info(f"✅ {test_name} 完成")
            logger.info(f"   - 完成操作: {completed_count}")
            logger.info(f"   - 错误操作: {error_count}")
            logger.info(f"   - 每秒操作数: {operations_per_second:.2f}")
            logger.info(f"   - 内存增长: {memory_usage_increase:.2f}MB")
            
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"❌ {test_name} 失败: {e}")
            
            return TestResult(
                test_name=test_name,
                success=False,
                duration=duration,
                error_message=str(e)
            )
    
    async def run_latency_benchmark(self, operation_count: int = 1000) -> BenchmarkResult:
        """延迟基准测试"""
        operation = "订单处理延迟"
        
        try:
            logger.info(f"🚀 开始延迟基准测试 - {operation_count} 次操作")
            
            latencies = []
            error_count = 0
            start_time = time.time()
            
            for i in range(operation_count):
                try:
                    operation_start = time.time()
                    
                    # 执行单次操作
                    await self._single_order_operation(f"benchmark_{i}")
                    
                    operation_end = time.time()
                    latency_ms = (operation_end - operation_start) * 1000
                    latencies.append(latency_ms)
                    
                except Exception as e:
                    error_count += 1
                    logger.debug(f"基准测试操作失败: {e}")
            
            total_duration = time.time() - start_time
            successful_operations = len(latencies)
            
            if successful_operations == 0:
                raise Exception("所有基准测试操作都失败了")
            
            # 计算统计指标
            avg_latency = statistics.mean(latencies)
            p95_latency = statistics.quantiles(latencies, n=20)[18] if len(latencies) >= 20 else max(latencies)
            p99_latency = statistics.quantiles(latencies, n=100)[98] if len(latencies) >= 100 else max(latencies)
            
            result = BenchmarkResult(
                operation=operation,
                total_operations=operation_count,
                duration=total_duration,
                operations_per_second=successful_operations / total_duration,
                avg_latency_ms=avg_latency,
                p95_latency_ms=p95_latency,
                p99_latency_ms=p99_latency,
                error_count=error_count,
                success_rate=successful_operations / operation_count
            )
            
            logger.info(f"✅ 延迟基准测试完成")
            logger.info(f"   - 成功操作: {successful_operations}/{operation_count}")
            logger.info(f"   - 平均延迟: {avg_latency:.2f}ms")
            logger.info(f"   - P95延迟: {p95_latency:.2f}ms")
            logger.info(f"   - P99延迟: {p99_latency:.2f}ms")
            logger.info(f"   - 成功率: {result.success_rate:.2%}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ 延迟基准测试失败: {e}")
            raise
    
    async def run_throughput_benchmark(self, duration_seconds: int = 60) -> BenchmarkResult:
        """吞吐量基准测试"""
        operation = "系统吞吐量"
        
        try:
            logger.info(f"🚀 开始吞吐量基准测试 - {duration_seconds} 秒")
            
            start_time = time.time()
            end_time = start_time + duration_seconds
            
            completed_operations = 0
            error_count = 0
            latencies = []
            
            while time.time() < end_time:
                try:
                    operation_start = time.time()
                    
                    # 执行操作
                    await self._high_frequency_operation(completed_operations)
                    
                    operation_end = time.time()
                    latency_ms = (operation_end - operation_start) * 1000
                    latencies.append(latency_ms)
                    completed_operations += 1
                    
                except Exception as e:
                    error_count += 1
                    logger.debug(f"吞吐量测试操作失败: {e}")
            
            total_duration = time.time() - start_time
            
            if completed_operations == 0:
                raise Exception("吞吐量测试中没有成功的操作")
            
            # 计算统计指标
            avg_latency = statistics.mean(latencies)
            p95_latency = statistics.quantiles(latencies, n=20)[18] if len(latencies) >= 20 else max(latencies)
            p99_latency = statistics.quantiles(latencies, n=100)[98] if len(latencies) >= 100 else max(latencies)
            
            result = BenchmarkResult(
                operation=operation,
                total_operations=completed_operations + error_count,
                duration=total_duration,
                operations_per_second=completed_operations / total_duration,
                avg_latency_ms=avg_latency,
                p95_latency_ms=p95_latency,
                p99_latency_ms=p99_latency,
                error_count=error_count,
                success_rate=completed_operations / (completed_operations + error_count)
            )
            
            logger.info(f"✅ 吞吐量基准测试完成")
            logger.info(f"   - 总操作数: {completed_operations}")
            logger.info(f"   - 错误数: {error_count}")
            logger.info(f"   - 吞吐量: {result.operations_per_second:.2f} ops/s")
            logger.info(f"   - 平均延迟: {avg_latency:.2f}ms")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ 吞吐量基准测试失败: {e}")
            raise
    
    # 辅助方法
    async def _send_mock_market_data(self, symbol: str, count: int) -> None:
        """发送模拟市场数据"""
        base_price = 4500.0
        
        for i in range(count):
            tick_data = TickData(
                symbol=symbol,
                exchange=Exchange.CZCE,
                datetime=datetime.now(),
                last_price=base_price + (i % 10) * 0.2,
                volume=100 + i,
                turnover=(base_price + (i % 10) * 0.2) * (100 + i),
                open_interest=1000 + i,
                gateway_name="send_mock_market_data"
            )
            
            assert self.event_bus is not None
            self.event_bus.publish(Event("market.tick", tick_data))
            await asyncio.sleep(0.001)  # 1ms间隔
    
    async def _concurrent_trading_operation(self, operation_id: str) -> str:
        """并发交易操作"""
        # 模拟策略处理
        await asyncio.sleep(0.001)
        
        # 发布模拟事件
        assert self.event_bus is not None
        self.event_bus.publish(create_trading_event(
            "strategy.signal",
            {
                "action": "place_order",
                "strategy_id": operation_id,
                "order_request": OrderRequest(
                    symbol="FG509",
                    exchange=Exchange.CZCE,
                    direction=Direction.LONG,
                    type=OrderType.LIMIT,
                    volume=1,
                    price=4500.0
                )
            },
            operation_id
        ))
        
        # 模拟处理延迟
        await asyncio.sleep(0.005)
        
        return operation_id
    
    async def _single_order_operation(self, operation_id: str) -> None:
        """单次订单操作"""
        order_request = OrderRequest(
            symbol="FG509",
            exchange=Exchange.CZCE,
            direction=Direction.LONG,
            type=OrderType.LIMIT,
            volume=1,
            price=4500.0
        )
        
        # 发布订单事件
        assert self.event_bus is not None
        self.event_bus.publish(create_trading_event(
            "strategy.signal",
            {
                "action": "place_order",
                "strategy_id": operation_id,
                "order_request": order_request
            },
            operation_id
        ))
        
        # 等待处理
        await asyncio.sleep(0.001)
    
    async def _high_frequency_operation(self, operation_id: int) -> None:
        """高频操作"""
        # 发布高频tick事件
        tick_data = TickData(
            symbol="FG509",
            exchange=Exchange.CZCE,
            datetime=datetime.now(),
            last_price=4500.0 + (operation_id % 100) * 0.1,
            volume=100,
            turnover=450000.0,
            open_interest=1000,
            gateway_name="high_frequency_operation"
        )
        
        assert self.event_bus is not None
        self.event_bus.publish(Event("market.tick", tick_data))
        
        # 微小延迟
        await asyncio.sleep(0.0001)
    
    def generate_performance_report(self) -> Dict[str, Any]:
        """生成性能测试报告"""
        return {
            "test_summary": {
                "total_tests": len(self.test_results),
                "passed_tests": sum(1 for r in self.test_results if r.success),
                "failed_tests": sum(1 for r in self.test_results if not r.success),
                "total_duration": sum(r.duration for r in self.test_results)
            },
            "test_results": [
                {
                    "name": r.test_name,
                    "success": r.success,
                    "duration": r.duration,
                    "metrics": r.metrics,
                    "error": r.error_message
                }
                for r in self.test_results
            ],
            "benchmark_results": [
                {
                    "operation": b.operation,
                    "total_operations": b.total_operations,
                    "duration": b.duration,
                    "ops_per_second": b.operations_per_second,
                    "avg_latency_ms": b.avg_latency_ms,
                    "p95_latency_ms": b.p95_latency_ms,
                    "p99_latency_ms": b.p99_latency_ms,
                    "error_count": b.error_count,
                    "success_rate": b.success_rate
                }
                for b in self.benchmark_results
            ]
        }


# 测试用例
class TestPerformanceFramework:
    """性能测试用例集合"""
    
    @pytest.fixture
    async def performance_framework(self) -> Any:
        """性能测试框架夹具"""
        framework = PerformanceTestFramework()
        setup_success = await framework.setup_test_environment()
        if not setup_success:
            pytest.skip("测试环境设置失败")
        
        yield framework
        
        await framework.teardown_test_environment()
    
    @pytest.mark.asyncio
    async def test_end_to_end_performance(self, performance_framework: Any) -> None:
        """测试端到端性能"""
        result = await performance_framework.run_end_to_end_test()
        performance_framework.test_results.append(result)
        
        assert result.success, f"端到端测试失败: {result.error_message}"
        assert result.duration < 10.0, f"端到端测试耗时过长: {result.duration}秒"
    
    @pytest.mark.asyncio
    async def test_stress_performance(self, performance_framework: Any) -> None:
        """测试压力性能"""
        result = await performance_framework.run_stress_test(concurrent_operations=50, duration_seconds=10)
        performance_framework.test_results.append(result)
        
        assert result.success, f"压力测试失败: {result.error_message}"
        assert result.metrics.get("success_rate", 0) > 0.8, "压力测试成功率过低"
    
    @pytest.mark.asyncio
    async def test_latency_benchmark(self, performance_framework):
        """测试延迟基准"""
        result = await performance_framework.run_latency_benchmark(operation_count=100)
        performance_framework.benchmark_results.append(result)
        
        assert result.success_rate > 0.9, "延迟基准测试成功率过低"
        assert result.avg_latency_ms < 50, f"平均延迟过高: {result.avg_latency_ms}ms"
    
    @pytest.mark.asyncio
    async def test_throughput_benchmark(self, performance_framework):
        """测试吞吐量基准"""
        result = await performance_framework.run_throughput_benchmark(duration_seconds=10)
        performance_framework.benchmark_results.append(result)
        
        assert result.operations_per_second > 100, f"吞吐量过低: {result.operations_per_second} ops/s"
        assert result.success_rate > 0.8, "吞吐量测试成功率过低"


if __name__ == "__main__":
    async def main() -> None:
        """主测试函数"""
        framework = PerformanceTestFramework()
        
        try:
            # 设置测试环境
            if not await framework.setup_test_environment():
                logger.error("测试环境设置失败")
                return
            
            # 运行测试套件
            logger.info("🚀 开始性能测试套件")
            
            # 端到端测试
            e2e_result = await framework.run_end_to_end_test()
            framework.test_results.append(e2e_result)
            
            # 压力测试
            stress_result = await framework.run_stress_test(concurrent_operations=20, duration_seconds=10)
            framework.test_results.append(stress_result)
            
            # 延迟基准测试
            latency_benchmark = await framework.run_latency_benchmark(operation_count=500)
            framework.benchmark_results.append(latency_benchmark)
            
            # 吞吐量基准测试
            throughput_benchmark = await framework.run_throughput_benchmark(duration_seconds=15)
            framework.benchmark_results.append(throughput_benchmark)
            
            # 生成报告
            report = framework.generate_performance_report()
            
            logger.info("📊 性能测试报告:")
            logger.info(f"总测试数: {report['test_summary']['total_tests']}")
            logger.info(f"通过测试: {report['test_summary']['passed_tests']}")
            logger.info(f"失败测试: {report['test_summary']['failed_tests']}")
            logger.info(f"总耗时: {report['test_summary']['total_duration']:.3f}秒")
            
            print("\n" + "="*60)
            print("🎯 Homalos性能测试结果汇总")
            print("="*60)
            
            for result in framework.test_results:
                status = "✅ 通过" if result.success else "❌ 失败"
                print(f"{status} {result.test_name} - {result.duration:.3f}秒")
                if not result.success:
                    print(f"   错误: {result.error_message}")
            
            print("\n基准测试结果:")
            for benchmark in framework.benchmark_results:
                print(f"📈 {benchmark.operation}:")
                print(f"   - 吞吐量: {benchmark.operations_per_second:.2f} ops/s")
                print(f"   - 平均延迟: {benchmark.avg_latency_ms:.2f}ms")
                print(f"   - P95延迟: {benchmark.p95_latency_ms:.2f}ms")
                print(f"   - 成功率: {benchmark.success_rate:.2%}")
            
            print("="*60)
            
        finally:
            await framework.teardown_test_environment()
    
    # 运行测试
    asyncio.run(main()) 