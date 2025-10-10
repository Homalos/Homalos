#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : datacenter.py
@Date       : 2025/10/10
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 数据中心相关的数据模型
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


class ConfigUpdateRequest(BaseModel):
    """配置更新请求"""
    config: Dict[str, Any] = Field(..., description="配置项")


class LogQueryRequest(BaseModel):
    """日志查询请求"""
    lines: int = Field(default=100, description="返回最后N行")
    level: str = Field(default="all", description="日志级别: all/INFO/WARNING/ERROR")


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


class ConfigResponse(BaseModel):
    """配置响应"""
    success: bool
    message: Optional[str] = None
    config: Optional[Dict[str, Any]] = None


class ConfigUpdateResponse(BaseResponse):
    """配置更新响应"""
    backup: Optional[str] = None

