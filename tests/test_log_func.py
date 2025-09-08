#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : test_log_func.py
@Date       : 2025/9/8 16:48
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: description
"""
from src.utils.log import logger


def fetch_data():
    log = logger.bind(context="datafeed")  # 给当前模块绑定 context
    log.info("开始抓取数据")
    log.warning("API 响应缓慢")
    log.error("API 请求失败")


if __name__ == '__main__':
    fetch_data()
