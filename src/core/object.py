#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : object.py
@Date       : 2025/9/8 17:34
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 交易平台中用于一般交易功能的基本数据结构。
"""
from dataclasses import dataclass, field

from datetime import datetime as Datetime

from src.core.constants import Exchange


@dataclass
class BaseData:
    """
    任何数据对象都需要一个名称作为来源，并且应该继承基础数据。

    Any data object needs a name to originate from and should inherit from a base data.
    """
    source_name: str = ""
    extra: dict | None = field(default=None, init=False)


@dataclass
class TickData(BaseData):
    """
    报价数据包含以下信息：
        * 市场最新交易
        * 订单簿快照
        * 日内市场统计数据。
    """
    symbol: str = None
    exchange: Exchange = None


@dataclass
class BarData(BaseData):
    """
    特定交易周期的蜡烛图数据。

    Candlestick bar data of a certain trading period.
    """
    symbol: str = None
    exchange: Exchange = None
