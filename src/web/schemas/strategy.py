#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : strategy.py
@Date       : 2025/10/16
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 策略相关的 Pydantic Schema 模型
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any


class StrategyInfo(BaseModel):
    """策略基本信息"""
    uuid: Optional[str] = Field(None, description="策略UUID")
    file: str = Field(..., description="策略文件路径")
    module: str = Field(..., description="策略模块路径")
    class_name: str = Field(default="Strategy", alias="class", description="策略类名")
    name: Optional[str] = Field(None, description="策略名称")
    description: Optional[str] = Field(None, description="策略描述")
    author: Optional[str] = Field(None, description="策略作者")
    instruments: list[str] = Field(default_factory=list, description="订阅的合约列表")
    enabled: bool = Field(..., description="是否启用")
    params: Dict[str, Any] = Field(default_factory=dict, description="策略参数")
    admin_username: Optional[str] = Field(None, description="创建者管理员用户名")
    
    class Config:
        populate_by_name = True


class StrategyStatus(BaseModel):
    """策略运行状态"""
    pid: Optional[int] = Field(None, description="进程ID")
    alive: bool = Field(..., description="是否存活")
    module: str = Field(..., description="模块路径")
    class_name: str = Field(..., alias="class", description="类名")
    strategy_name: str = Field(..., description="策略显示名称")
    start_time: Optional[float] = Field(None, description="启动时间戳")
    pnl: float = Field(..., description="浮动盈亏")
    trade_count: int = Field(..., description="交易次数")
    
    class Config:
        populate_by_name = True


class StrategyListResponse(BaseModel):
    """策略列表响应"""
    strategies: Dict[str, StrategyInfo] = Field(..., description="策略配置字典")


class StrategyStatusResponse(BaseModel):
    """策略状态响应"""
    running: Dict[str, StrategyStatus] = Field(..., description="运行中的策略状态")


class OperationResponse(BaseModel):
    """操作响应"""
    status: str = Field(..., description="操作状态")
    sid: str = Field(..., description="策略ID")
    message: Optional[str] = Field(None, description="附加消息")


class WebSocketMessage(BaseModel):
    """WebSocket消息"""
    type: str = Field(..., description="消息类型: log/error/status/order/trade")
    sid: str = Field(..., description="策略ID")
    payload: Any = Field(..., description="消息内容")
    trace: Optional[str] = Field(None, description="错误堆栈（仅error类型）")

