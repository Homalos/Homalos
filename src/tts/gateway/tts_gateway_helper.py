#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Nilotica
@FileName   : tts_gateway_helper.py
@Date       : 2025/5/24 23:29
@Author     : Donny
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: description
"""
from datetime import datetime

from src.config.constants import Product, Exchange
from src.core.object import ContractData
from src.tts.gateway.tts_mapping import PRODUCT_TTS2VT, EXCHANGE_TTS2VT, OPTIONTYPE_TTS2VT


def tts_build_contract(data: dict, gateway_name: str) -> ContractData | None:
    """合约对象构建及期权特殊处理"""
    product: Product = PRODUCT_TTS2VT.get(data["ProductClass"], None)
    exchange: Exchange = EXCHANGE_TTS2VT.get(data["ExchangeID"], None)
    if not product or not exchange:
        return None

    contract: ContractData = ContractData(
        symbol=data.get("InstrumentID", ""),
        exchange=EXCHANGE_TTS2VT.get(data.get("ExchangeID", "")),
        name=data.get("InstrumentName", ""),
        product=product,
        size=data.get("VolumeMultiple", 1),
        price_tick=data.get("PriceTick", 0.0),
        gateway_name=gateway_name
    )

    # 期权相关
    if contract.product == Product.OPTION:
        # 移除郑商所期权产品名称带有的C/P后缀
        if contract.exchange == Exchange.CZCE:
            contract.option_portfolio = data["ProductID"][:-1]
        else:
            contract.option_portfolio = data["ProductID"]

        contract.option_underlying = data["UnderlyingInstrID"]
        contract.option_type = OPTIONTYPE_TTS2VT.get(data["OptionsType"], None)
        contract.option_strike = data["StrikePrice"]
        contract.option_index = str(data["StrikePrice"])
        contract.option_expiry = datetime.strptime(data["ExpireDate"], "%Y%m%d")

    elif contract.product == Product.EQUITY or contract.product == Product.FUND:
        if exchange in [Exchange.SSE, Exchange.SZSE]:
            contract.min_volume = 100
    elif contract.product == Product.BOND and exchange in [Exchange.SSE, Exchange.SZSE]:
        contract.min_volume = 10

    return contract