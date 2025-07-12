#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos_v2
@FileName   : strategy_factory.py
@Date       : 2025/7/6 23:00
@Author     : Donny
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 策略工厂 - 统一管理策略的创建和配置
"""
from typing import Dict, Any, Type

from src.strategies.base_strategy import BaseStrategy
from src.strategies.moving_average_strategy import MovingAverageStrategy
from src.strategies.grid_trading_strategy import GridTradingStrategy


class StrategyFactory:
    """
    策略工厂类
    
    作用：
    1. 统一管理所有策略类的注册
    2. 根据策略类型动态创建策略实例
    3. 提供策略配置验证
    4. 支持策略的热加载和热更新
    """
    
    def __init__(self):
        # 策略注册表
        self._strategies: Dict[str, Type[BaseStrategy]] = {}
        self._register_default_strategies()
    
    def _register_default_strategies(self):
        """注册默认策略"""
        self.register_strategy("moving_average", MovingAverageStrategy)
        self.register_strategy("grid_trading", GridTradingStrategy)
    
    def register_strategy(self, strategy_type: str, strategy_class: Type[BaseStrategy]):
        """注册策略类"""
        if not issubclass(strategy_class, BaseStrategy):
            raise ValueError(f"策略类必须继承自BaseStrategy: {strategy_class}")
        
        self._strategies[strategy_type] = strategy_class
        print(f"策略已注册: {strategy_type} -> {strategy_class.__name__}")
    
    def create_strategy(self, strategy_type: str, strategy_id: str, event_bus, params: Dict[str, Any] = None) -> BaseStrategy:
        """
        创建策略实例
        
        Args:
            strategy_type: 策略类型
            strategy_id: 策略ID
            event_bus: 事件总线
            params: 策略参数
            
        Returns:
            策略实例
            
        Raises:
            ValueError: 未知的策略类型
        """
        strategy_class = self._strategies.get(strategy_type)
        if not strategy_class:
            available_strategies = list(self._strategies.keys())
            raise ValueError(f"未知的策略类型: {strategy_type}. 可用策略: {available_strategies}")
        
        # 创建策略实例
        strategy = strategy_class(strategy_id, event_bus, params or {})
        return strategy
    
    def get_available_strategies(self) -> Dict[str, Dict[str, Any]]:
        """获取所有可用策略的信息"""
        strategies_info = {}
        
        for strategy_type, strategy_class in self._strategies.items():
            strategies_info[strategy_type] = {
                "class_name": strategy_class.__name__,
                "strategy_name": getattr(strategy_class, 'strategy_name', 'Unknown'),
                "version": getattr(strategy_class, 'version', '1.0.0'),
                "description": getattr(strategy_class, 'description', ''),
                "authors": getattr(strategy_class, 'authors', [])
            }
        
        return strategies_info
    
    def validate_strategy_config(self, strategy_type: str, config: Dict[str, Any]) -> bool:
        """
        验证策略配置
        
        Args:
            strategy_type: 策略类型
            config: 策略配置
            
        Returns:
            配置是否有效
        """
        if strategy_type not in self._strategies:
            return False
        
        # 这里可以添加更详细的配置验证逻辑
        # 例如检查必需参数、参数类型、参数范围等
        
        return True


# 全局策略工厂实例
strategy_factory = StrategyFactory()


def create_strategy(strategy_type: str, strategy_id: str, event_bus, params: Dict[str, Any] = None) -> BaseStrategy:
    """
    便捷函数：创建策略实例
    
    Args:
        strategy_type: 策略类型
        strategy_id: 策略ID
        event_bus: 事件总线
        params: 策略参数
        
    Returns:
        策略实例
    """
    return strategy_factory.create_strategy(strategy_type, strategy_id, event_bus, params)


def register_strategy(strategy_type: str, strategy_class: Type[BaseStrategy]):
    """
    便捷函数：注册策略类
    
    Args:
        strategy_type: 策略类型
        strategy_class: 策略类
    """
    strategy_factory.register_strategy(strategy_type, strategy_class)


def get_available_strategies() -> Dict[str, Dict[str, Any]]:
    """
    便捷函数：获取所有可用策略信息
    
    Returns:
        策略信息字典
    """
    return strategy_factory.get_available_strategies()


# 示例策略配置
EXAMPLE_STRATEGIES = {
    "ma_sa2509": {
        "type": "moving_average",
        "params": {
            "symbol": "SA509",
            "exchange": "CZCE",
            "short_window": 10,
            "long_window": 30,
            "volume": 1,
            "stop_loss": 0.02,
            "take_profit": 0.05
        }
    },
    "grid_fg2509": {
        "type": "grid_trading",
        "params": {
            "symbol": "FG509",
            "exchange": "CZCE",
            "grid_spacing": 5.0,
            "grid_count": 3,
            "base_volume": 1
        }
    }
} 