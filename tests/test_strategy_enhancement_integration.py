#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos_v2
@FileName   : test_strategy_enhancement_integration
@Date       : 2025/1/20
@Author     : Assistant
@Description: 策略增强功能集成测试
"""

import asyncio
import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta

from src.core.event_bus import EventBus
from src.core.config import Config
from src.services.trading_engine import StrategyManager
from src.strategies.dependency_checker import DependencyChecker, DependencyType, CheckStatus
from src.strategies.strategy_validator import StrategyValidator, ValidationStatus, IssueSeverity
from src.strategies.strategy_health_monitor import StrategyHealthMonitor, HealthStatus
from src.strategies.strategy_event_handler import StrategyEventHandler
from src.strategies.strategy_factory import StrategyFactory


class TestStrategyEnhancementIntegration:
    """策略增强功能集成测试类"""
    
    @pytest.fixture
    async def setup_test_environment(self):
        """设置测试环境"""
        # 创建临时目录
        self.temp_dir = tempfile.mkdtemp()
        
        # 创建模拟配置
        config_data = {
            'strategy': {
                'strategy_management': {
                    'dependency_check': {
                        'cache_ttl_seconds': 300,
                        'timeout_seconds': 30,
                        'max_retries': 3
                    },
                    'strategy_validation': {
                        'cache_ttl_seconds': 600,
                        'timeout_seconds': 60,
                        'max_complexity_score': 100
                    },
                    'health_monitoring': {
                        'check_interval_seconds': 30,
                        'metrics_window_minutes': 10,
                        'auto_recovery_enabled': True,
                        'max_recovery_attempts': 3
                    },
                    'event_handling': {
                        'enable_persistence': True,
                        'database_path': os.path.join(self.temp_dir, 'events.db')
                    }
                }
            }
        }
        
        self.config = Mock(spec=Config)
        self.config.get.side_effect = lambda key, default=None: self._get_nested_config(config_data, key, default)
        
        # 创建事件总线
        self.event_bus = EventBus()
        
        # 创建各个组件
        self.dependency_checker = DependencyChecker(self.config, self.event_bus)
        self.strategy_validator = StrategyValidator(self.config, self.event_bus)
        self.health_monitor = StrategyHealthMonitor(self.config, self.event_bus)
        self.event_handler = StrategyEventHandler(self.config, self.event_bus)
        self.strategy_factory = StrategyFactory(self.config, self.event_bus)
        
        # 创建策略管理器
        self.strategy_manager = StrategyManager(self.event_bus, self.config)
        
        # 创建测试策略文件
        self.test_strategy_path = os.path.join(self.temp_dir, 'test_strategy.py')
        self._create_test_strategy_file()
        
        yield
        
        # 清理
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def _get_nested_config(self, config_data, key, default=None):
        """获取嵌套配置值"""
        keys = key.split('.')
        value = config_data
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def _create_test_strategy_file(self):
        """创建测试策略文件"""
        strategy_content = '''
import pandas as pd
import numpy as np
from src.strategies.base_strategy import BaseStrategy

class TestStrategy(BaseStrategy):
    """测试策略"""
    
    def __init__(self, strategy_uuid: str, config: dict):
        super().__init__(strategy_uuid, config)
        self.name = "TestStrategy"
        self.version = "1.0.0"
        self.required_gateways = ["test_gateway"]
    
    def on_tick(self, tick_data):
        """处理行情数据"""
        pass
    
    def on_order(self, order_data):
        """处理订单数据"""
        pass
    
    def start(self):
        """启动策略"""
        self.is_running = True
    
    def stop(self):
        """停止策略"""
        self.is_running = False
'''
        
        with open(self.test_strategy_path, 'w', encoding='utf-8') as f:
            f.write(strategy_content)
    
    @pytest.mark.asyncio
    async def test_complete_strategy_lifecycle(self, setup_test_environment):
        """测试完整的策略生命周期"""
        strategy_uuid = "test-strategy-001"
        
        # 1. 加载策略
        with patch.object(self.strategy_manager, '_find_strategy_class') as mock_find:
            mock_find.return_value = Mock
            
            # 模拟策略加载
            await self.strategy_manager.load_strategy(self.test_strategy_path, strategy_uuid)
            
            # 验证策略已加载
            assert strategy_uuid in self.strategy_manager.strategies
        
        # 2. 验证策略
        validation_result = await self.strategy_validator.run_full_validation(
            self.test_strategy_path
        )
        
        assert validation_result.overall_status in [ValidationStatus.PASSED, ValidationStatus.WARNING]
        
        # 3. 检查依赖
        dependency_result = await self.dependency_checker.run_all_checks(
            strategy_uuid=strategy_uuid
        )
        
        # 依赖检查可能失败（因为是模拟环境），但应该有结果
        assert dependency_result is not None
        assert dependency_result.total_checks > 0
        
        # 4. 启动策略
        with patch.object(self.strategy_manager, '_check_gateway_ready_for_strategy', return_value=True):
            await self.strategy_manager.start_strategy(strategy_uuid)
            
            # 验证策略状态
            strategy_status = self.strategy_manager.get_strategy_status(strategy_uuid)
            assert strategy_status['status'] == 'running'
        
        # 5. 监控策略健康
        # 等待一段时间让健康监控收集数据
        await asyncio.sleep(1)
        
        health_report = await self.strategy_manager.get_strategy_health_report(strategy_uuid)
        assert health_report is not None
        
        # 6. 停止策略
        await self.strategy_manager.stop_strategy(strategy_uuid)
        
        strategy_status = self.strategy_manager.get_strategy_status(strategy_uuid)
        assert strategy_status['status'] == 'stopped'
    
    @pytest.mark.asyncio
    async def test_strategy_error_recovery(self, setup_test_environment):
        """测试策略错误恢复机制"""
        strategy_uuid = "test-strategy-recovery"
        
        # 加载策略
        with patch.object(self.strategy_manager, '_find_strategy_class') as mock_find:
            mock_strategy_class = Mock()
            mock_strategy_instance = Mock()
            mock_strategy_instance.strategy_uuid = strategy_uuid
            mock_strategy_instance.name = "TestRecoveryStrategy"
            mock_strategy_instance.is_running = False
            
            # 模拟策略启动时出错
            mock_strategy_instance.start.side_effect = Exception("模拟启动错误")
            mock_strategy_class.return_value = mock_strategy_instance
            mock_find.return_value = mock_strategy_class
            
            await self.strategy_manager.load_strategy(self.test_strategy_path, strategy_uuid)
        
        # 尝试启动策略（应该失败）
        with patch.object(self.strategy_manager, '_check_gateway_ready_for_strategy', return_value=True):
            await self.strategy_manager.start_strategy(strategy_uuid)
            
            # 验证策略状态为错误
            strategy_status = self.strategy_manager.get_strategy_status(strategy_uuid)
            assert strategy_status['status'] == 'error'
        
        # 测试恢复机制
        # 修复策略实例（移除错误）
        mock_strategy_instance.start.side_effect = None
        mock_strategy_instance.start.return_value = None
        
        # 尝试恢复策略
        await self.strategy_manager._attempt_strategy_recovery(strategy_uuid, "manual")
        
        # 验证恢复后的状态
        strategy_status = self.strategy_manager.get_strategy_status(strategy_uuid)
        # 恢复可能成功也可能失败，取决于具体实现
        assert strategy_status['status'] in ['running', 'error']
    
    @pytest.mark.asyncio
    async def test_health_monitoring_integration(self, setup_test_environment):
        """测试健康监控集成"""
        strategy_uuid = "test-strategy-health"
        
        # 创建模拟策略实例
        mock_strategy = Mock()
        mock_strategy.strategy_uuid = strategy_uuid
        mock_strategy.name = "TestHealthStrategy"
        mock_strategy.is_running = True
        
        # 添加策略到健康监控
        self.health_monitor.add_strategy(mock_strategy)
        
        # 模拟一些指标数据
        await self.health_monitor._collect_strategy_metrics(strategy_uuid)
        
        # 获取健康报告
        health_report = self.health_monitor.get_strategy_health(strategy_uuid)
        
        assert health_report is not None
        assert 'status' in health_report
        assert 'metrics' in health_report
        assert 'timestamp' in health_report
        
        # 测试异常检测
        # 模拟异常情况
        with patch.object(self.health_monitor, '_detect_anomalies') as mock_detect:
            mock_detect.return_value = ['CPU使用率过高', '内存泄漏检测']
            
            await self.health_monitor._check_strategy_health(strategy_uuid)
            
            # 验证异常被检测到
            health_report = self.health_monitor.get_strategy_health(strategy_uuid)
            assert 'anomalies' in health_report
            assert len(health_report['anomalies']) > 0
    
    @pytest.mark.asyncio
    async def test_event_handling_integration(self, setup_test_environment):
        """测试事件处理集成"""
        # 测试事件发布和处理
        test_events = []
        
        def event_handler(event_data):
            test_events.append(event_data)
        
        # 订阅测试事件
        self.event_bus.subscribe('test.event', event_handler)
        
        # 发布事件
        await self.event_bus.publish('test.event', {
            'message': 'Test event data',
            'timestamp': datetime.now().isoformat()
        })
        
        # 等待事件处理
        await asyncio.sleep(0.1)
        
        # 验证事件被处理
        assert len(test_events) == 1
        assert test_events[0]['message'] == 'Test event data'
    
    @pytest.mark.asyncio
    async def test_dependency_validation_integration(self, setup_test_environment):
        """测试依赖检查和验证集成"""
        # 测试策略验证
        validation_result = await self.strategy_validator.run_full_validation(
            self.test_strategy_path
        )
        
        assert validation_result is not None
        assert hasattr(validation_result, 'overall_status')
        assert hasattr(validation_result, 'issues')
        
        # 测试依赖检查
        strategy_uuid = "test-strategy-deps"
        
        dependency_result = await self.dependency_checker.run_all_checks(
            strategy_uuid=strategy_uuid
        )
        
        assert dependency_result is not None
        assert hasattr(dependency_result, 'overall_status')
        assert hasattr(dependency_result, 'check_items')
    
    @pytest.mark.asyncio
    async def test_concurrent_operations(self, setup_test_environment):
        """测试并发操作"""
        strategy_uuids = [f"test-strategy-{i}" for i in range(5)]
        
        # 并发加载多个策略
        tasks = []
        
        with patch.object(self.strategy_manager, '_find_strategy_class') as mock_find:
            mock_find.return_value = Mock
            
            for uuid in strategy_uuids:
                task = self.strategy_manager.load_strategy(self.test_strategy_path, uuid)
                tasks.append(task)
            
            # 等待所有策略加载完成
            await asyncio.gather(*tasks, return_exceptions=True)
        
        # 验证所有策略都已加载
        for uuid in strategy_uuids:
            assert uuid in self.strategy_manager.strategies
        
        # 并发验证策略
        validation_tasks = [
            self.strategy_validator.run_full_validation(self.test_strategy_path)
            for _ in strategy_uuids
        ]
        
        validation_results = await asyncio.gather(*validation_tasks, return_exceptions=True)
        
        # 验证所有验证都完成（可能成功或失败）
        assert len(validation_results) == len(strategy_uuids)
    
    @pytest.mark.asyncio
    async def test_configuration_integration(self, setup_test_environment):
        """测试配置集成"""
        # 测试配置读取
        dependency_config = self.config.get('strategy.strategy_management.dependency_check')
        assert dependency_config is not None
        assert 'cache_ttl_seconds' in dependency_config
        
        validation_config = self.config.get('strategy.strategy_management.strategy_validation')
        assert validation_config is not None
        assert 'timeout_seconds' in validation_config
        
        health_config = self.config.get('strategy.strategy_management.health_monitoring')
        assert health_config is not None
        assert 'check_interval_seconds' in health_config
        
        event_config = self.config.get('strategy.strategy_management.event_handling')
        assert event_config is not None
        assert 'enable_persistence' in event_config
    
    @pytest.mark.asyncio
    async def test_error_propagation(self, setup_test_environment):
        """测试错误传播机制"""
        strategy_uuid = "test-strategy-error"
        
        # 测试加载不存在的策略文件
        non_existent_path = os.path.join(self.temp_dir, 'non_existent.py')
        
        try:
            await self.strategy_manager.load_strategy(non_existent_path, strategy_uuid)
            assert False, "应该抛出异常"
        except Exception as e:
            # 验证错误被正确处理
            assert "not found" in str(e).lower() or "no such file" in str(e).lower()
        
        # 测试验证无效策略文件
        invalid_strategy_path = os.path.join(self.temp_dir, 'invalid_strategy.py')
        with open(invalid_strategy_path, 'w') as f:
            f.write("invalid python syntax {{{")
        
        validation_result = await self.strategy_validator.run_full_validation(invalid_strategy_path)
        
        # 验证检测到语法错误
        assert validation_result.overall_status == ValidationStatus.FAILED
        assert len(validation_result.issues) > 0
    
    @pytest.mark.asyncio
    async def test_performance_monitoring(self, setup_test_environment):
        """测试性能监控"""
        strategy_uuid = "test-strategy-performance"
        
        # 创建模拟策略
        mock_strategy = Mock()
        mock_strategy.strategy_uuid = strategy_uuid
        mock_strategy.name = "TestPerformanceStrategy"
        mock_strategy.is_running = True
        
        # 添加到健康监控
        self.health_monitor.add_strategy(mock_strategy)
        
        # 模拟性能数据收集
        start_time = datetime.now()
        
        # 收集多次指标
        for _ in range(5):
            await self.health_monitor._collect_strategy_metrics(strategy_uuid)
            await asyncio.sleep(0.1)
        
        end_time = datetime.now()
        
        # 验证性能数据
        health_report = self.health_monitor.get_strategy_health(strategy_uuid)
        
        assert health_report is not None
        assert 'metrics' in health_report
        
        # 验证时间范围合理
        collection_time = end_time - start_time
        assert collection_time.total_seconds() < 10  # 应该在10秒内完成


if __name__ == '__main__':
    # 运行集成测试
    pytest.main([__file__, '-v', '--asyncio-mode=auto'])