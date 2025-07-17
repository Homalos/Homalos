#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos_v2
@FileName   : exchange_mapping
@Date       : 2025/7/18 00:30
@Author     : Donny
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 交易所映射
"""
from src.config.constant import Exchange


EXCHANGE_MAPPING: dict[str, Exchange] = {
    "CZCE": Exchange.CZCE,
    "SHFE": Exchange.SHFE,
    "DCE": Exchange.DCE,
    "CFFEX": Exchange.CFFEX,
    "INE": Exchange.INE,
    "GFEX": Exchange.GFEX
}
