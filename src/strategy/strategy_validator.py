#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos_v2
@FileName   : strategy_validator
@Date       : 2025/7/23 15:38
@Author     : Donny
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description:
策略验证器模块
提供策略代码验证功能，包括语法检查、方法验证、参数校验等。
"""
import ast
import inspect
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Type, Dict, List, Any, Optional

from src.config.config_manager import ConfigManager
from src.core.logger import get_logger
from src.strategy.base_strategy import BaseStrategy


class ValidationType(Enum):
    """验证类型枚举"""
    SYNTAX = "syntax"
    METHODS = "methods"
    PARAMETERS = "parameters"
    RISK_RULES = "risk_rules"
    COMPATIBILITY = "compatibility"
    PERFORMANCE = "performance"


class ValidationSeverity(Enum):
    """验证严重程度枚举"""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationIssue:
    """验证问题"""
    validation_type: ValidationType
    severity: ValidationSeverity
    message: str
    line_number: Optional[int] = None
    column_number: Optional[int] = None
    suggestion: Optional[str] = None
    code_snippet: Optional[str] = None


@dataclass
class ValidationResult:
    """验证结果"""
    strategy_path: str
    is_valid: bool
    issues: List[ValidationIssue] = field(default_factory=list)
    validation_time: datetime = field(default_factory=datetime.now)
    validator_version: str = "1.0.0"
    summary: Dict[str, int] = field(default_factory=dict)
    validation_duration: float = 0.0

    def __post_init__(self):
        """计算摘要信息"""
        self.summary = {
            "total_issues": len(self.issues),
            "errors": sum(1 for issue in self.issues if issue.severity == ValidationSeverity.ERROR),
            "warnings": sum(1 for issue in self.issues if issue.severity == ValidationSeverity.WARNING),
            "info": sum(1 for issue in self.issues if issue.severity == ValidationSeverity.INFO)
        }

        # 如果有错误，则验证失败
        if self.summary["errors"] > 0:
            self.is_valid = False


class StrategyValidator:
    """策略验证器

    负责验证策略代码的正确性、完整性和合规性。
    """

    def __init__(self, config: ConfigManager):
        self.config = config
        self.logger = get_logger(self.__class__.__name__)

        # 配置参数
        self.strict_mode = config.get("strategy_management.validation.strict_mode", False)
        self.skip_syntax_check = config.get("strategy_management.validation.skip_syntax_check", False)

        # 验证规则配置
        validation_rules = config.get("strategy_management.validation.rules", {})
        self.required_methods = validation_rules.get("required_methods", [
            "on_init", "on_start", "on_stop", "on_tick"
        ])
        self.optional_methods = validation_rules.get("optional_methods", [
            "on_bar", "on_order", "on_trade"
        ])
        self.max_file_size = validation_rules.get("max_file_size", 1048576)  # 1MB
        self.max_complexity = validation_rules.get("max_complexity", 100)

        # 风险规则
        self.risk_rules = {
            "max_position_ratio": 0.5,  # 最大持仓比例
            "max_single_order_ratio": 0.1,  # 最大单笔订单比例
            "required_stop_loss": True,  # 是否必须设置止损
            "max_leverage": 10,  # 最大杠杆
            "min_risk_reward_ratio": 1.5  # 最小风险收益比
        }

        self.logger.info("策略验证器初始化完成")

    async def validate_syntax(self, strategy_path: str) -> ValidationResult:
        """验证策略代码语法"""
        import time
        start_time = time.time()

        result = ValidationResult(
            strategy_path=strategy_path,
            is_valid=True
        )

        if self.skip_syntax_check:
            result.issues.append(ValidationIssue(
                validation_type=ValidationType.SYNTAX,
                severity=ValidationSeverity.INFO,
                message="语法检查已跳过"
            ))
            result.validation_duration = time.time() - start_time
            return result

        try:
            # 检查文件是否存在
            if not os.path.exists(strategy_path):
                result.issues.append(ValidationIssue(
                    validation_type=ValidationType.SYNTAX,
                    severity=ValidationSeverity.ERROR,
                    message=f"策略文件不存在: {strategy_path}"
                ))
                result.validation_duration = time.time() - start_time
                return result

            # 检查文件大小
            file_size = os.path.getsize(strategy_path)
            if file_size > self.max_file_size:
                result.issues.append(ValidationIssue(
                    validation_type=ValidationType.SYNTAX,
                    severity=ValidationSeverity.WARNING,
                    message=f"策略文件过大: {file_size} bytes，建议小于 {self.max_file_size} bytes"
                ))

            # 读取文件内容
            with open(strategy_path, 'r', encoding='utf-8') as f:
                source_code = f.read()

            # 语法检查
            try:
                tree = ast.parse(source_code, filename=strategy_path)

                # 检查代码复杂度
                complexity = self._calculate_complexity(tree)
                if complexity > self.max_complexity:
                    result.issues.append(ValidationIssue(
                        validation_type=ValidationType.SYNTAX,
                        severity=ValidationSeverity.WARNING,
                        message=f"代码复杂度过高: {complexity}，建议小于 {self.max_complexity}",
                        suggestion="考虑将复杂逻辑拆分为多个方法"
                    ))

                # 检查导入语句
                self._check_imports(tree, result)

                # 检查类定义
                self._check_class_definitions(tree, result)

                # 检查潜在问题
                self._check_potential_issues(tree, source_code, result)

            except SyntaxError as e:
                result.issues.append(ValidationIssue(
                    validation_type=ValidationType.SYNTAX,
                    severity=ValidationSeverity.ERROR,
                    message=f"语法错误: {e.msg}",
                    line_number=e.lineno,
                    column_number=e.offset,
                    code_snippet=self._get_code_snippet(source_code, e.lineno)
                ))

        except Exception as e:
            self.logger.error(f"语法验证异常: {e}")
            result.issues.append(ValidationIssue(
                validation_type=ValidationType.SYNTAX,
                severity=ValidationSeverity.ERROR,
                message=f"语法验证异常: {str(e)}"
            ))

        result.validation_duration = time.time() - start_time
        return result

    async def validate_required_methods(self, strategy_class: Type) -> ValidationResult:
        """验证必需方法存在性"""
        start_time = time.time()

        result = ValidationResult(
            strategy_path=f"{strategy_class.__module__}.{strategy_class.__name__}",
            is_valid=True
        )

        try:
            # 检查是否继承自 BaseStrategy
            if not issubclass(strategy_class, BaseStrategy):
                result.issues.append(ValidationIssue(
                    validation_type=ValidationType.METHODS,
                    severity=ValidationSeverity.ERROR,
                    message=f"策略类 {strategy_class.__name__} 必须继承自 BaseStrategy",
                    suggestion="确保策略类继承自 src.strategies.base_strategy.BaseStrategy"
                ))

            # 检查必需方法
            for method_name in self.required_methods:
                if not hasattr(strategy_class, method_name):
                    result.issues.append(ValidationIssue(
                        validation_type=ValidationType.METHODS,
                        severity=ValidationSeverity.ERROR,
                        message=f"缺少必需方法: {method_name}",
                        suggestion=f"请实现 {method_name} 方法"
                    ))
                else:
                    method = getattr(strategy_class, method_name)
                    if not callable(method):
                        result.issues.append(ValidationIssue(
                            validation_type=ValidationType.METHODS,
                            severity=ValidationSeverity.ERROR,
                            message=f"{method_name} 不是可调用方法"
                        ))
                    else:
                        # 检查方法签名
                        self._check_method_signature(strategy_class, method_name, result)

            # 检查可选方法
            for method_name in self.optional_methods:
                if hasattr(strategy_class, method_name):
                    method = getattr(strategy_class, method_name)
                    if callable(method):
                        self._check_method_signature(strategy_class, method_name, result)
                    else:
                        result.issues.append(ValidationIssue(
                            validation_type=ValidationType.METHODS,
                            severity=ValidationSeverity.WARNING,
                            message=f"可选方法 {method_name} 不是可调用方法"
                        ))

            # 检查方法实现
            self._check_method_implementations(strategy_class, result)

        except Exception as e:
            self.logger.error(f"方法验证异常: {e}")
            result.issues.append(ValidationIssue(
                validation_type=ValidationType.METHODS,
                severity=ValidationSeverity.ERROR,
                message=f"方法验证异常: {str(e)}"
            ))

        result.validation_duration = time.time() - start_time
        return result

    async def validate_parameters(self, params: Dict[str, Any], schema: Dict[str, Any]) -> ValidationResult:
        """验证参数配置"""
        import time
        start_time = time.time()

        result = ValidationResult(
            strategy_path="parameter_validation",
            is_valid=True
        )

        try:
            # 检查必需参数
            required_params = schema.get("required", [])
            for param_name in required_params:
                if param_name not in params:
                    result.issues.append(ValidationIssue(
                        validation_type=ValidationType.PARAMETERS,
                        severity=ValidationSeverity.ERROR,
                        message=f"缺少必需参数: {param_name}",
                        suggestion=f"请在策略配置中添加 {param_name} 参数"
                    ))

            # 检查参数类型和值
            param_definitions = schema.get("properties", {})
            for param_name, param_value in params.items():
                if param_name in param_definitions:
                    param_def = param_definitions[param_name]
                    self._validate_parameter_value(param_name, param_value, param_def, result)
                else:
                    result.issues.append(ValidationIssue(
                        validation_type=ValidationType.PARAMETERS,
                        severity=ValidationSeverity.WARNING,
                        message=f"未知参数: {param_name}",
                        suggestion="检查参数名称是否正确"
                    ))

            # 检查参数组合
            self._check_parameter_combinations(params, result)

        except Exception as e:
            self.logger.error(f"参数验证异常: {e}")
            result.issues.append(ValidationIssue(
                validation_type=ValidationType.PARAMETERS,
                severity=ValidationSeverity.ERROR,
                message=f"参数验证异常: {str(e)}"
            ))

        result.validation_duration = time.time() - start_time
        return result

    async def validate_risk_rules(self, strategy_config: Dict[str, Any]) -> ValidationResult:
        """验证风险控制规则"""
        import time
        start_time = time.time()

        result = ValidationResult(
            strategy_path="risk_validation",
            is_valid=True
        )

        try:
            # 检查持仓比例
            max_position = strategy_config.get("max_position", 0)
            account_balance = strategy_config.get("account_balance", 100000)

            if max_position > 0 and account_balance > 0:
                position_ratio = max_position / account_balance
                max_allowed_ratio = self.risk_rules["max_position_ratio"]

                if position_ratio > max_allowed_ratio:
                    result.issues.append(ValidationIssue(
                        validation_type=ValidationType.RISK_RULES,
                        severity=ValidationSeverity.ERROR,
                        message=f"最大持仓比例 {position_ratio:.2%} 超过限制 {max_allowed_ratio:.2%}",
                        suggestion=f"降低最大持仓至 {account_balance * max_allowed_ratio:.0f} 以下"
                    ))

            # 检查单笔订单比例
            max_order_size = strategy_config.get("max_order_size", 0)
            if max_order_size > 0 and max_position > 0:
                order_ratio = max_order_size / max_position
                max_allowed_order_ratio = self.risk_rules["max_single_order_ratio"]

                if order_ratio > max_allowed_order_ratio:
                    result.issues.append(ValidationIssue(
                        validation_type=ValidationType.RISK_RULES,
                        severity=ValidationSeverity.WARNING,
                        message=f"单笔订单比例 {order_ratio:.2%} 过高，建议小于 {max_allowed_order_ratio:.2%}",
                        suggestion=f"降低单笔订单大小至 {max_position * max_allowed_order_ratio:.0f} 以下"
                    ))

            # 检查止损设置
            if self.risk_rules["required_stop_loss"]:
                stop_loss = strategy_config.get("stop_loss", 0)
                if stop_loss <= 0:
                    result.issues.append(ValidationIssue(
                        validation_type=ValidationType.RISK_RULES,
                        severity=ValidationSeverity.ERROR,
                        message="未设置止损或止损设置无效",
                        suggestion="设置合理的止损比例，建议 2-5%"
                    ))
                elif stop_loss > 0.1:  # 10%
                    result.issues.append(ValidationIssue(
                        validation_type=ValidationType.RISK_RULES,
                        severity=ValidationSeverity.WARNING,
                        message=f"止损比例 {stop_loss:.2%} 过高",
                        suggestion="建议止损比例控制在 5% 以内"
                    ))

            # 检查杠杆
            leverage = strategy_config.get("leverage", 1)
            max_leverage = self.risk_rules["max_leverage"]
            if leverage > max_leverage:
                result.issues.append(ValidationIssue(
                    validation_type=ValidationType.RISK_RULES,
                    severity=ValidationSeverity.ERROR,
                    message=f"杠杆 {leverage} 超过最大限制 {max_leverage}",
                    suggestion=f"降低杠杆至 {max_leverage} 以下"
                ))

            # 检查风险收益比
            stop_loss = strategy_config.get("stop_loss", 0)
            take_profit = strategy_config.get("take_profit", 0)

            if stop_loss > 0 and take_profit > 0:
                risk_reward_ratio = take_profit / stop_loss
                min_ratio = self.risk_rules["min_risk_reward_ratio"]

                if risk_reward_ratio < min_ratio:
                    result.issues.append(ValidationIssue(
                        validation_type=ValidationType.RISK_RULES,
                        severity=ValidationSeverity.WARNING,
                        message=f"风险收益比 {risk_reward_ratio:.2f} 过低，建议大于 {min_ratio}",
                        suggestion="提高止盈目标或降低止损比例"
                    ))

        except Exception as e:
            self.logger.error(f"风险规则验证异常: {e}")
            result.issues.append(ValidationIssue(
                validation_type=ValidationType.RISK_RULES,
                severity=ValidationSeverity.ERROR,
                message=f"风险规则验证异常: {str(e)}"
            ))

        result.validation_duration = time.time() - start_time
        return result

    async def validate_compatibility(self, strategy_class: Type) -> ValidationResult:
        """验证策略兼容性"""
        import time
        start_time = time.time()

        result = ValidationResult(
            strategy_path=f"{strategy_class.__module__}.{strategy_class.__name__}",
            is_valid=True
        )

        try:
            # 检查 Python 版本兼容性
            if sys.version_info < (3, 7):
                result.issues.append(ValidationIssue(
                    validation_type=ValidationType.COMPATIBILITY,
                    severity=ValidationSeverity.ERROR,
                    message=f"Python 版本 {sys.version} 不支持，需要 3.7 或更高版本"
                ))

            # 检查依赖库
            self._check_dependencies(strategy_class, result)

            # 检查异步方法兼容性
            self._check_async_compatibility(strategy_class, result)

            # 检查事件处理兼容性
            self._check_event_compatibility(strategy_class, result)

        except Exception as e:
            self.logger.error(f"兼容性验证异常: {e}")
            result.issues.append(ValidationIssue(
                validation_type=ValidationType.COMPATIBILITY,
                severity=ValidationSeverity.ERROR,
                message=f"兼容性验证异常: {str(e)}"
            ))

        result.validation_duration = time.time() - start_time
        return result

    async def run_full_validation(self, strategy_path: str, params: Dict[str, Any]) -> ValidationResult:
        """运行完整验证"""
        import time
        start_time = time.time()

        self.logger.info(f"开始完整验证策略: {strategy_path}")

        all_issues = []

        try:
            # 1. 语法验证
            syntax_result = await self.validate_syntax(strategy_path)
            all_issues.extend(syntax_result.issues)

            # 如果语法错误，跳过后续验证
            if syntax_result.summary["errors"] > 0:
                result = ValidationResult(
                    strategy_path=strategy_path,
                    is_valid=False,
                    issues=all_issues,
                    validation_duration=time.time() - start_time
                )
                return result

            # 2. 动态加载策略类
            strategy_class = self._load_strategy_class(strategy_path)
            if strategy_class is None:
                all_issues.append(ValidationIssue(
                    validation_type=ValidationType.SYNTAX,
                    severity=ValidationSeverity.ERROR,
                    message="无法加载策略类"
                ))
                result = ValidationResult(
                    strategy_path=strategy_path,
                    is_valid=False,
                    issues=all_issues,
                    validation_duration=time.time() - start_time
                )
                return result

            # 3. 方法验证
            methods_result = await self.validate_required_methods(strategy_class)
            all_issues.extend(methods_result.issues)

            # 4. 参数验证
            if params:
                schema = self.create_parameter_schema(strategy_class)
                params_result = await self.validate_parameters(params, schema)
                all_issues.extend(params_result.issues)

            # 5. 风险规则验证
            risk_result = await self.validate_risk_rules(params or {})
            all_issues.extend(risk_result.issues)

            # 6. 兼容性验证
            compatibility_result = await self.validate_compatibility(strategy_class)
            all_issues.extend(compatibility_result.issues)

        except Exception as e:
            self.logger.error(f"完整验证异常: {e}")
            all_issues.append(ValidationIssue(
                validation_type=ValidationType.SYNTAX,
                severity=ValidationSeverity.ERROR,
                message=f"验证过程异常: {str(e)}"
            ))

        result = ValidationResult(
            strategy_path=strategy_path,
            is_valid=True,  # 将在 __post_init__ 中重新计算
            issues=all_issues,
            validation_duration=time.time() - start_time
        )

        self.logger.info(f"策略验证完成: {strategy_path}，问题数: {len(all_issues)}")
        return result

    def create_parameter_schema(self, strategy_class: Type) -> Dict[str, Any]:
        """创建参数验证模式"""
        schema = {
            "type": "object",
            "properties": {},
            "required": []
        }

        try:
            # 检查策略类是否有参数定义
            if hasattr(strategy_class, "PARAMETERS"):
                parameters = getattr(strategy_class, "PARAMETERS")
                if isinstance(parameters, dict):
                    for param_name, param_config in parameters.items():
                        if isinstance(param_config, dict):
                            schema["properties"][param_name] = param_config
                            if param_config.get("required", False):
                                schema["required"].append(param_name)

            # 添加通用参数
            common_params = {
                "max_position": {
                    "type": "number",
                    "minimum": 0,
                    "description": "最大持仓"
                },
                "max_order_size": {
                    "type": "number",
                    "minimum": 0,
                    "description": "最大单笔订单"
                },
                "stop_loss": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 1,
                    "description": "止损比例"
                },
                "take_profit": {
                    "type": "number",
                    "minimum": 0,
                    "description": "止盈比例"
                }
            }

            for param_name, param_config in common_params.items():
                if param_name not in schema["properties"]:
                    schema["properties"][param_name] = param_config

        except Exception as e:
            self.logger.error(f"创建参数模式异常: {e}")

        return schema

    # 辅助方法
    @staticmethod
    def _calculate_complexity(tree: ast.AST) -> int:
        """计算代码复杂度"""
        complexity = 0

        for node in ast.walk(tree):
            # 控制流语句增加复杂度
            if isinstance(node, (ast.If, ast.While, ast.For, ast.Try, ast.With)):
                complexity += 1
            # 逻辑运算符增加复杂度
            elif isinstance(node, (ast.And, ast.Or)):
                complexity += 1
            # 函数定义增加复杂度
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                complexity += 1

        return complexity

    @staticmethod
    def _check_imports(tree: ast.AST, result: ValidationResult) -> None:
        """检查导入语句"""
        dangerous_imports = ['os', 'subprocess', 'sys']

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in dangerous_imports:
                        result.issues.append(ValidationIssue(
                            validation_type=ValidationType.SYNTAX,
                            severity=ValidationSeverity.WARNING,
                            message=f"导入了潜在危险的模块: {alias.name}",
                            line_number=node.lineno,
                            suggestion="确保使用安全的API"
                        ))
            elif isinstance(node, ast.ImportFrom):
                if node.module in dangerous_imports:
                    result.issues.append(ValidationIssue(
                        validation_type=ValidationType.SYNTAX,
                        severity=ValidationSeverity.WARNING,
                        message=f"从潜在危险的模块导入: {node.module}",
                        line_number=node.lineno,
                        suggestion="确保使用安全的API"
                    ))

    @staticmethod
    def _check_class_definitions(tree: ast.AST, result: ValidationResult) -> None:
        """检查类定义"""
        strategy_classes = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # 检查是否有策略类
                if any(base.id == 'BaseStrategy' for base in node.bases if isinstance(base, ast.Name)):
                    strategy_classes.append(node.name)

        if not strategy_classes:
            result.issues.append(ValidationIssue(
                validation_type=ValidationType.SYNTAX,
                severity=ValidationSeverity.ERROR,
                message="未找到继承自 BaseStrategy 的策略类",
                suggestion="确保策略类继承自 BaseStrategy"
            ))
        elif len(strategy_classes) > 1:
            result.issues.append(ValidationIssue(
                validation_type=ValidationType.SYNTAX,
                severity=ValidationSeverity.WARNING,
                message=f"发现多个策略类: {strategy_classes}",
                suggestion="建议每个文件只包含一个策略类"
            ))

    @staticmethod
    def _check_potential_issues(tree: ast.AST, source_code: str, result: ValidationResult) -> None:
        """检查潜在问题"""
        lines = source_code.split('\n')

        for node in ast.walk(tree):
            # 检查无限循环
            if isinstance(node, ast.While):
                if isinstance(node.test, ast.Constant) and node.test.value is True:
                    result.issues.append(ValidationIssue(
                        validation_type=ValidationType.SYNTAX,
                        severity=ValidationSeverity.WARNING,
                        message="发现潜在的无限循环",
                        line_number=node.lineno,
                        suggestion="确保循环有正确的退出条件"
                    ))

            # 检查空的异常处理
            elif isinstance(node, ast.ExceptHandler):
                if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
                    result.issues.append(ValidationIssue(
                        validation_type=ValidationType.SYNTAX,
                        severity=ValidationSeverity.WARNING,
                        message="发现空的异常处理",
                        line_number=node.lineno,
                        suggestion="添加适当的异常处理逻辑或日志记录"
                    ))

    @staticmethod
    def _get_code_snippet(source_code: str, line_number: Optional[int], context: int = 2) -> Optional[str]:
        """获取代码片段"""
        if line_number is None:
            return None

        lines = source_code.split('\n')
        start = max(0, line_number - context - 1)
        end = min(len(lines), line_number + context)

        snippet_lines = []
        for i in range(start, end):
            prefix = ">>> " if i == line_number - 1 else "    "
            snippet_lines.append(f"{prefix}{i + 1:3d}: {lines[i]}")

        return '\n'.join(snippet_lines)

    @staticmethod
    def _check_method_signature(strategy_class: Type, method_name: str, result: ValidationResult) -> None:
        """检查方法签名"""
        try:
            method = getattr(strategy_class, method_name)
            sig = inspect.signature(method)

            # 检查特定方法的签名
            if method_name == "on_tick":
                params = list(sig.parameters.keys())
                if len(params) < 2 or params[1] != "tick":
                    result.issues.append(ValidationIssue(
                        validation_type=ValidationType.METHODS,
                        severity=ValidationSeverity.ERROR,
                        message=f"方法 {method_name} 签名不正确，应为 on_tick(self, tick)",
                        suggestion="修正方法签名为 def on_tick(self, tick):"
                    ))

            elif method_name == "on_bar":
                params = list(sig.parameters.keys())
                if len(params) < 2 or params[1] != "bar":
                    result.issues.append(ValidationIssue(
                        validation_type=ValidationType.METHODS,
                        severity=ValidationSeverity.ERROR,
                        message=f"方法 {method_name} 签名不正确，应为 on_bar(self, bar)",
                        suggestion="修正方法签名为 def on_bar(self, bar):"
                    ))

        except Exception as e:
            result.issues.append(ValidationIssue(
                validation_type=ValidationType.METHODS,
                severity=ValidationSeverity.WARNING,
                message=f"无法检查方法 {method_name} 的签名: {str(e)}"
            ))

    def _check_method_implementations(self, strategy_class: Type, result: ValidationResult) -> None:
        """检查方法实现"""
        for method_name in self.required_methods:
            if hasattr(strategy_class, method_name):
                method = getattr(strategy_class, method_name)
                try:
                    source = inspect.getsource(method)
                    # 检查是否只有 pass 语句
                    if source.strip().endswith("pass") and "pass" in source.split('\n')[-2:]:
                        result.issues.append(ValidationIssue(
                            validation_type=ValidationType.METHODS,
                            severity=ValidationSeverity.WARNING,
                            message=f"方法 {method_name} 只有 pass 语句，可能需要实现",
                            suggestion=f"为 {method_name} 方法添加具体实现"
                        ))
                except (OSError, TypeError):
                    # 无法获取源码（可能是内置方法）
                    pass

    @staticmethod
    def _validate_parameter_value(param_name: str, param_value: Any, param_def: Dict[str, Any],
                                  result: ValidationResult) -> None:
        """验证参数值"""
        param_type = param_def.get("type")

        # 类型检查
        if param_type == "number":
            if not isinstance(param_value, (int, float)):
                result.issues.append(ValidationIssue(
                    validation_type=ValidationType.PARAMETERS,
                    severity=ValidationSeverity.ERROR,
                    message=f"参数 {param_name} 类型错误，期望数字，实际 {type(param_value).__name__}"
                ))
                return

            # 范围检查
            minimum = param_def.get("minimum")
            maximum = param_def.get("maximum")

            if minimum is not None and param_value < minimum:
                result.issues.append(ValidationIssue(
                    validation_type=ValidationType.PARAMETERS,
                    severity=ValidationSeverity.ERROR,
                    message=f"参数 {param_name} 值 {param_value} 小于最小值 {minimum}"
                ))

            if maximum is not None and param_value > maximum:
                result.issues.append(ValidationIssue(
                    validation_type=ValidationType.PARAMETERS,
                    severity=ValidationSeverity.ERROR,
                    message=f"参数 {param_name} 值 {param_value} 大于最大值 {maximum}"
                ))

        elif param_type == "string":
            if not isinstance(param_value, str):
                result.issues.append(ValidationIssue(
                    validation_type=ValidationType.PARAMETERS,
                    severity=ValidationSeverity.ERROR,
                    message=f"参数 {param_name} 类型错误，期望字符串，实际 {type(param_value).__name__}"
                ))

        elif param_type == "boolean":
            if not isinstance(param_value, bool):
                result.issues.append(ValidationIssue(
                    validation_type=ValidationType.PARAMETERS,
                    severity=ValidationSeverity.ERROR,
                    message=f"参数 {param_name} 类型错误，期望布尔值，实际 {type(param_value).__name__}"
                ))

    @staticmethod
    def _check_parameter_combinations(params: Dict[str, Any], result: ValidationResult) -> None:
        """检查参数组合"""
        # 检查止损和止盈的关系
        stop_loss = params.get("stop_loss", 0)
        take_profit = params.get("take_profit", 0)

        if stop_loss > 0 and 0 < take_profit <= stop_loss:
            result.issues.append(ValidationIssue(
                validation_type=ValidationType.PARAMETERS,
                severity=ValidationSeverity.WARNING,
                message=f"止盈 {take_profit} 小于等于止损 {stop_loss}，风险收益比不合理",
                suggestion="确保止盈大于止损"
            ))

        # 检查持仓和订单大小的关系
        max_position = params.get("max_position", 0)
        max_order_size = params.get("max_order_size", 0)

        if 0 < max_position < max_order_size:
            result.issues.append(ValidationIssue(
                validation_type=ValidationType.PARAMETERS,
                severity=ValidationSeverity.ERROR,
                message=f"最大单笔订单 {max_order_size} 大于最大持仓 {max_position}",
                suggestion="调整订单大小或持仓限制"
            ))

    def _check_dependencies(self, strategy_class: Type, result: ValidationResult) -> None:
        """检查依赖库"""
        # 这里可以检查策略是否使用了不兼容的库
        pass

    @staticmethod
    def _check_async_compatibility(strategy_class: Type, result: ValidationResult) -> None:
        """检查异步方法兼容性"""
        async_methods = []

        for method_name in dir(strategy_class):
            if not method_name.startswith('_'):
                method = getattr(strategy_class, method_name)
                if inspect.iscoroutinefunction(method):
                    async_methods.append(method_name)

        if async_methods:
            result.issues.append(ValidationIssue(
                validation_type=ValidationType.COMPATIBILITY,
                severity=ValidationSeverity.INFO,
                message=f"发现异步方法: {async_methods}",
                suggestion="确保异步方法正确处理"
            ))

    def _check_event_compatibility(self, strategy_class: Type, result: ValidationResult) -> None:
        """检查事件处理兼容性"""
        # 检查是否正确使用事件系统
        pass

    def _load_strategy_class(self, strategy_path: str) -> Optional[Type]:
        """动态加载策略类"""
        try:
            # 这里需要实现动态加载逻辑
            # 由于涉及到模块导入，这里返回 None 作为占位
            return None
        except Exception as e:
            self.logger.error(f"加载策略类异常: {e}")
            return None
