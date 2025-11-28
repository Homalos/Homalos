#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : strategy_position.py
@Date       : 2025/11/27
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 策略持仓数据模型
"""
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship

from .base import Base


class StrategyPosition(Base):
    """
    策略持仓表
    
    记录策略的持仓信息，包括当前持仓和历史持仓
    通过 is_closed 字段区分当前持仓和已平仓持仓
    """
    __tablename__ = "strategy_positions"

    # 主键
    position_id = Column(
        Integer,
        primary_key=True,
        index=True,
        autoincrement=True,
        comment="持仓唯一标识，主键"
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

    # 持仓方向
    direction = Column(
        String(10),
        nullable=False,
        index=True,
        comment="持仓方向: LONG(多头), SHORT(空头)"
    )

    # 持仓数量
    volume = Column(
        Integer,
        nullable=False,
        default=0,
        comment="持仓数量"
    )

    frozen = Column(
        Integer,
        nullable=False,
        default=0,
        comment="冻结数量"
    )

    # 价格信息
    avg_price = Column(
        Float,
        nullable=False,
        default=0.0,
        comment="平均开仓价格"
    )

    last_price = Column(
        Float,
        nullable=True,
        comment="最新价格"
    )

    # 盈亏信息
    position_pnl = Column(
        Float,
        nullable=False,
        default=0.0,
        comment="持仓盈亏"
    )

    close_pnl = Column(
        Float,
        nullable=False,
        default=0.0,
        comment="平仓盈亏"
    )

    # 状态
    is_closed = Column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
        comment="是否已平仓: False-持仓中, True-已平仓"
    )

    # 时间戳
    open_time = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        comment="开仓时间"
    )

    close_time = Column(
        DateTime,
        nullable=True,
        comment="平仓时间"
    )

    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        comment="最后更新时间"
    )

    # 关联关系
    strategy = relationship(
        "Strategy",
        backref="positions"
    )

    # 索引定义
    __table_args__ = (
        Index('idx_strategy_positions_strategy_id', 'strategy_id'),
        Index('idx_strategy_positions_symbol', 'symbol'),
        Index('idx_strategy_positions_is_closed', 'is_closed'),
        Index('idx_strategy_positions_strategy_symbol', 'strategy_id', 'symbol'),  # 复合索引
        Index('idx_strategy_positions_strategy_closed', 'strategy_id', 'is_closed'),  # 复合索引
        {'comment': '策略持仓表 - 记录策略的持仓信息'}
    )

    def __repr__(self):
        return f"<StrategyPosition(position_id={self.position_id}, strategy_id={self.strategy_id}, symbol={self.symbol}, direction={self.direction}, volume={self.volume})>"

    def to_dict(self):
        """转换为字典"""
        return {
            "position_id": self.position_id,
            "strategy_id": self.strategy_id,
            "symbol": self.symbol,
            "exchange": self.exchange,
            "direction": self.direction,
            "volume": self.volume,
            "frozen": self.frozen,
            "avg_price": round(self.avg_price, 2) if self.avg_price else 0.0,
            "last_price": round(self.last_price, 2) if self.last_price else 0.0,
            "position_pnl": self.position_pnl,
            "close_pnl": self.close_pnl,
            "is_closed": self.is_closed,
            "open_time": self.open_time.isoformat() if self.open_time else None,
            "close_time": self.close_time.isoformat() if self.close_time else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
