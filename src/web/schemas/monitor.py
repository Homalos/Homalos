#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : monitor.py
@Date       : 2025/10/8
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 系统监控相关数据模型
"""
from pydantic import BaseModel, Field


class SystemStatsResponse(BaseModel):
    """系统监控数据响应"""
    cpu_percent: float = Field(..., description="CPU使用率（%）", ge=0, le=100)
    memory_percent: float = Field(..., description="内存使用率（%）", ge=0, le=100)
    timestamp: str = Field(..., description="数据采集时间（ISO格式）")
    
    class Config:
        json_schema_extra = {
            "example": {
                "cpu_percent": 25.3,
                "memory_percent": 45.7,
                "timestamp": "2025-10-08T21:30:45.123456"
            }
        }

