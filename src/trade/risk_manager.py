#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos_v2
@FileName   : risk_manager
@Date       : 2025/7/23 00:18
@Author     : Donny
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 风控管理器
"""
import asyncio
import datetime
import time
from collections import defaultdict

from src.config.config_manager import ConfigManager
from src.core.event import Event, EventType
from src.core.event_bus import BasicEventBus as EventBus
from src.core.logger import get_logger
from src.core.object import OrderRequest, RiskCheckResult

logger = get_logger("RiskManager")


class RiskManager:

    def __init__(self, event_bus: EventBus, config: ConfigManager):
        self.event_bus = event_bus
        self.config = config

        # 风控配置
        self.enabled = config.get("risk.enabled", True)
        self.max_position_size = config.get("risk.max_position_size", 1000000)
        self.max_daily_loss = config.get("risk.max_daily_loss", 50000)
        self.max_order_size = config.get("risk.max_order_size", 100)
        self.order_frequency_limit = config.get("risk.order_frequency_limit", 10)
        self.position_concentration = config.get("risk.position_concentration", 0.3)
        self.enable_self_trade_check = config.get("risk.enable_self_trade_check", True)
        self.enable_price_check = config.get("risk.enable_price_check", True)
        self.price_deviation_threshold = config.get("risk.price_deviation_threshold", 0.05)

        # 新增：绝对价格限制配置
        self.absolute_price_limits = config.get("risk.absolute_price_limits", {
            "rb": {"min": 2000, "max": 6000},
            "hc": {"min": 2000, "max": 6000},
            "i": {"min": 400, "max": 1000},
            "default": {"min": 1, "max": 100000}
        })

        # 实时监控数据
        self.daily_loss = defaultdict(float)  # strategy_id -> daily_loss
        self.order_frequency = {}  # strategy_id -> {timestamp -> count}
        self.position_sizes = defaultdict(float)  # strategy_id -> total_position_value
        self.last_prices = {}  # symbol -> last_price

        # 实盘级别额外风控
        self.max_total_position = config.get("risk.max_total_position", 5000000)  # 总持仓限制
        self.max_single_order_value = config.get("risk.max_single_order_value", 100000)  # 单笔订单价值限制
        self.trading_hours_check = config.get("risk.trading_hours_check", True)  # 交易时间检查
        self.instrument_risk_limits = {}  # 品种风险限制

        # 异常计数和限制
        self.error_counts = defaultdict(int)  # strategy_id -> error_count
        self.max_errors_per_hour = config.get("risk.max_errors_per_hour", 50)
        self.strategy_suspend_threshold = config.get("risk.strategy_suspend_threshold", 100)

        # 注册事件处理器
        self.event_bus.subscribe(EventType.RISK_CHECK, lambda event: asyncio.create_task(self._handle_risk_check(event)))
        self.event_bus.subscribe(EventType.STRATEGY_ERROR, self._handle_strategy_error)
        self.event_bus.subscribe(EventType.MARKET_TICK, self._update_market_prices)

        # 启动风控监控任务
        asyncio.create_task(self._risk_monitoring_task())

    async def _risk_monitoring_task(self):
        """实时风控监控任务"""
        while True:
            try:
                await asyncio.sleep(10)  # 每10秒检查一次

                # 清理过期数据
                self._cleanup_expired_data()

                # 检查策略错误频率
                self._check_strategy_error_rates()

                # 检查市场异常情况
                self._check_market_conditions()

            except Exception as e:
                logger.error(f"风控监控任务异常: {e}")
                await asyncio.sleep(30)  # 异常后等待30秒再继续

    def _cleanup_expired_data(self):
        """清理过期的监控数据"""
        current_time = time.time()
        one_hour_ago = current_time - 3600

        # 清理1小时前的订单频率数据
        for strategy_id in list(self.order_frequency.keys()):
            if strategy_id in self.order_frequency:
                self.order_frequency[strategy_id] = {
                    ts: count for ts, count in self.order_frequency[strategy_id].items()
                    if ts > one_hour_ago
                }

    def _check_strategy_error_rates(self):
        """检查策略错误率"""
        for strategy_id, error_count in self.error_counts.items():
            if error_count > self.strategy_suspend_threshold:
                logger.error(f"策略 {strategy_id} 错误次数过多({error_count})，建议暂停")
                # 发布策略暂停建议事件
                self.event_bus.publish(Event(EventType.RISK_STRATEGY_SUSPEND_RECOMMENDED, {
                    "strategy_id": strategy_id,
                    "error_count": error_count,
                    "reason": "错误次数超过阈值"
                }))

    def _check_market_conditions(self):
        """检查市场条件"""
        if not self.trading_hours_check:
            return

        now = datetime.datetime.now()
        hour = now.hour

        # 期货交易时间：9:00-11:30, 13:30-15:00, 21:00-次日2:30
        is_trading_hours = (
                (9 <= hour <= 11) or
                (13 <= hour <= 14) or
                (21 <= hour <= 23) or
                (0 <= hour <= 2)
        )

        if not is_trading_hours:
            # 非交易时间，暂停接受新订单
            logger.warning(f"当前非交易时间 {hour}:00，暂停接受新订单")

    def _handle_strategy_error(self, event: Event):
        """处理策略错误事件"""
        data = event.data
        strategy_id = data.get("strategy_id", "unknown")
        error_type = data.get("error_type", "general")

        # 增加错误计数
        self.error_counts[strategy_id] += 1

        logger.warning(f"策略错误记录: {strategy_id} - {error_type}, 累计错误: {self.error_counts[strategy_id]}")

    def _update_market_prices(self, event: Event):
        """更新市场价格"""
        tick_data = event.data
        if hasattr(tick_data, 'symbol') and hasattr(tick_data, 'last_price'):
            self.last_prices[tick_data.symbol] = tick_data.last_price

    def _enhanced_price_check(self, order_request: OrderRequest) -> RiskCheckResult:
        """增强的价格合理性检查（支持绝对限制）"""
        if not self.enable_price_check:
            return RiskCheckResult(True, "", [], "low")

        symbol = order_request.symbol
        order_price = order_request.price
        violations = []

        # 1. 绝对价格合理性检查（适用于所有环境）
        # 获取品种前缀
        symbol_prefix = symbol[:2] if len(symbol) >= 2 else "default"
        price_limit = self.absolute_price_limits.get(symbol_prefix, self.absolute_price_limits.get("default", {"min": 1,
                                                                                                               "max": 100000}))

        if order_price < price_limit["min"] or order_price > price_limit["max"]:
            violations.append(f"订单价格 {order_price} 超出合理范围 [{price_limit['min']}, {price_limit['max']}]")

        # 2. 相对价格偏离检查（需要市场数据）
        last_price = self.last_prices.get(symbol)
        if last_price:
            price_deviation = abs(order_price - last_price) / last_price
            if price_deviation > self.price_deviation_threshold:
                violations.append(
                    f"订单价格 {order_price} 偏离市场价格 {last_price} 超过 {self.price_deviation_threshold * 100}%")
        else:
            # 无市场数据时记录警告，但依靠绝对限制
            logger.warning(f"无法获取 {symbol} 的最新价格，使用绝对价格限制检查")

        if violations:
            return RiskCheckResult(False, "", violations, "high")

        return RiskCheckResult(True, "", [], "low")

    def _trading_hours_check(self) -> RiskCheckResult:
        """交易时间检查（支持测试模式覆盖）"""
        # 检查是否为测试模式
        test_mode = self.config.get("system.test_mode", False)
        test_trading_hours = self.config.get("system.test_trading_hours", True)

        if test_mode and test_trading_hours:
            logger.debug("测试模式：跳过交易时间检查")
            return RiskCheckResult(True, "", ["测试模式：跳过交易时间检查"], "low")

        if not self.trading_hours_check:
            return RiskCheckResult(True, "", [], "low")

        import datetime
        now = datetime.datetime.now()
        hour = now.hour
        minute = now.minute

        # 详细的期货交易时间检查
        is_trading_hours = False

        # 上午：9:00-11:30
        if (hour == 9 and minute >= 0) or (hour == 10) or (hour == 11 and minute <= 30):
            is_trading_hours = True
        # 下午：13:30-15:00
        elif (hour == 13 and minute >= 30) or (hour == 14) or (hour == 15 and minute == 0):
            is_trading_hours = True
        # 夜盘：21:00-次日2:30
        elif hour >= 21 or hour <= 2:
            if hour == 2 and minute > 30:
                is_trading_hours = False
            else:
                is_trading_hours = True

        if not is_trading_hours:
            return RiskCheckResult(False, "", [f"当前时间 {hour:02d}:{minute:02d} 不在交易时间内"], "critical")

        return RiskCheckResult(True, "", [], "low")

    def _check_order_value_limit(self, order_request: OrderRequest) -> RiskCheckResult:
        """检查单笔订单价值限制"""
        try:
            order_value = order_request.price * order_request.volume

            # 根据不同合约类型设置不同的限制（这里简化处理）
            multiplier = 10  # 假设每手价值是价格*10（实际应根据合约规格）
            actual_order_value = order_value * multiplier

            if actual_order_value > self.max_single_order_value:
                return RiskCheckResult(False, "", [
                    f"订单价值 {actual_order_value} 超过单笔限制 {self.max_single_order_value}"
                ], "high")

            return RiskCheckResult(True, "", [], "low")

        except Exception as e:
            logger.error(f"订单价值检查异常: {e}")
            return RiskCheckResult(False, "", [f"订单价值计算异常: {e}"], "critical")

    def _check_order_frequency(self, strategy_id: str) -> RiskCheckResult:
        """检查订单频率"""
        current_time = time.time()
        one_minute_ago = current_time - 60

        # 获取策略的订单历史
        if strategy_id not in self.order_frequency:
            self.order_frequency[strategy_id] = {}

        # 清理过期数据
        self.order_frequency[strategy_id] = {
            ts: count for ts, count in self.order_frequency[strategy_id].items()
            if ts > one_minute_ago
        }

        # 计算当前分钟的订单数
        current_minute = int(current_time // 60)
        orders_this_minute = self.order_frequency[strategy_id].get(current_minute, 0)

        if orders_this_minute >= self.order_frequency_limit:
            return RiskCheckResult(False, "", [
                f"策略 {strategy_id} 订单频率过高: {orders_this_minute}/{self.order_frequency_limit} 每分钟"
            ], "high")

        # 更新计数
        self.order_frequency[strategy_id][current_minute] = orders_this_minute + 1

        return RiskCheckResult(True, "", [], "low")

    def _check_position_concentration(self, strategy_id: str, order_request: OrderRequest) -> RiskCheckResult:
        """检查持仓集中度"""
        # 简化实现
        return RiskCheckResult(True, "", [], "low")

    async def check_risk(self, order_request: OrderRequest, strategy_id: str) -> RiskCheckResult:
        """风控检查"""
        if not self.enabled:
            return RiskCheckResult(True, "", [], "low")

        violations = []
        max_risk_level = "low"
        order_id = f"{strategy_id}_{int(time.time() * 1000)}"

        try:
            # 1. 交易时间检查
            time_check = self._trading_hours_check()
            if not time_check.passed:
                violations.extend(time_check.reasons)
                max_risk_level = max(max_risk_level, time_check.risk_level,
                                     key=lambda x: {"low": 0, "medium": 1, "high": 2, "critical": 3}[x])

            # 2. 订单大小检查
            if order_request.volume > self.max_order_size:
                violations.append(f"订单手数 {order_request.volume} 超过限制 {self.max_order_size}")
                max_risk_level = max(max_risk_level, "high",
                                     key=lambda x: {"low": 0, "medium": 1, "high": 2, "critical": 3}[x])

            # 3. 订单价值检查
            value_check = self._check_order_value_limit(order_request)
            if not value_check.passed:
                violations.extend(value_check.reasons)
                max_risk_level = max(max_risk_level, value_check.risk_level,
                                     key=lambda x: {"low": 0, "medium": 1, "high": 2, "critical": 3}[x])

            # 4. 增强价格检查
            price_check = self._enhanced_price_check(order_request)
            if not price_check.passed:
                violations.extend(price_check.reasons)
                max_risk_level = max(max_risk_level, price_check.risk_level,
                                     key=lambda x: {"low": 0, "medium": 1, "high": 2, "critical": 3}[x])

            # 5. 订单频率检查
            freq_check = self._check_order_frequency(strategy_id)
            if not freq_check.passed:
                violations.extend(freq_check.reasons)
                max_risk_level = max(max_risk_level, freq_check.risk_level,
                                     key=lambda x: {"low": 0, "medium": 1, "high": 2, "critical": 3}[x])

            # 6. 持仓集中度检查（简化）
            concentration_check = self._check_position_concentration(strategy_id, order_request)
            if not concentration_check.passed:
                violations.extend(concentration_check.reasons)
                max_risk_level = max(max_risk_level, concentration_check.risk_level,
                                     key=lambda x: {"low": 0, "medium": 1, "high": 2, "critical": 3}[x])

            # 记录风控检查结果
            result = RiskCheckResult(len(violations) == 0, order_id, violations, max_risk_level)

            if result.passed:
                logger.debug(f"风控检查通过: {strategy_id} {order_request.symbol}")
            else:
                logger.warning(f"风控检查失败: {strategy_id} {order_request.symbol} - {violations}")

            return result

        except Exception as e:
            logger.error(f"风控检查异常: {e}")
            return RiskCheckResult(False, order_id, [f"风控检查异常: {e}"], "critical")

    async def _handle_risk_check(self, event: Event):
        """处理风控检查请求（完整版）"""
        data = event.data
        order_request = data["order_request"]
        strategy_id = data["strategy_id"]

        # 执行风控检查
        risk_result = await self.check_risk(order_request, strategy_id)

        if risk_result.passed:
            # 风控通过，发布批准事件
            self.event_bus.publish(Event(EventType.RISK_APPROVED, {
                "order_request": order_request,
                "strategy_id": strategy_id,
                "risk_result": risk_result
            }))
            logger.info(f"风控检查通过: {strategy_id} {order_request.symbol}")
        else:
            # 风控拒绝，发布拒绝事件
            self.event_bus.publish(Event(EventType.RISK_REJECTED, {
                "order_request": order_request,
                "strategy_id": strategy_id,
                "risk_result": risk_result,
                "violations": risk_result.reasons
            }))
            logger.warning(f"风控检查拒绝: {strategy_id} {order_request.symbol} - {risk_result.reasons}")
