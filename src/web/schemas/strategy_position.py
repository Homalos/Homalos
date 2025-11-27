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
from pydantic import BaseModel, Field
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
