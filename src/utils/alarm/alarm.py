#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : alarm.py
@Date       : 2025/9/11 10:59
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 闹钟工具类
"""
from src.utils.log import get_logger


class Alarm(object):
    """
    闹钟工具类
    """
    def __init__(self) -> None:
        self.alarm_list = []
        self.strategy_id_list = []
        self.logger = get_logger(__class__.__name__)

    def get_strategy_id(self, alarm_time) -> list:
        """
        根据闹钟时间获取对应的所有策略ID

        :param alarm_time: 闹钟时间
        :return: 与指定闹钟时间关联的策略ID列表
        """
        ret = []
        for ala_time, strategy_id in zip(self.alarm_list, self.strategy_id_list):
            if ala_time == alarm_time:
                if ala_time not in ret:
                    ret.append(strategy_id)
        return ret

    def set_alarm(self, alarm_time, strategy_id=0) -> None:
        """
        设置闹钟时间和对应的策略ID

        :param alarm_time: 闹钟时间
        :param strategy_id: 策略ID，默认为0
        :return: None
        """
        rsp = self.get_strategy_id(alarm_time)
        if strategy_id not in rsp:
            self.alarm_list.append(alarm_time)
            self.strategy_id_list.append(strategy_id)

    def time_in_alarm(self, alarm_time) -> bool:
        """
        检查指定时间是否已设置闹钟

        :param alarm_time: 要检查的闹钟时间
        :return: 如果时间在闹钟列表中返回True，否则返回False
        """
        return alarm_time in self.alarm_list

    def clean(self) -> None:
        """
        清理所有闹钟设置

        :return: None
        """
        self.alarm_list = []
        self.strategy_id_list = []
        self.logger.info("已清理所有闹钟")