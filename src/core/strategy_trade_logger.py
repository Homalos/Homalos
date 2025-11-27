#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : strategy_trade_logger.py
@Date       : 2025/11/26
@Author     : Lumosylva
@Description: 策略交易日志转发器
将订单流程中的关键日志转发到策略日志系统，便于在策略详情页面查看完整的交易链路
"""
import logging
from typing import Optional, Dict, Any
from src.utils.strategy_logger import get_strategy_logger


class StrategyTradeLogger:
    """策略交易日志转发器 - 单例模式"""
    
    _instance: Optional['StrategyTradeLogger'] = None
    _strategy_loggers: Dict[str, logging.Logger] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True
    
    def get_strategy_logger(self, strategy_id: str) -> logging.Logger:
        """获取或创建策略的日志记录器"""
        if strategy_id not in self._strategy_loggers:
            # 使用策略ID作为logger名称
            self._strategy_loggers[strategy_id] = get_strategy_logger(strategy_id)
        return self._strategy_loggers[strategy_id]
    
    def log_signal_received(self, strategy_id: str, instrument_id: str, 
                           direction: str, offset: str, volume: int, price: float):
        """记录收到交易信号"""
        logger = self.get_strategy_logger(strategy_id)
        logger.info(f"[交易信号] {instrument_id} {direction} {offset} {volume}@{price}")
    
    def log_risk_check_passed(self, strategy_id: str, instrument_id: str, signal_id: str):
        """记录风控检查通过"""
        logger = self.get_strategy_logger(strategy_id)
        logger.info(f"[风控通过] {instrument_id} - SignalID: {signal_id}")
    
    def log_risk_check_failed(self, strategy_id: str, instrument_id: str, 
                             reason: str, signal_id: str):
        """记录风控检查失败"""
        logger = self.get_strategy_logger(strategy_id)
        logger.warning(f"[风控拒绝] {instrument_id} - 原因: {reason} - SignalID: {signal_id}")
    
    def log_order_submitted(self, strategy_id: str, instrument_id: str, 
                           order_id: str, signal_id: str):
        """记录订单已提交"""
        logger = self.get_strategy_logger(strategy_id)
        logger.info(f"[订单提交] {instrument_id} OrderID: {order_id} - SignalID: {signal_id}")
    
    def log_order_status_changed(self, strategy_id: str, instrument_id: str, 
                                order_id: str, old_status: str, new_status: str):
        """记录订单状态变化"""
        logger = self.get_strategy_logger(strategy_id)
        logger.info(f"[订单状态] {instrument_id} OrderID: {order_id} - {old_status} -> {new_status}")
    
    def log_order_traded(self, strategy_id: str, instrument_id: str, 
                        order_id: str, trade_id: str, volume: int, price: float):
        """记录订单成交"""
        logger = self.get_strategy_logger(strategy_id)
        logger.info(f"[订单成交] {instrument_id} OrderID: {order_id} TradeID: {trade_id} "
                   f"成交量: {volume} 成交价: {price}")
    
    def log_order_error(self, strategy_id: str, instrument_id: str, 
                       order_id: str, error_code: int, error_msg: str):
        """记录订单错误"""
        logger = self.get_strategy_logger(strategy_id)
        logger.error(f"[订单错误] {instrument_id} OrderID: {order_id} - "
                    f"错误代码: {error_code}, 错误信息: {error_msg}")


# 全局单例
_strategy_trade_logger = StrategyTradeLogger()


def get_strategy_trade_logger() -> StrategyTradeLogger:
    """获取策略交易日志转发器"""
    return _strategy_trade_logger
