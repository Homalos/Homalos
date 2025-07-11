#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos_v2
@FileName   : trading_engine
@Date       : 2025/7/6 20:30
@Author     : Donny
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 交易引擎核心 - 集成策略、风控、订单管理
"""
import asyncio
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Any

from src.config.config_manager import ConfigManager
from src.core.event import Event, EventType, create_trading_event
from src.core.event_bus import EventBus
from src.core.logger import get_logger
from src.core.object import OrderRequest, OrderData, TradeData, TickData, PositionData, AccountData, Status
from src.services.performance_monitor import PerformanceMonitor


logger = get_logger("TradingEngine")


@dataclass
class StrategyInfo:
    """策略信息"""
    strategy_id: str
    strategy_name: str
    instance: Any
    status: str  # "loading", "loaded", "running", "stopped", "error"
    params: Dict[str, Any]
    start_time: Optional[float] = None
    stop_time: Optional[float] = None
    error_message: Optional[str] = None


@dataclass
class RiskCheckResult:
    """风控检查结果"""
    passed: bool
    order_id: str
    reasons: List[str]
    risk_level: str  # "low", "medium", "high", "critical"


@dataclass
class OrderInfo:
    """订单信息扩展"""
    order_data: OrderData
    strategy_id: str
    create_time: float
    update_time: float
    risk_check_result: Optional[RiskCheckResult] = None


class StrategyManager:
    """策略管理器"""
    
    def __init__(self, event_bus: EventBus, config: ConfigManager):
        self.event_bus = event_bus
        self.config = config
        self.strategies: Dict[str, StrategyInfo] = {}
        self.strategy_subscriptions: Dict[str, set] = defaultdict(set)  # strategy_id -> symbols
        
        # 注册事件处理器
        self.event_bus.subscribe("market.tick", self._handle_market_tick)
        self.event_bus.subscribe("strategy.load", self._handle_load_strategy)
        self.event_bus.subscribe("strategy.start", self._handle_start_strategy)
        self.event_bus.subscribe("strategy.stop", self._handle_stop_strategy)
    
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
    
    async def load_strategy(self, strategy_path: str, strategy_id: str, params: Dict[str, Any]) -> bool:
        """动态加载策略"""
        try:
            import importlib.util
            
            # 动态导入策略模块
            spec = importlib.util.spec_from_file_location("strategy", strategy_path)
            if spec is None or spec.loader is None:
                raise ValueError(f"无法加载策略文件: {strategy_path}")
            
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # 创建策略实例 - 自动发现策略类
            strategy_class = self._find_strategy_class(module)
            if strategy_class is None:
                raise ValueError("策略文件中未找到继承自BaseStrategy的策略类")
            
            strategy_instance = strategy_class(strategy_id, self.event_bus, params)
            
            # 注册策略信息
            strategy_info = StrategyInfo(
                strategy_id=strategy_id,
                strategy_name=getattr(strategy_instance, 'strategy_name', strategy_id),
                instance=strategy_instance,
                status="loaded",
                params=params
            )
            
            self.strategies[strategy_id] = strategy_info
            
            # 发布策略加载事件
            self.event_bus.publish(create_trading_event(
                EventType.STRATEGY_SIGNAL,
                {
                    "action": "loaded",
                    "strategy_id": strategy_id,
                    "strategy_name": strategy_info.strategy_name
                },
                "StrategyManager"
            ))
            
            logger.info(f"策略加载成功: {strategy_id} ({strategy_info.strategy_name})")
            return True
            
        except Exception as e:
            logger.error(f"策略加载失败 {strategy_id}: {e}")
            if strategy_id in self.strategies:
                self.strategies[strategy_id].status = "error"
                self.strategies[strategy_id].error_message = str(e)
            return False
    
    async def start_strategy(self, strategy_id: str) -> bool:
        """启动策略"""
        if strategy_id not in self.strategies:
            logger.error(f"策略不存在: {strategy_id}")
            return False
        
        strategy_info = self.strategies[strategy_id]
        if strategy_info.status == "running":
            logger.warning(f"策略已在运行: {strategy_id}")
            return True
        
        try:
            # 修改：调用策略的start()方法，这会自动处理initialize() -> on_init() -> on_start()流程
            await strategy_info.instance.start()
            
            strategy_info.status = "running"
            strategy_info.start_time = time.time()
            
            logger.info(f"策略启动成功: {strategy_id}")
            return True
            
        except Exception as e:
            logger.error(f"策略启动失败 {strategy_id}: {e}")
            strategy_info.status = "error"
            strategy_info.error_message = str(e)
            return False
    
    async def stop_strategy(self, strategy_id: str) -> bool:
        """停止策略"""
        if strategy_id not in self.strategies:
            logger.error(f"策略不存在: {strategy_id}")
            return False
        
        strategy_info = self.strategies[strategy_id]
        
        try:
            # 修改：调用策略的stop()方法
            await strategy_info.instance.stop()
            
            strategy_info.status = "stopped"
            strategy_info.stop_time = time.time()
            
            logger.info(f"策略停止成功: {strategy_id}")
            return True
            
        except Exception as e:
            logger.error(f"策略停止失败 {strategy_id}: {e}")
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
        strategy_id = event.data["strategy_id"]
        asyncio.create_task(self.start_strategy(strategy_id))
    
    def _handle_stop_strategy(self, event: Event):
        """处理策略停止请求"""
        strategy_id = event.data["strategy_id"]
        asyncio.create_task(self.stop_strategy(strategy_id))
    
    def get_strategy_status(self, strategy_id: str) -> Optional[Dict[str, Any]]:
        """获取策略状态"""
        if strategy_id not in self.strategies:
            return None
        
        strategy_info = self.strategies[strategy_id]
        return {
            "strategy_id": strategy_info.strategy_id,
            "strategy_name": strategy_info.strategy_name,
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


class RiskManager:
    """风控管理器"""
    
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
        self.event_bus.subscribe("risk.check", self._handle_risk_check)
        self.event_bus.subscribe("strategy.error", self._handle_strategy_error)
        self.event_bus.subscribe("market.tick", self._update_market_prices)
        
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
                self.event_bus.publish(Event("risk.strategy_suspend_recommended", {
                    "strategy_id": strategy_id,
                    "error_count": error_count,
                    "reason": "错误次数超过阈值"
                }))
    
    def _check_market_conditions(self):
        """检查市场条件"""
        if not self.trading_hours_check:
            return
        
        # 简化的交易时间检查
        import datetime
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
        """增强的价格合理性检查"""
        if not self.enable_price_check:
            return RiskCheckResult(True, "", [], "low")
        
        symbol = order_request.symbol
        order_price = order_request.price
        
        # 获取最新市场价格
        last_price = self.last_prices.get(symbol)
        if not last_price:
            # 没有最新价格，允许通过但记录警告
            logger.warning(f"无法获取 {symbol} 的最新价格，跳过价格检查")
            return RiskCheckResult(True, "", ["无最新价格数据"], "medium")
        
        # 计算价格偏离度
        price_deviation = abs(order_price - last_price) / last_price
        
        if price_deviation > self.price_deviation_threshold:
            return RiskCheckResult(False, "", [
                f"订单价格 {order_price} 偏离市场价格 {last_price} 超过 {self.price_deviation_threshold*100}%"
            ], "high")
        
        return RiskCheckResult(True, "", [], "low")
    
    def _trading_hours_check(self) -> RiskCheckResult:
        """交易时间检查"""
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
                max_risk_level = max(max_risk_level, time_check.risk_level, key=lambda x: {"low": 0, "medium": 1, "high": 2, "critical": 3}[x])
            
            # 2. 订单大小检查
            if order_request.volume > self.max_order_size:
                violations.append(f"订单手数 {order_request.volume} 超过限制 {self.max_order_size}")
                max_risk_level = max(max_risk_level, "high", key=lambda x: {"low": 0, "medium": 1, "high": 2, "critical": 3}[x])
            
            # 3. 订单价值检查
            value_check = self._check_order_value_limit(order_request)
            if not value_check.passed:
                violations.extend(value_check.reasons)
                max_risk_level = max(max_risk_level, value_check.risk_level, key=lambda x: {"low": 0, "medium": 1, "high": 2, "critical": 3}[x])
            
            # 4. 增强价格检查
            price_check = self._enhanced_price_check(order_request)
            if not price_check.passed:
                violations.extend(price_check.reasons)
                max_risk_level = max(max_risk_level, price_check.risk_level, key=lambda x: {"low": 0, "medium": 1, "high": 2, "critical": 3}[x])
            
            # 5. 订单频率检查
            freq_check = self._check_order_frequency(strategy_id)
            if not freq_check.passed:
                violations.extend(freq_check.reasons)
                max_risk_level = max(max_risk_level, freq_check.risk_level, key=lambda x: {"low": 0, "medium": 1, "high": 2, "critical": 3}[x])
            
            # 6. 持仓集中度检查（简化）
            concentration_check = self._check_position_concentration(strategy_id, order_request)
            if not concentration_check.passed:
                violations.extend(concentration_check.reasons)
                max_risk_level = max(max_risk_level, concentration_check.risk_level, key=lambda x: {"low": 0, "medium": 1, "high": 2, "critical": 3}[x])
            
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
    
    def _handle_risk_check(self, event: Event):
        """处理风控检查请求"""
        data = event.data
        asyncio.create_task(self.check_risk(
            data["order_request"],
            data["strategy_id"]
        ))


class OrderManager:
    """订单管理器"""
    
    def __init__(self, event_bus: EventBus, config: ConfigManager):
        self.event_bus = event_bus
        self.config = config
        
        self.orders: Dict[str, OrderInfo] = {}
        self.strategy_orders: Dict[str, set] = defaultdict(set)  # strategy_id -> order_ids
        # 添加订单ID映射：系统订单ID -> CTP订单ID
        self.system_to_ctp_orderid: Dict[str, str] = {}
        self.ctp_to_system_orderid: Dict[str, str] = {}
        
        # 注册事件处理器
        self.event_bus.subscribe(EventType.RISK_APPROVED, self._handle_risk_approved)
        self.event_bus.subscribe(EventType.ORDER_FILLED, self._handle_order_filled)
        self.event_bus.subscribe(EventType.ORDER_CANCELLED, self._handle_order_cancelled)
        self.event_bus.subscribe("order.place", self._handle_order_request)
        self.event_bus.subscribe("order.cancel", self._handle_cancel_order)
        
        # 订阅CTP网关回报事件
        self.event_bus.subscribe(EventType.ORDER, self._handle_ctp_order_update)
        self.event_bus.subscribe(EventType.TRADE, self._handle_ctp_trade_update)
        self.event_bus.subscribe("order.sent_to_ctp", self._handle_order_sent_to_ctp)
        self.event_bus.subscribe("order.send_failed", self._handle_order_send_failed)
    
    async def place_order(self, order_request: OrderRequest, strategy_id: str) -> str:
        """下单"""
        order_id = str(uuid.uuid4())
        current_time = time.time()
        
        # 创建订单数据
        order_data = order_request.create_order_data(order_id, "TradingEngine")
        
        # 创建订单信息
        order_info = OrderInfo(
            order_data=order_data,
            strategy_id=strategy_id,
            create_time=current_time,
            update_time=current_time
        )
        
        self.orders[order_id] = order_info
        self.strategy_orders[strategy_id].add(order_id)
        
        # 发布下单事件（将由网关处理）
        self.event_bus.publish(create_trading_event(
            "gateway.send_order",
            {"order_data": order_data},
            "OrderManager"
        ))
        
        # 发布订单提交事件（供监控器监听）
        self.event_bus.publish(Event("order.submitted", order_data))
        
        logger.info(f"订单已提交: {order_id} ({strategy_id})")
        return order_id
    
    async def cancel_order(self, order_id: str) -> bool:
        """撤单"""
        if order_id not in self.orders:
            logger.error(f"订单不存在: {order_id}")
            return False
        
        order_info = self.orders[order_id]
        
        # 创建撤单请求
        cancel_request = order_info.order_data.create_cancel_request()
        
        # 发布撤单事件
        self.event_bus.publish(create_trading_event(
            "gateway.cancel_order",
            {"cancel_request": cancel_request},
            "OrderManager"
        ))
        
        logger.info(f"撤单请求已发送: {order_id}")
        return True
    
    def _handle_risk_approved(self, event: Event):
        """处理风控通过事件"""
        data = event.data
        order_request = data["order_request"]
        strategy_id = data["strategy_id"]
        
        # 创建订单
        asyncio.create_task(self.place_order(order_request, strategy_id))
    
    def _handle_order_filled(self, event: Event):
        """处理订单成交事件"""
        trade_data = event.data
        if isinstance(trade_data, TradeData):
            logger.info(f"订单成交: {trade_data.orderid} - {trade_data.volume}@{trade_data.price}")
    
    def _handle_order_cancelled(self, event: Event):
        """处理订单撤销事件"""
        order_data = event.data
        if isinstance(order_data, OrderData):
            logger.info(f"订单已撤销: {order_data.orderid}")
    
    def _handle_order_request(self, event: Event):
        """处理下单请求"""
        data = event.data
        order_request = data.get("order_request")
        strategy_id = data.get("strategy_id")
        
        if not order_request or not strategy_id:
            logger.error("下单请求数据不完整")
            return
        
        # 生成订单ID
        order_id = f"{strategy_id}_{int(time.time() * 1000)}"
        
        # 创建订单数据
        order_data = order_request.create_order_data(order_id, "CTP_TD")
        order_data.datetime = datetime.now()
        
        # 存储订单信息
        order_info = OrderInfo(
            order_data=order_data,
            strategy_id=strategy_id,
            create_time=time.time(),
            update_time=time.time()
        )
        self.orders[order_id] = order_info
        self.strategy_orders[strategy_id].add(order_id)
        
        # 发布订单提交事件
        self.event_bus.publish(Event("order.submitted", order_data))
        
        # 转发到CTP网关进行真实下单
        self.event_bus.publish(create_trading_event(
            "gateway.send_order",
            {
                "order_request": order_request,
                "order_data": order_data
            },
            "OrderManager"
        ))
        
        logger.info(f"转发下单请求到CTP网关: {order_id} {order_request.symbol} {order_request.direction.value if order_request.direction else 'UNKNOWN'} {order_request.volume}@{order_request.price}")
    
    def _handle_cancel_order(self, event: Event):
        """处理撤单请求"""
        order_id = event.data["order_id"]
        asyncio.create_task(self.cancel_order(order_id))
    
    def get_strategy_orders(self, strategy_id: str) -> List[Dict[str, Any]]:
        """获取策略的所有订单"""
        order_ids = self.strategy_orders.get(strategy_id, set())
        return [
            {
                "order_id": order_id,
                "order_data": self.orders[order_id].order_data.__dict__,
                "create_time": self.orders[order_id].create_time,
                "update_time": self.orders[order_id].update_time
            }
            for order_id in order_ids if order_id in self.orders
        ]

    def _handle_ctp_order_update(self, event: Event):
        """处理CTP订单状态更新"""
        order_data = event.data
        if isinstance(order_data, OrderData):
            # 通过CTP订单ID找到系统订单ID
            ctp_order_id = order_data.orderid
            system_order_id = self.ctp_to_system_orderid.get(ctp_order_id)
            
            if system_order_id and system_order_id in self.orders:
                # 更新系统中的订单信息
                order_info = self.orders[system_order_id]
                order_info.order_data.status = order_data.status
                order_info.order_data.traded = order_data.traded
                order_info.update_time = time.time()
                
                logger.info(f"订单状态更新: {system_order_id} -> {order_data.status.value}")
                
                # 转发给策略
                self.event_bus.publish(Event("order.updated", order_info.order_data))
            else:
                # 可能是其他来源的订单，记录日志
                logger.debug(f"收到未知CTP订单更新: {ctp_order_id}")
    
    def _handle_ctp_trade_update(self, event: Event):
        """处理CTP成交回报"""
        trade_data = event.data
        if isinstance(trade_data, TradeData):
            # 通过CTP订单ID找到系统订单ID
            ctp_order_id = trade_data.orderid
            system_order_id = self.ctp_to_system_orderid.get(ctp_order_id)
            
            if system_order_id and system_order_id in self.orders:
                order_info = self.orders[system_order_id]
                
                logger.info(f"订单成交: {system_order_id} - {trade_data.volume}@{trade_data.price}")
                
                # 发布成交事件给AccountManager和策略
                self.event_bus.publish(Event("order.filled", trade_data))
                
                # 更新订单状态
                if order_info.order_data.traded >= order_info.order_data.volume:
                    order_info.order_data.status = Status.ALL_TRADED
                else:
                    order_info.order_data.status = Status.PART_TRADED
                
                order_info.update_time = time.time()
                
                # 通知策略
                self.event_bus.publish(Event("order.updated", order_info.order_data))
            else:
                logger.debug(f"收到未知CTP成交回报: {ctp_order_id}")
    
    def _handle_order_sent_to_ctp(self, event: Event):
        """处理订单已发送到CTP的确认"""
        data = event.data
        ctp_order_id = data.get("order_id")
        order_data = data.get("order_data")
        
        if ctp_order_id and order_data:
            system_order_id = order_data.orderid
            
            # 建立订单ID映射
            self.system_to_ctp_orderid[system_order_id] = ctp_order_id
            self.ctp_to_system_orderid[ctp_order_id] = system_order_id
            
            # 更新订单状态为已提交
            if system_order_id in self.orders:
                self.orders[system_order_id].order_data.status = Status.SUBMITTING
                self.orders[system_order_id].update_time = time.time()
            
            logger.info(f"订单已发送到CTP: {system_order_id} -> {ctp_order_id}")
    
    def _handle_order_send_failed(self, event: Event):
        """处理订单发送失败"""
        data = event.data
        order_data = data.get("order_data")
        reason = data.get("reason", "未知原因")
        
        if order_data:
            system_order_id = order_data.orderid
            
            # 更新订单状态为被拒绝
            if system_order_id in self.orders:
                self.orders[system_order_id].order_data.status = Status.REJECTED
                self.orders[system_order_id].update_time = time.time()
                
                # 通知策略
                self.event_bus.publish(Event("order.updated", self.orders[system_order_id].order_data))
            
            logger.error(f"订单发送失败: {system_order_id} - {reason}")


class AccountManager:
    """账户管理器"""
    
    def __init__(self, event_bus: EventBus, config: ConfigManager):
        self.event_bus = event_bus
        self.config = config
        
        self.accounts: Dict[str, AccountData] = {}
        self.positions: Dict[str, PositionData] = {}
        self.strategy_pnl: Dict[str, float] = defaultdict(float)
        
        # 注册事件处理器
        self.event_bus.subscribe(EventType.ACCOUNT_UPDATE, self._handle_account_update)
        self.event_bus.subscribe(EventType.POSITION_UPDATE, self._handle_position_update)
        self.event_bus.subscribe(EventType.ORDER_FILLED, self._handle_trade_update)
        
        # 添加定期查询任务
        self._last_query_time = 0
        self._query_interval = 30  # 30秒查询一次
        
        # 启动定期查询任务
        asyncio.create_task(self._periodic_query_task())
    
    async def _periodic_query_task(self):
        """定期查询账户和持仓"""
        while True:
            try:
                await asyncio.sleep(self._query_interval)
                current_time = time.time()
                
                if current_time - self._last_query_time >= self._query_interval:
                    # 发布查询请求事件
                    self.event_bus.publish(Event("gateway.query_account", {}))
                    self.event_bus.publish(Event("gateway.query_position", {}))
                    self._last_query_time = current_time
                    
            except Exception as e:
                from src.core.logger import get_logger
                logger = get_logger("AccountManager")
                logger.error(f"定期查询任务异常: {e}")
                await asyncio.sleep(5)  # 异常后等待5秒再继续
    
    def _handle_account_update(self, event: Event):
        """处理账户更新"""
        account_data = event.data
        if isinstance(account_data, AccountData):
            self.accounts[account_data.account_id] = account_data
            
            from src.core.logger import get_logger
            logger = get_logger("AccountManager")
            logger.info(f"账户更新: {account_data.account_id} 余额={account_data.balance} 可用={account_data.available}")
    
    def _handle_position_update(self, event: Event):
        """处理持仓更新"""
        position_data = event.data
        if isinstance(position_data, PositionData):
            position_key = f"{position_data.symbol}.{position_data.direction.value}"
            self.positions[position_key] = position_data
            
            from src.core.logger import get_logger
            logger = get_logger("AccountManager")
            logger.info(f"持仓更新: {position_key} 数量={position_data.volume} 均价={position_data.price}")
    
    def _handle_trade_update(self, event: Event):
        """处理成交更新，计算策略盈亏"""
        trade_data = event.data
        if isinstance(trade_data, TradeData):
            # 简化盈亏计算逻辑
            # 实际应用中需要根据具体的持仓和价格变化计算
            from src.core.logger import get_logger
            logger = get_logger("AccountManager")
            logger.info(f"成交更新: {trade_data.symbol} {trade_data.direction.value if trade_data.direction else 'UNKNOWN'} {trade_data.volume}@{trade_data.price}")
    
    def get_strategy_pnl(self, strategy_id: str) -> float:
        """获取策略盈亏"""
        return self.strategy_pnl.get(strategy_id, 0.0)
    
    def get_total_account_info(self) -> Dict[str, Any]:
        """获取总账户信息"""
        total_balance = sum(acc.balance for acc in self.accounts.values())
        total_frozen = sum(acc.frozen for acc in self.accounts.values())
        
        return {
            "total_balance": total_balance,
            "total_frozen": total_frozen,
            "available": total_balance - total_frozen,
            "account_count": len(self.accounts)
        }


class TradingEngine:
    """交易引擎核心 - 集成策略、风控、订单管理"""
    
    def __init__(self, event_bus: EventBus, config: ConfigManager):
        self.event_bus = event_bus
        self.config = config
        
        # 初始化各管理器
        self.strategy_manager = StrategyManager(event_bus, config)
        self.risk_manager = RiskManager(event_bus, config)
        self.order_manager = OrderManager(event_bus, config)
        self.account_manager = AccountManager(event_bus, config)
        
        # 引擎状态
        self.is_running = False
        self.start_time: Optional[float] = None
        
        # 初始化性能监控器
        self.performance_monitor = PerformanceMonitor(event_bus, config)
        
        # 设置事件处理器
        self._setup_event_handlers()
        
        logger.info("交易引擎核心初始化完成")
    
    def _setup_event_handlers(self):
        """设置事件处理器链"""
        # 策略信号 -> 风控检查 -> 订单执行
        self.event_bus.subscribe(EventType.STRATEGY_SIGNAL, self._handle_strategy_signal)
        
        # 系统控制事件
        self.event_bus.subscribe("engine.start", self._handle_engine_start)
        self.event_bus.subscribe("engine.stop", self._handle_engine_stop)
    
    async def initialize(self):
        """初始化交易引擎"""
        try:
            logger.info("正在初始化交易引擎...")
            
            # 可以在这里执行一些初始化任务
            # 例如：加载默认策略、连接数据库等
            
            logger.info("交易引擎初始化完成")
            return True
        except Exception as e:
            logger.error(f"交易引擎初始化失败: {e}")
            return False
    
    async def start(self):
        """启动交易引擎"""
        if self.is_running:
            logger.warning("交易引擎已在运行")
            return
        
        self.is_running = True
        self.start_time = time.time()
        
        # 启动性能监控
        self.performance_monitor.start_monitoring()
        
        logger.info("交易引擎已启动")
        
        # 发布引擎启动事件
        self.event_bus.publish(create_trading_event(
            "engine.started",
            {"start_time": self.start_time},
            "TradingEngine"
        ))
    
    async def stop(self):
        """停止交易引擎"""
        if not self.is_running:
            logger.warning("交易引擎未在运行")
            return
        
        # 停止所有策略
        for strategy_id in list(self.strategy_manager.strategies.keys()):
            await self.strategy_manager.stop_strategy(strategy_id)
        
        # 停止性能监控
        self.performance_monitor.stop_monitoring()
        
        self.is_running = False
        
        logger.info("交易引擎已停止")
        
        # 发布引擎停止事件
        self.event_bus.publish(create_trading_event(
            "engine.stopped",
            {"stop_time": time.time()},
            "TradingEngine"
        ))
    
    def _handle_strategy_signal(self, event: Event):
        """处理策略信号"""
        data = event.data
        action = data.get("action")
        strategy_id = data.get("strategy_id", "unknown")
        
        # 记录订单处理开始时间（用于延迟计算）
        process_start_time = time.time()
        
        if action == "place_order":
            # 策略请求下单 -> 风控检查
            order_request = data["order_request"]
            
            # 记录订单下达事件
            self.event_bus.publish(Event("strategy.order_placed", {
                "strategy_id": strategy_id,
                "order_request": order_request.__dict__ if hasattr(order_request, '__dict__') else str(order_request),
                "timestamp": process_start_time
            }))
            
            # 发布风控检查事件
            self.event_bus.publish(create_trading_event(
                "risk.check",
                {"order_request": order_request, "strategy_id": strategy_id},
                "TradingEngine"
            ))
        
        elif action == "cancel_order":
            # 策略请求撤单
            order_id = data["order_id"]
            self.event_bus.publish(create_trading_event(
                "order.cancel",
                {"order_id": order_id},
                "TradingEngine"
            ))
    
    def _handle_engine_start(self, event: Event):
        """处理引擎启动请求"""
        asyncio.create_task(self.start())
    
    def _handle_engine_stop(self, event: Event):
        """处理引擎停止请求"""
        asyncio.create_task(self.stop())
    
    def get_engine_status(self) -> Dict[str, Any]:
        """获取引擎状态"""
        base_status = {
            "is_running": self.is_running,
            "start_time": self.start_time,
            "strategies": self.strategy_manager.get_all_strategies(),
            "account_info": self.account_manager.get_total_account_info()
        }
        
        # 集成性能监控数据
        if self.performance_monitor:
            base_status["performance"] = {
                "system_metrics": self.performance_monitor.get_system_metrics(),
                "strategy_performance": {
                    strategy_id: self.performance_monitor.get_performance_summary(strategy_id)
                    for strategy_id in self.strategy_manager.strategies.keys()
                }
            }
        
        return base_status
    
    def get_performance_metrics(self, strategy_id: str) -> Dict[str, Any]:
        """获取特定策略的性能指标"""
        if self.performance_monitor:
            return self.performance_monitor.get_performance_summary(strategy_id)
        return {}
    
    def get_system_performance(self) -> Dict[str, Any]:
        """获取系统性能指标"""
        if self.performance_monitor:
            return self.performance_monitor.get_system_metrics()
        return {} 