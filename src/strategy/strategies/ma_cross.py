#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : example_ma_cross.py
@Date       : 2025/10/16 10:27
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 双均线交叉策略 - 基于快慢均线交叉的简单趋势跟踪策略（基于类的正确实现）
"""
from src.core.constants import Interval
from src.core.object import TickData, BarData, OrderData, TradeData
from src.strategy.base_strategy import SpecificStrategyApi
from src.utils.log import get_logger


class MACrossStrategy(SpecificStrategyApi):
    """
    双均线交叉策略
    
    策略逻辑：
    - 金叉（快线上穿慢线）：开多仓
    - 死叉（快线下穿慢线）：平多仓
    - 使用K线数据计算均线，避免tick数据噪音
    
    设计原则：
    - 基于 SpecificStrategyApi 类，确保数据过滤生效
    - 明确订阅信息，只接收订阅合约的数据
    - 支持状态持久化和热重载
    """
    
    def __init__(self):
        # 订阅合约 - 明确订阅信息，实现数据隔离
        instruments = ["SA601"]  # 纯碱主力合约
        strategy_name = "ma_cross_strategy"
        strategy_content = "双均线交叉策略"
        sub_kline_type = [Interval.MINUTE]  # 订阅1分钟K线
        
        super().__init__(
            instruments=instruments,
            strategy_name=strategy_name,
            strategy_content=strategy_content,
            sub_kline_type=sub_kline_type
        )
        
        self.logger = get_logger(self.__class__.__name__)
        
        # 明确类型注解
        self.instruments: list[str] = instruments
        
        # 策略参数
        self.fast_period = 5   # 快线周期
        self.slow_period = 20  # 慢线周期
        self.position_size = 1  # 每次交易手数
        
        # 策略状态
        self.bars: dict[str, list[BarData]] = {ins: [] for ins in self.instruments}
        self.fast_ma: dict[str, float] = {ins: 0.0 for ins in self.instruments}
        self.slow_ma: dict[str, float] = {ins: 0.0 for ins in self.instruments}
        self.last_cross_signal: dict[str, str | None] = {ins: None for ins in self.instruments}
        
    def on_init(self) -> None:
        """策略初始化"""
        self.logger.info("=" * 60)
        self.logger.info("双均线交叉策略初始化")
        self.logger.info(f"订阅合约: {self.instruments}")
        self.logger.info(f"快线周期: {self.fast_period}, 慢线周期: {self.slow_period}")
        self.logger.info(f"每次交易手数: {self.position_size}")
        self.logger.info("=" * 60)
        
    def on_close(self) -> None:
        """收盘处理"""
        self.logger.info("=" * 60)
        self.logger.info(f"收盘处理 - 当前持仓: {self.positions}")
        for ins in self.instruments:
            if self.positions[ins] != 0:
                self.logger.info(f"  {ins}: 持仓 {self.positions[ins]} 手")
        self.logger.info("=" * 60)
        
    def on_alarm(self) -> None:
        """闹钟处理"""
        pass
    
    def on_tick(self, tick: TickData) -> None:
        """
        Tick数据处理
        
        注意：由于有 instruments 属性，strategy_worker.py 会自动过滤数据
        此方法只接收订阅合约（SA601）的 tick 数据
        """
        # 双均线策略主要基于K线，tick数据仅用于监控
        # 可以在这里添加tick级别的监控逻辑
        pass
    
    def on_bar(self, bar: BarData) -> None:
        """
        K线数据处理 - 策略核心逻辑
        
        注意：由于有 instruments 属性，strategy_worker.py 会自动过滤数据
        此方法只接收订阅合约（SA601）的 bar 数据
        """
        instrument_id = bar.instrument_id
        
        # 保存K线数据
        self.bars[instrument_id].append(bar)
        
        # 只保留最近的 slow_period + 10 根K线
        max_bars = self.slow_period + 10
        if len(self.bars[instrument_id]) > max_bars:
            self.bars[instrument_id] = self.bars[instrument_id][-max_bars:]
        
        # 需要足够的K线数据才能计算慢线
        if len(self.bars[instrument_id]) < self.slow_period:
            self.logger.info(f"[{instrument_id}] K线数量不足 ({len(self.bars[instrument_id])}/{self.slow_period})，等待更多数据...")
            return
        
        # 计算均线
        self._calculate_ma(instrument_id)
        
        # 检测交叉信号
        self._check_cross_signal(instrument_id, bar)
        
    def _calculate_ma(self, instrument_id: str):
        """计算快慢均线"""
        bars = self.bars[instrument_id]
        
        # 计算快线（最近N根K线的收盘价平均）
        fast_closes = [b.close_price for b in bars[-self.fast_period:]]
        self.fast_ma[instrument_id] = sum(fast_closes) / len(fast_closes)
        
        # 计算慢线
        slow_closes = [b.close_price for b in bars[-self.slow_period:]]
        self.slow_ma[instrument_id] = sum(slow_closes) / len(slow_closes)
        
    def _check_cross_signal(self, instrument_id: str, current_bar: BarData):
        """检测均线交叉信号"""
        # 至少需要两根K线才能检测交叉
        if len(self.bars[instrument_id]) < self.slow_period + 1:
            return
        
        # 获取当前均线值
        current_fast = self.fast_ma[instrument_id]
        current_slow = self.slow_ma[instrument_id]
        
        # 计算前一根K线的均线（使用前一根K线之前的数据）
        prev_bars = self.bars[instrument_id][:-1]
        if len(prev_bars) < self.slow_period:
            return
            
        prev_fast_closes = [b.close_price for b in prev_bars[-self.fast_period:]]
        prev_fast = sum(prev_fast_closes) / len(prev_fast_closes)
        
        prev_slow_closes = [b.close_price for b in prev_bars[-self.slow_period:]]
        prev_slow = sum(prev_slow_closes) / len(prev_slow_closes)
        
        # 检测金叉（快线上穿慢线）
        if prev_fast <= prev_slow and current_fast > current_slow:
            self._on_golden_cross(instrument_id, current_bar)
            
        # 检测死叉（快线下穿慢线）
        elif prev_fast >= prev_slow and current_fast < current_slow:
            self._on_death_cross(instrument_id, current_bar)
    
    def _on_golden_cross(self, instrument_id: str, bar: BarData):
        """金叉信号处理 - 开多仓"""
        current_position = self.positions[instrument_id]
        
        self.logger.info("=" * 60)
        self.logger.info(f"🟢 [{instrument_id}] 金叉信号！")
        self.logger.info(f"   快线: {self.fast_ma[instrument_id]:.2f}, 慢线: {self.slow_ma[instrument_id]:.2f}")
        self.logger.info(f"   当前价格: {bar.close_price:.2f}, 当前持仓: {current_position}")
        
        # 如果有空仓，先平仓
        if current_position < 0:
            self.logger.info(f"   → 平空仓: {abs(current_position)} 手 @ {bar.close_price:.2f}")
            self.positions[instrument_id] = 0
        
        # 开多仓
        if current_position == 0:
            self.logger.info(f"   → 开多仓: {self.position_size} 手 @ {bar.close_price:.2f}")
            self.positions[instrument_id] = self.position_size
            self.last_cross_signal[instrument_id] = "golden"
            
        self.logger.info("=" * 60)
        
        # 这里可以调用实际的下单接口
        # self.send_order(instrument_id, Direction.LONG, self.position_size, bar.close_price)
    
    def _on_death_cross(self, instrument_id: str, bar: BarData):
        """死叉信号处理 - 平多仓"""
        current_position = self.positions[instrument_id]
        
        self.logger.info("=" * 60)
        self.logger.info(f"🔴 [{instrument_id}] 死叉信号！")
        self.logger.info(f"   快线: {self.fast_ma[instrument_id]:.2f}, 慢线: {self.slow_ma[instrument_id]:.2f}")
        self.logger.info(f"   当前价格: {bar.close_price:.2f}, 当前持仓: {current_position}")
        
        # 如果有多仓，先平仓
        if current_position > 0:
            self.logger.info(f"   → 平多仓: {current_position} 手 @ {bar.close_price:.2f}")
            self.positions[instrument_id] = 0
            self.last_cross_signal[instrument_id] = "death"
        
        self.logger.info("=" * 60)
        
        # 这里可以调用实际的下单接口
        # self.send_order(instrument_id, Direction.SHORT, self.position_size, bar.close_price)
    
    def on_trade(self, trade: TradeData) -> None:
        """成交回报处理"""
        instrument_id = trade.instrument_id
        self.logger.info(f"[{instrument_id}] 成交回报: {trade.volume}手 @ {trade.price:.2f}")
    
    def on_order(self, order: OrderData) -> None:
        """订单状态变化处理"""
        instrument_id = order.instrument_id
        self.logger.info(f"[{instrument_id}] 订单状态: {order.order_status}")
    
    # ========== 状态持久化 ==========
    
    def save_state(self) -> dict:
        """保存策略状态"""
        return {
            "positions": self.positions,
            "fast_ma": self.fast_ma,
            "slow_ma": self.slow_ma,
            "last_cross_signal": self.last_cross_signal,
            # 只保存最近的K线数据
            "bars": {
                ins: [
                    {
                        "open": b.open_price,
                        "high": b.high_price,
                        "low": b.low_price,
                        "close": b.close_price,
                        "volume": b.volume,
                        "update_time": str(b.update_time)
                    } 
                    for b in bars[-self.slow_period:]
                ] 
                for ins, bars in self.bars.items()
            }
        }
    
    def load_state(self, state: dict):
        """加载策略状态"""
        if state:
            self.positions = state.get("positions", {ins: 0 for ins in self.instruments})
            self.fast_ma = state.get("fast_ma", {ins: 0.0 for ins in self.instruments})
            self.slow_ma = state.get("slow_ma", {ins: 0.0 for ins in self.instruments})
            self.last_cross_signal = state.get("last_cross_signal", {ins: None for ins in self.instruments})
            
            # 恢复K线数据（简化版本，实际使用中可能需要从BarData重建）
            # bars_data = state.get("bars", {})
            # 注意：这里不完全恢复K线数据，因为需要BarData对象
            
            self.logger.info("双均线策略状态已恢复")
            self.logger.info(f"  持仓: {self.positions}")
            self.logger.info(f"  快线: {self.fast_ma}")
            self.logger.info(f"  慢线: {self.slow_ma}")
            self.logger.info(f"  最后信号: {self.last_cross_signal}")


def get_strategy():
    """策略工厂函数 - 供系统加载使用"""
    return MACrossStrategy()
