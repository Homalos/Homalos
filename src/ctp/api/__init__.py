#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: homalos-ctp
@FileName   : __init__.py.py
@Date       : 2025/8/26 17:34
@Author     : Donny
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 初始化导入MdApi和TdApi，方便其它模块导入
"""
try:
    from .ctpmd import MdApi
except ImportError as e:
    print(f"Warning: Failed to import MdApi: {e}")
    MdApi = None

try:
    from .ctptd import TdApi
except ImportError as e:
    print(f"Warning: Failed to import TdApi: {e}")
    TdApi = None
