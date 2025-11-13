#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : brokerage.py
@Date       : 2025/11/13
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 期货券商账户相关的Pydantic模式
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, validator


class BrokerageAccountBase(BaseModel):
    """券商账户基础模式"""
    account_name: str = Field(..., min_length=1, max_length=100, description="账户别名")
    broker_code: str = Field(..., min_length=1, max_length=50, description="券商代码")
    broker_name: str = Field(..., min_length=1, max_length=100, description="券商名称")
    account_id: str = Field(..., min_length=1, max_length=50, description="资金账户")
    investor_id: str = Field(..., min_length=1, max_length=50, description="投资者代码")
    broker_id: str = Field(..., min_length=1, max_length=50, description="经纪公司代码")
    user_product_info: Optional[str] = Field(None, max_length=200, description="用户端产品信息")
    account_type: str = Field(default="production", description="账户类型：simulation/production")
    environment: str = Field(default="prod", description="运行环境：dev/test/prod")
    daily_order_limit: int = Field(default=1000, ge=1, description="每日订单限制")
    is_default: bool = Field(default=False, description="是否为默认账户")


class BrokerageAccountCreate(BrokerageAccountBase):
    """券商账户创建模式"""
    password: str = Field(..., min_length=1, description="交易密码")
    auth_code: Optional[str] = Field(None, description="认证码")
    app_id: Optional[str] = Field(None, description="应用标识")
    
    @validator('account_type')
    def validate_account_type(cls, v):
        if v not in ['simulation', 'production']:
            raise ValueError('账户类型必须是 simulation 或 production')
        return v
    
    @validator('environment')
    def validate_environment(cls, v):
        if v not in ['dev', 'test', 'prod']:
            raise ValueError('运行环境必须是 dev、test 或 prod')
        return v


class BrokerageAccountUpdate(BaseModel):
    """券商账户更新模式"""
    account_name: Optional[str] = Field(None, min_length=1, max_length=100, description="账户别名")
    password: Optional[str] = Field(None, min_length=1, description="交易密码")
    auth_code: Optional[str] = Field(None, description="认证码")
    app_id: Optional[str] = Field(None, description="应用标识")
    user_product_info: Optional[str] = Field(None, max_length=200, description="用户端产品信息")
    daily_order_limit: Optional[int] = Field(None, ge=1, description="每日订单限制")
    is_default: Optional[bool] = Field(None, description="是否为默认账户")
    status: Optional[str] = Field(None, description="账户状态")


class BrokerageAccountResponse(BrokerageAccountBase):
    """券商账户响应模式"""
    id: int
    user_id: int
    user_type: str
    status: str
    connection_status: Optional[str] = None
    last_connected_at: Optional[datetime] = None
    last_disconnected_at: Optional[datetime] = None
    last_error: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class AccountSnapshotBase(BaseModel):
    """账户快照基础模式"""
    pre_balance: float = Field(..., description="昨日账户权益")
    balance: float = Field(..., description="当前账户权益")
    available: float = Field(..., description="可用资金")
    commission: float = Field(..., description="手续费")
    margin: float = Field(..., description="保证金占用")
    frozen_margin: float = Field(..., description="冻结保证金")
    frozen_commission: float = Field(..., description="冻结手续费")
    close_profit: float = Field(..., description="平仓盈亏")
    position_profit: float = Field(..., description="持仓盈亏")
    withdraw_quota: float = Field(..., description="可取资金")
    reserve_balance: float = Field(..., description="基本准备金")


class AccountSnapshotCreate(AccountSnapshotBase):
    """账户快照创建模式"""
    snapshot_timestamp: Optional[datetime] = Field(None, description="快照时间")


class AccountSnapshotResponse(AccountSnapshotBase):
    """账户快照响应模式"""
    id: int
    user_brokerage_id: int
    snapshot_timestamp: datetime
    created_at: datetime
    
    # 计算字段
    total_profit: Optional[float] = Field(None, description="总盈亏")
    used_margin_ratio: Optional[float] = Field(None, description="保证金使用率")
    risk_ratio: Optional[float] = Field(None, description="风险度")
    
    class Config:
        from_attributes = True


class ConnectionStatusUpdate(BaseModel):
    """连接状态更新模式"""
    status: str = Field(..., description="连接状态：connected/disconnected/connecting/error")
    error_message: Optional[str] = Field(None, description="错误信息")
    
    @validator('status')
    def validate_status(cls, v):
        if v not in ['connected', 'disconnected', 'connecting', 'error']:
            raise ValueError('连接状态必须是 connected、disconnected、connecting 或 error')
        return v


class BrokerageAccountList(BaseModel):
    """券商账户列表响应"""
    accounts: list[BrokerageAccountResponse]
    total: int
    default_account_id: Optional[int] = None


class BrokerageCredentials(BaseModel):
    """券商账户凭据（解密后）"""
    password: str
    auth_code: Optional[str] = None
    app_id: Optional[str] = None
