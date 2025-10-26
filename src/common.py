#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : common.py
@Date       : 2025/10/17 17:10
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 业务公共方法
"""
import os
from typing import Any

from src.system_config import Config
from src.utils.config_manager import ConfigManager
from src.utils.log import get_logger

_logger = get_logger(__name__)


def get_enable_broker(cfg: ConfigManager) -> dict[str, Any]:
    """
    获取配置中启用的broker配置
    :param cfg: ConfigManager实例
    :return:
    """
    rsp_enable_broker: dict[str, Any] = {}

    # 获取根配置
    brokers_config = cfg.get("base", {})

    if not brokers_config:
        _logger.warning("请检查券商配置文件，base配置为空或不存在")
        return {}

    # 获取启用的broker名称
    enable_broker_name: str = brokers_config.get("enable_broker", "")

    if not enable_broker_name:
        _logger.warning("未找到可用的broker名称，请检查base.enable_broker配置项")
        return {}

    # 获取启用的broker配置
    all_brokers: dict = brokers_config.get("brokers", {})

    if not all_brokers:
        _logger.warning("未找到brokers配置，请检查base.brokers配置项")
        return {}

    # 检查启用的broker名称是否存在于brokers配置中
    if enable_broker_name not in all_brokers:
        _logger.warning(f"启用的broker '{enable_broker_name}' 在brokers配置中不存在，请检查配置")
        return {}

    # 获取启用broker的配置
    enable_broker_config: dict = all_brokers.get(enable_broker_name)

    if not enable_broker_config:
        _logger.warning(f"启用的broker '{enable_broker_name}' 配置为空，请检查具体配置项")
        return {}

    # 获取broker类型（从api_type字段）
    broker_type = enable_broker_config.get("api_type", "")
    if not broker_type:
        _logger.warning(f"启用的broker '{enable_broker_name}' 缺少api_type配置")
        return {}

    rsp_enable_broker["broker_name"] = enable_broker_name
    rsp_enable_broker["broker_type"] = broker_type
    rsp_enable_broker["broker_config"] = enable_broker_config

    return rsp_enable_broker

def load_broker_config() -> dict[str, Any]:
    """
    加载启用的交易商配置信息

    Returns:
        dict - 经纪商配置信息
    """
    brokers_filepath = Config.brokers_filepath
    try:
        if not os.path.exists(brokers_filepath):
            _logger.error(f"经纪商配置文件不存在: {brokers_filepath}")
            return {}

        brokers_cfg_manager = ConfigManager(brokers_filepath)
        # 获取启用的broker名称和类型
        rsp_enable_broker = get_enable_broker(brokers_cfg_manager)
        _logger.info(f"经纪商配置加载成功")
        return rsp_enable_broker

    except Exception as e:
        _logger.exception(f"加载经纪商配置失败: {e}")
        return {}
