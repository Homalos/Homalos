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
from typing import Any, Optional

from src.system_config import Config
from src.utils.config_manager import ConfigManager
from src.utils.log import get_logger

_logger = get_logger(__name__)


def get_enable_broker(cfg: ConfigManager) -> dict[str, Any]:
    """
    获取配置中启用的broker配置（向后兼容旧配置格式）
    
    优先级：
    1. 新配置格式：enable_md_broker / enable_td_broker
    2. 旧配置格式：enable_broker
    
    :param cfg: ConfigManager实例
    :return:
    """
    rsp_enable_broker: dict[str, Any] = {}

    # 获取根配置
    brokers_config = cfg.get("base", {})

    if not brokers_config:
        _logger.warning("请检查券商配置文件，base配置为空或不存在")
        return {}

    # 获取启用的broker名称（兼容新旧配置格式）
    # 优先使用新格式：enable_md_broker（因为是回退方案，使用MD配置即可）
    enable_broker_name: str = (
        brokers_config.get("enable_md_broker", "") or 
        brokers_config.get("enable_broker", "")
    )

    if not enable_broker_name:
        _logger.warning("未找到可用的broker名称，请检查base.enable_md_broker或base.enable_broker配置项")
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
    enable_broker_config: dict = all_brokers.get(enable_broker_name, [])

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
    加载启用的交易商配置信息（已弃用，请使用build_broker_config_from_account）

    Returns:
        dict - 经纪商配置信息
    """
    brokers_filepath = Config.brokers_filepath
    try:
        if not os.path.exists(brokers_filepath):
            _logger.error(f"经纪商配置文件不存在: {brokers_filepath}")
            return {}

        brokers_cfg_manager = ConfigManager(str(brokers_filepath))
        # 获取启用的broker名称和类型
        rsp_enable_broker = get_enable_broker(brokers_cfg_manager)
        _logger.info("经纪商配置加载成功")
        return rsp_enable_broker

    except Exception as e:
        _logger.exception(f"加载经纪商配置失败: {e}")
        return {}


def get_node_config(
    cfg_manager: ConfigManager,
    node_name: str
) -> Optional[dict[str, Any]]:
    """
    从brokers.yaml获取指定节点的配置
    
    Args:
        cfg_manager: ConfigManager实例
        node_name: 节点名称（如simnow、tts等）
    
    Returns:
        dict: 节点配置（包括broker_id, md_address, td_address等）
        None: 节点不存在
    """
    try:
        base_config = cfg_manager.get("base", {})
        all_brokers = base_config.get("brokers", {})
        
        if node_name not in all_brokers:
            _logger.warning(f"节点 '{node_name}' 在brokers配置中不存在")
            return None
        
        node_config = all_brokers.get(node_name, {})
        if not node_config:
            _logger.warning(f"节点 '{node_name}' 配置为空")
            return None
        
        return node_config
    except Exception as e:
        _logger.exception(f"获取节点配置失败: {e}")
        return None


def build_broker_config_from_account(
    account_data: dict[str, Any],
    decrypted_password: str
) -> dict[str, Any]:
    """
    根据数据库账户信息和brokers.yaml节点信息构建完整的broker配置
    
    安全设计：
    - 敏感信息（user_id, password, app_id, auth_code）从数据库获取
    - 节点信息（md_address, td_address等）从brokers.yaml获取
    - 支持独立的行情和交易服务器节点
    
    Args:
        account_data: 数据库中的账户信息
            - broker_id: 券商ID
            - account_id: 用户账号
            - app_id: 应用ID（可选）
            - auth_code: 授权码（可选）
            - md_node_name: 行情服务器节点名称（可选，默认使用broker_key）
            - td_node_name: 交易服务器节点名称（可选，默认使用broker_key）
            - broker_key: 默认节点名称（向后兼容）
        decrypted_password: 解密后的密码
    
    Returns:
        dict: 完整的broker配置，格式：
        {
            "broker_name": "节点名称",
            "broker_type": "api类型",
            "md_config": {...},  # 行情服务器配置
            "td_config": {...}   # 交易服务器配置
        }
    
    Raises:
        ValueError: 配置不完整或节点不存在
    """
    try:
        brokers_filepath = Config.brokers_filepath
        if not os.path.exists(brokers_filepath):
            raise ValueError(f"经纪商配置文件不存在: {brokers_filepath}")
        
        cfg_manager = ConfigManager(str(brokers_filepath))
        
        # 获取节点名称
        md_node_name = account_data.get("md_node_name") or account_data.get("broker_key")
        td_node_name = account_data.get("td_node_name") or account_data.get("broker_key")
        
        if not md_node_name or not td_node_name:
            raise ValueError("账户配置缺少节点名称信息")
        
        # 获取行情节点配置
        md_node_config = get_node_config(cfg_manager, md_node_name)
        if not md_node_config:
            raise ValueError(f"行情节点 '{md_node_name}' 不存在")
        
        # 获取交易节点配置
        td_node_config = get_node_config(cfg_manager, td_node_name)
        if not td_node_config:
            raise ValueError(f"交易节点 '{td_node_name}' 不存在")
        
        # 构建行情服务器配置（节点信息 + 账户信息）
        md_config = {
            "broker_id": account_data.get("broker_id"),
            "md_address": md_node_config.get("md_address"),
            "user_id": account_data.get("account_id"),
            "password": decrypted_password,
            "app_id": account_data.get("app_id") or md_node_config.get("app_id", ""),
            "auth_code": account_data.get("auth_code") or md_node_config.get("auth_code", ""),
            "product_info": md_node_config.get("product_info", ""),
            "api_type": md_node_config.get("api_type", "ctp"),
        }
        
        # 构建交易服务器配置（节点信息 + 账户信息）
        td_config = {
            "broker_id": account_data.get("broker_id"),
            "td_address": td_node_config.get("td_address"),
            "user_id": account_data.get("account_id"),
            "password": decrypted_password,
            "app_id": account_data.get("app_id") or td_node_config.get("app_id", ""),
            "auth_code": account_data.get("auth_code") or td_node_config.get("auth_code", ""),
            "product_info": td_node_config.get("product_info", ""),
            "api_type": td_node_config.get("api_type", "ctp"),
        }
        
        # 验证配置完整性
        required_md_fields = ["broker_id", "md_address", "user_id", "password"]
        required_td_fields = ["broker_id", "td_address", "user_id", "password"]
        
        for field in required_md_fields:
            if not md_config.get(field):
                raise ValueError(f"行情配置缺少必需字段: {field}")
        
        for field in required_td_fields:
            if not td_config.get(field):
                raise ValueError(f"交易配置缺少必需字段: {field}")
        
        # 返回完整配置
        result = {
            "broker_name": f"{md_node_name}/{td_node_name}",
            "broker_type": md_config.get("api_type", "ctp"),
            "md_config": md_config,
            "td_config": td_config,
            # 向后兼容：合并后的配置（用于旧代码）
            "broker_config": {**md_config, **td_config}
        }
        
        _logger.info(
            f"成功构建broker配置: "
            f"行情节点={md_node_name}, 交易节点={td_node_name}, "
            f"账户={account_data.get('account_id')}"
        )
        
        return result
        
    except Exception as e:
        _logger.exception(f"构建broker配置失败: {e}")
        raise ValueError(f"构建broker配置失败: {str(e)}")
