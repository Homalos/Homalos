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


def extract_error_msg(rsp_info: dict, custom_msg: str = "出错") -> str:
    """
    从响应中提取错误消息
    :param rsp_info: 响应的信息
    :param custom_msg: 自定义消息
    :return: 错误消息
    """
    if isinstance(rsp_info, dict):
        if rsp_info and rsp_info.get("ErrorID") != 0:
            return (f"{custom_msg}, 错误代码：{rsp_info.get('ErrorID', 'N/A')}, "
                    f"错误信息：{rsp_info.get('ErrorMsg', 'Unknown')}")
        elif rsp_info and rsp_info.get("ErrorID") == 0:
            return ""
        else:
            return f"{custom_msg}, 未知错误：{str(rsp_info)}"
    else:
        return f"{custom_msg}, 未知类型错误：{type(rsp_info)}, {str(rsp_info)}"

def get_exchange_name(symbol: str) -> str:
    """
    获取交易所名称
    :param symbol: 合约代码
    :return: 交易所名称
    """
    return load_json_file(INSTRUMENT_EXCHANGE_FILEPATH).get(symbol, "")