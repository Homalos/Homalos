#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : test_logger_class.py
@Date       : 2025/9/8 15:25
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: description
"""
from src.utils.log import logger


class StrategyEngine:
    def __init__(self, name):
        self.name = name
        logger.info(f"策略引擎 {self.name} 初始化完成")

    def run(self):
        logger.info(f"策略 {self.name} 开始运行")
        try:
            1 / 0
        except Exception:
            logger.exception("策略运行出错")


if __name__ == '__main__':
    strategy = StrategyEngine("策略1")
    strategy.run()
