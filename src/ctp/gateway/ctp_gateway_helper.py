#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Nilotica
@FileName   : ctp_gateway_helper
@Date       : 2025/5/20 16:44
@Author     : Donny
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: ctp_gateway helper
"""
import re
from configparser import ConfigParser
from datetime import datetime

from src.util.i18n import _
from src.util.logger import logger
from src.config.constants import Product, Exchange
from src.core.object import ContractData
from .ctp_mapping import PRODUCT_CTP2VT, EXCHANGE_CTP2VT, OPTIONTYPE_CTP2VT


def del_num(content):
    """
    删除字符串中的所有数字。

    Args:
        content (str): 需要删除数字的字符串。

    Returns:
        str: 删除数字后的字符串。

    :param content:
    :return:
    """
    res = re.sub(r'\d', '', content)
    return res

def calculate_commission_rate(product_parser: ConfigParser, p_trade):
    """
    计算手续费
    :param product_parser:
    :param p_trade:
    :return:
    """
    # 产品
    product = del_num(p_trade['InstrumentID'])
    # 数量
    volume = p_trade['Volume']
    # 合约乘数
    volume_multiple = float(product_parser[product]["contract_multiplier"])
    # 开仓手续费率
    open_ratio_by_money = float(product_parser[product]["open_fee_rate"])
    # 开仓手续费
    open_ratio_by_volume = float(product_parser[product]["open_fee"])
    # 平仓手续费率
    close_ratio_by_money = float(product_parser[product]["close_fee_rate"])
    # 平仓手续费
    close_ratio_by_volume = float(product_parser[product]["close_fee"])
    # 平今手续费率
    close_today_ratio_by_money = float(product_parser[product]["close_today_fee_rate"])
    # 平今手续费
    close_today_ratio_by_volume = float(product_parser[product]["close_today_fee"])

    fee = 'fee'

    # 这个信号是根据下单来决定的，填的平仓，实际平的是今仓，但是回报里是平仓，会按照平仓进行计算，有的时候会造成错误
    # 比如，m合约，平今手续费0.1，平昨是0.2
    # 开仓
    if p_trade.OffsetFlag == '0':
        fee = volume * (p_trade.Price * volume_multiple * open_ratio_by_money + open_ratio_by_volume)
        pass
    # 平仓
    elif p_trade.OffsetFlag == '1':
        fee = volume * (p_trade.Price * volume_multiple * close_ratio_by_money + close_ratio_by_volume)
        pass
    # 强平
    elif p_trade.OffsetFlag == '2':
        pass
    # 平今
    elif p_trade.OffsetFlag == '3':
        fee = volume * (p_trade.Price * volume_multiple * close_today_ratio_by_money + close_today_ratio_by_volume)
        pass
    # 平昨
    elif p_trade.OffsetFlag == '4':
        fee = volume * (p_trade.Price * volume_multiple * close_ratio_by_money + close_ratio_by_volume)
        pass

    return fee

def ctp_build_contract(data: dict, gateway_name: str) -> ContractData | None:
    """合约对象构建及期权特殊处理"""
    product = PRODUCT_CTP2VT.get(data.get("ProductClass"))
    if not product:
        return None
    contract = ContractData(
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
            logger.error(_("期权合约构建失败: {}".format(e)))
            contract.option_listed = None
            contract.option_expiry = None
    return contract

