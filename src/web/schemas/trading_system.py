#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : trading_system.py
@Date       : 2025/10/23
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 交易系统相关的数据模型
"""
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


# ========== 请求模型 ==========

class StartRequest(BaseModel):
    """启动请求"""
    pass


class StopRequest(BaseModel):
    """停止请求"""
    force: bool = Field(default=False, description="是否强制停止")
    timeout: int = Field(default=30, description="等待超时时间（秒）")


# ========== 响应模型 ==========

class BaseResponse(BaseModel):
    """基础响应"""
    success: bool
    message: str


class StartResponse(BaseResponse):
    """启动响应"""
    pid: Optional[int] = None


class StopResponse(BaseResponse):
    """停止响应"""
    pass


class StatusResponse(BaseModel):
    """状态响应"""
    running: bool
    message: Optional[str] = None
    pid: Optional[int] = None
    status: Optional[str] = None
    cpu_percent: Optional[float] = None
    memory_mb: Optional[float] = None
    memory_percent: Optional[float] = None
    create_time: Optional[str] = None
    num_threads: Optional[int] = None
    internal_status: Optional[Dict[str, Any]] = None


class LogsResponse(BaseModel):
    """日志响应"""
    success: bool
    message: Optional[str] = None
    logs: Optional[List[str]] = None
    total_lines: Optional[int] = None
    log_file: Optional[str] = None

