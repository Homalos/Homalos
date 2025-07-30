#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos_v2
@FileName   : gateway_helper
@Date       : 2025/7/16 18:00
@Author     : Donny
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 网关辅助
"""
from typing import Dict, Any, Optional

from src.config.config_manager import ConfigManager
from src.core.logger import get_logger


logger = get_logger(__name__)


# 网关类映射
GATEWAY_CLASSES: Dict[str, Dict[str, Any]] = {}

# 尝试导入CTP网关
try:
    from src.ctp.gateway.market_data_gateway import MarketDataGateway as CtpMarketDataGateway
    from src.ctp.gateway.order_trading_gateway import OrderTradingGateway as CtpOrderTradingGateway
    CTP_AVAILABLE = True
    GATEWAY_CLASSES['ctp'] = {
        'market_data': CtpMarketDataGateway,
        'order_trading': CtpOrderTradingGateway,
        'available': True
    }
except ImportError:
    CtpMarketDataGateway = None
    CtpOrderTradingGateway = None
    CTP_AVAILABLE = False
    GATEWAY_CLASSES['ctp'] = {
        'market_data': None,
        'order_trading': None,
        'available': False
    }

# 尝试导入TTS网关
try:
    from src.tts.gateway.market_data_gateway import MarketDataGateway as TtsMarketDataGateway
    from src.tts.gateway.order_trading_gateway import OrderTradingGateway as TtsOrderTradingGateway
    TTS_AVAILABLE = True
    GATEWAY_CLASSES['tts'] = {
        'market_data': TtsMarketDataGateway,
        'order_trading': TtsOrderTradingGateway,
        'available': True
    }
except ImportError:
    TtsMarketDataGateway = None
    TtsOrderTradingGateway = None
    TTS_AVAILABLE = False
    GATEWAY_CLASSES['tts'] = {
        'market_data': None,
        'order_trading': None,
        'available': False
    }


def get_enabled_gateways(config: Optional[ConfigManager]) -> Dict[str, Dict[str, Any]]:
    """获取配置中启用的网关"""
    enabled_gateways = {}

    if not config:
        return enabled_gateways

    # 获取启用的broker名称
    enabled_broker = config.get("gateway.enabled_broker", "")
    
    if not enabled_broker:
        logger.warning("未找到gateway.enabled_broker配置")
        return enabled_gateways

    # 获取网关配置中的brokers
    brokers_config = config.get("gateway.brokers", {})
    
    if not brokers_config:
        logger.warning("未找到gateway.brokers配置")
        return enabled_gateways

    # 检查启用的broker是否存在于配置中
    if enabled_broker not in brokers_config:
        logger.error(f"启用的broker '{enabled_broker}' 在brokers配置中不存在")
        return enabled_gateways

    # 获取启用broker的配置
    broker_config = brokers_config[enabled_broker]
    
    if not broker_config:
        logger.warning(f"启用的broker '{enabled_broker}' 配置为空")
        return enabled_gateways

    # 确定网关类型（simnow和simnow7x24都使用ctp类，tts和tts7x24使用tts类）
    if enabled_broker in ['simnow', 'simnow7x24']:
        gateway_type = 'ctp'
    elif enabled_broker in ['tts', 'tts7x24']:
        gateway_type = 'tts'
    elif enabled_broker == 'real':
        gateway_type = 'ctp'  # 实盘通常使用CTP
    else:
        gateway_type = 'ctp'  # 默认使用CTP类型

    # 检查网关是否可用
    if GATEWAY_CLASSES.get(gateway_type, {}).get('available', False):
        enabled_gateways[enabled_broker] = {
            'config': broker_config,
            'type': gateway_type,
            'classes': GATEWAY_CLASSES[gateway_type]
        }
        logger.info(f"启用网关: {enabled_broker} (类型: {gateway_type})")
    else:
        logger.warning(f"网关 {enabled_broker} 已配置但类型 {gateway_type} 不可用")

    return enabled_gateways


if __name__ == '__main__':
    config_file: str = "D:\\Project\\PycharmProjects\\Homalos_v2\\config\\system.yaml"
    get_config = ConfigManager(config_file)
    enabled_gateways = get_enabled_gateways(get_config)
    print(enabled_gateways)
    # 初始化每个启用的网关
    for gateway_key, gateway_info in enabled_gateways.items():
        gateway_config = gateway_info['config']
        gateway_type = gateway_info['type']
        gateway_classes = gateway_info['classes']

        print(f"gateway_key: {gateway_key}")
        print(f"gateway_config: {gateway_config}")
        print(f"gateway_type: {gateway_type}")
        print(f"gateway_classes: {gateway_classes}")

