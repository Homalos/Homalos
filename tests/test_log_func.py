#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : test_log_func.py
@Date       : 2025/9/8 16:48
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 函数中使用日志模块
"""
from src.utils.log.logger import get_logger


def fetch_data():
    logger = get_logger("datafeed")  # # 给当前模块绑定 context
    logger.info("开始抓取数据")
    logger.warning("API 响应缓慢")
    logger.error("API 请求失败")


if __name__ == '__main__':
    fetch_data()
