#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : api_response.py
@Date       : 2025/9/9 18:08
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: Event payload 封装工具类
包含：
1. 错误码枚举（通用、行情、交易、风控、策略模块）
2. 统一 payload 封装（成功/失败方法）
"""
import time
from typing import Optional, Any

from src.core.constants import RspCode


class PackPayload(object):
    """
    API 响应封装
    """
    @staticmethod
    def _base(
            code: RspCode,
            message: str,
            data: Optional[Any] = None
    ) -> dict:
        """
        响应信息

        Args:
            code: 错误码
            message: 信息
            data: 数据

        Returns:
            dict: 响应字典
        """
        rsp = {
            "code": code,
            "message": message,
            "data": data,
            "timestamp": int(time.time() * 1000)
        }
        return rsp

    @classmethod
    def success(cls, data: Optional[Any] = None, message: str = "success") -> dict:
        """
        成功响应

        Args:
            data: 数据
            message: 信息

        Returns:
            dict: 响应字典
        """
        return cls._base(RspCode.SUCCESS, message, data)

    @classmethod
    def fail(cls, code: int | str | RspCode, message: str, data: Optional[Any] = None) -> dict:
        """
        失败响应

        Args:
            code: 错误码
            message: 信息
            data: 数据

        Returns:
            dict: 响应字典
        """
        if isinstance(code, str):
            code = int(code)
        return cls._base(code, message, data)
