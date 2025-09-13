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
import configparser
import json
import os
import re
from typing import Any

import yaml

from src.utils.log import get_logger

_logger = get_logger(__name__)


def load_json(file_path: str) -> dict[str, Any]:
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

def write_json(file_path: str, data: dict[str, Any]) -> None:
    """
    将数据写入 JSON 文件。

    Writes the given data into a JSON file at the specified path.
    """
    try:
        with open(file_path, 'w', newline='\n', encoding='utf-8') as f:
            f.write(json.dumps(data, indent=4, ensure_ascii=False))
    except IOError as e:
        _logger.error("无法写入文件 {}: {}".format(file_path, e))

def load_ini(file_path: str) -> configparser:
    """
    从指定路径加载INI配置文件。

    Args:
        file_path (str): INI配置文件的路径。

    Returns:
        ConfigParser: 加载的INI配置文件对象。

    说明：
        如果指定的文件不存在，则会创建一个空的INI文件。
        如果文件存在，则读取文件内容并返回一个ConfigParser对象。
        在创建空文件时，可以选择写入一些默认的空section或者注释，如果需要的话。

    """
    config_parser: configparser = configparser.ConfigParser()
    # 检查文件是否存在，如果不存在则创建一个空的ini文件
    if not os.path.exists(file_path):
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("")
    config_parser.read(file_path, encoding='utf-8')

    return config_parser

def write_ini(config_parser: configparser, file_path: str) -> None:
    """
    将配置写入ini文件。

    Args:
        config_parser (ConfigParser): 配置文件对象。
        file_path (str): 要写入的ini文件路径。

    """
    config_parser.write(open(file_path, "w", encoding='utf-8'))

def load_yaml(config_path: str) -> dict:
    """
    加载 yaml 配置文件，单纯加载 yaml 文件后直接返回 dict 数据
    如果需要更强大的配置加载功能请使用 utils/config_manager.py 中的配置管理，支持热加载
    :param config_path:
    :return:
    """
    if not os.path.exists(config_path):
        _logger.error(f"未找到配置文件: {config_path}")
        return {}
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except (yaml.YAMLError, IOError):
        # 如果配置文件解析失败，返回默认配置
        return {}

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

def del_num(content) -> str:
    """
    删除字符串中的所有数字。

    Args:
        content (str): 需要删除数字的字符串。

    Returns:
        str: 删除数字后的字符串。
    """
    return re.sub(r'\d', '', content)


def get_enable_broker(brokers_config: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """
    获取配置中启用的broker配置
    :param brokers_config:
    :return:
    """
    rsp_enable_broker: dict[str, Any] = {}

    if not brokers_config:
        return {}

    # 获取启用的broker名称
    enable_broker_name: str = brokers_config.get("base", {}).get("enable_broker", "")

    if not enable_broker_name:
        _logger.warning("未找到可用的broker名称")
        return {}

    # 获取启用的broker配置
    all_brokers: dict = brokers_config.get("base", {}).get("brokers", {})

    if not all_brokers:
        _logger.warning("未找到brokers配置")
        return {}

    # 检查启用的broker名称是否存在于brokers配置中
    if enable_broker_name not in all_brokers:
        _logger.error(f"启用的broker '{enable_broker_name}' 在brokers配置中不存在")
        return {}

    # 获取启用broker的配置
    enable_broker_config = all_brokers.get(enable_broker_name)

    if not enable_broker_config:
        _logger.warning(f"启用的broker '{enable_broker_name}' 配置为空")
        return {}

    # 确定broker类型（simnow和simnow7x24都使用ctp类，tts和tts7x24使用tts类）
    if enable_broker_name in ['simnow', 'simnow7x24']:
        enable_broker_type = 'ctp'
    elif enable_broker_name in ['tts', 'tts7x24']:
        enable_broker_type = 'tts'
    elif enable_broker_name == 'real':
        enable_broker_type = 'ctp'  # 实盘通常使用CTP
    else:
        enable_broker_type = 'ctp'  # 默认使用CTP类型

    rsp_enable_broker["broker_name"] = enable_broker_name
    rsp_enable_broker["broker_type"] = enable_broker_type
    rsp_enable_broker["broker_config"] = enable_broker_config

    return rsp_enable_broker

