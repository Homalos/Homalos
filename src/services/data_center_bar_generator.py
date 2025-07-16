#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据中心K线合成器
负责将tick数据合成为不同周期的K线数据，支持多合约多周期
"""

from datetime import datetime, timedelta
from typing import Dict, Optional, Callable, List
from collections import defaultdict

from src.core.logger import get_logger
from src.config.constant import Interval

logger = get_logger(__name__)
from src.core.object import TickData, BarData


class DataCenterBarGenerator:
    """
    数据中心K线合成器
    负责多合约多周期K线合成
    """
    
    def __init__(self, intervals: List[int] = None, on_bar: Optional[Callable] = None):
        """
        初始化数据中心K线合成器
        
        Args:
            intervals: K线周期列表（分钟），默认[1, 5, 15, 30, 60]
            on_bar: K线生成回调函数
        """
        self.intervals = intervals or [1, 5, 15, 30, 60]
        self.on_bar = on_bar
        
        # 多合约多周期的当前K线数据
        # 结构: {symbol: {interval: BarData}}
        self.current_bars: Dict[str, Dict[int, BarData]] = defaultdict(lambda: defaultdict(lambda: None))
        
        # 最后一个tick数据
        # 结构: {symbol: TickData}
        self.last_ticks: Dict[str, TickData] = {}
        
        logger.info(f"数据中心K线合成器初始化完成，支持周期: {self.intervals}分钟")

    def on_tick(self, tick: TickData) -> None:
        """
        处理tick数据，生成多周期K线
        
        Args:
            tick: tick数据
        """
        try:
            symbol = tick.symbol
            
            # 为每个周期生成K线
            for interval in self.intervals:
                self._process_tick_for_interval(tick, symbol, interval)
            
            # 更新最后tick数据
            self.last_ticks[symbol] = tick
            
        except Exception as e:
            logger.error(f"处理tick数据失败: {e}", exc_info=True)
    
    def _process_tick_for_interval(self, tick: TickData, symbol: str, interval: int) -> None:
        """
        为指定周期处理tick数据
        
        Args:
            tick: tick数据
            symbol: 合约代码
            interval: K线周期（分钟）
        """
        # 计算当前tick所属的K线时间
        bar_time = self._get_bar_time(tick.datetime, interval)
        
        # 获取当前K线
        current_bar = self.current_bars[symbol][interval]
        
        # 如果是新的K线周期，输出上一根K线
        if current_bar and current_bar.datetime != bar_time:
            if self.on_bar:
                self.on_bar(current_bar)
            current_bar = None
        
        # 创建或更新当前K线
        if not current_bar:
            current_bar = self._create_new_bar(tick, bar_time, interval)
            self.current_bars[symbol][interval] = current_bar
        else:
            self._update_current_bar(current_bar, tick)
        
        self.current_bars[symbol][interval] = current_bar
    
    def _get_bar_time(self, tick_time: datetime, interval: int) -> datetime:
        """
        计算tick时间对应的K线时间
        
        Args:
            tick_time: tick时间
            interval: K线周期（分钟）
            
        Returns:
            K线时间
        """
        # 计算分钟数
        minutes = tick_time.minute
        # 计算K线开始分钟
        bar_minute = (minutes // interval) * interval
        
        # 返回K线时间（秒和微秒设为0）
        return tick_time.replace(minute=bar_minute, second=0, microsecond=0)
    
    def _create_new_bar(self, tick: TickData, bar_time: datetime, interval: int) -> BarData:
        """
        创建新的K线数据
        
        Args:
            tick: tick数据
            bar_time: K线时间
            interval: K线周期（分钟）
            
        Returns:
            新的K线数据
        """
        return BarData(
            symbol=tick.symbol,
            exchange=tick.exchange,
            datetime=bar_time,
            interval=Interval.MINUTE,  # 使用正确的 Interval 枚举
            volume=tick.volume,
            turnover=tick.turnover,
            open_interest=tick.open_interest,
            open_price=tick.last_price,
            high_price=tick.last_price,
            low_price=tick.last_price,
            close_price=tick.last_price,
            gateway_name="BarData"
        )
    
    def _update_current_bar(self, current_bar: BarData, tick: TickData) -> None:
        """
        更新当前K线数据
        
        Args:
            current_bar: 当前K线数据
            tick: tick数据
        """
        # 更新最高价
        if tick.last_price > current_bar.high_price:
            current_bar.high_price = tick.last_price
        
        # 更新最低价
        if tick.last_price < current_bar.low_price:
            current_bar.low_price = tick.last_price
        
        # 更新收盘价
        current_bar.close_price = tick.last_price
        
        # 更新成交量（累计）
        last_tick = self.last_ticks.get(tick.symbol)
        if last_tick:
            volume_diff = tick.volume - last_tick.volume
            if volume_diff > 0:
                current_bar.volume += volume_diff
        
        # 更新成交额（累计）
        if last_tick:
            turnover_diff = tick.turnover - last_tick.turnover
            if turnover_diff > 0:
                current_bar.turnover += turnover_diff
        
        # 更新持仓量
        current_bar.open_interest = tick.open_interest
    
    def get_current_bars(self, symbol: str = None) -> Dict:
        """
        获取当前K线数据
        
        Args:
            symbol: 合约代码，如果为None则返回所有合约
            
        Returns:
            当前K线数据字典
        """
        if symbol:
            return self.current_bars.get(symbol, {})
        return dict(self.current_bars)
    
    def force_generate_bars(self, symbol: str = None) -> List[BarData]:
        """
        强制生成当前K线（用于收盘时）
        
        Args:
            symbol: 合约代码，如果为None则生成所有合约的K线
            
        Returns:
            生成的K线数据列表
        """
        generated_bars = []
        
        if symbol:
            # 生成指定合约的K线
            symbol_bars = self.current_bars.get(symbol, {})
            for interval, bar in symbol_bars.items():
                if bar and self.on_bar:
                    self.on_bar(bar)
                    generated_bars.append(bar)
            # 清空当前K线
            if symbol in self.current_bars:
                self.current_bars[symbol].clear()
        else:
            # 生成所有合约的K线
            for symbol, symbol_bars in self.current_bars.items():
                for interval, bar in symbol_bars.items():
                    if bar and self.on_bar:
                        self.on_bar(bar)
                        generated_bars.append(bar)
            # 清空所有当前K线
            self.current_bars.clear()
        
        return generated_bars
    
    def get_supported_intervals(self) -> List[int]:
        """
        获取支持的K线周期
        
        Returns:
            支持的K线周期列表
        """
        return self.intervals.copy()