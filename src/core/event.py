#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : event.py
@Date       : 2025/9/8 09:54
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 事件类, 封装事件数据
"""
import uuid
from typing import Optional, Any


class Event:
    def __init__(self, event_type, data: Any = None, source: Optional[str] = None, trace_id: Optional[str] = None):
        self.event_type: str = event_type    # 事件类型
        self.data: Any = data                # 事件数据
        self.source: str = source or "unknown"          # 事件来源，如果没有提供来源，则默认为"unknown"
        self.trace_id = trace_id or str(uuid.uuid4())   # 事件追踪ID，如果没有提供追踪ID，则生成一个新的UUID

    def __repr__(self):
        """
        返回事件对象的字符串表示形式。
        Args:
            无。
        Returns:
            str: 事件对象的字符串表示形式，包含事件类型、事件源和追踪ID。
        """
        return f"Event(event_type={self.event_type}, source={self.source}, trace_id={self.trace_id})"


class EventType:
    """事件类型常量"""

    EVENT_BUS_SHUTDOWN = "event_bus.shutdown"
