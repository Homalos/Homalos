#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Nilotica
@FileName   : ctp_gateway_helper
@Date       : 2025/5/20 16:44
@Author     : Donny
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: ctp gateway helper
"""
from datetime import datetime
from typing import Optional

from src.config.constant import Product, Exchange
from src.core.object import ContractData
from .ctp_mapping import PRODUCT_CTP2VT, EXCHANGE_CTP2VT, OPTIONTYPE_CTP2VT
from ...core.logger import get_logger

logger = get_logger("ctp_build_contract")


def ctp_build_contract(data: dict, gateway_name: str) -> ContractData | None:
    """
    合约对象构建及期权特殊处理
    """
    product: Product = PRODUCT_CTP2VT.get(data.get("ProductClass"), None)
    contract: Optional[ContractData] = None
    if product:
        contract: ContractData = ContractData(
            symbol=data.get("InstrumentID", ""),
            exchange=EXCHANGE_CTP2VT.get(data.get("ExchangeID", "")),
            name=data.get("InstrumentName", ""),
            product=product,
            size=data.get("VolumeMultiple", 1),
            price_tick=data.get("PriceTick", 0.0),
            min_volume=data.get("MinLimitOrderVolume", 1),
            max_volume=data.get("MaxLimitOrderVolume", 1),
            gateway_name=gateway_name
        )
        # 期权相关
        if contract.product == Product.OPTION:
            if contract.exchange == Exchange.CZCE:
                contract.option_portfolio = data.get("ProductID", "")[:-1]
            else:
                contract.option_portfolio = data.get("ProductID", "")
            contract.option_underlying = data.get("UnderlyingInstrID", "")
            contract.option_type = OPTIONTYPE_CTP2VT.get(data.get("OptionsType"))
            contract.option_strike = data.get("StrikePrice", 0.0)
            contract.option_index = str(data.get("StrikePrice", ""))
            try:
                contract.option_listed = datetime.strptime(data.get("OpenDate", ""), "%Y%m%d")
                contract.option_expiry = datetime.strptime(data.get("ExpireDate", ""), "%Y%m%d")
            except Exception as e:
                logger.error("期权合约构建失败: {}".format(e))
                contract.option_listed = None
                contract.option_expiry = None

    return contract

