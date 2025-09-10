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
from src.utils.path import get_path_ins

# ================== 项目中目录名称 ==================
PROJECT_NAME = "Homalos"  # 项目名称

LOG_DIR_NAME = "log"  # 日志目录名

DATA_DIR_NAME = "data"  # 数据目录名

CONFIG_DIR_NAME = "config"  # 配置目录名

# ================== 项目中文件名称 ==================
BROKERS_FILENAME = "brokers.yaml"  # 多源服务器节点配置文件名

LOG_CONFIG_FILENAME = "log_config.yaml"  # 全局日志配置文件名

SYSTEM_DEV_CONFIG_FILENAME = "system.dev.yaml"

SYSTEM_PROD_CONFIG_FILENAME = "system.prod.yaml"

INSTRUMENT_EXCHANGE_FILENAME = "instrument_exchange.json"  # 期货合约与交易所映射信息文件名

PRODUCT_INFO_FILENAME = "product_info.ini"  # 合约乘数及手续费信息文件名

HOLIDAY_FILENAME = "holidays.json"  # 节假日文件名称


# ================== 代码中常量 ==================
file_format = "%Y%m%d"  # 日志文件名格式

log_time_format = "%Y-%m-%d %H:%M:%S.%f"  # 日志文件中时间格式

print_time_format = "%Y-%m-%d %H:%M:%S.%f"  # 控制台打印的时间格式

# ================== 路径常量 ==================
CONFIG_DIR_PATH = get_path_ins.get_config_dir()

BROKERS_FILEPATH = CONFIG_DIR_PATH / BROKERS_FILENAME

LOG_CONFIG_FILEPATH = CONFIG_DIR_PATH / LOG_CONFIG_FILENAME

SYSTEM_DEV_CONFIG_FILEPATH = CONFIG_DIR_PATH / SYSTEM_DEV_CONFIG_FILENAME

SYSTEM_PROD_CONFIG_FILEPATH = CONFIG_DIR_PATH / SYSTEM_PROD_CONFIG_FILENAME

INSTRUMENT_EXCHANGE_FILEPATH = CONFIG_DIR_PATH / INSTRUMENT_EXCHANGE_FILENAME

PRODUCT_INFO_FILEPATH = CONFIG_DIR_PATH / PRODUCT_INFO_FILENAME

HOLIDAY_FILEPATH = CONFIG_DIR_PATH / HOLIDAY_FILENAME
