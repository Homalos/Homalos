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
from typing import Dict, Any, Type, Optional, Tuple

from src.strategies.moving_average_strategy import MovingAverageStrategy
from src.strategies.grid_trading_strategy import GridTradingStrategy
from src.config.config_manager import ConfigManager
from src.core.event_bus import EventBus
from src.core.logger import get_logger
from src.strategy.base_strategy import BaseStrategy
from src.strategy.dependency_checker import DependencyChecker, DependencyCheckResult
from src.strategy.strategy_validator import StrategyValidator, ValidationResult


class StrategyFactory:
    """
    策略工厂类
    
    作用：
    1. 统一管理所有策略类的注册
    2. 根据策略类型动态创建策略实例
    3. 提供策略配置验证
    4. 支持策略的热加载和热更新
    5. 集成依赖检查和策略验证
    """
    
    def __init__(self, config: Optional[ConfigManager] = None, event_bus: Optional[EventBus] = None):
        # 策略注册表
        self._strategies: dict[str, type[BaseStrategy]] = {}
        
        # 配置和事件总线
        self.config = config
        self.event_bus = event_bus
        self.logger = get_logger(self.__class__.__name__)
        
        # 依赖检查器和验证器
        self.dependency_checker: Optional[DependencyChecker] = None
        self.strategy_validator: Optional[StrategyValidator] = None
        
        # 缓存
        self.validation_cache: dict[str, ValidationResult] = {}
        self.dependency_cache: dict[str, DependencyCheckResult] = {}
        
        # 初始化组件
        if config and event_bus:
            self._initialize_components()
        
        self._register_default_strategies()
    
    def _initialize_components(self):
        """初始化依赖检查器和验证器"""
        try:
            self.dependency_checker = DependencyChecker(self.event_bus, self.config)
            self.strategy_validator = StrategyValidator(self.config)
            self.logger.info("策略工厂组件初始化完成")
        except Exception as e:
            self.logger.error(f"策略工厂组件初始化失败: {e}")
    
    def _register_default_strategies(self):
        """注册默认策略"""
        self.register_strategy("moving_average", MovingAverageStrategy)
        self.register_strategy("grid_trading", GridTradingStrategy)
    
    def set_dependency_checker(self, checker: DependencyChecker) -> None:
        """设置依赖检查器"""
        self.dependency_checker = checker
        self.logger.info("依赖检查器已设置")
    
    def set_strategy_validator(self, validator: StrategyValidator) -> None:
        """设置策略验证器"""
        self.strategy_validator = validator
        self.logger.info("策略验证器已设置")
    
    def register_strategy(self, strategy_type: str, strategy_class: Type[BaseStrategy]):
        """注册策略类"""
        if not issubclass(strategy_class, BaseStrategy):
            raise ValueError(f"策略类必须继承自BaseStrategy: {strategy_class}")
        
        self._strategies[strategy_type] = strategy_class
        print(f"策略已注册: {strategy_type} -> {strategy_class.__name__}")
    
    def create_strategy(self, strategy_type: str, strategy_id: str, event_bus, params: Dict[str, Any] = None) -> BaseStrategy:
        """
        创建策略实例（不进行验证）
        
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
    
    async def create_strategy_with_validation(self, 
                                            strategy_type: str, 
                                            strategy_id: str, 
                                            event_bus, 
                                            params: Dict[str, Any] = None,
                                            skip_validation: bool = False) -> Tuple[Optional[BaseStrategy], str]:
        """
        创建策略实例并进行验证
        
        Args:
            strategy_type: 策略类型
            strategy_id: 策略ID
            event_bus: 事件总线
            params: 策略参数
            skip_validation: 是否跳过验证
            
        Returns:
            (策略实例, 错误信息)
        """
        try:
            # 检查策略类型是否存在
            strategy_class = self._strategies.get(strategy_type)
            if not strategy_class:
                available_strategies = list(self._strategies.keys())
                return None, f"未知的策略类型: {strategy_type}. 可用策略: {available_strategies}"
            
            if not skip_validation:
                # 1. 策略验证
                if self.strategy_validator:
                    validation_result = await self._validate_strategy(strategy_type, params or {})
                    if not validation_result.is_valid:
                        error_messages = [issue.message for issue in validation_result.issues 
                                        if issue.severity.value == "error"]
                        return None, f"策略验证失败: {'; '.join(error_messages)}"
                
                # 2. 依赖检查
                if self.dependency_checker:
                    dependency_result = await self._check_dependencies(strategy_id, params or {})
                    if dependency_result.overall_status.value == "failed":
                        failed_checks = [item.message for item in dependency_result.check_items 
                                       if item.status.value == "failed"]
                        return None, f"依赖检查失败: {'; '.join(failed_checks)}"
            
            # 创建策略实例
            strategy = strategy_class(strategy_id, event_bus, params or {})
            self.logger.info(f"策略创建成功: {strategy_type} - {strategy_id}")
            return strategy, ""
            
        except Exception as e:
            error_msg = f"创建策略异常: {str(e)}"
            self.logger.error(error_msg)
            return None, error_msg
    
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
    
    async def pre_validate_strategy(self, strategy_type: str, params: Dict[str, Any]) -> Tuple[bool, str]:
        """
        预验证策略
        
        Args:
            strategy_type: 策略类型
            params: 策略参数
            
        Returns:
            (是否通过验证, 错误信息)
        """
        try:
            if strategy_type not in self._strategies:
                return False, f"未知的策略类型: {strategy_type}"
            
            if self.strategy_validator:
                validation_result = await self._validate_strategy(strategy_type, params)
                if not validation_result.is_valid:
                    error_messages = [issue.message for issue in validation_result.issues 
                                    if issue.severity.value == "error"]
                    return False, f"策略验证失败: {'; '.join(error_messages)}"
            
            return True, ""
            
        except Exception as e:
            error_msg = f"预验证异常: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg
    
    async def check_strategy_dependencies(self, strategy_id: str, strategy_config: Dict[str, Any]) -> Tuple[bool, str]:
        """
        检查策略依赖
        
        Args:
            strategy_id: 策略ID
            strategy_config: 策略配置
            
        Returns:
            (是否通过检查, 错误信息)
        """
        try:
            if self.dependency_checker:
                dependency_result = await self._check_dependencies(strategy_id, strategy_config)
                if dependency_result.overall_status.value == "failed":
                    failed_checks = [item.message for item in dependency_result.check_items 
                                   if item.status.value == "failed"]
                    return False, f"依赖检查失败: {'; '.join(failed_checks)}"
                elif dependency_result.overall_status.value == "warning":
                    warning_checks = [item.message for item in dependency_result.check_items 
                                    if item.status.value == "warning"]
                    self.logger.warning(f"依赖检查警告: {'; '.join(warning_checks)}")
            
            return True, ""
            
        except Exception as e:
            error_msg = f"依赖检查异常: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg
    
    def validate_strategy_config(self, strategy_type: str, config: Dict[str, Any]) -> bool:
        """
        验证策略配置（同步版本，保持向后兼容）
        
        Args:
            strategy_type: 策略类型
            config: 策略配置
            
        Returns:
            配置是否有效
        """
        if strategy_type not in self._strategies:
            return False
        
        # 基本配置验证
        return True


    def get_validation_report(self, strategy_type: str) -> Optional[ValidationResult]:
        """获取验证报告"""
        return self.validation_cache.get(strategy_type)
    
    def get_dependency_report(self, strategy_id: str) -> Optional[DependencyCheckResult]:
        """获取依赖检查报告"""
        return self.dependency_cache.get(strategy_id)
    
    def clear_validation_cache(self) -> None:
        """清除验证缓存"""
        self.validation_cache.clear()
        self.dependency_cache.clear()
        if self.dependency_checker:
            self.dependency_checker.clear_cache()
        self.logger.info("验证缓存已清除")
    
    async def _validate_strategy(self, strategy_type: str, params: Dict[str, Any]) -> ValidationResult:
        """内部策略验证方法"""
        # 检查缓存
        cache_key = f"{strategy_type}_{hash(str(sorted(params.items())))}"
        if cache_key in self.validation_cache:
            return self.validation_cache[cache_key]
        
        # 执行验证
        strategy_class = self._strategies[strategy_type]
        
        # 方法验证
        methods_result = await self.strategy_validator.validate_required_methods(strategy_class)
        
        # 参数验证
        schema = self.strategy_validator.create_parameter_schema(strategy_class)
        params_result = await self.strategy_validator.validate_parameters(params, schema)
        
        # 风险规则验证
        risk_result = await self.strategy_validator.validate_risk_rules(params)
        
        # 兼容性验证
        compatibility_result = await self.strategy_validator.validate_compatibility(strategy_class)
        
        # 合并结果
        all_issues: list = []
        all_issues.extend(methods_result.issues)
        all_issues.extend(params_result.issues)
        all_issues.extend(risk_result.issues)
        all_issues.extend(compatibility_result.issues)
        
        combined_result = ValidationResult(
            strategy_path=f"{strategy_type}_validation",
            is_valid=True,  # 将在 __post_init__ 中重新计算
            issues=all_issues
        )
        
        # 缓存结果
        self.validation_cache[cache_key] = combined_result
        
        return combined_result
    
    async def _check_dependencies(self, strategy_id: str, strategy_config: Dict[str, Any]) -> DependencyCheckResult:
        """内部依赖检查方法"""
        # 检查缓存
        if strategy_id in self.dependency_cache:
            return self.dependency_cache[strategy_id]
        
        # 执行依赖检查
        dependency_config = strategy_config.copy()
        dependency_config["strategy_id"] = strategy_id
        
        result = await self.dependency_checker.run_all_checks(dependency_config)
        
        # 缓存结果
        self.dependency_cache[strategy_id] = result
        
        return result


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


async def create_strategy_with_validation(strategy_type: str, strategy_id: str, event_bus, 
                                        params: Dict[str, Any] = None, 
                                        skip_validation: bool = False) -> Tuple[Optional[BaseStrategy], str]:
    """
    便捷函数：创建策略实例并进行验证
    
    Args:
        strategy_type: 策略类型
        strategy_id: 策略ID
        event_bus: 事件总线
        params: 策略参数
        skip_validation: 是否跳过验证
        
    Returns:
        (策略实例, 错误信息)
    """
    return await strategy_factory.create_strategy_with_validation(
        strategy_type, strategy_id, event_bus, params, skip_validation
    )


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