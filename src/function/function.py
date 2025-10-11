#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : function.py
@Date       : 2025/9/15 14:05
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 业务函数
"""
import time
from typing import Optional

from src.api.notify import notify_ins
from src.api.thread_pool import thread_pool_ins
from src.function.func import get_ip_port, is_open
from src.modules.gateway.market_gateway import MarketGateway
from src.modules.gateway.trader_gateway import TraderGateway
from src.strategy import strategy_pool_ins
from src.utils.alarm import Alarm
from src.utils.log import get_logger
from src.utils.time import time_module_ins


class Function(object):

    def __init__(self):
        self.logger = get_logger(__name__)
        self.alarm_ins = Alarm()
        self.is_open: bool = False
        self.market_gateway: Optional[MarketGateway] = None  # 行情网关
        self.trader_gateway: Optional[TraderGateway] = None  # 交易网关
        self.broker_config: dict[str, dict] = {}  # 服务器节点配置信息
        self.md_login_status: bool = False  # 行情网关登录状态
        self.td_login_status: bool = False  # 交易网关登录状态
        self.is_login_status: bool = False  # 登录状态
        self.td_is_confirmed: bool = False  # 是否确认过了结算单

    def check_alarm(self) -> None:
        """
        检查是否存在闹钟

        Returns:

        """
        time_now = time_module_ins.now().strftime('%H:%M')

        # 检查是否存在用户设定闹钟
        if self.alarm_ins.time_in_alarm(time_now):
            strategy_id_list: list[str] = self.alarm_ins.get_strategy_ids(time_now)
            for strategy_id in strategy_id_list:
                for ins_id in strategy_pool_ins.strategy_map[strategy_id].sub_ins_id:
                    thread_pool_ins.submit(
                        strategy_pool_ins.strategy_map[strategy_id].specific_strategy_map[ins_id].on_alarm)


