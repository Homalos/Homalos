#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : commission_loader.py
@Date       : 2025/11/28
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 手续费配置加载器
"""
import configparser
from typing import Optional, Dict
from src.utils.log import get_logger
from src.utils.get_path import get_path_ins

logger = get_logger(__name__)


class CommissionLoader:
    """手续费配置加载器"""
    
    def __init__(self):
        self._config: Optional[Dict] = None
        self._loaded = False
        self.logger = logger
    
    def load_config(self) -> bool:
        """
        加载手续费配置文件
        
        Returns:
            bool: 是否加载成功
        """
        if self._loaded:
            return True
        
        try:
            # 获取配置文件路径
            config_path = get_path_ins.join_path("config", "product_info.ini")
            self.logger.info(f"加载手续费配置文件: {config_path}")
            
            # 读取配置文件
            config = configparser.ConfigParser()
            config.read(config_path, encoding='utf-8')
            
            # 解析配置
            self._config = {}
            for section in config.sections():
                product_name = section.strip()
                self._config[product_name] = {
                    'contract_multiplier': float(config.get(section, 'contract_multiplier', fallback=1)),
                    'minimum_price_change': float(config.get(section, 'minimum_price_change', fallback=0.0)),
                    'open_fee_rate': float(config.get(section, 'open_fee_rate', fallback=0.0)),
                    'open_fee': float(config.get(section, 'open_fee', fallback=0.0)),
                    'close_fee_rate': float(config.get(section, 'close_fee_rate', fallback=0.0)),
                    'close_fee': float(config.get(section, 'close_fee', fallback=0.0)),
                    'close_today_fee_rate': float(config.get(section, 'close_today_fee_rate', fallback=0.0)),
                    'close_today_fee': float(config.get(section, 'close_today_fee', fallback=0.0)),
                }
            
            self._loaded = True
            self.logger.info(f"✓ 手续费配置加载成功，共 {len(self._config)} 个产品")
            return True
        
        except Exception as e:
            self.logger.error(f"✗ 加载手续费配置失败: {e}", exc_info=True)
            self._config = {}
            self._loaded = False
            return False
    
    def get_commission(
        self,
        symbol: str,
        volume: int,
        price: float,
        offset_type: str
    ) -> float:
        """
        计算手续费
        
        Args:
            symbol: 合约代码（如 'FG601', 'IH2512' 等）
            volume: 成交数量
            price: 成交价格
            offset_type: 开平类型 ('OPEN' 或 'CLOSE')
            
        Returns:
            float: 手续费
        """
        if not self._loaded:
            self.load_config()
        
        if not self._config:
            self.logger.warning(f"手续费配置为空，无法计算 {symbol} 的手续费")
            return 0.0
        
        # 从合约代码中提取产品名称（如 'FG601' -> 'FG'）
        product_name = self._extract_product_name(symbol)
        
        if product_name not in self._config:
            self.logger.warning(f"未找到产品 {product_name} 的手续费配置")
            return 0.0
        
        product_config = self._config[product_name]
        contract_multiplier = product_config.get('contract_multiplier', 1)
        
        # 根据开平类型选择手续费
        if offset_type == 'OPEN':
            fee_rate = product_config.get('open_fee_rate', 0.0)
            fee = product_config.get('open_fee', 0.0)
        elif offset_type == 'CLOSE':
            fee_rate = product_config.get('close_fee_rate', 0.0)
            fee = product_config.get('close_fee', 0.0)
        else:
            self.logger.warning(f"未知的开平类型: {offset_type}")
            return 0.0
        
        # 计算手续费: 固定费用 + 按比例费用
        # 按比例费用 = 价格 * 数量 * 合约乘数 * 费率
        commission = fee + price * volume * contract_multiplier * fee_rate
        
        return round(commission, 2)
    
    def _extract_product_name(self, symbol: str) -> str:
        """
        从合约代码中提取产品名称
        
        例如:
        - 'FG601' -> 'FG'
        - 'IH2512' -> 'IH'
        - 'SA2512' -> 'SA'
        
        Args:
            symbol: 合约代码
            
        Returns:
            str: 产品名称
        """
        # 提取前面的字母部分
        product_name = ''
        for char in symbol:
            if char.isalpha():
                product_name += char
            else:
                break
        
        return product_name


# 全局单例
_commission_loader = None


def get_commission_loader() -> CommissionLoader:
    """获取手续费加载器单例"""
    global _commission_loader
    if _commission_loader is None:
        _commission_loader = CommissionLoader()
    return _commission_loader
