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
    def __init__(self,
                 event_type: str,
                 payload: Optional[Any] = None,
                 source: Optional[str] = None,
                 trace_id: Optional[str] = None
                 ):
        self.event_type: str = event_type    # 事件类型
        self.payload: Any = payload                # 事件数据
        self.source: str = source or "unknown"          # 事件来源，如果没有提供来源，则默认为"unknown"
        self.trace_id: str = trace_id or str(uuid.uuid4())   # 事件追踪ID，如果没有提供追踪ID，则生成一个新的UUID

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
    EVENT_BUS_SHUTDOWN = "event_bus.shutdown"  # 停止事件

    TIMER = "timer"  # 定时器事件

    TICK = "market.tick"  # Tick事件

    BAR = "market.bar"  # K线事件

    ORDER = "order"  # 订单事件

    POSITION = "position"  # 持仓事件

    ACCOUNT = "account"  # 账户事件

    CONTRACT = "contract"  # 合约事件

    # 行情接口事件
    MD_GATEWAY_CONNECT = "md_gateway.connect"  # 行情接口连接事件(成功/断开)

    MD_GATEWAY_LOGIN = "md_gateway.login"  # 行情登录

    TD_GATEWAY_LOGIN = "td_gateway.login"  # 交易登录

    TD_GATEWAY_READY = "td_gateway.ready"  # 交易网关就绪

    TD_QRY_INS = "td.qry.ins"  # 交易网关查询合约事件

    TD_CONFIRM_SUCCESS = "td.confirm.success"  # 结算单确认成功

    TD_ALREADY_CONFIRMED = "td.already.confirmed"  # 结算单已经确认过事件 already

    DATA_CENTER_START = "data_center.start"  # 数据中心启动事件

    DATA_CENTER_STOP = "data_center.stop"  # 数据中心停止事件

    DATA_CENTER_QRY_INS = "data_center.qry_ins"  # 数据中心查询合约事件

    # INS_FILE_UPDATED = "ins_file.updated"  # 合约文件更新事件




def create_event(event_type: str, payload: Any = None, source: str = "unknown") -> Event:
    """
    创建一个默认的事件对象。
    Args:
        event_type (str): 事件类型。
        payload (Any, optional): 事件数据。默认为空。
        source (str): 事件来源，如果没有提供来源，则默认为"unknown"
    Returns:
        Event: 默认事件对象。
    """
    return Event(event_type=event_type, payload=payload, source=source)
