#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos_v2
@FileName   : strategy_manager
@Date       : 2025/7/23 00:13
@Author     : Donny
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 策略管理器
"""
import asyncio
import time
from collections import defaultdict
from typing import Dict, Optional, Any

from src.config.config_manager import ConfigManager
from src.core.event import Event, EventType, create_trading_event
from src.core.event_bus import EventBus
from src.core.logger import get_logger
from src.core.object import TickData, StrategyInfo
from src.strategies.strategy_event_handler import StrategyEventHandler
from src.strategies.strategy_health_monitor import StrategyHealthMonitor, HealthReport

logger = get_logger("StrategyManager")


class StrategyManager:

    def __init__(self, event_bus: EventBus, config: ConfigManager):
        self.event_bus = event_bus
        self.config = config
        self.strategies: Dict[str, StrategyInfo] = {}
        self.strategy_subscriptions: Dict[str, set] = defaultdict(set)  # strategy_id -> symbols

        # 初始化健康监控器
        self.health_monitor = StrategyHealthMonitor(event_bus, config)

        # 初始化事件处理器
        self.event_handler = StrategyEventHandler(event_bus, config)

        # 策略恢复配置
        self.auto_recovery_enabled = config.get("strategy_management.health_monitoring.auto_recovery", True)
        self.max_recovery_attempts = config.get("strategy_management.health_monitoring.max_recovery_attempts", 3)
        self.recovery_attempts: Dict[str, int] = {}  # 记录每个策略的恢复尝试次数

        # 注册事件处理器
        self._register_event_handlers()

        # 启动健康监控
        asyncio.create_task(self._start_health_monitoring())

    def _register_event_handlers(self):
        """注册事件处理器"""
        self.event_bus.subscribe("market.tick", self._handle_market_tick)
        self.event_bus.subscribe("strategy.load", self._handle_load_strategy)
        self.event_bus.subscribe("strategy.start", self._handle_start_strategy)
        self.event_bus.subscribe("strategy.stop", self._handle_stop_strategy)

        # 注册策略健康和恢复相关事件
        self.event_bus.subscribe(EventType.STRATEGY_ANOMALY_DETECTED, self._handle_strategy_anomaly)
        self.event_bus.subscribe(EventType.STRATEGY_RECOVERY_FAILED, self._handle_recovery_failed)
        self.event_bus.subscribe(EventType.STRATEGY_ERROR, self._handle_strategy_error)

    def _find_strategy_class(self, module):
        """自动发现策略类 - 查找继承自BaseStrategy的类"""
        import inspect
        from src.strategies.base_strategy import BaseStrategy

        for name, obj in inspect.getmembers(module):
            if (inspect.isclass(obj) and
                    issubclass(obj, BaseStrategy) and
                    obj != BaseStrategy):
                logger.debug(f"发现策略类: {name}")
                return obj

        # 如果没找到继承自BaseStrategy的类，尝试查找名为Strategy的类
        strategy_class = getattr(module, 'Strategy', None)
        if strategy_class is not None:
            logger.debug("使用Strategy类作为回退选项")
            return strategy_class

        return None

    async def load_strategy(self,
                            strategy_path: str,
                            user_strategy_name: Optional[str] = None,
                            params: Optional[Dict[str, Any]] = None
                            ) -> tuple[bool, str]:
        """动态加载策略 - 自动生成UUID作为主键，增强异常处理"""
        params = params or {}

        try:
            import importlib.util
            import os

            # 验证策略文件存在性
            if not os.path.exists(strategy_path):
                raise FileNotFoundError(f"策略文件不存在: {strategy_path}")

            if not strategy_path.endswith('.py'):
                raise ValueError(f"策略文件必须是Python文件: {strategy_path}")

            # 动态导入策略模块
            spec = importlib.util.spec_from_file_location("strategy", strategy_path)
            if spec is None or spec.loader is None:
                raise ImportError(f"无法创建模块规范: {strategy_path}")

            module = importlib.util.module_from_spec(spec)

            try:
                spec.loader.exec_module(module)
            except SyntaxError as e:
                raise SyntaxError(f"策略文件语法错误: {e}")
            except ImportError as e:
                raise ImportError(f"策略文件依赖导入失败: {e}")

            # 创建策略实例 - 自动发现策略类
            strategy_class = self._find_strategy_class(module)
            if strategy_class is None:
                raise ValueError("策略文件中未找到继承自BaseStrategy的策略类")

            # 创建策略实例，传入用户提供的策略名称或自动生成
            display_name = user_strategy_name or strategy_class.__name__

            try:
                strategy_instance = strategy_class(display_name, self.event_bus, params)
            except TypeError as e:
                raise TypeError(f"策略类初始化参数错误: {e}")
            except Exception as e:
                raise RuntimeError(f"策略实例创建失败: {e}")

            # 获取策略自动生成的UUID
            strategy_uuid = strategy_instance.get_strategy_uuid()

            # 检查UUID冲突
            if strategy_uuid in self.strategies:
                raise ValueError(f"策略UUID冲突: {strategy_uuid}")

            # 注册策略信息，使用UUID作为主键
            strategy_info = StrategyInfo(
                strategy_id=display_name,  # 用于显示的友好名称
                strategy_name=getattr(strategy_instance, 'strategy_name', display_name),
                instance=strategy_instance,
                status="loaded",
                params=params,
                strategy_uuid=strategy_uuid,  # 策略UUID作为唯一标识
                strategy_path=strategy_path  # 保存策略文件路径
            )

            # 使用UUID作为存储键
            self.strategies[strategy_uuid] = strategy_info

            # 发布策略加载成功事件
            self.event_bus.publish(create_trading_event(
                EventType.STRATEGY_LOADED,
                {
                    "strategy_id": display_name,
                    "strategy_uuid": strategy_uuid,
                    "strategy_name": strategy_info.strategy_name,
                    "strategy_path": strategy_path,
                    "message": f"策略 {display_name} 加载成功"
                },
                "StrategyManager"
            ))

            logger.info(f"策略加载成功: {display_name} (UUID: {strategy_uuid})")
            return True, strategy_uuid

        except (FileNotFoundError, ValueError, ImportError, SyntaxError, TypeError, RuntimeError) as e:
            # 分类处理已知异常类型
            error_msg = f"策略加载失败: {e}"
            logger.error(error_msg, exc_info=True)

            # 发布策略加载失败事件
            self.event_bus.publish(create_trading_event(
                EventType.STRATEGY_LOAD_FAILED,
                {
                    "strategy_path": strategy_path,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "message": error_msg
                },
                "StrategyManager"
            ))

            return False, ""
        except Exception as e:
            # 处理未预期的异常
            error_msg = f"策略加载遇到未预期错误: {e}"
            logger.error(error_msg, exc_info=True)

            # 发布策略加载失败事件
            self.event_bus.publish(create_trading_event(
                EventType.STRATEGY_LOAD_FAILED,
                {
                    "strategy_path": strategy_path,
                    "error": str(e),
                    "error_type": "UnexpectedError",
                    "message": error_msg
                },
                "StrategyManager"
            ))

            return False, ""

    async def start_strategy(self, strategy_uuid: str) -> bool:
        """启动策略 - 使用UUID作为标识符，增强网关状态检查和异常处理"""
        if strategy_uuid not in self.strategies:
            logger.error(f"策略不存在: {strategy_uuid}")
            return False

        strategy_info = self.strategies[strategy_uuid]
        if strategy_info.status == "running":
            logger.warning(f"策略已在运行: {strategy_info.strategy_name} ({strategy_uuid})")
            return True

        try:
            # 检查网关就绪状态
            try:
                gateway_ready = await self._check_gateway_ready_for_strategy(strategy_info.instance)
                if not gateway_ready:
                    logger.warning(f"网关未就绪，策略启动可能受影响: {strategy_info.strategy_name}")
                    # 继续启动，但发出警告，系统会自动处理重连
            except Exception as e:
                logger.warning(f"网关状态检查失败: {e}，继续启动策略")

            # 调用策略的start()方法，这会自动处理initialize() -> on_init() -> on_start()流程
            try:
                await strategy_info.instance.start()
            except AttributeError as e:
                raise RuntimeError(f"策略实例缺少必要方法: {e}")
            except asyncio.TimeoutError as e:
                raise TimeoutError(f"策略启动超时: {e}")
            except Exception as e:
                raise RuntimeError(f"策略启动过程中发生错误: {e}")

            strategy_info.status = "running"
            strategy_info.start_time = time.time()
            strategy_info.error_message = None  # 清除之前的错误信息

            # 发布策略启动成功事件
            self.event_bus.publish(create_trading_event(
                EventType.STRATEGY_STARTED,
                {
                    "strategy_id": strategy_info.strategy_id,
                    "strategy_uuid": strategy_uuid,
                    "strategy_name": strategy_info.strategy_name,
                    "message": f"策略 {strategy_info.strategy_name} 启动成功"
                },
                "StrategyManager"
            ))

            # 将策略添加到健康监控
            self.health_monitor.add_strategy(strategy_info.instance)

            # 重置恢复尝试计数
            self.recovery_attempts[strategy_uuid] = 0

            logger.info(f"策略启动成功: {strategy_info.strategy_name} (UUID: {strategy_uuid})")
            return True

        except (RuntimeError, TimeoutError) as e:
            # 处理已知的启动异常
            logger.error(f"策略启动失败 {strategy_info.strategy_name}: {e}", exc_info=True)
            strategy_info.status = "error"
            strategy_info.error_message = str(e)

            # 发布策略启动失败事件
            self.event_bus.publish(create_trading_event(
                EventType.STRATEGY_START_FAILED,
                {
                    "strategy_id": strategy_info.strategy_id,
                    "strategy_uuid": strategy_uuid,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "message": f"策略 {strategy_info.strategy_name} 启动失败: {e}"
                },
                "StrategyManager"
            ))

            return False
        except Exception as e:
            # 处理未预期的异常
            logger.error(f"策略启动遇到未预期错误 {strategy_info.strategy_name}: {e}", exc_info=True)
            strategy_info.status = "error"
            strategy_info.error_message = str(e)

            # 发布策略启动失败事件
            self.event_bus.publish(create_trading_event(
                EventType.STRATEGY_START_FAILED,
                {
                    "strategy_id": strategy_info.strategy_id,
                    "strategy_uuid": strategy_uuid,
                    "error": str(e),
                    "error_type": "UnexpectedError",
                    "message": f"策略 {strategy_info.strategy_name} 启动遇到未预期错误: {e}"
                },
                "StrategyManager"
            ))

            return False

    async def stop_strategy(self, strategy_uuid: str) -> bool:
        """停止策略 - 使用UUID作为标识符，增强异常处理"""
        if strategy_uuid not in self.strategies:
            logger.error(f"策略不存在: {strategy_uuid}")
            return False

        strategy_info = self.strategies[strategy_uuid]

        # 检查策略状态
        if strategy_info.status == "stopped":
            logger.warning(f"策略已停止: {strategy_info.strategy_name} ({strategy_uuid})")
            return True

        try:
            # 调用策略的stop()方法
            try:
                await strategy_info.instance.stop()
            except AttributeError as e:
                raise RuntimeError(f"策略实例缺少stop方法: {e}")
            except asyncio.TimeoutError as e:
                raise TimeoutError(f"策略停止超时: {e}")
            except Exception as e:
                raise RuntimeError(f"策略停止过程中发生错误: {e}")

            strategy_info.status = "stopped"
            strategy_info.stop_time = time.time()
            strategy_info.error_message = None  # 清除错误信息

            # 发布策略停止成功事件
            self.event_bus.publish(create_trading_event(
                EventType.STRATEGY_STOPPED,
                {
                    "strategy_id": strategy_info.strategy_id,
                    "strategy_uuid": strategy_uuid,
                    "strategy_name": strategy_info.strategy_name,
                    "message": f"策略 {strategy_info.strategy_name} 停止成功"
                },
                "StrategyManager"
            ))

            # 从健康监控中移除策略
            self.health_monitor.remove_strategy(strategy_info.instance.strategy_id)

            # 清除恢复尝试计数
            self.recovery_attempts.pop(strategy_uuid, None)

            logger.info(f"策略停止成功: {strategy_info.strategy_name} (UUID: {strategy_uuid})")
            return True

        except (RuntimeError, TimeoutError) as e:
            # 处理已知的停止异常
            logger.error(f"策略停止失败 {strategy_info.strategy_name}: {e}", exc_info=True)
            strategy_info.error_message = str(e)

            # 发布策略停止失败事件
            self.event_bus.publish(create_trading_event(
                EventType.STRATEGY_STOP_FAILED,
                {
                    "strategy_id": strategy_info.strategy_id,
                    "strategy_uuid": strategy_uuid,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "message": f"策略 {strategy_info.strategy_name} 停止失败: {e}"
                },
                "StrategyManager"
            ))

            return False
        except Exception as e:
            # 处理未预期的异常
            logger.error(f"策略停止遇到未预期错误 {strategy_info.strategy_name}: {e}", exc_info=True)
            strategy_info.error_message = str(e)

            # 发布策略停止失败事件
            self.event_bus.publish(create_trading_event(
                EventType.STRATEGY_STOP_FAILED,
                {
                    "strategy_id": strategy_info.strategy_id,
                    "strategy_uuid": strategy_uuid,
                    "error": str(e),
                    "error_type": "UnexpectedError",
                    "message": f"策略 {strategy_info.strategy_name} 停止遇到未预期错误: {e}"
                },
                "StrategyManager"
            ))

            return False

    def _handle_market_tick(self, event: Event):
        """分发行情数据给相关策略"""
        tick_data = event.data
        if not isinstance(tick_data, TickData):
            return

        # 分发给订阅此合约的策略
        for strategy_id, symbols in self.strategy_subscriptions.items():
            if tick_data.symbol in symbols:
                strategy_info = self.strategies.get(strategy_id)
                if strategy_info and strategy_info.status == "running":
                    try:
                        asyncio.create_task(strategy_info.instance.on_tick(tick_data))
                    except Exception as e:
                        logger.error(f"策略处理行情失败 {strategy_id}: {e}")

    def _handle_load_strategy(self, event: Event):
        """处理策略加载请求"""
        data = event.data
        asyncio.create_task(self.load_strategy(
            data["strategy_path"],
            data["strategy_id"],
            data["params"]
        ))

    def _handle_start_strategy(self, event: Event):
        """处理策略启动请求"""
        strategy_uuid = event.data["strategy_uuid"]
        asyncio.create_task(self.start_strategy(strategy_uuid))

    def _handle_stop_strategy(self, event: Event):
        """处理策略停止请求"""
        strategy_uuid = event.data["strategy_uuid"]
        asyncio.create_task(self.stop_strategy(strategy_uuid))

    def get_strategy_status(self, strategy_uuid: str) -> Optional[Dict[str, Any]]:
        """获取策略状态 - 使用UUID查找"""
        if strategy_uuid not in self.strategies:
            return None

        strategy_info = self.strategies[strategy_uuid]
        return {
            "strategy_id": strategy_info.strategy_id,
            "strategy_name": strategy_info.strategy_name,
            "strategy_uuid": strategy_info.strategy_uuid,  # 返回策略UUID
            "strategy_path": strategy_info.strategy_path,  # 返回策略路径
            "status": strategy_info.status,
            "start_time": strategy_info.start_time,
            "stop_time": strategy_info.stop_time,
            "error_message": strategy_info.error_message,
            "params": strategy_info.params
        }

    def get_all_strategies(self) -> Dict[str, Dict[str, Any]]:
        """获取所有策略状态"""
        result = {}
        for strategy_id in self.strategies:
            status = self.get_strategy_status(strategy_id)
            if status is not None:
                result[strategy_id] = status
        return result

    async def _check_gateway_ready_for_strategy(self, strategy) -> bool:
        """
        检查策略所需的网关是否就绪

        Args:
            strategy: 策略实例

        Returns:
            bool: 网关是否就绪
        """
        try:
            # 获取策略需要的合约
            required_symbols = getattr(strategy, 'symbol', None)
            if required_symbols:
                if isinstance(required_symbols, str):
                    required_symbols = [required_symbols]

                # 发布网关状态查询事件
                if self.event_bus:
                    query_event = create_trading_event(
                        EventType.GATEWAY_READY_CHECK,
                        {
                            "symbols": required_symbols,
                            "strategy_id": strategy.strategy_id,
                            "check_type": "market_data"
                        },
                        source="StrategyManager"
                    )

                    self.event_bus.publish(query_event)

                    # 等待一小段时间让网关响应
                    await asyncio.sleep(0.5)

            # 暂时返回True，让系统处理连接问题
            return True

        except Exception as e:
            logger.error(f"检查网关状态失败: {e}")
            return False

    def setup_gateway_monitoring(self):
        """设置网关监控"""
        try:
            # 订阅网关状态事件
            self.event_bus.subscribe(EventType.GATEWAY_CONNECTED, self._handle_gateway_connected)
            self.event_bus.subscribe(EventType.GATEWAY_DISCONNECTED, self._handle_gateway_disconnected)
            self.event_bus.subscribe(EventType.GATEWAY_READY, self._handle_gateway_ready)

            logger.info("网关监控事件处理器已注册")

        except Exception as e:
            logger.error(f"设置网关监控失败: {e}")

    def _handle_gateway_connected(self, event: Event):
        """处理网关连接事件"""
        try:
            data = event.data
            gateway_name = data.get("gateway_name", "unknown")

            logger.info(f"网关已连接: {gateway_name}")

            # 通知所有运行中的策略网关状态变化
            self._notify_strategies_gateway_status(gateway_name, "connected")

        except Exception as e:
            logger.error(f"处理网关连接事件失败: {e}")

    def _handle_gateway_disconnected(self, event: Event):
        """处理网关断开事件"""
        try:
            data = event.data
            gateway_name = data.get("gateway_name", "unknown")

            logger.warning(f"网关已断开: {gateway_name}")

            # 通知所有运行中的策略网关状态变化
            self._notify_strategies_gateway_status(gateway_name, "disconnected")

        except Exception as e:
            logger.error(f"处理网关断开事件失败: {e}")

    def _handle_gateway_ready(self, event: Event):
        """处理网关就绪事件"""
        try:
            data = event.data
            gateway_name = data.get("gateway_name", "unknown")

            logger.info(f"网关已就绪: {gateway_name}")

            # 重新处理待启动的策略
            self._retry_pending_strategy_starts()

        except Exception as e:
            logger.error(f"处理网关就绪事件失败: {e}")

    def _notify_strategies_gateway_status(self, gateway_name: str, status: str):
        """通知策略网关状态变化"""
        try:
            for strategy_uuid, strategy_info in self.strategies.items():
                if strategy_info.status == "running":
                    strategy = strategy_info.instance

                    # 通知策略网关状态变化
                    if hasattr(strategy, 'on_gateway_status_change'):
                        try:
                            asyncio.create_task(
                                strategy.on_gateway_status_change(gateway_name, status)
                            )
                        except Exception as e:
                            logger.error(f"通知策略网关状态变化失败: {e}")

        except Exception as e:
            logger.error(f"通知策略网关状态变化失败: {e}")

    def _retry_pending_strategy_starts(self):
        """重试待启动的策略"""
        try:
            # 这里可以实现重试逻辑
            # 目前只是记录日志
            logger.info("检查是否有待重试的策略启动")

        except Exception as e:
            logger.error(f"重试策略启动失败: {e}")

    async def _start_health_monitoring(self):
        """启动健康监控"""
        try:
            await self.health_monitor.start_monitoring()
            logger.info("策略健康监控已启动")
        except Exception as e:
            logger.error(f"启动健康监控失败: {e}")

    def _handle_strategy_anomaly(self, event: Event):
        """处理策略异常检测事件"""
        try:
            data = event.data
            strategy_uuid = data.get("strategy_uuid")
            anomaly_type = data.get("anomaly_type")

            if not strategy_uuid or strategy_uuid not in self.strategies:
                return

            strategy_info = self.strategies[strategy_uuid]
            logger.warning(f"检测到策略异常: {strategy_info.strategy_name} - {anomaly_type}")

            # 如果启用了自动恢复
            if self.auto_recovery_enabled:
                asyncio.create_task(self._attempt_strategy_recovery(strategy_uuid, anomaly_type))

        except Exception as e:
            logger.error(f"处理策略异常事件失败: {e}")

    def _handle_recovery_failed(self, event: Event):
        """处理策略恢复失败事件"""
        try:
            data = event.data
            strategy_uuid = data.get("strategy_uuid")

            if not strategy_uuid or strategy_uuid not in self.strategies:
                return

            strategy_info = self.strategies[strategy_uuid]
            attempts = self.recovery_attempts.get(strategy_uuid, 0)

            logger.error(f"策略恢复失败: {strategy_info.strategy_name}, 尝试次数: {attempts}")

            # 如果超过最大恢复尝试次数，停止策略
            if attempts >= self.max_recovery_attempts:
                logger.error(f"策略 {strategy_info.strategy_name} 恢复尝试次数超限，停止策略")
                asyncio.create_task(self.stop_strategy(strategy_uuid))

                # 发布策略恢复放弃事件
                self.event_bus.publish(create_trading_event(
                    EventType.STRATEGY_RECOVERY_FAILED,
                    {
                        "strategy_uuid": strategy_uuid,
                        "strategy_name": strategy_info.strategy_name,
                        "reason": "超过最大恢复尝试次数",
                        "attempts": attempts
                    },
                    "StrategyManager"
                ))

        except Exception as e:
            logger.error(f"处理策略恢复失败事件失败: {e}")

    def _handle_strategy_error(self, event: Event):
        """处理策略错误事件"""
        try:
            data = event.data
            strategy_uuid = data.get("strategy_uuid")
            error_type = data.get("error_type")

            if not strategy_uuid or strategy_uuid not in self.strategies:
                return

            strategy_info = self.strategies[strategy_uuid]
            logger.error(f"策略错误: {strategy_info.strategy_name} - {error_type}")

            # 更新策略状态
            strategy_info.status = "error"
            strategy_info.error_message = data.get("error", "未知错误")

            # 如果是严重错误，考虑自动恢复
            if error_type in ["RuntimeError", "ConnectionError", "TimeoutError"]:
                if self.auto_recovery_enabled:
                    asyncio.create_task(self._attempt_strategy_recovery(strategy_uuid, error_type))

        except Exception as e:
            logger.error(f"处理策略错误事件失败: {e}")

    async def _attempt_strategy_recovery(self, strategy_uuid: str, issue_type: str):
        """尝试策略恢复"""
        try:
            if strategy_uuid not in self.strategies:
                return

            strategy_info = self.strategies[strategy_uuid]
            current_attempts = self.recovery_attempts.get(strategy_uuid, 0)

            if current_attempts >= self.max_recovery_attempts:
                logger.error(f"策略 {strategy_info.strategy_name} 已达到最大恢复尝试次数")
                return

            # 增加恢复尝试计数
            self.recovery_attempts[strategy_uuid] = current_attempts + 1

            logger.info(f"开始恢复策略: {strategy_info.strategy_name}, 尝试次数: {current_attempts + 1}")

            # 发布恢复开始事件
            self.event_bus.publish(create_trading_event(
                EventType.STRATEGY_RECOVERY_STARTED,
                {
                    "strategy_uuid": strategy_uuid,
                    "strategy_name": strategy_info.strategy_name,
                    "issue_type": issue_type,
                    "attempt": current_attempts + 1
                },
                "StrategyManager"
            ))

            # 尝试恢复策略
            recovery_success = await self.health_monitor.attempt_recovery(strategy_uuid)

            if recovery_success:
                logger.info(f"策略恢复成功: {strategy_info.strategy_name}")

                # 发布恢复成功事件
                self.event_bus.publish(create_trading_event(
                    EventType.STRATEGY_RECOVERY_COMPLETED,
                    {
                        "strategy_uuid": strategy_uuid,
                        "strategy_name": strategy_info.strategy_name,
                        "attempt": current_attempts + 1
                    },
                    "StrategyManager"
                ))

                # 重置恢复尝试计数
                self.recovery_attempts[strategy_uuid] = 0
            else:
                logger.warning(f"策略恢复失败: {strategy_info.strategy_name}")

                # 发布恢复失败事件
                self.event_bus.publish(create_trading_event(
                    EventType.STRATEGY_RECOVERY_FAILED,
                    {
                        "strategy_uuid": strategy_uuid,
                        "strategy_name": strategy_info.strategy_name,
                        "attempt": current_attempts + 1
                    },
                    "StrategyManager"
                ))

        except Exception as e:
            logger.error(f"策略恢复过程中发生异常: {e}")

    async def get_strategy_health_report(self, strategy_uuid: str) -> HealthReport:
        """
        获取策略健康报告
        返回类型 由Optional[Dict[str, Any]]修改为HealthReport
        """
        try:
            if strategy_uuid not in self.strategies:
                return Optional[HealthReport]

            return await self.health_monitor.check_strategy_health(strategy_uuid)
        except Exception as e:
            logger.error(f"获取策略健康报告失败: {e}")
            return Optional[HealthReport]

    def get_all_strategy_health(self) -> Dict[str, Any]:
        """获取所有策略的健康状态"""
        try:
            health_reports = {}
            for strategy_uuid in self.strategies:
                health_report = asyncio.create_task(self.get_strategy_health_report(strategy_uuid))
                health_reports[strategy_uuid] = health_report
            return health_reports
        except Exception as e:
            logger.error(f"获取所有策略健康状态失败: {e}")
            return {}
