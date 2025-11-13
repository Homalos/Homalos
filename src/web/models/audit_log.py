#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : audit_log.py
@Date       : 2025/11/12
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 审计日志数据模型 - 重新设计版本
"""
from datetime import datetime
from sqlalchemy import Column, Integer, BigInteger, String, DateTime, Boolean, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.mysql import LONGTEXT

from src.web.models.base import Base


class AuditLog(Base):
    """
    审计日志表
    
    记录用户的安全相关操作，如登录尝试、密码修改等
    """
    __tablename__ = "audit_logs"
    
    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    
    user_id = Column(
        BigInteger, 
        ForeignKey("users.user_id", ondelete="SET NULL"),
        nullable=True,  # 允许为空，因为可能记录未登录用户的操作
        index=True,
        comment="用户ID，外键关联users.user_id"
    )
    
    action = Column(
        String(50), 
        nullable=False,
        index=True,
        comment="操作类型：login, logout, password_change, etc."
    )
    
    resource = Column(
        String(100), 
        nullable=True,
        comment="操作的资源"
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
    
    details = Column(
        LONGTEXT, 
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
    user = relationship("User", back_populates="audit_logs")
    
    __table_args__ = (
        Index('idx_audit_logs_user_id', 'user_id'),
        Index('idx_audit_logs_action', 'action'),
        Index('idx_audit_logs_created_at', 'created_at'),
        Index('idx_audit_logs_success', 'success'),
        Index('idx_audit_logs_user_action', 'user_id', 'action'),
        {'comment': '审计日志表'}
    )
    
    def __repr__(self):
        return f"<AuditLog(id={self.id}, user_id={self.user_id}, action={self.action}, success={self.success})>"
    
    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "username": self.user.username if self.user else None,
            "action": self.action,
            "resource": self.resource,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "success": self.success,
            "error_message": self.error_message,
            "details": self.details,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
    
    # 兼容性属性（用于向后兼容）
    @property
    def operation_type(self) -> str:
        """兼容性属性：返回action"""
        return self.action
    
    @property
    def target(self) -> str:
        """兼容性属性：返回resource"""
        return self.resource or ""

