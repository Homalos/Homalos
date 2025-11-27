#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : user_preference.py
@Date       : 2025/11/12
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 用户偏好设置数据模型
"""
from datetime import datetime
from sqlalchemy import Column, String, Integer, BigInteger, DateTime, Index, ForeignKey, Text
from sqlalchemy.orm import relationship

from .base import Base


class UserPreference(Base):
    """
    用户偏好设置表
    
    存储用户的个性化配置，如主题、图表设置、默认参数等
    支持普通用户(users表)和管理员(admins表)
    """
    __tablename__ = "user_preferences"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    user_id = Column(
        BigInteger, 
        nullable=False, 
        index=True,
        comment="用户ID，可以是users.user_id或admins.admin_id"
    )
    
    user_type = Column(
        String(10),
        nullable=False,
        default='user',
        index=True,
        comment="用户类型：user(普通用户) 或 admin(管理员)"
    )
    
    # 界面设置
    theme = Column(
        String(20), 
        default="light", 
        nullable=False,
        comment="界面主题：light, dark, auto"
    )
    
    language = Column(
        String(10), 
        default="zh-CN", 
        nullable=False,
        comment="界面语言"
    )
    
    # 交易设置
    default_order_type = Column(
        String(20), 
        default="limit", 
        nullable=False,
        comment="默认订单类型"
    )
    
    default_time_in_force = Column(
        String(20), 
        default="GTC", 
        nullable=False,
        comment="默认订单有效期"
    )
    
    # 图表设置
    chart_settings = Column(
        Text, 
        nullable=True,
        comment="图表配置，JSON格式存储"
    )
    
    # 通知设置
    notification_settings = Column(
        Text, 
        nullable=True,
        comment="通知配置，JSON格式存储"
    )
    
    # 其他自定义设置
    custom_settings = Column(
        Text, 
        nullable=True,
        comment="其他自定义设置，JSON格式存储"
    )
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        Index('idx_user_preferences_user_id', 'user_id'),
        Index('idx_user_preferences_user_type', 'user_type'),
        Index('idx_user_preferences_user_id_type', 'user_id', 'user_type', unique=True),
        {'comment': '用户偏好设置表，支持普通用户和管理员'}
    )
    
    def __repr__(self):
        return f"<UserPreference(id={self.id}, user_id={self.user_id}, user_type={self.user_type}, theme={self.theme})>"
