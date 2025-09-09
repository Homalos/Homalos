#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : test_response.py
@Date       : 2025/9/9 18:14
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: description
"""
from src.core.api_response import APIResponse, ErrorCode

# 成功返回
resp1 = APIResponse.success(data={"symbol": "rb2501", "price": 3580.5})
print(resp1)

# 失败返回（交易资金不足）
resp2 = APIResponse.fail(ErrorCode.TRADE_NO_FUNDS, "资金不足")
print(resp2)
