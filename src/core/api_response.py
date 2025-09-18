#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : api_response.py
@Date       : 2025/9/9 18:08
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: APIResponse 工具类
包含：
1. 错误码枚举（通用、行情、交易、风控、策略模块）
2. 统一响应封装（成功/失败方法）
3. trace_id 自动生成（用 uuid4）
4. 日志上下文集成（loguru + trace_id）
"""
import time
import uuid
from typing import Optional, Any

from src.core.constants import ErrorCode
from src.core.trace_context import get_trace_id
from src.utils.log import get_logger

_logger = get_logger("APIResponse")


# ================= API Response 封装 =================
class APIResponse:
    @staticmethod
    def _base(code: int, message: str, data: Optional[Any] = None, trace_id: Optional[str] = None):
        # 优先用参数，其次用上下文 trace_id，最后生成新 trace_id
        trace_id = trace_id or get_trace_id() or str(uuid.uuid4())

        resp = {
            "code": code,
            "message": message,
            "data": data,
            "timestamp": int(time.time() * 1000),
            "trace_id": trace_id,
        }
        # 记录日志，带 trace_id
        log = _logger.bind(trace_id=trace_id)
        if code != ErrorCode.SUCCESS:
            log.debug(f"失败响应: {code} - {message}")
        return resp

    @classmethod
    def success(cls, data: Optional[Any] = None, message: str = "success", trace_id: Optional[str] = None):
        return cls._base(ErrorCode.SUCCESS, message, data, trace_id)

    @classmethod
    def fail(cls, code: int | str, message: str, data: Optional[Any] = None, trace_id: Optional[str] = None):
        if isinstance(code, str):
            code = int(code)
        return cls._base(code, message, data, trace_id)
