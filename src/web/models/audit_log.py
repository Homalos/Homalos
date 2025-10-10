#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : audit_log.py
@Date       : 2025/10/10
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 审计日志数据模型
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship

from src.web.models.base import Base


class AuditLog(Base):
    """审计日志模型"""
    
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True, comment="主键ID")
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="操作用户ID")
    operation_type = Column(String(50), nullable=False, comment="操作类型: start/stop/restart/config_update等")
    target = Column(String(100), nullable=False, comment="操作目标: datacenter/trading_system等")
    details = Column(Text, comment="操作详情(JSON格式)")
    success = Column(Boolean, default=True, comment="操作是否成功")
    error_message = Column(Text, comment="错误信息")
    ip_address = Column(String(50), comment="操作IP地址")
    user_agent = Column(String(255), comment="用户代理")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    
    # 关联用户
    user = relationship("User", back_populates="audit_logs")
    
    def __repr__(self):
        return f"<AuditLog(id={self.id}, user_id={self.user_id}, operation={self.operation_type}, target={self.target})>"
    
    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "username": self.user.username if self.user else None,
            "operation_type": self.operation_type,
            "target": self.target,
            "details": self.details,
            "success": self.success,
            "error_message": self.error_message,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

