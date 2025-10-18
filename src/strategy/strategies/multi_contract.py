#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : multi_contract.py
@Date       : 2025/10/16 23:45
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 多合约策略示例 - 展示如何在双层策略中处理多个合约
"""
from src.core.constants import Interval
from src.core.object import TickData, BarData, OrderData, TradeData
from src.strategy.base_strategy import BaseStrategy, SpecificStrategy
from src.utils.log import get_logger


class MultiContractStrategy(BaseStrategy):
    """
    多合约策略 - 双层设计
    
    功能演示：
    1. SA601: 开仓逻辑（基于移动平均线突破）
    2. FG601: 平仓逻辑（基于价格变化率）
    """
    
    def __init__(self):
        super().__init__()
        self.strategy_name = "multi_contract_strategy"
        self.strategy_content = "多合约策略示例 - 双层设计"
        self.author = "Lumosylva"
        self.instruments = ["SA601", "FG601"]
        self.bar_intervals = [Interval.MINUTE]
        self.logger = get_logger(self.strategy_name)
        
        # 合约特定配置（可以传递给 SpecificStrategy）
        self.contract_config = {
            "SA601": {"position_size": 2, "stop_loss": 0.03, "role": "open"},
            "FG601": {"position_size": 1, "stop_loss": 0.02, "role": "close"}
        }
        
        # 初始化每个合约的策略实例
        self.specific_strategy_map: dict[str, SpecificStrategy] = {}
        for instrument_id in self.instruments:
            config = self.contract_config[instrument_id]
            if config["role"] == "open":
                self.specific_strategy_map[instrument_id] = MultiContractStrategy.OpenStrategy(
                    self.strategy_id,
                    instrument_id,
                    self.bar_intervals,
                    config
                )
            else:
                self.specific_strategy_map[instrument_id] = MultiContractStrategy.CloseStrategy(
                    self.strategy_id,
                    instrument_id,
                    self.bar_intervals,
                    config
                )
    
    class OpenStrategy(SpecificStrategy):
        """开仓策略（SA601）"""
        
        def __init__(self, strategy_id: str, instrument_id: str, bar_intervals: list[Interval], config: dict):
            super().__init__(instrument_id, bar_intervals)
            self.strategy_id = strategy_id
            self.logger = get_logger(f"MultiContract.Open.{instrument_id}")
            self.config = config
            
            # 策略参数
            self.ma_period = 20
            self.open_threshold = 0.02
            
            # 策略状态
            self.prices: list[float] = []
            self.last_signal: str | None = None
            self.entry_price: float = 0.0
            self.position: int = 0
        
        def on_init(self) -> None:
            self.logger.info(f"[{self.instrument_id}] 开仓策略初始化")
            self.logger.info(f"  角色: {self.config['role']}, 手数: {self.config['position_size']}")
        
        def on_close(self) -> None:
            self.logger.info(f"[{self.instrument_id}] 收盘处理，当前持仓: {self.position}")
        
        def on_alarm(self) -> None:
            pass
        
        def on_tick(self, tick: TickData) -> None:
            """处理开仓逻辑"""
            # 更新价格数据
            self.prices.append(tick.last_price)
            if len(self.prices) > 100:
                self.prices = self.prices[-100:]
            
            # 需要足够的数据
            if len(self.prices) < self.ma_period:
                return
            
            # 计算移动平均线
            ma = sum(self.prices[-self.ma_period:]) / self.ma_period
            current_price = tick.last_price
            
            # 开仓信号检测
            if current_price > ma * (1 + self.open_threshold) and self.position == 0:
                self._open_position("buy", current_price)
            elif current_price < ma * (1 - self.open_threshold) and self.position == 0:
                self._open_position("sell", current_price)
        
        def _open_position(self, direction: str, price: float):
            """开仓"""
            size = self.config["position_size"]
            self.logger.info(f"[{self.instrument_id}] 开仓 {direction} {size}手 @ {price:.2f}")
            
            if direction == "buy":
                self.position += size
            else:
                self.position -= size
            
            self.entry_price = price
            self.last_signal = f"open_{direction}"
        
        def on_bar(self, bar: BarData) -> None:
            self.logger.info(f"[{self.instrument_id}] K线: C={bar.close_price:.2f}")
        
        def on_trade(self, trade: TradeData) -> None:
            self.logger.info(f"[{self.instrument_id}] 成交: {trade.volume}手 @ {trade.price:.2f}")
        
        def on_order(self, order: OrderData) -> None:
            self.logger.info(f"[{self.instrument_id}] 订单: {order.order_status}")
        
        def save_state(self) -> dict:
            return {
                "prices": self.prices[-10:],
                "last_signal": self.last_signal,
                "entry_price": self.entry_price,
                "position": self.position
            }
        
        def load_state(self, state: dict):
            if state:
                self.prices = state.get("prices", [])
                self.last_signal = state.get("last_signal")
                self.entry_price = state.get("entry_price", 0.0)
                self.position = state.get("position", 0)
                self.logger.info(f"[{self.instrument_id}] 状态已恢复: 持仓={self.position}")
    
    class CloseStrategy(SpecificStrategy):
        """平仓策略（FG601）"""
        
        def __init__(self, strategy_id: str, instrument_id: str, bar_intervals: list[Interval], config: dict):
            super().__init__(instrument_id, bar_intervals)
            self.strategy_id = strategy_id
            self.logger = get_logger(f"MultiContract.Close.{instrument_id}")
            self.config = config
            
            # 策略参数
            self.close_threshold = 0.01
            
            # 策略状态
            self.prices: list[float] = []
            self.last_signal: str | None = None
            self.entry_price: float = 0.0
            self.position: int = 0
        
        def on_init(self) -> None:
            self.logger.info(f"[{self.instrument_id}] 平仓策略初始化")
            self.logger.info(f"  角色: {self.config['role']}, 手数: {self.config['position_size']}")
        
        def on_close(self) -> None:
            self.logger.info(f"[{self.instrument_id}] 收盘处理，当前持仓: {self.position}")
        
        def on_alarm(self) -> None:
            pass
        
        def on_tick(self, tick: TickData) -> None:
            """处理平仓逻辑"""
            # 更新价格数据
            self.prices.append(tick.last_price)
            if len(self.prices) > 100:
                self.prices = self.prices[-100:]
            
            # 没有持仓，不处理
            if self.position == 0:
                return
            
            # 需要足够的数据
            if len(self.prices) < 10:
                return
            
            # 基于价格变化率的平仓信号
            price_change = (tick.last_price - self.prices[-10]) / self.prices[-10]
            
            # 止损或止盈
            if self.entry_price > 0:
                pnl_rate = (tick.last_price - self.entry_price) / self.entry_price
                if self.position < 0:  # 空头持仓
                    pnl_rate = -pnl_rate
                
                # 止损或价格变化超过阈值
                stop_loss = self.config["stop_loss"]
                if pnl_rate < -stop_loss or abs(price_change) > self.close_threshold:
                    self._close_position(tick.last_price)
        
        def _close_position(self, price: float):
            """平仓"""
            if self.position == 0:
                return
            
            self.logger.info(f"[{self.instrument_id}] 平仓 {abs(self.position)}手 @ {price:.2f}")
            
            # 计算盈亏
            if self.entry_price > 0:
                pnl = (price - self.entry_price) * self.position
                self.logger.info(f"[{self.instrument_id}] 盈亏: {pnl:.2f}")
            
            # 清空持仓
            self.position = 0
            self.entry_price = 0.0
            self.last_signal = "close"
        
        def on_bar(self, bar: BarData) -> None:
            self.logger.info(f"[{self.instrument_id}] K线: C={bar.close_price:.2f}")
        
        def on_trade(self, trade: TradeData) -> None:
            self.logger.info(f"[{self.instrument_id}] 成交: {trade.volume}手 @ {trade.price:.2f}")
        
        def on_order(self, order: OrderData) -> None:
            self.logger.info(f"[{self.instrument_id}] 订单: {order.order_status}")
        
        def save_state(self) -> dict:
            return {
                "prices": self.prices[-10:],
                "last_signal": self.last_signal,
                "entry_price": self.entry_price,
                "position": self.position
            }
        
        def load_state(self, state: dict):
            if state:
                self.prices = state.get("prices", [])
                self.last_signal = state.get("last_signal")
                self.entry_price = state.get("entry_price", 0.0)
                self.position = state.get("position", 0)
                self.logger.info(f"[{self.instrument_id}] 状态已恢复: 持仓={self.position}")


def get_strategy():
    return MultiContractStrategy()
