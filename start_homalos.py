#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : start_homalos.py
@Date       : 2025/10/11 15:34
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 系统入口
"""
from src.api.bar_generator import bar_generator_ins
from src.api.task_scheduler import task_scheduler_ins
from src.function import function_ins
from src.strategy import strategy_pool_ins
from src.strategy.strategy1 import strategy1


def main():
    print("Hello from homalos!")
    strategy_pool_ins.add_strategy(1, strategy1)
    strategy_pool_ins.get_strategy_pool_info()

    task_scheduler_ins.add_minute_task(bar_generator_ins.check_min1, "检查1分钟K线")
    task_scheduler_ins.add_minute_task(function_ins.check_alarm, "检查策略闹钟")


if __name__ == "__main__":
    main()
