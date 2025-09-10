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
            return f"{func_name}: {custom_msg}, ErrorID={error.get('ErrorMsg')}, ErrorMsg={error.get('ErrorMsg', '')}"
        elif error and error.get("ErrorID") == 0:
            return ""
        else:
            return f"{func_name}: {custom_msg}, Unknown error: {str(error)}"
    else:
        return f"{func_name}: {custom_msg}, Unknown type of error: {str(error)}"