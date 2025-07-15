#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos_v2
@FileName   : gateway_state
@Date       : 2025/7/15 23:16
@Author     : Donny
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 网关状态枚举
"""
from enum import Enum


class ConnectionState(Enum):
    """网关状态枚举"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    AUTHENTICATED = "authenticated"
    QUERYING_CONTRACTS = "querying_contracts"
    READY = "ready"
    ERROR = "error"
    LOGGED_IN = "logged_in"


class LoginState(Enum):
    """登录状态枚举"""
    LOGGED_OUT = "logged_out"
    LOGGING_IN = "logging_in"
    LOGGED_IN = "logged_in"
    LOGIN_FAILED = "login_failed"
