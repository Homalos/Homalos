#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : utility.py
@Date       : 2025/9/8 15:54
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 公用的工具
"""
import json
import os
import time
from typing import Dict, Any

import yaml

from src.utils.log import get_logger

_logger = get_logger(__name__)

def load_json_file(file_path: str) -> Dict[str, Any]:
    """
    加载 JSON 文件。

    Loads a JSON file.
    """
    if not os.path.exists(file_path):
        _logger.info("未找到可选的 JSON 配置文件：{}".format(file_path))
        return {}
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except json.JSONDecodeError as e:
        _logger.error("无法解析 JSON 文件 {}: {}".format(file_path, e))
        return {}
    except IOError as e:
        _logger.error("无法读取文件 {}: {}".format(file_path, e))
        return {}


def load_config(config_path: str) -> dict:
    """加载配置文件"""
    if not os.path.exists(config_path):
        _logger.error(f"未找到配置文件: {config_path}")
        raise FileNotFoundError(f"配置文件不存在: {config_path}")
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def prepare_address(address: str) -> str:
    """
    如果没有协议，则帮助程序会在前面添加 tcp:// 作为前缀。

    If there is no protocol, the helper prefixes it with tcp:// .
    :param address: 行情服务器地址 Market server address
    :return: 返回带协议的服务器地址 Returns the server address with protocol
    """
    if not any(address.startswith(scheme) for scheme in ["tcp://", "ssl://", "socks://"]):
        return "tcp://" + address
    return address

