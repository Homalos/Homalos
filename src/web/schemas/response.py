#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : response.py
@Date       : 2025/10/8
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 通用响应模式
"""
from typing import Generic, TypeVar, Optional
from pydantic import BaseModel

T = TypeVar('T')


class Response(BaseModel, Generic[T]):
    """通用API响应模式"""
    code: int = 200
    message: str = "success"
    data: Optional[T] = None


class ErrorResponse(BaseModel):
    """错误响应模式"""
    code: int
    message: str
    detail: Optional[str] = None

