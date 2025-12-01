#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : strategy_db.py
@Date       : 2025/11/27
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 策略数据库相关的 Pydantic Schema 模型
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class StrategyCreate(BaseModel):
    """策略创建请求"""
    name: str = Field(..., description="策略名称", min_length=1, max_length=100)
    description: Optional[str] = Field(None, description="策略描述", max_length=1000)
    author: Optional[str] = Field(None, description="策略作者", max_length=100)
    file_path: str = Field(..., description="策略文件路径")
    module_path: str = Field(..., description="策略模块路径")
    class_name: str = Field(default="Strategy", description="策略类名")
    instruments: Optional[List[str]] = Field(None, description="订阅的合约列表")
    parameters: Optional[Dict[str, Any]] = Field(None, description="策略参数配置")
    status: Optional[str] = Field(None, description="策略状态: draft, active, inactive, archived")
    enabled: Optional[bool] = Field(None, description="是否启用")


class StrategyUpdate(BaseModel):
    """策略更新请求"""
    name: Optional[str] = Field(None, description="策略名称")
    description: Optional[str] = Field(None, description="策略描述")
    author: Optional[str] = Field(None, description="策略作者")
    instruments: Optional[List[str]] = Field(None, description="订阅的合约列表")
    parameters: Optional[Dict[str, Any]] = Field(None, description="策略参数配置")
    status: Optional[str] = Field(None, description="策略状态")
    enabled: Optional[bool] = Field(None, description="是否启用")


class StrategyResponse(BaseModel):
    """策略响应"""
    strategy_id: int = Field(..., description="策略ID")
    uuid: str = Field(..., description="策略UUID")
    name: str = Field(..., description="策略名称")
    description: Optional[str] = Field(None, description="策略描述")
    author: Optional[str] = Field(None, description="策略作者")
    file_path: str = Field(..., description="策略文件路径")
    module_path: str = Field(..., description="策略模块路径")
    class_name: str = Field(..., description="策略类名")
    instruments: List[str] = Field(default_factory=list, description="订阅的合约列表")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="策略参数配置")
    status: str = Field(..., description="策略状态")
    enabled: bool = Field(..., description="是否启用")
    admin_id: int = Field(..., description="创建者管理员ID")
    admin_username: Optional[str] = Field(None, description="创建者管理员用户名")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="最后更新时间")

    class Config:
        from_attributes = True


class StrategyListResponse(BaseModel):
    """策略列表响应"""
    total: int = Field(..., description="总数")
    skip: int = Field(..., description="跳过的记录数")
    limit: int = Field(..., description="返回的最大记录数")
    strategies: List[StrategyResponse] = Field(..., description="策略列表")


class StrategyStatusUpdate(BaseModel):
    """策略状态更新请求"""
    status: str = Field(..., description="策略状态: draft, active, inactive, archived")


class StrategyEnableToggle(BaseModel):
    """策略启用/禁用请求"""
    enabled: bool = Field(..., description="是否启用")
