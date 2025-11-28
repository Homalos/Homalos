#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : strategy_position.py
@Date       : 2025/11/27
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 策略持仓相关的 Pydantic Schema 模型
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime


class StrategyPositionResponse(BaseModel):
    """策略持仓响应"""
    position_id: int = Field(..., description="持仓ID")
    strategy_id: int = Field(..., description="策略ID")
    symbol: str = Field(..., description="合约代码")
    exchange: Optional[str] = Field(None, description="交易所代码")
    direction: str = Field(..., description="持仓方向: LONG/SHORT")
    volume: int = Field(..., description="持仓数量")
    frozen: int = Field(default=0, description="冻结数量")
    avg_price: float = Field(..., description="平均开仓价格")
    last_price: Optional[float] = Field(None, description="最新价格")
    position_pnl: float = Field(default=0.0, description="持仓盈亏")
    close_pnl: float = Field(default=0.0, description="平仓盈亏")
    is_closed: bool = Field(..., description="是否已平仓")
    open_time: datetime = Field(..., description="开仓时间")
    close_time: Optional[datetime] = Field(None, description="平仓时间")
    updated_at: datetime = Field(..., description="最后更新时间")

    @field_validator('avg_price', mode='after')
    @classmethod
    def round_avg_price(cls, v):
        """开仓均价四舍五入保留2位小数"""
        if v is not None:
            return round(v, 2)
        return v

    @field_validator('last_price', mode='after')
    @classmethod
    def round_last_price(cls, v):
        """最新价四舍五入保留2位小数"""
        if v is not None:
            return round(v, 2)
        return v

    class Config:
        from_attributes = True


class StrategyPositionListResponse(BaseModel):
    """策略持仓列表响应"""
    total: int = Field(..., description="总数")
    positions: List[StrategyPositionResponse] = Field(..., description="持仓列表")


class StrategyPositionUpdate(BaseModel):
    """策略持仓更新请求"""
    volume: Optional[int] = Field(None, description="持仓数量")
    frozen: Optional[int] = Field(None, description="冻结数量")
    avg_price: Optional[float] = Field(None, description="平均开仓价格")
    last_price: Optional[float] = Field(None, description="最新价格")
    position_pnl: Optional[float] = Field(None, description="持仓盈亏")
    close_pnl: Optional[float] = Field(None, description="平仓盈亏")


class StrategyPositionCreate(BaseModel):
    """策略持仓创建请求"""
    strategy_id: int = Field(..., description="策略ID")
    symbol: str = Field(..., description="合约代码")
    exchange: Optional[str] = Field(None, description="交易所代码")
    direction: str = Field(..., description="持仓方向: LONG/SHORT")
    volume: int = Field(..., description="持仓数量")
    avg_price: float = Field(..., description="平均开仓价格")


class StrategyTradeResponse(BaseModel):
    """策略成交记录响应"""
    trade_id: int = Field(..., description="成交ID")
    strategy_id: int = Field(..., description="策略ID")
    symbol: str = Field(..., description="合约代码")
    exchange: Optional[str] = Field(None, description="交易所代码")
    direction: str = Field(..., description="成交方向: LONG/SHORT")
    offset_type: str = Field(..., description="开平类型: OPEN/CLOSE")
    trade_price: float = Field(..., description="成交价格")
    trade_volume: int = Field(..., description="成交数量")
    commission: float = Field(default=0.0, description="手续费")
    order_id: Optional[str] = Field(None, description="订单编号")
    pnl: float = Field(default=0.0, description="成交盈亏")
    trade_time: datetime = Field(..., description="成交时间")

    @field_validator('trade_price', mode='after')
    @classmethod
    def round_trade_price(cls, v):
        """成交价格四舍五入保留2位小数"""
        if v is not None:
            return round(v, 2)
        return v

    @field_validator('commission', mode='after')
    @classmethod
    def round_commission(cls, v):
        """手续费四舍五入保留2位小数"""
        if v is not None:
            return round(v, 2)
        return v

    @field_validator('pnl', mode='after')
    @classmethod
    def round_pnl(cls, v):
        """盈亏四舍五入保留2位小数"""
        if v is not None:
            return round(v, 2)
        return v

    class Config:
        from_attributes = True


class StrategyTradeListResponse(BaseModel):
    """策略成交记录列表响应"""
    total: int = Field(..., description="总数")
    trades: List[StrategyTradeResponse] = Field(..., description="成交记录列表")
