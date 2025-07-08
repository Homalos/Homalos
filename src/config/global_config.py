#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos_v2
@FileName   : global_config
@Date       : 2025/6/27 16:03
@Author     : Donny
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 获取全局配置
"""
import os
import yaml

from src.config.path import GlobalPath


def get_global_config():
    """
    加载全局 YAML 文件配置。
    Loads a YAML file.
    """
    global_config_file_path = GlobalPath.global_config_filepath
    if not os.path.exists(global_config_file_path):
        return {}
    try:
        with open(global_config_file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        return data if data else {}
    except yaml.YAMLError as e:
        print(e)
        return {}
    except IOError as e:
        print(e)
        return {}


config_settings = get_global_config()
