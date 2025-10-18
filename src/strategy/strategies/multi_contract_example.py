#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : multi_contract_example.py
@Date       : 2025/10/16 23:45
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 多合约策略示例 - 展示如何在单个策略中处理多个合约
"""
from typing import Any

from src.core.constants import Interval
from src.core.object import TickData, BarData, OrderData, TradeData
from src.strategy.base_strategy import SpecificStrategyApi
from src.utils.log import get_logger


class MultiContractStrategy(SpecificStrategyApi):
    """
    多合约策略示例
    
    功能演示：
    1. SA601: 开仓逻辑（基于移动平均线突破）
    2. FG601: 平仓逻辑（基于价格变化率）
    """
    
    def __init__(self):
        # 订阅多个合约
        instruments = ["SA601", "FG601"]
        strategy_name = "multi_contract_example"
        strategy_content = "多合约策略示例"
        sub_kline_type = [Interval.MINUTE]

        super().__init__(
            instruments = instruments,
            strategy_name = strategy_name,
            strategy_content = strategy_content,
            sub_kline_type = sub_kline_type
        )

        self.logger = get_logger(self.__class__.__name__)
        
        # 明确 instruments 类型，避免 lint 错误
        self.instruments: list[str] = instruments
        
        # 策略参数
        self.ma_period = 20
        self.open_threshold = 0.02  # 开仓阈值
        self.close_threshold = 0.01  # 平仓阈值
        
        # 合约特定配置
        self.contract_config = {
            "SA601": {"position_size": 2, "stop_loss": 0.03, "role": "open"},
            "FG601": {"position_size": 1, "stop_loss": 0.02, "role": "close"}
        }
        
        # 策略状态
        self.last_signals: dict[str, Any | None] = {ins: None for ins in self.instruments}
        self.entry_prices: dict[str, float] = {ins: 0.0 for ins in self.instruments}

    def on_init(self) -> None:
        """策略初始化"""
        self.logger.info("多合约策略初始化")
        self.logger.info(f"订阅合约: {self.instruments}")
        for ins, config in self.contract_config.items():
            print(f"  {ins}: 角色={config['role']}, 手数={config['position_size']}")

    def on_close(self) -> None:
        """收盘处理"""
        self.logger.info(f"收盘处理，当前持仓: {self.positions}")

    def on_alarm(self) -> None:
        """闹钟处理"""
        pass

    def on_tick(self, tick: TickData) -> None:
        """处理tick数据"""
        instrument_id = tick.instrument_id
        
        # 【测试打印】验证策略是否正常接收tick数据
        print(f"[MultiContractStrategy] 收到tick: {instrument_id} | "
              f"最新价: {tick.last_price:.2f} | "
              f"买一: {tick.bid_price_1:.2f}({tick.bid_volume_1}) | "
              f"卖一: {tick.ask_price_1:.2f}({tick.ask_volume_1}) | "
              f"时间: {tick.update_time}")
        
        # 更新价格数据
        self.prices[instrument_id].append(tick.last_price)
        if len(self.prices[instrument_id]) > 100:
            self.prices[instrument_id] = self.prices[instrument_id][-100:]
        
        # 根据合约角色执行不同逻辑
        config = self.contract_config.get(instrument_id, {})
        role = config.get("role", "unknown")
        
        if role == "open":
            self._handle_open_logic(instrument_id, tick)
        elif role == "close":
            self._handle_close_logic(instrument_id, tick)
        
        # 执行跨合约分析
        self._cross_contract_analysis()

    def _handle_open_logic(self, instrument_id: str, tick: TickData):
        """处理开仓逻辑（SA601）"""
        prices = self.prices[instrument_id]
        if len(prices) < self.ma_period:
            return
            
        # 计算移动平均线
        ma = sum(prices[-self.ma_period:]) / self.ma_period
        current_price = tick.last_price
        
        # 开仓信号检测
        if current_price > ma * (1 + self.open_threshold) and self.positions[instrument_id] == 0:
            self._open_position(instrument_id, "buy", current_price)
        elif current_price < ma * (1 - self.open_threshold) and self.positions[instrument_id] == 0:
            self._open_position(instrument_id, "sell", current_price)

    def _handle_close_logic(self, instrument_id: str, tick: TickData):
        """处理平仓逻辑（FG601）"""
        if self.positions[instrument_id] == 0:
            return
            
        prices = self.prices[instrument_id]
        if len(prices) < 10:
            return
            
        # 基于价格变化率的平仓信号
        price_change = (tick.last_price - prices[-10]) / prices[-10]
        entry_price = self.entry_prices[instrument_id]
        
        # 止损或止盈
        if entry_price > 0:
            pnl_rate = (tick.last_price - entry_price) / entry_price
            if self.positions[instrument_id] < 0:  # 空头持仓
                pnl_rate = -pnl_rate
                
            # 止损或价格变化超过阈值
            stop_loss = self.contract_config[instrument_id]["stop_loss"]
            if pnl_rate < -stop_loss or abs(price_change) > self.close_threshold:
                self._close_position(instrument_id, tick.last_price)

    def _cross_contract_analysis(self):
        """跨合约分析"""
        # 检查是否有足够的数据进行跨合约分析
        if not all(len(self.prices[ins]) > 0 for ins in self.instruments):
            return
            
        # 简单的相关性分析示例
        if len(self.prices["SA601"]) >= 20 and len(self.prices["FG601"]) >= 20:
            sa_prices = self.prices["SA601"][-20:]
            fg_prices = self.prices["FG601"][-20:]
            
            # 计算价格变化率的相关性（简化版本）
            sa_returns = [(sa_prices[i] - sa_prices[i-1]) / sa_prices[i-1] for i in range(1, len(sa_prices))]
            fg_returns = [(fg_prices[i] - fg_prices[i-1]) / fg_prices[i-1] for i in range(1, len(fg_prices))]
            
            if len(sa_returns) == len(fg_returns) and len(sa_returns) > 0:
                # 简单的相关性指标
                correlation_signal = sum(sa_returns[i] * fg_returns[i] for i in range(len(sa_returns)))
                if abs(correlation_signal) > 0.001:
                    self.logger.info(f"SA601-FG601 相关性信号: {correlation_signal:.6f}")

    def _open_position(self, instrument_id: str, direction: str, price: float):
        """开仓"""
        config = self.contract_config[instrument_id]
        size = config["position_size"]
        
        self.logger.info(f"[{instrument_id}] 开仓 {direction} {size}手 @ {price}")
        
        # 更新持仓和入场价格
        if direction == "buy":
            self.positions[instrument_id] += size
        else:
            self.positions[instrument_id] -= size
            
        self.entry_prices[instrument_id] = price
        self.last_signals[instrument_id] = {"action": "open", "direction": direction, "price": price}
        
        # 这里可以调用实际的下单接口
        # self.place_order(instrument_id, direction, size, price)

    def _close_position(self, instrument_id: str, price: float):
        """平仓"""
        current_pos = self.positions[instrument_id]
        if current_pos == 0:
            return
            
        self.logger.info(f"[{instrument_id}] 平仓 {abs(current_pos)}手 @ {price}")
        
        # 计算盈亏
        entry_price = self.entry_prices[instrument_id]
        if entry_price > 0:
            pnl = (price - entry_price) * current_pos
            self.logger.info(f"[{instrument_id}] 盈亏: {pnl:.2f}")
        
        # 清空持仓
        self.positions[instrument_id] = 0
        self.entry_prices[instrument_id] = 0.0
        self.last_signals[instrument_id] = {"action": "close", "price": price}
        
        # 这里可以调用实际的平仓接口
        # self.close_position(instrument_id, abs(current_pos), price)

    def on_bar(self, bar: BarData) -> None:
        """K线数据处理"""
        instrument_id = bar.instrument_id
        self.logger.info(f"[{instrument_id}] 收到K线: O={bar.open_price} H={bar.high_price} L={bar.low_price} C={bar.close_price}")

    def on_trade(self, trade: TradeData) -> None:
        """成交回报处理"""
        instrument_id = trade.instrument_id
        self.logger.info(f"[{instrument_id}] 成交回报: {trade.volume}手 @ {trade.price}")

    def on_order(self, order: OrderData) -> None:
        """订单状态变化处理"""
        instrument_id = order.instrument_id
        self.logger.info(f"[{instrument_id}] 订单状态: {order.order_status}")

    # ========== 状态持久化 ==========
    
    def save_state(self) -> dict:
        """保存策略状态"""
        return {
            "positions": self.positions,
            "prices": {ins: prices[-10:] for ins, prices in self.prices.items()},  # 只保存最近10个价格
            "entry_prices": self.entry_prices,
            "last_signals": self.last_signals
        }
    
    def load_state(self, state: dict):
        """加载策略状态"""
        if state:
            self.positions = state.get("positions", {ins: 0 for ins in self.instruments})
            self.prices = state.get("prices", {ins: [] for ins in self.instruments})
            self.entry_prices = state.get("entry_prices", {ins: 0.0 for ins in self.instruments})
            self.last_signals = state.get("last_signals", {ins: None for ins in self.instruments})
            self.logger.info("多合约状态已恢复")
            self.logger.info(f"  持仓: {self.positions}")
            self.logger.info(f"  入场价格: {self.entry_prices}")

def get_strategy():
    return MultiContractStrategy()
