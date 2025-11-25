#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : risk.py
@Date       : 2025/9/10 16:48
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 风控模块 - 交易信号风险检查和控制
"""
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from threading import Lock
from typing import Dict, Optional, Any, cast

from src.core.constants import Direction, Offset
from src.core.event import Event, EventType
from src.core.event_bus import EventBus
from src.core.object import OrderRequest
from src.utils.log import get_logger


@dataclass
class RiskCheckResult:
    """风控检查结果"""
    passed: bool
    reason: str = ""
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PositionInfo:
    """持仓信息"""
    instrument_id: str
    long_position: int = 0
    short_position: int = 0
    long_frozen: int = 0  # 冻结多头
    short_frozen: int = 0  # 冻结空头
    last_update: Optional[datetime] = None
    
    def __post_init__(self):
        if self.last_update is None:
            self.last_update = datetime.now()
    
    @property
    def net_position(self) -> int:
        """净持仓"""
        return self.long_position - self.short_position
    
    @property
    def available_long(self) -> int:
        """可平多头"""
        return max(0, self.long_position - self.long_frozen)
    
    @property
    def available_short(self) -> int:
        """可平空头"""
        return max(0, self.short_position - self.short_frozen)


class RiskManager:
    """
    风险管理器
    
    功能：
    - 交易信号风险检查
    - 资金管理和持仓限制
    - 交易频率控制
    - 价格异常检查
    - 风险规则配置管理
    """

    def __init__(self, event_bus: EventBus):
        self.event_bus: EventBus = event_bus
        self.logger = get_logger("RiskManager")
        
        # 风险参数配置
        self.config = {
            # 资金管理
            "max_total_risk_ratio": 0.02,  # 总风险敞口不超过2%
            "max_single_position_ratio": 0.01,  # 单个持仓不超过1%
            "max_daily_loss_ratio": 0.05,  # 日最大亏损5%
            
            # 持仓限制
            "max_position_per_instrument": 100,  # 单合约最大持仓
            "max_order_volume": 50,  # 单笔最大下单量
            
            # 交易频率限制
            "max_orders_per_second": 5,  # 每秒最大下单数
            "max_orders_per_minute": 60,  # 每分钟最大下单数
            "max_cancel_ratio": 0.8,  # 最大撤单比例
            
            # 价格检查
            "max_price_deviation": 0.05,  # 价格偏离限制5%
            "min_tick_size": 0.01,  # 最小价格变动
            
            # 时间限制
            "trading_start_time": "09:00:00",
            "trading_end_time": "15:00:00",
            "night_trading_start": "21:00:00",
            "night_trading_end": "02:30:00",
        }
        
        # 持仓管理
        self.positions: Dict[str, PositionInfo] = {}
        self.positions_lock = Lock()
        
        # 资金信息
        self.account_balance = 0.0
        self.available_funds = 0.0
        self.total_margin = 0.0
        self.daily_pnl = 0.0
        
        # 交易统计
        self.order_count_per_second: Dict[int, int] = defaultdict(int)
        self.order_count_per_minute: Dict[int, int] = defaultdict(int)
        self.cancel_count = 0
        self.total_order_count = 0
        
        # 价格缓存（用于价格检查）
        self.last_prices: Dict[str, float] = {}
        self.price_lock = Lock()
        
        # 风险事件统计
        self.risk_events: Dict[str, int] = defaultdict(int)
        
        self.logger.info("风险管理器初始化完成")
    
    async def startup(self):
        """启动风险管理器"""
        self.logger.info("风险管理器启动中...")
        
        # 订阅相关事件
        self.event_bus.subscribe(EventType.TRADE_SIGNAL, self._handle_trade_signal)
        self.event_bus.subscribe(EventType.POSITION_UPDATE, self._handle_position_update)
        self.event_bus.subscribe(EventType.ACCOUNT_UPDATE, self._handle_account_update)
        self.event_bus.subscribe(EventType.TICK, self._handle_price_update)
        
        self.logger.info("风险管理器启动完成")
    
    async def shutdown(self):
        """关闭风险管理器"""
        self.logger.info("风险管理器关闭中...")
        # 这里可以添加保存风险统计数据等清理工作
        self.logger.info("风险管理器已关闭")
    
    def update_config(self, new_config: Dict[str, Any]):
        """更新风险参数配置"""
        self.config.update(new_config)
        self.logger.info(f"风险配置已更新: {list(new_config.keys())}")
    
    def risk_check(self, order_request: OrderRequest, strategy_id: Optional[str] = None) -> RiskCheckResult:
        """
        综合风险检查
        
        Args:
            order_request: 订单请求
            strategy_id: 策略ID
        
        Returns:
            RiskCheckResult: 检查结果
        """
        try:
            # 1. 基础参数检查
            result = self._check_basic_params(order_request)
            if not result.passed:
                return result
            
            # 2. 资金检查
            result = self._check_funds(order_request)
            if not result.passed:
                return result
            
            # 3. 持仓限制检查
            result = self._check_position_limits(order_request)
            if not result.passed:
                return result
            
            # 4. 交易频率检查
            result = self._check_trading_frequency(order_request, strategy_id)
            if not result.passed:
                return result
            
            # 5. 价格异常检查
            result = self._check_price_validity(order_request)
            if not result.passed:
                return result
            
            # 6. 交易时间检查
            result = self._check_trading_time(order_request)
            if not result.passed:
                return result
            
            # 所有检查通过
            self.logger.debug(f"风控检查通过: {order_request.instrument_id} {order_request.direction.value} {order_request.volume}")
            return RiskCheckResult(True, "风控检查通过")
            
        except Exception as e:
            self.logger.error(f"风控检查异常: {e}", exc_info=True)
            return RiskCheckResult(False, f"风控检查异常: {str(e)}")
    
    def _check_basic_params(self, order_request: OrderRequest) -> RiskCheckResult:
        """基础参数检查"""
        # 检查订单量
        if order_request.volume <= 0:
            return RiskCheckResult(False, "订单量必须大于0")
        
        max_order_volume: int = int(cast(int, self.config.get("max_order_volume", 50)))
        if order_request.volume > max_order_volume:
            return RiskCheckResult(False, f"单笔订单量超限: {order_request.volume} > {max_order_volume}")
        
        # 检查价格
        if order_request.price <= 0:
            return RiskCheckResult(False, "订单价格必须大于0")
        
        # 检查合约代码
        if not order_request.instrument_id or len(order_request.instrument_id.strip()) == 0:
            return RiskCheckResult(False, "合约代码不能为空")
        
        return RiskCheckResult(True)
    
    def _check_funds(self, order_request: OrderRequest) -> RiskCheckResult:
        """资金检查"""
        if self.available_funds <= 0:
            return RiskCheckResult(False, "可用资金不足")
        
        # 估算所需保证金（简化计算）
        estimated_margin = order_request.price * order_request.volume * 0.1  # 假设10%保证金
        
        if estimated_margin > self.available_funds:
            return RiskCheckResult(False, f"资金不足: 需要{estimated_margin:.2f}, 可用{self.available_funds:.2f}")
        
        # 检查总风险敞口
        max_total_risk_ratio: float = float(cast(float, self.config.get("max_total_risk_ratio", 0.02)))
        risk_ratio = (self.total_margin + estimated_margin) / max(self.account_balance, 1)
        if risk_ratio > max_total_risk_ratio:
            return RiskCheckResult(False, f"总风险敞口超限: {risk_ratio:.4f} > {max_total_risk_ratio}")
        
        # 检查日亏损限制
        if self.daily_pnl < 0:
            max_daily_loss_ratio: float = float(cast(float, self.config.get("max_daily_loss_ratio", 0.05)))
            loss_ratio = abs(self.daily_pnl) / max(self.account_balance, 1)
            if loss_ratio > max_daily_loss_ratio:
                return RiskCheckResult(False, f"日亏损超限: {loss_ratio:.4f} > {max_daily_loss_ratio}")
        
        return RiskCheckResult(True)
    
    def _check_position_limits(self, order_request: OrderRequest) -> RiskCheckResult:
        """持仓限制检查"""
        with self.positions_lock:
            position = self.positions.get(order_request.instrument_id)
            if not position:
                position = PositionInfo(order_request.instrument_id)
                self.positions[order_request.instrument_id] = position
            
            # 模拟订单执行后的持仓
            new_long = position.long_position
            new_short = position.short_position
            
            if order_request.offset == Offset.OPEN:
                # 开仓
                if order_request.direction == Direction.LONG:
                    new_long += order_request.volume
                else:
                    new_short += order_request.volume
            else:
                # 平仓 - 检查是否有足够持仓可平
                if order_request.direction == Direction.LONG:
                    # 买入平空
                    if order_request.volume > position.available_short:
                        return RiskCheckResult(False, f"可平空头不足: 需要{order_request.volume}, 可用{position.available_short}")
                    new_short -= order_request.volume
                else:
                    # 卖出平多
                    if order_request.volume > position.available_long:
                        return RiskCheckResult(False, f"可平多头不足: 需要{order_request.volume}, 可用{position.available_long}")
                    new_long -= order_request.volume
            
            # 检查单合约持仓限制
            max_position_per_instrument: int = int(cast(int, self.config.get("max_position_per_instrument", 100)))
            max_position = max(new_long, new_short)
            if max_position > max_position_per_instrument:
                return RiskCheckResult(False, f"单合约持仓超限: {max_position} > {max_position_per_instrument}")
        
        return RiskCheckResult(True)
    
    def _check_trading_frequency(self, order_request: OrderRequest, strategy_id: Optional[str] = None) -> RiskCheckResult:
        """交易频率检查"""
        now = int(time.time())
        current_minute = now // 60
        
        # 检查每秒下单频率
        max_orders_per_second: int = int(cast(int, self.config.get("max_orders_per_second", 5)))
        self.order_count_per_second[now] += 1
        if self.order_count_per_second[now] > max_orders_per_second:
            return RiskCheckResult(False, f"每秒下单频率超限: {self.order_count_per_second[now]} > {max_orders_per_second}")
        
        # 检查每分钟下单频率
        max_orders_per_minute: int = int(cast(int, self.config.get("max_orders_per_minute", 60)))
        self.order_count_per_minute[current_minute] += 1
        if self.order_count_per_minute[current_minute] > max_orders_per_minute:
            return RiskCheckResult(False, f"每分钟下单频率超限: {self.order_count_per_minute[current_minute]} > {max_orders_per_minute}")
        
        # 检查撤单比例
        if self.total_order_count > 0:
            max_cancel_ratio: float = float(cast(float, self.config.get("max_cancel_ratio", 0.8)))
            cancel_ratio = self.cancel_count / self.total_order_count
            if cancel_ratio > max_cancel_ratio:
                return RiskCheckResult(False, f"撤单比例过高: {cancel_ratio:.4f} > {max_cancel_ratio}")
        
        return RiskCheckResult(True)
    
    def _check_price_validity(self, order_request: OrderRequest) -> RiskCheckResult:
        """价格有效性检查"""
        with self.price_lock:
            last_price = self.last_prices.get(order_request.instrument_id)
            
            if last_price and last_price > 0:
                # 检查价格偏离
                max_price_deviation: float = float(cast(float, self.config.get("max_price_deviation", 0.05)))
                deviation = abs(order_request.price - last_price) / last_price
                if deviation > max_price_deviation:
                    return RiskCheckResult(False, f"价格偏离过大: {deviation:.4f} > {max_price_deviation}")
        
        # 检查价格精度（使用浮点数容差避免精度问题）
        min_tick: float = float(cast(float, self.config.get("min_tick_size", 0.01)))
        # 使用容差检查，避免浮点数精度问题
        remainder = order_request.price % min_tick
        if abs(remainder) > 1e-9 and abs(remainder - min_tick) > 1e-9:
            return RiskCheckResult(False, f"价格精度错误: 价格必须是{min_tick}的整数倍")
        
        return RiskCheckResult(True)
    
    def _check_trading_time(self, order_request: OrderRequest) -> RiskCheckResult:
        """交易时间检查"""
        now = datetime.now()
        current_time = now.strftime("%H:%M:%S")
        
        # 日盘时间检查
        day_start = str(self.config.get("trading_start_time", "09:00:00"))
        day_end = str(self.config.get("trading_end_time", "15:00:00"))
        
        # 夜盘时间检查
        night_start = str(self.config.get("night_trading_start", "21:00:00"))
        night_end = str(self.config.get("night_trading_end", "02:30:00"))
        
        in_day_session = day_start <= current_time <= day_end
        
        # 夜盘跨日处理
        if night_start > night_end:  # 夜盘跨过午夜
            in_night_session = current_time >= night_start or current_time <= night_end
        else:
            in_night_session = night_start <= current_time <= night_end
        
        if not (in_day_session or in_night_session):
            return RiskCheckResult(False, f"非交易时间: {current_time}")
        
        return RiskCheckResult(True)
    
    def _handle_trade_signal(self, event: Event):
        """处理交易信号事件"""
        try:
            signal_data = event.payload
            
            # 提取订单信息
            order_request = signal_data.get("order_request")
            strategy_id = signal_data.get("strategy_id")
            
            if not order_request:
                self.logger.error("交易信号缺少订单请求数据")
                return
            
            # 执行风险检查
            risk_result = self.risk_check(order_request, strategy_id)
            
            if risk_result.passed:
                # 风控通过，转发给交易网关
                self.logger.info(f"风控检查通过，转发订单: {order_request.instrument_id}")
                
                approved_event = Event(
                    EventType.TRADE_ORDER_APPROVED,
                    payload={
                        "signal_id": event.payload.get("signal_id"),  # 添加 signal_id
                        "order_request": order_request,
                        "strategy_id": strategy_id,
                        "risk_check_result": risk_result
                    }
                )
                self.event_bus.publish(approved_event)
                
                # 更新统计
                self.total_order_count += 1
                
            else:
                # 风控不通过，发送拒绝事件和告警
                self.logger.warning(f"风控检查失败: {risk_result.reason}")
                
                rejected_event = Event(
                    EventType.TRADE_ORDER_REJECTED,
                    payload={
                        "signal_id": event.payload.get("signal_id"),  # 添加 signal_id
                        "order_request": order_request,
                        "strategy_id": strategy_id,
                        "risk_check_result": risk_result
                    }
                )
                self.event_bus.publish(rejected_event)
                
                # 发送告警
                alarm_event = Event(
                    EventType.RISK_ALARM,
                    payload={
                        "alarm_type": "risk_rejection",
                        "severity": "warning",
                        "message": f"交易信号被风控拒绝: {risk_result.reason}",
                        "strategy_id": strategy_id,
                        "instrument_id": order_request.instrument_id if order_request else "unknown",
                        "details": risk_result.details
                    }
                )
                self.event_bus.publish(alarm_event)
                
                # 统计风险事件
                self.risk_events[risk_result.reason] += 1
                
        except Exception as e:
            self.logger.error(f"处理交易信号异常: {e}", exc_info=True)
    
    def _handle_position_update(self, event: Event):
        """处理持仓更新事件"""
        try:
            position_data = event.payload
            
            instrument_id = position_data.get("instrument_id")
            if not instrument_id:
                return
            
            with self.positions_lock:
                if instrument_id not in self.positions:
                    self.positions[instrument_id] = PositionInfo(instrument_id)
                
                position = self.positions[instrument_id]
                position.long_position = position_data.get("long_position", 0)
                position.short_position = position_data.get("short_position", 0)
                position.long_frozen = position_data.get("long_frozen", 0)
                position.short_frozen = position_data.get("short_frozen", 0)
                position.last_update = datetime.now()
                
        except Exception as e:
            self.logger.error(f"处理持仓更新异常: {e}", exc_info=True)
    
    def _handle_account_update(self, event: Event):
        """处理账户更新事件"""
        try:
            account_data = event.payload
            
            self.account_balance = account_data.get("balance", 0.0)
            self.available_funds = account_data.get("available", 0.0)
            self.total_margin = account_data.get("margin", 0.0)
            
        except Exception as e:
            self.logger.error(f"处理账户更新异常: {e}", exc_info=True)
    
    def _handle_price_update(self, event: Event):
        """处理价格更新事件（tick数据）"""
        try:
            tick_data = event.payload.get("data")
            if not tick_data:
                return
            
            instrument_id = tick_data.instrument_id
            last_price = tick_data.last_price
            
            with self.price_lock:
                self.last_prices[instrument_id] = last_price
                
        except Exception as e:
            self.logger.error(f"处理价格更新异常: {e}", exc_info=True)
    
    def get_risk_statistics(self) -> Dict[str, Any]:
        """获取风险统计信息"""
        return {
            "total_orders": self.total_order_count,
            "cancel_count": self.cancel_count,
            "cancel_ratio": self.cancel_count / max(self.total_order_count, 1),
            "risk_events": dict(self.risk_events),
            "position_count": len(self.positions),
            "account_balance": self.account_balance,
            "available_funds": self.available_funds,
            "daily_pnl": self.daily_pnl,
            "config": self.config.copy()
        }


# 向后兼容的别名
Risk = RiskManager
