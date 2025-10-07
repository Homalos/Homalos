#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : test_task_scheduler.py
@Date       : 2025/10/7 23:36
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: description
"""
import time

from src.api.task_scheduler import task_scheduler_ins

if __name__ == "__main__":

    import datetime

    def my_func(task_name):
        now = datetime.datetime.now()
        print(f"{now}: 这是{task_name}任务")

    def ceshi_thread(task_name):
        now = datetime.datetime.now()
        print(f"{now}: 开始{task_name}任务")
        time.sleep(5)
        now = datetime.datetime.now()
        print(f"{now}: 结束{task_name}任务")

    # 添加每天要执行的任务
    task_scheduler_ins.add_daily_task("23:05", lambda: my_func("每天"), task_name="my_func(每天)")

    # 添加只执行一次的任务
    task_scheduler_ins.add_once_task("2025-10-07 23:02", lambda: my_func("只执行一次"), task_name="my_func(只执行一次)")


    # 添加每周某几天要执行的任务
    # "Mon：星期一,Tue：星期二,Wed：星期三,Thu：星期四,Fri：星期五,Sat：星期六,Sun：星期日
    task_scheduler_ins.add_weekday_task("23:03", lambda: my_func("每周"), "Sat", task_name="my_func(每周)")  # 每周一的10点执行

    # 添加每月某天或某几天要执行的任务
    task_scheduler_ins.add_monthly_task("23:04", lambda: my_func("每月"), "03", task_name="my_func(每月)")  # 每月1号的10点执行

    # 启动任务调度器
    task_scheduler_ins.run()

    # 添加每分钟要执行的任务
    task_scheduler_ins.add_minute_task(lambda: my_func("每分钟"), task_name="my_func(每分钟)")

    # 添加每分钟要执行的任务, 主要用于测试多线程是否有延迟
    task_scheduler_ins.add_minute_task(lambda: ceshi_thread("delay1"), task_name="ceshiThread2")
    task_scheduler_ins.add_minute_task(lambda: ceshi_thread("delay2"), task_name="ceshiThread2")

    task_scheduler_ins.statistic()

    # 保持程序运行，按Ctrl+C退出
    print("\n任务调度器已启动，按 Ctrl+C 退出...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n正在停止任务调度器...")
        task_scheduler_ins.stop()
        print("任务调度器已停止")