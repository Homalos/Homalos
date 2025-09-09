#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : trace_context.py
@Date       : 2025/9/9 22:35
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 全局上下文存 trace_id
"""
import contextvars
import uuid
from typing import Optional

# ===================== 定义全局 context var =====================
_trace_id_ctx: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("trace_id", default=None)

# ===================== TraceId 操作函数 =====================
def set_trace_id(trace_id: str = None) -> str:
    """
    设置当前上下文 trace_id（如果未传入则自动生成 UUID）
    :param trace_id: 可选，自定义 trace_id
    :return: 最终使用的 trace_id
    """
    if not trace_id:
        trace_id = str(uuid.uuid4())
    _trace_id_ctx.set(trace_id)
    return trace_id

def get_trace_id() -> Optional[str]:
    """
    获取当前上下文 trace_id
    :return: trace_id 或 None
    """
    return _trace_id_ctx.get()

def clear_trace_id():
    """
    清除当前上下文 trace_id
    """
    _trace_id_ctx.set(None)

# ===================== 装饰器辅助 =====================
def with_new_trace_id(func):
    """
    装饰器：自动生成新的 trace_id 并注入上下文
    用于事件分发/接口入口时，保证每个请求链路都有 trace_id
    """
    def wrapper(*args, **kwargs):
        set_trace_id()
        return func(*args, **kwargs)
    return wrapper
