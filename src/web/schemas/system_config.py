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
from typing import Optional, List


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


class SystemInfoResponse(BaseModel):
    """系统基础信息响应模型"""
    name: str = Field(..., description="系统名称")
    describe: str = Field(..., description="系统描述")
    version: str = Field(..., description="系统版本")
    author: str = Field(..., description="作者")
    copyright: str = Field(..., description="版权信息")
    contact: str = Field(..., description="联系方式")
    technology_stack: List[str] = Field(..., description="技术栈")
    timezone: str = Field(..., description="时区")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Homalos 量化交易系统",
                "describe": "Homalos 是一个专业的期货量化交易系统",
                "version": "0.0.1",
                "author": "Homalos Team",
                "copyright": "Copyright © 2025 Homalos Team. All rights reserved.",
                "contact": "https://github.com/homalos",
                "technology_stack": [
                    "后端：Python 3.10 + FastAPI",
                    "前端：Vue 3 + Element Plus + Vite",
                    "数据库：SQLite"
                ],
                "timezone": "Asia/Shanghai"
            }
        }

