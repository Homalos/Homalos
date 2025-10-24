#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : trading_core.py
@Date       : 2025/10/23
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 交易核心相关的数据模型
"""
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


# ========== 状态枚举 ==========

class TradingCoreStatus(str, Enum):
    """交易核心状态"""
    STOPPED = "stopped"              # 未启动
    INITIALIZING = "initializing"    # 初始化中
    CONNECTING = "connecting"        # 连接网关中
    RUNNING = "running"              # 运行中
    STOPPING = "stopping"            # 停止中
    ERROR = "error"                  # 错误状态


class ModuleStatus(str, Enum):
    """模块状态"""
    STOPPED = "stopped"
    RUNNING = "running"
    ERROR = "error"


# ========== 请求模型 ==========

class StartCoreRequest(BaseModel):
    """启动核心请求"""
    config: Optional[Dict[str, Any]] = Field(default=None, description="核心配置（可选，使用默认配置）")
    auto_connect_gateway: bool = Field(default=False, description="是否自动连接网关")


class StopCoreRequest(BaseModel):
    """停止核心请求"""
    force: bool = Field(default=False, description="是否强制停止")
    timeout: int = Field(default=30, description="等待超时时间（秒）")


class ConnectGatewayRequest(BaseModel):
    """连接网关请求"""
    broker_config: Optional[Dict[str, Any]] = Field(default=None, description="经纪商配置（可选）")


# ========== 响应模型 ==========

class BaseResponse(BaseModel):
    """基础响应"""
    success: bool
    message: str


class GatewayStatus(BaseModel):
    """网关状态"""
    md_login: bool = Field(default=False, description="行情网关登录状态")
    td_login: bool = Field(default=False, description="交易网关登录状态")
    td_confirm: bool = Field(default=False, description="结算单确认状态")
    instruments_loaded: bool = Field(default=False, description="合约加载状态")


class ModuleStatusInfo(BaseModel):
    """模块状态信息"""
    name: str
    status: ModuleStatus
    description: Optional[str] = None


class CoreStatusResponse(BaseModel):
    """核心状态响应"""
    status: TradingCoreStatus
    message: Optional[str] = None
    gateway: GatewayStatus
    modules: Dict[str, ModuleStatus]
    running_time: Optional[str] = None
    startup_time: Optional[str] = None
    
    # 统计信息
    total_strategies: int = 0
    total_instruments: int = 0
    total_orders: int = 0
    position_count: int = 0
    active_signals: int = 0
    
    # 内部状态（从status文件读取）
    internal_status: Optional[Dict[str, Any]] = None


class StartCoreResponse(BaseResponse):
    """启动核心响应"""
    status: Optional[TradingCoreStatus] = None
    startup_time: Optional[float] = None  # 启动耗时（秒）


class StopCoreResponse(BaseResponse):
    """停止核心响应"""
    shutdown_time: Optional[float] = None  # 关闭耗时（秒）
    stopped_strategies_count: int = 0  # 停止的策略数量


class ConnectGatewayResponse(BaseResponse):
    """连接网关响应"""
    gateway: Optional[GatewayStatus] = None
    connection_time: Optional[float] = None  # 连接耗时（秒）


class ModulesResponse(BaseModel):
    """模块列表响应"""
    success: bool
    modules: list[ModuleStatusInfo]

