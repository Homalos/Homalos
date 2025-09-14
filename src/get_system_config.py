#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : get_system_config.py
@Date       : 2025/9/13 14:08
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 获取系统配置
"""
from pathlib import Path

from src.constants import (
    CONFIG_DIR_NAME,
    SYSTEM_DEV_CONFIG_FILENAME,
    SYSTEM_PROD_CONFIG_FILENAME,
    SYSTEM_CONFIG_FILENAME
)
from src.utils.config_manager import ConfigManager
from src.utils.utility import load_yaml


# 获取配置目录路径
config_dir_path = Path(__file__).resolve().parent.parent / CONFIG_DIR_NAME

_system_config_path = config_dir_path / SYSTEM_CONFIG_FILENAME
_dev_config_path = config_dir_path / SYSTEM_DEV_CONFIG_FILENAME
_prod_config_path = config_dir_path / SYSTEM_PROD_CONFIG_FILENAME

# system_config = Config(str(_system_config_path))
system_config = load_yaml(_system_config_path)
# 项目名称
system_name = system_config.get("base").get("name")
system_describe = system_config.get("base").get("describe")
system_version = system_config.get("base").get("version")
timezone = system_config.get("base").get("timezone")
dev_mode = system_config.get("base").get("dev_mode")
dev_trading_hours = system_config.get("base.dev_trading_hours")

# 如果是开发模式，则使用开发配置文件
if dev_mode:
    extra_config = ConfigManager(str(_dev_config_path))
else:
    extra_config = ConfigManager(str(_prod_config_path))
# 数据目录名
data_dir_name = extra_config.get("base.data_dir")
# 日志目录名
log_dir_name = extra_config.get("base.log_dir")
flow_dir_name = extra_config.get("base.flow_dir")
timezone = extra_config.get("base.timezone")
trading_hours_check = extra_config.get("trading_hours.enable_check")
futures = extra_config.get("trading_hours.futures")


print(data_dir_name)
print(log_dir_name)
print(flow_dir_name)
print(timezone)
print(trading_hours_check)
print(futures)
