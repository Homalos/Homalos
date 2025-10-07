#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : user.py
@Date       : 2025/10/8
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 用户数据模型
"""
from sqlalchemy import Column, String, Boolean, DateTime
from .base import BaseModel


class User(BaseModel):
    """用户模型"""
    __tablename__ = "users"

    username = Column(String(50), unique=True, nullable=False, index=True, comment="用户名")
    email = Column(String(100), unique=True, index=True, comment="邮箱")
    hashed_password = Column(String(255), nullable=False, comment="加密密码")
    full_name = Column(String(100), comment="全名")
    role = Column(String(20), default="user", nullable=False, comment="角色：admin/user")
    is_active = Column(Boolean, default=True, nullable=False, comment="是否激活")
    last_login = Column(DateTime, nullable=True, comment="最后登录时间")

