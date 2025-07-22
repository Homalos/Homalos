#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos_v2
@FileName   : data_mapping
@Date       : 2025/7/18 00:30
@Author     : Donny
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 数据映射
"""
from src.config.constant import Exchange, Interval


# 交易所映射
EXCHANGE_MAPPING: dict[str, Exchange] = {
    "CZCE": Exchange.CZCE,
    "SHFE": Exchange.SHFE,
    "DCE": Exchange.DCE,
    "CFFEX": Exchange.CFFEX,
    "INE": Exchange.INE,
    "GFEX": Exchange.GFEX
}

# 时间周期映射(用于BarData)
INTERVAL_MAPPING: dict[int, Interval] = {
    1: Interval.MINUTE,
    3: Interval.THREE_MINUTE,
    5: Interval.FIVE_MINUTE,
    8: Interval.EIGHT_MINUTE,
    13: Interval.THIRTEEN_MINUTE,
    21: Interval.TWENTY_ONE_MINUTE,
    34: Interval.THIRTY_FOUR_MINUTE,
    55: Interval.FIFTY_FIVE_MINUTE,
    60: Interval.HOUR,
    89: Interval.EIGHTY_NINE_MINUTE,
    144: Interval.ONE_HUNDRED_FORTY_FOUR_MINUTE,
    1440: Interval.DAILY,
    10080: Interval.WEEKLY
}

