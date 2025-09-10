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
from enum import IntEnum
from typing import Optional, Any

from src.core.trace_context import get_trace_id
from src.utils.log import get_logger

_logger = get_logger("APIResponse")


# ================= 错误码定义 =================
class ErrorCode(IntEnum):
    # 通用
    SUCCESS = 0
    PARAM_ERROR = 1001
    AUTH_FAILED = 1002
    PERMISSION_DENIED = 1003
    TOO_MANY_REQUESTS = 1004
    NOT_FOUND = 1005
    SYSTEM_ERROR = 1006
    UNKNOWN_ERROR = 1999

    # 行情模块 2xxx
    MARKET_SYMBOL_NOT_FOUND = 2001
    MARKET_DELAYED = 2002
    MARKET_TYPE_INVALID = 2003
    MARKET_SUB_EXISTS = 2004

    # 交易模块 3xxx
    TRADE_ORDER_FAILED = 3001
    TRADE_CANCEL_FAILED = 3002
    TRADE_NO_FUNDS = 3003
    TRADE_RISK_LIMIT = 3004
    TRADE_ORDER_INVALID = 3005

    # 风控模块 4xxx
    RISK_CHECK_FAILED = 4001
    RISK_CONFIG_MISSING = 4002
    RISK_SERVICE_UNAVAILABLE = 4003

    # 策略模块 5xxx
    STRATEGY_NOT_FOUND = 5001
    STRATEGY_RUNTIME_ERROR = 5002
    STRATEGY_PARAM_INVALID = 5003
    STRATEGY_BLOCKED_BY_RISK = 5004

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
        if code == ErrorCode.SUCCESS:
            log.info(f"成功响应: {message}")
        else:
            log.error(f"失败响应: {code} - {message}")
        return resp

    @classmethod
    def success(cls, data: Optional[Any] = None, message: str = "success", trace_id: Optional[str] = None):
        return cls._base(ErrorCode.SUCCESS, message, data, trace_id)

    @classmethod
    def fail(cls, code: int | str, message: str, data: Optional[Any] = None, trace_id: Optional[str] = None):
        if isinstance(code, str):
            code = int(code)
        return cls._base(code, message, data, trace_id)
