#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: homalos-ctp
@FileName   : custom_constant.py
@Date       : 2025/9/5 14:26
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: CTP自定义常量
    CTP custom constants
"""


class CtpConst(object):

    # reason mapping
    REASON_MAPPING = {
        0x1001: "网络读失败",
        0x1002: "网络写失败",
        0x2001: "接收心跳超时",
        0x2002: "发送心跳失败",
        0x2003: "收到错误报文"
    }
