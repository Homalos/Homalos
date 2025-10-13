#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : trading_account.py
@Date       : 2025/10/13
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 资金账户数据模型
"""
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from .base import BaseModel


class TradingAccount(BaseModel):
    """资金账户模型"""
    __tablename__ = "trading_accounts"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True, comment="用户ID")
    broker_key = Column(String(50), nullable=False, comment="券商配置key（如simnow、tts等）")
    broker_id = Column(String(50), nullable=False, comment="券商ID")
    account_id = Column(String(100), nullable=False, comment="资金账号")
    encrypted_password = Column(String(255), nullable=False, comment="加密密码")
    app_id = Column(String(100), nullable=True, comment="应用ID")
    auth_code = Column(String(100), nullable=True, comment="授权码")
    display_name = Column(String(100), comment="显示名称")
    is_active = Column(Boolean, default=True, nullable=False, comment="是否激活")
    is_default = Column(Boolean, default=False, nullable=False, comment="是否默认账户")
    failed_attempts = Column(Integer, default=0, nullable=False, comment="登录失败次数")
    locked_until = Column(DateTime, nullable=True, comment="锁定到期时间")
    last_login = Column(DateTime, nullable=True, comment="最后登录时间")
    
    # 关联用户
    user = relationship("User", back_populates="trading_accounts")
    
    def __repr__(self):
        return f"<TradingAccount(id={self.id}, broker_id={self.broker_id}, account_id={self.account_id})>"

