#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : token.py
@Date       : 2025/10/8
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: Token相关的Pydantic模式
"""
from typing import Optional
from pydantic import BaseModel


class Token(BaseModel):
    """Token响应模式"""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Token数据模式"""
    username: Optional[str] = None

