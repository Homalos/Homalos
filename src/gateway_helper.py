#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : gateway_helper.py
@Date       : 2025/6/5 22:12
@Author     : Donny
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: description
"""
import re
from configparser import ConfigParser


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

