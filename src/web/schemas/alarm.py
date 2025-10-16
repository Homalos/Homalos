#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : alarm.py
@Date       : 2025/10/16 18:30
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 告警相关数据模型
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class AlarmRecord(BaseModel):
    """告警记录"""
    id: int
    alarm_id: str
    alarm_type: str
    severity: str
    source: str
    target: Optional[str] = None
    message: str
    details: Optional[Dict[str, Any]] = None
    status: str
    created_at: str
    acknowledged_at: Optional[str] = None
    resolved_at: Optional[str] = None


class AlarmListResponse(BaseModel):
    """告警列表响应"""
    total: int
    page: int
    page_size: int
    items: List[AlarmRecord]


class AlarmStatsResponse(BaseModel):
    """告警统计响应"""
    status_stats: Dict[str, int]
    severity_stats: Dict[str, int]
    type_stats: Dict[str, int]
    today_count: int
    active_count: int


class AlarmConfigResponse(BaseModel):
    """告警配置响应"""
    cpu_threshold: int = Field(description="CPU告警阈值(%)")
    memory_threshold: int = Field(description="内存告警阈值(%)")
    retention_days: int = Field(description="历史保留天数")
    email_enabled: bool = Field(description="是否启用邮件通知")


class AlarmConfigUpdate(BaseModel):
    """告警配置更新"""
    cpu_threshold: Optional[int] = Field(None, ge=1, le=100, description="CPU告警阈值(%)")
    memory_threshold: Optional[int] = Field(None, ge=1, le=100, description="内存告警阈值(%)")
    retention_days: Optional[int] = Field(None, ge=1, le=365, description="历史保留天数")
    email_enabled: Optional[bool] = Field(None, description="是否启用邮件通知")


class TestAlarmRequest(BaseModel):
    """测试告警请求"""
    alarm_type: str = Field(default="test", description="告警类型")
    severity: str = Field(default="info", description="严重程度")
    message: str = Field(default="这是一条测试告警", description="告警消息")


class OperationResponse(BaseModel):
    """操作响应"""
    status: str
    message: str

