#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : broker_service.py
@Date       : 2025/10/13
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 券商配置服务
"""
from typing import Any

from ruamel.yaml import YAML

from src.constants import BROKERS_FILENAME
from src.utils.get_path import get_path_ins
from src.utils.log import get_logger

logger = get_logger(__name__)


class BrokerService:
    """券商配置服务"""
    
    _CONFIG_FILE = get_path_ins.get_config_dir() / BROKERS_FILENAME
    
    @classmethod
    def get_broker_list(cls) -> list[dict[str, str]]:
        """
        获取可用的券商列表
        
        Returns:
            [{"broker_key": "simnow", "broker_id": "9999", "name": "SimNow模拟", "description": "..."}]
        """
        try:
            yaml = YAML()
            with open(cls._CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = yaml.load(f) or {}
            
            brokers_config = config.get('base', {}).get('brokers', {})
            
            broker_list = []
            broker_names = {
                'simnow': 'SimNow模拟（日盘）',
                'simnow7x24': 'SimNow模拟（7x24）',
                'tts': 'TTS模拟（日盘）',
                'tts7x24': 'TTS模拟（7x24）',
                'guofu': '国富期货-主席',
                'everbright': '光大期货-主席'
            }
            
            for key, broker_config in brokers_config.items():
                broker_list.append({
                    'broker_key': key,  # 使用配置key作为唯一标识符
                    'broker_id': broker_config.get('broker_id', '9999'),
                    'name': broker_names.get(key, key),
                    'description': broker_config.get('md_address', '')  # 只显示地址，去掉broker_id
                })
            
            logger.info(f"加载券商列表成功: {len(broker_list)} 个券商")
            return broker_list
            
        except Exception as e:
            logger.error(f"读取券商配置失败: {e}")
            return []
    
    @classmethod
    def get_broker_config(cls, broker_key: str) -> dict[str, Any]:
        """
        获取指定券商的完整配置
        
        Args:
            broker_key: 券商配置key（如 simnow, tts等）
            
        Returns:
            券商配置字典
        """
        try:
            yaml = YAML()
            with open(cls._CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = yaml.load(f) or {}
            
            brokers_config = config.get('base', {}).get('brokers', {})
            return brokers_config.get(broker_key, {})
            
        except Exception as e:
            logger.error(f"读取券商配置失败: {e}")
            return {}

