#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : strategy_trade.py
@Date       : 2025/11/28
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 策略成交记录数据模型
"""
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship

from .base import Base


class StrategyTrade(Base):
    """
    策略成交记录表
    
    记录策略的每笔成交明细，包括开仓和平仓
    """
    __tablename__ = "strategy_trades"

    # 主键
    trade_id = Column(
        Integer,
        primary_key=True,
        index=True,
        autoincrement=True,
        comment="成交唯一标识，主键"
    )

    # 策略关联
    strategy_id = Column(
        Integer,
        ForeignKey('strategies.strategy_id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        comment="策略ID，外键关联strategies表"
    )

    # 合约信息
    symbol = Column(
        String(50),
        nullable=False,
        index=True,
        comment="合约代码"
    )

    exchange = Column(
        String(20),
        nullable=True,
        comment="交易所代码"
    )

    # 成交方向
    direction = Column(
        String(10),
        nullable=False,
        comment="成交方向: LONG(多), SHORT(空)"
    )

    # 开平类型
    offset_type = Column(
        String(10),
        nullable=False,
        comment="开平类型: OPEN(开仓), CLOSE(平仓)"
    )

    # 成交价格
    trade_price = Column(
        Float,
        nullable=False,
        comment="成交价格"
    )

    # 成交数量
    trade_volume = Column(
        Integer,
        nullable=False,
        comment="成交数量"
    )

    # 手续费
    commission = Column(
        Float,
        nullable=False,
        default=0.0,
        comment="手续费"
    )

    # 订单编号
    order_id = Column(
        String(100),
        nullable=True,
        index=True,
        comment="订单编号"
    )

    # 盈亏
    pnl = Column(
        Float,
        nullable=False,
        default=0.0,
        comment="成交盈亏"
    )

    # 成交时间
    trade_time = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True,
        comment="成交时间"
    )

    # 关联关系
    strategy = relationship(
        "Strategy",
        backref="trades"
    )

    # 索引定义
    __table_args__ = (
        Index('idx_strategy_trades_strategy_id', 'strategy_id'),
        Index('idx_strategy_trades_symbol', 'symbol'),
        Index('idx_strategy_trades_order_id', 'order_id'),
        Index('idx_strategy_trades_trade_time', 'trade_time'),
        Index('idx_strategy_trades_strategy_time', 'strategy_id', 'trade_time'),  # 复合索引
        {'comment': '策略成交记录表 - 记录策略的每笔成交明细'}
    )

    def __repr__(self):
        return f"<StrategyTrade(trade_id={self.trade_id}, strategy_id={self.strategy_id}, symbol={self.symbol}, direction={self.direction}, offset_type={self.offset_type}, trade_volume={self.trade_volume})>"

    def to_dict(self):
        """转换为字典"""
        return {
            "trade_id": self.trade_id,
            "strategy_id": self.strategy_id,
            "symbol": self.symbol,
            "exchange": self.exchange,
            "direction": self.direction,
            "offset_type": self.offset_type,
            "trade_price": round(self.trade_price, 2) if self.trade_price else 0.0,
            "trade_volume": self.trade_volume,
            "commission": round(self.commission, 2) if self.commission else 0.0,
            "order_id": self.order_id,
            "pnl": round(self.pnl, 2) if self.pnl else 0.0,
            "trade_time": self.trade_time.isoformat() if self.trade_time else None
        }
