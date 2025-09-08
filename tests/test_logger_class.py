#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : test_logger_class.py
@Date       : 2025/9/8 15:25
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 类中使用日志模块
"""
from src.utils.log.logger import get_logger


class StrategyEngine:


    def __init__(self, name):
        self.name = name
        # 绑定上下文为类名，日志中显示 [StrategyEngine]
        self.logger = get_logger(f"{self.__class__.__name__}:{self.name}")
        self.logger.info("策略初始化完成")

    def run(self):
        self.logger.info("策略开始运行")
        try:
            1 / 0
        except Exception as e:
            self.logger.exception(f"策略运行出错: {e}")


if __name__ == '__main__':
    strategy = StrategyEngine("策略1")
    strategy.run()
