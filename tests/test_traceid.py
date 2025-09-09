#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : test_traceid.py
@Date       : 2025/9/9 23:56
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: traceid 测试用例
"""
from src.core.trace_context import get_trace_id, set_trace_id, clear_trace_id, with_new_trace_id
from src.utils.log import get_logger

log = get_logger("strategy")

def run_strategy():
    log.info(f"执行策略逻辑，trace_id={get_trace_id()}")

# 手动设置 trace_id
set_trace_id("abc-123")
log.info("收到下单请求")   # 自动打印 trace_id=abc-123
run_strategy()

# 清理
clear_trace_id()

# 自动生成 trace_id
@with_new_trace_id
def new_order():
    log.info("下单事件触发")  # 会自动带新 trace_id

new_order()

