#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : simple_ma_cross.py
@Date       : 2025/10/16 11:32
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 双均线交叉策略 - 双层设计实现
"""
from src.core.constants import Interval
from src.core.object import TickData, BarData, OrderData, TradeData
from src.strategy.base_strategy import BaseStrategy, SpecificStrategy
from src.utils.log import get_logger


class SimpleMACrossStrategy(BaseStrategy):
    """
    双均线交叉策略 - 双层设计
    
    策略逻辑：
    - 金叉（快线上穿慢线）：开多仓
    - 死叉（快线下穿慢线）：平多仓或开空仓
    - 使用K线数据计算均线，避免tick数据噪音
    """
    
    def __init__(self):
        super().__init__()
        self.strategy_name = "simple_ma_cross_strategy"
        self.strategy_content = "简单双均线交叉策略"
        self.author = "Lumosylva"
        self.instruments = ["SA601"]  # 纯碱主力合约
        self.bar_intervals = [Interval.MINUTE]
        self.logger = get_logger(self.strategy_name)
        
        # 初始化每个合约的策略实例
        self.specific_strategy_map: dict[str, SpecificStrategy] = {}
        for instrument_id in self.instruments:
            self.specific_strategy_map[instrument_id] = SimpleMACrossStrategy.Specific(
                self.strategy_id,
                instrument_id,
                self.bar_intervals
            )
    
    class Specific(SpecificStrategy):
        """合约级双均线策略实现"""
        
        def __init__(self, strategy_id: str, instrument_id: str, bar_intervals: list[Interval]):
            super().__init__(instrument_id, bar_intervals)
            self.strategy_id = strategy_id
            self.logger = get_logger(f"SimpleMACross.{instrument_id}")
            
            # 策略参数
            self.fast_period = 5  # 快线周期
            self.slow_period = 20  # 慢线周期
            self.position_size = 1  # 每次交易手数
            
            # 策略状态
            self.bars: list[BarData] = []
            self.fast_ma: float = 0.0
            self.slow_ma: float = 0.0
            self.last_cross_signal: str | None = None  # "golden" or "death"
            self.position: int = 0
        
        def on_init(self) -> None:
            """策略初始化"""
            self.logger.info("=" * 60)
            self.logger.info(f"[{self.instrument_id}] 双均线交叉策略初始化")
            self.logger.info(f"  快线周期: {self.fast_period}, 慢线周期: {self.slow_period}")
            self.logger.info(f"  每次交易手数: {self.position_size}")
            self.logger.info("=" * 60)
        
        def on_close(self) -> None:
            """收盘处理"""
            self.logger.info("=" * 60)
            self.logger.info(f"[{self.instrument_id}] 收盘处理 - 当前持仓: {self.position}")
            self.logger.info("=" * 60)
        
        def on_alarm(self) -> None:
            """闹钟处理"""
            pass
        
        def on_tick(self, tick: TickData) -> None:
            """
            Tick数据处理
            双均线策略主要基于K线，tick数据仅用于监控
            """
            # 可以在这里添加tick级别的监控逻辑
            pass
        
        def on_bar(self, bar: BarData) -> None:
            """
            K线数据处理 - 策略核心逻辑
            """
            # 保存K线数据
            self.bars.append(bar)
            
            # 只保留最近的 slow_period + 10 根K线
            max_bars = self.slow_period + 10
            if len(self.bars) > max_bars:
                self.bars = self.bars[-max_bars:]
            
            # 需要足够的K线数据才能计算慢线
            if len(self.bars) < self.slow_period:
                self.logger.info(
                    f"[{self.instrument_id}] K线数量不足 ({len(self.bars)}/{self.slow_period})，等待更多数据...")
                return
            
            # 计算均线
            self._calculate_ma()
            
            # 检测交叉信号
            self._check_cross_signal(bar)
        
        def _calculate_ma(self):
            """计算快慢均线"""
            # 计算快线（最近N根K线的收盘价平均）
            fast_closes = [b.close_price for b in self.bars[-self.fast_period:]]
            self.fast_ma = sum(fast_closes) / len(fast_closes)
            
            # 计算慢线
            slow_closes = [b.close_price for b in self.bars[-self.slow_period:]]
            self.slow_ma = sum(slow_closes) / len(slow_closes)
        
        def _check_cross_signal(self, current_bar: BarData):
            """检测均线交叉信号"""
            # 至少需要两根K线才能检测交叉
            if len(self.bars) < self.slow_period + 1:
                return
            
            # 获取当前和前一根K线的均线值
            current_fast = self.fast_ma
            current_slow = self.slow_ma
            
            # 计算前一根K线的均线（使用前一根K线之前的数据）
            prev_bars = self.bars[:-1]
            if len(prev_bars) < self.slow_period:
                return
            
            prev_fast_closes = [b.close_price for b in prev_bars[-self.fast_period:]]
            prev_fast = sum(prev_fast_closes) / len(prev_fast_closes)
            
            prev_slow_closes = [b.close_price for b in prev_bars[-self.slow_period:]]
            prev_slow = sum(prev_slow_closes) / len(prev_slow_closes)
            
            # 检测金叉（快线上穿慢线）
            if prev_fast <= prev_slow and current_fast > current_slow:
                self._on_golden_cross(current_bar)
            
            # 检测死叉（快线下穿慢线）
            elif prev_fast >= prev_slow and current_fast < current_slow:
                self._on_death_cross(current_bar)
        
        def _on_golden_cross(self, bar: BarData):
            """金叉信号处理 - 开多仓"""
            self.logger.info("=" * 60)
            self.logger.info(f"🟢 [{self.instrument_id}] 金叉信号！")
            self.logger.info(f"   快线: {self.fast_ma:.2f}, 慢线: {self.slow_ma:.2f}")
            self.logger.info(f"   当前价格: {bar.close_price:.2f}, 当前持仓: {self.position}")
            
            # 如果有空仓，先平仓
            if self.position < 0:
                self.logger.info(f"   → 平空仓: {abs(self.position)} 手 @ {bar.close_price:.2f}")
                self.position = 0
            
            # 开多仓
            if self.position == 0:
                self.logger.info(f"   → 开多仓: {self.position_size} 手 @ {bar.close_price:.2f}")
                self.position = self.position_size
                self.last_cross_signal = "golden"
            
            self.logger.info("=" * 60)
        
        def _on_death_cross(self, bar: BarData):
            """死叉信号处理 - 平多仓或开空仓"""
            self.logger.info("=" * 60)
            self.logger.info(f"🔴 [{self.instrument_id}] 死叉信号！")
            self.logger.info(f"   快线: {self.fast_ma:.2f}, 慢线: {self.slow_ma:.2f}")
            self.logger.info(f"   当前价格: {bar.close_price:.2f}, 当前持仓: {self.position}")
            
            # 如果有多仓，先平仓
            if self.position > 0:
                self.logger.info(f"   → 平多仓: {self.position} 手 @ {bar.close_price:.2f}")
                self.position = 0
            
            # 可选：开空仓（保守策略可以不开空）
            # if self.position == 0:
            #     self.logger.info(f"   → 开空仓: {self.position_size} 手 @ {bar.close_price:.2f}")
            #     self.position = -self.position_size
            #     self.last_cross_signal = "death"
            
            self.logger.info("=" * 60)
        
        def on_trade(self, trade: TradeData) -> None:
            """成交回报处理"""
            self.logger.info(f"[{self.instrument_id}] 成交回报: {trade.volume}手 @ {trade.price:.2f}")
        
        def on_order(self, order: OrderData) -> None:
            """订单状态变化处理"""
            self.logger.info(f"[{self.instrument_id}] 订单状态: {order.order_status}")
        
        # ========== 状态持久化 ==========
        
        def save_state(self) -> dict:
            """保存策略状态"""
            return {
                "position": self.position,
                "fast_ma": self.fast_ma,
                "slow_ma": self.slow_ma,
                "last_cross_signal": self.last_cross_signal,
                # 只保存最近的K线数据
                "bars": [
                    {
                        "open": b.open_price,
                        "high": b.high_price,
                        "low": b.low_price,
                        "close": b.close_price,
                        "volume": b.volume,
                        "update_time": str(b.update_time)
                    }
                    for b in self.bars[-self.slow_period:]
                ]
            }
        
        def load_state(self, state: dict):
            """加载策略状态"""
            if state:
                self.position = state.get("position", 0)
                self.fast_ma = state.get("fast_ma", 0.0)
                self.slow_ma = state.get("slow_ma", 0.0)
                self.last_cross_signal = state.get("last_cross_signal")
                
                # 注意：这里不完全恢复K线数据，因为需要BarData对象
                # 实际使用中可能需要从BarData重建或者忽略历史K线
                
                self.logger.info(f"[{self.instrument_id}] 双均线策略状态已恢复")
                self.logger.info(f"  持仓: {self.position}")
                self.logger.info(f"  快线: {self.fast_ma:.2f}")
                self.logger.info(f"  慢线: {self.slow_ma:.2f}")
                self.logger.info(f"  最后信号: {self.last_cross_signal}")


def get_strategy():
    """策略工厂函数 - 供系统加载使用"""
    return SimpleMACrossStrategy()
