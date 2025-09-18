#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : test_thread_pool.py
@Date       : 2025/9/18 15:49
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: description
"""
import threading
from datetime import datetime

from src.utils.thread_pool import ThreadPool


def action(time_num: int) -> int:
    print("开始时间：{}".format(datetime.now().strftime("%H:%M:%S")))
    time.sleep(time_num)
    print("结束时间：{}".format(datetime.now().strftime("%H:%M:%S")))
    return 1


def action2(time_num: int, action_num: int) -> int:
    print("开始时间：{}".format(datetime.now().strftime("%H:%M:%S")))
    time.sleep(time_num)
    print("结束时间：{}".format(datetime.now().strftime("%H:%M:%S")))
    return 1



if __name__ == "__main__":
    import time
    pool = ThreadPool(5, 10)

    print("第一次提交")
    start = time.time()
    for i in range(20):
        print(i)
        pool.submit(action, 1)
    end = time.time()
    print(f"第一次提交花费时间：{end - start}s")

    print(threading.current_thread())
    for i in range(5):
        time.sleep(1)

    print("第二次提交")
    pool.submit(action2, 2, 2)

    time.sleep(2)
