#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : system_config.py
@Date       : 2025/10/12
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 系统配置相关Schema
"""
from pydantic import BaseModel, Field
from typing import Optional


class SystemConfigResponse(BaseModel):
    """系统配置响应模型"""
    dev_mode: bool = Field(..., description="开发模式")
    dev_trading_hours_check: bool = Field(..., description="交易时间检查")
    
    class Config:
        json_schema_extra = {
            "example": {
                "dev_mode": True,
                "dev_trading_hours_check": False
            }
        }


class SystemConfigUpdate(BaseModel):
    """系统配置更新模型"""
    dev_mode: Optional[bool] = Field(None, description="开发模式")
    dev_trading_hours_check: Optional[bool] = Field(None, description="交易时间检查")
    
    class Config:
        json_schema_extra = {
            "example": {
                "dev_mode": True,
                "dev_trading_hours_check": False
            }
        }

