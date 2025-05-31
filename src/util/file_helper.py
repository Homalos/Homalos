#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : file_helper
@Date       : 2025/5/28 00:02
@Author     : Donny
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: description
"""
import configparser
import json
import os
from typing import Dict, Any, Tuple

import yaml

from src.util.logger import logger, setup_logging, INFO
from src.util.i18n import _



setup_logging(service_name=__name__, level=INFO)


def load_yaml_file(file_path: str) -> Dict[str, Any]:
    """
    加载 YAML 文件。

    Loads a YAML file.
    """
    if not os.path.exists(file_path):
        logger.error("Configuration file not found: {}".format(file_path))
        return {}
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        return data if data else {}
    except yaml.YAMLError as e:
        logger.error("Unable to parse YAML file {}: {}".format(file_path, e))
        return {}
    except IOError as e:
        logger.error("Unable to read file {}: {}".format(file_path, e))
        return {}

def load_json_file(file_path: str) -> Dict[str, Any]:
    """
    加载 JSON 文件。

    Loads a JSON file.
    """
    if not os.path.exists(file_path):
        logger.info(_("未找到可选的 JSON 配置文件：{}").format(file_path))
        return {}
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data if data else {}
    except json.JSONDecodeError as e:
        logger.error(_("无法解析 JSON 文件 {}: {}").format(file_path, e))
        return {}
    except IOError as e:
        logger.error(_("无法读取文件 {}: {}").format(file_path, e))
        return {}


def write_json_file(file_path: str, data: Dict[str, Any]) -> None:
    """
    将数据写入 JSON 文件。

    Writes the given data into a JSON file at the specified path.
    """
    try:
        with open(file_path, 'w', newline='\n', encoding='utf-8') as f:
            file_data = json.dumps(data, indent=4, ensure_ascii=False)
            f.write(file_data)
    except IOError as e:
        logger.error(_("无法写入文件 {}: {}").format(file_path, e))


def load_ini_file(file_path: str):
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
    parser = configparser.ConfigParser()
    # 检查文件是否存在，如果不存在则创建一个空的ini文件
    if not os.path.exists(file_path):
        with open(file_path, 'w', encoding='utf-8') as f:
            # 可以选择写入一些默认的空section或者注释，如果需要的话
            # f.write("# Empty product_info.ini created by system\n")
            pass  # 创建一个空文件
    parser.read(file_path, encoding='utf-8')

    return parser

