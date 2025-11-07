#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : trading_account.py
@Date       : 2025/10/13
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 资金账户Schema
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class TradingAccountBase(BaseModel):
    """资金账户基础模型"""
    broker_key: str = Field(..., description="券商配置key（如simnow、tts等）")
    broker_id: str = Field(..., description="券商ID")
    account_id: str = Field(..., description="资金账户")
    app_id: Optional[str] = Field(None, description="应用ID")
    auth_code: Optional[str] = Field(None, description="授权码")
    md_node_name: Optional[str] = Field(None, description="行情服务器节点名称")
    td_node_name: Optional[str] = Field(None, description="交易服务器节点名称")
    display_name: Optional[str] = Field(None, description="显示名称")


class TradingAccountCreate(TradingAccountBase):
    """创建资金账户"""
    password: str = Field(..., description="账户密码", min_length=6)
    is_default: bool = Field(False, description="是否设为默认")


class TradingAccountUpdate(BaseModel):
    """更新资金账户"""
    display_name: Optional[str] = Field(None, description="显示名称")
    is_active: Optional[bool] = Field(None, description="是否激活")


class TradingAccountPasswordUpdate(BaseModel):
    """修改密码"""
    old_password: str = Field(..., description="旧密码")
    new_password: str = Field(..., description="新密码", min_length=6)


class TradingAccountLogin(BaseModel):
    """资金账户登录"""
    account_id: Optional[int] = Field(None, description="账户ID（已有账户）")
    broker_key: Optional[str] = Field(None, description="券商配置key（新账户）")
    broker_id: Optional[str] = Field(None, description="券商ID（新账户，可选）")
    account_number: Optional[str] = Field(None, description="资金账号（新账户）")
    password: str = Field("", description="密码（使用已记住密码时可为空）")
    remember: bool = Field(False, description="记住账户")


class TradingAccountResponse(TradingAccountBase):
    """资金账户响应"""
    id: int
    user_id: int
    is_active: bool
    is_default: bool
    remember_password: bool
    last_login: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True


class TradingAccountStatus(BaseModel):
    """资金账户登录状态"""
    is_logged_in: bool = Field(..., description="是否已登录")
    account_id: Optional[int] = Field(None, description="账户ID")
    broker_id: Optional[str] = Field(None, description="券商ID")
    account_number: Optional[str] = Field(None, description="资金账号")
    display_name: Optional[str] = Field(None, description="显示名称")
    has_broker_config: bool = Field(False, description="是否有完整的broker配置（用于连接网关）")


class BrokerInfo(BaseModel):
    """券商信息"""
    broker_key: str = Field(..., description="券商配置key（如simnow、tts等）")
    broker_id: str = Field(..., description="券商ID")
    name: str = Field(..., description="券商名称")
    description: Optional[str] = Field(None, description="描述")


class TradingAccountListResponse(BaseModel):
    """账户列表响应"""
    accounts: list[TradingAccountResponse]
    total: int

