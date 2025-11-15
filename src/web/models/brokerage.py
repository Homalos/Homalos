#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : brokerage.py
@Date       : 2025/11/13
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 期货券商账户数据模型
"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    Column, String, Boolean, DateTime, Integer, 
    BigInteger, Text, Enum as SQLEnum, Index, Float, ForeignKey
)
from sqlalchemy.orm import relationship
import enum

from .base import Base


class AccountType(enum.Enum):
    """账户类型枚举"""
    SIMULATION = "simulation"  # 模拟盘
    PRODUCTION = "production"  # 实盘


class AccountStatus(enum.Enum):
    """账户状态枚举"""
    ACTIVE = "active"      # 激活
    INACTIVE = "inactive"  # 未激活
    ERROR = "error"        # 错误


class Environment(enum.Enum):
    """运行环境枚举"""
    DEV = "dev"      # 开发环境
    TEST = "test"    # 测试环境
    PROD = "prod"    # 生产环境


class ConnectionStatus(enum.Enum):
    """连接状态枚举"""
    CONNECTED = "connected"        # 已连接
    DISCONNECTED = "disconnected"  # 已断开
    CONNECTING = "connecting"      # 连接中
    ERROR = "error"               # 连接错误


class UserType(enum.Enum):
    """用户类型枚举"""
    USER = "user"    # 普通用户
    ADMIN = "admin"  # 管理员


class UserBrokerage(Base):
    """
    用户券商账户模型
    
    支持用户和管理员的多券商账户管理
    """
    __tablename__ = "user_brokerages"

    # 主键
    id = Column(
        Integer, 
        primary_key=True, 
        index=True, 
        autoincrement=True,
        comment="主键自动递增"
    )
    
    # 用户关联
    user_id = Column(
        Integer, 
        nullable=False, 
        index=True,
        comment="关联到用户表或管理员表的ID"
    )
    
    user_type = Column(
        SQLEnum(UserType),
        default=UserType.USER,
        nullable=False,
        index=True,
        comment="用户类型：user-普通用户, admin-管理员"
    )
    
    # 账户基本信息
    account_name = Column(
        String(100), 
        nullable=False,
        comment="用户自定义的账户别名，便于识别"
    )
    
    is_default = Column(
        Boolean, 
        default=False, 
        nullable=False,
        index=True,
        comment="标记用户的默认交易账户"
    )
    
    # 券商信息
    broker_code = Column(
        String(50), 
        nullable=False,
        index=True,
        comment="券商代码，如: CTP, 恒生等"
    )
    
    broker_name = Column(
        String(100), 
        nullable=False,
        comment="券商全称，例如中信期货"
    )
    
    # 账户标识
    account_id = Column(
        String(50), 
        nullable=False,
        comment="资金账户"
    )
    
    investor_id = Column(
        String(50), 
        nullable=False,
        comment="投资者代码"
    )
    
    broker_id = Column(
        String(50), 
        nullable=False,
        comment="经纪公司代码"
    )
    
    # 敏感信息（加密存储）
    password_encrypted = Column(
        Text, 
        nullable=False,
        comment="交易密码（加密存储）"
    )
    
    auth_code = Column(
        Text,
        nullable=True,
        comment="认证码（加密存储）"
    )
    
    app_id = Column(
        Text,
        nullable=True,
        comment="应用标识（加密存储）"
    )
    
    # 产品信息
    user_product_info = Column(
        String(200),
        nullable=True,
        comment="用户端产品信息"
    )
    
    # 账户配置
    account_type = Column(
        SQLEnum(AccountType),
        default=AccountType.PRODUCTION,
        nullable=False,
        index=True,
        comment="账户类型：simulation-模拟盘, production-实盘"
    )
    
    status = Column(
        SQLEnum(AccountStatus),
        default=AccountStatus.INACTIVE,
        nullable=False,
        index=True,
        comment="账户状态：active-激活, inactive-未激活, error-错误"
    )
    
    environment = Column(
        SQLEnum(Environment),
        default=Environment.PROD,
        nullable=False,
        index=True,
        comment="运行环境：dev-开发, test-测试, prod-生产"
    )
    
    # 前置机配置（预留扩展）
    md_front_index = Column(
        Integer,
        default=0,
        comment="当前使用的行情前置索引，未来扩展"
    )
    
    td_front_index = Column(
        Integer,
        default=0,
        comment="当前使用的交易前置索引，未来扩展"
    )
    
    # 交易限制
    daily_order_limit = Column(
        Integer,
        default=1000,
        comment="每日订单限制"
    )
    
    # 连接状态
    last_connected_at = Column(
        DateTime,
        nullable=True,
        comment="最后连接成功时间"
    )
    
    last_disconnected_at = Column(
        DateTime,
        nullable=True,
        comment="最后断开连接时间"
    )
    
    connection_status = Column(
        SQLEnum(ConnectionStatus),
        default=ConnectionStatus.DISCONNECTED,
        nullable=True,
        index=True,
        comment="实时连接状态：connected-已连接, disconnected-已断开, connecting-连接中, error-错误"
    )
    
    # 错误信息
    last_error = Column(
        Text,
        nullable=True,
        comment="最后错误信息"
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
    account_snapshots = relationship(
        "BrokerageAccountSnapshot", 
        back_populates="user_brokerage", 
        cascade="all, delete-orphan"
    )
    
    # 索引定义
    __table_args__ = (
        Index('idx_user_brokerages_user_id', 'user_id'),
        Index('idx_user_brokerages_user_type', 'user_type'),
        Index('idx_user_brokerages_broker_code', 'broker_code'),
        Index('idx_user_brokerages_account_type', 'account_type'),
        Index('idx_user_brokerages_status', 'status'),
        Index('idx_user_brokerages_environment', 'environment'),
        Index('idx_user_brokerages_connection_status', 'connection_status'),
        Index('idx_user_brokerages_is_default', 'is_default'),
        Index('idx_user_brokerages_created_at', 'created_at'),
        # 唯一约束：同一用户在同一券商下的资金账号必须唯一
        Index('idx_user_brokerages_unique_account', 'user_id', 'account_id', 'broker_code', unique=True),
        # 唯一约束：同一用户在同一券商下的投资者ID必须唯一
        Index('idx_user_brokerages_unique_investor', 'user_id', 'investor_id', 'broker_code', unique=True),
        {'comment': '用户券商账户表 - 支持多券商账户管理'}
    )
    
    # 属性方法
    @property
    def is_active(self) -> bool:
        """判断账户是否激活"""
        return self.status == AccountStatus.ACTIVE
    
    @property
    def is_connected(self) -> bool:
        """判断是否已连接"""
        return self.connection_status == ConnectionStatus.CONNECTED
    
    @property
    def is_simulation(self) -> bool:
        """判断是否为模拟账户"""
        return self.account_type == AccountType.SIMULATION
    
    @property
    def display_name(self) -> str:
        """获取显示名称"""
        return f"{self.account_name} ({self.broker_name})"
    
    def __repr__(self):
        return f"<UserBrokerage(id={self.id}, account_name='{self.account_name}', broker_code='{self.broker_code}')>"


class BrokerageAccountSnapshot(Base):
    """
    券商账户资金快照模型
    
    记录账户资金的历史快照数据
    """
    __tablename__ = "brokerage_account_snapshots"

    # 主键
    id = Column(
        Integer, 
        primary_key=True, 
        index=True, 
        autoincrement=True,
        comment="主键自动递增"
    )
    
    # 关联券商账户
    user_brokerage_id = Column(
        Integer,
        ForeignKey('user_brokerages.id'),
        nullable=False,
        index=True,
        comment="关联的券商账户ID"
    )
    
    # 资金信息
    pre_balance = Column(
        Float,
        nullable=False,
        comment="昨日账户权益"
    )
    
    balance = Column(
        Float,
        nullable=False,
        comment="当前账户权益"
    )
    
    available = Column(
        Float,
        nullable=False,
        comment="可用资金"
    )
    
    commission = Column(
        Float,
        nullable=False,
        comment="手续费"
    )
    
    margin = Column(
        Float,
        nullable=False,
        comment="保证金占用"
    )
    
    frozen_margin = Column(
        Float,
        nullable=False,
        comment="冻结保证金"
    )
    
    frozen_commission = Column(
        Float,
        nullable=False,
        comment="冻结手续费"
    )
    
    close_profit = Column(
        Float,
        nullable=False,
        comment="平仓盈亏"
    )
    
    position_profit = Column(
        Float,
        nullable=False,
        comment="持仓盈亏"
    )
    
    withdraw_quota = Column(
        Float,
        nullable=False,
        comment="可取资金"
    )
    
    reserve_balance = Column(
        Float,
        nullable=False,
        comment="基本准备金"
    )
    
    # 快照时间
    snapshot_timestamp = Column(
        DateTime,
        nullable=False,
        index=True,
        comment="快照时间"
    )
    
    # 创建时间
    created_at = Column(
        DateTime, 
        default=datetime.utcnow, 
        nullable=False,
        index=True,
        comment="创建时间"
    )
    
    # 关联关系
    user_brokerage = relationship(
        "UserBrokerage", 
        back_populates="account_snapshots"
    )
    
    # 索引定义
    __table_args__ = (
        Index('idx_brokerage_snapshots_user_brokerage_id', 'user_brokerage_id'),
        Index('idx_brokerage_snapshots_timestamp', 'snapshot_timestamp'),
        Index('idx_brokerage_snapshots_created_at', 'created_at'),
        Index('idx_brokerage_snapshots_unique', 'user_brokerage_id', 'snapshot_timestamp', unique=True),
        {'comment': '券商账户资金快照表 - 记录资金历史数据'}
    )
    
    # 属性方法
    @property
    def total_profit(self) -> float:
        """总盈亏"""
        return self.close_profit + self.position_profit
    
    @property
    def used_margin_ratio(self) -> float:
        """保证金使用率"""
        if self.balance <= 0:
            return 0.0
        return (self.margin / self.balance) * 100
    
    @property
    def risk_ratio(self) -> float:
        """风险度"""
        if self.margin <= 0:
            return 0.0
        return (self.balance / self.margin) * 100
    
    def __repr__(self):
        return f"<BrokerageAccountSnapshot(id={self.id}, balance={self.balance}, timestamp='{self.snapshot_timestamp}')>"
