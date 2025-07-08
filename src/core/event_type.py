#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos_v2
@FileName   : event_type
@Date       : 2025/7/6 18:28
@Author     : Donny
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 事件类型
"""
from enum import Enum


class EventType(Enum):
    """
    定义不同事件的类型枚举。
    """
    TICK = "Tick."
    TRADE = "Trade."
    ORDER = "Order."
    POSITION = "Position."
    ACCOUNT = "Account."
    QUOTE = "Quote."
    CONTRACT = "Contract."
    LOG = "Log."
    TIMER = "Timer."
    SIGNAL = "Signal."
    SHUTDOWN = "Shutdown"
    MODULE_LOADED = "ModuleLoaded"
    MODULE_UNLOAD = "ModuleUnload"

    SERVICE_REGISTER = "ServiceRegister"
    SERVICE_UNREGISTER = "ServiceUnregister"
    SERVICE_HEART_BEAT = "ServiceHeartBeat"
    SERVICE_DISCOVERY = "ServiceDiscovery"
