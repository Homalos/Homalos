#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : constants.py
@Date       : 2025/9/9 17:10
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 全局常量
"""
from typing import Optional, Any, TYPE_CHECKING



class Const:
    # 交易日，全局变量
    trading_day: str = None

# ================== 项目中目录名称 ==================
# PROJECT_NAME = "Homalos"  # 项目名称
#
# LOG_DIR_NAME = "log"  # 日志目录名

DATA_DIR_NAME = "data"  # 数据目录名

TICK_DIR_NAME = "tick"  # TICK数据子目录名

CONFIG_DIR_NAME = "config"  # 配置目录名

# ================== 项目中文件名称 ==================
SYSTEM_CONFIG_FILENAME = "system.yaml"

SYSTEM_DEV_CONFIG_FILENAME = "extra.dev.yaml"

SYSTEM_PROD_CONFIG_FILENAME = "extra.prod.yaml"

BROKERS_FILENAME = "brokers.yaml"  # 多源服务器节点配置文件名

DATA_CENTER_CONFIG_FILENAME = "data_center.yaml"

LOG_CONFIG_FILENAME = "log_config.yaml"  # 全局日志配置文件名

INSTRUMENT_EXCHANGE_FILENAME = "instrument_exchange.json"  # 期货合约与交易所映射信息文件名

PRODUCT_INFO_FILENAME = "product_info.ini"  # 合约乘数及手续费信息文件名

HOLIDAY_FILENAME = "holidays.json"  # 节假日文件名称

# ================== 代码中常量 ==================
filename_format = "%Y%m%d"  # 日志文件名格式

log_time_format = "%Y-%m-%d %H:%M:%S.%f"  # 日志文件中时间格式

print_time_format = "%Y-%m-%d %H:%M:%S.%f"  # 控制台打印的时间格式

strategy_map: dict[str, Any] = {}

# ================== 全局线程池已移除 ==================
# 原全局线程池存在竞态条件，已用ThreadPoolExecutor替换

# tick合成K线系统
tick_to_kline_sys = None
