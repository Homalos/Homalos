#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : strategy.py
@Date       : 2025/11/27
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 策略数据模型 - 策略与创建者对应关系
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column, String, Boolean, DateTime, Integer, BigInteger, Text,
    Enum as SQLEnum, Index, ForeignKey, JSON
)
from sqlalchemy.orm import relationship
import enum
import uuid

from .base import Base


class StrategyStatus(enum.Enum):
    """策略状态枚举"""
    DRAFT = "draft"           # 草稿
    ACTIVE = "active"         # 激活
    INACTIVE = "inactive"     # 未激活
    ARCHIVED = "archived"     # 归档


class Strategy(Base):
    """
    策略模型 - 策略与创建者对应关系
    
    每个策略由一个管理员创建，只有创建者能查看和管理该策略
    """
    __tablename__ = "strategies"

    # 主键
    strategy_id = Column(
        Integer,
        primary_key=True,
        index=True,
        autoincrement=True,
        comment="策略唯一标识，主键"
    )

    # 策略UUID - 用于系统内部唯一标识
    uuid = Column(
        String(36),
        unique=True,
        nullable=False,
        index=True,
        default=lambda: str(uuid.uuid4()),
        comment="策略UUID，唯一标识"
    )

    # 创建者信息 - 建立与管理员的对应关系
    admin_id = Column(
        Integer,
        ForeignKey('admins.admin_id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        comment="创建者管理员ID，外键关联admins表"
    )

    # 策略基本信息
    name = Column(
        String(100),
        nullable=False,
        index=True,
        comment="策略名称"
    )

    description = Column(
        Text,
        nullable=True,
        comment="策略描述"
    )

    author = Column(
        String(100),
        nullable=True,
        comment="策略作者"
    )

    # 策略文件信息
    file_path = Column(
        String(500),
        nullable=False,
        comment="策略文件路径"
    )

    module_path = Column(
        String(500),
        nullable=False,
        comment="策略模块路径"
    )

    class_name = Column(
        String(100),
        nullable=False,
        default="Strategy",
        comment="策略类名"
    )

    # 策略配置
    instruments = Column(
        JSON,
        nullable=True,
        default=list,
        comment="订阅的合约列表，JSON格式"
    )

    parameters = Column(
        JSON,
        nullable=True,
        default=dict,
        comment="策略参数配置，JSON格式"
    )

    # 策略状态
    status = Column(
        SQLEnum(StrategyStatus),
        default=StrategyStatus.DRAFT,
        nullable=False,
        index=True,
        comment="策略状态：draft-草稿, active-激活, inactive-未激活, archived-归档"
    )

    enabled = Column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        comment="是否启用"
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

    # 关联关系
    admin = relationship(
        "Admin",
        backref="strategies"
    )

    # 索引定义
    __table_args__ = (
        Index('idx_strategies_admin_id', 'admin_id'),
        Index('idx_strategies_name', 'name'),
        Index('idx_strategies_status', 'status'),
        Index('idx_strategies_enabled', 'enabled'),
        Index('idx_strategies_created_at', 'created_at'),
        Index('idx_strategies_admin_id_status', 'admin_id', 'status'),  # 复合索引：查询某管理员的策略
        Index('idx_strategies_admin_id_enabled', 'admin_id', 'enabled'),  # 复合索引：查询某管理员的启用策略
        {'comment': '策略表 - 策略与创建者对应关系'}
    )

    def __repr__(self):
        return f"<Strategy(strategy_id={self.strategy_id}, name={self.name}, admin_id={self.admin_id})>"

    def to_dict(self):
        """转换为字典"""
        return {
            "strategy_id": self.strategy_id,
            "uuid": self.uuid,
            "name": self.name,
            "description": self.description,
            "author": self.author,
            "file_path": self.file_path,
            "module_path": self.module_path,
            "class_name": self.class_name,
            "instruments": self.instruments or [],
            "parameters": self.parameters or {},
            "status": self.status.value if self.status else "draft",
            "enabled": self.enabled,
            "admin_id": self.admin_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
