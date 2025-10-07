#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : pool_config.py
@Date       : 2025/10/7 21:13
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 线程池常量
"""
from src import constants
from src.constants import RES_USAGE_DIR_NAME
from src.utils.get_path import get_path_ins

# 文件名称是否按照真实时间来
file_time_is_true = constants.file_time_is_true

# 记录文件中时间是否按照真实时间来
content_time_is_true = constants.content_time_is_true

# 保存位置
save_path = str(get_path_ins.get_data_dir() / RES_USAGE_DIR_NAME)

# 表头
pool_column = constants.pool_column

# 在程序首次运行时是否抹除今天之前的记录
is_first = constants.is_first
