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
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from datetime import datetime

from src.config.config_manager import ConfigManager
from src.core.event import Event, EventType, create_trading_event, create_critical_event
from src.core.event_bus import EventBus
from src.core.logger import get_logger
from src.core.object import OrderRequest, OrderData, TradeData, TickData, PositionData, AccountData, Status

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
            
            # 创建策略实例
            strategy_class = getattr(module, 'Strategy', None)
            if strategy_class is None:
                raise ValueError("策略文件中未找到Strategy类")
            
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
            # 调用策略的启动方法
            await strategy_info.instance.on_start()
            
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
            # 调用策略的停止方法
            await strategy_info.instance.on_stop()
            
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
        return {
            strategy_id: self.get_strategy_status(strategy_id)
            for strategy_id in self.strategies
        }


class RiskManager:
    """风控管理器"""
    
    def __init__(self, event_bus: EventBus, config: ConfigManager):
        self.event_bus = event_bus
        self.config = config
        
        # 风控规则
        self.rules = self._load_risk_rules()
        
        # 运行时数据
        self.position_tracker: Dict[str, PositionData] = {}
        self.daily_stats = {
            "total_pnl": 0.0,
            "order_count": 0,
            "last_reset": time.time()
        }
        self.order_frequency = deque(maxlen=100)  # 订单频率控制
        
        # 注册事件处理器
        self.event_bus.subscribe("risk.check", self._handle_risk_check)
        
    def _load_risk_rules(self) -> Dict[str, Any]:
        """加载风控规则"""
        return {
            'max_position_size': self.config.get('risk.max_position_size', 1000000),
            'max_daily_loss': self.config.get('risk.max_daily_loss', 50000),
            'max_order_size': self.config.get('risk.max_order_size', 100),
            'order_frequency_limit': self.config.get('risk.order_frequency_limit', 10),
            'position_concentration': self.config.get('risk.position_concentration', 0.3),
            'enable_self_trade_check': self.config.get('risk.enable_self_trade_check', True),
            'enable_price_check': self.config.get('risk.enable_price_check', True),
            'price_deviation_threshold': self.config.get('risk.price_deviation_threshold', 0.05)
        }
    
    async def check_order_risk(self, order_request: OrderRequest, strategy_id: str) -> RiskCheckResult:
        """并行风控检查"""
        order_id = str(uuid.uuid4())
        reasons = []
        risk_level = "low"
        
        try:
            # 并行执行多个风控检查
            checks = await asyncio.gather(
                self._check_order_size(order_request),
                self._check_daily_loss_limit(order_request),
                self._check_position_limit(order_request, strategy_id),
                self._check_frequency_limit(),
                self._check_price_validity(order_request),
                return_exceptions=True
            )
            
            # 处理检查结果
            for i, result in enumerate(checks):
                if isinstance(result, Exception):
                    reasons.append(f"风控检查异常: {str(result)}")
                    risk_level = "critical"
                elif not result:
                    check_names = [
                        "订单大小检查", "日亏损限制检查", "持仓限制检查", 
                        "频率限制检查", "价格有效性检查"
                    ]
                    reasons.append(f"{check_names[i]}未通过")
                    if risk_level != "critical":
                        risk_level = "high"
            
            passed = len(reasons) == 0
            
            # 创建检查结果
            result = RiskCheckResult(
                passed=passed,
                order_id=order_id,
                reasons=reasons,
                risk_level=risk_level
            )
            
            # 发布风控结果事件
            if passed:
                self.event_bus.publish(create_trading_event(
                    EventType.RISK_APPROVED,
                    {"order_request": order_request, "strategy_id": strategy_id, "order_id": order_id},
                    "RiskManager"
                ))
            else:
                self.event_bus.publish(create_critical_event(
                    EventType.RISK_REJECTED,
                    {
                        "order_request": order_request,
                        "strategy_id": strategy_id,
                        "reasons": reasons,
                        "risk_level": risk_level
                    },
                    "RiskManager"
                ))
            
            return result
            
        except Exception as e:
            logger.error(f"风控检查异常: {e}")
            return RiskCheckResult(
                passed=False,
                order_id=order_id,
                reasons=[f"风控系统异常: {str(e)}"],
                risk_level="critical"
            )
    
    async def _check_order_size(self, order_request: OrderRequest) -> bool:
        """检查订单大小"""
        max_size = self.rules['max_order_size']
        return order_request.volume <= max_size
    
    async def _check_daily_loss_limit(self, order_request: OrderRequest) -> bool:
        """检查当日亏损限制"""
        max_loss = self.rules['max_daily_loss']
        return abs(self.daily_stats['total_pnl']) < max_loss
    
    async def _check_position_limit(self, order_request: OrderRequest, strategy_id: str) -> bool:
        """检查持仓限制"""
        max_position = self.rules['max_position_size']
        # 简化检查：假设当前持仓总值小于限制
        return True  # 具体实现需要根据实际持仓计算
    
    async def _check_frequency_limit(self) -> bool:
        """检查下单频率"""
        current_time = time.time()
        self.order_frequency.append(current_time)
        
        # 统计最近一秒的订单数量
        one_second_ago = current_time - 1.0
        recent_orders = sum(1 for t in self.order_frequency if t >= one_second_ago)
        
        limit = self.rules['order_frequency_limit']
        return recent_orders <= limit
    
    async def _check_price_validity(self, order_request: OrderRequest) -> bool:
        """检查价格有效性"""
        if not self.rules['enable_price_check']:
            return True
        
        # 简化实现：检查价格是否为正数
        return order_request.price > 0
    
    def _handle_risk_check(self, event: Event):
        """处理风控检查请求"""
        data = event.data
        asyncio.create_task(self.check_order_risk(
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
        
        # 注册事件处理器
        self.event_bus.subscribe(EventType.RISK_APPROVED, self._handle_risk_approved)
        self.event_bus.subscribe(EventType.ORDER_FILLED, self._handle_order_filled)
        self.event_bus.subscribe(EventType.ORDER_CANCELLED, self._handle_order_cancelled)
        self.event_bus.subscribe("order.place", self._handle_order_request)
        self.event_bus.subscribe("order.cancel", self._handle_cancel_order)
    
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
        
        # 发布订单事件
        self.event_bus.publish(Event("order.submitted", order_data))
        
        # 自动mock成交回报（1秒后）
        asyncio.create_task(self._mock_trade_fill(order_data, 1.0))
        
        logger.info(f"处理下单请求: {order_id} {order_request.symbol} {order_request.direction.value if order_request.direction else 'UNKNOWN'} {order_request.volume}@{order_request.price}")
    
    async def _mock_trade_fill(self, order_data: OrderData, delay: float):
        """模拟订单成交"""
        await asyncio.sleep(delay)
        
        # 创建成交数据
        trade_data = TradeData(
            symbol=order_data.symbol,
            exchange=order_data.exchange,
            orderid=order_data.orderid,
            trade_id=f"mock_{order_data.orderid}",
            direction=order_data.direction,
            offset=order_data.offset,
            price=order_data.price,
            volume=order_data.volume,
            datetime=datetime.now(),
            gateway_name="CTP_TD"
        )
        
        # 更新订单状态为已成交
        order_data.status = Status.ALL_TRADED
        order_data.traded = order_data.volume
        
        # 发布成交事件
        self.event_bus.publish(Event("order.filled", trade_data))
        self.event_bus.publish(Event("order.updated", order_data))
        
        logger.info(f"模拟成交: {trade_data.trade_id} {trade_data.symbol} {trade_data.direction.value if trade_data.direction else 'UNKNOWN'} {trade_data.volume}@{trade_data.price}")
    
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
    
    def _handle_account_update(self, event: Event):
        """处理账户更新"""
        account_data = event.data
        if isinstance(account_data, AccountData):
            self.accounts[account_data.account_id] = account_data
    
    def _handle_position_update(self, event: Event):
        """处理持仓更新"""
        position_data = event.data
        if isinstance(position_data, PositionData):
            position_key = f"{position_data.symbol}.{position_data.direction.value}"
            self.positions[position_key] = position_data
    
    def _handle_trade_update(self, event: Event):
        """处理成交更新，计算策略盈亏"""
        trade_data = event.data
        if isinstance(trade_data, TradeData):
            # 简化盈亏计算逻辑
            # 实际应用中需要根据具体的持仓和价格变化计算
            pass
    
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
        
        if action == "place_order":
            # 策略请求下单 -> 风控检查
            order_request = data["order_request"]
            strategy_id = data["strategy_id"]
            
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
        return {
            "is_running": self.is_running,
            "start_time": self.start_time,
            "strategies": self.strategy_manager.get_all_strategies(),
            "account_info": self.account_manager.get_total_account_info()
        } 