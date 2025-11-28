#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : user.py
@Date       : 2025/11/12
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 用户数据模型 - 重新设计版本
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column, String, Boolean, DateTime, Integer, 
    BigInteger, Text, Enum as SQLEnum, Index, and_
)
from sqlalchemy.orm import foreign
from sqlalchemy.orm import relationship
import enum

from .base import Base


class UserStatus(enum.Enum):
    """用户状态枚举"""
    INACTIVE = 0    # 未激活
    ACTIVE = 1      # 正常
    FROZEN = 2      # 冻结
    DISABLED = 3    # 禁用


class UserRole(enum.Enum):
    """用户角色枚举"""
    NORMAL = "normal"
    ADMIN = "admin"


class User(Base):
    """
    用户模型 - 重新设计版本
    
    安全性优先，支持完整的用户管理功能
    """
    __tablename__ = "users"

    # 主键 - 使用INT自增ID，与业务无关
    user_id = Column(
        Integer, 
        primary_key=True, 
        index=True, 
        autoincrement=True,
        comment="用户唯一标识，主键"
    )
    
    # 基本信息
    username = Column(
        String(50), 
        unique=True, 
        nullable=False, 
        index=True,
        comment="用户名，唯一索引，用于登录和显示"
    )
    
    email = Column(
        String(255), 
        unique=True, 
        nullable=False, 
        index=True,
        comment="邮箱地址，唯一索引，可用于登录、找回密码和接收通知"
    )
    
    password_hash = Column(
        String(255), 
        nullable=False,
        comment="密码哈希值，使用bcrypt或Argon2等强哈希算法"
    )
    
    phone = Column(
        String(20), 
        unique=True, 
        nullable=True, 
        index=True,
        comment="手机号，可选，唯一索引，可用于二次验证或短信通知"
    )
    
    # 账户状态和角色
    status = Column(
        SQLEnum(UserStatus),
        default=UserStatus.INACTIVE,
        nullable=False,
        index=True,
        comment="账户状态：0-未激活，1-正常，2-冻结，3-禁用"
    )
    
    role = Column(
        SQLEnum(UserRole),
        default=UserRole.NORMAL,
        nullable=False,
        index=True,
        comment="角色：normal、admin"
    )
    
    # 时间戳
    created_at = Column(
        DateTime, 
        default=datetime.utcnow, 
        nullable=False,
        index=True,
        comment="创建时间"
    )
    
    updated_at = Column(
        DateTime, 
        default=datetime.utcnow, 
        onupdate=datetime.utcnow, 
        nullable=False,
        comment="最后更新时间"
    )
    
    # 个人信息
    full_name = Column(
        String(100), 
        nullable=True,
        comment="用户全名/真实姓名"
    )
    
    # 本地化设置
    timezone = Column(
        String(50), 
        default="Asia/Shanghai", 
        nullable=False,
        comment="用户所在时区，用于正确显示时间和执行定时任务"
    )
    
    locale = Column(
        String(10), 
        default="zh-CN", 
        nullable=False,
        comment="语言偏好，如 zh-CN, en-US"
    )
    
    # 头像
    avatar_url = Column(
        String(500), 
        nullable=True,
        comment="头像图片的URL地址"
    )
    
    # 验证状态
    email_verified_at = Column(
        DateTime, 
        nullable=True,
        comment="邮箱验证时间，NULL表示未验证"
    )
    
    phone_verified_at = Column(
        DateTime, 
        nullable=True,
        comment="手机号验证时间，NULL表示未验证"
    )
    
    # 登录信息
    last_login_at = Column(
        DateTime, 
        nullable=True,
        comment="最后登录时间"
    )
    
    last_login_ip = Column(
        String(45), 
        nullable=True,
        comment="最后一次登录的IP地址，支持IPv6"
    )
    
    # 多因素认证
    mfa_secret = Column(
        String(255), 
        nullable=True,
        comment="多因素认证密钥，加密存储"
    )
    
    mfa_enabled = Column(
        Boolean, 
        default=False, 
        nullable=False,
        comment="是否启用了MFA"
    )
    
    # 安全增强字段
    password_changed_at = Column(
        DateTime,
        nullable=True,
        comment="密码最后修改时间"
    )
    
    failed_login_attempts = Column(
        BigInteger,
        default=0,
        nullable=False,
        comment="连续登录失败次数"
    )
    
    locked_until = Column(
        DateTime,
        nullable=True,
        comment="账户锁定到期时间"
    )
    
    # 关联关系
    audit_logs = relationship(
        "AuditLog", 
        back_populates="user", 
        cascade="all, delete-orphan",
        foreign_keys="AuditLog.user_id"
    )
    
    user_brokerages = relationship(
        "UserBrokerage", 
        cascade="all, delete-orphan",
        primaryjoin="and_(User.user_id == foreign(UserBrokerage.user_id), UserBrokerage.user_type == 'user')"
    )
    
    # user_preferences 关系已移除，因为user_preferences表现在支持users和admins两种用户类型
    # 不再使用外键关联，改为通过user_id和user_type查询
    
    trading_accounts = relationship(
        "TradingAccount", 
        back_populates="user", 
        cascade="all, delete-orphan"
    )
    
    # 索引定义
    __table_args__ = (
        Index('idx_users_username', 'username'),
        Index('idx_users_email', 'email'),
        Index('idx_users_phone', 'phone'),
        Index('idx_users_status', 'status'),
        Index('idx_users_role', 'role'),
        Index('idx_users_created_at', 'created_at'),
        Index('idx_users_last_login_at', 'last_login_at'),
        {'comment': '用户表 - 重新设计版本，安全性优先'}
    )
    
    # 属性方法
    @property
    def is_admin(self) -> bool:
        """判断是否为管理员"""
        return self.role == UserRole.ADMIN
    
    @property
    def is_active(self) -> bool:
        """判断账户是否激活"""
        return self.status == UserStatus.ACTIVE
    
    @property
    def is_verified(self) -> bool:
        """判断邮箱是否已验证"""
        return self.email_verified_at is not None
    
    @property
    def phone_verified(self) -> bool:
        """判断手机号是否已验证"""
        return self.phone_verified_at is not None
    
    # 兼容性属性（用于向后兼容）
    @property
    def id(self) -> int:
        """兼容性属性：返回user_id"""
        return self.user_id
    
    @property
    def hashed_password(self) -> str:
        """兼容性属性：返回password_hash"""
        return self.password_hash
    
    @property
    def last_login(self) -> Optional[datetime]:
        """兼容性属性：返回last_login_at"""
        return self.last_login_at
    
    @last_login.setter
    def last_login(self, value: Optional[datetime]):
        """兼容性属性：设置last_login_at"""
        self.last_login_at = value
    
    @property
    def email_verified(self) -> bool:
        """判断邮箱是否已验证"""
        return self.email_verified_at is not None
    
    def __repr__(self):
        return f"<User(user_id={self.user_id}, username={self.username}, email={self.email})>"

