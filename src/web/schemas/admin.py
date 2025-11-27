#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : admin.py
@Date       : 2025/11/12
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 管理员相关的Pydantic模式
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, validator


class AdminBase(BaseModel):
    """管理员基础模式"""
    username: str = Field(..., min_length=3, max_length=50, description="管理员用户名")
    email: EmailStr = Field(..., description="邮箱地址")
    phone: Optional[str] = Field(None, max_length=20, description="手机号")
    full_name: Optional[str] = Field(None, max_length=100, description="管理员真实姓名")
    timezone: str = Field(default="Asia/Shanghai", max_length=50, description="时区")
    locale: str = Field(default="zh-CN", max_length=10, description="语言偏好")


class AdminCreate(AdminBase):
    """管理员创建模式"""
    password: str = Field(..., min_length=12, max_length=50, description="密码（至少12位）")
    confirm_password: str = Field(..., description="确认密码")
    role: str = Field(default="normal", description="管理员角色：normal/super")
    invitation_code: Optional[str] = Field(None, description="邀请码（创建超级管理员时需要）")
    
    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'password' in values and v != values['password']:
            raise ValueError('两次输入的密码不一致')
        return v
    
    @validator('password')
    def validate_password_strength(cls, v):
        """验证密码强度"""
        if len(v) < 12:
            raise ValueError('密码长度至少12位')
        
        has_upper = any(c.isupper() for c in v)
        has_lower = any(c.islower() for c in v)
        has_digit = any(c.isdigit() for c in v)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in v)
        
        if not all([has_upper, has_lower, has_digit, has_special]):
            raise ValueError('密码必须包含大小写字母、数字和特殊字符')
        
        return v
    
    @validator('phone')
    def validate_phone(cls, v):
        """验证手机号格式"""
        if v is None:
            return v
        
        # 简单的手机号验证（支持国际格式）
        import re
        if not re.match(r'^(\+\d{1,3}[- ]?)?\d{10,11}$', v.replace(' ', '').replace('-', '')):
            raise ValueError('请输入正确的手机号格式')
        
        return v


class AdminUpdate(BaseModel):
    """管理员更新模式"""
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    full_name: Optional[str] = None
    timezone: Optional[str] = None
    locale: Optional[str] = None
    avatar_url: Optional[str] = None


class AdminLogin(BaseModel):
    """管理员登录模式"""
    username_or_email_or_phone: str = Field(..., description="用户名、邮箱或手机号")
    password: str = Field(..., description="密码")
    mfa_code: Optional[str] = Field(None, description="MFA验证码")


class AdminResponse(BaseModel):
    """管理员响应模式"""
    admin_id: int
    username: str
    email: str  # 改为 str 而不是 EmailStr，避免严格验证
    phone: Optional[str] = None
    full_name: Optional[str] = None
    timezone: str
    locale: str
    role: str
    status: str
    email_verified: bool
    phone_verified: bool
    mfa_enabled: bool
    avatar_url: Optional[str] = None
    created_at: datetime
    last_login_at: Optional[datetime] = None
    
    @classmethod
    def from_admin_model(cls, admin):
        """从Admin模型创建AdminResponse"""
        return cls(
            admin_id=admin.admin_id,
            username=admin.username,
            email=admin.email,
            phone=admin.phone,
            full_name=admin.full_name,
            timezone=admin.timezone,
            locale=admin.locale,
            role=admin.role.value if admin.role else "normal",
            status=admin.status.name if admin.status else "INACTIVE",
            email_verified=admin.email_verified_at is not None,
            phone_verified=admin.phone_verified_at is not None,
            mfa_enabled=admin.mfa_enabled,
            avatar_url=admin.avatar_url,
            created_at=admin.created_at,
            last_login_at=admin.last_login_at
        )
    
    class Config:
        from_attributes = True


class AdminPasswordChange(BaseModel):
    """管理员密码修改模式"""
    old_password: str = Field(..., description="旧密码")
    new_password: str = Field(..., min_length=12, max_length=50, description="新密码")
    confirm_password: str = Field(..., description="确认新密码")
    
    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('两次输入的密码不一致')
        return v
    
    @validator('new_password')
    def validate_password_strength(cls, v):
        """验证密码强度"""
        if len(v) < 12:
            raise ValueError('密码长度至少12位')
        
        has_upper = any(c.isupper() for c in v)
        has_lower = any(c.islower() for c in v)
        has_digit = any(c.isdigit() for c in v)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in v)
        
        if not all([has_upper, has_lower, has_digit, has_special]):
            raise ValueError('密码必须包含大小写字母、数字和特殊字符')
        
        return v


class AdminProfileUpdate(BaseModel):
    """管理员个人资料更新模式"""
    full_name: Optional[str] = Field(None, max_length=100, description="真实姓名")
    timezone: Optional[str] = Field(None, max_length=50, description="时区")
    locale: Optional[str] = Field(None, max_length=10, description="语言偏好")
    avatar_url: Optional[str] = Field(None, max_length=500, description="头像URL")


class AdminVerificationRequest(BaseModel):
    """管理员验证请求模式"""
    verification_type: str = Field(..., description="验证类型：email/phone")
    code: Optional[str] = Field(None, description="验证码")


class AdminInvitationCreate(BaseModel):
    """管理员邀请创建模式"""
    email: EmailStr = Field(..., description="被邀请人邮箱")
    role: str = Field(default="normal", description="角色：normal/super")
    expires_hours: int = Field(default=72, description="邀请有效期（小时）")
    message: Optional[str] = Field(None, description="邀请消息")


class AdminInvitationResponse(BaseModel):
    """管理员邀请响应模式"""
    invitation_id: str
    email: str
    role: str
    created_by: str
    expires_at: datetime
    status: str  # pending, accepted, expired, revoked
    
    class Config:
        from_attributes = True
