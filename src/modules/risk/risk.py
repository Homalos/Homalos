#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : risk.py
@Date       : 2025/9/10 16:48
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 风控模块
"""
from src.core.event_bus import EventBus
from src.utils.log import get_logger


class Risk:

    def __init__(self, event_bus: EventBus):
        self.event_bus: EventBus = event_bus
        self.logger = get_logger(context="Risk")
    def risk_check(self, order: dict):
        logger = get_logger(context="Risk")
        logger.info(f"风控检查订单: {order}")
        # 假设通过，转发给网关
        self.event_bus.publish("gateway", order)
