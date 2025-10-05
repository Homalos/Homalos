#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : data_center_const.py
@Date       : 2025/9/29 10:24
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: description
"""
import datetime

from src.constants import DATA_CENTER_CONFIG_FILENAME
from src.utils.get_path import get_path_ins
from src.utils.utility import load_yaml


"""
数据中心常量类
"""
kline_times: list = []
debug: bool = False

dc_config_filepath: str = str(get_path_ins.get_config_dir() / DATA_CENTER_CONFIG_FILENAME)
dc_config = load_yaml(dc_config_filepath)
base_config = dc_config.get("base", {})

if base_config:
    kline_times: list = base_config.get("alarm_schedule", {}).get("kline_times", [])
    debug: bool = base_config.get("debug", False)

if debug:
    now_time = datetime.datetime.now()
    t_kline_time = now_time + datetime.timedelta(seconds=60)
    t_kline = t_kline_time.time().strftime('%H:%M')
    kline_times.append(t_kline)


if __name__ == '__main__':
    print(kline_times)
