#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : setting
@Date       : 2025/6/2 10:32
@Author     : Donny
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 获取配置
"""
from src.config.path import GlobalPath
from src.util.file_helper import load_json_file


def get_broker_config():
    broker_json = load_json_file(GlobalPath.broker_config_filepath)
    return broker_json

def get_instrument_exchange_id():
    instrument_exchange_json = load_json_file(GlobalPath.instrument_exchange_id_filepath)
    return instrument_exchange_json

if __name__ == '__main__':
    # print(get_broker_config())
    print(get_instrument_exchange_id())

