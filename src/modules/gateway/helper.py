#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : helper.py
@Date       : 2025/9/10 17:47
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: gateway 的帮助类
"""
from src.constants import INSTRUMENT_EXCHANGE_FILEPATH
from src.utils.utility import load_json_file


def extract_error_msg(error: dict, func_name: str = "", custom_msg: str = "") -> str:
    """
    从错误响应中提取错误消息
    :param error: 错误响应的信息
    :param func_name: 函数名称
    :param custom_msg: 自定义消息
    :return: 错误消息
    """
    if isinstance(error, dict):
        if error and error.get("ErrorID") != 0:
            return (f"{func_name}: {custom_msg}, ErrorID={error.get('ErrorID', 'N/A')}, "
                    f"ErrorMsg={error.get('ErrorMsg', 'Unknown')}")
        elif error and error.get("ErrorID") == 0:
            return ""
        else:
            return f"{func_name}: {custom_msg}, Unknown error: {str(error)}"
    else:
        return f"{func_name}: {custom_msg}, Unknown type of error: {str(error)}"

def get_exchange_name(symbol: str) -> str:
    """
    获取交易所名称
    :param symbol: 合约代码
    :return: 交易所名称
    """
    return load_json_file(INSTRUMENT_EXCHANGE_FILEPATH).get(symbol, "")