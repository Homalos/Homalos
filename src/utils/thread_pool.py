#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : thread_pool.py
@Date       : 2025/9/15 11:15
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 自定义线程池
"""
import threading
from concurrent.futures import ThreadPoolExecutor, Future
from datetime import datetime
from typing import Dict, Any, Callable

from src.utils.log import get_logger


class ThreadPool:
    """
    自定义线程池
    
    特性：
    - 支持动态扩展线程池
    - 自动警戒线管理
    - 线程安全的任务提交和回调
    - 完善的异常处理
    - 资源清理和重置
    """

    def __init__(self, max_workers: int, add_max_workers: int) -> None:
        """
        初始化线程池
        
        Args:
            max_workers: 初始线程池最大线程数
            add_max_workers: 扩展线程池最大线程数
        """
        # 当前使用的线程池序号
        self.now_pool_num: int = 1

        # 当前线程池满了之后的下一个线程池序号
        self.next_pool_num: int = -1

        # 线程池中最大线程池的个数
        self.max_workers: int = max_workers

        # 增加线程池中最大线程池的个数
        self.add_max_workers: int = add_max_workers

        # 初始警戒位置，如果达到警戒位置则寻找一个空闲线程池
        if max_workers * 0.05 > 1:
            self.warn_workers_num = int(max_workers * 0.95)
        else:
            self.warn_workers_num = max_workers - 1

        # 增加线程池的警戒界位置，如果达到警戒位置则寻找一个空闲线程池
        if add_max_workers * 0.05 > 1:
            self.add_warn_workers_num = int(add_max_workers * 0.95)
        else:
            self.add_warn_workers_num = add_max_workers - 1

        self.thread_pool_map: Dict[int, ThreadPoolExecutor] = {
            self.now_pool_num: ThreadPoolExecutor(max_workers=max_workers,
                                                  thread_name_prefix=f"threadPool_{self.now_pool_num}")
        }
        # 线程池中活跃线程个数的字典
        self.pool_alive_num_map: Dict[int, int] = {self.now_pool_num: 0}

        # 提交锁，防止同时提交
        self.submit_lock: threading.Lock = threading.Lock()

        # 准备信号，是否准备好下一个空闲线程池
        self.prepare_flag: bool = False

        self.logger = get_logger(__class__.__name__)

    def __enter__(self):
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口，自动清理资源"""
        self.clean_pool()

    def submit(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Future[Any]:
        """
        提交任务到线程池
        
        Args:
            fn: 要执行的函数
            *args: 函数的位置参数
            **kwargs: 函数的关键字参数
            
        Returns:
            Future对象，可用于获取执行结果
        """
        with self.submit_lock:
            if self.now_pool_num == 1:
                warn_workers_num = self.warn_workers_num
                max_workers = self.max_workers
            else:
                warn_workers_num = self.add_warn_workers_num
                max_workers = self.add_max_workers
            # 如果当前线程池满了，需要更换新的线程池
            if self.pool_alive_num_map[self.now_pool_num] >= max_workers:
                if self.next_pool_num != -1:
                    self.now_pool_num = self.next_pool_num
                    self.prepare_flag = False
            # 如果当前线程池达到警戒线，并未准备好下一个
            elif (self.pool_alive_num_map[self.now_pool_num] == warn_workers_num) and (self.prepare_flag is False):
                self.find_free_pool()
                self.prepare_flag = True

            ret = self.thread_pool_map[self.now_pool_num].submit(fn, *args, **kwargs)
            self.pool_alive_num_map[self.now_pool_num] += 1
            ret.add_done_callback(self.callback)
            return ret


    def find_free_pool(self) -> None:
        """
        寻找一个空闲的线程池，如果没有则创建一个新的线程池
        :return:
        """
        # 如果只有一个线程池则开启一个线程池，并以新建的线程池为工作线程池
        if len(self.thread_pool_map) == 1:
            self.next_pool_num = self.add_pool()

        else:
            # 判断是否所有线程池活跃线程都达到上限，如果是则创建线程线程池，并以新建的线程池为工作线程池
            # 否则寻找一个空闲的线程池为工作线程池
            pool_num = self.which_pool_free()
            if pool_num == -1:
                self.next_pool_num = self.add_pool()
            else:
                self.next_pool_num = pool_num

    def add_pool(self) -> int:
        """
        增加一个线程池，并返回增加线程池在线程池字典中的序号
        :return:
        """
        add_pool_num = self.get_max_pool_num() + 1

        # 添加线程池
        self.thread_pool_map[add_pool_num] = ThreadPoolExecutor(
            max_workers=self.add_max_workers, thread_name_prefix=f"threadPool_{add_pool_num}")
        # 添加线程池活跃线程字典
        self.pool_alive_num_map[add_pool_num] = 0

        return add_pool_num

    def get_max_pool_num(self) -> int:
        # 获取线程池字典中最大的线程序号
        max_num = 0
        for num in self.thread_pool_map.keys():
            if num > max_num:
                max_num = num
        return max_num

    def which_pool_free(self) -> int:
        # 判断当前线程池字典是否有空闲的线程池
        for pool_num in self.thread_pool_map.keys():
            if self.is_pool_free(pool_num):
                return pool_num
        return -1

    def is_pool_free(self, pool_num: int) -> bool:
        # 判断当前线程池是否有空闲位置
        # 如果活跃线程小于60%则为空闲
        if pool_num == 1:
            max_workers = self.max_workers
        else:
            max_workers = self.add_max_workers
        if self.pool_alive_num_map[pool_num] < max_workers * 0.6:
            return True
        else:
            return False

    @staticmethod
    def get_pool_all_thread(prefix: str = "threadPool") -> list:
        # 获取线程池中的所有线程，
        # 300个活跃线程，循环一万次花费1.1933586597442627s
        pool_alive_thread = []
        for t in threading.enumerate():
            if prefix in t.name:
                pool_alive_thread.append(t)
        return pool_alive_thread

    @staticmethod
    def get_pool_all_thread_num(prefix: str = "threadPool") -> int:
        # 获取线程池中所有活跃的线程的数量
        pool_alive_thread = []
        for t in threading.enumerate():
            if prefix in t.name:
                pool_alive_thread.append(t)
        return len(pool_alive_thread)

    def callback(self, ret: Future[Any]) -> None:
        with self.submit_lock:
            pool_num = self.get_pool_num()
            if pool_num != -1 and pool_num in self.pool_alive_num_map:
                if self.pool_alive_num_map[pool_num] > 0:
                    self.pool_alive_num_map[pool_num] -= 1
            
            # 检查任务是否有异常
            exception = ret.exception()
            if exception is not None:
                self.logger.exception(f"线程池任务执行异常: {exception}")

    @staticmethod
    def get_pool_num() -> int:
        thread_name = threading.current_thread().name
        if 'threadPool' not in thread_name:
            return -1
        else:
            return int(thread_name.split('_')[1])

    def clean_pool(self) -> None:
        """清理所有线程池并重置为初始状态"""
        with self.submit_lock:
            self.logger.info('开始清理线程池')
            self.logger.info(f'当前线程池总数：{len(self.thread_pool_map)}')
            
            for pool_num in self.pool_alive_num_map.keys():
                self.logger.info(f'线程池{pool_num}中活跃线程数：{self.pool_alive_num_map[pool_num]}')
            
            # 关闭所有线程池
            for pool_num in list(self.thread_pool_map.keys()):
                try:
                    self.thread_pool_map[pool_num].shutdown(wait=True)
                except Exception as e:
                    self.logger.error(f'关闭线程池{pool_num}时出错: {e}')
            
            # 重置状态
            self.now_pool_num = 1
            self.next_pool_num = -1
            self.prepare_flag = False
            
            # 重建线程池
            self.thread_pool_map = {
                self.now_pool_num: ThreadPoolExecutor(max_workers=self.max_workers,
                                                      thread_name_prefix=f"threadPool_{self.now_pool_num}")
            }
            
            # 重置计数器
            self.pool_alive_num_map = {self.now_pool_num: 0}
            
            self.logger.info('已重置线程池')
            for pool_num in self.pool_alive_num_map.keys():
                self.logger.info(f'清理后线程池{pool_num}中活跃线程数：{self.pool_alive_num_map[pool_num]}')

    def show_all_thread(self) -> None:
        self.logger.info(f"总线程数：{len(threading.enumerate())}")
        for pool_num in self.thread_pool_map.keys():
            self.logger.info(f'线程池{pool_num}中线程总数为：{self.get_pool_all_thread_num(f"threadPool_{pool_num}")}')


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

