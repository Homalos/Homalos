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


# ============================================================================
# UserBrokerage Schema (新的券商账户模型)
# ============================================================================

class UserBrokerageBase(BaseModel):
    """用户券商账户基础模型"""
    account_name: str = Field(..., description="账户别名", min_length=1, max_length=100)
    broker_code: str = Field(..., description="券商代码", max_length=50)
    broker_name: str = Field(..., description="券商名称", max_length=100)
    account_id: str = Field(..., description="资金账号", max_length=50)
    investor_id: str = Field(..., description="投资者ID", max_length=50)
    broker_id: str = Field(..., description="券商ID", max_length=50)
    account_type: str = Field("production", description="账户类型：simulation/production")
    is_default: bool = Field(False, description="是否为默认账户")


class UserBrokerageCreate(UserBrokerageBase):
    """创建用户券商账户"""
    password_encrypted: str = Field(..., description="加密后的密码")
    auth_code: Optional[str] = Field(None, description="授权码")
    app_id: Optional[str] = Field(None, description="应用ID")


class UserBrokerageUpdate(BaseModel):
    """更新用户券商账户"""
    account_name: Optional[str] = Field(None, description="账户别名")
    password: Optional[str] = Field(None, min_length=1, description="交易密码（明文，后端会加密）")
    auth_code: Optional[str] = Field(None, description="授权码")
    app_id: Optional[str] = Field(None, description="应用ID")
    is_default: Optional[bool] = Field(None, description="是否为默认账户")


class UserBrokerageResponse(UserBrokerageBase):
    """用户券商账户响应"""
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    connection_status: Optional[str] = Field(None, description="连接状态")
    last_connected_at: Optional[datetime] = Field(None, description="最后连接时间")
    last_error: Optional[str] = Field(None, description="最后错误信息")
    
    class Config:
        from_attributes = True


class UserBrokerageListResponse(BaseModel):
    """用户券商账户列表响应"""
    accounts: list[UserBrokerageResponse]
    total: int


class UserBrokerageLogin(BaseModel):
    """券商账户登录请求"""
    account_id: int = Field(..., description="账户ID")
    password: Optional[str] = Field(None, description="密码（如果账户已记住密码可不传）")
    remember: bool = Field(False, description="是否记住密码")


class UserBrokerageLoginResponse(BaseModel):
    """券商账户登录响应"""
    success: bool
    message: str
    account: UserBrokerageResponse
    token: str = Field(..., description="新的JWT token（包含账户信息）")
    decrypted_password: Optional[str] = Field(None, description="解密后的密码（用于构建broker配置）")

