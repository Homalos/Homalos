#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos_v2
@FileName   : health_monitor
@Date       : 2025/1/16
@Author     : Donny
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 系统健康监控 - 第二阶段优化核心组件
提供全面的系统健康检查、监控和告警机制
"""

import asyncio
import threading
import time
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Callable

import psutil

from src.core.logger import get_logger

logger = get_logger("HealthMonitor")


class HealthStatus(Enum):
    """健康状态枚举"""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"
    DEGRADED = "degraded"


class CheckType(Enum):
    """检查类型枚举"""
    SYSTEM = "system"  # 系统资源检查
    APPLICATION = "application"  # 应用程序检查
    DEPENDENCY = "dependency"  # 依赖服务检查
    CUSTOM = "custom"  # 自定义检查
    PERFORMANCE = "performance"  # 性能检查


@dataclass
class HealthCheckResult:
    """健康检查结果"""
    check_name: str
    status: HealthStatus
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    execution_time: float = 0.0
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'check_name': self.check_name,
            'status': self.status.value,
            'message': self.message,
            'details': self.details,
            'timestamp': self.timestamp,
            'execution_time': self.execution_time,
            'error': self.error
        }
    
    def is_healthy(self) -> bool:
        """是否健康"""
        return self.status == HealthStatus.HEALTHY
    
    def is_critical(self) -> bool:
        """是否严重"""
        return self.status == HealthStatus.CRITICAL


@dataclass
class SystemMetrics:
    """系统指标"""
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    disk_percent: float = 0.0
    network_io: Dict[str, int] = field(default_factory=dict)
    disk_io: Dict[str, int] = field(default_factory=dict)
    process_count: int = 0
    thread_count: int = 0
    open_files: int = 0
    timestamp: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'cpu_percent': self.cpu_percent,
            'memory_percent': self.memory_percent,
            'disk_percent': self.disk_percent,
            'network_io': self.network_io,
            'disk_io': self.disk_io,
            'process_count': self.process_count,
            'thread_count': self.thread_count,
            'open_files': self.open_files,
            'timestamp': self.timestamp
        }


class HealthCheck(ABC):
    """健康检查基类"""
    
    def __init__(self,
                 name: str,
                 check_type: CheckType = CheckType.CUSTOM,
                 interval: float = 60.0,
                 timeout: float = 30.0,
                 enabled: bool = True,
                 critical: bool = False):
        
        self.name = name
        self.check_type = check_type
        self.interval = interval
        self.timeout = timeout
        self.enabled = enabled
        self.critical = critical
        
        self._last_check_time = 0.0
        self._last_result: Optional[HealthCheckResult] = None
    
    @abstractmethod
    async def check(self) -> HealthCheckResult:
        """执行健康检查"""
        pass
    
    def should_run(self) -> bool:
        """是否应该运行检查"""
        if not self.enabled:
            return False
        
        return time.time() - self._last_check_time >= self.interval
    
    def get_last_result(self) -> Optional[HealthCheckResult]:
        """获取最后一次检查结果"""
        return self._last_result
    
    def set_last_result(self, result: HealthCheckResult) -> None:
        """设置最后一次检查结果"""
        self._last_result = result
        self._last_check_time = time.time()


class SystemResourceCheck(HealthCheck):
    """系统资源检查"""
    
    def __init__(self,
                 cpu_threshold: float = 80.0,
                 memory_threshold: float = 80.0,
                 disk_threshold: float = 90.0,
                 **kwargs):
        
        super().__init__("system_resources", CheckType.SYSTEM, **kwargs)
        self.cpu_threshold = cpu_threshold
        self.memory_threshold = memory_threshold
        self.disk_threshold = disk_threshold
    
    async def check(self) -> HealthCheckResult:
        """检查系统资源"""
        try:
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # 内存使用率
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # 磁盘使用率
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            
            # 判断状态
            status = HealthStatus.HEALTHY
            messages = []
            
            if cpu_percent > self.cpu_threshold:
                status = HealthStatus.WARNING if cpu_percent < 95 else HealthStatus.CRITICAL
                messages.append(f"High CPU usage: {cpu_percent:.1f}%")
            
            if memory_percent > self.memory_threshold:
                if status != HealthStatus.CRITICAL:
                    status = HealthStatus.WARNING if memory_percent < 95 else HealthStatus.CRITICAL
                messages.append(f"High memory usage: {memory_percent:.1f}%")
            
            if disk_percent > self.disk_threshold:
                if status != HealthStatus.CRITICAL:
                    status = HealthStatus.WARNING if disk_percent < 98 else HealthStatus.CRITICAL
                messages.append(f"High disk usage: {disk_percent:.1f}%")
            
            message = "; ".join(messages) if messages else "System resources are healthy"
            
            return HealthCheckResult(
                check_name=self.name,
                status=status,
                message=message,
                details={
                    'cpu_percent': cpu_percent,
                    'memory_percent': memory_percent,
                    'disk_percent': disk_percent,
                    'thresholds': {
                        'cpu': self.cpu_threshold,
                        'memory': self.memory_threshold,
                        'disk': self.disk_threshold
                    }
                }
            )
            
        except Exception as e:
            return HealthCheckResult(
                check_name=self.name,
                status=HealthStatus.UNKNOWN,
                message=f"Failed to check system resources: {str(e)}",
                error=str(e)
            )


class EventBusHealthCheck(HealthCheck):
    """事件总线健康检查"""
    
    def __init__(self, event_bus, **kwargs):
        super().__init__("event_bus", CheckType.APPLICATION, **kwargs)
        self.event_bus = event_bus
    
    async def check(self) -> HealthCheckResult:
        """检查事件总线健康状态"""
        try:
            if not hasattr(self.event_bus, 'is_running') or not self.event_bus.is_running:
                return HealthCheckResult(
                    check_name=self.name,
                    status=HealthStatus.CRITICAL,
                    message="Event bus is not running"
                )
            
            # 获取事件总线统计
            stats = self.event_bus.get_stats() if hasattr(self.event_bus, 'get_stats') else {}
            
            # 检查队列大小
            queue_size = stats.get('queue_size', 0)
            max_queue_size = stats.get('max_queue_size', 1000)
            queue_usage = (queue_size / max_queue_size) * 100 if max_queue_size > 0 else 0
            
            # 检查错误率
            total_processed = stats.get('total_processed', 0)
            total_errors = stats.get('total_errors', 0)
            error_rate = (total_errors / total_processed) * 100 if total_processed > 0 else 0
            
            # 判断状态
            status = HealthStatus.HEALTHY
            messages = []
            
            if queue_usage > 80:
                status = HealthStatus.WARNING if queue_usage < 95 else HealthStatus.CRITICAL
                messages.append(f"High queue usage: {queue_usage:.1f}%")
            
            if error_rate > 5:
                if status != HealthStatus.CRITICAL:
                    status = HealthStatus.WARNING if error_rate < 20 else HealthStatus.CRITICAL
                messages.append(f"High error rate: {error_rate:.1f}%")
            
            message = "; ".join(messages) if messages else "Event bus is healthy"
            
            return HealthCheckResult(
                check_name=self.name,
                status=status,
                message=message,
                details={
                    'queue_size': queue_size,
                    'queue_usage_percent': queue_usage,
                    'error_rate_percent': error_rate,
                    'stats': stats
                }
            )
            
        except Exception as e:
            return HealthCheckResult(
                check_name=self.name,
                status=HealthStatus.UNKNOWN,
                message=f"Failed to check event bus: {str(e)}",
                error=str(e)
            )


class DatabaseHealthCheck(HealthCheck):
    """数据库健康检查"""
    
    def __init__(self, connection_func: Callable, **kwargs):
        super().__init__("database", CheckType.DEPENDENCY, **kwargs)
        self.connection_func = connection_func
    
    async def check(self) -> HealthCheckResult:
        """检查数据库连接"""
        try:
            start_time = time.time()
            
            # 尝试连接数据库
            connection = await self.connection_func()
            
            # 执行简单查询
            # 这里需要根据具体数据库类型实现
            # cursor = connection.cursor()
            # cursor.execute("SELECT 1")
            # result = cursor.fetchone()
            
            connection_time = time.time() - start_time
            
            # 判断连接时间
            status = HealthStatus.HEALTHY
            if connection_time > 5.0:
                status = HealthStatus.WARNING
            elif connection_time > 10.0:
                status = HealthStatus.CRITICAL
            
            return HealthCheckResult(
                check_name=self.name,
                status=status,
                message=f"Database connection successful (time: {connection_time:.2f}s)",
                details={
                    'connection_time': connection_time,
                    'status': 'connected'
                }
            )
            
        except Exception as e:
            return HealthCheckResult(
                check_name=self.name,
                status=HealthStatus.CRITICAL,
                message=f"Database connection failed: {str(e)}",
                error=str(e)
            )


class CustomHealthCheck(HealthCheck):
    """自定义健康检查"""
    
    def __init__(self, name: str, check_func: Callable, **kwargs):
        super().__init__(name, CheckType.CUSTOM, **kwargs)
        self.check_func = check_func
    
    async def check(self) -> HealthCheckResult:
        """执行自定义检查"""
        try:
            if asyncio.iscoroutinefunction(self.check_func):
                result = await self.check_func()
            else:
                result = self.check_func()
            
            if isinstance(result, HealthCheckResult):
                return result
            elif isinstance(result, dict):
                return HealthCheckResult(
                    check_name=self.name,
                    status=HealthStatus(result.get('status', 'healthy')),
                    message=result.get('message', ''),
                    details=result.get('details', {})
                )
            else:
                return HealthCheckResult(
                    check_name=self.name,
                    status=HealthStatus.HEALTHY if result else HealthStatus.CRITICAL,
                    message=str(result)
                )
                
        except Exception as e:
            return HealthCheckResult(
                check_name=self.name,
                status=HealthStatus.UNKNOWN,
                message=f"Custom check failed: {str(e)}",
                error=str(e)
            )


class HealthMonitor:
    """
    系统健康监控器
    
    功能特性：
    1. 多种健康检查支持
    2. 自动定期检查
    3. 健康状态聚合
    4. 告警通知
    5. 历史数据记录
    """
    
    def __init__(self,
                 name: str = "HealthMonitor",
                 check_interval: float = 30.0,
                 history_size: int = 1000,
                 enable_alerts: bool = True):
        
        self._name = name
        self._check_interval = check_interval
        self._history_size = history_size
        self._enable_alerts = enable_alerts
        
        # 健康检查
        self._checks: Dict[str, HealthCheck] = {}
        self._checks_lock = threading.Lock()
        
        # 监控状态
        self._running = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        # 结果存储
        self._latest_results: Dict[str, HealthCheckResult] = {}
        self._results_history: deque = deque(maxlen=history_size)
        self._system_metrics_history: deque = deque(maxlen=history_size)
        
        # 告警回调
        self._alert_callbacks: List[Callable] = []
        
        # 统计信息
        self._stats = {
            'total_checks': 0,
            'healthy_checks': 0,
            'warning_checks': 0,
            'critical_checks': 0,
            'unknown_checks': 0,
            'last_check_time': 0.0,
            'avg_check_time': 0.0
        }
        
        logger.info(f"HealthMonitor '{name}' initialized")
    
    def add_check(self, check: HealthCheck) -> None:
        """添加健康检查"""
        with self._checks_lock:
            self._checks[check.name] = check
        
        logger.info(f"Added health check: {check.name} ({check.check_type.value})")
    
    def remove_check(self, check_name: str) -> bool:
        """移除健康检查"""
        with self._checks_lock:
            if check_name in self._checks:
                del self._checks[check_name]
                if check_name in self._latest_results:
                    del self._latest_results[check_name]
                logger.info(f"Removed health check: {check_name}")
                return True
        return False
    
    def get_check(self, check_name: str) -> Optional[HealthCheck]:
        """获取健康检查"""
        return self._checks.get(check_name)
    
    def list_checks(self) -> List[str]:
        """列出所有健康检查"""
        return list(self._checks.keys())
    
    def add_alert_callback(self, callback: Callable) -> None:
        """添加告警回调"""
        self._alert_callbacks.append(callback)
        logger.info(f"Added alert callback: {callback.__name__}")
    
    def remove_alert_callback(self, callback: Callable) -> bool:
        """移除告警回调"""
        if callback in self._alert_callbacks:
            self._alert_callbacks.remove(callback)
            logger.info(f"Removed alert callback: {callback.__name__}")
            return True
        return False
    
    def start(self) -> None:
        """启动健康监控"""
        if self._running:
            logger.warning(f"HealthMonitor '{self._name}' is already running")
            return
        
        self._running = True
        self._stop_event.clear()
        
        # 启动监控线程
        self._monitor_thread = threading.Thread(
            target=self._monitoring_loop,
            name=f"{self._name}-Monitor",
            daemon=True
        )
        self._monitor_thread.start()
        
        logger.info(f"HealthMonitor '{self._name}' started")
    
    def stop(self, timeout: float = 30.0) -> None:
        """停止健康监控"""
        if not self._running:
            return
        
        logger.info(f"Stopping HealthMonitor '{self._name}'...")
        
        self._running = False
        self._stop_event.set()
        
        # 等待监控线程结束
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=timeout)
            
            if self._monitor_thread.is_alive():
                logger.warning(f"Monitor thread did not stop within timeout")
        
        logger.info(f"HealthMonitor '{self._name}' stopped")
    
    def _monitoring_loop(self) -> None:
        """监控主循环"""
        logger.debug(f"Monitoring loop started for '{self._name}'")
        
        while self._running and not self._stop_event.is_set():
            try:
                # 执行健康检查
                self._run_health_checks()
                
                # 收集系统指标
                self._collect_system_metrics()
                
                # 等待下一个检查周期
                self._stop_event.wait(self._check_interval)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}", exc_info=True)
                time.sleep(1.0)  # 避免错误循环
        
        logger.debug(f"Monitoring loop stopped for '{self._name}'")
    
    def _run_health_checks(self) -> None:
        """运行健康检查"""
        start_time = time.time()
        
        with self._checks_lock:
            checks_to_run = [(name, check) for name, check in self._checks.items() 
                           if check.should_run()]
        
        if not checks_to_run:
            return
        
        # 始终在新线程中创建新的事件循环来运行检查
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(self._run_checks_sync, checks_to_run)
            results = future.result()
        
        # 处理结果
        for result in results:
            self._process_check_result(result)
        
        # 更新统计
        check_time = time.time() - start_time
        self._update_stats(results, check_time)
    
    def _run_checks_sync(self, checks: List[tuple]) -> List[HealthCheckResult]:
        """在新线程中同步运行检查"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            return loop.run_until_complete(self._run_checks_async(checks))
        finally:
            loop.close()
    
    async def _run_checks_async(self, checks: List[tuple]) -> List[HealthCheckResult]:
        """异步运行检查"""
        tasks = []
        
        for check_name, check in checks:
            task = asyncio.create_task(self._run_single_check(check))
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理异常
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                check_name = checks[i][0]
                processed_results.append(HealthCheckResult(
                    check_name=check_name,
                    status=HealthStatus.UNKNOWN,
                    message=f"Check execution failed: {str(result)}",
                    error=str(result)
                ))
            else:
                processed_results.append(result)
        
        return processed_results
    
    async def _run_single_check(self, check: HealthCheck) -> HealthCheckResult:
        """运行单个检查"""
        start_time = time.time()
        
        try:
            # 设置超时
            result = await asyncio.wait_for(check.check(), timeout=check.timeout)
            result.execution_time = time.time() - start_time
            
            # 更新检查的最后结果
            check.set_last_result(result)
            
            return result
            
        except asyncio.TimeoutError:
            return HealthCheckResult(
                check_name=check.name,
                status=HealthStatus.CRITICAL,
                message=f"Check timed out after {check.timeout}s",
                execution_time=time.time() - start_time,
                error="Timeout"
            )
        except Exception as e:
            return HealthCheckResult(
                check_name=check.name,
                status=HealthStatus.UNKNOWN,
                message=f"Check failed: {str(e)}",
                execution_time=time.time() - start_time,
                error=str(e)
            )
    
    def _process_check_result(self, result: HealthCheckResult) -> None:
        """处理检查结果"""
        # 存储最新结果
        self._latest_results[result.check_name] = result
        
        # 添加到历史记录
        self._results_history.append(result)
        
        # 检查是否需要告警
        if self._enable_alerts and (result.status in [HealthStatus.WARNING, HealthStatus.CRITICAL]):
            self._trigger_alerts(result)
        
        logger.debug(f"Health check result: {result.check_name} -> {result.status.value}")
    
    def _trigger_alerts(self, result: HealthCheckResult) -> None:
        """触发告警"""
        for callback in self._alert_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    # 异步回调需要在事件循环中执行
                    try:
                        loop = asyncio.get_running_loop()
                        asyncio.create_task(callback(result))
                    except RuntimeError:
                        # 没有运行中的事件循环，在线程池中执行
                        import concurrent.futures
                        with concurrent.futures.ThreadPoolExecutor() as executor:
                            future = executor.submit(asyncio.run, callback(result))
                            future.result(timeout=5.0)  # 5秒超时
                else:
                    callback(result)
            except Exception as e:
                logger.error(f"Alert callback failed: {e}", exc_info=True)
    
    def _collect_system_metrics(self) -> None:
        """收集系统指标"""
        try:
            metrics = SystemMetrics(
                cpu_percent=psutil.cpu_percent(),
                memory_percent=psutil.virtual_memory().percent,
                disk_percent=(psutil.disk_usage('/').used / psutil.disk_usage('/').total) * 100,
                network_io=psutil.net_io_counters()._asdict(),
                disk_io=psutil.disk_io_counters()._asdict(),
                process_count=len(psutil.pids()),
                thread_count=threading.active_count(),
                open_files=len(psutil.Process().open_files()) if hasattr(psutil.Process(), 'open_files') else 0
            )
            
            self._system_metrics_history.append(metrics)
            
        except Exception as e:
            logger.error(f"Failed to collect system metrics: {e}", exc_info=True)
    
    def _update_stats(self, results: List[HealthCheckResult], check_time: float) -> None:
        """更新统计信息"""
        self._stats['total_checks'] += len(results)
        self._stats['last_check_time'] = time.time()
        
        # 更新平均检查时间
        if self._stats['avg_check_time'] == 0:
            self._stats['avg_check_time'] = check_time
        else:
            self._stats['avg_check_time'] = self._stats['avg_check_time'] * 0.9 + check_time * 0.1
        
        # 统计各状态数量
        status_counts = defaultdict(int)
        for result in results:
            status_counts[result.status] += 1
        
        self._stats['healthy_checks'] = status_counts[HealthStatus.HEALTHY]
        self._stats['warning_checks'] = status_counts[HealthStatus.WARNING]
        self._stats['critical_checks'] = status_counts[HealthStatus.CRITICAL]
        self._stats['unknown_checks'] = status_counts[HealthStatus.UNKNOWN]
    
    def get_overall_health(self) -> HealthStatus:
        """获取整体健康状态"""
        if not self._latest_results:
            return HealthStatus.UNKNOWN
        
        # 如果有任何严重问题，整体状态为严重
        for result in self._latest_results.values():
            if result.status == HealthStatus.CRITICAL:
                return HealthStatus.CRITICAL
        
        # 如果有警告，整体状态为警告
        for result in self._latest_results.values():
            if result.status == HealthStatus.WARNING:
                return HealthStatus.WARNING
        
        # 如果有未知状态，整体状态为降级
        for result in self._latest_results.values():
            if result.status == HealthStatus.UNKNOWN:
                return HealthStatus.DEGRADED
        
        # 否则为健康
        return HealthStatus.HEALTHY
    
    def get_health_report(self) -> Dict[str, Any]:
        """获取健康报告"""
        overall_status = self.get_overall_health()
        
        # 按状态分组检查结果
        results_by_status = defaultdict(list)
        for result in self._latest_results.values():
            results_by_status[result.status.value].append(result.to_dict())
        
        # 获取最新系统指标
        latest_metrics = self._system_metrics_history[-1].to_dict() if self._system_metrics_history else {}
        
        return {
            'overall_status': overall_status.value,
            'timestamp': time.time(),
            'total_checks': len(self._latest_results),
            'results_by_status': dict(results_by_status),
            'latest_results': {name: result.to_dict() for name, result in self._latest_results.items()},
            'system_metrics': latest_metrics,
            'stats': self._stats.copy()
        }
    
    def get_check_history(self, check_name: str, limit: int = 100) -> List[Dict[str, Any]]:
        """获取检查历史"""
        history = []
        for result in reversed(self._results_history):
            if result.check_name == check_name:
                history.append(result.to_dict())
                if len(history) >= limit:
                    break
        return history
    
    def get_system_metrics_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取系统指标历史"""
        return [metrics.to_dict() for metrics in list(self._system_metrics_history)[-limit:]]
    
    def run_check_now(self, check_name: str) -> Optional[HealthCheckResult]:
        """立即运行指定检查"""
        check = self.get_check(check_name)
        if check is None:
            return None
        
        # 使用线程池来避免事件循环冲突
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(self._run_checks_sync, [(check_name, check)])
            results = future.result()
            
        if results:
            result = results[0]
            self._process_check_result(result)
            return result
        
        return None
    
    def get_stats(self) -> Dict[str, Any]:
        """获取监控统计"""
        return {
            'name': self._name,
            'running': self._running,
            'check_interval': self._check_interval,
            'total_checks_registered': len(self._checks),
            'enabled_checks': len([c for c in self._checks.values() if c.enabled]),
            'overall_health': self.get_overall_health().value,
            'stats': self._stats.copy(),
            'alert_callbacks': len(self._alert_callbacks)
        }
    
    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
        return False


# 便捷函数
def create_system_health_monitor(name: str = "SystemHealthMonitor") -> HealthMonitor:
    """创建系统健康监控器"""
    monitor = HealthMonitor(name)
    
    # 添加系统资源检查
    monitor.add_check(SystemResourceCheck())
    
    return monitor


def create_event_bus_health_monitor(event_bus, name: str = "EventBusHealthMonitor") -> HealthMonitor:
    """创建事件总线健康监控器"""
    monitor = HealthMonitor(name)
    
    # 添加事件总线检查
    monitor.add_check(EventBusHealthCheck(event_bus))
    
    # 添加系统资源检查
    monitor.add_check(SystemResourceCheck())
    
    return monitor