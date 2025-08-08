#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos_v2
@FileName   : account_manager
@Date       : 2025/7/23 00:23
@Author     : Donny
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 账户管理器
"""
import asyncio
import time
from collections import defaultdict
from typing import Dict, Any

from src.config.config_manager import ConfigManager
from src.core.event import Event, EventType
from src.core.event_bus import EventBus
from src.core.logger import get_logger
from src.core.object import TradeData, PositionData, AccountData

logger = get_logger("AccountManager")


class AccountManager:

    def __init__(self, event_bus: EventBus, config: ConfigManager):
        self.event_bus = event_bus
        self.config = config

        self.accounts: Dict[str, AccountData] = {}
        self.positions: Dict[str, PositionData] = {}
        self.strategy_pnl: Dict[str, float] = defaultdict(float)

        # 注册事件处理器
        self.event_bus.subscribe(EventType.ACCOUNT_UPDATED, self._handle_account_update)
        self.event_bus.subscribe(EventType.POSITION_UPDATED, self._handle_position_update)
        self.event_bus.subscribe(EventType.ORDER_FILLED, self._handle_trade_update)

        # 添加定期查询任务
        self._last_query_time = 0
        self._query_interval: float = 30.0  # 30秒查询一次

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
                    self.event_bus.publish(Event(EventType.GATEWAY_QUERY_ACCOUNT, {}))
                    self.event_bus.publish(Event(EventType.GATEWAY_QUERY_POSITION, {}))
                    self._last_query_time = current_time

            except Exception as e:
                logger.error(f"定期查询任务异常: {e}")
                await asyncio.sleep(5)  # 异常后等待5秒再继续

    def _handle_account_update(self, event: Event):
        """处理账户更新"""
        account_data = event.data
        if isinstance(account_data, AccountData):
            self.accounts[account_data.account_id] = account_data

            logger.info(
                f"账户更新: {account_data.account_id} 余额={account_data.balance} 可用={account_data.available}")

    def _handle_position_update(self, event: Event):
        """处理持仓更新"""
        position_data = event.data
        if isinstance(position_data, PositionData):
            position_key = f"{position_data.symbol}.{position_data.direction.value}"
            self.positions[position_key] = position_data

            logger.info(f"持仓更新: {position_key} 数量={position_data.volume} 均价={position_data.price}")

    @staticmethod
    def _handle_trade_update(event: Event):
        """处理成交更新，计算策略盈亏"""
        trade_data = event.data
        if isinstance(trade_data, TradeData):
            # 简化盈亏计算逻辑
            # 实际应用中需要根据具体的持仓和价格变化计算
            logger.info(
                f"成交更新: {trade_data.symbol} {trade_data.direction.value if trade_data.direction else 'UNKNOWN'} {trade_data.volume}@{trade_data.price}")

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
