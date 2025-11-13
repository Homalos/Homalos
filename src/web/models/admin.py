#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : admin.py
@Date       : 2025/11/12
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 管理员数据模型 - 独立设计，权限分离
"""
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy import (
    Column, String, Boolean, DateTime, BigInteger, 
    Enum as SQLEnum, Index, ForeignKey
)
from sqlalchemy.orm import relationship
import enum

from .base import Base


class AdminStatus(enum.Enum):
    """管理员状态枚举"""
    INACTIVE = 0    # 未激活
    ACTIVE = 1      # 正常
    FROZEN = 2      # 冻结
    DISABLED = 3    # 禁用


class AdminRole(enum.Enum):
    """管理员角色枚举"""
    NORMAL = "normal"    # 普通管理员
    SUPER = "super"      # 超级管理员


class Admin(Base):
    """
    管理员模型 - 独立设计
    
    与普通用户完全分离，实现权限分离和更高的安全性
    """
    __tablename__ = "admins"

    # 主键 - 使用BIGINT自增ID
    admin_id = Column(
        BigInteger, 
        primary_key=True, 
        index=True, 
        autoincrement=True,
        comment="管理员唯一标识，主键"
    )
    
    # 基本信息
    username = Column(
        String(50), 
        unique=True, 
        nullable=False, 
        index=True,
        comment="管理员用户名，唯一索引"
    )
    
    email = Column(
        String(255), 
        unique=True, 
        nullable=False, 
        index=True,
        comment="邮箱地址，唯一索引"
    )
    
    phone = Column(
        String(20), 
        unique=True, 
        nullable=True, 
        index=True,
        comment="手机号，可选，唯一索引，可用于二次验证或短信通知"
    )
    
    password_hash = Column(
        String(255), 
        nullable=False,
        comment="密码哈希值，使用强哈希算法（建议Argon2）"
    )
    
    # 管理员角色和状态
    role = Column(
        SQLEnum(AdminRole),
        default=AdminRole.NORMAL,
        nullable=False,
        index=True,
        comment="管理员角色：super-超级管理员, normal-普通管理员"
    )
    
    status = Column(
        SQLEnum(AdminStatus),
        default=AdminStatus.INACTIVE,
        nullable=False,
        index=True,
        comment="账户状态：0-未激活，1-正常，2-冻结，3-禁用"
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
        comment="管理员真实姓名"
    )
    
    # 本地化设置
    timezone = Column(
        String(50), 
        default="Asia/Shanghai", 
        nullable=False,
        comment="管理员所在时区，用于正确显示时间和执行定时任务"
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
        index=True,
        comment="最后一次登录时间"
    )
    
    last_login_ip = Column(
        String(45), 
        nullable=True,
        comment="最后一次登录IP，支持IPv6"
    )
    
    # 多因素认证（管理员强制要求更高安全性）
    mfa_secret = Column(
        String(255), 
        nullable=True,
        comment="多因素认证密钥，加密存储"
    )
    
    mfa_enabled = Column(
        Boolean, 
        default=False, 
        nullable=False,
        comment="是否启用MFA（建议管理员强制启用）"
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
    admin_audit_logs = relationship(
        "AdminAuditLog", 
        back_populates="admin", 
        cascade="all, delete-orphan"
    )
    
    # 索引定义
    __table_args__ = (
        Index('idx_admins_username', 'username'),
        Index('idx_admins_email', 'email'),
        Index('idx_admins_phone', 'phone'),
        Index('idx_admins_role', 'role'),
        Index('idx_admins_status', 'status'),
        Index('idx_admins_created_at', 'created_at'),
        Index('idx_admins_last_login_at', 'last_login_at'),
        Index('idx_admins_role_status', 'role', 'status'),  # 复合索引
        {'comment': '管理员表 - 独立设计，权限分离'}
    )
    
    # 属性方法
    @property
    def is_super_admin(self) -> bool:
        """判断是否为超级管理员"""
        return self.role == AdminRole.SUPER
    
    @property
    def is_active(self) -> bool:
        """判断账户是否激活"""
        return self.status == AdminStatus.ACTIVE
    
    @property
    def is_verified(self) -> bool:
        """判断邮箱是否已验证"""
        return self.email_verified_at is not None
    
    @property
    def email_verified(self) -> bool:
        """判断邮箱是否已验证（AdminResponse兼容性）"""
        return self.email_verified_at is not None
    
    @property
    def phone_verified(self) -> bool:
        """判断手机号是否已验证"""
        return self.phone_verified_at is not None
    
    @property
    def status_str(self) -> str:
        """返回状态的字符串表示（AdminResponse兼容性）"""
        return self.status.name if self.status else "INACTIVE"
    
    @property
    def role_str(self) -> str:
        """返回角色的字符串表示（AdminResponse兼容性）"""
        return self.role.value if self.role else "normal"
    
    @property
    def is_locked(self) -> bool:
        """判断账户是否被锁定"""
        if self.locked_until is None:
            return False
        return datetime.utcnow() < self.locked_until
    
    @property
    def password_expired(self) -> bool:
        """判断密码是否过期（90天策略）"""
        if self.password_changed_at is None:
            return True  # 未设置密码修改时间，认为已过期
        
        password_max_age_days = 90
        expiry_date = self.password_changed_at + timedelta(days=password_max_age_days)
        return datetime.utcnow() > expiry_date
    
    @property
    def requires_mfa(self) -> bool:
        """判断是否需要MFA（超级管理员强制要求）"""
        return self.is_super_admin or self.mfa_enabled
    
    def can_perform_action(self, action: str) -> bool:
        """
        检查管理员是否可以执行特定操作
        
        Args:
            action: 操作类型
            
        Returns:
            bool: 是否有权限执行
        """
        # 基本状态检查
        if not self.is_active or self.is_locked:
            return False
        
        # 超级管理员权限
        super_admin_actions = {
            'create_admin', 'delete_admin', 'modify_admin_role',
            'system_config', 'database_backup', 'system_maintenance'
        }
        
        # 普通管理员权限
        normal_admin_actions = {
            'view_users', 'modify_user_status', 'view_trading_accounts',
            'view_strategies', 'view_audit_logs', 'basic_system_monitor'
        }
        
        if self.is_super_admin:
            return action in super_admin_actions or action in normal_admin_actions
        else:
            return action in normal_admin_actions
    
    def lock_account(self, duration_minutes: int = 30):
        """锁定账户"""
        self.locked_until = datetime.utcnow() + timedelta(minutes=duration_minutes)
        self.failed_login_attempts = 0
    
    def unlock_account(self):
        """解锁账户"""
        self.locked_until = None
        self.failed_login_attempts = 0
    
    def record_failed_login(self):
        """记录登录失败"""
        self.failed_login_attempts += 1
        
        # 连续失败5次锁定账户30分钟
        if self.failed_login_attempts >= 5:
            self.lock_account(30)
    
    def record_successful_login(self, ip_address: str):
        """记录成功登录"""
        self.last_login_at = datetime.utcnow()
        self.last_login_ip = ip_address
        self.failed_login_attempts = 0
        self.locked_until = None
    
    def __repr__(self):
        return f"<Admin(admin_id={self.admin_id}, username={self.username}, role={self.role.value})>"


class AdminAuditLog(Base):
    """
    管理员审计日志表
    
    专门记录管理员的操作，特别是敏感操作
    """
    __tablename__ = "admin_audit_logs"
    
    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    
    admin_id = Column(
        BigInteger, 
        ForeignKey('admins.admin_id', ondelete='SET NULL'),
        nullable=True,  # 允许为空，记录未认证的管理员操作尝试
        index=True,
        comment="管理员ID"
    )
    
    action = Column(
        String(100), 
        nullable=False,
        index=True,
        comment="操作类型：login, create_user, delete_strategy, etc."
    )
    
    resource = Column(
        String(100), 
        nullable=True,
        comment="操作的资源"
    )
    
    resource_id = Column(
        String(50),
        nullable=True,
        comment="资源ID"
    )
    
    ip_address = Column(
        String(45), 
        nullable=True,
        comment="操作IP地址，支持IPv6"
    )
    
    user_agent = Column(
        String(500), 
        nullable=True,
        comment="用户代理字符串"
    )
    
    success = Column(
        Boolean, 
        nullable=False,
        index=True,
        comment="操作是否成功"
    )
    
    error_message = Column(
        String(500), 
        nullable=True,
        comment="错误信息（如果操作失败）"
    )
    
    risk_level = Column(
        SQLEnum(enum.Enum('RiskLevel', 'LOW MEDIUM HIGH CRITICAL')),
        default='MEDIUM',
        nullable=False,
        index=True,
        comment="风险级别：LOW, MEDIUM, HIGH, CRITICAL"
    )
    
    details = Column(
        String(2000),  # 使用较短的字段，避免过大
        nullable=True,
        comment="操作详情，JSON格式存储"
    )
    
    created_at = Column(
        DateTime, 
        default=datetime.utcnow, 
        nullable=False,
        index=True,
        comment="操作时间"
    )
    
    # 关联关系
    admin = relationship("Admin", back_populates="admin_audit_logs")
    
    __table_args__ = (
        Index('idx_admin_audit_logs_admin_id', 'admin_id'),
        Index('idx_admin_audit_logs_action', 'action'),
        Index('idx_admin_audit_logs_created_at', 'created_at'),
        Index('idx_admin_audit_logs_success', 'success'),
        Index('idx_admin_audit_logs_risk_level', 'risk_level'),
        Index('idx_admin_audit_logs_admin_action', 'admin_id', 'action'),
        Index('idx_admin_audit_logs_resource', 'resource', 'resource_id'),
        {'comment': '管理员审计日志表'}
    )
    
    def __repr__(self):
        return f"<AdminAuditLog(id={self.id}, admin_id={self.admin_id}, action={self.action}, risk_level={self.risk_level})>"
    
    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "admin_id": self.admin_id,
            "admin_username": self.admin.username if self.admin else None,
            "action": self.action,
            "resource": self.resource,
            "resource_id": self.resource_id,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "success": self.success,
            "error_message": self.error_message,
            "risk_level": self.risk_level.value if self.risk_level else None,
            "details": self.details,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
