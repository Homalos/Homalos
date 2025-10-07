#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : thread_pool.py
@Date       : 2025/10/7 21:02
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 线程池类
"""
import threading
import traceback
from concurrent.futures import ThreadPoolExecutor

from src.api.thread_pool import pool_config
from src.utils.log import get_logger
from src.utils.time import time_module_ins
from src.utils.utility import write_csv, is_file_in


class ThreadPool(object):

    def __init__(self, max_workers=35) -> None:
        """
        初始化线程池
        :param max_workers: 最大线程数
        """
        # 创建新的线程池
        self.pool = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="Pool")
        # 线程池锁，每一次更新消息时保证数据安全,每个线程池对应一个锁
        self.pool_lock = threading.Lock()
        # 用于记录每个线程池中未完成工作数量
        self.wait_num = 0
        self.logger = get_logger(__class__.__name__)

    def submit(self, fn, *args, **kwargs) -> None:
        """
        提交任务，并将线程保存到对应列表中，用于后续判断

        Args:
            fn: 要执行的可调用对象
            *args: 传递给fn的位置参数
            **kwargs: 传递给fn的关键字参数

        Returns:
            None
        """
        future = self.pool.submit(fn, *args, **kwargs)
        future.add_done_callback(self.callback)
        self.pool_lock.acquire()
        self.wait_num += 1
        self.pool_lock.release()

    def clean_pool(self) -> None:
        pass

    def statistics(self) -> str:
        """
        统计线程池信息

        Returns:
            str: 统计信息
        """
        state = "#" * 15 + '\n'
        state += f"线程池未完成工作数量：{self.wait_num}"
        return state

    def callback(self, ret) -> None:
        """
        回调函数，用于计算线程池中还有多少线程未完成

        Args:
            ret:

        Returns:
            None
        """
        self.pool_lock.acquire()
        self.wait_num -= 1
        self.pool_lock.release()
        if ret.exception() is not None:
            self.logger.exception(traceback.format_exc())

    def record(self) -> None:
        """
        记录线程池信息

        Returns:
            None
        """
        # 如果文件不存在则创建
        filename = '{}-pool.csv'.format(time_module_ins.now().strftime("%Y%m%d"))
        if not is_file_in(filename, pool_config.save_path):
            content = pool_config.pool_column
            write_csv(f"{pool_config.save_path}/{filename}", 'w', content)
        # 判断文件是否第一次运行
        if pool_config.is_first:
            content = pool_config.pool_column
            write_csv(f"{pool_config.save_path}/{filename}", 'w', content)
            pool_config.isFirst = False

        now_time = time_module_ins.now().strftime("%Y-%m-%d %H:%M:%S.%f")

        content = [now_time, self.wait_num]
        write_csv(f"{pool_config.save_path}/{filename}", 'a', content)
