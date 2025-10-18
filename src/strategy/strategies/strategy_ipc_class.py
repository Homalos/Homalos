#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : strategy_ipc_class.py
@Date       : 2025/10/16 11:12
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 示例策略 - 双层设计实现
"""
from src.core.constants import Interval
from src.core.object import TickData, BarData, OrderData, TradeData
from src.strategy.base_strategy import BaseStrategy, SpecificStrategy
from src.utils.log import get_logger


class StrategyIpc(BaseStrategy):
    """
    示例策略 - 双层设计
    """
    def __init__(self):
        """策略初始化"""
        super().__init__()
        self.strategy_name = "strategy_ipc_class"
        self.strategy_content = "示例策略 - 完整实现所有抽象方法"
        self.author = "Lumosylva"
        self.instruments = ["ru2601"]
        self.bar_intervals = [Interval.MINUTE]
        self.logger = get_logger(self.strategy_name)
        
        # 初始化每个合约的策略实例
        self.specific_strategy_map: dict[str, SpecificStrategy] = {}
        for instrument_id in self.instruments:
            self.specific_strategy_map[instrument_id] = StrategyIpc.Specific(
                self.strategy_id,
                instrument_id,
                self.bar_intervals
            )
    
    class Specific(SpecificStrategy):
        """合约级策略实现"""
        
        def __init__(self, strategy_id: str, instrument_id: str, bar_intervals: list[Interval]):
            super().__init__(instrument_id, bar_intervals)
            self.strategy_id = strategy_id
            self.logger = get_logger(f"StrategyIpc.{instrument_id}")
            self.tick_count = 0
            self.bar_count = 0
            self.prices: list[float] = []  # 用于演示状态持久化

        def on_init(self) -> None:
            """开盘前执行"""
            self.logger.info(f"[{self.instrument_id}] 策略初始化")

        def on_close(self) -> None:
            """收盘后执行"""
            self.logger.info(f"[{self.instrument_id}] 收盘处理")

        def on_alarm(self) -> None:
            """到达设置闹钟时间时执行"""
            pass

        def on_tick(self, tick: TickData) -> None:
            """有新的tick产生时执行"""
            self.tick_count += 1
            # 记录价格用于状态持久化演示
            last_price = tick.last_price
            self.prices.append(last_price)
            # 只保留最近100个价格
            if len(self.prices) > 100:
                self.prices = self.prices[-100:]
            
            if self.tick_count % 10 == 0:
                self.logger.info(f"[{self.instrument_id}] 已处理 {self.tick_count} 个tick, 价格={last_price:.2f}")

        def on_bar(self, bar: BarData) -> None:
            """有新的Bar产生时执行"""
            self.bar_count += 1
            self.logger.info(f"[{self.instrument_id}] 收到第 {self.bar_count} 个bar")

        def on_trade(self, trade: TradeData) -> None:
            """有订单成交时执行"""
            pass

        def on_order(self, order: OrderData) -> None:
            """订单状态发生改变时执行"""
            pass
        
        # ========== 状态持久化实现 ==========
        
        def save_state(self) -> dict:
            """
            保存策略状态
            
            系统会每5分钟自动调用此方法，保存策略状态到文件
            """
            return {
                "tick_count": self.tick_count,
                "bar_count": self.bar_count,
                "prices": self.prices[-10:] if self.prices else []  # 只保存最近10个价格
            }
        
        def load_state(self, state: dict):
            """
            加载策略状态
            
            在策略启动时，如果存在保存的状态，系统会自动调用此方法恢复状态
            """
            if state:
                self.tick_count = state.get("tick_count", 0)
                self.bar_count = state.get("bar_count", 0)
                self.prices = state.get("prices", [])
                self.logger.info(f"[{self.instrument_id}] 已恢复状态: tick_count={self.tick_count}, "
                               f"bar_count={self.bar_count}, prices={len(self.prices)}个")


def get_strategy():
    return StrategyIpc()
