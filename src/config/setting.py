#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : setting
@Date       : 2025/6/2 10:32
@Author     : Donny
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: description
"""
from src.config.path import GlobalPath
from src.util.file_helper import load_yaml_file, load_json_file


def get_global_setting():
    global_yaml = load_yaml_file(GlobalPath.global_config_filepath)
    return global_yaml


def get_broker_setting():
    broker_json = load_json_file(GlobalPath.broker_config_filepath)
    return broker_json
