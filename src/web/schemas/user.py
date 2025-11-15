#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : user.py
@Date       : 2025/10/7
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 用户相关的Pydantic模式
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, validator


class UserBase(BaseModel):
    """用户基础模式"""
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    email: EmailStr = Field(..., description="邮箱地址")  # 必填，用于找回密码和通知
    phone: Optional[str] = Field(None, max_length=20, description="手机号")
    full_name: Optional[str] = Field(None, max_length=100, description="全名")
    timezone: str = Field(default="Asia/Shanghai", max_length=50, description="时区")
    locale: str = Field(default="zh-CN", max_length=10, description="语言偏好")


class UserCreate(UserBase):
    """用户创建模式"""
    password: str = Field(..., min_length=6, max_length=50, description="密码")
    confirm_password: str = Field(..., description="确认密码")
    avatar_url: Optional[str] = Field(None, max_length=500, description="头像URL")
    
    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'password' in values and v != values['password']:
            raise ValueError('两次输入的密码不一致')
        return v


class UserUpdate(BaseModel):
    """用户更新模式"""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    password: Optional[str] = Field(None, min_length=6, max_length=50)


class UserLogin(BaseModel):
    """用户登录模式"""
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")


class UserResponse(UserBase):
    """用户响应模式"""
    user_id: int
    status: str
    email_verified: bool
    phone_verified: bool
    mfa_enabled: bool
    avatar_url: Optional[str] = None
    created_at: datetime
    last_login_at: Optional[datetime] = None

    class Config:
        from_attributes = True  # Pydantic v2语法


class PasswordResetRequest(BaseModel):
    """密码重置请求（验证身份）"""
    username: str = Field(..., description="用户名")
    email: EmailStr = Field(..., description="注册邮箱")


class PasswordResetConfirm(BaseModel):
    """密码重置确认（设置新密码）"""
    username: str = Field(..., description="用户名")
    email: EmailStr = Field(..., description="注册邮箱")
    new_password: str = Field(..., min_length=6, max_length=50, description="新密码")
