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

    # 检查所有可能的网关配置
    gateway_configs = {
        'simnow': config.get("gateway.simnow", {}),
        'simnow7x24': config.get("gateway.simnow7x24", {}),
        'tts': config.get("gateway.tts", {}),
        'tts7x24': config.get("gateway.tts7x24", {})
    }

    for gateway_key, gateway_config in gateway_configs.items():
        if gateway_config.get("enabled", False):
            # 确定网关类型（simnow和simnow7x24都使用ctp类，tts和tts7x24使用tts类）
            if gateway_key in ['simnow', 'simnow7x24']:
                gateway_type = 'ctp'
            elif gateway_key in ['tts', 'tts7x24']:
                gateway_type = 'tts'
            else:
                gateway_type = gateway_key

            # 检查网关是否可用
            if GATEWAY_CLASSES.get(gateway_type, {}).get('available', False):
                enabled_gateways[gateway_key] = {
                    'config': gateway_config,
                    'type': gateway_type,
                    'classes': GATEWAY_CLASSES[gateway_type]
                }
                logger.info(f"发现启用的网关: {gateway_key} (类型: {gateway_type})")
            else:
                logger.warning(f"网关 {gateway_key} 已启用但类型 {gateway_type} 不可用")

    return enabled_gateways


# if __name__ == '__main__':
#     config_file: str = "D:\\Project\\PycharmProjects\\Homalos_v2\\config\\system.yaml"
#     get_config = ConfigManager(config_file)
#     enabled_gateways = get_enabled_gateways(get_config)
#     print(enabled_gateways)
#     # 初始化每个启用的网关
#     for gateway_key, gateway_info in enabled_gateways.items():
#         gateway_config = gateway_info['config']
#         gateway_type = gateway_info['type']
#         gateway_classes = gateway_info['classes']
#
#         print(f"gateway_key: {gateway_key}")
#         print(f"gateway_config: {gateway_config}")
#         print(f"gateway_type: {gateway_type}")
#         print(f"gateway_classes: {gateway_classes}")

