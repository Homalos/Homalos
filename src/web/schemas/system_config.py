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
from typing import Optional, List, Any


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
    user_guide: str = Field(..., description="用户手册")
    
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
                "timezone": "Asia/Shanghai",
                "user_guide": "https://homalos.github.io/guide/quick_start"
            }
        }


# ==================== 通知配置相关模型 ====================

class DingtalkConfig(BaseModel):
    """钉钉配置模型"""
    enabled: bool = Field(False, description="是否启用钉钉通知")
    name: str = Field("", description="钉钉机器人名称")
    id: str = Field("", description="钉钉机器人ID")
    webhookUrl: str = Field("", description="钉钉Webhook地址")


class WecomConfig(BaseModel):
    """企业微信配置模型"""
    enabled: bool = Field(False, description="是否启用企业微信通知")
    name: str = Field("", description="企业微信机器人名称")
    corpId: str = Field("", description="企业微信ID")
    agentId: Any = Field("", description="应用ID")
    appSecret: str = Field("", description="应用密钥")


class EmailConfig(BaseModel):
    """邮件配置模型"""
    enabled: bool = Field(False, description="是否启用邮件通知")
    address: str = Field("", description="邮箱地址")
    smtpServer: str = Field("", description="SMTP服务器")


class NotificationConfigResponse(BaseModel):
    """通知配置响应模型"""
    dingtalk: DingtalkConfig = Field(..., description="钉钉配置")
    wecom: WecomConfig = Field(..., description="企业微信配置")
    email: EmailConfig = Field(..., description="邮件配置")
    
    class Config:
        json_schema_extra = {
            "example": {
                "dingtalk": {
                    "enabled": True,
                    "name": "Homalos量化助手",
                    "id": "dingding",
                    "webhookUrl": "https://dingding.com"
                },
                "wecom": {
                    "enabled": True,
                    "name": "Homalos量化助手",
                    "corpId": "ww24d2eea685faf0cc",
                    "agentId": 1000002,
                    "appSecret": "5vF10PfLULzcrw2LlWEbS6iE3Hxujeu4fSCxKoqN-RY"
                },
                "email": {
                    "enabled": False,
                    "address": "",
                    "smtpServer": ""
                }
            }
        }


class NotificationConfigUpdate(BaseModel):
    """通知配置更新模型"""
    dingtalk: Optional[DingtalkConfig] = Field(None, description="钉钉配置")
    wecom: Optional[WecomConfig] = Field(None, description="企业微信配置")
    email: Optional[EmailConfig] = Field(None, description="邮件配置")


# ==================== 日志配置相关模型 ====================

class LoggingConfigResponse(BaseModel):
    """日志配置响应模型"""
    level: str = Field(..., description="日志级别")
    rotation: str = Field(..., description="单个日志文件大小上限")
    retention: str = Field(..., description="日志保留时间")
    compression: str = Field(..., description="日志文件压缩格式")
    
    class Config:
        json_schema_extra = {
            "example": {
                "level": "INFO",
                "rotation": "50 MB",
                "retention": "14 days",
                "compression": "zip"
            }
        }


class LoggingConfigUpdate(BaseModel):
    """日志配置更新模型"""
    level: Optional[str] = Field(None, description="日志级别")
    rotation: Optional[str] = Field(None, description="单个日志文件大小上限")
    retention: Optional[str] = Field(None, description="日志保留时间")
    compression: Optional[str] = Field(None, description="日志文件压缩格式")

